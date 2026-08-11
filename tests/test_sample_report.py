import shutil
import pytest
from stock_analyst.sample import create_sample_report


def test_sample_pdf_renders(monkeypatch, tmp_path):
    if not any(shutil.which(x) for x in ("chromium","chromium-browser","google-chrome")):
        pytest.skip("Chromium unavailable")
    monkeypatch.setenv("STOCK_ANALYST_DATA_DIR", str(tmp_path))
    art = create_sample_report()
    assert art.pdf_path.exists()
    assert art.pdf_path.stat().st_size > 10000
