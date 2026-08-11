#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="Stock Analyst Daily PDF"
RUNNER="$ROOT/scripts/run-daily.sh"

# Remove only our own prior job, if present, to keep bootstrap/update idempotent.
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
if openclaw cron list --all --json >"$TMP" 2>/dev/null; then
  IDS="$(python3 - "$TMP" "$NAME" <<'PY'
import json,sys
obj=json.load(open(sys.argv[1]))
name=sys.argv[2]
found=[]
def walk(x):
    if isinstance(x,dict):
        if x.get('name')==name and x.get('id'):
            found.append(str(x['id']))
        for v in x.values(): walk(v)
    elif isinstance(x,list):
        for v in x: walk(v)
walk(obj)
print('\n'.join(dict.fromkeys(found)))
PY
)"
  while IFS= read -r id; do
    [[ -z "$id" ]] || openclaw cron remove "$id" >/dev/null
  done <<<"$IDS"
fi

openclaw cron create "10 8 * * 1-5" \
  --name "$NAME" \
  --tz "America/New_York" \
  --command "$RUNNER" \
  --command-cwd "$ROOT" \
  --timeout-seconds 3600 \
  --no-deliver >/dev/null

echo "Installed OpenClaw cron: weekdays 08:10 America/New_York"
