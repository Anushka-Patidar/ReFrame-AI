from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_frontend_origins, settings
from app.db.database import close_mongo_connection, connect_to_mongo
from app.schemas.common import AiCapabilitiesResponse, HealthResponse
from app.services.bootstrap import ensure_seed_data
from app.services.generation_runtime import generation_gate
from app.services.image_generation import get_ai_capabilities, get_generation_progress, log_startup_hardware
from app.services.media import UPLOADS_ROOT, ensure_upload_directories


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_upload_directories()
    log_startup_hardware()
    await connect_to_mongo()
    await ensure_seed_data()
    try:
        yield
    finally:
        await close_mongo_connection()


ensure_upload_directories()

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_frontend_origins(),
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)
app.mount("/media", StaticFiles(directory=UPLOADS_ROOT), name="media")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.get("/api/system/ai-capabilities", response_model=AiCapabilitiesResponse)
async def ai_capabilities() -> AiCapabilitiesResponse:
    return AiCapabilitiesResponse(**get_ai_capabilities())


@app.get("/api/system/generation-status")
async def generation_status() -> dict:
    """Live local-generation stage for the product UI (no fake percentages)."""
    return get_generation_progress()


@app.post("/api/system/generation-reset")
async def generation_reset() -> dict:
    """Clear a stuck generation lock so the user can retry."""
    generation_gate.force_reset(
        error="Generation was cleared. You can start a new redesign."
    )
    return get_generation_progress()
