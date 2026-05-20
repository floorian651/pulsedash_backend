#!/bin/sh
set -e
echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
python - <<'PY'
import os
import socket
import time

host = os.getenv("POSTGRES_HOST", "db")
port = int(os.getenv("POSTGRES_PORT", "5432"))
timeout_seconds = int(os.getenv("DB_WAIT_TIMEOUT", "60"))
deadline = time.monotonic() + timeout_seconds
last_error = None

while time.monotonic() < deadline:
	try:
		with socket.create_connection((host, port), timeout=2):
			break
	except OSError as exc:
		last_error = exc
		time.sleep(2)
else:
	raise SystemExit(
		f"PostgreSQL at {host}:{port} is not reachable after {timeout_seconds}s: {last_error}"
	)
PY

uv run --no-sync alembic upgrade head
exec "$@"
