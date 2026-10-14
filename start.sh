#!/usr/bin/env bash
# One command: set up venv on first run, then serve UI + API at http://127.0.0.1:9005
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
exec .venv/bin/uvicorn main:app --host 127.0.0.1 --port "${PORT:-9005}"
