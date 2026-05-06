"""Tests pour /game-sessions."""

import pytest
from src.api.db.models.Music import Music


@pytest.fixture
def music(db):
    m = Music(title="test-music", artist="Artist", bpm=120.0, duration=180.0,
              bucket_name="musics", file_path="test/file.mp3")
    db.add(m)
    db.commit()
    return m


def _start(auth_client, music_title="test-music"):
    return auth_client.post("/api/v1/game-sessions", json={"music_title": music_title})


def _end(auth_client, session_id, final_score=5000, accuracy: float | None = 0.9, abandoned=False):
    return auth_client.patch(f"/api/v1/game-sessions/{session_id}/end", json={
        "final_score": final_score,
        "accuracy": accuracy,
        "abandoned": abandoned,
    })


# ── Start ──────────────────────────────────────────────────────────────────────

def test_start_session_returns_201(auth_client, music):
    r = _start(auth_client)
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "active"
    assert data["music_title"] == "test-music"
    assert data["ended_at"] is None
    assert data["final_score"] is None
    assert "id" in data


def test_start_session_unknown_music_returns_404(auth_client):
    r = _start(auth_client, music_title="does-not-exist")
    assert r.status_code == 404


def test_start_session_requires_auth(client, music):
    r = client.post("/api/v1/game-sessions", json={"music_title": "test-music"})
    assert r.status_code == 403


def test_start_session_missing_music_title_returns_422(auth_client):
    r = auth_client.post("/api/v1/game-sessions", json={})
    assert r.status_code == 422


# ── End ────────────────────────────────────────────────────────────────────────

def test_end_session_completed(auth_client, music):
    session_id = _start(auth_client).json()["id"]
    r = _end(auth_client, session_id, final_score=7500, accuracy=0.85)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert data["final_score"] == 7500
    assert data["accuracy"] == pytest.approx(0.85)
    assert data["ended_at"] is not None


def test_end_session_abandoned(auth_client, music):
    session_id = _start(auth_client).json()["id"]
    r = _end(auth_client, session_id, final_score=0, accuracy=None, abandoned=True)
    assert r.status_code == 200
    assert r.json()["status"] == "abandoned"


def test_end_session_already_ended_returns_409(auth_client, music):
    session_id = _start(auth_client).json()["id"]
    _end(auth_client, session_id)
    r = _end(auth_client, session_id)
    assert r.status_code == 409


def test_end_session_not_found_returns_404(auth_client):
    r = _end(auth_client, "non-existent-id")
    assert r.status_code == 404


def test_end_session_wrong_user_returns_403(client, music):
    # user A starts a session
    r_a = client.post("/api/v1/auth/register",
                      json={"email": "a@example.com", "password": "password123"})
    token_a = r_a.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token_a}"})
    session_id = _start(client).json()["id"]

    # user B tries to end it
    r_b = client.post("/api/v1/auth/register",
                      json={"email": "b@example.com", "password": "password123"})
    token_b = r_b.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token_b}"})
    r = _end(client, session_id)
    assert r.status_code == 403


def test_end_session_requires_auth(client, music):
    r = client.patch("/api/v1/game-sessions/some-id/end",
                     json={"final_score": 1000, "accuracy": 0.9, "abandoned": False})
    assert r.status_code == 403


def test_end_session_negative_score_returns_422(auth_client, music):
    session_id = _start(auth_client).json()["id"]
    r = auth_client.patch(f"/api/v1/game-sessions/{session_id}/end",
                          json={"final_score": -1, "accuracy": 0.9, "abandoned": False})
    assert r.status_code == 422


def test_end_session_accuracy_out_of_range_returns_422(auth_client, music):
    session_id = _start(auth_client).json()["id"]
    r = auth_client.patch(f"/api/v1/game-sessions/{session_id}/end",
                          json={"final_score": 100, "accuracy": 1.5, "abandoned": False})
    assert r.status_code == 422


# ── Score auto-creation ────────────────────────────────────────────────────────

def test_end_session_completed_creates_score(auth_client, music):
    session_id = _start(auth_client).json()["id"]
    _end(auth_client, session_id, final_score=7500, accuracy=0.85)

    r = auth_client.get("/api/v1/scores/me")
    assert r.status_code == 200
    scores = r.json()
    assert len(scores) == 1
    assert scores[0]["points"] == 7500
    assert scores[0]["music_title"] == "test-music"
    assert scores[0]["session_id"] == session_id


def test_end_session_abandoned_does_not_create_score(auth_client, music):
    session_id = _start(auth_client).json()["id"]
    _end(auth_client, session_id, final_score=0, accuracy=None, abandoned=True)

    r = auth_client.get("/api/v1/scores/me")
    assert r.status_code == 200
    assert r.json() == []


# ── My sessions ────────────────────────────────────────────────────────────────

def test_my_sessions_empty(auth_client):
    r = auth_client.get("/api/v1/game-sessions/me")
    assert r.status_code == 200
    assert r.json() == []


def test_my_sessions_returns_own(auth_client, music):
    _start(auth_client)
    _start(auth_client)
    r = auth_client.get("/api/v1/game-sessions/me")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_my_sessions_ordered_by_date_desc(auth_client, music):
    id1 = _start(auth_client).json()["id"]
    id2 = _start(auth_client).json()["id"]
    r = auth_client.get("/api/v1/game-sessions/me")
    ids = [s["id"] for s in r.json()]
    assert ids[0] == id2


def test_my_sessions_requires_auth(client):
    r = client.get("/api/v1/game-sessions/me")
    assert r.status_code == 403
