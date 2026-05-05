from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.db.models.Score import Score
from src.api.db.models.User import User


def create_score(
    db: Session,
    user_id: str,
    music_title: str,
    points: int,
    session_id: str | None = None,
    accuracy: float | None = None,
) -> Score:
    score = Score(
        user_id=user_id,
        session_id=session_id,
        music_title=music_title,
        points=points,
        accuracy=accuracy,
    )
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


def get_top_scores(db: Session, music_title: str, limit: int = 10) -> list:
    return (
        db.query(Score, User.username)
        .outerjoin(User, Score.user_id == User.id)
        .filter(Score.music_title == music_title)
        .order_by(Score.points.desc())
        .limit(limit)
        .all()
    )


def get_global_top(db: Session, limit: int = 100) -> list:
    return (
        db.query(
            Score.user_id,
            User.username,
            func.sum(Score.points).label("total_points"),
            func.count(Score.id).label("games_played"),
        )
        .outerjoin(User, Score.user_id == User.id)
        .group_by(Score.user_id, User.username)
        .order_by(func.sum(Score.points).desc())
        .limit(limit)
        .all()
    )


def get_scores_by_user(db: Session, user_id: str, limit: int = 50) -> list[Score]:
    return (
        db.query(Score)
        .filter(Score.user_id == user_id)
        .order_by(Score.created_at.desc())
        .limit(limit)
        .all()
    )
