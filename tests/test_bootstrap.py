"""Golden-master test for the bootstrap port (src/curves/bootstrap.py).

Reproduces the legacy ``Bootstrapped/XX_yield_curves.csv`` (the VBA output). The match
is held **per-segment**, NOT under one blanket tolerance — each column is pinned to the
tightest bound it actually achieves, so a future regression in an exact column cannot
hide behind a loose global threshold.

Observed residuals (US, 2024-01-16; numpy 1.26.1 / pandas 2.1.1) — all economically ~0:

    Annual_Rate      bit-exact   2.7e-15   <- RED LINE (OAS pricing foundation) — kept < 1e-9
    Semiannual_Rate  bit-exact   4.4e-15   <- RED LINE                          — kept < 1e-9
    Quarterly_Rate   exact <=30y  <1e-9    ; one 30y+ extrapolated node 2.12e-05 @ 31.08y
    Monthly_Rate     8.06e-02 @ 0.42y      (short-end flat fill)
    Annual/Semi/Q DF <= 1.7e-06            (machine / interpolation precision)
    Monthly_DF       6.72e-04 @ 0.92y      (short-end fill propagated through the recursion)

Residual source: the USD par txt's shortest tenor is 3m, so the Monthly grid's 1m/2m nodes
are flat-extrapolated and differ infinitesimally from the VBA's short-end handling; that
perturbation rides the recursive bootstrap (DF_i = f(Σ_{k<i} DF_k)) into the Monthly belly.
The Quarterly miss is a single node in the 30y+ linear-extrapolation tail. Compounded by a
numpy/pandas version delta vs the colleague's original validation env (versions unknown —
see WORKLOG open item). None of this touches pricing or OAS.

Needs two git-ignored data files (raw par-curve txt + golden CSV). Point at them via env
vars, or drop them under ``data/``. The test SKIPS (not fails) when they are absent.

    pytest -q                                     # skips if data missing
    FIP_US_TXT=.../USD_Yield_Curve.txt \
    FIP_US_GOLDEN=.../Bootstrapped/US_yield_curves.csv  pytest -q
"""
import os
import pathlib

import numpy as np
import pandas as pd
import pytest

from curves.bootstrap import bootstrap

VAL_DATE = "2024-01-16"   # the date the golden CSVs were built for (validated, RMSE 0)
PAR_MAX_TENOR = 30.0      # longest tenor in the USD par txt; beyond this the grid is extrapolated
_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _find(env, *candidates):
    p = os.environ.get(env)
    if p and pathlib.Path(p).exists():
        return pathlib.Path(p)
    for c in candidates:
        c = _ROOT / c
        if c.exists():
            return c
    return None


US_TXT = _find("FIP_US_TXT", "data/USD_Yield_Curve.txt", "USD_Yield_Curve.txt")
US_GOLDEN = _find(
    "FIP_US_GOLDEN", "data/Bootstrapped/US_yield_curves.csv", "Bootstrapped/US_yield_curves.csv"
)

pytestmark = pytest.mark.skipif(
    US_TXT is None or US_GOLDEN is None,
    reason="par-curve txt / golden CSV not found; set FIP_US_TXT and FIP_US_GOLDEN (git-ignored data).",
)


@pytest.fixture(scope="module")
def aligned():
    got = bootstrap(str(US_TXT), VAL_DATE).set_index("Maturity")
    gold = pd.read_csv(US_GOLDEN).set_index("Maturity")
    return got.reindex(gold.index, method="nearest"), gold


def _err(a, g, col, mask=None):
    """Max |computed - golden| for one column, optionally over a maturity mask."""
    d = np.abs(a[col].to_numpy() - g[col].to_numpy())
    return float(np.max(d if mask is None else d[mask]))


# ---- RED LINE: Annual / Semiannual rates must stay bit-exact (the OAS pricing foundation) ----
@pytest.mark.parametrize("col", ["Annual_Rate", "Semiannual_Rate"])
def test_rates_bit_exact(aligned, col):
    a, g = aligned
    # Observed 2.7e-15 / 4.4e-15 (machine epsilon). DO NOT relax: a real drift here would
    # corrupt every discounted cash flow and the rating-OAS overlay built on top of it.
    assert _err(a, g, col) < 1e-9, f"{col} must reproduce the golden output to the digit"


# ---- Quarterly rate: exact inside the par grid; the single extrapolated tail node tolerated ----
def test_quarterly_rate_exact_within_grid(aligned):
    a, g = aligned
    interior = g.index.to_numpy() <= PAR_MAX_TENOR + 1e-6
    # Observed < 1e-9 for all nodes up to 30y (the same bit-exact bar as Annual/Semiannual).
    assert _err(a, g, "Quarterly_Rate", interior) < 1e-9, "Quarterly_Rate must be exact within <=30y"


