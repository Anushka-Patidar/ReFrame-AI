"""Local inpainting provider using StableDiffusionInpaintPipeline.

Canonical mask semantics (ReFrame internal):
  WHITE (255) = editable / regenerate
  BLACK (0)   = preserve / protected

The SD inpainting pipeline expects the SAME convention:
  white = inpaint region, black = keep original.

So we pass our edit_mask directly — no polarity inversion needed.
"""

from __future__ import annotations

import gc
import logging
import threading
import time
from pathlib import Path
from typing import Callable

from PIL import Image, ImageFilter

from app.core.config import settings
from app.services.design_brief import (
    DesignBrief,
    build_edit_requirements_block,
    build_local_clip_prompt,
    build_local_negative_prompt,
)
from app.services.generation_runtime import (
    USER_GENERIC_ERROR,
    USER_RESOURCE_ERROR,
    generation_gate,
)
from app.services.hardware import (
    LocalAiProfile,
    active_profile,
    choose_profile,
    process_rss_gb,
    system_available_gb,
)
from app.services.media import UPLOADS_ROOT
from app.services.pipeline.image_preprocess import (
    compute_inference_size,
    safe_postprocess,
)
from app.services.pipeline.types import SegmentationResult, StructuralSignals
from app.services.providers import GenerationResult, RoomGenerationProvider

logger = logging.getLogger(__name__)

INPAINTING_MODEL_ID = "runwayml/stable-diffusion-inpainting"

# Mask expansion/blur for better edge blending around edited objects.
DEFAULT_MASK_EXPAND_PX = 8
DEFAULT_MASK_BLUR_PX = 5

ProgressCallback = Callable[[str, int | None, int | None], None]


def _mem_log(label: str, marks: dict[str, float | None]) -> None:
    rss = process_rss_gb()
    avail = system_available_gb()
    marks[label] = rss
    logger.info(
        "REFRAME_INPAINT_MEM stage=%s rss=%s avail=%s",
        label,
        f"{rss:.3f}" if rss is not None else "n/a",
        f"{avail:.3f}" if avail is not None else "n/a",
    )


def _cleanup() -> None:
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _expand_and_blur_mask(
    mask: Image.Image,
    expand_px: int = DEFAULT_MASK_EXPAND_PX,
    blur_px: int = DEFAULT_MASK_BLUR_PX,
) -> Image.Image:
    """Dilate mask slightly then gaussian-blur edges for seamless inpainting."""
    out = mask.convert("L")
    if expand_px > 0:
        out = out.filter(ImageFilter.MaxFilter(size=max(3, expand_px * 2 + 1)))
    if blur_px > 0:
        out = out.filter(ImageFilter.GaussianBlur(radius=blur_px))
    return out


def _load_edit_mask_from_segmentation(
    seg: SegmentationResult,
    target_size: tuple[int, int],
) -> Image.Image | None:
    """Load the combined edit mask from disk and resize to target inference size."""
    if not seg.edit_mask_path:
        return None
    try:
        path = UPLOADS_ROOT / seg.edit_mask_path
        with Image.open(path) as m:
            alpha = m.convert("RGBA").split()[-1]
        # Binary threshold
        binary = alpha.point(lambda p: 255 if p > 0 else 0)
        # Expand + blur for edge blending
        processed = _expand_and_blur_mask(binary)
        if processed.size != target_size:
            processed = processed.resize(target_size, resample=Image.Resampling.LANCZOS)
        return processed
    except Exception:
        logger.exception("Failed to load edit mask from %s", seg.edit_mask_path)
        return None


