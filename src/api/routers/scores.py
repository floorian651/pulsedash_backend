from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.db.session import get_session
from src.api.db.repositories import score_repo
from src.api.schemas.score import LeaderboardEntry, ScoreResponse, ScoreSubmit

# TODO: importer get_current_user depuis src.api.dependencies quand l'auth sera mergée
# from src.api.dependencies import get_current_user

router = APIRouter(prefix="/scores", tags=["scores"])


@router.post("", response_model=ScoreResponse, status_code=201)
async def submit_score(body: ScoreSubmit, db: Session = Depends(get_session)):
    """
    Soumet un score après une partie.
    TODO: remplacer body.user_id par current_user.id via Depends(get_current_user).
    """
    score = score_repo.create_score(
        db,
        user_id=body.user_id,
        track_id=body.track_id,
        points=body.points,
        accuracy=body.accuracy,
    )
    return score


@router.get("/top", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    track_id: str = Query(..., description="ID de la track"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """Retourne le classement des meilleurs scores pour une track."""
    scores = score_repo.get_top_scores(db, track_id=track_id, limit=limit)
    return [
        LeaderboardEntry(
            rank=i + 1,
            user_id=s.user_id,
            points=s.points,
            accuracy=s.accuracy,
        )
        for i, s in enumerate(scores)
    ]


@router.get("/me", response_model=list[ScoreResponse])
async def get_my_scores(
    user_id: str = Query(..., description="TODO: sera remplacé par le token JWT"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_session),
):
    """
    Retourne l'historique des scores d'un joueur.
    TODO: remplacer user_id query param par Depends(get_current_user).
    """
    return score_repo.get_scores_by_user(db, user_id=user_id, limit=limit)
