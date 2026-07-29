"""Quick smoke: generate and save one redesign after OpenCV fix."""

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image

from app.services.design_brief import build_design_brief
from app.services.image_generation import (
    contains_human_face,
    images_byte_identical,
    mean_abs_delta,
    structure_similarity,
)
from app.services.media import GENERATED_UPLOADS_ROOT
from app.services.providers.local_diffusion import get_local_provider


def main() -> int:
    src = Image.open(
        ROOT / "uploads" / "rooms" / "a16628a2e27d48ccaa3b6ccc6c6210e5.jpeg"
    ).convert("RGB")
    brief = build_design_brief(
        {"room_type": "Living Room"},
        {
            "style": "Indian Contemporary",
            "keep": ["curtains", "door"],
            "remove": ["sofa", "TV unit", "paintings"],
            "add": ["artwork", "wall clock"],
            "colours": ["blue", "yellow", "brown", "white"],
        },
    )
    result = get_local_provider().generate_room(src, brief, brief.transformation_strength)
    out = result.image
    print("identical", images_byte_identical(src, out))
    print("delta", round(mean_abs_delta(src, out), 2))
    print("structure", round(structure_similarity(src, out), 3))
    print("face", contains_human_face(out))
    GENERATED_UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    path = GENERATED_UPLOADS_ROOT / "smoke_fix.jpg"
    buf = io.BytesIO()
    out.save(buf, format="JPEG", quality=90)
    path.write_bytes(buf.getvalue())
    print("saved", path)
    print("elapsed", round(result.elapsed_seconds, 1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
