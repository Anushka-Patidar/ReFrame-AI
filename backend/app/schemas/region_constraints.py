from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


RegionAction = Literal["KEEP", "CHANGE", "REMOVE"]


class RegionConstraintCreateForm(BaseModel):
    action: RegionAction
    label: str = Field(min_length=1, max_length=80)
    image_width: int = Field(gt=0, lt=20000)
    image_height: int = Field(gt=0, lt=20000)


class RegionConstraintRead(BaseModel):
    id: str
    action: RegionAction
    label: str
    mask_url: str
    image_width: int
    image_height: int
    created_at: datetime

    model_config = {"extra": "ignore"}

