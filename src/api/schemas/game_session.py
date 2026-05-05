from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GameSessionStart(BaseModel):
    music_title: str


class GameSessionEnd(BaseModel):
    final_score: int = Field(..., ge=0)
    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    abandoned: bool = False


class GameSessionResponse(BaseModel):
    id: str
    user_id: str
    music_title: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    final_score: Optional[int]
    accuracy: Optional[float]

    class Config:
        from_attributes = True
