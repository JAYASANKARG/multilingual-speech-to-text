import uuid

from httpx import AsyncClient
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine


async def test_quota_sets_visitor_cookie_and_reports_full_allowance(client: AsyncClient) -> None:
    res = await client.get("/api/quota")
    assert res.status_code == 200
    body = res.json()
    assert body == {
        "limit": settings.sessions_per_hour,
        "remaining": settings.sessions_per_hour,
        "resets_at": None,
    }
    cookie = res.headers["set-cookie"]
    assert "visitor_id=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie or "samesite=lax" in cookie.lower()
    uuid.UUID(client.cookies["visitor_id"])


async def test_quota_reuses_existing_cookie(client: AsyncClient) -> None:
    vid = str(uuid.uuid4())
    client.cookies.set("visitor_id", vid)
    res = await client.get("/api/quota")
    assert "set-cookie" not in res.headers


async def test_quota_counts_this_visitors_sessions(client: AsyncClient) -> None:
    vid = str(uuid.uuid4())
    client.cookies.set("visitor_id", vid)
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO session_log (visitor_id, ip_hash) VALUES (:v, 'x'), (:v, 'x')"),
            {"v": vid},
        )
    body = (await client.get("/api/quota")).json()
    assert body["remaining"] == settings.sessions_per_hour - 2
    assert body["resets_at"] is not None
