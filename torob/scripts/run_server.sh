#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

HOST="${TOROB_HOST:-0.0.0.0}"
PORT="${TOROB_PORT:-8080}"

echo "=========================================================="
echo " Starting Torob Intelligence Engine (Backend-First API)   "
echo " Host: $HOST | Port: $PORT                                "
echo " OpenAPI Docs: http://$HOST:$PORT/docs                     "
echo "=========================================================="

export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$SCRIPT_DIR/.venv/bin/python" -m uvicorn torob.api.main:app --host "$HOST" --port "$PORT"
