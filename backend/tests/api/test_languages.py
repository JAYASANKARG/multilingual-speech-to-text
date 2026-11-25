from httpx import AsyncClient


async def test_languages_endpoint(client: AsyncClient) -> None:
    res = await client.get("/api/languages")
    assert res.status_code == 200
    body = res.json()
    by_code = {item["code"]: item for item in body}
    assert body[0]["code"] == "auto"
    assert set(by_code) == {"auto", "hi", "en", "ta", "te", "bn", "mr", "gu", "kn", "ml"}
    assert all(item["pinnable"] for item in body)
    assert set(body[0]) == {"code", "name", "pinnable"}
