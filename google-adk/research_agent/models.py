from pydantic import BaseModel


class ResearchBrief(BaseModel):
    topic: str
    summary: str
    key_points: list[str]
    sources: list[str]
