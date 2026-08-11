from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from .config import load_environment, paths


def _run(args: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        return p.returncode, p.stdout.strip()
    except Exception as exc:
        return 1, str(exc)


def run_doctor() -> int:
    load_environment()
    checks: list[tuple[str, bool, str]] = []
    machine = platform.machine().lower()
    checks.append(("Architecture", machine in {"aarch64", "arm64", "x86_64", "amd64"}, machine))
    oc = shutil.which("openclaw")
    checks.append(("OpenClaw CLI", bool(oc), oc or "not found"))
    browser = next((shutil.which(x) for x in ("chromium","chromium-browser","google-chrome") if shutil.which(x)), None)
    checks.append(("Chromium", bool(browser), browser or "not found"))
    checks.append(("Telegram target", bool(os.getenv("TELEGRAM_TARGET","")), os.getenv("TELEGRAM_TARGET", "not configured")))
    checks.append(("Data directory", True, str(paths().root)))

    if oc:
        code, out = _run(["openclaw", "gateway", "status"])
        checks.append(("OpenClaw Gateway", code == 0, out.splitlines()[-1] if out else "no output"))
        agent = os.getenv("OPENCLAW_AGENT_ID", "stock-analyst")
        code, out = _run(["openclaw", "config", "get", f"agents.entries.{agent}.tools", "--json"])
        secure = False
        detail = out[:500]
        if code == 0:
            try:
                tools = json.loads(out)
                allowed = set(tools.get("allow", []))
                denied = set(tools.get("deny", []))
                secure = {"web_search", "web_fetch"}.issubset(allowed) and {"exec","process","write","edit","apply_patch","browser","cron","gateway"}.issubset(denied)
            except Exception:
                pass
        checks.append(("Agent security policy", secure, detail))

    width = max(len(x[0]) for x in checks)
    failed = False
    for name, ok, detail in checks:
        failed |= not ok
        print(f"{'OK' if ok else 'FAIL':4}  {name:<{width}}  {detail}")
    return 1 if failed else 0
