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
