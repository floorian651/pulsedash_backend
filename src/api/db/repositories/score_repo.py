from sqlalchemy.orm import Session

from src.api.db.models.Score import Score


def create_score(db: Session, user_id: str, track_id: str, points: int, accuracy: float = None) -> Score:
    score = Score(user_id=user_id, track_id=track_id, points=points, accuracy=accuracy)
    db.add(score)
    db.commit()
    db.refresh(score)
    return score


def get_top_scores(db: Session, track_id: str, limit: int = 10) -> list[Score]:
    return (
        db.query(Score)
        .filter(Score.track_id == track_id)
        .order_by(Score.points.desc())
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
