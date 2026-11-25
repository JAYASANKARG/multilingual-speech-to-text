import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_TEXT_LENGTH = 50_000
_LANG = re.compile(r"^([a-z]{2,3}|unknown)$")


def _clean_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Text cannot be empty")
    return value


class Transcription(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    languages: list[str]
    engine: str | None
    source: Literal["spoken", "manual"]
    status: Literal["complete", "interrupted"]
    created_at: datetime
    updated_at: datetime

    @field_validator("languages")
    @classmethod
    def _check_languages(cls, value: list[str]) -> list[str]:
        for code in value:
            if not _LANG.match(code):
                raise ValueError(f"Invalid language code: {code}")
        return value


class TranscriptionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=MAX_TEXT_LENGTH)

    @field_validator("text")
    @classmethod
    def _strip(cls, value: str) -> str:
        return _clean_text(value)


class TranscriptionUpdate(TranscriptionCreate):
    pass


class TranscriptionPage(BaseModel):
    items: list[Transcription]
    next_cursor: str | None
