"""Controlled SD1.5 generation using a single Canny ControlNet pipeline.

This provider is the normal quality path for ReFrame:
- automatic mode: full-room controlled redesign with architecture conditioning
- precision mode: masked inpainting with the same structure conditioning stack

Tiny-SD remains preview-only and sits outside this provider.
"""

from __future__ import annotations

import gc
import logging
import threading
import time
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
    choose_profile,
    process_rss_gb,
    system_available_gb,
)
from app.services.media import UPLOADS_ROOT
from app.services.pipeline.image_preprocess import compute_inference_size, safe_postprocess
from app.services.pipeline.types import SegmentationResult, StructuralSignals
from app.services.providers import GenerationResult, RoomGenerationProvider

logger = logging.getLogger(__name__)

DEFAULT_MASK_EXPAND_PX = 8
DEFAULT_MASK_BLUR_PX = 5

ProgressCallback = Callable[[str, int | None, int | None], None]


def _mem_log(label: str, marks: dict[str, float | None]) -> None:
    rss = process_rss_gb()
    avail = system_available_gb()
    marks[label] = rss
    logger.info(
        "REFRAME_CONTROLLED_MEM stage=%s rss=%s avail=%s",
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


def _load_mask(segmentation: SegmentationResult | None, target_size: tuple[int, int]) -> Image.Image | None:
    if not segmentation or not segmentation.edit_mask_path:
        return None
    try:
        with Image.open(UPLOADS_ROOT / segmentation.edit_mask_path) as mask:
            alpha = mask.convert("RGBA").split()[-1]
        binary = alpha.point(lambda p: 255 if p > 0 else 0)
        expanded = binary.filter(ImageFilter.MaxFilter(size=max(3, DEFAULT_MASK_EXPAND_PX * 2 + 1)))
        softened = expanded.filter(ImageFilter.GaussianBlur(radius=DEFAULT_MASK_BLUR_PX))
        if softened.size != target_size:
            softened = softened.resize(target_size, Image.Resampling.LANCZOS)
        return softened
    except Exception:
        logger.exception("Failed to load edit mask for controlled provider")
        return None


def _load_structure_map(structure: StructuralSignals | None, target_size: tuple[int, int]) -> Image.Image | None:
    if not structure:
        return None
    structure_path = structure.architecture_condition_path or structure.edges_path
    if not structure_path:
        return None
    try:
        with Image.open(UPLOADS_ROOT / structure_path) as image:
            control = image.convert("RGB")
        if control.size != target_size:
            control = control.resize(target_size, Image.Resampling.LANCZOS)
        return control
    except Exception:
        logger.exception("Failed to load structure map for controlled provider")
        return None


class LocalControlledGenerationProvider(RoomGenerationProvider):
    name = "local-controlled"
    supports_masks: bool = True
    supports_structure: bool = True
    supports_controlnet: bool = True
    supports_inpainting: bool = True
    supports_seed: bool = True
    supports_negative_prompt: bool = True
    supports_img2img: bool = True

    def __init__(self) -> None:
        self._pipe = None
        self._device = "cpu"
        self._dtype_name = "float32"
        self._model_id = ""
        self._controlnet_model_id = ""
        self._load_lock = threading.Lock()
        self._last_memory: dict[str, float | None] = {}
        self._last_run_config: dict = {}

    @property
    def last_run_config(self) -> dict:
        return dict(self._last_run_config)

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
        structure_strength_override: float | None = None,
    ) -> GenerationResult:
        _ = constraints
        marks: dict[str, float | None] = {}
        _mem_log("before_model_loading", marks)

        profile = profile or choose_profile()

        def progress(stage: str, step: int | None = None, total: int | None = None) -> None:
            generation_gate.set_stage(stage, step=step, total_steps=total)
            if on_progress:
                on_progress(stage, step, total)

        progress("analyzing")
        self._ensure_pipeline()
        _mem_log("after_model_loading", marks)

        progress("preparing")
        src = source_image.convert("RGB")
        inf_w, inf_h = compute_inference_size(src.width, src.height, profile.max_side)
        src_resized = src.resize((inf_w, inf_h), Image.Resampling.LANCZOS)

        edit_mask = _load_mask(segmentation, (inf_w, inf_h))
        has_mask = edit_mask is not None
        if edit_mask is None:
            edit_mask = Image.new("L", (inf_w, inf_h), 255)

        control_image = _load_structure_map(structure, (inf_w, inf_h))
        if control_image is None:
            control_image = src_resized.convert("L").filter(ImageFilter.FIND_EDGES).convert("RGB")

        _mem_log("after_source_prep", marks)

        prompt = build_local_clip_prompt(design_brief)
        negative = build_local_negative_prompt(design_brief)
        strength_label = (transformation_strength or design_brief.transformation_strength or "balanced").lower()
        denoise_strength = (
            float(strength_override)
            if strength_override is not None
            else {
                "subtle": 0.72 if has_mask else 0.62,
                "balanced": 0.86 if has_mask else 0.70,
                "strong": 0.95 if has_mask else 0.78,
            }.get(strength_label, 0.70)
        )
        denoise_strength = max(0.45, min(0.98, denoise_strength))
        steps = int(steps_override if steps_override is not None else profile.steps)
        guidance = float(max(profile.guidance, 7.0))
        structure_strength = float(
            structure_strength_override
            if structure_strength_override is not None
            else (settings.local_structure_strength or profile.structure_strength)
        )
        structure_strength = max(0.2, min(1.3, structure_strength))

        import torch

        if seed is None:
            seed = int(torch.randint(0, 2**31 - 1, (1,)).item())
        generator = torch.Generator(device="cpu").manual_seed(int(seed))

        logger.info(
            "REFRAME_CONTROLLED_PROFILE model=%s controlnet=%s device=%s dtype=%s "
            "res=%sx%s steps=%s denoise=%.3f guidance=%.2f structure=%.2f seed=%s mask=%s",
            self._model_id,
            self._controlnet_model_id,
            self._device,
            self._dtype_name,
            inf_w,
            inf_h,
            steps,
            denoise_strength,
            guidance,
            structure_strength,
            seed,
            has_mask,
        )
        logger.info("REFRAME_CONTROLLED_PROMPT_POS %s", prompt)
        logger.info("REFRAME_CONTROLLED_PROMPT_NEG %s", negative)
        logger.info("REFRAME_CONTROLLED_EDIT_BLOCK\n%s", build_edit_requirements_block(design_brief))

        progress("redesigning", 0, steps)
        started = time.perf_counter()
        image: Image.Image | None = None

        try:

            def _step_cb(pipe, step_index, timestep, callback_kwargs):
                progress("redesigning", int(step_index) + 1, steps)
                if step_index == 0:
                    _mem_log("during_latent_preparation", marks)
                elif step_index == max(0, steps // 2):
                    _mem_log("during_inference", marks)
                return callback_kwargs

            with torch.inference_mode():
                result = self._pipe(
                    prompt=prompt,
                    negative_prompt=negative,
                    image=src_resized,
                    mask_image=edit_mask,
                    control_image=control_image,
                    height=inf_h,
                    width=inf_w,
                    strength=denoise_strength,
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                    controlnet_conditioning_scale=structure_strength,
                    generator=generator,
                    callback_on_step_end=_step_cb,
                )
            _mem_log("during_decoding", marks)
            image = result.images[0].convert("RGB")
            del result
        except Exception as exc:
            _cleanup()
            message = str(exc).lower()
            logger.exception("Controlled generation failed: %s", exc)
            if any(token in message for token in ("out of memory", "not enough memory", "memoryerror", "paging file")):
                raise RuntimeError(USER_RESOURCE_ERROR) from exc
            raise RuntimeError(USER_GENERIC_ERROR) from exc
        finally:
            src_resized.close()
            edit_mask.close()
            control_image.close()

        progress("refining")
        display_max = profile.display_max_side or 1200
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
            "controlnet_model": self._controlnet_model_id,
            "device": self._device,
            "dtype": self._dtype_name,
            "profile": profile.name,
            "input_resolution": [inf_w, inf_h],
            "output_resolution": list(final.size),
            "steps": steps,
            "strength": denoise_strength,
            "guidance": guidance,
            "structure_strength": structure_strength,
            "seed": seed,
            "elapsed_seconds": elapsed,
            "peak_rss_gb": peak,
            "mode": "precision" if has_mask else "automatic",
        }
        logger.info(
            "REFRAME_CONTROLLED done model=%s controlnet=%s elapsed=%.1fs peak_rss_gb=%s seed=%s",
            self._model_id,
            self._controlnet_model_id,
            elapsed,
            f"{peak:.3f}" if peak is not None else "n/a",
            seed,
        )

        return GenerationResult(
            image=final,
            provider="local-controlled",
            model=self._model_id,
            device=self._device,
            steps=steps,
            strength=denoise_strength,
            resolution=(inf_w, inf_h),
            elapsed_seconds=elapsed,
            seed=int(seed),
            engine=(
                f"local-controlled:{self._model_id}|controlnet={self._controlnet_model_id}"
                f"|device={self._device}|strength={denoise_strength:.2f}"
                f"|structure={structure_strength:.2f}|steps={steps}"
                f"|res={inf_w}x{inf_h}|seed={seed}|t={elapsed:.1f}s"
            ),
        )

    def _ensure_pipeline(self) -> None:
        with self._load_lock:
            if self._pipe is not None:
                return
            try:
                import torch
                from diffusers import ControlNetModel, StableDiffusionControlNetInpaintPipeline
            except ImportError as exc:
                raise RuntimeError(USER_GENERIC_ERROR) from exc

            model_id = (settings.local_inpainting_model_id or "").strip()
            controlnet_id = (settings.local_controlnet_canny_model_id or "").strip()
            if not model_id or not controlnet_id:
                raise RuntimeError(USER_GENERIC_ERROR)

            # Keep only one heavy pipeline resident on CPU when possible.
            try:
                from app.services.providers.local_diffusion import reset_local_provider
                from app.services.providers.local_inpainting import reset_inpainting_provider

                reset_local_provider()
                reset_inpainting_provider()
            except Exception:
                logger.debug("Could not reset alternate providers before loading controlled stack", exc_info=True)

            device = "cpu"
            dtype = torch.float32
            dtype_name = "float32"
            if torch.cuda.is_available():
                device = "cuda"
                dtype = torch.float16
                dtype_name = "float16"

            logger.info("Loading controlled pipeline base=%s controlnet=%s on %s ...", model_id, controlnet_id, device)
            try:
                controlnet = ControlNetModel.from_pretrained(
                    controlnet_id,
                    torch_dtype=dtype,
                    low_cpu_mem_usage=True,
                )
                pipe = StableDiffusionControlNetInpaintPipeline.from_pretrained(
                    model_id,
                    controlnet=controlnet,
                    torch_dtype=dtype,
                    safety_checker=None,
                    requires_safety_checker=False,
                    low_cpu_mem_usage=True,
                )
            except Exception as exc:
                logger.exception("Controlled model load failed for %s + %s", model_id, controlnet_id)
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
                        logger.debug("VAE tiling unavailable for controlled provider", exc_info=True)
            pipe.set_progress_bar_config(disable=True)

            self._pipe = pipe
            self._device = device
            self._dtype_name = dtype_name
            self._model_id = model_id
            self._controlnet_model_id = controlnet_id
            _cleanup()


_controlled_lock = threading.Lock()
_shared_controlled: LocalControlledGenerationProvider | None = None


def get_controlled_provider() -> LocalControlledGenerationProvider:
    global _shared_controlled
    with _controlled_lock:
        if _shared_controlled is None:
            _shared_controlled = LocalControlledGenerationProvider()
        return _shared_controlled


def reset_controlled_provider() -> None:
    global _shared_controlled
    with _controlled_lock:
        _shared_controlled = None
        gc.collect()
