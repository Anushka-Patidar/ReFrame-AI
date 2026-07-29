from pydantic import BaseModel


class DesignScoreRead(BaseModel):
    id: str
    design_version_id: str
    total_score: int
    categories: dict[str, int]
    observation: str
    recommendation: str


class ContractorBriefRead(BaseModel):
    id: str
    room_id: str
    design_version_id: str
    room_name: str
    style: str
    budget: int
    room_size: str
    keep_existing: list[str]
    remove: list[str]
    wall: str
    lighting: list[str]
    additions: list[str]
    colour_palette: list[str]
    important_notes: list[str]


class InspirationRead(BaseModel):
    id: str
    user_id: str
    image_url: str
    detected_tags: list[str]


class InspirationCreate(BaseModel):
    image_url: str
    detected_tags: list[str]


class ProfessionalRead(BaseModel):
    id: str
    name: str
    profession: str
    city: str
    area: str
    phone: str
    experience_years: int
    rating: float
    availability: str
