from bson import ObjectId
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.db.database import get_database
from app.models.collections import DESIGN_SCORES, DESIGN_VERSIONS, HOMES, ROOMS
from app.schemas.dashboard import DashboardSummary, RoomStatusItem
from app.schemas.home import HomeRead, OverallStyleProfile
from app.services.mongo import serialize_id

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(
    current_user: dict = Depends(get_current_user),
) -> DashboardSummary:
    db = get_database()
    room_cursor = db[ROOMS].find({"user_id": ObjectId(current_user["id"])})
    room_items: list[RoomStatusItem] = []
    recent_designs: list[str] = []

    async for room in room_cursor:
        room_items.append(RoomStatusItem(name=room["room_type"], status=room["status"]))
        latest_design = await db[DESIGN_VERSIONS].find_one(
            {"room_id": room["_id"]},
            sort=[("created_at", -1)],
        )
        if latest_design is not None:
            recent_designs.append(f"{room['room_type']} {latest_design['version']}")

    average_design_score = 0
    score_values: list[int] = []
    score_cursor = db[DESIGN_SCORES].find({})
    async for score in score_cursor:
        version = await db[DESIGN_VERSIONS].find_one({"_id": score["design_version_id"]})
        if version is None:
            continue
        room = await db[ROOMS].find_one(
            {"_id": version["room_id"], "user_id": ObjectId(current_user["id"])}
        )
        if room is None:
            continue
        score_values.append(score["total_score"])
    if score_values:
        average_design_score = int(sum(score_values) / len(score_values))

    return DashboardSummary(
        greeting=f"Good Morning, {current_user['name'].split()[0]}",
        summary="Let's design your dream home.",
        average_design_score=average_design_score,
        estimated_budget=len(room_items) * 80000,
        my_home=room_items,
        recent_designs=recent_designs[:4],
        quick_actions=[
            "Design Room",
            "Inspiration",
            "Contractor Brief",
            "Find Professional",
        ],
    )


@router.get("/profile/home", response_model=HomeRead)
async def home_summary(current_user: dict = Depends(get_current_user)) -> HomeRead:
    document = await get_database()[HOMES].find_one(
        {"user_id": ObjectId(current_user["id"])}
    )
    home_document = serialize_id(document)
    if home_document is None:
        return HomeRead(
            id="",
            user_id=current_user["id"],
            property_type="Apartment",
            rooms=0,
            preferred_style="Warm Minimal",
            overall_style_profile=OverallStyleProfile(
                style="Warm Minimal Luxury",
                colours=[],
                lighting="Warm",
                wood="Walnut",
                metal_finish="Matte Black",
            ),
        )

    home_document["user_id"] = str(home_document["user_id"])
    return HomeRead(**home_document)
