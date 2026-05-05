from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProfileStats(BaseModel):
    total_games: int
    completed_games: int
    total_points: int
    best_score: Optional[int]
    average_accuracy: Optional[float]


class ProfileResponse(BaseModel):
    user_id: str
    username: Optional[str]
    member_since: datetime
    stats: ProfileStats
