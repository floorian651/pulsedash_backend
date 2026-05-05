import json
import os
import tempfile

import redis as _sync_redis
from loguru import logger

from src.api.core.celery_app import app
from src.api.db.session import get_session
from src.api.db.repositories import job_repo
from src.api.db.repositories.job_repo import JobState


def _publish(job_id: str, state: str, progress: int, error: str | None = None) -> None:
    from src.api.core.config import get_settings
    settings = get_settings()
    try:
        r = _sync_redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)
        payload: dict = {"job_id": job_id, "state": state, "progress": progress}
        if error:
            payload["error"] = error
        r.publish(f"job:{job_id}", json.dumps(payload))
        r.close()
    except Exception as exc:
        logger.warning(f"Job {job_id}: Redis publish failed — {exc}")


@app.task(name="generate_level")
def generate_level_task(job_id: str, track_id: str, audio_object: str | None = None):
    """Analyse un fichier audio et stocke le level.json dans MinIO.

    Si audio_object est fourni, l'audio est lu depuis le bucket music de MinIO
    (évite un double téléchargement depuis Jamendo).
    """
    db = next(get_session())
    audio_path = None
    level_path = None

    try:
        job_repo.update_job_state(db, job_id, JobState.RUNNING)
        job_repo.update_job_progress(db, job_id, 0)
        _publish(job_id, JobState.RUNNING, 0)
        logger.info(f"Job {job_id}: processing track {track_id}")

        from src.api.services.storage import StorageService

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            audio_path = tmp.name

        if audio_object:
            # Audio déjà dans MinIO — on le récupère directement
            storage_music = StorageService(bucket_type="music")
            storage_music.download_file(audio_object, audio_path)
            job_repo.update_job_progress(db, job_id, 40)
            _publish(job_id, JobState.RUNNING, 40)
            logger.info(f"Job {job_id}: audio fetched from MinIO ({audio_object})")
        else:
            # Téléchargement depuis Jamendo (0 → 20%) puis upload dans MinIO (20 → 40%)
            from src.api.services.jamendo import download_track
            download_track(track_id, audio_path)
            job_repo.update_job_progress(db, job_id, 20)
            _publish(job_id, JobState.RUNNING, 20)
            logger.info(f"Job {job_id}: audio downloaded from Jamendo")

            storage_audio = StorageService(bucket_type="audio")
            storage_audio.upload_file(f"{job_id}/{track_id}.mp3", audio_path)
            job_repo.update_job_progress(db, job_id, 40)
            _publish(job_id, JobState.RUNNING, 40)
            logger.info(f"Job {job_id}: audio uploaded to MinIO")

        # Pipeline d'analyse (40 → 85%)
        from src.pipeline.main import main as run_pipeline
        level_data = run_pipeline(audio_path)
        job_repo.update_job_progress(db, job_id, 85)
        _publish(job_id, JobState.RUNNING, 85)
        logger.info(f"Job {job_id}: pipeline completed — {len(level_data.get('hits', []))} hits")

        # Sauvegarde du level.json dans MinIO (85 → 100%)
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
            json.dump(level_data, tmp)
            level_path = tmp.name

        storage_levels = StorageService(bucket_type="levels")
        level_object = f"{job_id}/level.json"
        storage_levels.upload_file(level_object, level_path)

        job_repo.set_result_path(db, job_id, level_object)
        job_repo.update_job_progress(db, job_id, 100)
        job_repo.update_job_state(db, job_id, JobState.COMPLETED)
        _publish(job_id, JobState.COMPLETED, 100)
        logger.info(f"Job {job_id}: completed")

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"Job {job_id} failed: {error_msg}")
        job_repo.set_error_message(db, job_id, error_msg)
        job_repo.update_job_state(db, job_id, JobState.FAILED)
        _publish(job_id, JobState.FAILED, 0, error=error_msg)
        raise
    finally:
        db.close()
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)
        if level_path and os.path.exists(level_path):
            os.unlink(level_path)
