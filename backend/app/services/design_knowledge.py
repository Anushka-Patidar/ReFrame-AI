"""Trained interior-design knowledge: styles, room rules, and prompt discipline."""

from __future__ import annotations

STYLE_PROFILES: dict[str, dict] = {
    "Warm Minimal Luxury": {
        "palette": ["warm ivory", "soft taupe", "champagne", "walnut"],
        "lighting": "layered warm ambient lighting, soft accent glow, no harsh spots",
        "materials": ["matte plaster", "light oak", "brushed brass", "linen"],
        "mood": "calm, elevated, quietly luxurious",
        "furniture_language": "low-profile refined pieces, generous negative space, soft textiles",
        "must_have": ["warm layered lighting", "clean surfaces", "one statement soft seating piece"],
        "never": ["clutter", "neon colours", "busy patterns", "cold blue LED"],
        "tint": (214, 184, 148),
        "brightness": 1.1,
        "contrast": 1.06,
        "color": 1.14,
        "warmth": 0.2,
        "redesign_strength": 0.62,
    },
    "Scandinavian": {
        "palette": ["soft white", "pale oak", "muted sage", "light grey"],
        "lighting": "bright natural daylight with clean pendant accents",
        "materials": ["light wood", "wool", "cotton", "matte white paint"],
        "mood": "airy, simple, and softly organic",
        "furniture_language": "light wood furniture, airy layouts, functional simplicity",
        "must_have": ["light wood accents", "uncluttered floor", "soft natural textiles"],
        "never": ["dark heavy furniture", "ornate carving", "saturated reds"],
        "tint": (220, 228, 218),
        "brightness": 1.16,
        "contrast": 0.98,
        "color": 0.9,
        "warmth": 0.07,
        "redesign_strength": 0.58,
    },
    "Japandi": {
        "palette": ["warm beige", "charcoal", "stone", "soft clay"],
        "lighting": "soft diffused daylight and low warm lamps",
        "materials": ["ash wood", "paper", "stone", "raw textiles"],
        "mood": "grounded, serene, and intentionally spare",
        "furniture_language": "low furniture, balanced asymmetry, tactile natural materials",
        "must_have": ["low seating or bed profile", "natural wood", "calm empty floor zones"],
        "never": ["glossy plastic", "maximal decor", "cool fluorescent light"],
        "tint": (210, 196, 178),
        "brightness": 1.05,
        "contrast": 1.1,
        "color": 0.94,
        "warmth": 0.14,
        "redesign_strength": 0.64,
    },
    "Modern Contemporary": {
        "palette": ["graphite", "ivory", "slate", "matte black"],
        "lighting": "crisp architectural lighting with focused highlights",
        "materials": ["glass", "concrete", "polished wood", "steel"],
        "mood": "clean, structured, and quietly bold",
        "furniture_language": "geometric silhouettes, strong lines, restrained accents",
        "must_have": ["clean lines", "structured composition", "focused accent lighting"],
        "never": ["rustic clutter", "floral overload", "mismatched finishes"],
        "tint": (180, 188, 198),
        "brightness": 1.07,
        "contrast": 1.16,
        "color": 0.88,
        "warmth": 0.03,
        "redesign_strength": 0.66,
    },
    "Coastal Calm": {
        "palette": ["sea salt", "soft blue", "sand", "driftwood"],
        "lighting": "breezy daylight with pale reflective surfaces",
        "materials": ["washed wood", "linen", "rattan", "matte ceramic"],
        "mood": "fresh, open, and gently coastal",
        "furniture_language": "relaxed seating, light fabrics, organic textures",
        "must_have": ["light fabrics", "airiness", "soft blue or sand accents"],
        "never": ["heavy dark walls", "industrial steel dominance"],
        "tint": (186, 210, 220),
        "brightness": 1.14,
        "contrast": 1.0,
        "color": 1.08,
        "warmth": 0.05,
        "redesign_strength": 0.6,
    },
    "Indian Contemporary": {
        "palette": ["ivory", "terracotta", "mustard", "deep teak"],
        "lighting": "warm ambient wash with brass accent points",
        "materials": ["teak", "cane", "cotton", "handmade ceramics"],
        "mood": "grounded, hospitable, and richly lived-in",
        "furniture_language": "warm wood furniture, cane accents, lived-in comfort",
        "must_have": ["warm wood", "brass or cane detail", "inviting seating"],
        "never": ["cold minimal sterility", "pure white-only rooms"],
        "tint": (208, 164, 120),
        "brightness": 1.06,
        "contrast": 1.12,
        "color": 1.2,
        "warmth": 0.24,
        "redesign_strength": 0.68,
    },
}

