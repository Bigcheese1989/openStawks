from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

from . import database
from .charts import (
    allocation_chart, equity_curve_chart, market_performance_chart, ranking_chart,
    scorecard_chart, sector_return_chart, stock_price_chart,
)
from .config import load_environment, load_settings, paths
from .delivery import send_pdf
from .market import MarketBundle, compute_screen, download_market_data, normalized_series, save_bundle
from .models import DailyRunResult
from .portfolio import current_state, rebalance
from .report import build_report
from .research import research_company, run_committee
from .universe import fetch_sp500


def _is_trading_day(day, timezone: str) -> bool:
    import pandas_market_calendars as mcal
    nyse = mcal.get_calendar("NYSE")
    schedule = nyse.schedule(start_date=day.isoformat(), end_date=day.isoformat())
    return not schedule.empty


def _latest_prices(closes: pd.DataFrame) -> dict[str, float]:
    result = {}
    for ticker in closes.columns:
        s = closes[ticker].dropna()
        if not s.empty:
            result[ticker] = float(s.iloc[-1])
    return result


def _price_context(ticker: str, closes: pd.DataFrame, screen_lookup: dict[str, dict]) -> dict:
    if ticker in screen_lookup:
        row = dict(screen_lookup[ticker])
        for k, v in list(row.items()):
            if hasattr(v, "item"):
                row[k] = v.item()
        return row
    s = closes[ticker].dropna() if ticker in closes else pd.Series(dtype=float)
    if s.empty:
        return {"ticker": ticker, "note": "No deterministic price context available"}
    ret = lambda d: float(s.iloc[-1] / s.iloc[-1-d] - 1) if len(s) > d else None
    return {
        "ticker": ticker,
        "price": float(s.iloc[-1]),
        "return_1m": ret(21), "return_3m": ret(63), "return_6m": ret(126), "return_12m": ret(252),
        "note": "Existing model holding included for re-review even if it did not pass today's screen.",
    }


