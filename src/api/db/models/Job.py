from sqlalchemy import Column, String, Integer, DateTime, Enum
from datetime import datetime, timezone
from enum import Enum as PyEnum

from .base import Base


class JobState(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    state = Column(Enum(JobState), default=JobState.PENDING)
    progress = Column(Integer, default=0)
    result_path = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Job(id={self.id}, state={self.state}, progress={self.progress})>"
