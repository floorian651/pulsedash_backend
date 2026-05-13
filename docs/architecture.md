# PulseDash — Architecture Backend

## Vue d'ensemble

```mermaid
flowchart TB
    subgraph Clients["Clients"]
        UNITY["🎮 Unity (jeu)"]
        WEB["🌐 Frontend Web"]
    end

    subgraph Edge["Edge"]
        CF["☁️ Cloudflare Tunnel"]
    end

    subgraph API["FastAPI  ·  :9050"]
        direction TB
        REST["REST API\n/api/v1/..."]
        WS["WebSocket\n/ws/jobs/{id}"]

        subgraph Routers["Routers"]
            R_AUTH["auth"]
            R_MUSIC["music · playlists · tracks"]
            R_JAM["jamendo"]
            R_GEN["generate"]
            R_JOBS["jobs"]
            R_SCORES["scores · game_sessions"]
            R_PROFILE["profile"]
        end
    end

    subgraph Async["Traitement asynchrone"]
        REDIS["🗄️ Redis\nBroker + Pub/Sub"]
        CELERY["⚙️ Celery Worker\ngenerate_level"]
        PIPELINE["🎵 Pipeline Librosa\nBPM · Key · Hits · Sections"]
    end

    subgraph Storage["Stockage"]
        PG[("🐘 PostgreSQL\nUsers · Tracks · Playlists\nScores · GameSessions · Jobs")]
        MINIO[("🪣 MinIO\nbucket: music\nbucket: levels")]
    end

    subgraph External["Externe"]
        JAMENDO["🎶 Jamendo API"]
    end

    %% Flux principaux
    Clients -->|"HTTPS"| CF
    CF -->|"HTTP"| API

    REST --> Routers
    WS <-->|"Pub/Sub"| REDIS

    Routers --> PG
    Routers -->|"Enqueue task"| REDIS
    Routers <-->|"Presigned URL"| MINIO
    R_JAM <-->|"Search / Download"| JAMENDO

    REDIS -->|"Task queue"| CELERY
    CELERY --> PIPELINE
    CELERY <-->|"Download / Upload"| MINIO
    CELERY -->|"Publish progress"| REDIS
    CELERY --> PG

    PIPELINE -->|"level.json"| CELERY

    style Clients fill:#1e3a5f,color:#fff,stroke:#4a9eff
    style Edge fill:#2d1b4e,color:#fff,stroke:#9b59b6
    style API fill:#1a3a2a,color:#fff,stroke:#2ecc71
    style Async fill:#3a2000,color:#fff,stroke:#f39c12
    style Storage fill:#2a1a1a,color:#fff,stroke:#e74c3c
    style External fill:#1a2a3a,color:#fff,stroke:#3498db
```

---

## Flux : génération d'un niveau

```mermaid
sequenceDiagram
    participant C as 🎮 Client
    participant API as ⚡ FastAPI
    participant RD as 🗄️ Redis
    participant CL as ⚙️ Celery
    participant JAM as 🎶 Jamendo
    participant MN as 🪣 MinIO
    participant PL as 🎵 Pipeline

    C->>API: POST /api/v1/generate\n{track_id}
    API->>RD: Enqueue generate_level
    API-->>C: {job_id}

    C->>API: WS /ws/jobs/{job_id}
    API->>RD: SUBSCRIBE job:{job_id}

    RD->>CL: Dispatch task
    CL->>JAM: Download MP3
    CL->>MN: Upload audio (bucket: music)
    Note over CL: progress 40%
    RD-->>API: {state: running, progress: 40}
    API-->>C: {state: running, progress: 40}

    CL->>PL: Analyse audio (librosa)
    Note over PL: BPM · Key · Hits · Sections
    Note over CL: progress 85%
    RD-->>API: {state: running, progress: 85}
    API-->>C: {state: running, progress: 85}

    CL->>MN: Upload level.json (bucket: levels)
    Note over CL: progress 100%
    RD-->>API: {state: completed, progress: 100}
    API-->>C: {state: completed, progress: 100}

    C->>API: GET /api/v1/jobs/{job_id}/result
    API->>MN: Presigned URL (level.json)
    API-->>C: level.json
```

---

## Stack technique

| Couche | Technologie |
|--------|-------------|
| **API** | FastAPI · Uvicorn · SQLAlchemy · Alembic |
| **Auth** | JWT (Bearer token) · SlowAPI (rate limiting) |
| **Async** | Celery · Redis (broker + pub/sub) |
| **Pipeline** | librosa · numpy |
| **BDD** | PostgreSQL 16 |
| **Stockage fichiers** | MinIO (S3-compatible) |
| **Musique externe** | Jamendo API |
| **Infra** | Podman Compose · Cloudflare Tunnel |