ROOM_PLAYBOOKS: dict[str, dict] = {
    "Bedroom": {
        "anchors": ["bed", "wardrobe", "windows", "ceiling line"],
        "default_add": ["bedside lighting", "soft rug", "calmer wall treatment"],
        "default_remove": ["visual clutter", "harsh overhead-only lighting"],
        "layout": "keep bed wall orientation, improve bedside balance, leave clear walkways",
        "scale_rules": "king/queen bed scaled to room width, wardrobe along longest free wall",
    },
    "Living Room": {
        "anchors": ["sofa wall", "windows", "TV wall", "circulation paths"],
        "default_add": ["layered lighting", "coffee table", "accent chair"],
        "default_remove": ["crowded furniture", "cable clutter"],
        "layout": "conversation-focused seating, clear path through the room",
        "scale_rules": "sofa against main wall, leave 30-36 inch circulation where possible",
    },
    "Kitchen": {
        "anchors": ["counters", "cabinets", "sink wall", "windows"],
        "default_add": ["under-cabinet lighting", "clearer work triangle"],
        "default_remove": ["countertop clutter", "mismatched storage"],
        "layout": "preserve wet and cooking zones, improve storage clarity",
        "scale_rules": "keep appliance locations stable unless redesign explicitly asks",
    },
    "Bathroom": {
        "anchors": ["vanity", "wet area", "mirror wall"],
        "default_add": ["softer vanity lighting", "cleaner storage"],
        "default_remove": ["visual clutter", "dated accessories"],
        "layout": "keep plumbing walls fixed, elevate finishes and lighting",
        "scale_rules": "do not invent impossible plumbing moves",
    },
    "Balcony": {
        "anchors": ["railing", "floor plane", "outdoor view direction"],
        "default_add": ["compact seating", "planters", "warm outdoor lighting"],
        "default_remove": ["storage clutter"],
        "layout": "keep open edge and view, add compact lounge zone",
        "scale_rules": "use slim furniture that preserves movement",
    },
    "Other": {
        "anchors": ["windows", "main walls", "circulation"],
        "default_add": ["better lighting", "clearer focal point"],
        "default_remove": ["visual clutter"],
        "layout": "preserve room geometry and improve function",
        "scale_rules": "keep furniture proportional to room size",
    },
}

STYLE_ALIASES = {
    "warm minimal": "Warm Minimal Luxury",
    "minimal luxury": "Warm Minimal Luxury",
    "luxury minimal": "Warm Minimal Luxury",
    "scandi": "Scandinavian",
    "scandinavian": "Scandinavian",
    "japandi": "Japandi",
    "japanese": "Japandi",
    "zen": "Japandi",
    "modern": "Modern Contemporary",
    "contemporary": "Modern Contemporary",
    "coastal": "Coastal Calm",
    "beach": "Coastal Calm",
    "indian": "Indian Contemporary",
    "indian contemporary": "Indian Contemporary",
}


def resolve_style(raw_style: str | None) -> str:
    if not raw_style:
        return "Warm Minimal Luxury"
    cleaned = raw_style.strip()
    if cleaned in STYLE_PROFILES:
        return cleaned
    lowered = cleaned.lower()
    for alias, style in STYLE_ALIASES.items():
        if alias in lowered:
            return style
    return "Warm Minimal Luxury"


def get_style_profile(style: str | None) -> dict:
    resolved = resolve_style(style)
    return STYLE_PROFILES[resolved] | {"name": resolved}


def get_room_playbook(room_type: str | None) -> dict:
    key = (room_type or "Other").strip()
    return ROOM_PLAYBOOKS.get(key, ROOM_PLAYBOOKS["Other"]) | {"room_type": key or "Other"}


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def normalize_requirements(
    room: dict,
    requirements: dict | None,
    *,
    for_render: bool = False,
) -> dict:
    """Sanitize a design brief.

    Stored/display briefs (for_render=False) keep ONLY what the user or LLM set —
    never invent coffee tables, accent chairs, or playbook defaults into MongoDB.

    for_render=True adds structure anchors + avoid-list guardrails for the image
    model only; it still does not invent unrequested furniture adds.
    """
    requirements = dict(requirements or {})
    playbook = get_room_playbook(room.get("room_type") or requirements.get("room"))
    style = resolve_style(
        requirements.get("style")
        or ("Warm Minimal Luxury" if room.get("match_home_style", True) else "Japandi")
    )
    profile = get_style_profile(style)

    keep = _unique(list(requirements.get("keep") or []))
    remove = _unique(list(requirements.get("remove") or []))
    add = _unique(list(requirements.get("add") or []))
    colours = _unique(list(requirements.get("colours") or []))
    avoid = _unique(list(requirements.get("avoid") or []))
    notes = _unique(list(requirements.get("notes") or []))[:4]

    if for_render:
        keep = _unique([*keep, *playbook["anchors"]])
        if not colours:
            colours = _unique(profile["palette"][:3])
        avoid = _unique(
            [
                *avoid,
                *profile["never"][:3],
                "people",
                "faces",
                "portraits",
                "human figures",
                "different room layout",
                "new windows",
                "moved walls",
                "changed camera angle",
                "new ceiling beams",
                "different floor material unless requested",
            ]
        )

    remove_keys = {item.lower() for item in remove}
    keep = [item for item in keep if item.lower() not in remove_keys]

    return {
        "room": playbook["room_type"],
        "style": style,
        "budget": int(requirements.get("budget") or 80000),
        "keep": keep[:8],
        "remove": remove[:8],
        "add": add[:8],
        "colours": colours[:5],
        "avoid": avoid[:8],
        "notes": notes,
    }


def build_generation_prompt(
    room: dict,
    requirements: dict | None,
    revision_note: str | None = None,
) -> str:
    from app.services.design_brief import build_design_brief, build_edit_prompt

    return build_edit_prompt(build_design_brief(room, requirements, revision_note))


def build_negative_prompt(requirements: dict | None = None) -> str:
    from app.services.design_brief import DesignBrief, build_negative_constraints

    brief = DesignBrief(
        room_type="Room",
        target_style="Warm Minimal Luxury",
        keep_objects=list((requirements or {}).get("keep") or []),
        remove_objects=list((requirements or {}).get("remove") or []),
        replace_or_add=list((requirements or {}).get("add") or []),
        palette=list((requirements or {}).get("colours") or []),
    )
    return build_negative_constraints(brief)
