import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from src.api.core.limiter import limiter
from src.api.db.session import get_session
from src.api.db.repositories import job_repo, music_repo
from src.api.db.repositories.job_repo import JobState
from src.api.schemas.generate import GenerateRequest, GenerateAccepted
from src.api.services.tasks import generate_level_task
from src.api.dependencies import get_current_user
from loguru import logger

router = APIRouter()


@router.post("/generate", response_model=GenerateAccepted, status_code=202)
@limiter.limit("10/minute")
async def generate_level(
    request: Request,
    body: GenerateRequest,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    music = music_repo.get_music(db, body.music_title)
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")
    if not music.file_path:
        raise HTTPException(status_code=400, detail="Music has no audio file in storage")

    job_id = str(uuid.uuid4())
    job_repo.create_job(db, job_id=job_id, user_id=str(current_user.id))
    generate_level_task.delay(job_id, body.music_title, audio_object=str(music.file_path))
    logger.info(f"Job {job_id} queued for music '{body.music_title}'")
    return GenerateAccepted(job_id=job_id, state=JobState.PENDING)
