#!/usr/bin/env sh
set -eu

python -m app.rag.ingest

uvicorn app.main:app --host 0.0.0.0 --port 8000 &
api_pid=$!

python app/ui.py &
ui_pid=$!

cleanup() {
  kill "$api_pid" "$ui_pid" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

wait "$api_pid"
