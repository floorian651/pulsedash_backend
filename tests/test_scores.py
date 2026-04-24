"""Tests pour /scores."""


def _submit(client, user_id="user-1", track_id="track-42", points=1000, accuracy=0.95):
    return client.post("/api/v1/scores", json={
        "user_id": user_id,
        "track_id": track_id,
        "points": points,
        "accuracy": accuracy,
    })


def test_submit_score(client):
    response = _submit(client)
    assert response.status_code == 201
    data = response.json()
    assert data["points"] == 1000
    assert data["track_id"] == "track-42"
    assert data["user_id"] == "user-1"
    assert "id" in data


def test_submit_score_missing_fields_returns_422(client):
    response = client.post("/api/v1/scores", json={"points": 500})
    assert response.status_code == 422


def test_submit_score_negative_points_returns_422(client):
    response = client.post("/api/v1/scores", json={
        "user_id": "u1", "track_id": "t1", "points": -10
    })
    assert response.status_code == 422


def test_submit_score_accuracy_out_of_range_returns_422(client):
    response = client.post("/api/v1/scores", json={
        "user_id": "u1", "track_id": "t1", "points": 100, "accuracy": 1.5
    })
    assert response.status_code == 422


def test_leaderboard_empty(client):
    response = client.get("/api/v1/scores/top?track_id=unknown-track")
    assert response.status_code == 200
    assert response.json() == []


def test_leaderboard_ordered_by_points(client):
    _submit(client, user_id="alice", points=500)
    _submit(client, user_id="bob",   points=9000)
    _submit(client, user_id="carol", points=3000)

    response = client.get("/api/v1/scores/top?track_id=track-42")
    assert response.status_code == 200
    entries = response.json()
    assert entries[0]["user_id"] == "bob"
    assert entries[0]["rank"] == 1
    assert entries[1]["user_id"] == "carol"
    assert entries[2]["user_id"] == "alice"


def test_leaderboard_limit(client):
    for i in range(15):
        _submit(client, user_id=f"user-{i}", points=i * 100)

    response = client.get("/api/v1/scores/top?track_id=track-42&limit=5")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_leaderboard_limit_max_100(client):
    response = client.get("/api/v1/scores/top?track_id=t&limit=200")
    assert response.status_code == 422


def test_my_scores_empty(client):
    response = client.get("/api/v1/scores/me?user_id=nobody")
    assert response.status_code == 200
    assert response.json() == []


def test_my_scores_returns_only_own(client):
    _submit(client, user_id="alice", track_id="t1", points=100)
    _submit(client, user_id="alice", track_id="t2", points=200)
    _submit(client, user_id="bob",   track_id="t1", points=999)

    response = client.get("/api/v1/scores/me?user_id=alice")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(s["user_id"] == "alice" for s in data)


def test_my_scores_ordered_by_date_desc(client):
    _submit(client, user_id="alice", points=100)
    _submit(client, user_id="alice", points=500)

    response = client.get("/api/v1/scores/me?user_id=alice")
    data = response.json()
    assert data[0]["points"] == 500
