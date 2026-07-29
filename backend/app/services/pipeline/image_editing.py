"""Structure vs style abstractions — separate preservation from redesign."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from PIL import Image

from app.services.design_brief import DesignBrief
from app.services.pipeline.structural_conditioning import prepare_structural_signals
from app.services.pipeline.types import StructuralSignals
from app.services.providers import GenerationResult


@dataclass
class DesignTransform:
    """Appearance / redesign intent — independent of structure preservation."""

    strength: float  # img2img design strength (0–1)
    guidance: float
    steps: int
    prompt: str
    negative_prompt: str
    seed: int | None = None


class StructuralConditioner(ABC):
    """Eventually supplies edges/depth so architecture can stay stable."""

    @abstractmethod
    def condition(self, source_image: Image.Image, brief: DesignBrief) -> StructuralSignals:
        raise NotImplementedError


class LightweightStructuralConditioner(StructuralConditioner):
    """Development conditioner — no ControlNet/depth model download."""

    def condition(self, source_image: Image.Image, brief: DesignBrief) -> StructuralSignals:
        _ = brief
        return prepare_structural_signals(source_image, compute_lightweight_edges=True)


class ImageEditor(ABC):
    """Applies design transform; may optionally consume structural signals later."""

    @abstractmethod
    def edit(
        self,
        source_image: Image.Image,
        brief: DesignBrief,
        transform: DesignTransform,
        structure: StructuralSignals | None = None,
        **kwargs: Any,
    ) -> GenerationResult:
        raise NotImplementedError
