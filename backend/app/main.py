from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import health, reference, transcriptions, ws
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging([settings.gemini_api_key])

app = FastAPI(title="Multilingual Speech to Text")

if settings.is_development:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router, prefix="/api")
app.include_router(reference.router, prefix="/api")
app.include_router(transcriptions.router, prefix="/api")
app.include_router(ws.router, prefix="/api")


def _mount_frontend() -> None:
    static = Path(settings.static_dir) if settings.static_dir else None
    if static is None or not (static / "index.html").exists():
        return
    app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (static / path).resolve()
        if path and candidate.is_file() and static.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(static / "index.html")


_mount_frontend()
