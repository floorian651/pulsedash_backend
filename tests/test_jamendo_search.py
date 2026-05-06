"""Tests pour GET /jamendo/search et POST /jamendo/import/{track_id}."""

from unittest.mock import MagicMock, patch

FAKE_RESULTS = [
    {"id": "114069", "name": "Darude Sandstorm", "artist_name": "Darude",
     "duration": 224, "image": "http://img/cover.jpg", "audio": "http://cdn/track.mp3"},
    {"id": "222222", "name": "Darude Rush", "artist_name": "Darude",
     "duration": 180, "image": None, "audio": "http://cdn/track2.mp3"},
]

FAKE_TRACK_INFO = {
    "id": "114069",
    "name": "Darude Sandstorm",
    "artist_name": "Darude",
    "duration": 224,
    "audiodownload": "http://cdn/darude.mp3",
}


def _mock_search(results=None):
    return patch(
        "src.api.routers.jamendo.search_tracks",
        return_value=results if results is not None else FAKE_RESULTS,
    )


# ── Search ─────────────────────────────────────────────────────────────────────

def test_search_returns_results(client):
    with _mock_search():
        r = client.get("/api/v1/jamendo/search?q=darude")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["id"] == "114069"
    assert data[0]["name"] == "Darude Sandstorm"
    assert data[0]["artist_name"] == "Darude"
    assert data[0]["duration"] == 224


def test_search_empty_query_returns_422(client):
    r = client.get("/api/v1/jamendo/search?q=")
    assert r.status_code == 422


def test_search_missing_query_returns_422(client):
    r = client.get("/api/v1/jamendo/search")
    assert r.status_code == 422


def test_search_query_too_long_returns_422(client):
    r = client.get(f"/api/v1/jamendo/search?q={'a' * 101}")
    assert r.status_code == 422


def test_search_limit_respected(client):
    with _mock_search([FAKE_RESULTS[0]]):
        r = client.get("/api/v1/jamendo/search?q=darude&limit=1")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_search_limit_max_50(client):
    r = client.get("/api/v1/jamendo/search?q=test&limit=51")
    assert r.status_code == 422


def test_search_empty_results(client):
    with _mock_search([]):
        r = client.get("/api/v1/jamendo/search?q=xyznotfound")
    assert r.status_code == 200
    assert r.json() == []


def test_search_jamendo_unavailable_returns_502(client):
    with patch("src.api.routers.jamendo.search_tracks", side_effect=Exception("timeout")):
        r = client.get("/api/v1/jamendo/search?q=darude")
    assert r.status_code == 502


def test_search_result_fields(client):
    with _mock_search():
        r = client.get("/api/v1/jamendo/search?q=darude")
    track = r.json()[0]
    for field in ("id", "name", "artist_name", "duration", "image", "audio"):
        assert field in track


def test_search_nullable_image(client):
    with _mock_search():
        r = client.get("/api/v1/jamendo/search?q=darude")
    assert r.json()[1]["image"] is None


# ── Import & Generate ──────────────────────────────────────────────────────────

def _mock_import(info=None, audio_content=b"fakemp3"):
    """Context managers pour simuler get_track_info, download HTTP et MinIO."""
    import io
    import requests as _req

    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.iter_content = MagicMock(return_value=[audio_content])

    mock_info   = patch("src.api.routers.jamendo.get_track_info", return_value=info or FAKE_TRACK_INFO)
    mock_req    = patch("src.api.routers.jamendo._requests.get", return_value=fake_response)
    mock_storage = patch("src.api.routers.jamendo.StorageService")
    mock_celery  = patch("src.api.routers.jamendo.generate_level_task")
    return mock_info, mock_req, mock_storage, mock_celery


def test_import_returns_202(auth_client):
    mi, mr, ms, mc = _mock_import()
    with mi, mr, ms as MockStorage, mc as mock_task:
        MockStorage.return_value.upload_file = MagicMock()
        mock_task.delay = MagicMock()
        r = auth_client.post("/api/v1/jamendo/import/114069")
    assert r.status_code == 202
    data = r.json()
    assert data["state"] == "pending"
    assert data["music_title"] == "Darude Sandstorm"
    assert "job_id" in data


def test_import_requires_auth(client):
    r = client.post("/api/v1/jamendo/import/114069")
    assert r.status_code == 403


def test_import_creates_music_entry(auth_client, db):
    from src.api.db.models.Music import Music
    mi, mr, ms, mc = _mock_import()
    with mi, mr, ms as MockStorage, mc as mock_task:
        MockStorage.return_value.upload_file = MagicMock()
        mock_task.delay = MagicMock()
        auth_client.post("/api/v1/jamendo/import/114069")
    music = db.query(Music).filter(Music.title == "Darude Sandstorm").first()
    assert music is not None
    assert music.artist == "Darude"
    assert music.duration == 224.0


def test_import_creates_job(auth_client, db):
    from src.api.db.models.Job import Job
    mi, mr, ms, mc = _mock_import()
    with mi, mr, ms as MockStorage, mc as mock_task:
        MockStorage.return_value.upload_file = MagicMock()
        mock_task.delay = MagicMock()
        r = auth_client.post("/api/v1/jamendo/import/114069")
    job_id = r.json()["job_id"]
    job = db.query(Job).filter(Job.id == job_id).first()
    assert job is not None


def test_import_queues_celery_task_with_audio_object(auth_client):
    mi, mr, ms, mc = _mock_import()
    with mi, mr, ms as MockStorage, mc as mock_task:
        MockStorage.return_value.upload_file = MagicMock()
        mock_task.delay = MagicMock()
        auth_client.post("/api/v1/jamendo/import/114069")
    mock_task.delay.assert_called_once()
    _, kwargs = mock_task.delay.call_args
    assert kwargs.get("audio_object") == "jamendo_114069.mp3"


def test_import_track_not_found_returns_404(auth_client):
    with patch("src.api.routers.jamendo.get_track_info",
               side_effect=ValueError("Track xyz not found on Jamendo")):
        r = auth_client.post("/api/v1/jamendo/import/xyz")
    assert r.status_code == 404


def test_import_jamendo_unavailable_returns_502(auth_client):
    with patch("src.api.routers.jamendo.get_track_info",
               side_effect=Exception("network error")):
        r = auth_client.post("/api/v1/jamendo/import/114069")
    assert r.status_code == 502


def test_import_upserts_existing_music(auth_client, db):
    """Si la musique existe déjà, file_path est mis à jour sans doublon."""
    from src.api.db.models.Music import Music
    existing = Music(title="Darude Sandstorm", artist="Darude", bpm=None,
                     duration=200.0, bucket_name="musics", file_path="old_path.mp3")
    db.add(existing)
    db.commit()

    mi, mr, ms, mc = _mock_import()
    with mi, mr, ms as MockStorage, mc as mock_task:
        MockStorage.return_value.upload_file = MagicMock()
        mock_task.delay = MagicMock()
        auth_client.post("/api/v1/jamendo/import/114069")

    db.expire_all()
    entries = db.query(Music).filter(Music.title == "Darude Sandstorm").all()
    assert len(entries) == 1
    assert entries[0].file_path == "jamendo_114069.mp3"
