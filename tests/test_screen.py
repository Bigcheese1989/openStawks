import numpy as np
import pandas as pd
from stock_analyst.market import MarketBundle, compute_screen


def test_screen_ranks_stronger_momentum_higher():
    idx = pd.bdate_range("2025-01-01", periods=260)
    a = np.linspace(100, 160, 260)
    b = np.linspace(100, 110, 260)
    closes = pd.DataFrame({"AAA": a, "BBB": b}, index=idx)
    volumes = pd.DataFrame({"AAA": 1_000_000, "BBB": 1_000_000}, index=idx)
    settings = {"screen": {"minimum_history_days":200,"minimum_price":5,"minimum_avg_dollar_volume":1,
        "weights":{"momentum_1m":.1,"momentum_3m":.2,"momentum_6m":.25,"momentum_12m":.2,"trend":.15,"liquidity":.05,"low_volatility":.05}}}
    out = compute_screen(MarketBundle(closes, volumes), {"AAA":{"name":"A","sector":"Tech"},"BBB":{"name":"B","sector":"Tech"}}, settings)
    assert out.iloc[0].ticker == "AAA"
