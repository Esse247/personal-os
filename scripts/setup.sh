#!/usr/bin/env sh
set -eu

PYTHON_BIN="${PERSONAL_OS_BOOTSTRAP_PYTHON:-python3}"
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e 'backend[dev]'
npm install
.venv/bin/python -m alembic -c backend/alembic.ini upgrade head
.venv/bin/python -m personal_os.cli fixtures-load
npm run setup:check
printf '%s\n' 'Setup complete. All runtime data is synthetic and all providers are mocked.'
