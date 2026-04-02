FROM docker.io/library/python:3.12-slim

# Variables d'environnement pour optimiser
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Installer les dépendances système minimales pour audio/compilattion
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    libopenblas0 \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements/requirements-celery.txt requirements-celery.txt
RUN pip install --no-cache-dir -r requirements-celery.txt

# Copier le code source
COPY src/ ./src/

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 celery && chown -R celery:celery /app
USER celery

# Lancer le worker Celery
CMD ["celery", "-A", "src.api.core.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
