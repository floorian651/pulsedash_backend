"""Tests pour /scores."""


def _submit(auth_client, track_id="track-42", points=1000, accuracy=0.95):
    return auth_client.post("/api/v1/scores", json={
        "track_id": track_id,
        "points": points,
        "accuracy": accuracy,
    })


def test_submit_score(auth_client):
    response = _submit(auth_client)
    assert response.status_code == 201
    data = response.json()
    assert data["points"] == 1000
    assert data["track_id"] == "track-42"
    assert "user_id" in data
    assert "id" in data


def test_submit_score_missing_fields_returns_422(auth_client):
    response = auth_client.post("/api/v1/scores", json={"points": 500})
    assert response.status_code == 422


def test_submit_score_negative_points_returns_422(auth_client):
    response = auth_client.post("/api/v1/scores", json={"track_id": "t1", "points": -10})
    assert response.status_code == 422


def test_submit_score_accuracy_out_of_range_returns_422(auth_client):
    response = auth_client.post("/api/v1/scores", json={"track_id": "t1", "points": 100, "accuracy": 1.5})
    assert response.status_code == 422


def test_submit_requires_auth(client):
    response = client.post("/api/v1/scores", json={"track_id": "t1", "points": 100})
    assert response.status_code == 403


def test_leaderboard_empty(client):
    response = client.get("/api/v1/scores/top?track_id=unknown-track")
    assert response.status_code == 200
    assert response.json() == []


def test_leaderboard_ordered_by_points(auth_client):
    _submit(auth_client, points=500)
    _submit(auth_client, points=9000)
    _submit(auth_client, points=3000)

    response = auth_client.get("/api/v1/scores/top?track_id=track-42")
    assert response.status_code == 200
    entries = response.json()
    assert entries[0]["points"] == 9000
    assert entries[0]["rank"] == 1
    assert entries[1]["points"] == 3000
    assert entries[2]["points"] == 500


def test_leaderboard_limit(auth_client):
    for i in range(15):
        _submit(auth_client, points=i * 100)

    response = auth_client.get("/api/v1/scores/top?track_id=track-42&limit=5")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_leaderboard_limit_max_100(client):
    response = client.get("/api/v1/scores/top?track_id=t&limit=200")
    assert response.status_code == 422


def test_my_scores_empty(auth_client):
    response = auth_client.get("/api/v1/scores/me")
    assert response.status_code == 200
    assert response.json() == []


def test_my_scores_returns_own(auth_client):
    _submit(auth_client, track_id="t1", points=100)
    _submit(auth_client, track_id="t2", points=200)

    response = auth_client.get("/api/v1/scores/me")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_my_scores_ordered_by_date_desc(auth_client):
    _submit(auth_client, points=100)
    _submit(auth_client, points=500)

    response = auth_client.get("/api/v1/scores/me")
    data = response.json()
    assert data[0]["points"] == 500


def test_my_scores_requires_auth(client):
    response = client.get("/api/v1/scores/me")
    assert response.status_code == 403
