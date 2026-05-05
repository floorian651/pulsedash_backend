from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.api.core.limiter import limiter
from src.api.db.session import get_session
from src.api.db.repositories import user_repo
from src.api.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserProfile
from src.api.services.auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_refresh_token
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_session)):
    if user_repo.get_user_by_email(db, body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé")

    user = user_repo.create_user(db, email=body.email, password=hash_password(body.password), username=body.username)
    user_id = str(user.id)
    return TokenResponse(access_token=create_access_token(user_id), refresh_token=create_refresh_token(user_id))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_session)):
    user = user_repo.get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, str(user.password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants incorrects")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")

    user_id = str(user.id)
    return TokenResponse(access_token=create_access_token(user_id), refresh_token=create_refresh_token(user_id))


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_session)):
    try:
        user_id = decode_refresh_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide")

    user = user_repo.get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")

    return TokenResponse(access_token=create_access_token(user_id), refresh_token=create_refresh_token(user_id))


@router.get("/me", response_model=UserProfile)
def me(current_user=Depends(get_current_user)):
    return current_user
