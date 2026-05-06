from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.db.session import get_session
from src.api.db.repositories import score_repo
from src.api.schemas.score import GlobalLeaderboardEntry, LeaderboardEntry, ScoreResponse
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("/top", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    music_title: str = Query(..., description="Titre de la musique"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    rows = score_repo.get_top_scores(db, music_title=music_title, limit=limit)
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