class LocalInpaintingProvider(RoomGenerationProvider):
    """Inpainting provider using runwayml/stable-diffusion-inpainting.

    Capabilities:
      supports_img2img: False (use LocalDiffusionProvider for that)
      supports_inpainting: True
      supports_structure: False (ControlNet not loaded yet)
      supports_controlnet: False
      supports_keep_mask: True (via edit_mask inversion)
      supports_negative_prompt: True
      supports_seed: True
    """

    name = "local-inpainting"
    supports_masks: bool = True
    supports_structure: bool = False
    supports_inpainting: bool = True

    def __init__(self) -> None:
        self._pipe = None
        self._device = "cpu"
        self._dtype_name = "float32"
        self._model_id = ""
        self._load_lock = threading.Lock()
        self._last_memory: dict[str, float | None] = {}
        self._last_run_config: dict = {}

    @property
    def last_run_config(self) -> dict:
        return dict(self._last_run_config)

    def is_available(self) -> bool:
        """Check if the inpainting model can be loaded."""
        try:
            import torch  # noqa: F401
            from diffusers import StableDiffusionInpaintPipeline  # noqa: F401
            return True
        except ImportError:
            return False

    def generate_room(
        self,
        source_image: Image.Image,
        design_brief: DesignBrief,
        transformation_strength: str | None = None,
        *,
        on_progress: ProgressCallback | None = None,
        profile: LocalAiProfile | None = None,
        constraints=None,
        segmentation: SegmentationResult | None = None,
        structure: StructuralSignals | None = None,
        seed: int | None = None,
        strength_override: float | None = None,
        steps_override: int | None = None,
    ) -> GenerationResult:
        marks: dict[str, float | None] = {}
        _mem_log("before_model_loading", marks)

        profile = profile or choose_profile()

        def progress(stage: str, step: int | None = None, total: int | None = None) -> None:
            generation_gate.set_stage(stage, step=step, total_steps=total)
            if on_progress:
                on_progress(stage, step, total)

        progress("analyzing")
        self._ensure_pipeline(profile)
        _mem_log("after_model_loading", marks)

        progress("preparing")

        # Prepare source image at inference resolution (aspect-preserving).
        src = source_image.convert("RGB")
        # For inpainting, use 512px (SD1.5 native) capped by profile.
        max_side = min(512, profile.max_side) if profile.max_side > 0 else 512
        inf_w, inf_h = compute_inference_size(src.width, src.height, max_side)
        src_resized = src.resize((inf_w, inf_h), Image.Resampling.LANCZOS)

        # Load and prepare the edit mask.
        edit_mask: Image.Image | None = None
        if segmentation and segmentation.edit_mask_path:
            edit_mask = _load_edit_mask_from_segmentation(segmentation, (inf_w, inf_h))

        if edit_mask is None:
            # No mask available — fall back to a full-edit mask (entire image editable).
            # This is equivalent to img2img but through the inpainting pipeline.
            logger.warning("REFRAME_INPAINT no edit mask available; using full-image mask")
            edit_mask = Image.new("L", (inf_w, inf_h), 255)

        _mem_log("after_source_prep", marks)

        # Build prompts.
        prompt = build_local_clip_prompt(design_brief)
        negative = build_local_negative_prompt(design_brief)

        # Inpainting strength: how much of the masked region to regenerate.
        # 1.0 = fully regenerate masked area, 0.8 = blend with original.
        strength_label = (transformation_strength or design_brief.transformation_strength or "balanced").lower()
        inpaint_strength = float(strength_override) if strength_override is not None else {
            "subtle": 0.75,
            "balanced": 0.88,
            "strong": 0.98,
        }.get(strength_label, 0.88)
        inpaint_strength = max(0.5, min(1.0, inpaint_strength))

        steps = int(steps_override if steps_override is not None else max(20, profile.steps))
        guidance = float(max(7.0, profile.guidance))

        import torch

        if seed is None:
            seed = int(torch.randint(0, 2**31 - 1, (1,)).item())
        generator = torch.Generator(device="cpu").manual_seed(int(seed))

        logger.info(
            "REFRAME_INPAINT_PROFILE model=%s device=%s dtype=%s "
            "res=%sx%s steps=%s strength=%.3f guidance=%.2f seed=%s "
            "mask_available=%s",
            self._model_id, self._device, self._dtype_name,
            inf_w, inf_h, steps, inpaint_strength, guidance, seed,
            edit_mask is not None,
        )
        logger.info("REFRAME_INPAINT_PROMPT_POS %s", prompt)
        logger.info("REFRAME_INPAINT_PROMPT_NEG %s", negative)
        logger.info("REFRAME_INPAINT_EDIT_BLOCK\n%s", build_edit_requirements_block(design_brief))

        progress("redesigning", 0, steps)
        started = time.perf_counter()
        image: Image.Image | None = None

        try:
            def _step_cb(pipe, step_index, timestep, callback_kwargs):
                progress("redesigning", int(step_index) + 1, steps)
                if step_index == 0:
                    _mem_log("during_latent_prep", marks)
                return callback_kwargs

            with torch.inference_mode():
                result = self._pipe(
                    prompt=prompt,
                    negative_prompt=negative,
                    image=src_resized,
                    mask_image=edit_mask,
                    height=inf_h,
                    width=inf_w,
                    strength=inpaint_strength,
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                    generator=generator,
                    callback_on_step_end=_step_cb,
                )
            _mem_log("after_inference", marks)
            image = result.images[0].convert("RGB")
            del result
        except Exception as exc:
            _cleanup()
            message = str(exc).lower()
            logger.exception("Inpainting generation failed: %s", exc)
            if any(t in message for t in ("out of memory", "not enough memory", "memoryerror", "paging file")):
                raise RuntimeError(USER_RESOURCE_ERROR) from exc
            raise RuntimeError(USER_GENERIC_ERROR) from exc
        finally:
            src_resized.close()
            edit_mask.close()

        progress("refining")

        # Restore to a reasonable display size matching original aspect.
        display_max = profile.display_max_side or 800
        sw, sh = source_image.size
        if max(sw, sh) > display_max:
            scale = display_max / max(sw, sh)
            sw, sh = max(1, int(sw * scale)), max(1, int(sh * scale))
        final = image.resize((sw, sh), Image.Resampling.LANCZOS)
        image.close()
        final = safe_postprocess(final, mild_sharpen=profile.mild_sharpen)

        _cleanup()
        _mem_log("after_generation", marks)
        self._last_memory = marks

        elapsed = time.perf_counter() - started
        peak = max((v for v in marks.values() if v is not None), default=None)

        self._last_run_config = {
            "model": self._model_id,
            "device": self._device,
            "dtype": self._dtype_name,
            "profile": profile.name,
            "input_resolution": [inf_w, inf_h],
            "output_resolution": list(final.size),
            "steps": steps,
            "strength": inpaint_strength,
            "guidance": guidance,
            "seed": seed,
            "elapsed_seconds": elapsed,
            "peak_rss_gb": peak,
            "mode": "inpainting",
        }

        logger.info(
            "REFRAME_INPAINT done model=%s elapsed=%.1fs peak_rss=%s seed=%s",
            self._model_id, elapsed,
            f"{peak:.3f}" if peak is not None else "n/a",
            seed,
        )

        return GenerationResult(
            image=final,
            provider="local-inpainting",
            model=self._model_id,
            device=self._device,
            steps=steps,
            strength=inpaint_strength,
            resolution=(inf_w, inf_h),
            elapsed_seconds=elapsed,
            seed=int(seed),
            engine=(
                f"local-inpaint:{self._model_id}|device={self._device}"
                f"|strength={inpaint_strength:.2f}|steps={steps}"
                f"|res={inf_w}x{inf_h}|seed={seed}|t={elapsed:.1f}s"
            ),
        )

    def _ensure_pipeline(self, profile: LocalAiProfile) -> None:
        with self._load_lock:
            if self._pipe is not None:
                return
            try:
                import torch
                from diffusers import StableDiffusionInpaintPipeline
            except ImportError as exc:
                raise RuntimeError(
                    "Diffusers/torch not installed. Cannot load inpainting model."
                ) from exc

            model_id = (
                settings.local_inpainting_model_id
                if hasattr(settings, "local_inpainting_model_id") and settings.local_inpainting_model_id
                else INPAINTING_MODEL_ID
            )

            device = "cpu"
            dtype = torch.float32
            dtype_name = "float32"
            if torch.cuda.is_available():
                device = "cuda"
                dtype = torch.float16
                dtype_name = "float16"

            logger.info("Loading inpainting model %s on %s ...", model_id, device)
            try:
                pipe = StableDiffusionInpaintPipeline.from_pretrained(
                    model_id,
                    torch_dtype=dtype,
                    safety_checker=None,
                    requires_safety_checker=False,
                    low_cpu_mem_usage=True,
                )
            except Exception as exc:
                logger.exception("Inpainting model load failed for %s", model_id)
                raise RuntimeError(USER_GENERIC_ERROR) from exc

            pipe = pipe.to(device)
            if hasattr(pipe, "enable_attention_slicing"):
                pipe.enable_attention_slicing("max")
            if hasattr(pipe, "vae"):
                if hasattr(pipe.vae, "enable_slicing"):
                    pipe.vae.enable_slicing()
                if hasattr(pipe.vae, "enable_tiling"):
                    try:
                        pipe.vae.enable_tiling()
                    except Exception:
                        pass

            pipe.set_progress_bar_config(disable=True)
            self._pipe = pipe
            self._device = device
            self._dtype_name = dtype_name
            self._model_id = model_id
            _cleanup()


_inpainting_lock = threading.Lock()
_shared_inpainting: LocalInpaintingProvider | None = None


def get_inpainting_provider() -> LocalInpaintingProvider:
    """Process-wide singleton for the inpainting pipeline."""
    global _shared_inpainting
    with _inpainting_lock:
        if _shared_inpainting is None:
            _shared_inpainting = LocalInpaintingProvider()
        return _shared_inpainting
