"""Hardware detection and local AI profile selection (CPU-first)."""

from __future__ import annotations

import logging
import platform
from dataclasses import asdict, dataclass
from functools import lru_cache

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LocalAiProfile:
    name: str
    max_side: int
    steps: int
    guidance: float
    display_max_side: int
    # Design-transform strength (appearance). Structure is NOT solved by this alone.
    design_strength: float
    scheduler: str  # ddim | pndm | euler | default
    mild_sharpen: bool = True


# Public profile names requested by product + backwards-compatible aliases.
PROFILES: dict[str, LocalAiProfile] = {
    "preview": LocalAiProfile(
        name="preview",
        max_side=320,
        steps=12,
        guidance=6.5,
        display_max_side=960,
        design_strength=0.50,
        scheduler="ddim",
    ),
    "balanced": LocalAiProfile(
        name="balanced",
        max_side=384,
        steps=16,
        guidance=7.0,
        display_max_side=1200,
        design_strength=0.55,
        scheduler="ddim",
    ),
    "quality": LocalAiProfile(
        name="quality",
        max_side=448,
        steps=20,
        guidance=7.25,
        display_max_side=1280,
        # Slightly lower strength at higher res to reduce melted furniture.
        design_strength=0.52,
        scheduler="ddim",
    ),
}

# Aliases for older env values.
PROFILES["low_memory"] = PROFILES["preview"]
PROFILES["high"] = PROFILES["quality"]


@dataclass
class HardwareSnapshot:
    cpu: str
    cuda_available: bool
    cuda_device_name: str | None
    total_ram_gb: float | None
    available_ram_gb: float | None
    selected_profile: str
    model_id: str


def _ram_gb() -> tuple[float | None, float | None]:
    try:
        import psutil

        mem = psutil.virtual_memory()
        return mem.total / (1024**3), mem.available / (1024**3)
    except Exception:
        return None, None


def _cuda_info() -> tuple[bool, str | None]:
    try:
        import torch

        if not torch.cuda.is_available():
            return False, None
        name = torch.cuda.get_device_name(0)
        return True, name
    except Exception:
        return False, None


def choose_profile(
    *,
    requested: str | None = None,
    cuda_available: bool | None = None,
    available_ram_gb: float | None = None,
    total_ram_gb: float | None = None,
) -> LocalAiProfile:
    """Pick the highest realism profile that can safely run on this machine."""
    name = (requested or settings.local_ai_profile or "auto").strip().lower()
    if name in PROFILES:
        return PROFILES[name]

    if cuda_available is None or available_ram_gb is None or total_ram_gb is None:
        cuda_available, _ = _cuda_info()
        total_ram_gb, available_ram_gb = _ram_gb()

    avail = available_ram_gb or 0.0
    total = total_ram_gb or 0.0

    # Peak RSS for tiny-sd was ~2.7 GB; leave headroom for OS + browser.
    if cuda_available and avail >= 2.0:
        return PROFILES["quality"]
    if avail >= 3.8 and total >= 12.0:
        return PROFILES["quality"]
    if avail >= 2.6 and total >= 12.0:
        return PROFILES["balanced"]
    return PROFILES["preview"]


@lru_cache(maxsize=1)
def detect_hardware() -> HardwareSnapshot:
    total, available = _ram_gb()
    cuda, cuda_name = _cuda_info()
    profile = choose_profile(
        cuda_available=cuda,
        available_ram_gb=available,
        total_ram_gb=total,
    )
    model_id = (settings.local_model_id or settings.local_diffusion_model or "").strip()
    snapshot = HardwareSnapshot(
        cpu=platform.processor() or platform.machine() or "unknown",
        cuda_available=cuda,
        cuda_device_name=cuda_name,
        total_ram_gb=round(total, 2) if total is not None else None,
        available_ram_gb=round(available, 2) if available is not None else None,
        selected_profile=profile.name,
        model_id=model_id,
    )
    logger.info(
        "REFRAME_HW cpu=%s cuda=%s total_ram_gb=%s available_ram_gb=%s profile=%s model=%s",
        snapshot.cpu,
        snapshot.cuda_available,
        snapshot.total_ram_gb,
        snapshot.available_ram_gb,
        snapshot.selected_profile,
        snapshot.model_id,
    )
    return snapshot


def refresh_hardware() -> HardwareSnapshot:
    detect_hardware.cache_clear()
    return detect_hardware()


def hardware_dict() -> dict:
    return asdict(detect_hardware())


def active_profile() -> LocalAiProfile:
    snap = detect_hardware()
    return PROFILES[snap.selected_profile]


def process_rss_gb() -> float | None:
    try:
        import psutil

        return psutil.Process().memory_info().rss / (1024**3)
    except Exception:
        return None


def system_available_gb() -> float | None:
    _, available = _ram_gb()
    return available
