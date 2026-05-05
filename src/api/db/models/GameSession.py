import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from .base import Base


class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    music_title = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="active")  # active | completed | abandoned
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime(timezone=True), nullable=True)
    final_score = Column(Integer, nullable=True)
    accuracy = Column(Float, nullable=True)

    def __repr__(self):
        return f"<GameSession(id={self.id}, user={self.user_id}, status={self.status})>"
