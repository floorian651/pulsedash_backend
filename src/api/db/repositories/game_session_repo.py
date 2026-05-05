from datetime import datetime

from sqlalchemy.orm import Session

from src.api.db.models.GameSession import GameSession


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
    session.ended_at = datetime.utcnow()
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
