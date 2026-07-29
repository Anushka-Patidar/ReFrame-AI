from pydantic import BaseModel


class OverallStyleProfile(BaseModel):
    style: str
    colours: list[str]
    lighting: str
    wood: str
    metal_finish: str


class HomeBase(BaseModel):
    property_type: str
    rooms: int
    preferred_style: str
    overall_style_profile: OverallStyleProfile


class HomeRead(HomeBase):
    id: str
    user_id: str


class HomeUpdate(HomeBase):
    pass
