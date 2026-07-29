"""Conversation agent that extracts design requirements from user chat."""

from __future__ import annotations

import re
from copy import deepcopy

from app.services.design_knowledge import STYLE_ALIASES, resolve_style


LIST_PATTERNS = {
    "keep": re.compile(
        r"(?:keep|preserve|retain)\s+(?:the\s+)?([a-zA-Z][\w\s\-]{1,40}?)(?=(?:,|\.|$|\band\b|\bthen\b|\bremove\b|\breplace\b|\badd\b|\bbudget\b|\bmake\b|\bstyle\b))",
        re.IGNORECASE,
    ),
    "remove": re.compile(
        r"(?:remove|replace|get rid of|take out)\s+(?:the\s+)?([a-zA-Z][\w\s\-]{1,40}?)(?=(?:,|\.|$|\band\b|\bthen\b|\bkeep\b|\badd\b|\bbudget\b|\bmake\b|\bstyle\b))",
        re.IGNORECASE,
    ),
    "add": re.compile(
        r"(?:add|introduce|include)\s+(?:a\s+|an\s+|some\s+)?([a-zA-Z][\w\s\-]{1,40}?)(?=(?:,|\.|$|\band\b|\bthen\b|\bkeep\b|\bremove\b|\bbudget\b|\bmake\b|\bstyle\b))",
        re.IGNORECASE,
    ),
    "avoid": re.compile(
        r"(?:avoid|without)\s+(?:the\s+)?([a-zA-Z][\w\s\-]{1,40}?)(?=(?:,|\.|$|\band\b|\bthen\b|\bkeep\b|\bremove\b|\badd\b|\bbudget\b))",
        re.IGNORECASE,
    ),
}

BUDGET_PATTERN = re.compile(
    r"(?:budget|spend|around|upto|up to)\s*(?:of\s*|is\s*|about\s*)?(?:₹|rs\.?\s*|inr\s*)?([\d,]+)",
    re.IGNORECASE,
)

COLOUR_PATTERN = re.compile(
    r"(?:colour|color|palette|tones?)\s*(?:of|:)?\s*(.+?)(?:\.|$)",
    re.IGNORECASE,
)


def _split_items(raw: str) -> list[str]:
    cleaned = re.sub(r"\b(and|with|plus)\b", ",", raw, flags=re.IGNORECASE)
    items = [item.strip(" .") for item in cleaned.split(",")]
    return [item for item in items if 2 <= len(item) <= 48]


def _merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for item in [*existing, *incoming]:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged[:8]


def extract_requirement_updates(message: str, current: dict) -> dict:
    updated = deepcopy(current)
    lowered = message.lower()

    for alias, style in STYLE_ALIASES.items():
        if alias in lowered:
            updated["style"] = style
            break

    for field, pattern in LIST_PATTERNS.items():
        matches = pattern.findall(message)
        values: list[str] = []
        for match in matches:
            values.extend(_split_items(match))
        if values:
            updated[field] = _merge_unique(updated.get(field, []), values)

    colour_match = COLOUR_PATTERN.search(message)
    if colour_match:
        colours = _split_items(colour_match.group(1))
        if colours:
            updated["colours"] = _merge_unique(updated.get("colours", []), colours)

    budget_match = BUDGET_PATTERN.search(message)
    if budget_match:
        try:
            updated["budget"] = int(budget_match.group(1).replace(",", ""))
        except ValueError:
            pass

    note_candidates = [
        sentence.strip()
        for sentence in re.split(r"[.!?]\s+", message)
        if len(sentence.strip()) > 18
    ]
    if note_candidates:
        updated["notes"] = _merge_unique(updated.get("notes", []), note_candidates[:2])

    updated["style"] = resolve_style(updated.get("style"))
    return updated


def build_assistant_reply(room_type: str, requirements: dict, previous: dict) -> str:
    changes: list[str] = []
    if requirements.get("style") != previous.get("style"):
        changes.append(f"style toward {requirements['style']}")
    for key, label in (
        ("keep", "keeping"),
        ("remove", "removing"),
        ("add", "adding"),
        ("colours", "palette"),
        ("avoid", "avoiding"),
    ):
        before = set(map(str.lower, previous.get(key, [])))
        after = requirements.get(key, [])
        newly = [item for item in after if item.lower() not in before]
        if newly:
            changes.append(f"{label} {', '.join(newly[:3])}")
    if requirements.get("budget") != previous.get("budget"):
        changes.append(f"budget around Rs {requirements.get('budget', 0):,}")

    if not changes:
        return (
            f"I've noted that for your {room_type.lower()}. "
            "Tell me what to keep, remove, add, the style, or your budget, "
            "and I'll tighten the design plan."
        )

    summary = "; ".join(changes)
    return (
        f"Understood for your {room_type.lower()}: {summary}. "
        "I've updated the requirement plan accordingly. "
        "You can keep chatting or review the design plan when ready."
    )
