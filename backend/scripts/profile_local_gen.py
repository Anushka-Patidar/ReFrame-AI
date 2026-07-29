"""Profile local img2img memory + quality on this machine (no paid APIs)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from app.services.design_brief import DesignBrief, build_design_brief  # noqa: E402
from app.services.hardware import (  # noqa: E402
    choose_profile,
    detect_hardware,
    process_rss_gb,
    system_available_gb,
)
from app.services.image_generation import mean_abs_delta, structure_similarity  # noqa: E402
from app.services.providers.local_diffusion import get_local_provider  # noqa: E402


OUT_DIR = ROOT / "uploads" / "generated" / "profile"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _sample_living_room() -> Image.Image:
    """Create a stand-in living-room photo if no real upload is available."""
    img = Image.new("RGB", (960, 640), (232, 224, 210))
    draw = ImageDraw.Draw(img)
    # Floor / wall
    draw.rectangle((0, 420, 960, 640), fill=(150, 120, 90))
    draw.rectangle((40, 40, 920, 420), fill=(236, 228, 214))
    # Curtains
    draw.rectangle((60, 50, 160, 400), fill=(210, 200, 180))
    draw.rectangle((800, 50, 900, 400), fill=(210, 200, 180))
    # Door
    draw.rectangle((700, 120, 780, 400), fill=(120, 80, 50))
    # Sofa
    draw.rectangle((180, 300, 520, 420), fill=(70, 45, 35))
    # TV unit
    draw.rectangle((560, 180, 680, 320), fill=(40, 40, 40))
    draw.rectangle((540, 320, 700, 360), fill=(230, 230, 230))
    # Paintings
    draw.rectangle((220, 80, 340, 180), fill=(180, 160, 140))
    draw.rectangle((360, 90, 460, 170), fill=(160, 140, 120))
    return img


def _load_source() -> Image.Image:
    preferred = [
        "a16628a2e27d48ccaa3b6ccc6c6210e5.jpeg",
        "31315347752e4b308247e31ff26b7819.jpeg",
    ]
    rooms = ROOT / "uploads" / "rooms"
    for name in preferred:
        path = rooms / name
        if path.exists():
            print(f"Using room upload: {path}")
            return Image.open(path).convert("RGB")
    candidates = list(rooms.glob("*")) if rooms.exists() else []
    for path in candidates:
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"} and path.stat().st_size > 50_000:
            print(f"Using room upload: {path}")
            return Image.open(path).convert("RGB")
    print("No room upload found — using synthetic living-room stand-in for memory profile.")
    return _sample_living_room()


def main() -> int:
    hw = detect_hardware()
    print("HARDWARE", json.dumps(hw.__dict__, indent=2))
    profile = choose_profile()
    print("PROFILE", profile)

    baseline_rss = process_rss_gb()
    baseline_avail = system_available_gb()
    print(f"BASELINE process_rss_gb={baseline_rss} available_gb={baseline_avail}")

    source = _load_source()
    room = {"room_type": "Living Room", "original_image_url": None}
    requirements = {
        "room": "Living Room",
        "style": "Indian Contemporary",
        "keep": ["curtains", "door"],
        "remove": ["sofa", "TV unit", "paintings"],
        "add": ["artwork", "wall clock", "new furniture"],
        "colours": ["blue", "yellow", "brown", "white"],
        "budget": 150000,
    }
    brief = build_design_brief(room, requirements, None)
    print("BRIEF strength=", brief.transformation_strength)

    provider = get_local_provider()
    result = provider.generate_room(source, brief, brief.transformation_strength, profile=profile)
    out = OUT_DIR / "tiny_sd_living_room.jpg"
    result.image.save(out, quality=92)
    source_out = OUT_DIR / "source_before.jpg"
    source.save(source_out, quality=92)

    delta = mean_abs_delta(source, result.image)
    structure = structure_similarity(source, result.image)
    report = {
        "hardware": hw.__dict__,
        "profile": profile.name,
        "resolution": result.resolution,
        "steps": result.steps,
        "elapsed_seconds": result.elapsed_seconds,
        "delta": delta,
        "structure_similarity": structure,
        "memory_marks": provider.memory_profile,
        "output": str(out),
        "baseline_rss_gb": baseline_rss,
        "baseline_available_gb": baseline_avail,
        "model": result.model,
        "device": result.device,
    }
    report_path = OUT_DIR / "profile_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Wrote {out}")
    print(f"Wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
