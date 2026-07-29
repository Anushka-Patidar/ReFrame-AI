from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.api.deps import get_current_user
from app.db.database import get_database
from app.models.collections import (
    DESIGN_CONVERSATIONS,
    DESIGN_MEMORY,
    DESIGN_REQUIREMENTS,
    DESIGN_VERSIONS,
    GENERATION_EVENTS,
    ROOMS,
    REGION_CONSTRAINTS,
)
from app.schemas.common import ApiMessage
from app.schemas.room import (
    ChatMessage,
    DesignRequirements,
    DesignVersionRead,
    RoomCreate,
    RoomRead,
    SpaceCheckResponse,
    SpaceCheckItem,
)
from app.schemas.region_constraints import RegionConstraintRead, RegionAction
from app.services.design_brief import build_design_brief
from app.services.design_knowledge import normalize_requirements, resolve_style
from app.services.image_generation import (
    GenerationBusyError,
    InsufficientTransformError,
    RoomImageMissingError,
    generate_design_image,
)
from app.services.llm_design_agent import run_design_agent
from app.services.media import UPLOADS_ROOT, save_mask_upload, save_room_upload
from app.services.mongo import object_id, serialize_id, utc_now

router = APIRouter(prefix="/rooms", tags=["rooms"])


def _join_items(items: list[str], fallback: str) -> str:
    cleaned = [item.strip() for item in items if item.strip()]
    return ", ".join(cleaned[:3]) if cleaned else fallback


def _build_generation_note(room: dict, requirements: dict | None, engine: str | None = None) -> str:
    brief = build_design_brief(room, requirements)
    keep = _join_items(brief.keep_objects, "architecture only")
    remove = _join_items(brief.remove_objects, "nothing major")
    add = _join_items(brief.replace_or_add, "style refinements")
    colours = _join_items(brief.palette, "style palette")
    note = (
        f"{brief.target_style} redesign for the {brief.room_type.lower()} "
        f"(strength={brief.transformation_strength}) keeping {keep}, "
        f"removing {remove}, adding {add}, and using {colours}."
    )
    if engine and engine.startswith("local:"):
        note += " Generated locally from your uploaded room photo."
    return note


async def _run_image_generation(
    room: dict,
    requirements: dict,
    revision_note: str | None = None,
    memory_document: dict | None = None,
) -> tuple[str, str, dict]:
    try:
        return await generate_design_image(
            room,
            requirements,
            revision_note,
            memory_document=memory_document,
        )
    except RoomImageMissingError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except GenerationBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except InsufficientTransformError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc) or "Local generation couldn't complete. Please retry.",
        ) from exc


async def _load_design_memory(user_id: ObjectId) -> dict | None:
    return await get_database()[DESIGN_MEMORY].find_one({"user_id": user_id})


async def _upsert_design_memory(user_id: ObjectId, memory_payload: dict) -> None:
    await get_database()[DESIGN_MEMORY].update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id": user_id,
                "design_memory": memory_payload,
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )


async def _persist_generation_event(
    *,
    user_id: ObjectId,
    room_id: ObjectId,
    design_version_id: ObjectId,
    metadata: dict,
) -> None:
    """Store generation audit metadata. training_consent stays False by default."""
    await get_database()[GENERATION_EVENTS].insert_one(
        {
            "user_id": user_id,
            "room_id": room_id,
            "design_version_id": design_version_id,
            "generation_id": metadata.get("generation_id"),
            "source_image_url": metadata.get("source_image_url"),
            "design_brief": metadata.get("design_brief"),
            "constraints": metadata.get("constraints"),
            "generated_image_meta": {
                "model": metadata.get("model"),
                "model_configuration": metadata.get("model_configuration"),
                "seed": metadata.get("seed"),
                "provider": metadata.get("provider"),
                "attempts": metadata.get("attempts"),
            },
            "validation": metadata.get("validation"),
            "user_accepted": metadata.get("user_accepted"),
            "user_rejected": metadata.get("user_rejected"),
            "user_feedback": metadata.get("user_feedback"),
            "training_consent": bool(metadata.get("training_consent", False)),
            "created_at": utc_now(),
        }
    )

def _public_media_url(request: Request, relative_path: str) -> str:
    return str(request.base_url).rstrip("/") + f"/media/{relative_path}"


