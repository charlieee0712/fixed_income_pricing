"""Credit spreads / OAS calibration (template: ``core/market/spreads.py``).

The repo-wide definition (Mario 2026-06-30): the OAS is a per-bond **calibration
factor**, not a pricing input — take the custodian's market price as given and solve
for the single flat spread that makes the model reprice to it. The calibrated model
is then the basis for the risk metrics. :func:`solve_spread_to_price` is that inverse
for ANY engine whose price is strictly decreasing in the spread (every discount
factor is), so the root is unique and bracketing (Brent) is robust.
"""
from __future__ import annotations

import pandas as pd
from scipy.optimize import brentq


def solve_spread_to_price(price_at_spread, target_price: float,
                          lo: float = -0.20, hi: float = 2.0, xtol: float = 1e-10,
                          max_expand: int = 40, widen_lo: float = 0.20,
                          widen_hi: float = 1.0) -> float:
    """Solve for the flat spread s.t. ``price_at_spread(spread) == target_price``.

    Inputs
    ------
    1. price_at_spread : callable(spread: float) -> float — model price at a flat
       spread (DECIMAL). Must be strictly DECREASING in the spread.
    2. target_price    : float — the market price to calibrate to (same units).
    3. lo, hi          : float — initial spread bracket, DECIMAL (default -0.20..2.0
       covers premium-to-distressed); auto-widened when the target falls outside.
    4. xtol            : float — root tolerance passed to Brent.
    5. max_expand      : int — total bracket-widening budget (both directions).
    6. widen_lo/widen_hi : float — step sizes for widening down / up.

    Returns: float — the implied spread in DECIMAL (0.0453 = 453 bp).
    Raises ``ValueError`` if the target cannot be bracketed.
    """
    def f(spread: float) -> float:
        return price_at_spread(spread) - target_price

    flo, fhi = f(lo), f(hi)
    n = 0
    # price is decreasing in the spread: f(lo) should be > 0, f(hi) < 0.
    while flo < 0 and n < max_expand:          # target above even the lo-spread price
        lo -= widen_lo
        flo = f(lo)
        n += 1
    while fhi > 0 and n < max_expand:          # target below the hi-spread price
        hi += widen_hi
        fhi = f(hi)
        n += 1
    if flo * fhi > 0:
        raise ValueError(
            f"cannot bracket implied spread for target_price={target_price}: "
            f"f({lo:.3f})={flo:.4f}, f({hi:.3f})={fhi:.4f}"
        )
    return brentq(f, lo, hi, xtol=xtol)


def near_maturity(valuation_date, maturity, min_years: float = 1.0) -> bool:
    """Flag bonds too close to maturity for a reliable implied spread.

    Inputs
    ------
    1. valuation_date : date-like — pricing "as of" date.
    2. maturity       : date-like — bond maturity.
    3. min_years      : float — the flagging horizon (default 1 year).

    Returns: bool — True if the bond matures within ``min_years``. A tiny price gap
    divided by a near-zero remaining horizon annualises to a huge — even negative —
    spread, so flag these and EXCLUDE them from spread statistics (never delete).
    """
    days = (pd.Timestamp(maturity) - pd.Timestamp(valuation_date)).days
    return days < min_years * 365.25
