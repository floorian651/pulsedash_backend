from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScoreResponse(BaseModel):
    id: int
    user_id: str
    session_id: Optional[str]
    music_title: str
    points: int
    accuracy: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: Optional[str]
    points: int
    accuracy: Optional[float]


class GlobalLeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: Optional[str]
    total_points: int
    games_played: int
