from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.services.transcriptions import InvalidCursor, decode_cursor, encode_cursor


def test_round_trip() -> None:
    created = datetime(2026, 11, 25, 10, 30, 15, 123456, tzinfo=UTC)
    ident = uuid4()
    assert decode_cursor(encode_cursor(created, ident)) == (created, ident)


@pytest.mark.parametrize("bad", ["", "garbage", "e30", "!!!!", "eyJ4IjoxfQ"])
def test_bad_cursors_raise(bad: str) -> None:
    with pytest.raises(InvalidCursor):
        decode_cursor(bad)
