from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime

from .base import Base


class User(Base):
    __tablename__ = "users"  # Assure-toi que c'est bien "users" ici aussi

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow())