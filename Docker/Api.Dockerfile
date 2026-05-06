FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_CACHE=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY Docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 9050

ENTRYPOINT ["/entrypoint.sh"]

# ---------- Production ----------
FROM base AS prod

RUN uv sync --frozen --no-install-project --no-dev

COPY src/ ./src/
COPY alembic.ini ./

CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "9050"]

# ---------- Development ----------
FROM base AS dev

RUN uv sync --frozen --no-install-project

COPY src/ ./src/
COPY alembic.ini ./

CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "9050", "--reload"]
