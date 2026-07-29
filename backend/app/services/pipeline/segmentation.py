"""Segmentation interface — user masks ready for future models.

Development goal: no heavy vision model downloads are required.
User-painted region masks (KEEP/CHANGE/REMOVE) can be loaded from disk,
combined into protected/editable unions, and passed to future editors.
"""

from __future__ import annotations

import logging
from PIL import Image
from PIL import ImageChops
from uuid import uuid4

from app.core.config import settings
from app.services.media import TEMP_UPLOADS_ROOT, UPLOADS_ROOT
from app.services.pipeline.types import ObjectMask, RoomAnalysis, SegmentationResult

logger = logging.getLogger(__name__)


def prepare_segmentation(
    source_image: Image.Image,
    room_analysis: RoomAnalysis,
    *,
    enabled: bool = False,
    user_region_masks: list[ObjectMask] | None = None,
) -> SegmentationResult:
    """Return a segmentation result.

    - If `user_region_masks` is provided: treat those masks as available
      segmentation artifacts aligned to `source_image.size`.
    - If `enabled` is False: return placeholders (no segmentation model runs).
    """
    user_region_masks = list(user_region_masks or [])

    def _load_mask_alpha(mask_path: str) -> Image.Image:
        # `mask_path` is stored as a relative path under UPLOADS_ROOT.
        absolute_path = UPLOADS_ROOT / mask_path
        with Image.open(absolute_path).convert("RGBA") as m:
            alpha = m.split()[-1]
            if alpha.size != source_image.size:
                # Nearest neighbor keeps region edges crisp for masks.
                alpha = alpha.resize(source_image.size, resample=Image.Resampling.NEAREST)
            return alpha

    if user_region_masks:
        def _mask_stats_from_alpha(alpha: Image.Image) -> dict[str, float]:
            # alpha is expected to be 1-channel L (0..255).
            w, h = alpha.size
            total = max(1, w * h)
            hist = alpha.histogram()
            painted = total - hist[0]  # pixels with alpha > 0
            painted_percentage = (painted / total) * 100.0
            return {
                "w": float(w),
                "h": float(h),
                "painted_pixels": float(painted),
                "total_pixels": float(total),
                "painted_percentage": painted_percentage,
            }

        def _validate_single_mask(mask: ObjectMask, alpha: Image.Image) -> None:
            w, h = alpha.size
            if w <= 0 or h <= 0:
                raise RuntimeError("Region mask has invalid dimensions.")
            stats = _mask_stats_from_alpha(alpha)
            painted_percentage = stats["painted_percentage"]
            action = (mask.action or "CHANGE").strip().upper()

            # Detect likely export bugs: all-black or all-white.
            if painted_percentage <= 0.0001:
                raise RuntimeError(f"{action} mask is entirely black (0 painted pixels).")
            if painted_percentage >= 99.9999:
                raise RuntimeError(f"{action} mask is entirely white (painted all pixels).")

            # Aspect ratio alignment check (must match the source photo).
            src_w, src_h = source_image.size
            mask_ar = w / h
            src_ar = src_w / src_h
            if abs(mask_ar - src_ar) / max(1e-6, src_ar) > 0.02:
                raise RuntimeError("Region mask aspect ratio does not match the source image.")

        keep_alpha: Image.Image | None = None
        edit_alpha: Image.Image | None = None

        resolved_masks: list[ObjectMask] = []

        # Load + validate each user mask (dev mode only enforces strict checks).
        for mask in user_region_masks:
            if not mask.mask_path:
                resolved_masks.append(mask)
                continue

            action = (mask.action or "CHANGE").strip().upper()
            if action not in {"KEEP", "CHANGE", "REMOVE"}:
                action = "CHANGE"

            try:
                absolute_path = UPLOADS_ROOT / mask.mask_path
                with Image.open(absolute_path).convert("RGBA") as m:
                    alpha = m.split()[-1]

                if settings.debug_mask_pipeline:
                    _validate_single_mask(mask, alpha)

                # Stats were validated; keep loading result for union building.

                # Resize alpha into the pipeline working space.
                if alpha.size != source_image.size:
                    alpha = alpha.resize(source_image.size, resample=Image.Resampling.NEAREST)

                resolved_masks.append(
                    ObjectMask(
                        object_id=mask.object_id,
                        action=action,
                        label=mask.label,
                        mask_path=mask.mask_path,
                        available=True,
                    )
                )

                if action == "KEEP":
                    keep_alpha = alpha if keep_alpha is None else ImageChops.lighter(keep_alpha, alpha)
                elif action in {"CHANGE", "REMOVE"}:
                    edit_alpha = alpha if edit_alpha is None else ImageChops.lighter(edit_alpha, alpha)
            except Exception:
                # Non-dev mode: mark unavailable and continue.
                if settings.debug_mask_pipeline:
                    raise
                resolved_masks.append(
                    ObjectMask(
                        object_id=mask.object_id,
                        action=action,
                        label=mask.label,
                        mask_path=mask.mask_path,
                        available=False,
                    )
                )

        # If masks were provided but none were usable, stop (dev mode) or proceed (non-dev).
        keep_alpha = keep_alpha
        edit_alpha = edit_alpha
        if settings.debug_mask_pipeline and edit_alpha is None:
            raise RuntimeError("No usable CHANGE/REMOVE masks were loaded for editing.")

        seg_tmp_dir = TEMP_UPLOADS_ROOT / "segmentation"
        seg_tmp_dir.mkdir(parents=True, exist_ok=True)
        run_id = uuid4().hex

        keep_mask_path = None
        edit_mask_path = None

        keep_mask_dimensions = None
        edit_mask_dimensions = None
        keep_painted_pixel_percentage = None
        edit_painted_pixel_percentage = None
        keep_edit_overlap_pixel_percentage = None
        debug_preview_path = None

        # Compute binary KEEP/EDIT masks and enforce KEEP priority.
        # Canonical internal representation:
        # - KEEP pixels = protected (never part of EDIT)
        # - EDIT pixels = editable (CHANGE + REMOVE, minus KEEP)
        keep_bin: Image.Image | None = None
        final_edit_bin: Image.Image | None = None
        if keep_alpha is not None:
            keep_mask_dimensions = source_image.size
            keep_bin = keep_alpha.point(lambda p: 255 if p > 0 else 0)
            keep_hist = keep_bin.histogram()
            total = max(1, keep_bin.size[0] * keep_bin.size[1])
            keep_painted = total - keep_hist[0]
            keep_painted_pixel_percentage = (keep_painted / total) * 100.0

            keep_rgba = Image.new("RGBA", keep_bin.size, (255, 255, 255, 0))
            keep_rgba.putalpha(keep_bin)
            keep_file = seg_tmp_dir / f"{run_id}_keep.png"
            keep_rgba.save(keep_file, format="PNG")
            keep_mask_path = str(keep_file.relative_to(UPLOADS_ROOT)).replace("\\", "/")

        if edit_alpha is not None:
            edit_mask_dimensions = source_image.size
            edit_bin = edit_alpha.point(lambda p: 255 if p > 0 else 0)

            if keep_bin is not None:
                # Overlap is computed BEFORE subtracting KEEP.
                overlap_bin = ImageChops.multiply(keep_bin, edit_bin)
                overlap_hist = overlap_bin.histogram()
                total = max(1, overlap_bin.size[0] * overlap_bin.size[1])
                overlap_painted = total - overlap_hist[0]
                keep_edit_overlap_pixel_percentage = (overlap_painted / total) * 100.0

                keep_inv = keep_bin.point(lambda p: 0 if p > 0 else 255)
                final_edit_bin = ImageChops.multiply(edit_bin, keep_inv)
            else:
                final_edit_bin = edit_bin
                keep_edit_overlap_pixel_percentage = 0.0

            edit_hist = final_edit_bin.histogram()
            total = max(1, final_edit_bin.size[0] * final_edit_bin.size[1])
            edit_painted = total - edit_hist[0]
            edit_painted_pixel_percentage = (edit_painted / total) * 100.0

            if settings.debug_mask_pipeline and edit_painted <= 0:
                # Step 2 hard stop: do not proceed if masked generation would be a no-op.
                raise RuntimeError("EDIT mask has 0 painted pixels after applying KEEP priority.")

            edit_rgba = Image.new("RGBA", final_edit_bin.size, (255, 255, 255, 0))
            edit_rgba.putalpha(final_edit_bin)
            edit_file = seg_tmp_dir / f"{run_id}_edit.png"
            edit_rgba.save(edit_file, format="PNG")
            edit_mask_path = str(edit_file.relative_to(UPLOADS_ROOT)).replace("\\", "/")
        else:
            edit_mask_dimensions = None
            final_edit_bin = None

        if settings.debug_mask_visual_preview and (keep_bin is not None or final_edit_bin is not None):
            try:
                debug_dir = TEMP_UPLOADS_ROOT / "debug"
                debug_dir.mkdir(parents=True, exist_ok=True)

                preview = source_image.convert("RGB").convert("RGBA")
                if keep_bin is not None:
                    keep_layer = Image.new("RGBA", preview.size, (34, 197, 94, 0))
                    keep_layer.putalpha(keep_bin.point(lambda p: int(p * 0.35)))
                    preview.alpha_composite(keep_layer)
                if final_edit_bin is not None:
                    edit_layer = Image.new("RGBA", preview.size, (239, 68, 68, 0))
                    edit_layer.putalpha(final_edit_bin.point(lambda p: int(p * 0.35)))
                    preview.alpha_composite(edit_layer)

                preview_file = debug_dir / f"region_overlay_{run_id}.png"
                preview.save(preview_file, format="PNG")
                debug_preview_path = str(preview_file.relative_to(UPLOADS_ROOT)).replace("\\", "/")
            except Exception:
                debug_preview_path = None

        return SegmentationResult(
            masks=resolved_masks,
            provider="user",
            available=True,
            reason="User region masks provided (no segmentation model downloaded).",
            keep_mask_path=keep_mask_path,
            edit_mask_path=edit_mask_path,
            keep_mask_dimensions=keep_mask_dimensions,
            edit_mask_dimensions=edit_mask_dimensions,
            keep_painted_pixel_percentage=keep_painted_pixel_percentage,
            edit_painted_pixel_percentage=edit_painted_pixel_percentage,
            keep_edit_overlap_pixel_percentage=keep_edit_overlap_pixel_percentage,
            debug_preview_path=debug_preview_path,
        )

    if not enabled:
        return SegmentationResult(
            masks=[
                ObjectMask(
                    object_id=obj.id,
                    label=obj.type,
                    bounding_box=obj.bounding_box,
                    confidence=obj.confidence,
                    available=False,
                )
                for obj in room_analysis.objects
            ],
            provider=None,
            available=False,
            reason="Segmentation disabled — no large vision model downloaded.",
        )

    return SegmentationResult(
        available=False,
        reason="Segmentation backend not implemented yet.",
    )
