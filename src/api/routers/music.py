import re
import tempfile
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..services.jamendo import download_track
from ..services.storage import StorageService
from ..db.session import get_session
from ..db.repositories import music_repo
from ..schemas.music import MusicCreate, MusicUpdate, MusicResponse

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_\-.]")


def _sanitize_path_component(value: str, max_len: int = 128) -> str:
    """Supprime tout caractère non autorisé et empêche le path traversal."""
    name = os.path.basename(value)          # élimine les segments ../
    name = _SAFE_NAME_RE.sub("_", name)     # remplace les caractères spéciaux
    name = name.strip(".")                  # empêche les noms déguisés en .hidden
    name = name[:max_len]
    if not name:
        raise ValueError("Nom de fichier invalide après sanitisation")
    return name

router = APIRouter(prefix="/music", tags=["music"])


@router.get("", response_model=list[MusicResponse])
async def list_music(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_session)
):
    """List all music with pagination"""
    music_list = music_repo.get_all_music(db, skip=skip, limit=limit)
    return music_list


@router.get("/{title}", response_model=MusicResponse)
async def get_music(title: str, db: Session = Depends(get_session)):
    """Get music by title"""
    music = music_repo.get_music(db, title)
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")
    return music


@router.get("/{title}/download")
async def get_music_download_url(title: str, db: Session = Depends(get_session)):
    """
    Get a presigned download URL for a music file from MinIO.
    The URL expires in 60 minutes.
    """
    music = music_repo.get_music(db, title)
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")

    if not music.file_path:
        raise HTTPException(status_code=400, detail="Music has no associated file")

    try:
        storage = StorageService(bucket_type="music")
        download_url = storage.get_download_url(music.file_path, expires_minutes=60)

        return {
            "title": music.title,
            "file_path": music.file_path,
            "download_url": download_url,
            "expires_in_minutes": 60,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate URL: {str(e)}")


@router.post("", response_model=MusicResponse)
async def create_music(music_data: MusicCreate, db: Session = Depends(get_session)):
    """Create a new music entry"""
    existing_music = music_repo.get_music(db, music_data.title)
    if existing_music:
        raise HTTPException(
            status_code=400, detail="Music with this title already exists"
        )

    music = music_repo.create_music(
        db,
        title=music_data.title,
        artist=music_data.artist,
        bpm=music_data.bpm,
        duration=music_data.duration,
        file_path=music_data.file_path,
    )
    return music


ALLOWED_CONTENT_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/ogg", "audio/flac", "audio/x-flac"}
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 Mo


@router.post("/upload/{title}")
async def upload_music_file(
    title: str, file: UploadFile = File(...), db: Session = Depends(get_session)
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Format non supporté : {file.content_type}. Formats acceptés : mp3, wav, ogg, flac.",
        )

    try:
        safe_title = _sanitize_path_component(title)
        safe_filename = _sanitize_path_component(file.filename or "upload.mp3")

        music = music_repo.get_music(db, title)

        # Lecture par chunks pour limiter la RAM et vérifier la taille
        chunk_size = 64 * 1024  # 64 Ko
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

        # Upload to MinIO
        storage = StorageService(bucket_type="music")
        file_object_name = f"music_files/{safe_title}/{safe_filename}"
        storage.upload_file(file_object_name, temp_path)

        # Get file size
        file_size = os.path.getsize(temp_path)

        # Clean up temp file
        os.unlink(temp_path)

        if music:
            db.execute(
                text("UPDATE music SET file_path = :path WHERE title = :title"),
                {"path": file_object_name, "title": title},
            )
            db.commit()
        else:
            # Create new music entry with file
            music_repo.create_music(
                db,
                title=title,
                artist=None,
                bpm=None,
                duration=None,
                file_path=file_object_name,
            )

        # Generate download URL (valid for 7 days)
        download_url = storage.get_download_url(file_object_name, expires_minutes=10080)

        return {
            "status": "uploaded",
            "title": title,
            "file_path": file_object_name,
            "file_size": file_size,
            "download_url": download_url,
            "bucket_name": "musics",
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Upload failed")


@router.put("/{title}", response_model=MusicResponse)
async def update_music(
    title: str, music_data: MusicUpdate, db: Session = Depends(get_session)
):
    """Update music by title"""
    music = music_repo.get_music(db, title)
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")

    updated_music = music_repo.update_music(
        db,
        title=title,
        artist=music_data.artist,
        bpm=music_data.bpm,
        duration=music_data.duration,
    )
    return updated_music


@router.delete("/{title}")
async def delete_music(title: str, db: Session = Depends(get_session)):
    """Delete music by title"""
    deleted = music_repo.delete_music(db, title)
    if not deleted:
        raise HTTPException(status_code=404, detail="Music not found")
    return {"status": "deleted", "title": title}


@router.post("/import-jamendo/{track_id}")
async def import_jamendo_track(track_id: str):
    """
    Download music from Jamendo and save it to MinIO.
    Returns a presigned URL to download the file.
    """
    try:
        # 1. Download from Jamendo to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            temp_path = tmp.name

        download_track(track_id, temp_path)
        file_size = os.path.getsize(temp_path)

        # 2. Upload to MinIO
        storage = StorageService(bucket_type="music")
        safe_id = _sanitize_path_component(track_id)
        object_name = f"jamendo_{safe_id}.mp3"
        storage.upload_file(object_name, temp_path)

        # 3. Generate download URL for 24h
        download_url = storage.get_download_url(object_name, expires_minutes=1440)

        # 4. Clean up temporary file
        os.unlink(temp_path)

        return {
            "status": "success",
            "track_id": track_id,
            "object_name": object_name,
            "file_size": file_size,
            "download_url": download_url,
        }

    except ValueError as e:
        # Track not found on Jamendo
        raise HTTPException(status_code=404, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
