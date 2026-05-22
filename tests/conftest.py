"""
Fixtures partagées par tous les tests.

Ordre critique des opérations au chargement du module :
  1. Définir les variables d'environnement (avant que pydantic-settings les lise)
  2. Vider le cache lru_cache de get_settings()
  3. Patcher init_engine + ensure_buckets_exist AVANT d'importer main.py
     (car app = create_app() s'exécute au niveau module dans main.py)
  4. Créer l'engine SQLite in-memory et les tables
"""

import os

os.environ.setdefault("POSTGRES_HOST", "testhost")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("JAMENDO_CLIENT_ID", "test_client_id")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_tests_only")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from unittest.mock import MagicMock, patch

# Vider le cache avant tout import de l'app pour que les env vars ci-dessus soient lues
from src.api.core.config import get_settings
get_settings.cache_clear()

# Patcher DB, MinIO et Redis blacklist pendant le chargement de main.py
_p_engine = patch("src.api.db.session.init_engine")
_p_minio = patch("src.api.services.storage.ensure_buckets_exist")
_p_blacklist_check = patch("src.api.services.token_blacklist.is_blacklisted", return_value=False)
_p_blacklist_add = patch("src.api.services.token_blacklist.blacklist_jti")
_p_engine.start()
_p_minio.start()
_p_blacklist_check.start()
_p_blacklist_add.start()

from src.api.main import app  # déclenche app = create_app() avec les patches actifs

_p_engine.stop()
_p_minio.stop()
_p_blacklist_check.stop()
_p_blacklist_add.stop()

# Réactiver les patches pour toute la durée des tests
patch("src.api.services.token_blacklist.is_blacklisted", return_value=False).start()
patch("src.api.services.token_blacklist.blacklist_jti").start()

import itertools

import pytest
from fastapi.testclient import TestClient
from src.api.core.limiter import key_func as limiter_key_func
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importer tous les modèles pour qu'ils s'enregistrent dans Base.metadata
from src.api.db.models import Base, GameSession, Job, Music, Playlist, Track, User
from src.api.db.session import get_session

# StaticPool : toutes les connexions partagent la même DB in-memory.
# Sans ça, create_all() crée les tables sur une connexion et la session
# en ouvre une autre qui repart de zéro.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_engine)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@pytest.fixture
def db():
    """Session DB isolée par test : rollback + truncate à la fin."""
    session = _SessionLocal()
    yield session
    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


_test_counter = itertools.count()


@pytest.fixture
def client(db):
    """Client HTTP qui utilise la DB de test à la place de PostgreSQL."""
    def _override():
        yield db

    # IP unique par test pour ne pas déclencher le rate limiter entre tests
    test_ip = f"test-{next(_test_counter)}"
    limiter_key_func._override = lambda req: test_ip

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    limiter_key_func._override = None


@pytest.fixture
def mock_storage():
    """Remplace StorageService pour ne pas appeler MinIO."""
    with patch("src.api.routers.music.StorageService") as MockStorage:
        instance = MagicMock()
        instance.upload_file.return_value = "test/path.mp3"
        instance.get_download_url.return_value = "http://minio/test/file.mp3"
        MockStorage.return_value = instance
        yield instance


@pytest.fixture
def mock_celery():
    """Remplace le .delay() de la tâche Celery pour ne pas appeler Redis."""
    with patch("src.api.routers.generate.generate_level_task") as mock_task:
        mock_task.delay.return_value = MagicMock(id="fake-celery-id")
        yield mock_task


@pytest.fixture
def auth_client(client):
    """Client HTTP avec un token JWT valide pré-injecté dans les headers."""
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def admin_client(client, db):
    """Client HTTP avec un token JWT d'un utilisateur admin."""
    from src.api.db.models import User
    from src.api.services.auth import hash_password as _hash

    user = User(email="admin@example.com", password=_hash("adminpassword123"), is_admin=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    from src.api.services.auth import create_access_token
    token = create_access_token(str(user.id))
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client
