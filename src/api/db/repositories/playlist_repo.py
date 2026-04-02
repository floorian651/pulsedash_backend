from sqlalchemy.orm import Session
from src.api.db.models import Playlist


def create_playlist(db: Session, name: str, description: str = None) -> Playlist:
    """Create a new playlist"""
    playlist = Playlist(name=name, description=description)
    db.add(playlist)
    db.commit()
    db.refresh(playlist)
    return playlist


def get_playlist(db: Session, name: str) -> Playlist:
    """Get playlist by name"""
    return db.query(Playlist).filter(Playlist.name == name).first()


def get_all_playlists(db: Session, skip: int = 0, limit: int = 100) -> list:
    """Get all playlists with pagination"""
    return db.query(Playlist).offset(skip).limit(limit).all()


def update_playlist(db: Session, name: str, description: str = None) -> Playlist:
    """Update playlist by name"""
    playlist = get_playlist(db, name)
    if playlist:
        if description is not None:
            playlist.description = description
        db.commit()
        db.refresh(playlist)
    return playlist


def delete_playlist(db: Session, name: str) -> bool:
    """Delete playlist by name and its tracks"""
    playlist = get_playlist(db, name)
    if playlist:
        db.delete(playlist)
        db.commit()
        return True
    return False
