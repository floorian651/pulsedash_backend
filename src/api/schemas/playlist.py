from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TrackInPlaylist(BaseModel):
    id: int
    music_title: str
    position: Optional[int]

    class Config:
        from_attributes = True


class PlaylistCreate(BaseModel):
    name: str
    description: Optional[str] = None


class PlaylistUpdate(BaseModel):
    description: Optional[str] = None


class PlaylistResponse(BaseModel):
    name: str
    description: Optional[str]
    created_at: datetime
    tracks: List[TrackInPlaylist] = []

    class Config:
        from_attributes = True
