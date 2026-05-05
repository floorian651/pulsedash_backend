"""Tests pour les endpoints d'authentification JWT."""

import pytest


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

def test_register_returns_201_and_token(client):
    r = client.post("/api/v1/auth/register", json={"email": "user@test.com", "password": "secret123"})
    assert r.status_code == 201
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_register_with_username(client):
    r = client.post("/api/v1/auth/register", json={"email": "user2@test.com", "password": "password123", "username": "player1"})
    assert r.status_code == 201


def test_register_duplicate_email_returns_409(client):
    payload = {"email": "dup@test.com", "password": "password123"}
    client.post("/api/v1/auth/register", json=payload)
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


def test_register_short_password_returns_422(client):
    r = client.post("/api/v1/auth/register", json={"email": "short@test.com", "password": "abc"})
    assert r.status_code == 422


def test_register_invalid_email_returns_422(client):
    r = client.post("/api/v1/auth/register", json={"email": "not-an-email", "password": "pass"})
    assert r.status_code == 422


def test_register_missing_password_returns_422(client):
    r = client.post("/api/v1/auth/register", json={"email": "a@test.com"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

def test_login_returns_token(client):
    client.post("/api/v1/auth/register", json={"email": "login@test.com", "password": "mypassword"})
    r = client.post("/api/v1/auth/login", json={"email": "login@test.com", "password": "mypassword"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password_returns_401(client):
    client.post("/api/v1/auth/register", json={"email": "wrong@test.com", "password": "correctpass"})
    r = client.post("/api/v1/auth/login", json={"email": "wrong@test.com", "password": "incorrectpass"})
    assert r.status_code == 401


def test_login_unknown_email_returns_401(client):
    r = client.post("/api/v1/auth/login", json={"email": "ghost@test.com", "password": "password123"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

def test_me_returns_profile(auth_client):
    r = auth_client.get("/api/v1/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True
    assert "id" in data


def test_me_without_token_returns_403(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 403


def test_me_with_invalid_token_returns_401(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert r.status_code == 401


def test_register_then_login_tokens_are_different(client):
    """Deux connexions consécutives doivent donner des tokens différents (exp différente)."""
    import time
    client.post("/api/v1/auth/register", json={"email": "two@test.com", "password": "password123"})
    time.sleep(1)
    r1 = client.post("/api/v1/auth/login", json={"email": "two@test.com", "password": "password123"})
    time.sleep(1)
    r2 = client.post("/api/v1/auth/login", json={"email": "two@test.com", "password": "password123"})
    assert r1.json()["access_token"] != r2.json()["access_token"]


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

def test_refresh_returns_new_tokens(client):
    r = client.post("/api/v1/auth/register", json={"email": "refresh@test.com", "password": "password123"})
    refresh_token = r.json()["refresh_token"]
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 200
    data = r2.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_rotates_tokens(client):
    import time
    r = client.post("/api/v1/auth/register", json={"email": "rotate@test.com", "password": "password123"})
    old_refresh = r.json()["refresh_token"]
    time.sleep(1)
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r2.json()["refresh_token"] != old_refresh


def test_refresh_with_invalid_token_returns_401(client):
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})
    assert r.status_code == 401


def test_refresh_with_access_token_returns_401(client):
    r = client.post("/api/v1/auth/register", json={"email": "wrongtype@test.com", "password": "password123"})
    access_token = r.json()["access_token"]
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert r2.status_code == 401
