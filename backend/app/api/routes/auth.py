from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.db.database import get_database
from app.models.collections import HOMES, USERS
from app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserRead
from app.schemas.home import OverallStyleProfile
from app.services.mongo import serialize_id, utc_now
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
async def signup(payload: UserCreate) -> TokenResponse:
    db = get_database()
    existing = await db[USERS].find_one({"email": payload.email.lower()})
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user_document = {
        "name": payload.name,
        "email": payload.email.lower(),
        "phone": payload.phone,
        "city": payload.city,
        "password_hash": hash_password(payload.password),
        "created_at": utc_now(),
    }
    result = await db[USERS].insert_one(user_document)

    await db[HOMES].insert_one(
        {
            "user_id": result.inserted_id,
            "property_type": "Apartment",
            "rooms": 4,
            "preferred_style": "Warm Minimal",
            "overall_style_profile": OverallStyleProfile(
                style="Warm Minimal Luxury",
                colours=["Beige", "Cream", "Walnut"],
                lighting="Warm",
                wood="Walnut",
                metal_finish="Matte Black",
            ).model_dump(),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
    )

    created_user = serialize_id(await db[USERS].find_one({"_id": result.inserted_id}))
    if created_user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load created user.",
        )

    access_token = create_access_token(created_user["id"])
    return TokenResponse(access_token=access_token, user=UserRead(**created_user))


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    db = get_database()
    user_document = await db[USERS].find_one({"email": payload.email.lower()})
    if user_document is None or not verify_password(
        payload.password,
        user_document["password_hash"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user = serialize_id(user_document)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load user.",
        )

    access_token = create_access_token(user["id"])
    return TokenResponse(access_token=access_token, user=UserRead(**user))


@router.get("/me", response_model=TokenResponse)
async def me(current_user: dict = Depends(get_current_user)) -> TokenResponse:
    access_token = create_access_token(current_user["id"])
    return TokenResponse(access_token=access_token, user=UserRead(**current_user))
