"""Structural conditioning for architecture-preserving generation.

Computes:
- a raw Canny edge map from the source room photo
- an architecture condition map with editable regions suppressed

This lets ControlNet preserve the room shell while avoiding re-locking
furniture that the user marked CHANGE/REMOVE.
"""

from __future__ import annotations

from PIL import Image, ImageChops, ImageFilter

from app.services.media import STRUCTURE_UPLOADS_ROOT
from app.services.media import UPLOADS_ROOT
from app.services.pipeline.types import SegmentationResult, StructuralSignals


def _load_edit_mask(segmentation: SegmentationResult | None, size: tuple[int, int]) -> Image.Image | None:
    if not segmentation or not segmentation.edit_mask_path:
        return None
    try:
        with Image.open(UPLOADS_ROOT / segmentation.edit_mask_path) as mask:
            alpha = mask.convert("RGBA").split()[-1]
        if alpha.size != size:
            alpha = alpha.resize(size, resample=Image.Resampling.NEAREST)
        binary = alpha.point(lambda p: 255 if p > 0 else 0)
        # Expand slightly so nearby furniture edges also stop conditioning.
        return binary.filter(ImageFilter.MaxFilter(size=21))
    except Exception:
        return None


def prepare_structural_signals(
    source_image: Image.Image,
    *,
    segmentation: SegmentationResult | None = None,
    compute_lightweight_edges: bool = True,
) -> StructuralSignals:
    """Prepare structural signals for later ControlNet consumption."""
    edges_available = False
    edges_path: str | None = None
    architecture_condition_path: str | None = None
    suppressed_edges_path: str | None = None
    masked_edit_suppression = False
    suppressed_pixel_percentage: float | None = None
    edges_note = "Lightweight edges not computed."

    if compute_lightweight_edges:
        try:
            # OpenCV Canny tends to preserve architectural boundaries better
            # than simple edge filters in Pillow.
            import cv2  # type: ignore
            import numpy as np  # type: ignore

            rgb = np.array(source_image.convert("RGB"))
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edges_img = Image.fromarray(edges).convert("L")

            STRUCTURE_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
            import uuid

            filename = f"canny_{uuid.uuid4().hex}.png"
            edges_file = STRUCTURE_UPLOADS_ROOT / filename
            edges_img.save(edges_file, format="PNG")

            edges_available = True
            edges_path = f"tmp/structure/{filename}".replace("\\", "/")

            conditioned = edges_img
            edit_mask = _load_edit_mask(segmentation, edges_img.size)
            if edit_mask is not None:
                masked_edit_suppression = True
                keep_inv = edit_mask.point(lambda p: 0 if p > 0 else 255)
                conditioned = ImageChops.multiply(edges_img, keep_inv)
                overlap = ImageChops.multiply(edges_img.point(lambda p: 255 if p > 0 else 0), edit_mask)
                total = max(1, overlap.size[0] * overlap.size[1])
                overlap_hist = overlap.histogram()
                suppressed = total - overlap_hist[0]
                suppressed_pixel_percentage = (suppressed / total) * 100.0
                suppressed_file = STRUCTURE_UPLOADS_ROOT / f"suppressed_{filename}"
                overlap.save(suppressed_file, format="PNG")
                suppressed_edges_path = f"tmp/structure/{suppressed_file.name}".replace("\\", "/")

            conditioned_file = STRUCTURE_UPLOADS_ROOT / f"architecture_{filename}"
            conditioned.save(conditioned_file, format="PNG")
            architecture_condition_path = f"tmp/structure/{conditioned_file.name}".replace("\\", "/")
            edges_note = "OpenCV Canny edge map prepared for ControlNet conditioning."
        except Exception:
            # Fallback: Pillow FIND_EDGES when OpenCV/numpy is unavailable.
            try:
                edges_img = source_image.convert("L").filter(ImageFilter.FIND_EDGES)
                STRUCTURE_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
                import uuid

                filename = f"pillow_edges_{uuid.uuid4().hex}.png"
                edges_file = STRUCTURE_UPLOADS_ROOT / filename
                edges_img.save(edges_file, format="PNG")

                edges_available = True
                edges_path = f"tmp/structure/{filename}".replace("\\", "/")

                conditioned = edges_img
                edit_mask = _load_edit_mask(segmentation, edges_img.size)
                if edit_mask is not None:
                    masked_edit_suppression = True
                    keep_inv = edit_mask.point(lambda p: 0 if p > 0 else 255)
                    conditioned = ImageChops.multiply(edges_img, keep_inv)
                    overlap = ImageChops.multiply(edges_img.point(lambda p: 255 if p > 0 else 0), edit_mask)
                    total = max(1, overlap.size[0] * overlap.size[1])
                    overlap_hist = overlap.histogram()
                    suppressed = total - overlap_hist[0]
                    suppressed_pixel_percentage = (suppressed / total) * 100.0
                    suppressed_file = STRUCTURE_UPLOADS_ROOT / f"suppressed_{filename}"
                    overlap.save(suppressed_file, format="PNG")
                    suppressed_edges_path = f"tmp/structure/{suppressed_file.name}".replace("\\", "/")

                conditioned_file = STRUCTURE_UPLOADS_ROOT / f"architecture_{filename}"
                conditioned.save(conditioned_file, format="PNG")
                architecture_condition_path = f"tmp/structure/{conditioned_file.name}".replace("\\", "/")
                edges_note = "Pillow edge map prepared for ControlNet conditioning."
            except Exception:
                edges_note = "Failed to compute lightweight edges."

    return StructuralSignals(
        edges_available=edges_available,
        depth_available=False,
        geometry_available=False,
        edges_path=edges_path,
        architecture_condition_path=architecture_condition_path,
        suppressed_edges_path=suppressed_edges_path,
        depth_path=None,
        masked_edit_suppression=masked_edit_suppression,
        suppressed_pixel_percentage=suppressed_pixel_percentage,
        notes=edges_note + " Depth not configured.",
    )
