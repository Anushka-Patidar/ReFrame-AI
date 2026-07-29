"""DesignMemory — non-sensitive preference memory across rooms."""

from __future__ import annotations

from app.services.pipeline.types import DesignMemoryProfile


def empty_memory() -> DesignMemoryProfile:
    return DesignMemoryProfile()


def memory_from_document(document: dict | None) -> DesignMemoryProfile:
    if not document:
        return empty_memory()
    payload = document.get("design_memory") if "design_memory" in document else document
    payload = payload or {}
    return DesignMemoryProfile(
        preferred_styles=_clean(payload.get("preferred_styles")),
        preferred_materials=_clean(payload.get("preferred_materials")),
        preferred_colors=_clean(payload.get("preferred_colors")),
        lighting_preferences=_clean(payload.get("lighting_preferences")),
        frequently_kept=_clean(payload.get("frequently_kept")),
        avoid=_clean(payload.get("avoid")),
    )


def merge_memory_from_requirements(
    memory: DesignMemoryProfile,
    requirements: dict | None,
) -> DesignMemoryProfile:
    """Update memory from a room's requirements card (non-sensitive fields only)."""
    requirements = dict(requirements or {})
    style = (requirements.get("style") or "").strip()
    if style and style not in memory.preferred_styles:
        memory.preferred_styles = [style, *memory.preferred_styles][:6]

    for color in requirements.get("colours") or []:
        cleaned = str(color).strip()
        if cleaned and cleaned not in memory.preferred_colors:
            memory.preferred_colors.append(cleaned)
    memory.preferred_colors = memory.preferred_colors[:8]

    for kept in requirements.get("keep") or []:
        cleaned = str(kept).strip()
        if cleaned and cleaned not in memory.frequently_kept:
            memory.frequently_kept.append(cleaned)
    memory.frequently_kept = memory.frequently_kept[:10]

    for avoided in requirements.get("avoid") or []:
        cleaned = str(avoided).strip()
        if cleaned and cleaned not in memory.avoid:
            memory.avoid.append(cleaned)
    memory.avoid = memory.avoid[:10]

    return memory


def apply_memory_to_requirements(
    requirements: dict,
    memory: DesignMemoryProfile,
) -> dict:
    """Inject soft memory hints into requirements before DesignBrief construction."""
    updated = dict(requirements)
    hints: list[str] = []
    if memory.preferred_styles and not updated.get("style"):
        updated["style"] = memory.preferred_styles[0]
    if memory.preferred_colors and not updated.get("colours"):
        updated["colours"] = list(memory.preferred_colors[:4])
    if memory.preferred_materials:
        hints.extend(f"prefer material:{item}" for item in memory.preferred_materials[:3])
    if memory.lighting_preferences:
        hints.extend(f"prefer lighting:{item}" for item in memory.lighting_preferences[:2])
    if memory.avoid:
        existing_avoid = list(updated.get("avoid") or [])
        for item in memory.avoid:
            if item not in existing_avoid:
                existing_avoid.append(item)
        updated["avoid"] = existing_avoid[:10]
        hints.extend(f"avoid:{item}" for item in memory.avoid[:3])
    if hints:
        updated["memory_hints"] = hints
    return updated


def _clean(items) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items or []:
        text = str(item).strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result
