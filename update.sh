#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$ROOT"
if [[ -d .git ]]; then git pull --ff-only; fi
source .venv/bin/activate
python -m pip install -e '.[dev]'
"$ROOT/scripts/configure-openclaw.sh"
"$ROOT/scripts/install-cron.sh"
pytest -q
stock-analyst doctor
