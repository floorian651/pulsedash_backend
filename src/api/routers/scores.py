from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.db.session import get_session
from src.api.db.repositories import score_repo
from src.api.schemas.score import GlobalLeaderboardEntry, LeaderboardEntry, ScoreResponse, ScoreSubmit
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/scores", tags=["scores"])


@router.post("", response_model=ScoreResponse, status_code=201)
async def submit_score(
    body: ScoreSubmit,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return score_repo.create_score(
        db,
        user_id=str(current_user.id),
        track_id=body.track_id,
        points=body.points,
        accuracy=body.accuracy,
    )


@router.get("/top", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    track_id: str = Query(..., description="ID de la track"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    rows = score_repo.get_top_scores(db, track_id=track_id, limit=limit)
    return [
        LeaderboardEntry(rank=i + 1, user_id=s.user_id, username=username, points=s.points, accuracy=s.accuracy)
        for i, (s, username) in enumerate(rows)
    ]


@router.get("/global", response_model=list[GlobalLeaderboardEntry])
async def get_global_leaderboard(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_session),
):
    rows = score_repo.get_global_top(db, limit=limit)
    return [
        GlobalLeaderboardEntry(
            rank=i + 1,
            user_id=row.user_id,
            username=row.username,
            total_points=row.total_points,
            games_played=row.games_played,
        )
        for i, row in enumerate(rows)
    ]


@router.get("/me", response_model=list[ScoreResponse])
async def get_my_scores(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return score_repo.get_scores_by_user(db, user_id=str(current_user.id), limit=limit)
