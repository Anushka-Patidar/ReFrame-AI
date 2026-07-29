"""Constraint engine — explicit KEEP/REMOVE/REPLACE/ADD/style/color/architecture rules."""

from __future__ import annotations

from app.services.design_brief import DesignBrief
from app.services.pipeline.types import ConstraintKind, ConstraintSet, DesignConstraint, RoomAnalysis


def build_constraints(
    brief: DesignBrief,
    room_analysis: RoomAnalysis | None = None,
) -> ConstraintSet:
    items: list[DesignConstraint] = []

    for anchor in brief.preserve_architecture or [
        "room geometry and proportions",
        "camera viewpoint and perspective",
        "windows and permanent openings",
        "ceiling and floor boundaries",
        "structural walls and columns",
    ]:
        items.append(
            DesignConstraint(
                kind=ConstraintKind.ARCHITECTURE_LOCKED,
                target=anchor,
                detail="Must remain recognizable after redesign.",
            )
        )

    for target in brief.keep_objects:
        items.append(DesignConstraint(kind=ConstraintKind.OBJECT_KEEP, target=target))

    for target in brief.remove_objects:
        items.append(DesignConstraint(kind=ConstraintKind.OBJECT_REMOVE, target=target))

    # Items listed as add may replace removed furniture — mark REPLACE when overlapping types.
    remove_keys = {item.lower() for item in brief.remove_objects}
    for target in brief.replace_or_add:
        kind = ConstraintKind.OBJECT_REPLACE if _looks_like_replacement(target, remove_keys) else ConstraintKind.OBJECT_ADD
        items.append(DesignConstraint(kind=kind, target=target))

    if brief.change_targets:
        for target in brief.change_targets:
            items.append(
                DesignConstraint(
                    kind=ConstraintKind.OBJECT_REPLACE,
                    target=target,
                    detail="User-marked CHANGE target.",
                )
            )

    if brief.target_style:
        items.append(
            DesignConstraint(
                kind=ConstraintKind.STYLE_CONSTRAINT,
                target=brief.target_style,
                detail=brief.mood or None,
            )
        )

    for color in brief.palette:
        items.append(DesignConstraint(kind=ConstraintKind.COLOR_CONSTRAINT, target=color))

    # Enrich from room analysis statuses when present.
    if room_analysis:
        for obj in room_analysis.objects:
            if obj.status == "keep" and obj.type.lower() not in {t.lower() for t in brief.keep_objects}:
                items.append(DesignConstraint(kind=ConstraintKind.OBJECT_KEEP, target=obj.type))
            if obj.status == "remove" and obj.type.lower() not in remove_keys:
                items.append(DesignConstraint(kind=ConstraintKind.OBJECT_REMOVE, target=obj.type))

    return ConstraintSet(items=_dedupe(items))


def _looks_like_replacement(add_item: str, remove_keys: set[str]) -> bool:
    tokens = {token for token in add_item.lower().replace("-", " ").split() if len(token) > 2}
    furniture = {"sofa", "couch", "table", "chair", "bed", "wardrobe", "tv", "cabinet", "rug"}
    if tokens & furniture and any(any(tok in removed for tok in tokens) for removed in remove_keys):
        return True
    return False


def _dedupe(items: list[DesignConstraint]) -> list[DesignConstraint]:
    seen: set[tuple[str, str]] = set()
    result: list[DesignConstraint] = []
    for item in items:
        key = (item.kind.value, item.target.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
