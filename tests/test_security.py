"""Tests de sécurité : path traversal et sanitisation des entrées."""

import io
from unittest.mock import patch, MagicMock

from src.api.routers.music import _sanitize_path_component
import pytest


# ---------------------------------------------------------------------------
# Unit tests : _sanitize_path_component
# ---------------------------------------------------------------------------

def test_sanitize_normal_name():
    assert _sanitize_path_component("my_song.mp3") == "my_song.mp3"


def test_sanitize_removes_path_separators():
    result = _sanitize_path_component("../../etc/passwd")
    assert ".." not in result
    assert "/" not in result


def test_sanitize_replaces_special_chars():
    result = _sanitize_path_component("song <evil>; rm -rf |pipe.mp3")
    for char in "<>; |":
        assert char not in result


def test_sanitize_strips_leading_dots():
    result = _sanitize_path_component("...hidden")
    assert not result.startswith(".")


def test_sanitize_enforces_max_length():
    result = _sanitize_path_component("a" * 300 + ".mp3")
    assert len(result) <= 128


def test_sanitize_empty_after_strip_raises():
    with pytest.raises(ValueError):
        _sanitize_path_component("...")


def test_sanitize_null_bytes():
    result = _sanitize_path_component("file\x00name.mp3")
    assert "\x00" not in result


# ---------------------------------------------------------------------------
# Integration tests : upload endpoint
# ---------------------------------------------------------------------------

def _upload(client, title: str, filename: str):
    with patch("src.api.routers.music.StorageService") as MockStorage:
        instance = MagicMock()
        instance.get_download_url.return_value = "http://minio/test"
        MockStorage.return_value = instance
        response = client.post(
            f"/api/v1/music/upload/{title}",
            files={"file": (filename, io.BytesIO(b"fake"), "audio/mpeg")},
        )
        upload_call = instance.upload_file.call_args
    return response, upload_call


def test_upload_path_traversal_in_filename(auth_client):
    """Un filename comme ../../evil.sh ne doit pas sortir de music_files/."""
    response, call = _upload(auth_client, "legit_title", "../../../evil.sh")
    assert response.status_code == 200
    object_name = call[0][0]
    assert ".." not in object_name
    assert object_name.startswith("music_files/")


def test_upload_special_chars_in_title(auth_client):
    """Un title avec des caractères spéciaux est sanitisé dans le chemin MinIO."""
    response, call = _upload(auth_client, "song|rm -rf", "song.mp3")
    assert response.status_code == 200
    object_name = call[0][0]
    assert "|" not in object_name
    assert "rm" not in object_name or "_rm" in object_name


def test_upload_null_byte_in_filename(auth_client):
    """Un null byte dans le nom de fichier ne doit pas atteindre MinIO."""
    response, call = _upload(auth_client, "normal_title", "file\x00.mp3")
    assert response.status_code == 200
    object_name = call[0][0]
    assert "\x00" not in object_name


# ---------------------------------------------------------------------------
# Validation upload : content-type et taille
# ---------------------------------------------------------------------------

def _upload_with_type(client, content_type: str, content: bytes = b"fake audio"):
    with patch("src.api.routers.music.StorageService"):
        return client.post(
            "/api/v1/music/upload/test_title",
            files={"file": ("track.mp3", io.BytesIO(content), content_type)},
        )


def test_upload_valid_content_types(auth_client):
    for ct in ["audio/mpeg", "audio/wav", "audio/ogg", "audio/flac"]:
        with patch("src.api.routers.music.StorageService") as MockStorage:
            instance = MagicMock()
            instance.get_download_url.return_value = "http://minio/test"
            MockStorage.return_value = instance
            response = auth_client.post(
                "/api/v1/music/upload/test_title",
                files={"file": ("track.mp3", io.BytesIO(b"fake"), ct)},
            )
        assert response.status_code == 200, f"Attendu 200 pour {ct}, reçu {response.status_code}"


def test_upload_invalid_content_type_returns_415(auth_client):
    response = _upload_with_type(auth_client, "application/pdf")
    assert response.status_code == 415


def test_upload_executable_content_type_returns_415(auth_client):
    response = _upload_with_type(auth_client, "application/octet-stream")
    assert response.status_code == 415


def test_upload_file_too_large_returns_413(auth_client):
    from src.api.routers.music import MAX_UPLOAD_SIZE
    oversized = b"x" * (MAX_UPLOAD_SIZE + 1)
    with patch("src.api.routers.music.StorageService"):
        response = auth_client.post(
            "/api/v1/music/upload/test_title",
            files={"file": ("big.mp3", io.BytesIO(oversized), "audio/mpeg")},
        )
    assert response.status_code == 413


def test_upload_at_size_limit_is_accepted(auth_client):
    from src.api.routers.music import MAX_UPLOAD_SIZE
    exact_size = b"x" * MAX_UPLOAD_SIZE
    with patch("src.api.routers.music.StorageService") as MockStorage:
        instance = MagicMock()
        instance.get_download_url.return_value = "http://minio/test"
        MockStorage.return_value = instance
        response = auth_client.post(
            "/api/v1/music/upload/test_title",
            files={"file": ("exact.mp3", io.BytesIO(exact_size), "audio/mpeg")},
        )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def test_rate_limit_generate(auth_client, mock_celery):
    """Au-delà de 10 requêtes/min depuis la même IP, l'API doit retourner 429."""
    responses = [
        auth_client.post("/api/v1/generate", json={"track_id": str(i)})
        for i in range(12)
    ]
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes, "Le rate limiting devrait retourner 429 après 10 requêtes"
    assert responses[0].status_code == 202, "La première requête doit passer"
