from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.db.session import get_session
from src.api.db.models.GameSession import GameSession
from src.api.db.repositories import user_repo
from src.api.schemas.profile import ProfileResponse, ProfileStats
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


def _build_profile(db: Session, user_id: str) -> ProfileResponse:
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sessions = db.query(GameSession).filter(GameSession.user_id == user_id).all()

    total_games = len(sessions)
    completed = [s for s in sessions if s.status == "completed"]
    completed_games = len(completed)

    scores = [s.final_score for s in completed if s.final_score is not None]
    total_points = sum(scores)
    best_score = max(scores) if scores else None

    accuracies = [s.accuracy for s in completed if s.accuracy is not None]
    average_accuracy = sum(accuracies) / len(accuracies) if accuracies else None

    return ProfileResponse(
        user_id=user_id,
        username=user.username,
        member_since=user.created_at,
        stats=ProfileStats(
            total_games=total_games,
            completed_games=completed_games,
            total_points=total_points,
            best_score=best_score,
            average_accuracy=round(average_accuracy, 4) if average_accuracy is not None else None,
        ),
    )


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return _build_profile(db, str(current_user.id))


@router.get("/{user_id}", response_model=ProfileResponse)
async def get_user_profile(
    user_id: str,
    db: Session = Depends(get_session),
):
    return _build_profile(db, user_id)
