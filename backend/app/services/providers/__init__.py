"""Room image generation provider abstraction (model-independent)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from PIL import Image

from app.services.design_brief import DesignBrief


@dataclass
class GenerationResult:
    image: Image.Image
    provider: str
    model: str
    device: str
    steps: int
    strength: float
    resolution: tuple[int, int]
    elapsed_seconds: float
    engine: str
    seed: int | None = None


class RoomGenerationProvider(ABC):
    """Edit an uploaded room photo using a structured DesignBrief + optional conditioning."""

    name: str = "base"

    @abstractmethod
    def generate_room(
        self,
        source_image: Image.Image,
        design_brief: DesignBrief,
        transformation_strength: str | None = None,
        *,
        constraints: Any = None,
        segmentation: Any = None,
        structure: Any = None,
    ) -> GenerationResult:
        raise NotImplementedError