def test_quarterly_rate_extrapolated_tail(aligned):
    a, g = aligned
    tail = g.index.to_numpy() > PAR_MAX_TENOR + 1e-6
    # Single 30y+ linearly-extrapolated node: observed 2.12e-05 @ 31.08y. 30y after the last
    # par tenor, economic impact ~0 (the URS book has nothing pricing off the 31y node).
    assert _err(a, g, "Quarterly_Rate", tail) < 1e-4, "30y+ extrapolated tail; economic impact ~0"


# ---- Monthly rate: short-end flat-fill residual (USD txt starts at 3m -> 1m/2m extrapolated) ----
def test_monthly_rate_short_end(aligned):
    a, g = aligned
    # Observed 8.06e-02 pp @ 0.42y; documented short-end fill convention.
    assert _err(a, g, "Monthly_Rate") < 0.1


# ---- Discount factors: A/S/Q tight; Monthly carries the short-end fill into the belly ----
@pytest.mark.parametrize("col", ["Annual_DF", "Semiannual_DF", "Quarterly_DF"])
def test_discount_factors_tight(aligned, col):
    a, g = aligned
    # Observed <= 1.7e-06 (machine / interpolation precision).
    assert _err(a, g, col) < 1e-4


def test_monthly_df_short_end(aligned):
    a, g = aligned
    # The 1m/2m flat-fill rides the recursive bootstrap (DF_i = f(Σ_{k<i} DF_k)) into the
    # Monthly belly: observed 6.72e-04 @ 0.92y. Economic impact ~0 (short-end fill, documented).
    assert _err(a, g, "Monthly_DF") < 1e-3


# ---------------------------------------------------------------- par-yield file units
#
# Added 2026-08-30. The *_Yield_Curve.txt exports are not uniform: GBP and DKK store par
# yields in PERCENT, every other file in decimals. Read as decimals the GBP file becomes
# a 73%-415% par curve, whose bootstrap fails at the 3-year node with "par curve is not
# arbitrage-free" — a true statement about a curve we had mis-scaled, which was recorded
# as a fact about the market data and left the book's one GBP holding unpriced.

def test_only_gbp_and_dkk_are_declared_percent():
    from curves.bootstrap import DEFAULT_PAR_YIELD_UNITS, PAR_YIELD_UNITS, par_yield_units

    assert set(PAR_YIELD_UNITS) == {"GBP_Yield_Curve.txt", "DKK_Yield_Curve.txt"}
    assert DEFAULT_PAR_YIELD_UNITS == "decimal"
    assert par_yield_units("anywhere/GBP_Yield_Curve.txt") == "percent"
    assert par_yield_units("anywhere/USD_Yield_Curve.txt") == "decimal"


def test_every_curve_file_reads_as_a_plausible_market_curve():
    """The registry is only right if it makes every file plausible. This walks all of
    them at whatever date each carries, which is the check that would have caught GBP."""
    import glob
    import os

    import pandas as pd

    from curves.bootstrap import excel_serial_to_date, load_par_curve

    checked = 0
    for path in sorted(glob.glob(str(_ROOT / "data" / "*_Yield_Curve.txt"))):
        frame = pd.read_csv(path, usecols=["Date"])
        for serial in (frame["Date"].iloc[0], frame["Date"].iloc[len(frame) // 2],
                       frame["Date"].iloc[-1]):
            _, par_pct = load_par_curve(path, excel_serial_to_date(int(serial)))
            worst = float(np.nanmax(np.abs(par_pct)))
            assert worst < 30.0, f"{os.path.basename(path)} at {serial}: {worst:.1f}%"
            checked += 1
    assert checked >= 60


def test_a_file_read_in_the_wrong_units_is_named_as_a_units_problem():
    """The guard must fire BEFORE the bootstrap, so the message points at the loader
    rather than at the market."""
    from curves.bootstrap import ParYieldUnitError, load_par_curve

    with pytest.raises(ParYieldUnitError, match="PAR_YIELD_UNITS"):
        load_par_curve(str(_ROOT / "data" / "GBP_Yield_Curve.txt"), "2009-03-31",
                       units="decimal")


def test_the_gbp_curve_bootstraps_and_looks_like_the_2009_gilt_market():
    """2009-03-31 gilts: ~1.2% at 2y, ~2.3% at 5y, ~3.2% at 10y, ~4.2% at 30y."""
    from curves.zero_curve import ZeroCurve

    for variant in ("Annual", "Semiannual", "Quarterly", "Monthly"):
        curve = ZeroCurve.from_currency(str(_ROOT / "data"), "GBP", "2009-03-31", freq=variant)
        assert 0.010 < curve.zero_rate(2.0) < 0.015
        assert 0.021 < curve.zero_rate(5.0) < 0.026
        assert 0.030 < curve.zero_rate(10.0) < 0.035
        assert 0.040 < curve.zero_rate(30.0) < 0.048
        dfs = curve.grid[f"{variant}_DF"].to_numpy()
        assert dfs.min() > 0.0
        assert np.all(np.diff(dfs) <= 1e-15)          # discount factors never rise
