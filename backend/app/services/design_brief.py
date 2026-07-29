"""Structured DesignBrief for ReFrame room image editing.

KEEP is object-specific. Architecture preservation is separate.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.services.design_knowledge import get_style_profile, resolve_style


@dataclass
class DesignBrief:
    room_type: str
    target_style: str
    preserve_architecture: list[str] = field(default_factory=list)
    keep_objects: list[str] = field(default_factory=list)
    remove_objects: list[str] = field(default_factory=list)
    replace_or_add: list[str] = field(default_factory=list)
    palette: list[str] = field(default_factory=list)
    transformation_strength: str = "balanced"  # subtle | balanced | strong
    realism: str = "photorealistic"
    revision_note: str | None = None
    materials: list[str] = field(default_factory=list)
    mood: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_list(items: list[str] | None, limit: int = 8) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items or []:
        cleaned = item.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result[:limit]


def classify_transformation_strength(
    keep: list[str],
    remove: list[str],
    add: list[str],
) -> str:
    """Major furniture/wall changes => strong interior redesign."""
    major_tokens = (
        "sofa",
        "couch",
        "tv",
        "television",
        "furniture",
        "painting",
        "artwork",
        "wall paint",
        "paint",
        "wardrobe",
        "bed",
        "table",
        "chair",
        "rug",
        "curtain",
        "lighting",
        "clock",
    )
    change_text = " ".join([*remove, *add]).lower()
    major_hits = sum(1 for token in major_tokens if token in change_text)
    if major_hits >= 2 or len(remove) >= 2 or len(add) >= 3:
        return "strong"
    if major_hits >= 1 or remove or add:
        return "balanced"
    if keep and not remove and not add:
        return "subtle"
    return "balanced"


def build_design_brief(
    room: dict,
    requirements: dict | None,
    revision_note: str | None = None,
) -> DesignBrief:
    requirements = dict(requirements or {})
    room_type = (requirements.get("room") or room.get("room_type") or "Living Room").strip()
    style = resolve_style(requirements.get("style"))
    profile = get_style_profile(style)

    # Object-level KEEP only — never inject architecture anchors into KEEP.
    keep_objects = _clean_list(requirements.get("keep"))
    remove_objects = _clean_list(requirements.get("remove"))
    replace_or_add = _clean_list(requirements.get("add"))
    palette = _clean_list(requirements.get("colours") or profile["palette"][:4], limit=5)

    remove_keys = {item.lower() for item in remove_objects}
    keep_objects = [item for item in keep_objects if item.lower() not in remove_keys]

    strength = classify_transformation_strength(keep_objects, remove_objects, replace_or_add)
    if revision_note and any(
        token in revision_note.lower()
        for token in ("replace", "remove", "change", "new furniture", "repaint", "redesign")
    ):
        strength = "strong"

    return DesignBrief(
        room_type=room_type,
        target_style=style,
        preserve_architecture=[
            "room geometry and proportions",
            "camera viewpoint and perspective",
            "windows and permanent openings",
            "ceiling and floor boundaries",
            "structural walls and columns",
        ],
        keep_objects=keep_objects,
        remove_objects=remove_objects,
        replace_or_add=replace_or_add,
        palette=palette,
        transformation_strength=strength,
        realism="photorealistic",
        revision_note=revision_note,
        materials=list(profile.get("materials") or [])[:4],
        mood=str(profile.get("mood") or ""),
    )


def build_edit_prompt(brief: DesignBrief) -> str:
    """Long prompt for APIs that accept full briefs (not CLIP-77)."""
    keep_line = (
        ", ".join(f"existing {item}" for item in brief.keep_objects)
        if brief.keep_objects
        else "none — redesign all movable interior content"
    )
    remove_line = (
        ", ".join(f"existing {item}" for item in brief.remove_objects)
        if brief.remove_objects
        else "none"
    )
    add_line = (
        ", ".join(brief.replace_or_add)
        if brief.replace_or_add
        else f"new {brief.target_style} furniture, wall treatment, and decor"
    )
    palette_line = ", ".join(brief.palette) if brief.palette else "style-default palette"
    strength_line = {
        "subtle": "subtle but visible interior refinements",
        "balanced": "clearly visible interior redesign",
        "strong": "STRONG clearly visible interior transformation",
    }.get(brief.transformation_strength, "clearly visible interior redesign")

    prompt = (
        f"Edit the supplied photograph of the user's real {brief.room_type.lower()}. "
        "This is an INTERIOR REDESIGN, not image reconstruction and not a new property. "
        "Preserve ONLY the physical architecture: "
        f"{', '.join(brief.preserve_architecture)}. "
        f"Perform a {strength_line}. "
        f"TARGET STYLE: {brief.target_style} interior design ({brief.mood}). "
        f"KEEP UNCHANGED (object-specific only): {keep_line}. "
        "Do NOT interpret KEEP as preserving the whole room or all furniture. "
        f"REMOVE COMPLETELY: {remove_line}. "
        f"REPLACE / INTRODUCE: {add_line}. "
        f"COLOR DIRECTION: {palette_line}. "
        f"Materials language: {', '.join(brief.materials)}. "
        "The AFTER image must be visibly different from the BEFORE image. "
        "Do NOT simply reproduce the source photograph. "
        "Do NOT preserve furniture unless explicitly listed under KEEP. "
        "Do NOT make only subtle cosmetic color grading. "
        "No people, no faces, no portraits, no text, no watermark. "
        "Maintain realistic scale, perspective, shadows, and lighting. "
        "Final image: professionally renovated version of the SAME real room."
    )
    if brief.revision_note:
        prompt += f" Revision focus: {brief.revision_note}."
    return prompt


def build_local_clip_prompt(brief: DesignBrief) -> str:
    """CLIP-safe prompt (~77 tokens). Local SD models truncate longer text."""
    keep = ", ".join(brief.keep_objects[:3]) if brief.keep_objects else "architecture"
    remove = ", ".join(brief.remove_objects[:3]) if brief.remove_objects else "old furniture"
    add = ", ".join(brief.replace_or_add[:3]) if brief.replace_or_add else "new furniture"
    palette = ", ".join(brief.palette[:3]) if brief.palette else "warm neutrals"
    revision = f" {brief.revision_note}." if brief.revision_note else ""
    # Keep under CLIP's 77-token limit; front-load the redesign intent.
    return (
        f"photorealistic {brief.target_style} {brief.room_type.lower()} interior redesign, "
        f"same room layout, keep {keep}, remove {remove}, add {add}, "
        f"palette {palette}, realistic furniture lighting shadows{revision}"
    )


def build_local_negative_prompt(brief: DesignBrief) -> str:
    remove = ", ".join(brief.remove_objects[:4]) if brief.remove_objects else "old sofa"
    return (
        f"{remove}, unchanged original room, blurry, abstract, cartoon, painting, "
        "people, faces, text, watermark, warped walls, extra windows, low quality"
    )


def build_pollinations_edit_prompt(brief: DesignBrief) -> str:
    """Shorter URL-safe prompt that still demands strong furniture replacement."""
    keep = ", ".join(brief.keep_objects) if brief.keep_objects else "architecture only"
    remove = ", ".join(brief.remove_objects) if brief.remove_objects else "old furniture"
    add = ", ".join(brief.replace_or_add[:4]) if brief.replace_or_add else "new furniture and wall finish"
    palette = ", ".join(brief.palette[:4])
    strength = "STRONG visible redesign" if brief.transformation_strength == "strong" else "visible redesign"
    revision = f" Revision: {brief.revision_note}." if brief.revision_note else ""
    return (
        f"{strength} of this exact {brief.room_type} photo. "
        f"{brief.target_style} interior design. Empty room, no people, no faces. "
        f"Preserve architecture and camera only. Keep objects only: {keep}. "
        f"Remove completely: {remove}. Add/replace: {add}. Palette: {palette}. "
        f"Must look clearly renovated, not the unchanged original.{revision}"
    )[:780]


def build_negative_constraints(brief: DesignBrief) -> str:
    kept = ", ".join(brief.keep_objects) if brief.keep_objects else "listed keep objects"
    return (
        "unchanged original furniture, duplicate furniture, retaining removed objects, "
        f"preserving items marked for removal, ignoring KEEP limit (only keep {kept}), "
        "distorted architecture, changed window positions, changed door positions, "
        "altered room proportions, warped walls, extra doors, extra windows, "
        "unrealistic furniture scale, floating objects, duplicated decor, "
        "people, faces, portraits, text overlay, watermark, collage"
    )
