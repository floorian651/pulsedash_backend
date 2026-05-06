"""Tests pour les scores et le leaderboard.

Les scores sont créés automatiquement en terminant une game session (non abandonnée).
"""

import pytest
from src.api.db.models.Music import Music


@pytest.fixture
def music(db):
    m = Music(title="test-music", artist="Artist", bpm=120.0, duration=180.0,
              bucket_name="musics", file_path="test/file.mp3")
    db.add(m)
    db.commit()
    return m


def _submit(auth_client, music_title="test-music", points=1000, accuracy=0.95):
    """Joue une session complète et retourne le session_id."""
    r = auth_client.post("/api/v1/game-sessions", json={"music_title": music_title})
    session_id = r.json()["id"]
    auth_client.patch(f"/api/v1/game-sessions/{session_id}/end", json={
        "final_score": points,
        "accuracy": accuracy,
        "abandoned": False,
    })
    return session_id


# ── Création de score ──────────────────────────────────────────────────────────

def test_submit_score_creates_entry(auth_client, music):
    _submit(auth_client, points=1000)
    r = auth_client.get("/api/v1/scores/me")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["points"] == 1000
    assert data[0]["music_title"] == "test-music"
    assert "user_id" in data[0]
    assert "id" in data[0]


def test_abandoned_session_does_not_create_score(auth_client, music):
    r = auth_client.post("/api/v1/game-sessions", json={"music_title": "test-music"})
    session_id = r.json()["id"]
    auth_client.patch(f"/api/v1/game-sessions/{session_id}/end", json={
        "final_score": 0,
        "accuracy": None,
        "abandoned": True,
    })
    r = auth_client.get("/api/v1/scores/me")
    assert r.status_code == 200
    assert r.json() == []


def test_submit_score_negative_points_returns_422(auth_client, music):
    r = auth_client.post("/api/v1/game-sessions", json={"music_title": "test-music"})
    session_id = r.json()["id"]
    r = auth_client.patch(f"/api/v1/game-sessions/{session_id}/end", json={
        "final_score": -1,
        "accuracy": 0.9,
        "abandoned": False,
    })
    assert r.status_code == 422


def test_submit_score_accuracy_out_of_range_returns_422(auth_client, music):
    r = auth_client.post("/api/v1/game-sessions", json={"music_title": "test-music"})
    session_id = r.json()["id"]
    r = auth_client.patch(f"/api/v1/game-sessions/{session_id}/end", json={
        "final_score": 100,
        "accuracy": 1.5,
        "abandoned": False,
    })
    assert r.status_code == 422


def test_submit_requires_auth(client, music):
    r = client.post("/api/v1/game-sessions", json={"music_title": "test-music"})
    assert r.status_code == 403


# ── Leaderboard par musique ───────────────────────────────────────────────────

def test_leaderboard_empty(client):
    response = client.get("/api/v1/scores/top?music_title=unknown-music")
    assert response.status_code == 200
    assert response.json() == []


def test_leaderboard_ordered_by_points(auth_client, music):
    _submit(auth_client, points=500)
    _submit(auth_client, points=9000)
    _submit(auth_client, points=3000)

    response = auth_client.get("/api/v1/scores/top?music_title=test-music")
    assert response.status_code == 200
    entries = response.json()
    assert entries[0]["points"] == 9000
    assert entries[0]["rank"] == 1
    assert entries[1]["points"] == 3000
    assert entries[2]["points"] == 500


def test_leaderboard_limit(auth_client, music):
    for i in range(15):
        _submit(auth_client, points=i * 100)

    response = auth_client.get("/api/v1/scores/top?music_title=test-music&limit=5")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_leaderboard_limit_max_100(client):
    response = client.get("/api/v1/scores/top?music_title=t&limit=200")
    assert response.status_code == 422


# ── Mes scores ────────────────────────────────────────────────────────────────

def test_my_scores_empty(auth_client):
    response = auth_client.get("/api/v1/scores/me")
    assert response.status_code == 200
    assert response.json() == []


