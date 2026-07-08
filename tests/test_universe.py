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
    # One primary reason per bond; the parts partition the 732 exactly. The old blanket
    # structured/floating bucket is split by coupon class (Mario 2026-07-08).
    _, _, funnel, _ = built
    total = int(funnel["TOTAL_unique_corporates"])
    assert total == 732
    parts = sum(int(funnel[k]) for k in (
        "canonical", "terms-unavailable", "defaulted", "no-rating",
        "excluded-structured", "floating", "special-fixed", "callable", "matured"))
    assert parts == total


def test_canonical_count_at_locked_date(built):
    # Priceable universe at 2009-06-10 (regression guard). Still 522 after Coupon_Formula2 routing
    # (Mario 2026-07-08), but now a clean coupon_class==F set: the coupon_type-mislabelled amortizing
    # bond dropped to excluded-structured and a formula-Fixed hybrid took its slot (net 0). 46 of the
    # 522 remain make-whole callables priced as vanilla.
    canonical, _, funnel, _ = built
    assert len(canonical) == 522
    assert int(funnel["canonical"]) == 522


def test_make_whole_routed_to_vanilla(built):
    # make-whole calls (call date ~ maturity, gap <= 7d) have ~zero option value -> priced as vanilla
    # (enter canonical, flagged is_make_whole); only genuine-gap callables remain excluded as `callable`.
    canonical, _, funnel, extras = built
    assert extras["make_whole_as_vanilla"] == 46
    # 6 genuine callables (was 5): a formula-Fixed bond that coupon_type had mislabelled non-fixed is
    # now correctly a fixed callable -> v2 lattice (Mario 2026-07-08 Coupon_Formula2 routing).
    assert int(funnel["callable"]) == 6
    assert "is_make_whole" in canonical.columns
    assert int(canonical["is_make_whole"].sum()) == 46


def test_golden_marks_not_in_canonical(built):
    # Custodian BT/BU/DI must never leak into the pricing inputs (input / truth separation).
    canonical, _, _, _ = built
    for col in ("gold_price", "gold_mkt_value", "gold_ytm"):
        assert col not in canonical.columns


def test_coupon_class_pivot_matches_mario(built):
    # Coupon_Formula2 (col M) classified over the raw 676 tab rows -> reconciles EXACTLY to Mario's
    # 2026-07-08 pivot. Locks the classifier; date-independent (no rating/maturity filter).
    _, _, _, extras = built
    assert extras["coupon_class_pivot"] == {
        "F": 617, "floating": 27, "fixed-to-reset": 6, "stepped": 2, "step-up": 1,
        "zero": 1, "defaulted": 1, "pass-through": 16, "amortizing": 1, "na": 4,
    }
    piv = extras["coupon_class_pivot"]
    assert piv["floating"] == 27                                  # Ref-Rate + EURIBOR + GBP-LIBOR + Fixed->Floating
    assert piv["pass-through"] + piv["amortizing"] + piv["na"] == 21   # Mario-excluded group


def test_canonical_is_all_vanilla_fixed(built):
    # After Coupon_Formula2 routing every canonical bond is plain-fixed (class F) and routes to the
    # vanilla engine — no coupon_type-mislabelled amortizing/structured leaks in (that bug is fixed).
    canonical, _, _, _ = built
    assert set(canonical["coupon_class"].unique()) == {"F"}
    assert set(canonical["route"].unique()) == {"vanilla"}


def test_funnel_new_buckets_split_structured_floating(built):
    # The old blanket structured/floating (51) now splits by coupon class. These reasons all sit above
    # `matured` in priority, so the counts are date-independent (regression guard).
    _, _, funnel, _ = built
    assert int(funnel["excluded-structured"]) == 15   # pass-through / amortizing / na / unknown
    assert int(funnel["floating"]) == 32              # floating + fixed-to-reset  -> Step 4 engine
    assert int(funnel["special-fixed"]) == 3          # stepped / step-up / zero / defaulted-coupon -> Step 3
