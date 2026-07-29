from fastapi import APIRouter

from app.api.routes import auth, dashboard, homes, rooms, support

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(homes.router)
api_router.include_router(rooms.router)
api_router.include_router(support.router)
