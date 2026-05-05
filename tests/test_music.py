"""Tests CRUD pour /music."""

import io
from unittest.mock import patch, MagicMock

MUSIC_PAYLOAD = {"title": "Test Song", "artist": "Test Artist", "bpm": 128.0, "duration": 180.0, "file_path": "music_files/test.mp3"}


def test_list_music_empty(client):
    response = client.get("/api/v1/music")
    assert response.status_code == 200
    assert response.json() == []


def test_create_music(auth_client):
    response = auth_client.post("/api/v1/music", json=MUSIC_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Song"
    assert data["artist"] == "Test Artist"
    assert data["bpm"] == 128.0


def test_create_music_duplicate_returns_400(auth_client):
    auth_client.post("/api/v1/music", json=MUSIC_PAYLOAD)
    response = auth_client.post("/api/v1/music", json=MUSIC_PAYLOAD)
    assert response.status_code == 400


def test_list_music_after_create(auth_client):
    auth_client.post("/api/v1/music", json=MUSIC_PAYLOAD)
    response = auth_client.get("/api/v1/music")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_music_by_title(auth_client):
    auth_client.post("/api/v1/music", json=MUSIC_PAYLOAD)
    response = auth_client.get("/api/v1/music/Test Song")
    assert response.status_code == 200
    assert response.json()["title"] == "Test Song"


def test_get_music_not_found(client):
    response = client.get("/api/v1/music/nonexistent")
    assert response.status_code == 404


def test_update_music(auth_client):
    auth_client.post("/api/v1/music", json=MUSIC_PAYLOAD)
    response = auth_client.put("/api/v1/music/Test Song", json={"bpm": 140.0, "artist": "New Artist"})
    assert response.status_code == 200
    data = response.json()
    assert data["bpm"] == 140.0
    assert data["artist"] == "New Artist"


def test_update_music_not_found(auth_client):
    response = auth_client.put("/api/v1/music/nonexistent", json={"bpm": 140.0})
    assert response.status_code == 404


def test_delete_music(auth_client):
    auth_client.post("/api/v1/music", json=MUSIC_PAYLOAD)
    response = auth_client.delete("/api/v1/music/Test Song")
    assert response.status_code == 200
    assert auth_client.get("/api/v1/music/Test Song").status_code == 404


def test_delete_music_not_found(auth_client):
    response = auth_client.delete("/api/v1/music/nonexistent")
    assert response.status_code == 404


def test_upload_file(auth_client, mock_storage):
    file_content = b"ID3" + b"\x00" * 100  # faux header MP3
    response = auth_client.post(
        "/api/v1/music/upload/My Track",
        files={"file": ("my_track.mp3", io.BytesIO(file_content), "audio/mpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "uploaded"
    assert "music_files/My_Track" in data["file_path"]
    mock_storage.upload_file.assert_called_once()


def test_write_requires_auth(client):
    response = client.post("/api/v1/music", json=MUSIC_PAYLOAD)
    assert response.status_code == 403
