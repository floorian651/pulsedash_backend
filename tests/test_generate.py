"""Tests pour l'endpoint /generate (création et suivi de jobs)."""


def test_generate_returns_202(auth_client, mock_celery):
    response = auth_client.post("/api/v1/generate", json={"track_id": "114069"})
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["state"] == "pending"


def test_generate_queues_celery_task(auth_client, mock_celery):
    auth_client.post("/api/v1/generate", json={"track_id": "114069"})
    mock_celery.delay.assert_called_once()
    args = mock_celery.delay.call_args[0]
    assert args[1] == "114069"


def test_generate_missing_track_id_returns_422(auth_client, mock_celery):
    response = auth_client.post("/api/v1/generate", json={})
    assert response.status_code == 422


def test_generate_each_call_creates_unique_job(auth_client, mock_celery):
    r1 = auth_client.post("/api/v1/generate", json={"track_id": "111"})
    r2 = auth_client.post("/api/v1/generate", json={"track_id": "222"})
    assert r1.json()["job_id"] != r2.json()["job_id"]


def test_generate_without_token_returns_403(client, mock_celery):
    response = client.post("/api/v1/generate", json={"track_id": "114069"})
    assert response.status_code == 403


def test_get_generate_pending_job(auth_client, mock_celery):
    job_id = auth_client.post("/api/v1/generate", json={"track_id": "114069"}).json()["job_id"]

    response = auth_client.get(f"/api/v1/generate/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["state"] == "pending"
    assert data["progress"] == 0
    assert data["level"] is None


def test_get_generate_unknown_job_returns_404(auth_client):
    response = auth_client.get("/api/v1/generate/nonexistent-job-id")
    assert response.status_code == 404
