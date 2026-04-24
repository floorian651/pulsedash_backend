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


def test_upload_path_traversal_in_filename(client):
    """Un filename comme ../../evil.sh ne doit pas sortir de music_files/."""
    response, call = _upload(client, "legit_title", "../../../evil.sh")
    assert response.status_code == 200
    object_name = call[0][0]
    assert ".." not in object_name
    assert object_name.startswith("music_files/")


def test_upload_special_chars_in_title(client):
    """Un title avec des caractères spéciaux est sanitisé dans le chemin MinIO."""
    response, call = _upload(client, "song|rm -rf", "song.mp3")
    assert response.status_code == 200
    object_name = call[0][0]
    assert "|" not in object_name
    assert "rm" not in object_name or "_rm" in object_name


def test_upload_null_byte_in_filename(client):
    """Un null byte dans le nom de fichier ne doit pas atteindre MinIO."""
    response, call = _upload(client, "normal_title", "file\x00.mp3")
    assert response.status_code == 200
    object_name = call[0][0]
    assert "\x00" not in object_name