def test_my_scores_returns_own(auth_client, music):
    _submit(auth_client, points=100)
    _submit(auth_client, points=200)

    response = auth_client.get("/api/v1/scores/me")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_my_scores_ordered_by_date_desc(auth_client, music):
    _submit(auth_client, points=100)
    _submit(auth_client, points=500)

    response = auth_client.get("/api/v1/scores/me")
    data = response.json()
    assert data[0]["points"] == 500


def test_my_scores_requires_auth(client):
    response = client.get("/api/v1/scores/me")
    assert response.status_code == 403


# ── Username dans le leaderboard ──────────────────────────────────────────────

def test_leaderboard_entry_has_username_field(auth_client, music):
    _submit(auth_client, points=1000)
    response = auth_client.get("/api/v1/scores/top?music_title=test-music")
    assert response.status_code == 200
    assert "username" in response.json()[0]


def test_leaderboard_entry_username_is_none_without_username(auth_client, music):
    _submit(auth_client, points=500)
    response = auth_client.get("/api/v1/scores/top?music_title=test-music")
    assert response.json()[0]["username"] is None


def test_leaderboard_entry_username_populated(client, db):
    m = Music(title="test-music", artist="Artist", bpm=120.0, duration=180.0,
              bucket_name="musics", file_path="test/file.mp3")
    db.add(m)
    db.commit()

    client.post("/api/v1/auth/register",
                json={"email": "pro@example.com", "password": "pass1234", "username": "ProGamer"})
    r = client.post("/api/v1/auth/login",
                    json={"email": "pro@example.com", "password": "pass1234"})
    client.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})

    r = client.post("/api/v1/game-sessions", json={"music_title": "test-music"})
    session_id = r.json()["id"]
    client.patch(f"/api/v1/game-sessions/{session_id}/end",
                 json={"final_score": 9999, "accuracy": None, "abandoned": False})

    response = client.get("/api/v1/scores/top?music_title=test-music")
    assert response.json()[0]["username"] == "ProGamer"


# ── Leaderboard global ────────────────────────────────────────────────────────

def test_global_leaderboard_empty(client):
    response = client.get("/api/v1/scores/global")
    assert response.status_code == 200
    assert response.json() == []


def test_global_leaderboard_aggregates_points(auth_client, music):
    _submit(auth_client, points=1000)
    _submit(auth_client, points=2000)
    _submit(auth_client, points=500)

    response = auth_client.get("/api/v1/scores/global")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["total_points"] == 3500
    assert data[0]["games_played"] == 3
    assert data[0]["rank"] == 1


def test_global_leaderboard_ordered_by_total_points(client, db):
    m = Music(title="test-music", artist="Artist", bpm=120.0, duration=180.0,
              bucket_name="musics", file_path="test/file.mp3")
    db.add(m)
    db.commit()

    r_a = client.post("/api/v1/auth/register",
                      json={"email": "a@ex.com", "password": "pass1234"})
    client.headers.update({"Authorization": f"Bearer {r_a.json()['access_token']}"})
    for pts in [3000, 2000]:
        r = client.post("/api/v1/game-sessions", json={"music_title": "test-music"})
        client.patch(f"/api/v1/game-sessions/{r.json()['id']}/end",
                     json={"final_score": pts, "accuracy": None, "abandoned": False})

    r_b = client.post("/api/v1/auth/register",
                      json={"email": "b@ex.com", "password": "pass1234"})
    client.headers.update({"Authorization": f"Bearer {r_b.json()['access_token']}"})
    r = client.post("/api/v1/game-sessions", json={"music_title": "test-music"})
    client.patch(f"/api/v1/game-sessions/{r.json()['id']}/end",
                 json={"final_score": 1000, "accuracy": None, "abandoned": False})

    response = client.get("/api/v1/scores/global")
    data = response.json()
    assert data[0]["total_points"] == 5000
    assert data[0]["rank"] == 1
    assert data[1]["total_points"] == 1000
    assert data[1]["rank"] == 2


def test_global_leaderboard_limit(auth_client, music):
    for i in range(5):
        _submit(auth_client, points=(i + 1) * 100)

    response = auth_client.get("/api/v1/scores/global?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 1  # 1 seul user, peu importe la limit


def test_global_leaderboard_has_username_field(auth_client, music):
    _submit(auth_client, points=100)
    response = auth_client.get("/api/v1/scores/global")
    assert "username" in response.json()[0]
