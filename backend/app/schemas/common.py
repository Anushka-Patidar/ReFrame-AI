from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "ReFrame API"


class AiCapabilitiesResponse(BaseModel):
    photoreal_image_edit: bool
    claude_chat: bool
    openai_chat: bool
    local_style_grade: bool = False
    openai_image_model: str
    recommended_setup: str
    mode: Literal["photoreal", "local-grade"] = "local-grade"
    image_provider: str = "none"
    pollinations_enabled: bool = False
    gemini_enabled: bool = False
    supports_reference_image_edit: bool = False
    local_ai_profile: str | None = None
    generation_busy: bool = False


class ApiMessage(BaseModel):
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
