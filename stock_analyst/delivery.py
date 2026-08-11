from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from .config import load_environment


def send_pdf(pdf: Path, message: str) -> None:
    load_environment()
    target = os.getenv("TELEGRAM_TARGET", "").strip()
    if not target:
        raise RuntimeError("TELEGRAM_TARGET is not configured in .env")
    cmd = [
        "openclaw", "message", "send",
        "--channel", "telegram",
        "--target", target,
        "--message", message,
        "--media", str(pdf.resolve()),
        "--force-document",
        "--json",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"Telegram PDF delivery failed: {proc.stderr.strip()[-1000:]}")
    if proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout)
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(f"Telegram delivery returned an error: {payload['error']}")
        except json.JSONDecodeError:
            pass


def send_text(message: str) -> None:
    load_environment()
    target = os.getenv("TELEGRAM_TARGET", "").strip()
    if not target:
        return
    subprocess.run(
        ["openclaw", "message", "send", "--channel", "telegram", "--target", target, "--message", message],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60,
    )
