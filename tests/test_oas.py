"""Golden test for the OAS-curve loader (src/credit/oas.py).

Locks the 2009-06-10 row of Pricing File.xlsm / 'OAS Credit Curves' (the project's authoritative
historical OAS source). SKIPS when the workbook is absent (git-ignored) — point at it via
FIP_PRICING_XLSM or drop it under data/.
"""
import os
import pathlib

import pytest

from credit.oas import BUCKETS, load_oas_history, oas_on

_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _find():
    p = os.environ.get("FIP_PRICING_XLSM")
    if p and pathlib.Path(p).exists():
        return pathlib.Path(p)
    c = _ROOT / "data" / "Pricing File.xlsm"
    return c if c.exists() else None


XLSM = _find()
pytestmark = pytest.mark.skipif(
    XLSM is None, reason="Pricing File.xlsm not found; set FIP_PRICING_XLSM (git-ignored data)."
)

# exact 2009-06-10 OAS (decimal) from the OAS Credit Curves sheet
EXPECTED = {"AAA": 0.0148, "AA": 0.0227, "A": 0.0302, "BBB": 0.0453,
            "BB": 0.0741, "B": 0.0945, "CCC": 0.1704}


def test_oas_2009_06_10_exact():
    oas = oas_on(str(XLSM), "2009-06-10")
    assert set(oas) == set(BUCKETS)
    for b, v in EXPECTED.items():
        assert abs(oas[b] - v) < 1e-6, f"{b}: {oas[b]} != {v}"


def test_buckets_widen_with_credit_risk():
    # OAS must increase monotonically AAA < AA < ... < CCC
    vals = [oas_on(str(XLSM), "2009-06-10")[b] for b in BUCKETS]
    assert vals == sorted(vals), vals


def test_missing_date_raises():
    with pytest.raises(ValueError):
        oas_on(str(XLSM), "2009-06-13")  # a Saturday — absent from a daily business series


def test_history_coverage():
    h = load_oas_history(str(XLSM))
    assert len(h) > 7000
    assert str(h.index.min()) <= "1997-01-02"
    assert str(h.index.max()) >= "2025-11-07"
