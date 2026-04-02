from sqlalchemy.orm import Session
from src.api.db.models import Music


def create_music(
    db: Session,
    title: str,
    artist: str = None,
    bpm: float = None,
    duration: float = None,
    file_path: str = None,
    bucket_name: str = "musics",
) -> Music:
    """Create a new music"""
    music = Music(
        title=title,
        artist=artist,
        bpm=bpm,
        duration=duration,
        file_path=file_path,
        bucket_name=bucket_name,
    )
    db.add(music)
    db.commit()
    db.refresh(music)
    return music


def get_music(db: Session, title: str) -> Music:
    """Get music by title"""
    return db.query(Music).filter(Music.title == title).first()


def get_all_music(db: Session, skip: int = 0, limit: int = 100) -> list:
    """Get all music with pagination"""
    return db.query(Music).offset(skip).limit(limit).all()


def update_music(
    db: Session,
    title: str,
    artist: str = None,
    bpm: float = None,
    duration: float = None,
) -> Music:
    """Update music by title"""
    music = get_music(db, title)
    if music:
        if artist is not None:
            music.artist = artist
        if bpm is not None:
            music.bpm = bpm
        if duration is not None:
            music.duration = duration
        db.commit()
        db.refresh(music)
    return music


def delete_music(db: Session, title: str) -> bool:
    """Delete music by title"""
    music = get_music(db, title)
    if music:
        db.delete(music)
        db.commit()
        return True
    return False