def run_daily(*, dry_run: bool = False, force: bool = False) -> DailyRunResult | None:
    load_environment()
    settings = load_settings()
    p = paths()
    tz = ZoneInfo(settings["timezone"])
    report_date = datetime.now(tz).date()
    if not force and not _is_trading_day(report_date, settings["timezone"]):
        return None

    database.initialize(p.db, float(settings["portfolio"]["starting_cash"]))
    with database.connect(p.db) as conn:
        existing = database.holdings(conn)

    universe_rows = fetch_sp500(p.cache / "sp500.csv")
    meta = {x["ticker"]: x for x in universe_rows}
    universe_symbols = list(meta)
    dashboard_symbols = list(settings["market_dashboard"]["indexes"]) + list(settings["market_dashboard"]["sectors"])
    symbols = list(dict.fromkeys(universe_symbols + list(existing) + dashboard_symbols))

    bundle = download_market_data(symbols, period=settings["history_period"])
    save_bundle(bundle, p.data, report_date.isoformat())

    universe_cols = [s for s in universe_symbols if s in bundle.closes.columns]
    universe_bundle = MarketBundle(bundle.closes[universe_cols], bundle.volumes[[s for s in universe_cols if s in bundle.volumes.columns]])
    screen = compute_screen(universe_bundle, meta, settings)
    screen.to_csv(p.data / f"screen-{report_date.isoformat()}.csv", index=False)
    screen_lookup = {str(row["ticker"]): row.to_dict() for _, row in screen.iterrows()}

    research_tickers = screen.head(int(settings["research_count"]))["ticker"].tolist()
    for ticker in existing:
        if ticker in bundle.closes.columns and ticker not in research_tickers:
            research_tickers.append(ticker)

    research_results = []
    research_dir = p.research / report_date.isoformat()
    research_dir.mkdir(parents=True, exist_ok=True)
    for ticker in research_tickers:
        candidate = meta.get(ticker, {"ticker": ticker, "name": ticker, "sector": "Unknown", "industry": ""}).copy()
        candidate["ticker"] = ticker
        result = research_company(report_date, candidate, _price_context(ticker, bundle.closes, screen_lookup))
        research_results.append(result)
        (research_dir / f"{ticker}.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")

    prices = _latest_prices(bundle.closes)
    with database.connect(p.db) as conn:
        before = current_state(conn, prices)
        decision = run_committee(report_date, research_results, before, settings)
        (research_dir / "committee.json").write_text(decision.model_dump_json(indent=2), encoding="utf-8")
        trades, after = rebalance(conn, report_date, decision, prices, settings["portfolio"])

        benchmark_symbol = settings["benchmark"]
        benchmark_price = prices.get(benchmark_symbol)
        benchmark_shares = database.get_meta(conn, "benchmark_shares")
        if benchmark_price and not benchmark_shares:
            starting_cash = float(database.get_meta(conn, "starting_cash", str(settings["portfolio"]["starting_cash"])))
            benchmark_shares = repr(starting_cash / benchmark_price)
            database.set_meta(conn, "benchmark_shares", benchmark_shares)
        benchmark_value = float(benchmark_shares) * benchmark_price if benchmark_price and benchmark_shares else None

        for r in research_results:
            database.save_recommendation(conn, report_date, r)
        database.save_snapshot(conn, report_date, after["equity"], after["cash"], benchmark_value, after)
        conn.commit()
        history = database.performance_history(conn)

    chart_dir = p.charts / report_date.isoformat()
    chart_dir.mkdir(parents=True, exist_ok=True)
    market_norm = normalized_series(bundle.closes, list(settings["market_dashboard"]["indexes"]), days=126)
    market_path = market_performance_chart(market_norm, settings["market_dashboard"]["indexes"], chart_dir / "market.png")
    sector_path = sector_return_chart(bundle.closes, settings["market_dashboard"]["sectors"], chart_dir / "sectors.png")
    ranking_path = ranking_chart(screen, chart_dir / "ranking.png")
    allocation_path = allocation_chart(after, chart_dir / "allocation.png")
    equity_path = equity_curve_chart(history, chart_dir / "equity.png")
    company_charts, score_charts = {}, {}
    for r in research_results:
        if r.ticker in bundle.closes:
            cp = stock_price_chart(bundle.closes[r.ticker], r.ticker, chart_dir / f"{r.ticker}-price.png")
            company_charts[r.ticker] = cp.as_uri() if cp else None
        sp = scorecard_chart(r.score, r.ticker, chart_dir / f"{r.ticker}-scores.png")
        score_charts[r.ticker] = sp.as_uri()

    charts = {
        "market": market_path.as_uri() if market_path else None,
        "sectors": sector_path.as_uri() if sector_path else None,
        "ranking": ranking_path.as_uri() if ranking_path else None,
        "allocation": allocation_path.as_uri() if allocation_path else None,
        "equity": equity_path.as_uri() if equity_path else None,
        "companies": company_charts,
        "scores": score_charts,
    }
    artifacts = build_report(
        report_date=report_date,
        settings=settings,
        screen_rows=screen.to_dict(orient="records"),
        research=research_results,
        decision=decision,
        portfolio_before=before,
        portfolio_after=after,
        trades=trades,
        charts=charts,
        history=history,
    )

    if os.getenv("KEEP_HTML_REPORTS", "true").lower() not in {"1", "true", "yes"}:
        artifacts.html_path.unlink(missing_ok=True)

    sent = False
    if not dry_run:
        send_pdf(
            artifacts.pdf_path,
            f"Daily Equity Research — {report_date.isoformat()}\nModel-portfolio changes: {len(trades)}",
        )
        sent = True

    return DailyRunResult(
        report_date=report_date,
        pdf_path=str(artifacts.pdf_path),
        action_count=len(trades),
        sent=sent,
    )
