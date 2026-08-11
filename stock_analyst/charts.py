from __future__ import annotations

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def market_performance_chart(normalized: pd.DataFrame, labels: dict[str, str], path: Path) -> Path | None:
    if normalized.empty:
        return None
    fig, ax = plt.subplots(figsize=(10, 4.4))
    for col in normalized.columns:
        ax.plot(normalized.index, normalized[col], linewidth=1.8, label=labels.get(col, col))
    ax.axhline(100, linewidth=0.8, alpha=0.4)
    ax.set_title("Six-month relative performance (start = 100)")
    ax.set_ylabel("Indexed value")
    ax.grid(alpha=0.2)
    ax.legend(loc="best", frameon=False, ncol=min(3, len(normalized.columns)))
    return _save(fig, path)


def sector_return_chart(closes: pd.DataFrame, labels: dict[str, str], path: Path) -> Path | None:
    values = []
    for ticker, label in labels.items():
        if ticker not in closes:
            continue
        s = closes[ticker].dropna()
        if len(s) < 22:
            continue
        values.append((label, float(s.iloc[-1] / s.iloc[-22] - 1) * 100))
    if not values:
        return None
    values.sort(key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(10, 5.2))
    names = [x[0] for x in values]
    returns = [x[1] for x in values]
    ax.barh(names, returns)
    ax.axvline(0, linewidth=0.8)
    ax.set_title("Sector ETF performance — trailing 1 month")
    ax.set_xlabel("Return (%)")
    ax.grid(axis="x", alpha=0.2)
    return _save(fig, path)


def ranking_chart(screen: pd.DataFrame, path: Path, top_n: int = 12) -> Path | None:
    if screen.empty:
        return None
    d = screen.head(top_n).sort_values("quant_score")
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    ax.barh(d["ticker"], d["quant_score"])
    ax.set_title("Quantitative shortlist")
    ax.set_xlabel("Quantitative score (0–100)")
    ax.set_xlim(0, 100)
    ax.grid(axis="x", alpha=0.2)
    return _save(fig, path)


def stock_price_chart(close: pd.Series, ticker: str, path: Path) -> Path | None:
    s = close.dropna().tail(252)
    if len(s) < 30:
        return None
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.plot(s.index, s, linewidth=1.7, label="Price")
    ma50 = s.rolling(50).mean()
    ma200 = s.rolling(200).mean()
    ax.plot(ma50.index, ma50, linewidth=1.1, label="50-day MA")
    if ma200.notna().any():
        ax.plot(ma200.index, ma200, linewidth=1.1, label="200-day MA")
    ax.set_title(f"{ticker} — adjusted price")
    ax.set_ylabel("USD")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    return _save(fig, path)


def scorecard_chart(score, ticker: str, path: Path) -> Path:
    names = ["Fundamentals", "Valuation", "Momentum", "Catalysts", "Risk"]
    values = [score.fundamentals, score.valuation, score.momentum, score.catalysts, score.risk]
    fig, ax = plt.subplots(figsize=(8.5, 3.5))
    ax.barh(names[::-1], values[::-1])
    ax.set_xlim(0, 100)
    ax.set_xlabel("Score")
    ax.set_title(f"{ticker} research scorecard")
    ax.grid(axis="x", alpha=0.2)
    return _save(fig, path)


def allocation_chart(portfolio_state: dict, path: Path) -> Path | None:
    rows = [(p["ticker"], p["weight"] * 100) for p in portfolio_state.get("positions", []) if p["weight"] > 0.001]
    cash_pct = portfolio_state.get("cash", 0) / portfolio_state.get("equity", 1) * 100 if portfolio_state.get("equity") else 0
    rows.append(("Cash", cash_pct))
    rows.sort(key=lambda x: x[1])
    if not rows:
        return None
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.barh([r[0] for r in rows], [r[1] for r in rows])
    ax.set_title("Model portfolio allocation")
    ax.set_xlabel("Weight (%)")
    ax.grid(axis="x", alpha=0.2)
    return _save(fig, path)


def equity_curve_chart(history: list[dict], path: Path) -> Path | None:
    if len(history) < 2:
        return None
    df = pd.DataFrame(history)
    df["report_date"] = pd.to_datetime(df["report_date"])
    fig, ax = plt.subplots(figsize=(10, 4.3))
    ax.plot(df["report_date"], df["equity"], linewidth=1.8, label="Model portfolio")
    if df["benchmark"].notna().any():
        ax.plot(df["report_date"], df["benchmark"], linewidth=1.5, label="S&P 500 benchmark")
    ax.set_title("Model portfolio vs benchmark")
    ax.set_ylabel("Value (USD)")
    ax.grid(alpha=0.2)
    ax.legend(frameon=False)
    return _save(fig, path)
