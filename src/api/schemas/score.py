from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ScoreSubmit(BaseModel):
    track_id: str
    points: int = Field(..., ge=0)
    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)


class ScoreResponse(BaseModel):
    id: int
    user_id: str
    track_id: str
    points: int
    accuracy: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    points: int
    accuracy: Optional[float]
