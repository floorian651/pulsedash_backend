from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from .base import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    track_id = Column(String, nullable=False, index=True)
    points = Column(Integer, nullable=False)
    accuracy = Column(Float, nullable=True)   # % de notes touchées
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Score(user={self.user_id}, track={self.track_id}, points={self.points})>"
