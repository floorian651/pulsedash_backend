from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.db.session import get_session
from src.api.db.repositories import game_session_repo, score_repo
from src.api.db.models.Music import Music
from src.api.schemas.game_session import GameSessionEnd, GameSessionResponse, GameSessionStart
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/game-sessions", tags=["game-sessions"])


@router.post("", response_model=GameSessionResponse, status_code=201)
async def start_session(
    body: GameSessionStart,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    music = db.query(Music).filter(Music.title == body.music_title).first()
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")

    return game_session_repo.create_session(
        db, user_id=str(current_user.id), music_title=body.music_title
    )


@router.patch("/{session_id}/end", response_model=GameSessionResponse)
async def end_session(
    session_id: str,
    body: GameSessionEnd,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    session = game_session_repo.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not your session")
    if session.status != "active":
        raise HTTPException(status_code=409, detail="Session already ended")

    updated = game_session_repo.end_session(
        db,
        session_id=session_id,
        final_score=body.final_score,
        accuracy=body.accuracy,
        abandoned=body.abandoned,
    )

    if not body.abandoned:
        score_repo.create_score(
            db,
            user_id=str(current_user.id),
            session_id=session_id,
            music_title=session.music_title,
            points=body.final_score,
            accuracy=body.accuracy,
        )

    return updated


@router.get("/me", response_model=list[GameSessionResponse])
async def get_my_sessions(
    limit: int = 50,
    db: Session = Depends(get_session),
    current_user=Depends(get_current_user),
):
    return game_session_repo.get_sessions_by_user(
        db, user_id=str(current_user.id), limit=limit
    )
