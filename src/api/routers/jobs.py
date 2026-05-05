from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..db.models import Job
from ..db.session import get_session
from ..dependencies import get_current_user
from ..services.storage import StorageService

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job non trouvé")

    if str(job.user_id) != str(current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")

    response = {
        "job_id": job.id,
        "state": job.state,
        "progress": job.progress,
        "result_url": None,
    }

    if job.state == "completed" and job.result_path:
        storage = StorageService(bucket_type="levels")
        response["result_url"] = storage.get_download_url(job.result_path)

    return response
