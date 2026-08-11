#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_ID="${OPENCLAW_AGENT_ID:-stock-analyst}"
"$ROOT/scripts/remove-cron.sh" || true
if openclaw config get "agents.entries.${AGENT_ID}" --json >/dev/null 2>&1; then
  openclaw agents delete "$AGENT_ID" --force >/dev/null || true
fi
if [[ "${1:-}" == "--purge-data" ]]; then
  DATA_DIR="${STOCK_ANALYST_DATA_DIR:-$HOME/stock-analyst-data}"
  rm -rf "${DATA_DIR/#\~/$HOME}"
fi
echo "Stock Analyst OpenClaw agent and cron removed. Data preserved unless --purge-data was supplied."
