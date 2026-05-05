"""Tests pour GET /jamendo/search."""

from unittest.mock import patch

FAKE_RESULTS = [
    {"id": "114069", "name": "Darude Sandstorm", "artist_name": "Darude",
     "duration": 224, "image": "http://img/cover.jpg", "audio": "http://cdn/track.mp3"},
    {"id": "222222", "name": "Darude Rush", "artist_name": "Darude",
     "duration": 180, "image": None, "audio": "http://cdn/track2.mp3"},
]


def _mock_search(results=None):
    return patch(
        "src.api.routers.jamendo.search_tracks",
        return_value=results if results is not None else FAKE_RESULTS,
    )


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
    assert "id" in track
    assert "name" in track
    assert "artist_name" in track
    assert "duration" in track
    assert "image" in track
    assert "audio" in track


def test_search_nullable_image(client):
    with _mock_search():
        r = client.get("/api/v1/jamendo/search?q=darude")
    assert r.json()[1]["image"] is None
