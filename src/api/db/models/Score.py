from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String

from .base import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=True, unique=True, index=True)
    music_title = Column(String, nullable=False, index=True)
    points = Column(Integer, nullable=False)
    accuracy = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Score(user={self.user_id}, music={self.music_title}, points={self.points})>"
