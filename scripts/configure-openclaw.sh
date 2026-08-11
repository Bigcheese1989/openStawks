#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENT_ID="${OPENCLAW_AGENT_ID:-stock-analyst}"
WORKSPACE="${STOCK_ANALYST_OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace-stock-analyst}"

command -v openclaw >/dev/null || { echo "OpenClaw CLI is not installed or not in PATH" >&2; exit 1; }
"$ROOT/scripts/sync-workspace.sh" >/dev/null

if ! openclaw config get "agents.entries.${AGENT_ID}" --json >/dev/null 2>&1; then
  openclaw agents add "$AGENT_ID" --workspace "$WORKSPACE" --non-interactive --json >/dev/null
fi

# The model-facing agent is research-only. Deny is intentionally redundant with allow.
openclaw config set "agents.entries.${AGENT_ID}.tools.profile" 'coding' >/dev/null
openclaw config set "agents.entries.${AGENT_ID}.tools.allow" '["web_search","web_fetch","read"]' --strict-json >/dev/null
openclaw config set "agents.entries.${AGENT_ID}.tools.deny" '["exec","process","write","edit","apply_patch","browser","message","cron","gateway","skill_workshop","group:messaging"]' --strict-json >/dev/null
openclaw config set "agents.entries.${AGENT_ID}.tools.fs.workspaceOnly" 'true' --strict-json >/dev/null
openclaw config set "agents.entries.${AGENT_ID}.tools.elevated.enabled" 'false' --strict-json >/dev/null
openclaw config set "agents.entries.${AGENT_ID}.sandbox.mode" 'off' >/dev/null

openclaw config validate >/dev/null
openclaw gateway restart >/dev/null
sleep 2
openclaw gateway status >/dev/null

echo "Configured OpenClaw agent: $AGENT_ID"
