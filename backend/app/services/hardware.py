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


PROFILES: dict[str, LocalAiProfile] = {
    "low_memory": LocalAiProfile(
        name="low_memory",
        max_side=320,
        steps=12,
        guidance=6.5,
        display_max_side=1024,
    ),
    "balanced": LocalAiProfile(
        name="balanced",
        max_side=384,
        steps=12,
        guidance=7.0,
        display_max_side=1200,
    ),
    "high": LocalAiProfile(
        name="high",
        max_side=512,
        steps=16,
        guidance=7.5,
        display_max_side=1400,
    ),
}


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
    """Pick a generation profile from config + measured hardware.

    Thresholds are intentionally modest: tiny SD img2img peaks well under 8 GB
    when resolution/steps are constrained. Values are refined by profiling.
    """
    name = (requested or settings.local_ai_profile or "auto").strip().lower()
    if name in PROFILES:
        return PROFILES[name]

    if cuda_available is None or available_ram_gb is None or total_ram_gb is None:
        cuda_available, _ = _cuda_info()
        total_ram_gb, available_ram_gb = _ram_gb()

    if cuda_available and (available_ram_gb or 0) >= 2.0:
        return PROFILES["high"]
    # Balanced only when there is comfortable headroom after the model is resident.
    if (available_ram_gb or 0) >= 4.5 and (total_ram_gb or 0) >= 12.0:
        return PROFILES["balanced"]
    return PROFILES["low_memory"]


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