async def _stored_requirements(room: dict) -> dict:
    """Load the user/LLM brief as stored — do not invent playbook furniture."""
    document = await get_database()[DESIGN_REQUIREMENTS].find_one({"room_id": room["_id"]})
    raw = {
        "room": (document or {}).get("room", room["room_type"]),
        "style": (document or {}).get("style"),
        "budget": (document or {}).get("budget", 80000),
        "keep": (document or {}).get("keep", []),
        "remove": (document or {}).get("remove", []),
        "add": (document or {}).get("add", []),
        "change": (document or {}).get("change", []),
        "colours": (document or {}).get("colours", []),
        "avoid": (document or {}).get("avoid", []),
        "notes": (document or {}).get("notes", []),
    }
    return normalize_requirements(room, raw)


def _initial_requirements(room_type: str, match_home_style: bool) -> dict:
    return normalize_requirements(
        {"room_type": room_type, "match_home_style": match_home_style},
        {
            "style": "Warm Minimal Luxury" if match_home_style else "Japandi",
            "budget": 80000,
            "keep": [],
            "remove": [],
            "add": [],
            "colours": [],
            "avoid": [],
            "notes": [],
        },
    )


@router.post("", response_model=RoomRead)
async def create_room(
    payload: RoomCreate,
    current_user: dict = Depends(get_current_user),
) -> RoomRead:
    db = get_database()
    room_document = {
        "user_id": ObjectId(current_user["id"]),
        "room_type": payload.room_type,
        "dimensions": payload.dimensions.model_dump(),
        "original_image_url": payload.original_image_url,
        "match_home_style": payload.match_home_style,
        "status": "Designing",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    result = await db[ROOMS].insert_one(room_document)

    await db[DESIGN_REQUIREMENTS].insert_one(
        {
            "room_id": result.inserted_id,
            **_initial_requirements(payload.room_type, payload.match_home_style),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
    )
    await db[DESIGN_CONVERSATIONS].insert_one(
        {"room_id": result.inserted_id, "messages": [], "created_at": utc_now()}
    )

    document = serialize_id(await db[ROOMS].find_one({"_id": result.inserted_id}))
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load created room.",
        )

    document["user_id"] = str(document["user_id"])
    return RoomRead(**document)


@router.get("", response_model=list[RoomRead])
async def list_rooms(current_user: dict = Depends(get_current_user)) -> list[RoomRead]:
    cursor = get_database()[ROOMS].find({"user_id": ObjectId(current_user["id"])})
    rooms: list[RoomRead] = []
    async for document in cursor:
        room_document = serialize_id(document)
        if room_document is None:
            continue
        room_document["user_id"] = str(room_document["user_id"])
        rooms.append(RoomRead(**room_document))
    return rooms


@router.get("/{room_id}", response_model=RoomRead)
async def get_room_detail(
    room_id: str,
    current_user: dict = Depends(get_current_user),
) -> RoomRead:
    document = await get_database()[ROOMS].find_one(
        {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])}
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )
    room_document = serialize_id(document)
    if room_document is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load room.",
        )
    room_document["user_id"] = str(room_document["user_id"])
    return RoomRead(**room_document)


@router.post("/{room_id}/upload", response_model=RoomRead)
async def upload_room_image(
    room_id: str,
    request: Request,
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> RoomRead:
    filename = await save_room_upload(image)
    image_url = str(request.base_url).rstrip("/") + f"/media/rooms/{filename}"
    result = await get_database()[ROOMS].update_one(
        {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])},
        {
            "$set": {
                "original_image_url": image_url,
                "updated_at": utc_now(),
            }
        },
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )
    document = serialize_id(
        await get_database()[ROOMS].find_one(
            {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])}
        )
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load updated room.",
        )
    document["user_id"] = str(document["user_id"])
    return RoomRead(**document)


