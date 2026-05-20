# PulseDash Backend

Backend d'un jeu de rythme (style Beat Saber) : analyse audio automatique, génération de niveaux, sessions de jeu et classements.

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
  └─ Publie la progression via Redis pub/sub

WebSocket /ws/jobs/{job_id}
  └─ Souscrit Redis avant lecture DB (pas de race condition)
  └─ Envoie l'état initial puis les mises à jour en temps réel
```

## Démarrage

### Prérequis

- [Podman](https://podman.io/) + `podman-compose`
- Python 3.12 + [uv](https://github.com/astral-sh/uv)

### Configuration

```bash
cp .env.example .env
# Remplir les variables ci-dessous
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

L'image API utilise la stage `prod` par défaut (pas de deps dev, pas de reload).

### Accès Tailscale / pare-feu

Le bridge Podman de production est figé sur `pulsedash-br` et le subnet du réseau est fixé pour garder des IPs stables. Les règles iptables/UFW utilisées pour exposer PostgreSQL et MinIO via Tailscale sont détaillées dans [IPTABLES_RULES.md](IPTABLES_RULES.md).

Si tu réappliques le stack manuellement hors de ce compose, il faut garder le même subnet et les mêmes IPs avant de recharger `/etc/iptables/rules.v4`.

### Développement local

```bash
uv sync
uv run uvicorn src.api.main:app --reload --port 9050
```

## Tests

```bash
uv run pytest
```

Les tests utilisent SQLite en mémoire et mockent MinIO/Celery — aucun service externe requis.

## Endpoints principaux

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Création de compte |
| `POST` | `/api/v1/auth/login` | Connexion (access + refresh token) |
| `GET` | `/api/v1/jamendo/search?q=` | Recherche de musiques sur Jamendo |
| `POST` | `/api/v1/jamendo/import/{track_id}` | Import + génération du niveau |
| `POST` | `/api/v1/music` | Ajout manuel (multipart, fichier optionnel) |
| `POST` | `/api/v1/generate` | Régénérer le niveau d'une musique existante |
| `GET` | `/api/v1/jobs/{job_id}` | État d'un job (progress, result_url, error) |
| `WS` | `/ws/jobs/{job_id}` | Suivi temps réel via WebSocket |
| `POST` | `/api/v1/game-sessions` | Démarrer une session de jeu |
| `POST` | `/api/v1/game-sessions/{id}/end` | Terminer (crée le score automatiquement) |
| `GET` | `/api/v1/scores/top?music_title=` | Classement par musique |
| `GET` | `/api/v1/scores/global` | Classement global |
| `GET` | `/api/v1/profile/me` | Profil + statistiques du joueur |

## Structure du projet

```
src/
├── api/
│   ├── core/          # Config, Celery, rate limiter
│   ├── db/
│   │   ├── models/    # SQLAlchemy ORM
│   │   ├── repositories/
│   │   └── migrations/
│   ├── routers/       # Endpoints FastAPI
│   ├── schemas/       # Pydantic I/O
│   └── services/      # Jamendo, MinIO, tâches Celery
└── pipeline/          # Analyse audio (librosa)
```

## Format du niveau généré

```json
{
  "meta": { "bpm": 128.0, "key": "C", "duration": 224.0 },
  "hits": [{ "time": 0.46, "lane": 2, "type": "tap", "strength": 0.8 }],
  "sections": [{ "start": 0.0, "end": 32.0, "label": "intro" }]
}
```