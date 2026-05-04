from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.db.session import get_session
from src.api.db.repositories import user_repo
from src.api.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserProfile
from src.api.services.auth import hash_password, verify_password, create_access_token
from src.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_session)):
    if user_repo.get_user_by_email(db, body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé")

    user = user_repo.create_user(db, email=body.email, password=hash_password(body.password), username=body.username)
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_session)):
    user = user_repo.get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, str(user.password)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiants incorrects")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Compte désactivé")

    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserProfile)
def me(current_user=Depends(get_current_user)):
    return current_user
