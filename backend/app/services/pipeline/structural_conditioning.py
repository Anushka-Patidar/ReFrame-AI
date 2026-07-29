"""Structural conditioning interface — edges/depth/geometry for future providers.

Current development implementation: Canny edge extraction using OpenCV (no
ControlNet/depth model downloads). Falls back to Pillow edges when OpenCV is
unavailable.
"""

from __future__ import annotations

from PIL import Image, ImageFilter

from app.services.media import STRUCTURE_UPLOADS_ROOT
from app.services.pipeline.types import StructuralSignals


def prepare_structural_signals(
    source_image: Image.Image,
    *,
    compute_lightweight_edges: bool = True,
) -> StructuralSignals:
    """Prepare structural signals without loading ControlNet / depth models.

    Uses OpenCV Canny on CPU to derive a lightweight structural map.
    """
    edges_available = False
    edges_path: str | None = None
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
            # Store relative path under backend/uploads for later consumption.
            edges_path = f"tmp/structure/{filename}".replace("\\", "/")
            edges_note = "OpenCV Canny edge map saved (temporary structure artifact)."
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
                edges_note = "Pillow FIND_EDGES fallback saved (no OpenCV available)."
            except Exception:
                edges_note = "Failed to compute lightweight edges."

    return StructuralSignals(
        edges_available=edges_available,
        depth_available=False,
        geometry_available=False,
        edges_path=edges_path,
        depth_path=None,
        notes=edges_note + " Depth/ControlNet not configured.",
    )
