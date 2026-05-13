from sqlalchemy.orm import Session

from src.api.db.models import User


def create_user(db: Session, email: str, password: str, username: str | None = None) -> User:
    user = User(email=email, password=password, username=username)
    db.add(user)
    db.commit()
    return user


def get_user_by_email(db: Session, email: str) -> User:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> User:
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: str) -> User:
    return db.query(User).filter(User.id == user_id).first()
