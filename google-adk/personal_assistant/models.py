from pydantic import BaseModel


class MemoryItem(BaseModel):
    id: str
    content: str
    memory_type: str        # "fact", "preference", "summary"
    timestamp: str
    relevance_score: float | None = None
