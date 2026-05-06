import re
import requests as _requests
import tempfile
import uuid
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from src.api.core.limiter import limiter
from src.api.db.session import get_session
from src.api.db.repositories import job_repo, music_repo
from src.api.dependencies import get_current_user
from src.api.schemas.jamendo import ImportAccepted, JamendoTrack
from src.api.services.jamendo import get_track_info, search_tracks
from src.api.services.storage import StorageService
from src.api.services.tasks import generate_level_task

router = APIRouter(prefix="/jamendo", tags=["jamendo"])

_SAFE_RE = re.compile(r"[^A-Za-z0-9_\-.]")


def _safe(value: str, max_len: int = 128) -> str:
    return _SAFE_RE.sub("_", os.path.basename(value))[:max_len]


@router.get("/search", response_model=list[JamendoTrack])
@limiter.limit("30/minute")
async def search_jamendo(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100, description="Titre à rechercher"),
    limit: int = Query(10, ge=1, le=50),
):
    try:
        return search_tracks(q, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Jamendo unavailable: {exc}")


@router.post("/import/{track_id}", response_model=ImportAccepted, status_code=202)
@limiter.limit("10/minute")
async def import_and_generate(
    request: Request,
    track_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """Télécharge un track Jamendo, le stocke dans MinIO, crée l'entrée Music
    et lance la génération du niveau. Retourne un job_id à suivre via WebSocket."""

    # 1. Métadonnées Jamendo
    try:
        info = get_track_info(track_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Jamendo unavailable: {exc}")

    music_title = info["name"]
    audio_url   = info["audiodownload"]
    if not audio_url:
        raise HTTPException(status_code=502, detail="No audio URL returned by Jamendo")

    # 2. Téléchargement de l'audio
    try:
        audio_resp = _requests.get(audio_url, stream=True, timeout=120)
        audio_resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Audio download failed: {exc}")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        for chunk in audio_resp.iter_content(chunk_size=8192):
            tmp.write(chunk)
        tmp_path = tmp.name

    # 3. Upload dans MinIO (bucket music)
    object_name = f"jamendo_{_safe(track_id)}.mp3"
    try:
        storage = StorageService(bucket_type="music")
        storage.upload_file(object_name, tmp_path)
    except Exception as exc:
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {exc}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # 4. Upsert de l'entrée Music en DB
    existing = music_repo.get_music(db, music_title)
    if existing:
        existing.file_path = object_name
        db.commit()
    else:
        music_repo.create_music(
            db,
            title=music_title,
            artist=info["artist_name"],
            bpm=None,
            duration=float(info["duration"]),
            file_path=object_name,
        )

    # 5. Création du job et lancement de la génération
    job_id = str(uuid.uuid4())
    job_repo.create_job(db, job_id=job_id, user_id=str(current_user.id))
    generate_level_task.delay(job_id, track_id, audio_object=object_name)

    return ImportAccepted(job_id=job_id, music_title=music_title, state="pending")
