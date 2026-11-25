import hashlib
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.services.rate_limit import Allowed, Denied, check_and_record, hash_ip, quota


async def _log(visitor: str, ip: str, minutes_ago: float) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO session_log (visitor_id, ip_hash, started_at) "
                "VALUES (:v, :i, now() - (:m * interval '1 minute'))"
            ),
            {"v": visitor, "i": ip, "m": minutes_ago},
        )


async def _count() -> int:
    async with engine.connect() as conn:
        return (await conn.execute(text("SELECT count(*) FROM session_log"))).scalar_one()


def test_ip_hash_is_salted_sha256_hex() -> None:
    expected = hashlib.sha256(f"203.0.113.9{settings.session_salt}".encode()).hexdigest()
    assert hash_ip("203.0.113.9") == expected
    assert "203.0.113.9" not in hash_ip("203.0.113.9")


async def test_allows_under_limit_and_records() -> None:
    async with SessionLocal() as s:
        result = await check_and_record(s, "v1", "ip1", limit=3)
    assert isinstance(result, Allowed)
    assert await _count() == 1


async def test_denied_when_visitor_at_limit_and_not_logged() -> None:
    for _ in range(3):
        await _log("v1", "other-ip", 10)
    async with SessionLocal() as s:
        result = await check_and_record(s, "v1", "ip-new", limit=3)
    assert isinstance(result, Denied)
    assert await _count() == 3
    # oldest counted session + 1 h = 50 minutes from now
    expected = datetime.now(UTC) + timedelta(minutes=50)
    assert abs((result.retry_at - expected).total_seconds()) < 5


async def test_denied_when_ip_at_limit_even_with_new_visitor() -> None:
    for i in range(3):
        await _log(f"v{i}", "shared-ip", 5)
    async with SessionLocal() as s:
        result = await check_and_record(s, "fresh-visitor", "shared-ip", limit=3)
    assert isinstance(result, Denied)


async def test_old_sessions_do_not_count() -> None:
    for _ in range(3):
        await _log("v1", "ip1", 61)
    async with SessionLocal() as s:
        assert isinstance(await check_and_record(s, "v1", "ip1", limit=3), Allowed)


async def test_rows_older_than_24h_are_pruned_on_insert() -> None:
    await _log("old", "old", 60 * 25)
    async with SessionLocal() as s:
        await check_and_record(s, "v1", "ip1", limit=3)
    async with engine.connect() as conn:
        left = (
            await conn.execute(text("SELECT count(*) FROM session_log WHERE visitor_id='old'"))
        ).scalar_one()
    assert left == 0


async def test_quota_reports_remaining_and_reset() -> None:
    async with SessionLocal() as s:
        q = await quota(s, "v1", "ip1", limit=5)
    assert (q.limit, q.remaining, q.resets_at) == (5, 5, None)
    await _log("v1", "ip1", 20)
    await _log("v1", "ip1", 10)
    async with SessionLocal() as s:
        q = await quota(s, "v1", "ip1", limit=5)
    assert q.remaining == 3
    assert q.resets_at is not None
    assert abs((q.resets_at - (datetime.now(UTC) + timedelta(minutes=40))).total_seconds()) < 5