@router.post("/{room_id}/chat", response_model=list[ChatMessage])
async def room_chat(
    room_id: str,
    message: ChatMessage,
    current_user: dict = Depends(get_current_user),
) -> list[ChatMessage]:
    db = get_database()
    room = await db[ROOMS].find_one(
        {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])}
    )
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )

    previous = await _stored_requirements(room)
    updated, reply_text, agent_engine = await run_design_agent(
        room,
        message.content,
        previous,
    )
    await db[DESIGN_REQUIREMENTS].update_one(
        {"room_id": room["_id"]},
        {
            "$set": {
                **updated,
                "room_id": room["_id"],
                "updated_at": utc_now(),
                "agent_engine": agent_engine,
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )

    reply = ChatMessage(
        role="assistant",
        content=reply_text,
    )
    await db[DESIGN_CONVERSATIONS].update_one(
        {"room_id": room["_id"]},
        {
            "$push": {
                "messages": {
                    "$each": [
                        {**message.model_dump(), "created_at": utc_now()},
                        {**reply.model_dump(), "created_at": utc_now()},
                    ]
                }
            }
        },
        upsert=True,
    )
    return [message, reply]


@router.get("/{room_id}/conversation", response_model=list[ChatMessage])
async def room_conversation(
    room_id: str,
    current_user: dict = Depends(get_current_user),
) -> list[ChatMessage]:
    db = get_database()
    room = await db[ROOMS].find_one(
        {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])}
    )
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )
    conversation = await db[DESIGN_CONVERSATIONS].find_one({"room_id": room["_id"]})
    messages = (conversation or {}).get("messages") or []
    return [
        ChatMessage(role=str(item.get("role", "assistant")), content=str(item.get("content", "")))
        for item in messages
        if item.get("content")
    ]


@router.get("/{room_id}/requirements", response_model=DesignRequirements)
async def room_requirements(
    room_id: str,
    current_user: dict = Depends(get_current_user),
) -> DesignRequirements:
    room = await get_database()[ROOMS].find_one(
        {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])}
    )
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )

    brief = await _stored_requirements(room)
    return DesignRequirements(**brief)


