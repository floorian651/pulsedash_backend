"""Tests CRUD pour /music."""

import io
from unittest.mock import MagicMock, patch

from fastapi.responses import Response

from src.api.db.repositories import music_repo

MUSIC_FORM = {"title": "Test Song", "artist": "Test Artist", "bpm": 128.0, "duration": 180.0}


def test_list_music_empty(client):
    assert client.get("/api/v1/music").status_code == 200
    assert client.get("/api/v1/music").json() == []


def test_create_music(auth_client):
    r = auth_client.post("/api/v1/music", data=MUSIC_FORM)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Test Song"
    assert data["artist"] == "Test Artist"
    assert data["bpm"] == 128.0
    assert data["file_path"] is None


def test_create_music_with_file(auth_client, mock_storage):
    file_content = b"ID3" + b"\x00" * 100
    r = auth_client.post(
        "/api/v1/music",
        data=MUSIC_FORM,
        files={"file": ("my_track.mp3", io.BytesIO(file_content), "audio/mpeg")},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Test Song"
    assert "music_files/Test_Song" in data["file_path"]
    mock_storage.upload_file.assert_called_once()


def test_create_music_duplicate_returns_400(auth_client):
    auth_client.post("/api/v1/music", data=MUSIC_FORM)
    assert auth_client.post("/api/v1/music", data=MUSIC_FORM).status_code == 400


def test_create_music_unsupported_format(auth_client):
    file_content = b"fake"
    r = auth_client.post(
        "/api/v1/music",
        data=MUSIC_FORM,
        files={"file": ("track.exe", io.BytesIO(file_content), "application/octet-stream")},
    )
    assert r.status_code == 415


def test_list_music_after_create(auth_client):
    auth_client.post("/api/v1/music", data=MUSIC_FORM)
    r = auth_client.get("/api/v1/music")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_music_by_title(auth_client):
    auth_client.post("/api/v1/music", data=MUSIC_FORM)
    r = auth_client.get("/api/v1/music/Test Song")
    assert r.status_code == 200
    assert r.json()["title"] == "Test Song"


def test_get_music_not_found(client):
    assert client.get("/api/v1/music/nonexistent").status_code == 404


def test_download_music_returns_file_response(client, db):
    music_repo.create_music(
        db,
        title="Test Song",
        artist="Test Artist",
        bpm=128.0,
        duration=180.0,
        file_path="music_files/Test_Song/my_track.mp3",
    )

    with patch("src.api.routers.music.StorageService") as MockStorage:
        instance = MagicMock()
        instance.get_download_response.return_value = Response(
            content=b"audio-bytes",
            media_type="audio/mpeg",
            headers={"Content-Disposition": 'attachment; filename="my_track.mp3"'},
        )
        MockStorage.return_value = instance

        response = client.get("/api/v1/music/Test Song/download")

    assert response.status_code == 200
    assert response.content == b"audio-bytes"
    assert response.headers["content-disposition"] == 'attachment; filename="my_track.mp3"'
    instance.get_download_response.assert_called_once_with("music_files/Test_Song/my_track.mp3")


def test_download_level_returns_file_response(client, db):
    music = music_repo.create_music(
        db,
        title="Test Song",
        artist="Test Artist",
        bpm=128.0,
        duration=180.0,
        file_path="music_files/Test_Song/my_track.mp3",
    )
    music.level_path = "levels/Test_Song/level.mp3"
    db.commit()
    db.refresh(music)

    with patch("src.api.routers.music.StorageService") as MockStorage:
        instance = MagicMock()
        instance.get_download_response.return_value = Response(
            content=b"level-bytes",
            media_type="audio/mpeg",
            headers={"Content-Disposition": 'attachment; filename="level.mp3"'},
        )
        MockStorage.return_value = instance

        response = client.get("/api/v1/music/Test Song/level")

    assert response.status_code == 200
    assert response.content == b"level-bytes"
    assert response.headers["content-disposition"] == 'attachment; filename="level.mp3"'
    instance.get_download_response.assert_called_once_with("levels/Test_Song/level.mp3")


def test_update_music(auth_client):
    auth_client.post("/api/v1/music", data=MUSIC_FORM)
    r = auth_client.put("/api/v1/music/Test Song", json={"bpm": 140.0, "artist": "New Artist"})
    assert r.status_code == 200
    data = r.json()
    assert data["bpm"] == 140.0
    assert data["artist"] == "New Artist"


def test_update_music_not_found(auth_client):
    assert auth_client.put("/api/v1/music/nonexistent", json={"bpm": 140.0}).status_code == 404


def test_delete_music(auth_client):
    auth_client.post("/api/v1/music", data=MUSIC_FORM)
    assert auth_client.delete("/api/v1/music/Test Song").status_code == 200
    assert auth_client.get("/api/v1/music/Test Song").status_code == 404


def test_delete_music_not_found(auth_client):
    assert auth_client.delete("/api/v1/music/nonexistent").status_code == 404


def test_write_requires_auth(client):
    assert client.post("/api/v1/music", data=MUSIC_FORM).status_code == 403
