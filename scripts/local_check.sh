#!/usr/bin/env bash
set -euo pipefail

python --version
node --version

cd backend
python -m ruff check app tests
python -m mypy app
python -m pytest

cd ../frontend
npm install
npm run typecheck
npm run build

cd ..
python scripts/check_media_paths.py
