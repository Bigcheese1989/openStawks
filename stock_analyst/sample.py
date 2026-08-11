from __future__ import annotations

from datetime import date, timedelta
import numpy as np
import pandas as pd

from .charts import allocation_chart, equity_curve_chart, market_performance_chart, ranking_chart, scorecard_chart, stock_price_chart
from .config import load_settings, paths
from .models import CitedPoint, CommitteeDecision, CompanyResearch, ScoreCard, Source, TargetPosition, Trade, ValuationScenario
from .report import build_report


def create_sample_report():
    settings = load_settings()
    p = paths()
    d = date.today()
    rng = np.random.default_rng(42)
    idx = pd.bdate_range(end=pd.Timestamp(d), periods=252)

    prices = {}
    for ticker, start, drift in [("ACME", 90, 0.0007), ("NOVA", 55, 0.0004), ("SPY", 500, 0.00035), ("QQQ", 430, 0.00045), ("IWM", 205, 0.0002)]:
        returns = rng.normal(drift, 0.015, len(idx))
        prices[ticker] = start * np.cumprod(1 + returns)
    closes = pd.DataFrame(prices, index=idx)

    research = [
        CompanyResearch(
            ticker="ACME", company_name="Acme Systems (illustrative)", sector="Technology",
            conclusion="BUY", confidence=0.78,
            score=ScoreCard(fundamentals=88, valuation=74, momentum=84, catalysts=81, risk=72),
            summary="Illustrative sample only: recurring revenue growth and improving operating leverage support a favorable risk/reward profile.",
            thesis=[CitedPoint(text="Illustrative thesis point: revenue quality is improving.", source_ids=["S1"]), CitedPoint(text="Illustrative thesis point: operating leverage is emerging.", source_ids=["S1"])],
            risks=[CitedPoint(text="Illustrative risk: valuation could compress if growth decelerates.", source_ids=["S1"])],
            catalysts=[CitedPoint(text="Illustrative catalyst: upcoming product cycle.", source_ids=["S1"])],
            invalidation=["Illustrative: material guidance cut", "Illustrative: sustained margin reversal"],
            valuation=ValuationScenario(bear=92, base=132, bull=158, assumptions=["Illustrative scenario values only"]),
            sources=[Source(id="S1", title="Illustrative placeholder - not a research source", url="https://example.com/", publisher="Sample", source_type="other")],
        ),
        CompanyResearch(
            ticker="NOVA", company_name="Nova Industries (illustrative)", sector="Industrials",
            conclusion="WATCH", confidence=0.66,
            score=ScoreCard(fundamentals=75, valuation=68, momentum=70, catalysts=62, risk=69),
            summary="Illustrative sample only: business quality is acceptable but the catalyst set is not strong enough for a new position.",
            thesis=[CitedPoint(text="Illustrative thesis point: stable free cash flow.", source_ids=["S1"])],
            risks=[CitedPoint(text="Illustrative risk: cyclicality and weaker order growth.", source_ids=["S1"])],
            catalysts=[CitedPoint(text="Illustrative catalyst: potential order recovery.", source_ids=["S1"])],
            invalidation=["Illustrative: order backlog contracts materially"],
            valuation=ValuationScenario(bear=48, base=63, bull=72, assumptions=["Illustrative scenario values only"]),
            sources=[Source(id="S1", title="Illustrative placeholder - not a research source", url="https://example.com/", publisher="Sample", source_type="other")],
        ),
    ]
    decision = CommitteeDecision(
        market_stance="moderately_bullish",
        executive_summary="This is a generated sample used only to validate layout, charts, PDF rendering and Telegram delivery.",
        key_market_risks=["Illustrative macro risk", "Illustrative valuation risk"],
        top_opportunity="ACME",
        targets=[TargetPosition(ticker="ACME", target_weight=0.07, action="BUY", rationale="Illustrative target")],
        watchlist=["NOVA"],
    )
    screen = [
        {"ticker":"ACME","name":"Acme Systems","sector":"Technology","price":float(closes.ACME.iloc[-1]),"quant_score":88.2,"return_1m":0.071,"return_6m":0.225},
        {"ticker":"NOVA","name":"Nova Industries","sector":"Industrials","price":float(closes.NOVA.iloc[-1]),"quant_score":81.5,"return_1m":0.031,"return_6m":0.104},
    ]
    screen_df = pd.DataFrame(screen)
    after = {"cash":93000.0,"equity":100000.0,"positions":[{"ticker":"ACME","shares":7000/float(closes.ACME.iloc[-1]),"price":float(closes.ACME.iloc[-1]),"value":7000.0,"weight":0.07}]}
    before = {"cash":100000.0,"equity":100000.0,"positions":[]}
    history = [
        {"report_date":(d-timedelta(days=3)).isoformat(),"equity":100000.0,"cash":100000.0,"benchmark":100000.0},
        {"report_date":d.isoformat(),"equity":100000.0,"cash":93000.0,"benchmark":100500.0},
    ]
    chart_dir = p.charts / f"sample-{d.isoformat()}"
    chart_dir.mkdir(parents=True, exist_ok=True)
    market = market_performance_chart(closes[["SPY","QQQ","IWM"]].tail(126).apply(lambda x:x/x.iloc[0]*100), {"SPY":"S&P 500","QQQ":"Nasdaq 100","IWM":"Russell 2000"}, chart_dir/"market.png")
    ranking = ranking_chart(screen_df, chart_dir/"ranking.png")
    allocation = allocation_chart(after, chart_dir/"allocation.png")
    equity = equity_curve_chart(history, chart_dir/"equity.png")
    company = {r.ticker: stock_price_chart(closes[r.ticker], r.ticker, chart_dir/f"{r.ticker}-price.png").as_uri() for r in research}
    scores = {r.ticker: scorecard_chart(r.score, r.ticker, chart_dir/f"{r.ticker}-scores.png").as_uri() for r in research}
    charts = {"market": market.as_uri() if market else None, "sectors": None, "ranking": ranking.as_uri() if ranking else None, "allocation": allocation.as_uri() if allocation else None, "equity": equity.as_uri() if equity else None, "companies": company, "scores": scores}
    sample_trade = Trade(ticker="ACME", side="BUY", shares=7000/float(closes.ACME.iloc[-1]), price=float(closes.ACME.iloc[-1]), notional=7000.0)
    return build_report(d, settings, screen, research, decision, before, after, [sample_trade], charts, history)
