from datetime import date
from stock_analyst import database
from stock_analyst.models import CommitteeDecision, TargetPosition
from stock_analyst.portfolio import rebalance


def test_rebalance_respects_position_and_cash_caps(tmp_path):
    db = tmp_path / "x.sqlite"
    database.initialize(db, 100000)
    decision = CommitteeDecision(
        market_stance="neutral", executive_summary="x", key_market_risks=[], top_opportunity="AAA",
        targets=[TargetPosition(ticker="AAA", target_weight=.50, action="BUY", rationale="test")], watchlist=[])
    cfg={"maximum_position_weight":.10,"minimum_cash_weight":.10,"maximum_daily_turnover":.15,"minimum_trade_weight":.001}
    with database.connect(db) as conn:
        trades, state = rebalance(conn, date(2026,1,2), decision, {"AAA":100}, cfg)
    assert state["positions"][0]["weight"] <= .10001
    assert state["cash"] >= 89999
