from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd


@dataclass
class MarketBundle:
    closes: pd.DataFrame
    volumes: pd.DataFrame


def download_market_data(symbols: list[str], period: str = "1y", chunk_size: int = 80) -> MarketBundle:
    import yfinance as yf
    closes: list[pd.DataFrame] = []
    volumes: list[pd.DataFrame] = []
    unique = list(dict.fromkeys(s.upper() for s in symbols if s))
    for i in range(0, len(unique), chunk_size):
        chunk = unique[i:i + chunk_size]
        frame = yf.download(
            tickers=chunk,
            period=period,
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by="column",
            timeout=30,
        )
        if frame is None or frame.empty:
            continue
        close, volume = _extract_fields(frame, chunk)
        closes.append(close)
        volumes.append(volume)
    if not closes:
        raise RuntimeError("Market-data download returned no prices")
    close_df = pd.concat(closes, axis=1)
    volume_df = pd.concat(volumes, axis=1)
    close_df = close_df.loc[:, ~close_df.columns.duplicated()].sort_index()
    volume_df = volume_df.loc[:, ~volume_df.columns.duplicated()].sort_index()
    return MarketBundle(close_df, volume_df)


def _extract_fields(frame: pd.DataFrame, requested: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if isinstance(frame.columns, pd.MultiIndex):
        level0 = frame.columns.get_level_values(0)
        if "Close" in level0:
            close = frame["Close"].copy()
            volume = frame["Volume"].copy()
        else:
            close_cols, vol_cols = {}, {}
            for symbol in requested:
                if (symbol, "Close") in frame.columns:
                    close_cols[symbol] = frame[(symbol, "Close")]
                if (symbol, "Volume") in frame.columns:
                    vol_cols[symbol] = frame[(symbol, "Volume")]
            close, volume = pd.DataFrame(close_cols), pd.DataFrame(vol_cols)
    else:
        symbol = requested[0]
        close = frame[["Close"]].rename(columns={"Close": symbol})
        volume = frame[["Volume"]].rename(columns={"Volume": symbol})
    close.columns = [str(c).upper() for c in close.columns]
    volume.columns = [str(c).upper() for c in volume.columns]
    return close, volume


def compute_screen(bundle: MarketBundle, meta: dict[str, dict], settings: dict) -> pd.DataFrame:
    close, volume = bundle.closes, bundle.volumes
    rows = []
    cfg = settings["screen"]
    min_days = int(cfg["minimum_history_days"])

    for ticker in close.columns:
        s = close[ticker].dropna()
        if len(s) < min_days:
            continue
        latest = float(s.iloc[-1])
        if latest < float(cfg["minimum_price"]):
            continue
        v = volume[ticker].reindex(s.index).fillna(0) if ticker in volume.columns else pd.Series(index=s.index, data=0.0)
        adv = float((s.tail(20) * v.tail(20)).mean())
        if not math.isfinite(adv) or adv < float(cfg["minimum_avg_dollar_volume"]):
            continue

        def ret(days: int) -> float:
            if len(s) <= days:
                return float("nan")
            return float(s.iloc[-1] / s.iloc[-1 - days] - 1)

        daily = s.pct_change().dropna()
        vol60 = float(daily.tail(60).std() * np.sqrt(252)) if len(daily) >= 20 else float("nan")
        ma50 = float(s.tail(50).mean())
        ma200 = float(s.tail(200).mean())
        rows.append({
            "ticker": ticker,
            "name": meta.get(ticker, {}).get("name", ticker),
            "sector": meta.get(ticker, {}).get("sector", "Unknown"),
            "price": latest,
            "return_1m": ret(21),
            "return_3m": ret(63),
            "return_6m": ret(126),
            "return_12m": ret(252),
            "ma50_gap": latest / ma50 - 1 if ma50 else 0,
            "ma200_gap": latest / ma200 - 1 if ma200 else 0,
            "volatility_60d": vol60,
            "avg_dollar_volume_20d": adv,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("No stocks survived the quantitative screening filters")

    pct = lambda col, asc=True: df[col].rank(pct=True, ascending=asc).fillna(0.5)
    df["p_1m"] = pct("return_1m")
    df["p_3m"] = pct("return_3m")
    df["p_6m"] = pct("return_6m")
    df["p_12m"] = pct("return_12m")
    trend_raw = (df["ma50_gap"].clip(-0.5, 0.5) + df["ma200_gap"].clip(-0.5, 0.5)) / 2
    df["p_trend"] = trend_raw.rank(pct=True).fillna(0.5)
    df["p_liquidity"] = np.log10(df["avg_dollar_volume_20d"].clip(lower=1)).rank(pct=True).fillna(0.5)
    df["p_low_vol"] = df["volatility_60d"].rank(pct=True, ascending=False).fillna(0.5)

    w = cfg["weights"]
    df["quant_score"] = 100 * (
        df["p_1m"] * w["momentum_1m"]
        + df["p_3m"] * w["momentum_3m"]
        + df["p_6m"] * w["momentum_6m"]
        + df["p_12m"] * w["momentum_12m"]
        + df["p_trend"] * w["trend"]
        + df["p_liquidity"] * w["liquidity"]
        + df["p_low_vol"] * w["low_volatility"]
    )
    return df.sort_values("quant_score", ascending=False).reset_index(drop=True)


def normalized_series(closes: pd.DataFrame, symbols: list[str], days: int = 126) -> pd.DataFrame:
    data = closes[[s for s in symbols if s in closes.columns]].tail(days).dropna(how="all")
    if data.empty:
        return data
    return data.apply(lambda x: x / x.dropna().iloc[0] * 100 if x.notna().any() else x)


def save_bundle(bundle: MarketBundle, directory: Path, date_key: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    bundle.closes.to_pickle(directory / f"closes-{date_key}.pkl")
    bundle.volumes.to_pickle(directory / f"volumes-{date_key}.pkl")
