"""Local free image-to-image redesign using Diffusers (CPU-optimized, no paid API)."""

from __future__ import annotations

import gc
import logging
import threading
import time
from typing import Callable

from PIL import Image, ImageOps

from app.core.config import settings
from app.services.design_brief import (
    DesignBrief,
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
from app.services.providers import GenerationResult, RoomGenerationProvider

logger = logging.getLogger(__name__)

STRENGTH_MAP = {
    "subtle": 0.35,
    "balanced": 0.48,
    "strong": 0.58,
}

# Tiny / low-capacity checkpoints collapse into noise above ~0.6 strength.
STRENGTH_CAP_BY_PROFILE = {
    "low_memory": 0.52,
    "balanced": 0.58,
    "high": 0.65,
}

ProgressCallback = Callable[[str, int | None, int | None], None]


def _round8(value: int) -> int:
    return max(64, int(round(value / 8) * 8))


def inference_size(width: int, height: int, max_side: int) -> tuple[int, int]:
    """Aspect-preserving resize target; dimensions divisible by 8 for SD."""
    scale = max_side / max(width, height)
    return _round8(int(width * scale)), _round8(int(height * scale))


def display_size(width: int, height: int, max_side: int) -> tuple[int, int]:
    if max(width, height) <= max_side:
        return width, height
    scale = max_side / max(width, height)
    return max(1, int(width * scale)), max(1, int(height * scale))


def _mem_log(label: str, marks: dict[str, float | None]) -> None:
    rss = process_rss_gb()
    avail = system_available_gb()
    marks[label] = rss
    logger.info(
        "REFRAME_MEM stage=%s process_rss_gb=%s system_available_gb=%s",
        label,
        f"{rss:.3f}" if rss is not None else "n/a",
        f"{avail:.3f}" if avail is not None else "n/a",
    )


def _cleanup_ephemeral() -> None:
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


class LocalDiffusionProvider(RoomGenerationProvider):
    """Singleton-friendly provider: one pipeline instance, lazy-loaded."""

    name = "local"

    def __init__(self) -> None:
        self._pipe = None
        self._device = "cpu"
        self._model_id = ""
        self._load_lock = threading.Lock()
        self._last_memory: dict[str, float | None] = {}

    @property
    def memory_profile(self) -> dict[str, float | None]:
        return dict(self._last_memory)

    def ensure_loaded(self, profile: LocalAiProfile | None = None) -> None:
        self._ensure_pipeline(profile or active_profile())

    def generate_room(
        self,
        source_image: Image.Image,
        design_brief: DesignBrief,
        transformation_strength: str | None = None,
        *,
        on_progress: ProgressCallback | None = None,
        profile: LocalAiProfile | None = None,
    ) -> GenerationResult:
        marks: dict[str, float | None] = {}
        _mem_log("before_model_loading", marks)

        profile = profile or choose_profile()
        strength_label = (
            transformation_strength or design_brief.transformation_strength or "balanced"
        ).lower()
        img2img_strength = STRENGTH_MAP.get(strength_label, STRENGTH_MAP["balanced"])
        img2img_strength = min(
            img2img_strength,
            STRENGTH_CAP_BY_PROFILE.get(profile.name, 0.58),
        )

        def progress(stage: str, step: int | None = None, total: int | None = None) -> None:
            generation_gate.set_stage(stage, step=step, total_steps=total)  # type: ignore[arg-type]
            if on_progress:
                on_progress(stage, step, total)

        progress("analyzing")
        self._ensure_pipeline(profile)
        _mem_log("after_model_loading", marks)

        progress("preparing")
        src = source_image.convert("RGB")
        width, height = inference_size(src.width, src.height, profile.max_side)
        prepared = ImageOps.fit(src, (width, height), method=Image.Resampling.LANCZOS)
        _mem_log("after_source_image", marks)

        prompt = build_local_clip_prompt(design_brief)
        negative = build_local_negative_prompt(design_brief)
        steps = int(profile.steps)
        guidance = float(profile.guidance)

        logger.info(
            "REFRAME_GEN provider=LOCAL model=%s device=%s profile=%s res=%sx%s strength=%.2f steps=%s",
            self._model_id,
            self._device,
            profile.name,
            width,
            height,
            img2img_strength,
            steps,
        )

        progress("redesigning", 0, steps)
        started = time.perf_counter()
        image: Image.Image | None = None

        try:
            import torch

            def _step_callback(pipe, step_index, timestep, callback_kwargs):
                # Diffusers passes 0-based step index during denoising.
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
                    image=prepared,
                    strength=img2img_strength,
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                    callback_on_step_end=_step_callback,
                )
            _mem_log("during_decoding", marks)
            image = result.images[0].convert("RGB")
            del result
        except Exception as exc:
            _cleanup_ephemeral()
            message = str(exc).lower()
            logger.exception("Local generation failed: %s", exc)
            if any(
                token in message
                for token in ("out of memory", "not enough memory", "memoryerror", "paging file")
            ):
                raise RuntimeError(USER_RESOURCE_ERROR) from exc
            raise RuntimeError(USER_GENERIC_ERROR) from exc
        finally:
            prepared.close()

        progress("refining")
        target_w, target_h = display_size(src.width, src.height, profile.display_max_side)
        final = ImageOps.fit(image, (target_w, target_h), method=Image.Resampling.LANCZOS)
        if image is not None:
            image.close()
        _cleanup_ephemeral()
        _mem_log("after_generation", marks)
        self._last_memory = marks

        elapsed = time.perf_counter() - started
        peak = max((v for v in marks.values() if v is not None), default=None)
        logger.info(
            "REFRAME_GEN done model=%s profile=%s elapsed=%.1fs peak_rss_gb=%s marks=%s",
            self._model_id,
            profile.name,
            elapsed,
            f"{peak:.3f}" if peak is not None else "n/a",
            {k: (round(v, 3) if v is not None else None) for k, v in marks.items()},
        )

        return GenerationResult(
            image=final,
            provider="local",
            model=self._model_id,
            device=self._device,
            steps=steps,
            strength=img2img_strength,
            resolution=(width, height),
            elapsed_seconds=elapsed,
            engine=(
                f"local:{self._model_id}|profile={profile.name}|device={self._device}"
                f"|strength={img2img_strength:.2f}|steps={steps}|res={width}x{height}|t={elapsed:.1f}s"
            ),
        )

    def _ensure_pipeline(self, profile: LocalAiProfile) -> None:
        with self._load_lock:
            if self._pipe is not None:
                return
            try:
                import torch
                from diffusers import StableDiffusionImg2ImgPipeline
            except ImportError as exc:
                raise RuntimeError(USER_GENERIC_ERROR) from exc

            model_id = (settings.local_model_id or settings.local_diffusion_model or "").strip()
            if not model_id:
                raise RuntimeError(USER_GENERIC_ERROR)

            device = "cpu"
            dtype = torch.float32
            if torch.cuda.is_available():
                device = "cuda"
                dtype = torch.float16

            logger.info(
                "Loading local diffusion model %s on %s (profile=%s) ...",
                model_id,
                device,
                profile.name,
            )
            try:
                pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
                    model_id,
                    torch_dtype=dtype,
                    safety_checker=None,
                    requires_safety_checker=False,
                    low_cpu_mem_usage=True,
                )
            except Exception as exc:
                logger.exception("Model load failed for %s", model_id)
                raise RuntimeError(USER_GENERIC_ERROR) from exc

            # CPU path: keep weights on CPU; never enable CUDA-only offload helpers.
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
                        logger.debug("VAE tiling unavailable", exc_info=True)

            pipe.set_progress_bar_config(disable=True)
            self._pipe = pipe
            self._device = device
            self._model_id = model_id
            _cleanup_ephemeral()


_provider_lock = threading.Lock()
_shared_provider: LocalDiffusionProvider | None = None


def get_local_provider() -> LocalDiffusionProvider:
    """Process-wide singleton — never construct a new pipeline per request."""
    global _shared_provider
    with _provider_lock:
        if _shared_provider is None:
            _shared_provider = LocalDiffusionProvider()
        return _shared_provider
