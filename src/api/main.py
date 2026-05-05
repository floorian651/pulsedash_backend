import asyncio
import json

import redis.asyncio as redis_asyncio
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.core.config import get_settings
from src.api.core.limiter import limiter
from src.api.db.session import init_engine, get_session
from src.api.db.repositories import job_repo, user_repo
from src.api.routers import auth, game_sessions, generate, jamendo, jobs, music, playlists, profile, scores, tracks
from src.api.services.auth import decode_token
from src.api.services.storage import ensure_buckets_exist
from src.api.utils.websocket_manager import WebSocketManager

settings = get_settings()
ws_manager = WebSocketManager()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    init_engine(settings.DATABASE_URL)
    ensure_buckets_exist()

    app.include_router(auth.router, prefix=settings.API_V1_PREFIX, tags=["auth"])
    app.include_router(jamendo.router, prefix=settings.API_V1_PREFIX, tags=["jamendo"])
    app.include_router(generate.router, prefix=settings.API_V1_PREFIX, tags=["generate"])
    app.include_router(jobs.router, prefix=settings.API_V1_PREFIX, tags=["jobs"])
    app.include_router(music.router, prefix=settings.API_V1_PREFIX, tags=["music"])
    app.include_router(playlists.router, prefix=settings.API_V1_PREFIX, tags=["playlists"])
    app.include_router(tracks.router, prefix=settings.API_V1_PREFIX, tags=["tracks"])
    app.include_router(scores.router, prefix=settings.API_V1_PREFIX, tags=["scores"])
    app.include_router(game_sessions.router, prefix=settings.API_V1_PREFIX, tags=["game-sessions"])
    app.include_router(profile.router, prefix=settings.API_V1_PREFIX, tags=["profile"])

    @app.get("/")
    async def healthcheck():
        return {"status": "ok", "app": settings.APP_NAME}

    @app.websocket("/ws/jobs/{job_id}")
    async def job_ws(websocket: WebSocket, job_id: str, token: str = Query(...)):
        # ── Auth ─────────────────────────────────────────────────────────────
        db = next(get_session())
        try:
            user_id = decode_token(token)
        except Exception:
            await websocket.close(code=1008)
            db.close()
            return

        user = user_repo.get_user_by_id(db, user_id)
        if not user or not user.is_active:
            await websocket.close(code=1008)
            db.close()
            return
        db.close()

        await ws_manager.connect(job_id, websocket)

        redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
        r = redis_asyncio.from_url(redis_url)
        pubsub = r.pubsub()

        try:
            # Souscrire avant de lire la DB pour ne rater aucun publish
            await pubsub.subscribe(f"job:{job_id}")

            db = next(get_session())
            job = job_repo.get_job(db, job_id)
            db.close()

            if not job:
                await websocket.send_text(json.dumps({"error": "job not found"}))
                return
            if str(job.user_id) != user_id:
                await websocket.close(code=1008)
                return

            state = job.state.value if hasattr(job.state, "value") else job.state
            progress = job.progress or 0
            payload: dict = {"job_id": job_id, "state": state, "progress": progress}
            if getattr(job, "error_message", None):
                payload["error"] = job.error_message
            await websocket.send_text(json.dumps(payload))

            if state in ("completed", "failed"):
                return

            # Relayer les messages Redis vers le WebSocket
            async def _forward():
                async for message in pubsub.listen():
                    if message["type"] != "message":
                        continue
                    data = json.loads(message["data"])
                    await websocket.send_text(json.dumps(data))
                    if data.get("state") in ("completed", "failed"):
                        return

            redis_task = asyncio.create_task(_forward())
            ws_task = asyncio.create_task(websocket.receive())

            done, pending = await asyncio.wait(
                {redis_task, ws_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

        except WebSocketDisconnect:
            pass
        finally:
            await pubsub.unsubscribe(f"job:{job_id}")
            await r.aclose()
            ws_manager.disconnect(job_id, websocket)

    return app


app = create_app()
