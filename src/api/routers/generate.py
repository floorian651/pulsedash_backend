import uuid
import json
import tempfile
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.api.core.config import get_settings
from src.api.core.limiter import limiter
from src.api.db.session import get_session
from src.api.db.repositories import job_repo
from src.api.db.repositories.job_repo import JobState
from src.api.schemas.generate import GenerateRequest, GenerateAccepted, GenerateResponse
from src.api.services.tasks import generate_level_task
from src.api.services.storage import StorageService
from src.api.dependencies import get_current_user
from loguru import logger

router = APIRouter()
settings = get_settings()


@router.post("/generate", response_model=GenerateAccepted, status_code=202)
@limiter.limit("10/minute")
async def generate_level(request: Request, body: GenerateRequest, db: Session = Depends(get_session), current_user = Depends(get_current_user)):
    job_id = str(uuid.uuid4())
    job_repo.create_job(db, job_id=job_id, user_id=current_user.id)
    generate_level_task.delay(job_id, body.track_id)
    logger.info(f"Job {job_id} queued for track {body.track_id}")
    return GenerateAccepted(job_id=job_id, state=JobState.PENDING)


@router.get("/generate/{job_id}", response_model=GenerateResponse)
async def get_generate_result(
    job_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    job = job_repo.get_job(db, job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if str(job.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Accès refusé")

    level_data = None

    if job.state == JobState.COMPLETED and job.result_path:
        try:
            level_data = _get_level_from_minio(job.result_path)
        except Exception as exc:
            logger.error(f"Failed to retrieve level from MinIO: {exc}")

    return GenerateResponse(
        job_id=job_id,
        state=job.state,
        progress=job.progress or 0,
        level=level_data,
        error=getattr(job, "error_message", None),
    )


def _get_level_from_minio(result_path: str) -> dict:
    storage = StorageService(bucket_type="levels")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        storage.download_file(result_path, tmp_path)
        with open(tmp_path, "r") as f:
            return json.load(f)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
