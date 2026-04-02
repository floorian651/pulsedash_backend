from pydantic import BaseModel
from typing import Optional


class TrackCreate(BaseModel):
    playlist_name: str
    music_title: str
    position: Optional[int] = None


class TrackUpdate(BaseModel):
    position: Optional[int] = None


class TrackResponse(BaseModel):
    id: int
    playlist_name: str
    music_title: str
    position: Optional[int]

    class Config:
        from_attributes = True
