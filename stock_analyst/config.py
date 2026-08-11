from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
import yaml
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AppPaths:
    root: Path
    data: Path
    cache: Path
    reports: Path
    research: Path
    charts: Path
    logs: Path
    db: Path


def expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def load_environment() -> None:
    env_file = ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=False)


def load_settings() -> dict:
    load_environment()
    with (ROOT / "config" / "settings.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_prompt_rules() -> dict:
    with (ROOT / "config" / "prompt_rules.yaml").open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def paths() -> AppPaths:
    load_environment()
    base = expand(os.getenv("STOCK_ANALYST_DATA_DIR", "~/stock-analyst-data"))
    p = AppPaths(
        root=base,
        data=base / "data",
        cache=base / "cache",
        reports=base / "reports",
        research=base / "research",
        charts=base / "charts",
        logs=base / "logs",
        db=base / "database" / "stock_analyst.sqlite3",
    )
    for directory in [p.root, p.data, p.cache, p.reports, p.research, p.charts, p.logs, p.db.parent]:
        directory.mkdir(parents=True, exist_ok=True)
    return p
