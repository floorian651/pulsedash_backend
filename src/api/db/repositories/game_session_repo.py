from datetime import datetime, timezone
from typing import NamedTuple

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from src.api.db.models.GameSession import GameSession


class ProfileStats(NamedTuple):
    total_games: int
    completed_games: int
    total_points: int
    best_score: int | None
    average_accuracy: float | None


def get_profile_stats(db: Session, user_id: str) -> ProfileStats:
    completed = GameSession.status == "completed"
    row = db.query(
        func.count(GameSession.id).label("total_games"),
        func.count(case((completed, GameSession.id))).label("completed_games"),
        func.coalesce(func.sum(case((completed, GameSession.final_score))), 0).label("total_points"),
        func.max(case((completed, GameSession.final_score))).label("best_score"),
        func.avg(case((completed, GameSession.accuracy))).label("average_accuracy"),
    ).filter(GameSession.user_id == user_id).one()
    return ProfileStats(
        total_games=row.total_games,
        completed_games=row.completed_games,
        total_points=row.total_points,
        best_score=row.best_score,
        average_accuracy=row.average_accuracy,
    )


def create_session(db: Session, user_id: str, music_title: str) -> GameSession:
    session = GameSession(user_id=user_id, music_title=music_title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: str) -> GameSession | None:
    return db.query(GameSession).filter(GameSession.id == session_id).first()


def end_session(
    db: Session,
    session_id: str,
    final_score: int,
    accuracy: float | None,
    abandoned: bool = False,
) -> GameSession | None:
    session = get_session(db, session_id)
    if not session:
        return None
    session.status = "abandoned" if abandoned else "completed"
    session.ended_at = datetime.now(timezone.utc)
    session.final_score = final_score
    session.accuracy = accuracy
    db.commit()
    db.refresh(session)
    return session


def get_sessions_by_user(db: Session, user_id: str, limit: int = 50) -> list[GameSession]:
    return (
        db.query(GameSession)
        .filter(GameSession.user_id == user_id)
        .order_by(GameSession.started_at.desc())
        .limit(limit)
        .all()
    )
