from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.db.database import get_database
from app.models.collections import HOMES, USERS
from app.schemas.auth import ProfileUpdate, UserRead
from app.schemas.common import ApiMessage
from app.schemas.home import HomeRead, HomeUpdate
from app.services.mongo import serialize_id, utc_now

router = APIRouter(tags=["homes"])


@router.get("/profile", response_model=UserRead)
async def profile(current_user: dict = Depends(get_current_user)) -> UserRead:
    return UserRead(**current_user)


@router.put("/profile", response_model=ApiMessage)
async def update_profile(
    payload: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
) -> ApiMessage:
    await get_database()[USERS].update_one(
        {"_id": ObjectId(current_user["id"])},
        {
            "$set": {
                "name": payload.name,
                "phone": payload.phone,
                "city": payload.city,
                "updated_at": utc_now(),
            }
        },
    )
    return ApiMessage(message="Profile updated successfully.")


@router.get("/homes/me", response_model=HomeRead)
async def home(current_user: dict = Depends(get_current_user)) -> HomeRead:
    document = await get_database()[HOMES].find_one(
        {"user_id": ObjectId(current_user["id"])}
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Home profile not found.",
        )
    home_document = serialize_id(document)
    if home_document is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load home profile.",
        )

    home_document["user_id"] = str(home_document["user_id"])
    return HomeRead(**home_document)


@router.put("/homes/me", response_model=ApiMessage)
async def update_home(
    payload: HomeUpdate,
    current_user: dict = Depends(get_current_user),
) -> ApiMessage:
    update_result = await get_database()[HOMES].update_one(
        {"user_id": ObjectId(current_user["id"])},
        {"$set": {**payload.model_dump(), "updated_at": utc_now()}},
    )
    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Home profile not found.",
        )
    return ApiMessage(message="Home preferences updated successfully.")
