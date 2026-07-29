"""DesignReasoning — conversation/requirements → DesignBrief (deterministic)."""

from __future__ import annotations

from app.services.design_brief import DesignBrief, build_design_brief
from app.services.pipeline.design_memory import (
    apply_memory_to_requirements,
    empty_memory,
    memory_from_document,
    merge_memory_from_requirements,
)
from app.services.pipeline.types import DesignMemoryProfile


def reason_design_brief(
    room: dict,
    requirements: dict | None,
    revision_note: str | None = None,
    *,
    memory_document: dict | None = None,
) -> tuple[DesignBrief, DesignMemoryProfile, dict]:
    """Convert stored requirements (+ optional memory) into a structured DesignBrief.

    Image generation must never parse messy chat history directly — this stage
    is the single source of structured intent.
    """
    memory = memory_from_document(memory_document) if memory_document else empty_memory()
    memory = merge_memory_from_requirements(memory, requirements)
    enriched = apply_memory_to_requirements(dict(requirements or {}), memory)
    brief = build_design_brief(room, enriched, revision_note)
    return brief, memory, enriched
