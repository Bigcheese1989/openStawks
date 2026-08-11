from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS holdings (
  ticker TEXT PRIMARY KEY,
  shares REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  report_date TEXT PRIMARY KEY,
  equity REAL NOT NULL,
  cash REAL NOT NULL,
  benchmark REAL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_date TEXT NOT NULL,
  ticker TEXT NOT NULL,
  side TEXT NOT NULL,
  shares REAL NOT NULL,
  price REAL NOT NULL,
  notional REAL NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recommendations (
  report_date TEXT NOT NULL,
  ticker TEXT NOT NULL,
  conclusion TEXT NOT NULL,
  confidence REAL NOT NULL,
  composite_score REAL NOT NULL,
  payload_json TEXT NOT NULL,
  PRIMARY KEY(report_date, ticker)
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def initialize(path: Path, starting_cash: float) -> None:
    with connect(path) as conn:
        conn.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('cash',?)", (str(starting_cash),))
        conn.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('starting_cash',?)", (str(starting_cash),))
        conn.commit()



def get_meta(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )

def get_cash(conn: sqlite3.Connection) -> float:
    row = conn.execute("SELECT value FROM meta WHERE key='cash'").fetchone()
    return float(row["value"]) if row else 0.0


def set_cash(conn: sqlite3.Connection, cash: float) -> None:
    conn.execute(
        "INSERT INTO meta(key,value) VALUES('cash',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (repr(float(cash)),),
    )


def holdings(conn: sqlite3.Connection) -> dict[str, float]:
    return {row["ticker"]: float(row["shares"]) for row in conn.execute("SELECT ticker,shares FROM holdings")}


def set_holding(conn: sqlite3.Connection, ticker: str, shares: float) -> None:
    if abs(shares) < 1e-8:
        conn.execute("DELETE FROM holdings WHERE ticker=?", (ticker,))
    else:
        conn.execute(
            "INSERT INTO holdings(ticker,shares) VALUES(?,?) ON CONFLICT(ticker) DO UPDATE SET shares=excluded.shares",
            (ticker, float(shares)),
        )


def save_trade(conn: sqlite3.Connection, report_date: date, ticker: str, side: str, shares: float, price: float) -> None:
    conn.execute(
        "INSERT INTO trades(report_date,ticker,side,shares,price,notional,created_at) VALUES(?,?,?,?,?,?,?)",
        (report_date.isoformat(), ticker, side, shares, price, shares * price, datetime.now(timezone.utc).isoformat()),
    )


def save_snapshot(conn: sqlite3.Connection, report_date: date, equity: float, cash: float, benchmark: float | None, payload: dict) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO portfolio_snapshots(report_date,equity,cash,benchmark,payload_json,created_at)
           VALUES(?,?,?,?,?,?)""",
        (report_date.isoformat(), equity, cash, benchmark, json.dumps(payload), datetime.now(timezone.utc).isoformat()),
    )


def save_recommendation(conn: sqlite3.Connection, report_date: date, research) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO recommendations(report_date,ticker,conclusion,confidence,composite_score,payload_json)
           VALUES(?,?,?,?,?,?)""",
        (
            report_date.isoformat(), research.ticker, research.conclusion, research.confidence,
            research.score.composite, research.model_dump_json(),
        ),
    )


def performance_history(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT report_date,equity,cash,benchmark FROM portfolio_snapshots ORDER BY report_date"
    ).fetchall()
    return [dict(row) for row in rows]
