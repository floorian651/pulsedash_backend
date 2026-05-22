from pydantic import BaseModel, computed_field
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
    level_path: Optional[str] = None

    @computed_field
    @property
    def has_level(self) -> bool:
        return self.level_path is not None

    class Config:
        from_attributes = True
