#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source "$ROOT/.venv/bin/activate"
LOG_DIR="$(python -c 'from stock_analyst.config import paths; print(paths().logs)')"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/daily-$(date +%F).log"

set +e
stock-analyst daily >>"$LOG" 2>&1
status=$?
set -e
if [[ $status -ne 0 ]]; then
  python - <<'PY' || true
from stock_analyst.delivery import send_text
send_text("Stock Analyst daily run failed. The report was not sent. Check the Raspberry Pi logs.")
PY
  tail -n 60 "$LOG" >&2
  exit "$status"
fi
# Suppress cron fallback text; the PDF itself is delivered by the pipeline.
echo "NO_REPLY"