@router.put("/{room_id}/requirements", response_model=ApiMessage)
async def update_requirements(
    room_id: str,
    payload: DesignRequirements,
    current_user: dict = Depends(get_current_user),
) -> ApiMessage:
    room = await get_database()[ROOMS].find_one(
        {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])}
    )
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )
    brief = normalize_requirements(room, payload.model_dump())
    await get_database()[DESIGN_REQUIREMENTS].update_one(
        {"room_id": room["_id"]},
        {
            "$set": {
                **brief,
                "room_id": room["_id"],
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )
    return ApiMessage(message="Design requirements updated.")


@router.get("/{room_id}/region-constraints", response_model=list[RegionConstraintRead])
async def list_region_constraints(
    room_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> list[RegionConstraintRead]:
    room_object_id = object_id(room_id)
    cursor = get_database()[REGION_CONSTRAINTS].find(
        {"room_id": room_object_id, "user_id": ObjectId(current_user["id"])}
    )
    results: list[RegionConstraintRead] = []
    async for doc in cursor:
        serialized = serialize_id(doc)
        if serialized is None:
            continue
        mask_path = str(serialized.get("mask_path") or "")
        mask_url = _public_media_url(request, mask_path)
        results.append(
            RegionConstraintRead(
                id=str(serialized["id"]),
                action=str(serialized.get("action") or "CHANGE").upper(),  # type: ignore[arg-type]
                label=str(serialized.get("label") or ""),
                mask_url=mask_url,
                image_width=int(serialized.get("image_width") or 0),
                image_height=int(serialized.get("image_height") or 0),
                created_at=serialized.get("created_at"),  # type: ignore[arg-type]
            )
        )
    return results


@router.post("/{room_id}/region-constraints", response_model=RegionConstraintRead)
async def create_region_constraint(
    room_id: str,
    request: Request,
    action: RegionAction = Form(...),
    label: str = Form(...),
    image_width: int = Form(...),
    image_height: int = Form(...),
    mask: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> RegionConstraintRead:
    room_object_id = object_id(room_id)
    user_object_id = ObjectId(current_user["id"])

    room = await get_database()[ROOMS].find_one({"_id": room_object_id, "user_id": user_object_id})
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found.")

    mask_path = await save_mask_upload(mask, room_id=room_id)
    mask_url = _public_media_url(request, mask_path)
    now = utc_now()

    doc = {
        "user_id": user_object_id,
        "room_id": room_object_id,
        "action": action,
        "label": label.strip()[:80],
        "mask_path": mask_path,
        "image_width": int(image_width),
        "image_height": int(image_height),
        "created_at": now,
        "updated_at": now,
    }
    result = await get_database()[REGION_CONSTRAINTS].insert_one(doc)
    return RegionConstraintRead(
        id=str(result.inserted_id),
        action=action,
        label=doc["label"],
        mask_url=mask_url,
        image_width=doc["image_width"],
        image_height=doc["image_height"],
        created_at=doc["created_at"],
    )


@router.delete("/{room_id}/region-constraints/{constraint_id}", response_model=ApiMessage)
async def delete_region_constraint(
    room_id: str,
    constraint_id: str,
    current_user: dict = Depends(get_current_user),
) -> ApiMessage:
    room_object_id = object_id(room_id)
    constraint_object_id = object_id(constraint_id)
    user_object_id = ObjectId(current_user["id"])

    db = get_database()
    doc = await db[REGION_CONSTRAINTS].find_one(
        {"_id": constraint_object_id, "room_id": room_object_id, "user_id": user_object_id}
    )
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Region constraint not found.")

    await db[REGION_CONSTRAINTS].delete_one(
        {"_id": constraint_object_id, "room_id": room_object_id, "user_id": user_object_id}
    )

    # Best-effort local cleanup.
    try:
        mask_path = str(doc.get("mask_path") or "")
        if mask_path:
            (UPLOADS_ROOT / mask_path).unlink(missing_ok=True)
    except Exception:
        pass

    return ApiMessage(message="Region constraint deleted.")


@router.post("/{room_id}/space-check", response_model=SpaceCheckResponse)
async def space_check(
    room_id: str,
    current_user: dict = Depends(get_current_user),
) -> SpaceCheckResponse:
    room = await get_database()[ROOMS].find_one(
        {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])}
    )
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )

    dimensions = room["dimensions"]
    room_area = dimensions["length"] * dimensions["width"]
    checks = [
        SpaceCheckItem(
            item="King bed",
            status="fits",
            note="Fits comfortably in the available layout.",
        ),
        SpaceCheckItem(
            item="Wardrobe",
            status="fits",
            note="Placement works along a main wall.",
        ),
    ]
    if room_area < 180:
        checks.append(
            SpaceCheckItem(
                item="Sofa",
                status="tight",
                note="May reduce walking space in the current room size.",
            )
        )
        recommendation = "Consider an accent chair instead of a full sofa."
    else:
        checks.append(
            SpaceCheckItem(
                item="Sofa",
                status="fits",
                note="Can fit while preserving circulation space.",
            )
        )
        recommendation = "The room can handle a small sofa with careful placement."

    return SpaceCheckResponse(
        room_size=f"{dimensions['length']} x {dimensions['width']} ft",
        checks=checks,
        recommendation=recommendation,
    )


@router.post("/{room_id}/generate", response_model=DesignVersionRead)
async def generate_design(
    room_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> DesignVersionRead:
    db = get_database()
    room = await db[ROOMS].find_one(
        {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])}
    )
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )
    requirements = await _stored_requirements(room)
    memory_document = await _load_design_memory(ObjectId(current_user["id"]))

    relative_path, engine, metadata = await _run_image_generation(
        room,
        requirements,
        memory_document=memory_document,
    )
    image_url = _public_media_url(request, relative_path)

    count = await db[DESIGN_VERSIONS].count_documents({"room_id": room["_id"]})
    version_number = count + 1
    style = resolve_style(requirements.get("style"))
    version_document = {
        "room_id": room["_id"],
        "version": f"V{version_number}",
        "title": (
            f"{style} {room['room_type']} Concept"
            if version_number == 1
            else f"{style} Revision {version_number}"
        ),
        "note": _build_generation_note(room, requirements, engine),
        "image_url": image_url,
        "engine": engine,
        "pipeline_metadata": metadata,
        "validation": (metadata or {}).get("validation"),
        "is_finalized": False,
        "created_at": utc_now(),
    }
    result = await db[DESIGN_VERSIONS].insert_one(version_document)
    await _persist_generation_event(
        user_id=ObjectId(current_user["id"]),
        room_id=room["_id"],
        design_version_id=result.inserted_id,
        metadata=metadata,
    )
    if metadata.get("design_brief"):
        from app.services.pipeline.design_memory import (
            memory_from_document,
            merge_memory_from_requirements,
        )

        memory = merge_memory_from_requirements(
            memory_from_document(memory_document),
            requirements,
        )
        await _upsert_design_memory(ObjectId(current_user["id"]), memory.to_dict())
    await db[ROOMS].update_one(
        {"_id": room["_id"]},
        {"$set": {"status": "Generated", "updated_at": utc_now()}},
    )
    created = serialize_id(await db[DESIGN_VERSIONS].find_one({"_id": result.inserted_id}))
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load generated design.",
        )
    created["room_id"] = str(created["room_id"])
    return DesignVersionRead(**created)


