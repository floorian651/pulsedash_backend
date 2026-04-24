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

os.environ["DEBUG"] = "false"  # forcer False même si le .env dit true
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

# Patcher DB et MinIO pendant le chargement de main.py (qui appelle create_app())
_p_engine = patch("src.api.db.session.init_engine")
_p_minio = patch("src.api.services.storage.ensure_buckets_exist")
_p_engine.start()
_p_minio.start()

from src.api.main import app  # déclenche app = create_app() avec les patches actifs

_p_engine.stop()
_p_minio.stop()

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importer tous les modèles pour qu'ils s'enregistrent dans Base.metadata
from src.api.db.models import Base, Job, Music, Playlist, Track, User
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


@pytest.fixture
def client(db):
    """Client HTTP qui utilise la DB de test à la place de PostgreSQL."""
    def _override():
        yield db

    app.dependency_overrides[get_session] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_raise(db):
    """Client qui retourne les réponses 5xx au lieu de lever l'exception.
    Nécessaire pour tester le handler d'erreur global."""
    def _override():
        yield db

    app.dependency_overrides[get_session] = _override
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


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
