"""RoomUnderstanding — user-assisted now, vision-ready later."""

from __future__ import annotations

from app.services.pipeline.types import (
    AnalysisSource,
    ArchitectureFeatures,
    RoomAnalysis,
    RoomObject,
)


def analyze_room(
    room: dict,
    requirements: dict | None = None,
    *,
    existing_analysis: dict | None = None,
) -> RoomAnalysis:
    """Build a RoomAnalysis from user/requirements data.

    Automatic vision analysis can replace/enrich this later without changing callers.
    """
    requirements = dict(requirements or {})
    if existing_analysis:
        return _from_stored(existing_analysis)

    room_type = (requirements.get("room") or room.get("room_type") or "Living Room").strip()
    objects: list[RoomObject] = []
    index = 1

    def _add(label: str, status: str) -> None:
        nonlocal index
        cleaned = label.strip()
        if not cleaned:
            return
        objects.append(
            RoomObject(
                id=f"object_{index:02d}",
                type=cleaned,
                status=status,
                source=AnalysisSource.USER.value,
            )
        )
        index += 1

    for item in requirements.get("keep") or []:
        _add(str(item), "keep")
    for item in requirements.get("remove") or []:
        _add(str(item), "remove")
    for item in requirements.get("add") or []:
        _add(str(item), "add")

    # Heuristic architecture placeholders — not inventing detections from the photo.
    architecture = ArchitectureFeatures(
        doors=["door"] if any("door" in str(x).lower() for x in (requirements.get("keep") or [])) else [],
        windows=[],
        walls=["structural walls"],
        ceiling="preserve ceiling geometry",
        floor="preserve floor boundaries",
    )

    return RoomAnalysis(
        room_type=room_type,
        architecture=architecture,
        objects=objects,
        lighting=[],
        decor=[str(x) for x in (requirements.get("colours") or [])[:4]],
        source=AnalysisSource.USER.value,
        notes="User/requirements-derived analysis. Automatic vision not configured.",
    )


def _from_stored(payload: dict) -> RoomAnalysis:
    arch = payload.get("architecture") or {}
    objects = [
        RoomObject(
            id=str(item.get("id") or f"object_{i:02d}"),
            type=str(item.get("type") or "unknown"),
            status=str(item.get("status") or "existing"),
            source=str(item.get("source") or AnalysisSource.USER.value),
            confidence=item.get("confidence"),
            bounding_box=tuple(item["bounding_box"]) if item.get("bounding_box") else None,
            notes=item.get("notes"),
        )
        for i, item in enumerate(payload.get("objects") or [], start=1)
    ]
    return RoomAnalysis(
        room_type=str(payload.get("room_type") or "Living Room"),
        architecture=ArchitectureFeatures(
            doors=list(arch.get("doors") or []),
            windows=list(arch.get("windows") or []),
            walls=list(arch.get("walls") or []),
            ceiling=arch.get("ceiling"),
            floor=arch.get("floor"),
        ),
        objects=objects,
        lighting=list(payload.get("lighting") or []),
        decor=list(payload.get("decor") or []),
        source=str(payload.get("source") or AnalysisSource.USER.value),
        notes=payload.get("notes"),
    )
