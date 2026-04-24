from pydantic import BaseModel
from typing import Optional


class GenerateRequest(BaseModel):
    track_id: str


class GenerateAccepted(BaseModel):
    job_id: str
    state: str


class GenerateResponse(BaseModel):
    job_id: str
    state: str
    progress: int = 0
    level: Optional[dict] = None
    error: Optional[str] = None
