# Ce fichier :

#     crée l’engine SQLAlchemy (connexion à Postgres)

#     configure la session

#     expose une dépendance FastAPI get_session() pour injecter la DB dans les endpoints

# C’est le point d’entrée pour accéder à la base.

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

engine = None
SessionLocal = None


def init_engine(database_url: str):
    global engine, SessionLocal
    engine = create_engine(database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    global engine, SessionLocal
    
    if SessionLocal is None:
        from src.api.core.config import get_settings
        init_engine(get_settings().DATABASE_URL)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
