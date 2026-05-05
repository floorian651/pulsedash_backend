"""Tests pour l'endpoint /jobs."""

from src.api.db.repositories import job_repo
from src.api.db.repositories.job_repo import JobState


def _create_job(db, job_id: str = "test-job-123", user_id: str = None) -> str:
    job_repo.create_job(db, job_id=job_id, user_id=user_id)
    return job_id


def test_get_job_pending(auth_client, db):
    user_id = auth_client.get("/api/v1/auth/me").json()["id"]
    job_id = _create_job(db, user_id=user_id)
    response = auth_client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["state"] == "pending"
    assert data["progress"] == 0
    assert data["result_url"] is None


def test_get_job_not_found(auth_client):
    response = auth_client.get("/api/v1/jobs/nonexistent")
    assert response.status_code == 404


def test_get_job_running(auth_client, db):
    user_id = auth_client.get("/api/v1/auth/me").json()["id"]
    job_id = _create_job(db, user_id=user_id)
    job_repo.update_job_state(db, job_id, JobState.RUNNING)
    job_repo.update_job_progress(db, job_id, 40)

    response = auth_client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "running"
    assert data["progress"] == 40


def test_get_job_failed_with_error(auth_client, db):
    user_id = auth_client.get("/api/v1/auth/me").json()["id"]
    job_id = _create_job(db, user_id=user_id)
    job_repo.update_job_state(db, job_id, JobState.FAILED)
    job_repo.set_error_message(db, job_id, "Jamendo track not found")

    response = auth_client.get(f"/api/v1/generate/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "failed"
    assert data["error"] == "Jamendo track not found"


def test_get_job_requires_auth(client, db):
    job_id = _create_job(db)
    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 403


def test_get_job_forbidden_for_other_user(auth_client, db):
    job_id = _create_job(db, user_id="other-user-id")
    response = auth_client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 403