@router.get("/{room_id}/designs", response_model=list[DesignVersionRead])
async def room_designs(
    room_id: str,
    current_user: dict = Depends(get_current_user),
) -> list[DesignVersionRead]:
    room = await get_database()[ROOMS].find_one(
        {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])}
    )
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )
    cursor = get_database()[DESIGN_VERSIONS].find({"room_id": room["_id"]}).sort("created_at", 1)
    versions: list[DesignVersionRead] = []
    async for document in cursor:
        version_document = serialize_id(document)
        if version_document is None:
            continue
        version_document["room_id"] = str(version_document["room_id"])
        versions.append(DesignVersionRead(**version_document))
    return versions


@router.post("/{room_id}/designs/{design_id}/revise", response_model=DesignVersionRead)
async def revise_design(
    room_id: str,
    design_id: str,
    message: ChatMessage,
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> DesignVersionRead:
    db = get_database()
    room = await db[ROOMS].find_one(
        {"_id": object_id(room_id), "user_id": ObjectId(current_user["id"])}
    )
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )
    original_design = await db[DESIGN_VERSIONS].find_one(
        {"_id": object_id(design_id), "room_id": room["_id"]}
    )
    if original_design is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design version not found.",
        )

    previous = await _stored_requirements(room)
    requirements, reply_text, agent_engine = await run_design_agent(
        room,
        message.content,
        previous,
    )
    await db[DESIGN_REQUIREMENTS].update_one(
        {"room_id": room["_id"]},
        {
            "$set": {
                **requirements,
                "room_id": room["_id"],
                "updated_at": utc_now(),
                "agent_engine": agent_engine,
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )
    await db[DESIGN_CONVERSATIONS].update_one(
        {"room_id": room["_id"]},
        {
            "$push": {
                "messages": {
                    "$each": [
                        {**message.model_dump(), "created_at": utc_now()},
                        {
                            "role": "assistant",
                            "content": reply_text,
                            "created_at": utc_now(),
                        },
                    ]
                }
            }
        },
        upsert=True,
    )

    memory_document = await _load_design_memory(ObjectId(current_user["id"]))
    relative_path, engine, metadata = await _run_image_generation(
        room,
        requirements,
        revision_note=message.content,
        memory_document=memory_document,
    )
    image_url = _public_media_url(request, relative_path)

    count = await db[DESIGN_VERSIONS].count_documents({"room_id": room["_id"]})
    new_version_number = count + 1
    style = resolve_style(requirements.get("style"))
    result = await db[DESIGN_VERSIONS].insert_one(
        {
            "room_id": room["_id"],
            "version": f"V{new_version_number}",
            "title": f"{style} Revision of {original_design['version']}",
            "note": (
                f"{_build_generation_note(room, requirements, engine)} "
                f"Revision focus: {message.content}"
            ),
            "image_url": image_url,
            "engine": engine,
            "pipeline_metadata": metadata,
            "validation": (metadata or {}).get("validation"),
            "is_finalized": False,
            "created_at": utc_now(),
        }
    )
    await _persist_generation_event(
        user_id=ObjectId(current_user["id"]),
        room_id=room["_id"],
        design_version_id=result.inserted_id,
        metadata=metadata,
    )
    from app.services.pipeline.design_memory import (
        memory_from_document,
        merge_memory_from_requirements,
    )

    memory = merge_memory_from_requirements(
        memory_from_document(memory_document),
        requirements,
    )
    await _upsert_design_memory(ObjectId(current_user["id"]), memory.to_dict())
    created = serialize_id(await db[DESIGN_VERSIONS].find_one({"_id": result.inserted_id}))
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load revised design.",
        )
    created["room_id"] = str(created["room_id"])
    return DesignVersionRead(**created)
