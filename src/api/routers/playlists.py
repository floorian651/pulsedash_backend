from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..dependencies import get_current_user
from ..db.session import get_session
from ..db.repositories import playlist_repo
from ..schemas.playlist import PlaylistCreate, PlaylistUpdate, PlaylistResponse

router = APIRouter(prefix="/playlists", tags=["playlists"])


@router.get("", response_model=list[PlaylistResponse])
async def list_playlists(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_session)
):
    """List all playlists with pagination"""
    playlists = playlist_repo.get_all_playlists(db, skip=skip, limit=limit)
    return playlists


@router.get("/{name}", response_model=PlaylistResponse)
async def get_playlist(name: str, db: Session = Depends(get_session)):
    """Get playlist by name with its tracks"""
    playlist = playlist_repo.get_playlist(db, name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return playlist


@router.post("", response_model=PlaylistResponse)
async def create_playlist(
    playlist_data: PlaylistCreate, db: Session = Depends(get_session), _=Depends(get_current_user)
):
    """Create a new playlist"""
    existing_playlist = playlist_repo.get_playlist(db, playlist_data.name)
    if existing_playlist:
        raise HTTPException(
            status_code=400, detail="Playlist with this name already exists"
        )

    playlist = playlist_repo.create_playlist(
        db, name=playlist_data.name, description=playlist_data.description
    )
    return playlist


@router.put("/{name}", response_model=PlaylistResponse)
async def update_playlist(
    name: str, playlist_data: PlaylistUpdate, db: Session = Depends(get_session), _=Depends(get_current_user)
):
    """Update playlist by name"""
    playlist = playlist_repo.get_playlist(db, name)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    updated_playlist = playlist_repo.update_playlist(
        db, name=name, description=playlist_data.description
    )
    return updated_playlist


@router.delete("/{name}")
async def delete_playlist(name: str, db: Session = Depends(get_session), _=Depends(get_current_user)):
    """Delete playlist by name (also deletes all its tracks)"""
    deleted = playlist_repo.delete_playlist(db, name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Playlist not found")
    return {"status": "deleted", "name": name}
