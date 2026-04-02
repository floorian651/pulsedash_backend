from sqlalchemy.orm import Session
from src.api.db.models import Track


def create_track(
    db: Session, playlist_name: str, music_title: str, position: int = None
) -> Track:
    """Create a new track in a playlist"""
    track = Track(
        playlist_name=playlist_name, music_title=music_title, position=position
    )
    db.add(track)
    db.commit()
    db.refresh(track)
    return track


def get_track(db: Session, track_id: int) -> Track:
    """Get track by ID"""
    return db.query(Track).filter(Track.id == track_id).first()


def get_tracks_by_playlist(db: Session, playlist_name: str) -> list:
    """Get all tracks in a playlist"""
    return (
        db.query(Track)
        .filter(Track.playlist_name == playlist_name)
        .order_by(Track.position)
        .all()
    )


def get_all_tracks(db: Session, skip: int = 0, limit: int = 100) -> list:
    """Get all tracks with pagination"""
    return db.query(Track).offset(skip).limit(limit).all()


def update_track(db: Session, track_id: int, position: int = None) -> Track:
    """Update track by ID"""
    track = get_track(db, track_id)
    if track:
        if position is not None:
            track.position = position
        db.commit()
        db.refresh(track)
    return track


def delete_track(db: Session, track_id: int) -> bool:
    """Delete track by ID"""
    track = get_track(db, track_id)
    if track:
        db.delete(track)
        db.commit()
        return True
    return False
