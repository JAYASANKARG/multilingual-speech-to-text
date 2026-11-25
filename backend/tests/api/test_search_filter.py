from httpx import AsyncClient
from sqlalchemy import text

from app.core.db import engine


async def _add(body: str, languages: list[str]) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO transcriptions (text, source, languages) VALUES (:t, 'spoken', :l)"),
            {"t": body, "l": languages},
        )


async def _texts(client: AsyncClient, **params: object) -> list[str]:
    res = await client.get("/api/transcriptions", params=params)
    assert res.status_code == 200, res.text
    return sorted(i["text"] for i in res.json()["items"])


async def _seed() -> None:
    await _add("Kal meeting hai at 10 AM", ["hi", "en"])
    await _add("कल की बैठक", ["hi"])
    await _add("Send the REPORT today", ["en"])
    await _add("100% sure_thing", ["en"])
    await _add("வணக்கம்", ["ta"])


async def test_search_is_case_insensitive_substring(client: AsyncClient) -> None:
    await _seed()
    assert await _texts(client, q="report") == ["Send the REPORT today"]
    assert await _texts(client, q="MEETING") == ["Kal meeting hai at 10 AM"]


async def test_search_devanagari(client: AsyncClient) -> None:
    await _seed()
    assert await _texts(client, q="बैठक") == ["कल की बैठक"]


async def test_wildcards_are_literal(client: AsyncClient) -> None:
    await _seed()
    assert await _texts(client, q="%") == ["100% sure_thing"]
    assert await _texts(client, q="_") == ["100% sure_thing"]
    assert await _texts(client, q="s_r") == []


async def test_q_too_long(client: AsyncClient) -> None:
    res = await client.get("/api/transcriptions", params={"q": "a" * 201})
    assert res.status_code == 422


async def test_language_filter(client: AsyncClient) -> None:
    await _seed()
    assert await _texts(client, language="hi") == ["Kal meeting hai at 10 AM", "कल की बैठक"]
    assert await _texts(client, language="ta") == ["வணக்கம்"]


async def test_language_validation(client: AsyncClient) -> None:
    for bad in ("HI", "h", "hindi", "x1"):
        res = await client.get("/api/transcriptions", params={"language": bad})
        assert res.status_code == 422
    assert (
        await client.get("/api/transcriptions", params={"language": "unknown"})
    ).status_code == 200


async def test_search_and_language_combine(client: AsyncClient) -> None:
    await _seed()
    assert await _texts(client, q="meeting", language="hi") == ["Kal meeting hai at 10 AM"]
    assert await _texts(client, q="meeting", language="ta") == []


async def test_filtered_results_still_page_cleanly(client: AsyncClient) -> None:
    for i in range(25):
        await _add(f"needle {i}", ["en"])
        await _add(f"hay {i}", ["en"])
    seen: list[str] = []
    cursor = None
    while True:
        params = {"q": "needle", "limit": 10} | ({"cursor": cursor} if cursor else {})
        body = (await client.get("/api/transcriptions", params=params)).json()
        seen += [i["id"] for i in body["items"]]
        cursor = body["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen)) == 25


async def test_no_match(client: AsyncClient) -> None:
    await _seed()
    body = (await client.get("/api/transcriptions", params={"q": "zzzz"})).json()
    assert body == {"items": [], "next_cursor": None}
