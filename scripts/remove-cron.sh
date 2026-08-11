#!/usr/bin/env bash
set -euo pipefail
NAME="Stock Analyst Daily PDF"
TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
openclaw cron list --all --json >"$TMP" 2>/dev/null || exit 0
python3 - "$TMP" "$NAME" <<'PY' | while IFS= read -r id; do [[ -z "$id" ]] || openclaw cron remove "$id" >/dev/null; done
import json,sys
obj=json.load(open(sys.argv[1])); name=sys.argv[2]
def walk(x):
    if isinstance(x,dict):
        if x.get('name')==name and x.get('id'): print(x['id'])
        for v in x.values(): walk(v)
    elif isinstance(x,list):
        for v in x: walk(v)
walk(obj)
PY
