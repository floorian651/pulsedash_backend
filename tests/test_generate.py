"""Tests pour POST /generate et GET /jobs/{job_id}."""
import io

MUSIC_FORM = {"title": "Darude Sandstorm", "artist": "Darude", "bpm": 128.0, "duration": 224.0}
GENERATE_BODY = {"music_title": "Darude Sandstorm"}


def _create_music_with_file(auth_client, mock_storage):
    auth_client.post(
        "/api/v1/music",
        data=MUSIC_FORM,
        files={"file": ("track.mp3", io.BytesIO(b"ID3" + b"\x00" * 100), "audio/mpeg")},
    )


# ── POST /generate ─────────────────────────────────────────────────────────────

def test_generate_returns_202(auth_client, mock_celery, mock_storage):
    _create_music_with_file(auth_client, mock_storage)
    r = auth_client.post("/api/v1/generate", json=GENERATE_BODY)
    assert r.status_code == 202
    data = r.json()
    assert "job_id" in data
    assert data["state"] == "pending"


def test_generate_queues_celery_task_with_audio_object(auth_client, mock_celery, mock_storage):
    _create_music_with_file(auth_client, mock_storage)
    auth_client.post("/api/v1/generate", json=GENERATE_BODY)
    mock_celery.delay.assert_called_once()
    _, kwargs = mock_celery.delay.call_args
    assert kwargs.get("audio_object") is not None


def test_generate_music_not_found_returns_404(auth_client, mock_celery):
    r = auth_client.post("/api/v1/generate", json={"music_title": "nonexistent"})
    assert r.status_code == 404


def test_generate_music_without_file_returns_400(auth_client, mock_celery):
    auth_client.post("/api/v1/music", data=MUSIC_FORM)
    r = auth_client.post("/api/v1/generate", json=GENERATE_BODY)
    assert r.status_code == 400


def test_generate_missing_body_returns_422(auth_client, mock_celery):
    assert auth_client.post("/api/v1/generate", json={}).status_code == 422


def test_generate_each_call_creates_unique_job(auth_client, mock_celery, mock_storage):
    _create_music_with_file(auth_client, mock_storage)
    r1 = auth_client.post("/api/v1/generate", json=GENERATE_BODY)
    r2 = auth_client.post("/api/v1/generate", json=GENERATE_BODY)
    assert r1.json()["job_id"] != r2.json()["job_id"]


def test_generate_without_token_returns_403(client, mock_celery):
    assert client.post("/api/v1/generate", json=GENERATE_BODY).status_code == 403


# ── GET /jobs/{job_id} ─────────────────────────────────────────────────────────

def test_get_job_pending(auth_client, mock_celery, mock_storage):
    _create_music_with_file(auth_client, mock_storage)
    job_id = auth_client.post("/api/v1/generate", json=GENERATE_BODY).json()["job_id"]
    r = auth_client.get(f"/api/v1/jobs/{job_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["job_id"] == job_id
    assert data["state"] == "pending"
    assert data["progress"] == 0
    assert data["result_url"] is None
    assert data["error"] is None


def test_get_job_not_found_returns_404(auth_client):
    assert auth_client.get("/api/v1/jobs/nonexistent-id").status_code == 404
