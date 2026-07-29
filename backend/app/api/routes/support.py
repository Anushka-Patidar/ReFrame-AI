from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.db.database import get_database
from app.models.collections import (
    CONTRACTOR_BRIEFS,
    DESIGN_REQUIREMENTS,
    DESIGN_SCORES,
    DESIGN_VERSIONS,
    INSPIRATIONS,
    PROFESSIONALS,
    ROOMS,
    SHARED_BRIEFS,
)
from app.schemas.common import ApiMessage
from app.schemas.support import (
    ContractorBriefRead,
    DesignScoreRead,
    InspirationCreate,
    InspirationRead,
    ProfessionalRead,
)
from app.services.mongo import object_id, serialize_id, utc_now

router = APIRouter(tags=["support"])


@router.get("/scores/{design_id}", response_model=DesignScoreRead)
async def score(design_id: str) -> DesignScoreRead:
    db = get_database()
    existing = await db[DESIGN_SCORES].find_one({"design_version_id": object_id(design_id)})
    if existing is None:
        version = await db[DESIGN_VERSIONS].find_one({"_id": object_id(design_id)})
        if version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Design version not found.",
            )
        room = await db[ROOMS].find_one({"_id": version["room_id"]})
        room_size = room["dimensions"]["length"] * room["dimensions"]["width"] if room else 0
        total_score = 87 if room_size >= 150 else 82
        result = await db[DESIGN_SCORES].insert_one(
            {
                "design_version_id": version["_id"],
                "total_score": total_score,
                "categories": {
                    "space_usage": 91 if room_size >= 150 else 82,
                    "colour_harmony": 89,
                    "lighting": 85,
                    "furniture_placement": 86,
                    "budget_fit": 84,
                },
                "observation": "Furniture placement makes good use of the available room.",
                "recommendation": "Additional hidden storage could improve functionality.",
                "created_at": utc_now(),
            }
        )
        existing = await db[DESIGN_SCORES].find_one({"_id": result.inserted_id})

    score_document = serialize_id(existing)
    if score_document is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load design score.",
        )
    score_document["design_version_id"] = str(score_document["design_version_id"])
    return DesignScoreRead(**score_document)


@router.post("/briefs/{design_id}/generate", response_model=ContractorBriefRead)
async def generate_brief(design_id: str) -> ContractorBriefRead:
    db = get_database()
    version = await db[DESIGN_VERSIONS].find_one({"_id": object_id(design_id)})
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Design version not found.",
        )
    room = await db[ROOMS].find_one({"_id": version["room_id"]})
    requirements = await db[DESIGN_REQUIREMENTS].find_one({"room_id": version["room_id"]})
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found.",
        )

    await db[CONTRACTOR_BRIEFS].delete_many({"design_version_id": version["_id"]})
    result = await db[CONTRACTOR_BRIEFS].insert_one(
        {
            "room_id": room["_id"],
            "design_version_id": version["_id"],
            "room_name": room["room_type"],
            "style": requirements["style"] if requirements else "Warm Minimal Luxury",
            "budget": requirements["budget"] if requirements else 80000,
            "room_size": f"{room['dimensions']['length']} x {room['dimensions']['width']} ft",
            "keep_existing": requirements["keep"] if requirements else [],
            "remove": requirements["remove"] if requirements else [],
            "wall": "Warm beige finish with walnut accent treatment.",
            "lighting": ["Warm white lighting", "Two bedside lights", "Ceiling lighting"],
            "additions": requirements["add"] if requirements else [],
            "colour_palette": requirements["colours"] if requirements else [],
            "important_notes": ["Existing large furniture should not be modified."],
            "created_at": utc_now(),
        }
    )
    brief = serialize_id(await db[CONTRACTOR_BRIEFS].find_one({"_id": result.inserted_id}))
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load contractor brief.",
        )
    brief["room_id"] = str(brief["room_id"])
    brief["design_version_id"] = str(brief["design_version_id"])
    return ContractorBriefRead(**brief)


@router.get("/briefs", response_model=list[ContractorBriefRead])
async def briefs(current_user: dict = Depends(get_current_user)) -> list[ContractorBriefRead]:
    cursor = get_database()[CONTRACTOR_BRIEFS].aggregate(
        [
            {
                "$lookup": {
                    "from": ROOMS,
                    "localField": "room_id",
                    "foreignField": "_id",
                    "as": "room",
                }
            },
            {"$unwind": "$room"},
            {"$match": {"room.user_id": ObjectId(current_user["id"])}},
        ]
    )
    items: list[ContractorBriefRead] = []
    async for document in cursor:
        brief_document = serialize_id(document)
        if brief_document is None:
            continue
        brief_document["room_id"] = str(brief_document["room_id"])
        brief_document["design_version_id"] = str(brief_document["design_version_id"])
        brief_document.pop("room", None)
        items.append(ContractorBriefRead(**brief_document))
    return items


@router.post("/briefs/{brief_id}/share", response_model=ApiMessage)
async def share_brief(
    brief_id: str,
    current_user: dict = Depends(get_current_user),
) -> ApiMessage:
    brief = await get_database()[CONTRACTOR_BRIEFS].find_one({"_id": object_id(brief_id)})
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brief not found.",
        )
    await get_database()[SHARED_BRIEFS].insert_one(
        {
            "brief_id": brief["_id"],
            "shared_by_user_id": ObjectId(current_user["id"]),
            "shared_at": utc_now(),
        }
    )
    return ApiMessage(message=f"Brief '{brief_id}' shared successfully.")


@router.get("/inspirations", response_model=list[InspirationRead])
async def inspirations(
    current_user: dict = Depends(get_current_user),
) -> list[InspirationRead]:
    cursor = get_database()[INSPIRATIONS].find({"user_id": ObjectId(current_user["id"])})
    items: list[InspirationRead] = []
    async for document in cursor:
        inspiration = serialize_id(document)
        if inspiration is None:
            continue
        inspiration["user_id"] = str(inspiration["user_id"])
        items.append(InspirationRead(**inspiration))
    return items


@router.post("/inspirations", response_model=InspirationRead)
async def add_inspiration(
    payload: InspirationCreate,
    current_user: dict = Depends(get_current_user),
) -> InspirationRead:
    result = await get_database()[INSPIRATIONS].insert_one(
        {
            "user_id": ObjectId(current_user["id"]),
            "image_url": payload.image_url,
            "detected_tags": payload.detected_tags,
            "created_at": utc_now(),
        }
    )
    inspiration = serialize_id(await get_database()[INSPIRATIONS].find_one({"_id": result.inserted_id}))
    if inspiration is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load inspiration.",
        )
    inspiration["user_id"] = str(inspiration["user_id"])
    return InspirationRead(**inspiration)


@router.get("/professionals", response_model=list[ProfessionalRead])
async def list_professionals(
    city: str | None = Query(default=None),
    profession: str | None = Query(default=None),
) -> list[ProfessionalRead]:
    filters = {}
    if city:
        filters["city"] = city
    if profession:
        filters["profession"] = profession

    cursor = get_database()[PROFESSIONALS].find(filters).sort("rating", -1)
    results: list[ProfessionalRead] = []
    async for document in cursor:
        professional = serialize_id(document)
        if professional is None:
            continue
        professional.pop("created_at", None)
        results.append(ProfessionalRead(**professional))
    return results
