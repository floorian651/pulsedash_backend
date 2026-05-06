from pydantic import BaseModel
from typing import Optional


class MusicUpdate(BaseModel):
    artist: Optional[str] = None
    bpm: Optional[float] = None
    duration: Optional[float] = None


class MusicResponse(BaseModel):
    title: str
    artist: Optional[str]
    bpm: Optional[float]
    duration: Optional[float]
    bucket_name: str
    file_path: Optional[str]

    class Config:
        from_attributes = True
