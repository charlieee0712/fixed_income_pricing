"""Yield-curve operations (template: ``core/market/curves.py``).

MIGRATION POINTER: the validated curve stack still lives in ``curves/`` —
``curves.bootstrap`` (par -> zero bootstrap, golden-tested against the legacy sheets)
and ``curves.zero_curve.ZeroCurve`` (linear-interp continuous zeros + per-currency
routing). They are re-exported here so template-layout code imports from ONE place;
the modules themselves move here in a later migration step (their golden tests come
with them — do not fork the implementations).
"""
from __future__ import annotations

import math

import pandas as pd

from curves.zero_curve import CURVE_FILE, ZeroCurve  # noqa: F401  (re-export)


def flat_zero_curve(rate: float, max_tenor: float = 60.0,
                    freq: str = "Semiannual") -> ZeroCurve:
    """Build a flat zero curve — input Type 1 ("Yield" as a single number) of the
    corporate ``bonds_input`` catalogue; also the workhorse of invariance tests.

    Inputs
    ------
    1. rate      : float — the flat continuous zero rate, DECIMAL (0.04 = 4%).
    2. max_tenor : float — last grid node in years (default 60; interpolation is
       flat everywhere, extrapolation clamps).
    3. freq      : str — which bootstrap variant the grid mimics (default Semiannual).

    Returns: :class:`ZeroCurve` serving ``rate`` at every tenor.
    """
    grid = pd.DataFrame({
        "Maturity": [0.01, max_tenor],
        f"{freq}_Rate": [rate * 100.0, rate * 100.0],
        f"{freq}_DF": [math.exp(-rate * 0.01), math.exp(-rate * max_tenor)],
    })
    return ZeroCurve(grid, freq=freq)
