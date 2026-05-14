import redis
from src.api.core.config import get_settings

settings = get_settings()


def _get_client() -> redis.Redis:
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_BLACKLIST_DB,
        decode_responses=True,
    )


def blacklist_jti(jti: str, ttl_seconds: int) -> None:
    if ttl_seconds <= 0:
        return
    _get_client().setex(f"bl:{jti}", ttl_seconds, "1")


def is_blacklisted(jti: str) -> bool:
    return bool(_get_client().exists(f"bl:{jti}"))
