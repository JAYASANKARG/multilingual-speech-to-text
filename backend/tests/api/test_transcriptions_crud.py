import uuid

import pytest
from httpx import AsyncClient


async def _create(client: AsyncClient, text: str = "hello world") -> dict:
    res = await client.post("/api/transcriptions", json={"text": text})
    assert res.status_code == 201, res.text
    return res.json()


async def test_create_manual_entry(client: AsyncClient) -> None:
    body = await _create(client, "  typed note  ")
    assert body["text"] == "typed note"
    assert body["source"] == "manual"
    assert body["status"] == "complete"
    assert body["engine"] is None
    assert body["languages"] == ["en"]  # derived from the text script
    assert uuid.UUID(body["id"])


async def test_create_derives_language_from_script(client: AsyncClient) -> None:
    body = await _create(client, "कल meeting है")
    assert body["languages"] == ["hi", "en"]


@pytest.mark.parametrize("bad", ["", "   ", "\n\t "])
async def test_blank_text_rejected(client: AsyncClient, bad: str) -> None:
    res = await client.post("/api/transcriptions", json={"text": bad})
    assert res.status_code == 422
    assert "Text cannot be empty" in res.text


async def test_too_long_rejected(client: AsyncClient) -> None:
    res = await client.post("/api/transcriptions", json={"text": "a" * 50_001})
    assert res.status_code == 422
    ok = await client.post("/api/transcriptions", json={"text": "a" * 50_000})
    assert ok.status_code == 201


async def test_unknown_fields_rejected(client: AsyncClient) -> None:
    res = await client.post("/api/transcriptions", json={"text": "x", "engine": "evil"})
    assert res.status_code == 422


async def test_get_one(client: AsyncClient) -> None:
    created = await _create(client)
    res = await client.get(f"/api/transcriptions/{created['id']}")
    assert res.status_code == 200
    assert res.json() == created


async def test_get_missing_and_malformed(client: AsyncClient) -> None:
    assert (await client.get(f"/api/transcriptions/{uuid.uuid4()}")).status_code == 404
    assert (await client.get("/api/transcriptions/not-a-uuid")).status_code == 422


async def test_patch_updates_text_and_updated_at_only(client: AsyncClient) -> None:
    created = await _create(client, "before")
    res = await client.patch(f"/api/transcriptions/{created['id']}", json={"text": "after"})
    assert res.status_code == 200
    body = res.json()
    assert body["text"] == "after"
    assert body["updated_at"] > created["updated_at"]
    for field in ("created_at", "engine", "source", "status", "id"):
        assert body[field] == created[field]


async def test_patch_rejects_blank_and_missing(client: AsyncClient) -> None:
    created = await _create(client)
    blank = await client.patch(f"/api/transcriptions/{created['id']}", json={"text": "  "})
    assert blank.status_code == 422
    missing = await client.patch(f"/api/transcriptions/{uuid.uuid4()}", json={"text": "x"})
    assert missing.status_code == 404
    still = await client.get(f"/api/transcriptions/{created['id']}")
    assert still.json()["text"] == created["text"]


async def test_patch_cannot_change_server_fields(client: AsyncClient) -> None:
    created = await _create(client)
    res = await client.patch(
        f"/api/transcriptions/{created['id']}", json={"text": "x", "status": "interrupted"}
    )
    assert res.status_code == 422


async def test_delete(client: AsyncClient) -> None:
    created = await _create(client)
    assert (await client.delete(f"/api/transcriptions/{created['id']}")).status_code == 204
    assert (await client.get(f"/api/transcriptions/{created['id']}")).status_code == 404
    assert (await client.delete(f"/api/transcriptions/{created['id']}")).status_code == 404
