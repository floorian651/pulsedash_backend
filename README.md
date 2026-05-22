# PulseDash Backend

Backend d'un projet de jeu de rythme basé sur l'analyse d'une musique afin d'en extraire un niveau de manière automatique.

**Documentation backend complète : [floorian651.github.io/pulsedash](https://floorian651.github.io/pulsedash/)**

---

## Stack

| Composant | Rôle |
|-----------|------|
| FastAPI + Python 3.12 | API REST + WebSocket |
| PostgreSQL 16 | Base de données |
| Celery + Redis 7 | Traitement asynchrone (génération de niveaux) |
| MinIO | Stockage objet (audio, niveaux JSON) |
| librosa / numpy | Pipeline d'analyse audio |
| JWT (jose + bcrypt) | Authentification |
| Cloudflare Tunnel | Exposition publique |

## Architecture

```
POST /jamendo/import/{track_id}
  └─ Télécharge l'audio depuis Jamendo
  └─ Stocke dans MinIO (bucket music)
  └─ Crée l'entrée Music en DB
  └─ Lance generate_level_task (Celery)

generate_level_task
  └─ Récupère l'audio depuis MinIO
  └─ Pipeline : BPM, beats, sections, hits
  └─ Stocke level.json dans MinIO (bucket levels)
  └─ Publie la progression via Redis

WebSocket /ws/jobs/{job_id}
  └─ Souscrit Redis avant lecture DB (pas de race condition)
  └─ Envoie l'état initial puis les mises à jour en temps réel
```

## Démarrage

### Prérequis

- [Podman](https://podman.io/) + `podman-compose`
- Python 3.12 + [uv](https://github.com/astral-sh/uv)

### Configuration

Copier le .env d'exemple et remplir les variables suivantes selon votre configuration :
```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `POSTGRES_USER` | Utilisateur PostgreSQL |
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL |
| `POSTGRES_DB` | Nom de la base |
| `MINIO_ROOT_USER` | Accès MinIO |
| `MINIO_ROOT_PASSWORD` | Secret MinIO |
| `MINIO_ENDPOINT` | Host:port MinIO (ex : `localhost:9000`) |
| `MINIO_ACCESS_KEY` | Clé d'accès MinIO |
| `MINIO_SECRET_KEY` | Secret MinIO |
| `REDIS_HOST` | Host Redis |
| `JWT_SECRET_KEY` | Clé secrète JWT (min. 32 caractères) |
| `JAMENDO_CLIENT_ID` | Client ID de l'API Jamendo |
| `TUNNEL_TOKEN` | Token Cloudflare Tunnel (optionnel) |

### Lancement en développement

```bash
podman-compose -f podman-compose.dev.yml up -d
```

L'image API est construite avec la stage `dev` (deps de dev incluses, `--reload` activé).

| Service | Accès |
|---------|-------|
| API REST | `http://localhost:9050` |
| Documentation interactive (Swagger) | `http://localhost:9050/docs` |
| MinIO console | `http://localhost:9001` |
| MinIO S3 API | `http://localhost:9000` |

### Lancement en production (avec tunnel)

```bash
podman-compose up -d
```

### Accès Tailscale / pare-feu

Le bridge Podman de production est fixé sur `pulsedash-br` et le subnet du réseau est fixé pour garder des IPs stables. 
Les règles iptables/UFW utilisées pour exposer PostgreSQL et MinIO via Tailscale sont détaillées dans la documentation.

### Développement local

```bash
uv sync
uv run uvicorn src.api.main:app --reload --port 9050
```

## Tests

```bash
uv run pytest
```

Les tests utilisent SQLite en mémoire et mockent MinIO/Celery — aucun service externe requis. La CI tourne automatiquement sur GitHub Actions à chaque push.