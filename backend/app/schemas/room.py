from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RoomDimensions(BaseModel):
    length: int
    width: int
    height: int


class RoomCreate(BaseModel):
    room_type: str
    dimensions: RoomDimensions
    original_image_url: str | None = None
    match_home_style: bool = True


class ChatMessage(BaseModel):
    role: str
    content: str


class DesignRequirements(BaseModel):
    room: str
    style: str = "Warm Minimal Luxury"
    budget: int = 80000
    keep: list[str] = Field(default_factory=list)
    remove: list[str] = Field(default_factory=list)
    add: list[str] = Field(default_factory=list)
    colours: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GenerationRequest(BaseModel):
    quality: Literal["preview", "balanced", "quality"] | None = None


class SpaceCheckItem(BaseModel):
    item: str
    status: str
    note: str


class SpaceCheckResponse(BaseModel):
    room_size: str
    checks: list[SpaceCheckItem]
    recommendation: str


class DesignVersionRead(BaseModel):
    id: str
    room_id: str
    version: str
    title: str
    note: str
    image_url: str | None = None
    engine: str | None = None
    pipeline_metadata: dict | None = None
    validation: dict | None = None
    is_finalized: bool = False
    created_at: datetime

    model_config = {"extra": "ignore"}


class RoomRead(BaseModel):
    id: str
    user_id: str
    room_type: str
    dimensions: RoomDimensions
    status: str
    original_image_url: str | None = None
    match_home_style: bool = True
    created_at: datetime


class UploadRoomImage(BaseModel):
    image_url: str
