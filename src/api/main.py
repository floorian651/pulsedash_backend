# Le point d’entrée de l’API.

#     crée l’application FastAPI

#     configure CORS

#     initialise la DB

#     monte les routers

#     expose WebSocket /ws/jobs/{job_id}

# C’est le fichier à lancer avec Uvicorn.

# from fastapi import FastAPI, File, UploadFile

# from src.pipeline.main import main as run_pipeline

import asyncio
import json

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.core.config import get_settings
from src.api.core.limiter import limiter
from src.api.db.session import init_engine, get_session
from src.api.db.repositories import job_repo
from src.api.routers import generate, jobs, music, playlists, tracks
from src.api.services.storage import ensure_buckets_exist
from src.api.utils.websocket_manager import WebSocketManager

settings = get_settings()
ws_manager = WebSocketManager()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

    # ---------------------------------------------------------
    # Rate limiting
    # ---------------------------------------------------------
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ---------------------------------------------------------
    # CORS
    # ---------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------
    # Database init
    # ---------------------------------------------------------
    init_engine(settings.DATABASE_URL)

    # ---------------------------------------------------------
    # MinIO setup
    # ---------------------------------------------------------
    ensure_buckets_exist()

    # ---------------------------------------------------------
    # Routers
    # ---------------------------------------------------------
    app.include_router(
        generate.router, prefix=settings.API_V1_PREFIX, tags=["generate"]
    )

    app.include_router(jobs.router, prefix=settings.API_V1_PREFIX, tags=["jobs"])

    app.include_router(music.router, prefix=settings.API_V1_PREFIX, tags=["music"])

    app.include_router(
        playlists.router, prefix=settings.API_V1_PREFIX, tags=["playlists"]
    )

    app.include_router(tracks.router, prefix=settings.API_V1_PREFIX, tags=["tracks"])

    # ---------------------------------------------------------
    # Healthcheck
    # ---------------------------------------------------------
    @app.get("/")
    async def healthcheck():
        return {"status": "ok", "app": settings.APP_NAME}

    # ---------------------------------------------------------
    # WebSocket: suivi des jobs en temps réel
    # ---------------------------------------------------------
    @app.websocket("/ws/jobs/{job_id}")
    async def job_ws(websocket: WebSocket, job_id: str):
        await ws_manager.connect(job_id, websocket)
        db = next(get_session())
        try:
            last_state = None
            last_progress = -1
            while True:
                job = job_repo.get_job(db, job_id)
                if not job:
                    await websocket.send_text(json.dumps({"error": "job not found"}))
                    break

                state = job.state.value if hasattr(job.state, "value") else job.state
                progress = job.progress or 0

                if state != last_state or progress != last_progress:
                    payload: dict = {"job_id": job_id, "state": state, "progress": progress}
                    error_msg = getattr(job, "error_message", None)
                    if error_msg:
                        payload["error"] = error_msg
                    await websocket.send_text(json.dumps(payload))
                    last_state = state
                    last_progress = progress

                if state in ("completed", "failed"):
                    break

                await asyncio.sleep(1)
        except WebSocketDisconnect:
            pass
        finally:
            ws_manager.disconnect(job_id, websocket)
            db.close()

    return app


app = create_app()
