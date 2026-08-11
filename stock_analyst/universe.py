from __future__ import annotations

import csv
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

FALLBACK = [
    ("AAPL", "Apple", "Information Technology"), ("MSFT", "Microsoft", "Information Technology"),
    ("NVDA", "NVIDIA", "Information Technology"), ("AMZN", "Amazon", "Consumer Discretionary"),
    ("GOOGL", "Alphabet A", "Communication Services"), ("GOOG", "Alphabet C", "Communication Services"),
    ("META", "Meta Platforms", "Communication Services"), ("BRK-B", "Berkshire Hathaway", "Financials"),
    ("LLY", "Eli Lilly", "Health Care"), ("AVGO", "Broadcom", "Information Technology"),
    ("TSLA", "Tesla", "Consumer Discretionary"), ("JPM", "JPMorgan Chase", "Financials"),
    ("WMT", "Walmart", "Consumer Staples"), ("V", "Visa", "Financials"), ("MA", "Mastercard", "Financials"),
    ("XOM", "Exxon Mobil", "Energy"), ("UNH", "UnitedHealth", "Health Care"), ("COST", "Costco", "Consumer Staples"),
    ("NFLX", "Netflix", "Communication Services"), ("ORCL", "Oracle", "Information Technology"),
    ("HD", "Home Depot", "Consumer Discretionary"), ("PG", "Procter & Gamble", "Consumer Staples"),
    ("JNJ", "Johnson & Johnson", "Health Care"), ("ABBV", "AbbVie", "Health Care"), ("BAC", "Bank of America", "Financials"),
    ("KO", "Coca-Cola", "Consumer Staples"), ("CRM", "Salesforce", "Information Technology"), ("AMD", "AMD", "Information Technology"),
    ("CVX", "Chevron", "Energy"), ("CSCO", "Cisco", "Information Technology"), ("PEP", "PepsiCo", "Consumer Staples"),
    ("TMO", "Thermo Fisher", "Health Care"), ("ACN", "Accenture", "Information Technology"), ("MCD", "McDonald's", "Consumer Discretionary"),
    ("LIN", "Linde", "Materials"), ("ADBE", "Adobe", "Information Technology"), ("IBM", "IBM", "Information Technology"),
    ("WFC", "Wells Fargo", "Financials"), ("GE", "GE Aerospace", "Industrials"), ("CAT", "Caterpillar", "Industrials"),
    ("NOW", "ServiceNow", "Information Technology"), ("INTU", "Intuit", "Information Technology"), ("QCOM", "Qualcomm", "Information Technology"),
    ("AMGN", "Amgen", "Health Care"), ("TXN", "Texas Instruments", "Information Technology"), ("DIS", "Disney", "Communication Services"),
    ("PM", "Philip Morris", "Consumer Staples"), ("GS", "Goldman Sachs", "Financials"), ("AXP", "American Express", "Financials"),
]


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().replace(".", "-")


def fetch_sp500(cache_file: Path, max_age_days: int = 7) -> list[dict]:
    if cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < max_age_days * 86400:
        return _read_csv(cache_file)

    try:
        response = requests.get(
            SP500_URL,
            timeout=20,
            headers={"User-Agent": "stock-analyst-openclaw/0.1 (+personal research bot)"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table", id="constituents")
        if not table:
            raise RuntimeError("S&P 500 constituent table was not found")
        rows = []
        for tr in table.find("tbody").find_all("tr"):
            td = tr.find_all("td")
            if len(td) < 4:
                continue
            rows.append({
                "ticker": _normalize_symbol(td[0].get_text(strip=True)),
                "name": td[1].get_text(strip=True),
                "sector": td[2].get_text(strip=True),
                "industry": td[3].get_text(strip=True),
            })
        if len(rows) < 400:
            raise RuntimeError(f"Only {len(rows)} constituents parsed")
        _write_csv(cache_file, rows)
        return rows
    except Exception:
        rows = [{"ticker": t, "name": n, "sector": s, "industry": ""} for t, n, s in FALLBACK]
        _write_csv(cache_file, rows)
        return rows


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["ticker", "name", "sector", "industry"])
        writer.writeheader()
        writer.writerows(rows)
