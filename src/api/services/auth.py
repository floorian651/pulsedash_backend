import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from src.api.core.config import get_settings
from src.api.services.token_blacklist import blacklist_jti, is_blacklisted

settings = get_settings()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "access", "jti": str(uuid.uuid4())},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": user_id, "exp": expire, "type": "refresh", "jti": str(uuid.uuid4())},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

def _decode_payload(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

def decode_token(token: str) -> str:
    payload = _decode_payload(token)
    if payload.get("type") == "refresh":
        raise JWTError("refresh token not accepted here")
    jti = payload.get("jti")
    if jti and is_blacklisted(jti):
        raise JWTError("token révoqué")
    return payload["sub"]

def decode_refresh_token(token: str) -> str:
    payload = _decode_payload(token)
    if payload.get("type") != "refresh":
        raise JWTError("not a refresh token")
    jti = payload.get("jti")
    if jti and is_blacklisted(jti):
        raise JWTError("token révoqué")
    return payload["sub"]

def revoke_token(token: str) -> None:
    """Blacklist a token using its JTI. Silently ignores invalid tokens."""
    try:
        payload = _decode_payload(token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            ttl = int(exp) - int(datetime.now(timezone.utc).timestamp())
            blacklist_jti(jti, ttl)
    except Exception:
        pass