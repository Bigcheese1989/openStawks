from __future__ import annotations

from datetime import date
import sqlite3
from . import database
from .models import CommitteeDecision, Trade


def current_state(conn: sqlite3.Connection, prices: dict[str, float]) -> dict:
    h = database.holdings(conn)
    cash = database.get_cash(conn)
    positions = []
    invested = 0.0
    for ticker, shares in h.items():
        price = float(prices.get(ticker, 0.0))
        value = shares * price
        invested += value
        positions.append({"ticker": ticker, "shares": shares, "price": price, "value": value})
    equity = cash + invested
    for p in positions:
        p["weight"] = p["value"] / equity if equity else 0.0
    return {"cash": cash, "equity": equity, "positions": positions}


def rebalance(
    conn: sqlite3.Connection,
    report_date: date,
    decision: CommitteeDecision,
    prices: dict[str, float],
    cfg: dict,
) -> tuple[list[Trade], dict]:
    state = current_state(conn, prices)
    equity = state["equity"]
    if equity <= 0:
        raise RuntimeError("Model portfolio has non-positive equity")

    current_weights = {p["ticker"]: p["weight"] for p in state["positions"]}
    target_weights = dict(current_weights)
    max_pos = float(cfg["maximum_position_weight"])
    for target in decision.targets:
        if target.ticker not in prices or prices[target.ticker] <= 0:
            continue
        target_weights[target.ticker] = min(float(target.target_weight), max_pos)

    minimum_cash = float(cfg["minimum_cash_weight"])
    max_invested = 1.0 - minimum_cash
    total_target = sum(target_weights.values())
    if total_target > max_invested and total_target > 0:
        scale = max_invested / total_target
        target_weights = {k: v * scale for k, v in target_weights.items()}

    deltas = {}
    for ticker in set(current_weights) | set(target_weights):
        price = prices.get(ticker)
        if not price or price <= 0:
            continue
        current = current_weights.get(ticker, 0.0)
        target = target_weights.get(ticker, current)
        delta_weight = target - current
        if abs(delta_weight) < float(cfg["minimum_trade_weight"]):
            continue
        deltas[ticker] = delta_weight * equity

    gross = sum(abs(x) for x in deltas.values())
    max_turnover = float(cfg["maximum_daily_turnover"]) * equity
    scale = min(1.0, max_turnover / gross) if gross > 0 else 1.0

    # Sells first so cash is available for buys.
    trades: list[Trade] = []
    ordered = sorted(deltas.items(), key=lambda x: x[1])
    h = database.holdings(conn)
    starting_tickers = {t for t, shares in h.items() if shares > 1e-8}
    cash = database.get_cash(conn)

    for ticker, raw_notional in ordered:
        price = float(prices[ticker])
        notional = raw_notional * scale
        if notional >= 0:
            continue
        max_sell = h.get(ticker, 0.0) * price
        sell_notional = min(abs(notional), max_sell)
        shares = sell_notional / price
        if shares <= 0:
            continue
        h[ticker] = max(0.0, h.get(ticker, 0.0) - shares)
        cash += sell_notional
        database.set_holding(conn, ticker, h[ticker])
        database.save_trade(conn, report_date, ticker, "SELL", shares, price)
        trades.append(Trade(ticker=ticker, side="SELL", shares=shares, price=price, notional=sell_notional))

    new_buys = 0
    max_new_buys = int(cfg.get("maximum_new_buys_per_day", 3))
    for ticker, raw_notional in ordered:
        if raw_notional <= 0:
            continue
        is_new = ticker not in starting_tickers
        if is_new and new_buys >= max_new_buys:
            continue
        price = float(prices[ticker])
        buy_notional = min(raw_notional * scale, max(0.0, cash - equity * minimum_cash))
        shares = buy_notional / price
        if shares <= 0:
            continue
        h[ticker] = h.get(ticker, 0.0) + shares
        cash -= buy_notional
        database.set_holding(conn, ticker, h[ticker])
        database.save_trade(conn, report_date, ticker, "BUY", shares, price)
        trades.append(Trade(ticker=ticker, side="BUY", shares=shares, price=price, notional=buy_notional))
        if is_new:
            new_buys += 1

    database.set_cash(conn, cash)
    conn.commit()
    return trades, current_state(conn, prices)
