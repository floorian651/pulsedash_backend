import os

from celery import Celery
from celery.signals import worker_process_init


def _build_broker_url() -> str:
    user = os.getenv("REDIS_USER", "")
    password = os.getenv("REDIS_PASSWORD", "")
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    db = os.getenv("REDIS_DB", "0")

    auth = ""
    if user and password:
        auth = f"{user}:{password}@"
    elif password:
        auth = f":{password}@"

    return f"redis://{auth}{host}:{port}/{db}"


broker_url = _build_broker_url()
result_backend = broker_url

app = Celery("wavr", broker=broker_url, backend=result_backend)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=os.getenv("TZ", "UTC"),
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    include=["src.api.services.tasks"],
)


def init_worker_db(**kwargs):
    """Initialize database engine when worker process starts."""
    from src.api.core.config import get_settings
    from src.api.db.session import init_engine

    settings = get_settings()
    init_engine(settings.DATABASE_URL)


worker_process_init.connect(init_worker_db, sender=app)
