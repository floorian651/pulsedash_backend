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


# ── Leaderboard username ───────────────────────────────────────────────────────

def test_leaderboard_entry_has_username_field(auth_client):
    _submit(auth_client, points=1000)
    response = auth_client.get("/api/v1/scores/top?track_id=track-42")
    assert response.status_code == 200
    entry = response.json()[0]
    assert "username" in entry


def test_leaderboard_entry_username_is_none_without_username(auth_client):
    # auth_client registers without username
    _submit(auth_client, points=500)
    response = auth_client.get("/api/v1/scores/top?track_id=track-42")
    entry = response.json()[0]
    assert entry["username"] is None


def test_leaderboard_entry_username_populated(client):
    client.post("/api/v1/auth/register",
                json={"email": "pro@example.com", "password": "pass1234",
                      "username": "ProGamer"})
    r = client.post("/api/v1/auth/login",
                    json={"email": "pro@example.com", "password": "pass1234"})
    client.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    client.post("/api/v1/scores", json={"track_id": "t1", "points": 9999})

    response = client.get("/api/v1/scores/top?track_id=t1")
    assert response.json()[0]["username"] == "ProGamer"


# ── Global leaderboard ────────────────────────────────────────────────────────

def test_global_leaderboard_empty(client):
    response = client.get("/api/v1/scores/global")
    assert response.status_code == 200
    assert response.json() == []


def test_global_leaderboard_aggregates_points(auth_client):
    _submit(auth_client, track_id="t1", points=1000)
    _submit(auth_client, track_id="t2", points=2000)
    _submit(auth_client, track_id="t3", points=500)

    response = auth_client.get("/api/v1/scores/global")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["total_points"] == 3500
    assert data[0]["games_played"] == 3
    assert data[0]["rank"] == 1


def test_global_leaderboard_ordered_by_total_points(client):
    # user A — 5000 pts total
    r_a = client.post("/api/v1/auth/register",
                      json={"email": "a@ex.com", "password": "pass1234"})
    client.headers.update({"Authorization": f"Bearer {r_a.json()['access_token']}"})
    client.post("/api/v1/scores", json={"track_id": "t1", "points": 3000})
    client.post("/api/v1/scores", json={"track_id": "t2", "points": 2000})

    # user B — 1000 pts total
    r_b = client.post("/api/v1/auth/register",
                      json={"email": "b@ex.com", "password": "pass1234"})
    client.headers.update({"Authorization": f"Bearer {r_b.json()['access_token']}"})
    client.post("/api/v1/scores", json={"track_id": "t1", "points": 1000})

    response = client.get("/api/v1/scores/global")
    data = response.json()
    assert data[0]["total_points"] == 5000
    assert data[0]["rank"] == 1
    assert data[1]["total_points"] == 1000
    assert data[1]["rank"] == 2


def test_global_leaderboard_limit(auth_client):
    for i in range(5):
        _submit(auth_client, track_id=f"t{i}", points=(i + 1) * 100)

    response = auth_client.get("/api/v1/scores/global?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 1  # only 1 user regardless of limit


def test_global_leaderboard_has_username_field(auth_client):
    _submit(auth_client, points=100)
    response = auth_client.get("/api/v1/scores/global")
    assert "username" in response.json()[0]
