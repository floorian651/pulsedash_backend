from fastapi import APIRouter, HTTPException, Query, Request

from src.api.core.limiter import limiter
from src.api.schemas.jamendo import JamendoTrack
from src.api.services.jamendo import search_tracks

router = APIRouter(prefix="/jamendo", tags=["jamendo"])


@router.get("/search", response_model=list[JamendoTrack])
@limiter.limit("30/minute")
async def search_jamendo(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100, description="Titre à rechercher"),
    limit: int = Query(10, ge=1, le=50),
):
    try:
        return search_tracks(q, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Jamendo unavailable: {exc}")
