from pydantic import BaseModel


class RoomStatusItem(BaseModel):
    name: str
    status: str


class DashboardSummary(BaseModel):
    greeting: str
    summary: str
    average_design_score: int
    estimated_budget: int
    my_home: list[RoomStatusItem]
    recent_designs: list[str]
    quick_actions: list[str]
