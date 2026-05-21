import re
import tempfile
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, File, Form, UploadFile
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from ..dependencies import get_current_user, get_admin_user
from ..services.storage import StorageService
from ..db.session import get_session
from ..db.repositories import music_repo
from ..schemas.music import MusicUpdate, MusicResponse

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_\-.]")


def _sanitize_path_component(value: str, max_len: int = 128) -> str:
    name = os.path.basename(value)
    name = _SAFE_NAME_RE.sub("_", name)
    name = name.strip(".")
    name = name[:max_len]
    if not name:
        raise ValueError("Nom de fichier invalide après sanitisation")
    return name


ALLOWED_CONTENT_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/flac", "audio/x-flac"}
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 Mo

router = APIRouter(prefix="/music", tags=["music"])


@router.get("", response_model=list[MusicResponse])
async def list_music(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_session)
):
    return music_repo.get_all_music(db, skip=skip, limit=limit)


@router.get("/{title}", response_model=MusicResponse)
async def get_music(title: str, db: Session = Depends(get_session)):
    music = music_repo.get_music(db, title)
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")
    return music


@router.get("/{title}/download")
async def get_music_download_url(title: str, db: Session = Depends(get_session)):
    music = music_repo.get_music(db, title)
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")
    if not music.file_path:
        raise HTTPException(status_code=400, detail="Music has no associated file")
    try:
        storage = StorageService(bucket_type="music")
        return storage.get_download_response(music.file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prepare download response: {str(e)}")


@router.get("/{title}/level")
async def get_music_level(title: str, db: Session = Depends(get_session)):
    music = music_repo.get_music(db, title)
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")
    if not music.level_path:
        raise HTTPException(status_code=404, detail="Level not generated yet")
    try:
        storage = StorageService(bucket_type="levels")
        return storage.get_download_response(music.level_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to prepare download response: {str(e)}")


@router.post("", response_model=MusicResponse)
async def create_music(
    title: str = Form(...),
    artist: Optional[str] = Form(None),
    bpm: Optional[float] = Form(None),
    duration: Optional[float] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_session),
    _=Depends(get_current_user),
):
    if music_repo.get_music(db, title):
        raise HTTPException(status_code=400, detail="Music with this title already exists")

    file_path = None

    if file is not None:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Format non supporté : {file.content_type}. Formats acceptés : mp3, wav, ogg, flac.",
            )
        try:
            safe_title = _sanitize_path_component(title)
            safe_filename = _sanitize_path_component(file.filename or "upload.mp3")

            chunk_size = 64 * 1024
            contents = b""
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                contents += chunk
                if len(contents) > MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Fichier trop volumineux. Limite : {MAX_UPLOAD_SIZE // 1024 // 1024} Mo.",
                    )

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(contents)
                temp_path = tmp.name

            try:
                storage = StorageService(bucket_type="music")
                file_path = f"music_files/{safe_title}/{safe_filename}"
                storage.upload_file(file_path, temp_path)
            finally:
                os.unlink(temp_path)

        except HTTPException:
            raise
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            raise HTTPException(status_code=500, detail="Upload failed")

    return music_repo.create_music(db, title=title, artist=artist, bpm=bpm, duration=duration, file_path=file_path)


@router.put("/{title}", response_model=MusicResponse)
async def update_music(
    title: str, music_data: MusicUpdate, db: Session = Depends(get_session), _=Depends(get_admin_user)
):
    music = music_repo.get_music(db, title)
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")
    return music_repo.update_music(db, title=title, artist=music_data.artist, bpm=music_data.bpm, duration=music_data.duration)


@router.delete("/{title}")
async def delete_music(title: str, db: Session = Depends(get_session), _=Depends(get_admin_user)):
    if not music_repo.delete_music(db, title):
        raise HTTPException(status_code=404, detail="Music not found")
    return {"status": "deleted", "title": title}
