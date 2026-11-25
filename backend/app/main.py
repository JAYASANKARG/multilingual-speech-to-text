import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import health, reference, transcriptions, ws
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging([settings.gemini_api_key])
log = logging.getLogger(__name__)

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
        # A deployment that forgets STATIC_DIR serves the API but 404s on "/", which is easy to
        # miss. The Docker image sets STATIC_DIR=/app/static; dev uses the Vite server instead.
        level = logging.INFO if settings.is_development else logging.WARNING
        log.log(
            level,
            "Frontend not served: STATIC_DIR=%r has no index.html, so GET / returns 404. "
            "Use the Docker image or the Vite dev server.",
            settings.static_dir,
        )
        return
    log.info("Serving frontend from %s", static)
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
