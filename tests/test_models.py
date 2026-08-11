from stock_analyst.models import ScoreCard

def test_composite_score_range():
    s = ScoreCard(fundamentals=80, valuation=70, momentum=60, catalysts=90, risk=75)
    assert 0 <= s.composite <= 100
    assert s.composite == 76.25 or s.composite == 76.2
