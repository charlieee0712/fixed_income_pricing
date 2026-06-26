"""Golden-master test for the bootstrap port (src/curves/bootstrap.py).

Reproduces the legacy ``Bootstrapped/XX_yield_curves.csv`` to the digit. This is the
pytest form of the module's ``_self_test``: Annual/Semiannual/Quarterly rates exact,
Monthly rate < 0.1 pp (short-end fill residual).

Needs two git-ignored data files (raw par-curve txt + golden CSV). Point at them via
env vars, or drop them under ``data/``. The test SKIPS (not fails) when they are absent.

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

VAL_DATE = "2024-01-16"  # the date the golden CSVs were built for (validated, RMSE 0)
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


def _max_err(a, g, col):
    return float(np.max(np.abs(a[col].to_numpy() - g[col].to_numpy())))


@pytest.mark.parametrize("col", ["Annual_Rate", "Semiannual_Rate", "Quarterly_Rate"])
def test_rates_exact(aligned, col):
    a, g = aligned
    assert _max_err(a, g, col) < 1e-9, f"{col} should reproduce the golden output exactly"


def test_monthly_rate_short_end(aligned):
    a, g = aligned
    # residual lives only at the 1m/2m nodes (USD txt starts at 3m -> flat-extrapolated)
    assert _max_err(a, g, "Monthly_Rate") < 0.1


@pytest.mark.parametrize("col", ["Annual_DF", "Semiannual_DF", "Quarterly_DF", "Monthly_DF"])
def test_discount_factors_close(aligned, col):
    a, g = aligned
    assert _max_err(a, g, col) < 1e-4
