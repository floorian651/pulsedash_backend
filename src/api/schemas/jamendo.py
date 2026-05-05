from typing import Optional
from pydantic import BaseModel


class JamendoTrack(BaseModel):
    id: str
    name: str
    artist_name: str
    duration: int
    image: Optional[str]
    audio: Optional[str]
