"""Shared dataclasses for the ReFrame modular AI pipeline.

Stages (conceptual):
  RoomUnderstanding → DesignReasoning → DesignBrief → SceneUnderstanding
  → Segmentation → StructuralConditioning → ImageEditing → ResultValidation
  → DesignMemory

Heavy vision/segmentation models are intentionally NOT required here —
interfaces are ready so stronger backends can be plugged in later.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ConstraintKind(str, Enum):
    ARCHITECTURE_LOCKED = "ARCHITECTURE_LOCKED"
    OBJECT_KEEP = "OBJECT_KEEP"
    OBJECT_REMOVE = "OBJECT_REMOVE"
    OBJECT_REPLACE = "OBJECT_REPLACE"
    OBJECT_ADD = "OBJECT_ADD"
    STYLE_CONSTRAINT = "STYLE_CONSTRAINT"
    COLOR_CONSTRAINT = "COLOR_CONSTRAINT"


class AnalysisSource(str, Enum):
    USER = "user"
    HEURISTIC = "heuristic"
    VISION = "vision"  # reserved for future automatic vision


@dataclass
class ArchitectureFeatures:
    doors: list[str] = field(default_factory=list)
    windows: list[str] = field(default_factory=list)
    walls: list[str] = field(default_factory=list)
    ceiling: str | None = None
    floor: str | None = None


@dataclass
class RoomObject:
    id: str
    type: str
    status: str = "existing"  # existing | keep | remove | replace | add
    source: str = AnalysisSource.USER.value
    confidence: float | None = None
    bounding_box: tuple[float, float, float, float] | None = None  # x,y,w,h normalized optional
    notes: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RoomAnalysis:
    """RoomUnderstanding output. May be user-assisted until vision is available."""

    room_type: str
    architecture: ArchitectureFeatures = field(default_factory=ArchitectureFeatures)
    objects: list[RoomObject] = field(default_factory=list)
    lighting: list[str] = field(default_factory=list)
    decor: list[str] = field(default_factory=list)
    source: str = AnalysisSource.USER.value
    notes: str | None = None

    def to_dict(self) -> dict:
        return {
            "room_type": self.room_type,
            "architecture": asdict(self.architecture),
            "objects": [obj.to_dict() for obj in self.objects],
            "lighting": list(self.lighting),
            "decor": list(self.decor),
            "source": self.source,
            "notes": self.notes,
        }


@dataclass
class DesignConstraint:
    kind: ConstraintKind
    target: str
    detail: str | None = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind.value if isinstance(self.kind, ConstraintKind) else str(self.kind),
            "target": self.target,
            "detail": self.detail,
        }


@dataclass
class ConstraintSet:
    """Source of truth for KEEP / REMOVE / REPLACE / ADD / style / color / architecture."""

    items: list[DesignConstraint] = field(default_factory=list)

    def by_kind(self, kind: ConstraintKind) -> list[DesignConstraint]:
        return [item for item in self.items if item.kind == kind]

    def targets(self, kind: ConstraintKind) -> list[str]:
        return [item.target for item in self.by_kind(kind)]

    def to_dict(self) -> dict:
        return {"items": [item.to_dict() for item in self.items]}


@dataclass
class ObjectMask:
    """Future segmentation artifact. No model required to define the schema."""

    object_id: str
    label: str
    # User intent for this region mask:
    # - KEEP: protected region
    # - CHANGE / REMOVE: editable regions
    action: str = "CHANGE"
    bounding_box: tuple[float, float, float, float] | None = None
    # Mask stored as path or deferred binary — never invent pixel data.
    mask_path: str | None = None
    confidence: float | None = None
    available: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SegmentationResult:
    masks: list[ObjectMask] = field(default_factory=list)
    provider: str | None = None
    available: bool = False
    reason: str = "Segmentation not configured on this development machine."
    # Combined user masks (unioned, action-aware) for future inpainting/editors.
    keep_mask_path: str | None = None
    edit_mask_path: str | None = None
    keep_painted_pixel_percentage: float | None = None
    edit_painted_pixel_percentage: float | None = None
    keep_mask_dimensions: tuple[int, int] | None = None
    edit_mask_dimensions: tuple[int, int] | None = None
    keep_edit_overlap_pixel_percentage: float | None = None
    debug_preview_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "masks": [mask.to_dict() for mask in self.masks],
            "provider": self.provider,
            "available": self.available,
            "reason": self.reason,
            "keep_mask_path": self.keep_mask_path,
            "edit_mask_path": self.edit_mask_path,
            "keep_painted_pixel_percentage": self.keep_painted_pixel_percentage,
            "edit_painted_pixel_percentage": self.edit_painted_pixel_percentage,
            "keep_mask_dimensions": list(self.keep_mask_dimensions) if self.keep_mask_dimensions else None,
            "edit_mask_dimensions": list(self.edit_mask_dimensions) if self.edit_mask_dimensions else None,
            "keep_edit_overlap_pixel_percentage": self.keep_edit_overlap_pixel_percentage,
            "debug_preview_path": self.debug_preview_path,
        }


@dataclass
class StructuralSignals:
    """Future depth/edge/geometry conditioning. Provider-agnostic."""

    edges_available: bool = False
    depth_available: bool = False
    geometry_available: bool = False
    edges_path: str | None = None
    architecture_condition_path: str | None = None
    suppressed_edges_path: str | None = None
    depth_path: str | None = None
    masked_edit_suppression: bool = False
    suppressed_pixel_percentage: float | None = None
    notes: str = "Structural conditioning interface only — no heavy model loaded."

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ValidationMetric:
    """Only populate value when a genuine measurement exists."""

    name: str
    measured: bool
    value: float | None = None
    passed: bool | None = None
    detail: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DesignValidationReport:
    architecture_preserved: bool | None
    constraints: dict[str, bool | None]
    metrics: list[ValidationMetric]
    violations: list[str]
    overall_passed: bool
    # Do NOT invent style_score / overall_score without a real evaluator.
    style_score: float | None = None
    overall_score: float | None = None
    attempt: int = 1

    def to_dict(self) -> dict:
        return {
            "architecture_preserved": self.architecture_preserved,
            "constraints": dict(self.constraints),
            "metrics": [metric.to_dict() for metric in self.metrics],
            "violations": list(self.violations),
            "overall_passed": self.overall_passed,
            "style_score": self.style_score,
            "overall_score": self.overall_score,
            "attempt": self.attempt,
        }


@dataclass
class DesignMemoryProfile:
    """Non-sensitive preference memory across rooms."""

    preferred_styles: list[str] = field(default_factory=list)
    preferred_materials: list[str] = field(default_factory=list)
    preferred_colors: list[str] = field(default_factory=list)
    lighting_preferences: list[str] = field(default_factory=list)
    frequently_kept: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GenerationMetadata:
    """Persisted with each design version for future learning (opt-in only)."""

    generation_id: str
    source_image_url: str | None
    design_brief: dict[str, Any]
    constraints: dict[str, Any]
    room_analysis: dict[str, Any] | None
    validation: dict[str, Any] | None
    model: str | None
    model_configuration: dict[str, Any]
    seed: int | None
    attempts: int
    provider: str | None
    user_accepted: bool | None = None
    user_rejected: bool | None = None
    user_feedback: str | None = None
    training_consent: bool = False  # must stay False unless user explicitly opts in

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PipelineArtifacts:
    room_analysis: RoomAnalysis
    constraints: ConstraintSet
    segmentation: SegmentationResult
    structure: StructuralSignals
    validation: DesignValidationReport | None = None
    memory: DesignMemoryProfile | None = None
    metadata: GenerationMetadata | None = None
    correction_note: str | None = None
