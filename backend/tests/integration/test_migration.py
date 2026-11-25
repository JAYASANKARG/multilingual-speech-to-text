import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.db import engine


async def _insert(**overrides: object) -> None:
    values = {"text": "hello", "source": "spoken", "status": "complete"} | overrides
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO transcriptions (text, source, status) VALUES (:text, :source, :status)"
            ),
            values,
        )


async def test_tables_and_defaults() -> None:
    await _insert()
    async with engine.connect() as conn:
        row = (await conn.execute(text("SELECT languages, status, id FROM transcriptions"))).one()
        assert row.languages == []
        assert row.status == "complete"
        assert row.id is not None
        await conn.execute(text("SELECT count(*) FROM session_log"))


@pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
async def test_blank_text_rejected(bad: str) -> None:
    with pytest.raises(IntegrityError):
        await _insert(text=bad)


async def test_source_and_status_checks() -> None:
    with pytest.raises(IntegrityError):
        await _insert(source="voice")
    with pytest.raises(IntegrityError):
        await _insert(status="done")


async def test_indexes_exist() -> None:
    async with engine.connect() as conn:
        names = {
            r[0]
            for r in await conn.execute(
                text("SELECT indexname FROM pg_indexes WHERE tablename = 'transcriptions'")
            )
        }
    assert {"ix_transcriptions_created_id", "ix_transcriptions_languages"} <= names
