from pydantic import BaseModel


class GenerateRequest(BaseModel):
    music_title: str


class GenerateAccepted(BaseModel):
    job_id: str
    state: str
