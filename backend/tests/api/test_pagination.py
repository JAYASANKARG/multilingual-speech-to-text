import time

from httpx import AsyncClient
from sqlalchemy import text

from app.core.db import engine


async def _seed(n: int, same_timestamp: bool = False) -> None:
    ts = "now()" if same_timestamp else "now() - (g * interval '1 second')"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO transcriptions (text, source, languages, created_at) "
                f"SELECT 'entry ' || g, 'spoken', '{{en}}', {ts} FROM generate_series(1, :n) g"
            ),
            {"n": n},
        )


async def _walk(client: AsyncClient, limit: int = 20) -> list[str]:
    ids: list[str] = []
    cursor = None
    while True:
        params = {"limit": limit} | ({"cursor": cursor} if cursor else {})
        body = (await client.get("/api/transcriptions", params=params)).json()
        ids += [i["id"] for i in body["items"]]
        cursor = body["next_cursor"]
        if cursor is None:
            return ids


async def test_defaults_and_bounds(client: AsyncClient) -> None:
    await _seed(25)
    body = (await client.get("/api/transcriptions")).json()
    assert len(body["items"]) == 20
    assert body["next_cursor"] is not None
    for bad in (0, 101):
        assert (await client.get("/api/transcriptions", params={"limit": bad})).status_code == 422


async def test_newest_first(client: AsyncClient) -> None:
    await _seed(5)
    items = (await client.get("/api/transcriptions")).json()["items"]
    stamps = [i["created_at"] for i in items]
    assert stamps == sorted(stamps, reverse=True)


async def test_walk_yields_each_row_once(client: AsyncClient) -> None:
    await _seed(55)
    ids = await _walk(client)
    assert len(ids) == 55
    assert len(set(ids)) == 55


async def test_identical_timestamps_do_not_duplicate_or_skip(client: AsyncClient) -> None:
    await _seed(45, same_timestamp=True)
    ids = await _walk(client, limit=7)
    assert len(ids) == len(set(ids)) == 45


async def test_insert_between_pages_causes_no_duplicates(client: AsyncClient) -> None:
    await _seed(30)
    first = (await client.get("/api/transcriptions", params={"limit": 10})).json()
    await client.post("/api/transcriptions", json={"text": "brand new"})
    second = (
        await client.get(
            "/api/transcriptions", params={"limit": 10, "cursor": first["next_cursor"]}
        )
    ).json()
    seen = {i["id"] for i in first["items"]}
    assert not seen & {i["id"] for i in second["items"]}


async def test_last_page_has_null_cursor(client: AsyncClient) -> None:
    await _seed(3)
    body = (await client.get("/api/transcriptions")).json()
    assert body["next_cursor"] is None
    assert len(body["items"]) == 3


async def test_invalid_cursor(client: AsyncClient) -> None:
    res = await client.get("/api/transcriptions", params={"cursor": "garbage"})
    assert res.status_code == 422


async def test_thousand_rows_first_page_fast(client: AsyncClient) -> None:
    await _seed(1000)
    started = time.monotonic()
    res = await client.get("/api/transcriptions")
    assert res.status_code == 200
    assert time.monotonic() - started < 2
