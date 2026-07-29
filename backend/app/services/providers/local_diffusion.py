"""Local free image-to-image redesign using Diffusers (CPU-optimized, no paid API)."""

from __future__ import annotations

import gc
import logging
import threading
import time
from typing import Callable

from PIL import Image

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
from app.services.pipeline.image_preprocess import (
    prepare_for_diffusion,
    restore_from_diffusion,
    safe_postprocess,
)
from app.services.providers import GenerationResult, RoomGenerationProvider

logger = logging.getLogger(__name__)

# Design-transform defaults by brief strength label.
# Structure preservation is NOT solved by these values alone.
DESIGN_STRENGTH_BY_LABEL = {
    "subtle": 0.42,
    "balanced": 0.52,
    "strong": 0.58,
}

ProgressCallback = Callable[[str, int | None, int | None], None]


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


def _resolve_scheduler(pipe, name: str):
    try:
        from diffusers import DDIMScheduler, EulerDiscreteScheduler, PNDMScheduler
    except Exception:
        return pipe

    key = (name or "ddim").strip().lower()
    try:
        if key == "ddim":
            pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
        elif key == "euler":
            pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
        elif key == "pndm":
            pipe.scheduler = PNDMScheduler.from_config(pipe.scheduler.config)
    except Exception:
        logger.debug("Scheduler %s unavailable; keeping pipeline default", key, exc_info=True)
    return pipe


class LocalDiffusionProvider(RoomGenerationProvider):
    """Singleton-friendly provider: one pipeline instance, lazy-loaded."""

    name = "local"
    supports_masks: bool = False
    supports_structure: bool = False

    def __init__(self) -> None:
        self._pipe = None
        self._device = "cpu"
        self._dtype_name = "float32"
        self._model_id = ""
        self._scheduler_name = "default"
        self._load_lock = threading.Lock()
        self._last_memory: dict[str, float | None] = {}
        self._last_run_config: dict = {}

    @property
    def memory_profile(self) -> dict[str, float | None]:
        return dict(self._last_memory)

    @property
    def last_run_config(self) -> dict:
        return dict(self._last_run_config)

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
        constraints=None,
        segmentation=None,
        structure=None,
        seed: int | None = None,
        strength_override: float | None = None,
        steps_override: int | None = None,
    ) -> GenerationResult:
        marks: dict[str, float | None] = {}
        _mem_log("before_model_loading", marks)

        # Conditioning accepted for architecture; Tiny-SD cannot consume it yet.
        _ = constraints
        _ = segmentation
        _ = structure

        profile = profile or choose_profile()
        strength_label = (
            transformation_strength or design_brief.transformation_strength or "balanced"
        ).lower()
        img2img_strength = (
            float(strength_override)
            if strength_override is not None
            else DESIGN_STRENGTH_BY_LABEL.get(strength_label, profile.design_strength)
        )
        # Cap extreme strengths that melt geometry on tiny models.
        img2img_strength = max(0.30, min(0.72, img2img_strength))

        def progress(stage: str, step: int | None = None, total: int | None = None) -> None:
            generation_gate.set_stage(stage, step=step, total_steps=total)  # type: ignore[arg-type]
            if on_progress:
                on_progress(stage, step, total)

        progress("analyzing")
        self._ensure_pipeline(profile)
        _mem_log("after_model_loading", marks)

        progress("preparing")
        src = source_image.convert("RGB")
        prepared = prepare_for_diffusion(src, profile.max_side)
        width, height = prepared.target_size
        _mem_log("after_source_image", marks)

        prompt = build_local_clip_prompt(design_brief)
        negative = build_local_negative_prompt(design_brief)
        steps = int(steps_override if steps_override is not None else profile.steps)
        guidance = float(profile.guidance)

        import torch

        if seed is None:
            seed = int(torch.randint(0, 2**31 - 1, (1,)).item())
        generator = torch.Generator(device="cpu").manual_seed(int(seed))

        logger.info(
            "REFRAME_GEN_PROFILE model=%s device=%s dtype=%s scheduler=%s profile=%s "
            "input_res=%sx%s output_display_max=%s steps=%s strength=%.3f guidance=%.2f seed=%s",
            self._model_id,
            self._device,
            self._dtype_name,
            self._scheduler_name,
            profile.name,
            width,
            height,
            profile.display_max_side,
            steps,
            img2img_strength,
            guidance,
            seed,
        )
        logger.info("REFRAME_GEN_PROMPT_POSITIVE %s", prompt)
        logger.info("REFRAME_GEN_PROMPT_NEGATIVE %s", negative)
        logger.info("REFRAME_GEN_EDIT_BLOCK\n%s", build_edit_requirements_block(design_brief))

        progress("redesigning", 0, steps)
        started = time.perf_counter()
        image: Image.Image | None = None

        try:

            def _step_callback(pipe, step_index, timestep, callback_kwargs):
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
                    image=prepared.image,
                    strength=img2img_strength,
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                    generator=generator,
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
            prepared.image.close()

        progress("refining")
        restored = restore_from_diffusion(image, prepared, display_max_side=profile.display_max_side)
        if image is not None:
            image.close()
        final = safe_postprocess(restored, mild_sharpen=profile.mild_sharpen)
        restored.close()
        _cleanup_ephemeral()
        _mem_log("after_generation", marks)
        self._last_memory = marks

        elapsed = time.perf_counter() - started
        peak = max((v for v in marks.values() if v is not None), default=None)
        self._last_run_config = {
            "model": self._model_id,
            "device": self._device,
            "dtype": self._dtype_name,
            "scheduler": self._scheduler_name,
            "profile": profile.name,
            "input_resolution": [width, height],
            "output_resolution": list(final.size),
            "steps": steps,
            "strength": img2img_strength,
            "guidance": guidance,
            "seed": seed,
            "elapsed_seconds": elapsed,
            "peak_rss_gb": peak,
            "positive_prompt": prompt,
            "negative_prompt": negative,
        }
        logger.info(
            "REFRAME_GEN done model=%s profile=%s elapsed=%.1fs peak_rss_gb=%s seed=%s",
            self._model_id,
            profile.name,
            elapsed,
            f"{peak:.3f}" if peak is not None else "n/a",
            seed,
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
            seed=int(seed),
            engine=(
                f"local:{self._model_id}|profile={profile.name}|device={self._device}"
                f"|sched={self._scheduler_name}|strength={img2img_strength:.2f}"
                f"|steps={steps}|res={width}x{height}|seed={seed}|t={elapsed:.1f}s"
            ),
        )

    def _ensure_pipeline(self, profile: LocalAiProfile) -> None:
        with self._load_lock:
            if self._pipe is not None:
                # Re-apply scheduler if profile asks for a different one.
                if profile.scheduler != self._scheduler_name:
                    self._pipe = _resolve_scheduler(self._pipe, profile.scheduler)
                    self._scheduler_name = profile.scheduler
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
            dtype_name = "float32"
            if torch.cuda.is_available():
                device = "cuda"
                dtype = torch.float16
                dtype_name = "float16"

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

            pipe = pipe.to(device)
            pipe = _resolve_scheduler(pipe, profile.scheduler)
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
            self._dtype_name = dtype_name
            self._model_id = model_id
            self._scheduler_name = profile.scheduler
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


def reset_local_provider() -> None:
    """Dev helper — drop cached pipeline (e.g. after model/settings change)."""
    global _shared_provider
    with _provider_lock:
        _shared_provider = None
        gc.collect()
