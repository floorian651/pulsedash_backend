"""Tests pour le handler d'erreur global."""

from unittest.mock import patch
import pytest


def test_unhandled_exception_returns_500_without_details(client_no_raise):
    """En prod (DEBUG=False), une erreur interne ne doit pas exposer de détails."""
    with patch("src.api.routers.music.music_repo.get_all_music", side_effect=RuntimeError("secret db error")):
        response = client_no_raise.get("/api/v1/music")

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "Internal server error"
    assert "secret db error" not in str(body)
    assert "Traceback" not in str(body)


def test_http_exception_still_passes_through(client):
    """Les HTTPException intentionnelles (404, 400…) ne doivent pas être masquées."""
    response = client.get("/api/v1/music/nonexistent-title")
    assert response.status_code == 404
    assert "detail" in response.json()
