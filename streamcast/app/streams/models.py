from pydantic import BaseModel, Field


class StreamCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    broadcaster: str = Field(min_length=1)


class StreamResponse(BaseModel):
    id: str
    title: str
    broadcaster: str
    is_live: bool = False
