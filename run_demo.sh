#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# WSL installations commonly keep Node in nvm.
if ! command -v node >/dev/null && [ -s "$HOME/.nvm/nvm.sh" ]; then
  source "$HOME/.nvm/nvm.sh"
fi
command -v node >/dev/null || { echo "Install Node.js 20+ first."; exit 1; }
[ -d backend/venv ] || python3 -m venv backend/venv
backend/venv/bin/python -m pip install -r backend/requirements.txt
backend/venv/bin/python backend/setup_db.py
if [ ! -d frontend/node_modules ]; then
  npm --prefix frontend ci
fi
npm --prefix frontend run build
echo "Open http://localhost:${PORT:-8000}"
echo "Create the first new account locally; it becomes the administrator."
exec backend/venv/bin/uvicorn main:app --app-dir backend --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
