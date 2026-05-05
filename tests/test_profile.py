"""Tests pour /profile."""

import pytest
from src.api.db.models.Music import Music


@pytest.fixture
def music(db):
    m = Music(title="song-a", artist="Artist", bpm=128.0, duration=200.0,
              bucket_name="musics", file_path="test/a.mp3")
    db.add(m)
    db.commit()
    return m


def _start(auth_client, music_title="song-a"):
    return auth_client.post("/api/v1/game-sessions", json={"music_title": music_title})


def _end(auth_client, session_id, score=3000, accuracy=0.8, abandoned=False):
    return auth_client.patch(f"/api/v1/game-sessions/{session_id}/end", json={
        "final_score": score,
        "accuracy": accuracy,
        "abandoned": abandoned,
    })


# ── /profile/me ───────────────────────────────────────────────────────────────

def test_my_profile_no_games(auth_client):
    r = auth_client.get("/api/v1/profile/me")
    assert r.status_code == 200
    data = r.json()
    assert data["stats"]["total_games"] == 0
    assert data["stats"]["completed_games"] == 0
    assert data["stats"]["total_points"] == 0
    assert data["stats"]["best_score"] is None
    assert data["stats"]["average_accuracy"] is None


def test_my_profile_after_completed_game(auth_client, music):
    sid = _start(auth_client).json()["id"]
    _end(auth_client, sid, score=5000, accuracy=0.9)

    r = auth_client.get("/api/v1/profile/me")
    assert r.status_code == 200
    stats = r.json()["stats"]
    assert stats["total_games"] == 1
    assert stats["completed_games"] == 1
    assert stats["total_points"] == 5000
    assert stats["best_score"] == 5000
    assert stats["average_accuracy"] == pytest.approx(0.9, abs=1e-4)


def test_my_profile_abandoned_not_counted_in_completed(auth_client, music):
    sid = _start(auth_client).json()["id"]
    _end(auth_client, sid, score=0, abandoned=True)

    r = auth_client.get("/api/v1/profile/me")
    stats = r.json()["stats"]
    assert stats["total_games"] == 1
    assert stats["completed_games"] == 0
    assert stats["total_points"] == 0
    assert stats["best_score"] is None


def test_my_profile_multiple_games_best_score(auth_client, music):
    for score in [1000, 8000, 3000]:
        sid = _start(auth_client).json()["id"]
        _end(auth_client, sid, score=score, accuracy=0.7)

    r = auth_client.get("/api/v1/profile/me")
    stats = r.json()["stats"]
    assert stats["total_games"] == 3
    assert stats["completed_games"] == 3
    assert stats["total_points"] == 12000
    assert stats["best_score"] == 8000


def test_my_profile_average_accuracy(auth_client, music):
    for acc in [0.6, 0.8, 1.0]:
        sid = _start(auth_client).json()["id"]
        _end(auth_client, sid, score=1000, accuracy=acc)

    r = auth_client.get("/api/v1/profile/me")
    stats = r.json()["stats"]
    assert stats["average_accuracy"] == pytest.approx(0.8, abs=1e-4)


def test_my_profile_has_username(client):
    client.post("/api/v1/auth/register",
                json={"email": "named@example.com", "password": "pass1234",
                      "username": "speedrunner"})
    r = client.post("/api/v1/auth/login",
                    json={"email": "named@example.com", "password": "pass1234"})
    token = r.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    r = client.get("/api/v1/profile/me")
    assert r.status_code == 200
    assert r.json()["username"] == "speedrunner"


def test_my_profile_requires_auth(client):
    r = client.get("/api/v1/profile/me")
    assert r.status_code == 403


# ── /profile/{user_id} ────────────────────────────────────────────────────────

def test_public_profile_exists(auth_client, music):
    sid = _start(auth_client).json()["id"]
    _end(auth_client, sid, score=2000)

    user_id = auth_client.get("/api/v1/auth/me").json()["id"]
    r = auth_client.get(f"/api/v1/profile/{user_id}")
    assert r.status_code == 200
    assert r.json()["stats"]["total_games"] == 1


def test_public_profile_not_found_returns_404(client):
    r = client.get("/api/v1/profile/non-existent-uuid")
    assert r.status_code == 404


def test_public_profile_no_auth_required(client):
    r_reg = client.post("/api/v1/auth/register",
                        json={"email": "pub@example.com", "password": "pass1234"})
    token = r_reg.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    user_id = client.get("/api/v1/auth/me").json()["id"]
    client.headers.clear()

    r = client.get(f"/api/v1/profile/{user_id}")
    assert r.status_code == 200
