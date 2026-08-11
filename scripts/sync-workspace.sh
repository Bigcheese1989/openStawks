#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKSPACE="${STOCK_ANALYST_OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace-stock-analyst}"
mkdir -p "$WORKSPACE/skills"
cp "$ROOT/workspace/AGENTS.md" "$WORKSPACE/AGENTS.md"
cp "$ROOT/workspace/IDENTITY.md" "$WORKSPACE/IDENTITY.md"
for d in "$ROOT"/workspace/skills/*; do
  name="$(basename "$d")"
  rm -rf "$WORKSPACE/skills/$name"
  cp -a "$d" "$WORKSPACE/skills/$name"
done
printf '%s\n' "$WORKSPACE"
