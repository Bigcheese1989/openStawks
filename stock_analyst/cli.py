from __future__ import annotations

import argparse
from .config import load_settings, paths
from .database import initialize
from .delivery import send_pdf
from .doctor import run_doctor
from .pipeline import run_daily
from .sample import create_sample_report


def main() -> None:
    parser = argparse.ArgumentParser(prog="stock-analyst", description="Read-only OpenClaw equity-research bot")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    sub.add_parser("init-db")
    p_sample = sub.add_parser("sample-report")
    p_sample.add_argument("--send", action="store_true")
    p_daily = sub.add_parser("daily")
    p_daily.add_argument("--dry-run", action="store_true")
    p_daily.add_argument("--force", action="store_true", help="Run even on a non-NYSE trading day")

    args = parser.parse_args()
    if args.cmd == "doctor":
        raise SystemExit(run_doctor())
    if args.cmd == "init-db":
        settings = load_settings()
        initialize(paths().db, float(settings["portfolio"]["starting_cash"]))
        print(paths().db)
        return
    if args.cmd == "sample-report":
        artifacts = create_sample_report()
        if args.send:
            send_pdf(artifacts.pdf_path, "Stock Analyst installation test — SAMPLE REPORT")
        print(artifacts.pdf_path)
        return
    if args.cmd == "daily":
        result = run_daily(dry_run=args.dry_run, force=args.force)
        if result is None:
            print("NO_REPLY")
        else:
            print(result.model_dump_json())
        return


if __name__ == "__main__":
    main()
