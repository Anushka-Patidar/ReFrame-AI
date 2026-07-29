"""ReFrame room redesign — local image-to-image only (no paid cloud APIs)."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from PIL import Image, ImageFilter, ImageOps, ImageStat

from app.core.config import settings
from app.db.database import get_database
from app.models.collections import REGION_CONSTRAINTS
from app.services.generation_runtime import (
    MAX_GENERATION_SECONDS,
    USER_BUSY_ERROR,
    USER_GENERIC_ERROR,
    USER_RESOURCE_ERROR,
    USER_TIMEOUT_ERROR,
    generation_gate,
)
from app.services.hardware import detect_hardware, hardware_dict
from app.services.media import GENERATED_UPLOADS_ROOT, ROOM_UPLOADS_ROOT
from app.services.pipeline.types import ObjectMask

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np

    _HAS_CV2 = True
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    _HAS_CV2 = False


class RoomImageMissingError(ValueError):
    """Raised when generation is attempted without a usable room photo."""


class InsufficientTransformError(RuntimeError):
    """Raised when local generation did not produce a clear redesign."""


class GenerationBusyError(RuntimeError):
    """Raised when another local generation job is already running."""


def _resolve_room_image_path(original_image_url: str | None) -> Path | None:
    if not original_image_url:
        return None
    parsed = urlparse(original_image_url)
    path = parsed.path or original_image_url
    match = re.search(r"/media/rooms/([^/?#]+)$", path)
    if match:
        candidate = ROOM_UPLOADS_ROOT / match.group(1)
        if candidate.exists():
            return candidate
    as_path = Path(original_image_url)
    return as_path if as_path.exists() else None


def _download_image(url: str) -> Image.Image | None:
    try:
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(url)
            if response.status_code >= 400:
                return None
            return Image.open(__import__("io").BytesIO(response.content)).convert("RGB")
    except Exception:
        logger.exception("Failed to download image from %s", url)
        return None


def load_room_image(original_image_url: str | None, *, require: bool = True) -> Image.Image:
    path = _resolve_room_image_path(original_image_url)
    if path is not None:
        image = Image.open(path).convert("RGB")
    elif original_image_url and original_image_url.startswith(("http://", "https://")):
        image = _download_image(original_image_url)
        if image is None:
            raise RoomImageMissingError(
                "Could not load the room photo. Re-upload the image and try again."
            )
    else:
        raise RoomImageMissingError(
            "Upload a clear room photo before generating a design."
        )

    # Keep a modest working copy before inference downscale — saves RAM.
    max_width = 1200
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, int(image.height * ratio)), Image.Resampling.LANCZOS)
    return image


async def _load_user_region_masks(room: dict) -> list[ObjectMask]:
    """Load user-painted region constraints and convert them into pipeline masks."""
    try:
        room_id = room.get("_id")
        user_id = room.get("user_id")
        if room_id is None or user_id is None:
            return []

        cursor = get_database()[REGION_CONSTRAINTS].find({"room_id": room_id, "user_id": user_id})
        docs = await cursor.to_list(length=500)
        result: list[ObjectMask] = []
        for doc in docs:
            mask_path = doc.get("mask_path")
            if not mask_path:
                continue
            action = str(doc.get("action") or "CHANGE").strip().upper()
            label = str(doc.get("label") or "")
            result.append(
                ObjectMask(
                    object_id=str(doc.get("_id")),
                    action=action,
                    label=label,
                    mask_path=str(mask_path),
                    available=True,
                )
            )
        return result
    except Exception:
        logger.exception("Failed to load user region masks")
        return []


def _edge_map(image: Image.Image, size: tuple[int, int] = (96, 96)) -> Image.Image:
    gray = image.resize(size, Image.Resampling.BILINEAR).convert("L")
    return gray.filter(ImageFilter.FIND_EDGES)


def structure_similarity(original: Image.Image, candidate: Image.Image) -> float:
    left = list(_edge_map(original).tobytes())
    right = list(_edge_map(candidate).tobytes())
    if not left:
        return 0.0
    diff = sum(abs(a - b) for a, b in zip(left, right, strict=False)) / (255.0 * len(left))
    return max(0.0, 1.0 - diff)


def mean_abs_delta(original: Image.Image, candidate: Image.Image) -> float:
    left = list(original.resize((96, 96), Image.Resampling.BILINEAR).tobytes())
    right = list(candidate.resize((96, 96), Image.Resampling.BILINEAR).tobytes())
    return sum(abs(a - b) for a, b in zip(left, right, strict=False)) / len(left)


def images_byte_identical(original: Image.Image, candidate: Image.Image) -> bool:
    a = original.convert("RGB")
    b = ImageOps.fit(candidate, a.size, method=Image.Resampling.LANCZOS).convert("RGB")
    return a.tobytes() == b.tobytes()


def min_delta_for_strength(strength: str) -> float:
    if strength == "strong":
        return 14.0
    if strength == "subtle":
        return 5.0
    return 9.0


def architecture_ok(original: Image.Image, candidate: Image.Image, strength: str) -> bool:
    if candidate.size != original.size:
        candidate = ImageOps.fit(candidate, original.size, method=Image.Resampling.LANCZOS)
    if ImageStat.Stat(candidate.convert("L")).stddev[0] < 12:
        return False
    minimum = 0.38 if strength == "strong" else 0.48 if strength == "balanced" else 0.58
    return structure_similarity(original, candidate) >= minimum


def looks_photoreal_enough(image: Image.Image) -> bool:
    """Reject extreme abstract collapses (not a substitute for human quality review)."""
    gray = image.convert("L").resize((128, 128), Image.Resampling.BILINEAR)
    pixels = list(gray.getdata())
    if not pixels:
        return False
    mean = sum(pixels) / len(pixels)
    variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
    edges = list(gray.filter(ImageFilter.FIND_EDGES).getdata())
    edge_mean = sum(edges) / len(edges)
    # Catches near-solid or near-noise abstract failures; tiny-SD mush can still pass.
    return variance >= 200 and edge_mean >= 5.0


def contains_human_face(image: Image.Image) -> bool:
    """Best-effort face check. Never crash generation if OpenCV is incomplete."""
    if not _HAS_CV2 or cv2 is None or np is None:
        return False
    try:
        if not hasattr(cv2, "CascadeClassifier"):
            return False
        rgb = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        if hasattr(cv2, "equalizeHist"):
            gray = cv2.equalizeHist(gray)
        cascade_path = ""
        data = getattr(cv2, "data", None)
        if data is not None:
            cascade_path = getattr(data, "haarcascades", "") + "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(cascade_path)
        if cascade is None or cascade.empty():
            return False
        min_face = max(48, min(image.size) // 10)
        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.12, minNeighbors=5, minSize=(min_face, min_face)
        )
        return len(faces) > 0
    except Exception:
        logger.debug("Face detection skipped due to OpenCV error", exc_info=True)
        return False


def _bytes_from_image(image: Image.Image) -> bytes:
    import io

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True)
    return buffer.getvalue()


def get_ai_capabilities() -> dict:
    provider = (settings.image_provider or "local").strip().lower()
    local_ready = provider == "local"
    hw = hardware_dict()
    return {
        "photoreal_image_edit": local_ready,
        "claude_chat": bool(settings.anthropic_api_key),
        "openai_chat": False,
        "local_style_grade": False,
        "openai_image_model": "",
        "image_provider": "local",
        "pollinations_enabled": False,
        "gemini_enabled": False,
        "supports_reference_image_edit": local_ready,
        "mode": "photoreal" if local_ready else "local-grade",
        "recommended_setup": "Local image-to-image redesign is enabled.",
        "local_ai_profile": hw.get("selected_profile"),
        "generation_busy": generation_gate.snapshot().busy,
    }


def get_generation_progress() -> dict:
    return generation_gate.snapshot().to_dict()


def _generate_sync(
    room: dict,
    requirements: dict | None,
    revision_note: str | None,
    memory_document: dict | None = None,
    user_region_masks: list[ObjectMask] | None = None,
    requested_profile: str | None = None,
) -> tuple[str, str, dict]:
    """Run modular pipeline and persist the accepted candidate.

    Returns (relative_path, engine_string, metadata_dict).
    """
    from app.services.pipeline.orchestrator import run_redesign_pipeline

    GENERATED_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    original = load_room_image(room.get("original_image_url"), require=True)

    try:
        run = run_redesign_pipeline(
            source_image=original,
            room=room,
            requirements=requirements,
            revision_note=revision_note,
            memory_document=memory_document,
            user_region_masks=user_region_masks,
            requested_profile=requested_profile,
        )
    except RuntimeError:
        raise

    final_image = run.image
    try:
        filename = f"{uuid4().hex}.jpg"
        relative = f"generated/{filename}"
        (GENERATED_UPLOADS_ROOT / filename).write_bytes(_bytes_from_image(final_image))

        validation = run.artifacts.validation.to_dict() if run.artifacts.validation else {}
        meta_payload = run.artifacts.metadata.to_dict() if run.artifacts.metadata else {}
        delta = next(
            (
                m.get("value")
                for m in validation.get("metrics", [])
                if m.get("name") == "mean_abs_delta"
            ),
            None,
        )
        similarity = next(
            (
                m.get("value")
                for m in validation.get("metrics", [])
                if m.get("name") == "structure_similarity"
            ),
            None,
        )

        logger.info(
            "REFRAME_GEN saved=%s provider=%s model=%s attempts=%s delta=%s structure=%s",
            relative,
            run.generation.provider,
            run.generation.model,
            meta_payload.get("attempts"),
            delta,
            similarity,
        )

        engine = (
            f"{run.generation.engine}|mode=pipeline|brief_strength={run.brief.transformation_strength}"
            f"|structure={similarity}|delta={delta}|attempts={meta_payload.get('attempts')}"
        )
        return relative, engine, meta_payload
    finally:
        try:
            final_image.close()
        except Exception:
            pass
        try:
            original.close()
        except Exception:
            pass


async def generate_design_image(
    room: dict,
    requirements: dict | None,
    revision_note: str | None = None,
    memory_document: dict | None = None,
    requested_profile: str | None = None,
) -> tuple[str, str, dict]:
    """Persist a locally redesigned room image. Never return the original as success."""
    if (settings.image_provider or "local").strip().lower() != "local":
        raise InsufficientTransformError(USER_GENERIC_ERROR)

    job_id = generation_gate.try_begin()
    if job_id is None:
        raise GenerationBusyError(USER_BUSY_ERROR)

    failed = False
    error_message: str | None = None
    try:
        user_region_masks = await _load_user_region_masks(room)
        return await asyncio.wait_for(
            asyncio.to_thread(
                _generate_sync,
                room,
                requirements,
                revision_note,
                memory_document,
                user_region_masks,
                requested_profile,
            ),
            timeout=MAX_GENERATION_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        failed = True
        error_message = USER_TIMEOUT_ERROR
        generation_gate.force_reset(error=USER_TIMEOUT_ERROR)
        logger.error("Generation timed out after %ss", MAX_GENERATION_SECONDS)
        raise InsufficientTransformError(USER_TIMEOUT_ERROR) from exc
    except InsufficientTransformError as exc:
        failed = True
        error_message = str(exc) or USER_GENERIC_ERROR
        raise
    except RuntimeError as exc:
        failed = True
        message = str(exc)
        if message in {USER_RESOURCE_ERROR, USER_GENERIC_ERROR, USER_BUSY_ERROR, USER_TIMEOUT_ERROR}:
            error_message = message
            raise InsufficientTransformError(message) from exc
        logger.exception("Unexpected generation failure")
        error_message = USER_GENERIC_ERROR
        raise InsufficientTransformError(USER_GENERIC_ERROR) from exc
    except Exception as exc:
        failed = True
        logger.exception("Unexpected generation failure")
        error_message = USER_GENERIC_ERROR
        raise InsufficientTransformError(USER_GENERIC_ERROR) from exc
    finally:
        generation_gate.end(job_id, failed=failed, error=error_message)


def log_startup_hardware() -> None:
    detect_hardware()
