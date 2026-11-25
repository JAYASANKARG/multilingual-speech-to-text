from datetime import datetime

from pydantic import BaseModel, Field


class Language(BaseModel):
    code: str
    name: str
    pinnable: bool


class Quota(BaseModel):
    limit: int
    remaining: int = Field(ge=0)
    resets_at: datetime | None


class ErrorDetail(BaseModel):
    detail: str
