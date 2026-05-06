from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.db.session import get_session
from src.api.db.repositories import user_repo
from src.api.db.repositories.game_session_repo import get_profile_stats
from src.api.schemas.profile import ProfileResponse, ProfileStats
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/profile", tags=["profile"])


def _build_profile(db: Session, user_id: str) -> ProfileResponse:
    user = user_repo.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stats = get_profile_stats(db, user_id)
    avg = stats.average_accuracy

    return ProfileResponse(
        user_id=user_id,
        username=user.username,
        member_since=user.created_at,
        stats=ProfileStats(
            total_games=stats.total_games,
            completed_games=stats.completed_games,
            total_points=stats.total_points,
            best_score=stats.best_score,
            average_accuracy=round(avg, 4) if avg is not None else None,
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
