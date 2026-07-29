"""Room image generation provider abstraction (local-first)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

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


class RoomGenerationProvider(ABC):
    """Edit an uploaded room photo using a structured DesignBrief."""

    name: str = "base"

    @abstractmethod
    def generate_room(
        self,
        source_image: Image.Image,
        design_brief: DesignBrief,
        transformation_strength: str | None = None,
    ) -> GenerationResult:
        raise NotImplementedError
