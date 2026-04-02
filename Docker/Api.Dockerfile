FROM docker.io/library/python:3.12-slim

# Évite la génération de fichiers .pyc et force l'affichage des logs en temps réel
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Installer les dépendances
COPY requirements/requirements-api.txt requirements-api.txt
RUN pip install --no-cache-dir -r requirements-api.txt

# Copier le code de l'application
COPY src/ ./src/

# Expose le port configuré dans le .env 
EXPOSE 9050

# Lancer FastAPI avec Uvicorn
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "9050"]