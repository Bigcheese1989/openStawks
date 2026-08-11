from pathlib import Path


def test_no_broker_sdk_or_credentials_in_runtime_code():
    root = Path(__file__).resolve().parents[1]
    code = "\n".join(p.read_text(errors="ignore").lower() for p in (root/"stock_analyst").glob("*.py"))
    forbidden = ["ib_insync", "interactivebrokers", "alpaca_trade_api", "place_order(", "submit_order("]
    assert not any(x in code for x in forbidden)
