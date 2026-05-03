from pydantic import BaseModel


class Meeting(BaseModel):
    title: str
    start_time: str
    end_time: str
    location: str | None = None


class Task(BaseModel):
    title: str
    due: str
    board: str
    url: str


class Birthday(BaseModel):
    name: str
    date: str


class DigestBrief(BaseModel):
    date: str
    meetings: list[Meeting]
    tasks: list[Task]
    birthdays: list[Birthday]
    summary: str
