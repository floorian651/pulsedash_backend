from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..db.session import get_session
from ..db.repositories import track_repo
from ..schemas.track import TrackCreate, TrackUpdate, TrackResponse

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("", response_model=list[TrackResponse])
async def list_tracks(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_session)
):
    """List all tracks with pagination"""
    tracks = track_repo.get_all_tracks(db, skip=skip, limit=limit)
    return tracks


@router.get("/playlist/{playlist_name}", response_model=list[TrackResponse])
async def list_playlist_tracks(playlist_name: str, db: Session = Depends(get_session)):
    """Get all tracks in a specific playlist, ordered by position"""
    tracks = track_repo.get_tracks_by_playlist(db, playlist_name)
    if not tracks:
        # This is OK - playlist may exist but have no tracks, or may not exist
        # We return empty list either way
        return []
    return tracks


@router.get("/{track_id}", response_model=TrackResponse)
async def get_track(track_id: int, db: Session = Depends(get_session)):
    """Get track by ID"""
    track = track_repo.get_track(db, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@router.post("", response_model=TrackResponse)
async def create_track(track_data: TrackCreate, db: Session = Depends(get_session)):
    """Create a new track in a playlist"""
    # Validate that the playlist and music exist
    from ..db.models import Playlist, Music

    playlist = (
        db.query(Playlist).filter(Playlist.name == track_data.playlist_name).first()
    )
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    music = db.query(Music).filter(Music.title == track_data.music_title).first()
    if not music:
        raise HTTPException(status_code=404, detail="Music not found")

    track = track_repo.create_track(
        db,
        playlist_name=track_data.playlist_name,
        music_title=track_data.music_title,
        position=track_data.position,
    )
    return track


@router.put("/{track_id}", response_model=TrackResponse)
async def update_track(
    track_id: int, track_data: TrackUpdate, db: Session = Depends(get_session)
):
    """Update track by ID"""
    track = track_repo.get_track(db, track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    updated_track = track_repo.update_track(
        db, track_id=track_id, position=track_data.position
    )
    return updated_track


@router.delete("/{track_id}")
async def delete_track(track_id: int, db: Session = Depends(get_session)):
    """Delete track by ID"""
    deleted = track_repo.delete_track(db, track_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Track not found")
    return {"status": "deleted", "track_id": track_id}
