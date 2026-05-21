import mimetypes
import os
from datetime import timedelta

from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask
from minio import Minio

from ..core.config import get_settings


def _normalize_endpoint(endpoint: str) -> str:
    if endpoint.startswith("http://"):
        return endpoint[len("http://") :]
    if endpoint.startswith("https://"):
        return endpoint[len("https://") :]
    return endpoint


def _build_client(settings):
    access_key = settings.MINIO_ROOT_USER or settings.MINIO_ACCESS_KEY
    secret_key = settings.MINIO_ROOT_PASSWORD or settings.MINIO_SECRET_KEY
    endpoint = _normalize_endpoint(settings.MINIO_ENDPOINT)

    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=settings.MINIO_SECURE,
    )


def ensure_buckets_exist():
    """Crée les buckets MinIO s'ils n'existent pas"""
    settings = get_settings()
    client = _build_client(settings)

    buckets = [
        settings.MINIO_BUCKET_MUSIC,
        settings.MINIO_BUCKET_LEVELS,
    ]

    for bucket_name in buckets:
        try:
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
        except Exception as e:
            pass


class StorageService:
    def __init__(self, bucket_type: str = "music"):
        # On récupère les settings
        settings = get_settings()
        self.client = _build_client(settings)

        # Sélection du bucket selon le besoin (music ou levels)
        if bucket_type == "music":
            self.bucket_name = settings.MINIO_BUCKET_MUSIC
        else:
            self.bucket_name = settings.MINIO_BUCKET_LEVELS

    def get_download_url(self, object_name: str, expires_minutes: int = 60):
        """Génère une URL présignée pour Unity"""
        url = self.client.presigned_get_object(
            self.bucket_name, object_name, expires=timedelta(minutes=expires_minutes)
        )
        settings = get_settings()
        if settings.MINIO_PUBLIC_ENDPOINT:
            internal = _normalize_endpoint(settings.MINIO_ENDPOINT)
            public = _normalize_endpoint(settings.MINIO_PUBLIC_ENDPOINT)
            scheme = "https" if settings.MINIO_SECURE else "http"
            url = url.replace(f"{scheme}://{internal}", f"{scheme}://{public}", 1)
        return url

    def get_download_response(self, object_name: str):
        """Retourne une réponse de téléchargement servie par l'API."""
        object_response = self.client.get_object(self.bucket_name, object_name)
        try:
            content_type = (
                object_response.headers.get("content-type")
                or mimetypes.guess_type(object_name)[0]
                or "application/octet-stream"
            )
            filename = os.path.basename(object_name)
            headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
            return StreamingResponse(
                object_response.stream(32 * 1024),
                media_type=content_type,
                headers=headers,
                background=BackgroundTask(object_response.close),
            )
        except Exception:
            object_response.close()
            raise

    def upload_file(self, object_name: str, file_path: str):
        """Upload vers le bucket sélectionné"""
        self.client.fput_object(self.bucket_name, object_name, file_path)
        return object_name

    def download_file(self, object_name: str, local_destination: str):
        """Téléchargement pour analyse locale au worker"""
        self.client.fget_object(self.bucket_name, object_name, local_destination)
