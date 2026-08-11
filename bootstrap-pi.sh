#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" != "Linux" ]]; then echo "This installer targets Linux/Raspberry Pi OS." >&2; exit 1; fi
ARCH="$(uname -m)"
if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" ]]; then
  echo "Warning: expected ARM64 Raspberry Pi; detected $ARCH. Continuing because the project is portable."
fi
command -v openclaw >/dev/null || { echo "Existing OpenClaw installation not found. Install/repair OpenClaw first." >&2; exit 1; }

if command -v apt-get >/dev/null; then
  echo "Installing OS packages..."
  sudo apt-get update
  packages=(python3 python3-venv python3-pip git curl ca-certificates fonts-dejavu-core fonts-liberation libcairo2 libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf-2.0-0)
  if apt-cache show chromium >/dev/null 2>&1; then packages+=(chromium); elif apt-cache show chromium-browser >/dev/null 2>&1; then packages+=(chromium-browser); fi
  sudo apt-get install -y "${packages[@]}"
fi

python3 - <<'PY'
import sys
if sys.version_info < (3,11):
    raise SystemExit(f"Python 3.11+ required; found {sys.version.split()[0]}")
PY

if [[ ! -f .env ]]; then cp .env.example .env; chmod 600 .env; fi

read_env() { sed -n "s/^$1=//p" .env | tail -n1; }
set_env() {
  local key="$1" value="$2"
  python3 - "$key" "$value" <<'PY'
from pathlib import Path
import sys
p=Path('.env'); key,value=sys.argv[1],sys.argv[2]
lines=p.read_text().splitlines(); out=[]; found=False
for line in lines:
    if line.startswith(key+'='):
        out.append(key+'='+value); found=True
    else: out.append(line)
if not found: out.append(key+'='+value)
p.write_text('\n'.join(out)+'\n')
PY
}

CURRENT_TARGET="$(read_env TELEGRAM_TARGET)"
if [[ -z "$CURRENT_TARGET" || "$CURRENT_TARGET" == "@your_username" ]]; then
  echo
  echo "Telegram target is required. It may be the numeric chat id or a target accepted by your configured OpenClaw Telegram channel."
  read -r -p "Telegram target: " TELEGRAM_TARGET
  [[ -n "$TELEGRAM_TARGET" ]] || { echo "Telegram target cannot be empty" >&2; exit 1; }
  set_env TELEGRAM_TARGET "$TELEGRAM_TARGET"
fi

DATA_DIR="$(read_env STOCK_ANALYST_DATA_DIR)"
DATA_DIR="${DATA_DIR:-~/stock-analyst-data}"
EXPANDED_DATA="${DATA_DIR/#\~/$HOME}"
mkdir -p "$EXPANDED_DATA"

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -e '.[dev]'

stock-analyst init-db >/dev/null
"$ROOT/scripts/configure-openclaw.sh"
"$ROOT/scripts/install-cron.sh"

pytest -q

echo "Generating local sample PDF..."
SAMPLE_PDF="$(stock-analyst sample-report)"
echo "Sample PDF: $SAMPLE_PDF"

echo "Testing Telegram PDF delivery..."
stock-analyst sample-report --send >/dev/null

stock-analyst doctor

echo
echo "Installation complete. A SAMPLE REPORT PDF should be in Telegram."
echo "Daily live reports are scheduled for 08:10 America/New_York on NYSE weekdays."
echo "Run a live test without Telegram:  source .venv/bin/activate && stock-analyst daily --dry-run --force"
