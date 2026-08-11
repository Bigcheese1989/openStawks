# Methodology

## Stage 1 — deterministic quantitative shortlist

The default universe is the current S&P 500 constituent list fetched from Wikipedia and cached for seven days. Price/volume history is downloaded through `yfinance`. The screen removes very low-priced, illiquid, and insufficient-history securities, then ranks the survivors using 1/3/6/12-month momentum, 50/200-day trend, liquidity, and inverse volatility.

The screen is only a candidate generator. It is deliberately not the final recommendation model.

## Stage 2 — evidence-backed company research

The top ranked names plus all existing model-portfolio holdings are sent one at a time to the restricted OpenClaw research agent. The agent is instructed to prioritize SEC filings, company investor-relations material, and high-quality current news, to return real URLs, and to produce a structured thesis, bear case, catalysts, invalidation criteria, valuation scenarios, scores, and confidence.

## Stage 3 — investment committee

A separate OpenClaw turn receives the validated research packages and the hypothetical model portfolio. It can propose target weights subject to configured caps. The deterministic portfolio engine then enforces maximum position size, minimum cash, minimum trade size, and maximum daily turnover.

## Stage 4 — audit and report

Research JSON, screen results, model-portfolio history, and generated reports are retained. The PDF is rendered from a deterministic Jinja2 HTML template with matplotlib charts and sent through the existing OpenClaw Telegram channel.

## Important data note

`yfinance` is convenient and keyless but is not a licensed institutional market-data feed. Before relying on the system for material capital, replace the market-data layer with a provider whose licensing, uptime, adjustment policy, and data quality meet your requirements. The provider is intentionally isolated behind `stock_analyst/market.py` for that reason.
