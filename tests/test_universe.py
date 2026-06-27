"""Golden funnel test for the corporate-bond universe pipeline (dataio/universe.py).

Locks the documented date-independent counts (PROJECT_STATUS §3.2) and the canonical
count at the locked 2009-06-10 valuation date. SKIPS (not fails) when the URS workbook
(git-ignored) is absent — point at it via ``FIP_URS_XLSX`` or drop it under ``data/``.
"""
import os
import pathlib

import pytest

from dataio.universe import build_universe_from_path

_ROOT = pathlib.Path(__file__).resolve().parents[1]
VAL_DATE = "2009-06-10"   # locked valuation/curve date; drives Layer B (matured)
_DEFAULT = "data/URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"


def _find_urs():
    p = os.environ.get("FIP_URS_XLSX")
    if p and pathlib.Path(p).exists():
        return pathlib.Path(p)
    c = _ROOT / _DEFAULT
    return c if c.exists() else None


URS = _find_urs()
pytestmark = pytest.mark.skipif(
    URS is None, reason="URS workbook not found; set FIP_URS_XLSX (git-ignored data)."
)


@pytest.fixture(scope="module")
def built():
    return build_universe_from_path(str(URS), VAL_DATE)


def test_join_counts(built):
    # Asset-ID join: 732 master-unique corporates vs 616 tab-unique codes.
    _, _, _, extras = built
    assert extras["matched"] == 597
    assert extras["master_only"] == 135
    assert extras["tab_only_count"] == 19


def test_rating_counts(built):
    # Notch-map over the 732 (S&P primary, Moody fallback, default precedence).
    _, _, _, extras = built
    assert extras["rating_covered"] == 712
    assert extras["rating_defaulted"] == 4
    assert extras["rating_no_rating"] == 16


def test_layer_a_raw_counts(built):
    # Raw (pre-priority) security-type classification within the 597 matched.
    _, _, _, extras = built
    assert extras["raw_non_fixed_in_matched"] == 54
    assert extras["raw_callable_in_matched"] == 73


def test_funnel_is_mece(built):
    # One primary reason per bond; the parts partition the 732 exactly.
    _, _, funnel, _ = built
    total = int(funnel["TOTAL_unique_corporates"])
    assert total == 732
    parts = sum(int(funnel[k]) for k in (
        "canonical", "terms-unavailable", "defaulted", "no-rating",
        "structured/floating", "callable", "matured"))
    assert parts == total


def test_canonical_count_at_locked_date(built):
    # Priceable universe at 2009-06-10 (regression guard; well under the 641 loose estimate).
    canonical, _, funnel, _ = built
    assert len(canonical) == 476
    assert int(funnel["canonical"]) == 476


def test_golden_marks_not_in_canonical(built):
    # Custodian BT/BU/DI must never leak into the pricing inputs (input / truth separation).
    canonical, _, _, _ = built
    for col in ("gold_price", "gold_mkt_value", "gold_ytm"):
        assert col not in canonical.columns
