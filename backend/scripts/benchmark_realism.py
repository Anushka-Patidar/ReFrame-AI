"""Sequential realism benchmark for local img2img (dev-only, CPU-safe).

Runs one configuration at a time. Does not download new models.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app.services.design_brief import (  # noqa: E402
    build_design_brief,
    build_local_clip_prompt,
    build_local_negative_prompt,
)
from app.services.hardware import PROFILES, process_rss_gb, refresh_hardware  # noqa: E402
from app.services.image_generation import mean_abs_delta, structure_similarity  # noqa: E402
from app.services.providers.local_diffusion import get_local_provider  # noqa: E402

OUT = ROOT / "uploads" / "generated" / "benchmark"
OUT.mkdir(parents=True, exist_ok=True)

# Fixed seed so strength/step comparisons are comparable.
SEED = 42

CONFIGS = [
    # strength sweep at fixed steps (preview-friendly resolution)
    {"id": "s045_st12_r320", "max_side": 320, "steps": 12, "strength": 0.45, "guidance": 6.5},
    {"id": "s055_st12_r320", "max_side": 320, "steps": 12, "strength": 0.55, "guidance": 6.5},
    {"id": "s065_st12_r320", "max_side": 320, "steps": 12, "strength": 0.65, "guidance": 6.5},
    # steps sweep near best expected strength
    {"id": "s055_st16_r320", "max_side": 320, "steps": 16, "strength": 0.55, "guidance": 7.0},
    {"id": "s055_st20_r384", "max_side": 384, "steps": 20, "strength": 0.52, "guidance": 7.25},
]


def _sharpness_proxy(image: Image.Image) -> float:
    edges = image.convert("L").resize((128, 128)).filter(__import__("PIL").ImageFilter.FIND_EDGES)
    pixels = list(edges.getdata())
    return sum(pixels) / max(1, len(pixels))


def main() -> int:
    refresh_hardware()
    source_path = ROOT / "uploads" / "rooms" / "a16628a2e27d48ccaa3b6ccc6c6210e5.jpeg"
    source = Image.open(source_path).convert("RGB")
    room = {"room_type": "Living Room", "original_image_url": None}
    requirements = {
        "style": "Indian Contemporary",
        "keep": ["curtains", "door"],
        "remove": ["sofa", "TV unit", "paintings"],
        "add": ["new seating", "artwork", "wall clock"],
        "change": ["furniture", "wall treatment"],
        "colours": ["blue", "yellow", "brown", "white"],
        "budget": 80000,
    }
    brief = build_design_brief(room, requirements, None)
    provider = get_local_provider()

    print("=== PHASE 1 BASELINE PROMPT ===")
    print("POSITIVE:", build_local_clip_prompt(brief))
    print("NEGATIVE:", build_local_negative_prompt(brief))
    print("SEED:", SEED)
    print("BASELINE_RSS_GB:", process_rss_gb())

    rows = []
    for cfg in CONFIGS:
        print(f"\n=== RUN {cfg['id']} ===")
        # Build a temporary profile-like object by cloning preview and overriding fields.
        base = PROFILES["preview"]
        from dataclasses import replace

        profile = replace(
            base,
            name=f"bench_{cfg['id']}",
            max_side=cfg["max_side"],
            steps=cfg["steps"],
            guidance=cfg["guidance"],
            design_strength=cfg["strength"],
            scheduler="ddim",
        )
        before = process_rss_gb()
        t0 = time.perf_counter()
        result = provider.generate_room(
            source,
            brief,
            "strong",
            profile=profile,
            seed=SEED,
            strength_override=cfg["strength"],
            steps_override=cfg["steps"],
        )
        elapsed = time.perf_counter() - t0
        after = process_rss_gb()
        delta = mean_abs_delta(source, result.image)
        structure = structure_similarity(source, result.image)
        sharp = _sharpness_proxy(result.image)
        out_path = OUT / f"{cfg['id']}.jpg"
        result.image.save(out_path, quality=92)
        row = {
            **cfg,
            "elapsed_seconds": round(elapsed, 2),
            "delta": round(delta, 2),
            "structure": round(structure, 3),
            "sharpness_proxy": round(sharp, 2),
            "rss_before": before,
            "rss_after": after,
            "peak_rss_gb": provider.memory_profile.get("during_decoding")
            or provider.memory_profile.get("after_generation"),
            "resolution": list(result.resolution),
            "output_size": list(result.image.size),
            "seed": result.seed,
            "scheduler": provider.last_run_config.get("scheduler"),
            "model": result.model,
            "device": result.device,
            "output": str(out_path),
            "run_config": provider.last_run_config,
        }
        rows.append(row)
        print(json.dumps({k: row[k] for k in row if k != "run_config"}, indent=2))
        result.image.close()
        # Cool down between runs on constrained machines.
        time.sleep(2)

    report = {
        "source": str(source_path),
        "seed": SEED,
        "positive_prompt": build_local_clip_prompt(brief),
        "negative_prompt": build_local_negative_prompt(brief),
        "rows": rows,
        "recommendation_notes": (
            "Prefer higher structure + visible delta + higher sharpness_proxy, "
            "without melted-furniture artifacts (manual visual check of saved JPGs)."
        ),
    }
    report_path = OUT / "benchmark_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nWrote", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
