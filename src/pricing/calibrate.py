"""Calibrate a per-bond implied OAS from the custodian's market price (the inverse of pricing).

Mario's 2026-06-30 call redefined the OAS's role: it is a **calibration factor**, not a pricing
input. Rather than looking up an index rating OAS and computing a price (v1), we take the
custodian's market price (``BT``) as given and solve for the single flat OAS that makes our model
reprice to it. The calibrated model — which by construction reproduces the market price exactly —
is then the basis for the risk metrics (duration / DV01 / convexity); see :mod:`pricing.risk`.

The implied OAS therefore absorbs *everything* between the model and the mark: genuine credit
spread, the ACT/364 + 182-day-schedule conventions, and the 70-day holdings/curve date gap. It is
a model-calibration spread, not a clean market OAS — but it is exactly what makes the risk
sensitivities self-consistent with the custodian valuation.

For an option-free bond the model clean price is **strictly decreasing** in the OAS (every
discount factor is), so the root is unique and bracketing (Brent) is robust.
"""
from __future__ import annotations

import pandas as pd
from scipy.optimize import brentq

from pricing.bond_price import price_bond


def implied_oas(target_clean, valuation_date, maturity, coupon_rate, curve, *,
                face: float = 100.0, freq: int = 2, vba_compat: bool = False,
                lo: float = -0.20, hi: float = 2.0, xtol: float = 1e-10,
                max_expand: int = 40) -> float:
    """Solve for the flat continuous OAS (decimal) s.t. model CLEAN price == ``target_clean``.

    ``target_clean`` is per ``face`` (so the custodian ``BT`` per-100 with ``face=100``). The
    initial bracket ``[lo, hi]`` covers a wide premium-to-distress range and is auto-widened if
    the target falls outside it. Returns the OAS in decimal (e.g. 0.0453 = 453 bp).

    Raises ``ValueError`` if the target cannot be bracketed (should not happen for a price in the
    open interval between the deep-discount floor and the very-negative-OAS ceiling).
    """
    def f(oas: float) -> float:
        return price_bond(valuation_date, maturity, coupon_rate, curve, oas=oas,
                          face=face, vba_compat=vba_compat, freq=freq).clean - target_clean

    flo, fhi = f(lo), f(hi)
    n = 0
    # price is decreasing in OAS: f(lo) should be > 0 (high price), f(hi) < 0 (low price).
    while flo < 0 and n < max_expand:          # target above even the lo-OAS price -> lower OAS
        lo -= 0.20
        flo = f(lo)
        n += 1
    while fhi > 0 and n < max_expand:          # target below the hi-OAS price -> raise OAS
        hi += 1.0
        fhi = f(hi)
        n += 1
    if flo * fhi > 0:
        raise ValueError(
            f"cannot bracket implied OAS for target_clean={target_clean}: "
            f"f({lo:.3f})={flo:.4f}, f({hi:.3f})={fhi:.4f}"
        )
    return brentq(f, lo, hi, xtol=xtol)


def near_maturity(valuation_date, maturity, min_years: float = 1.0) -> bool:
    """True if the bond matures within ``min_years`` of the valuation date.

    Implied OAS from a market price is **unreliable** for near-maturity bonds: a tiny price gap
    (here largely the 70-day holdings/curve date mismatch) divided by a near-zero remaining horizon
    annualises to a huge — even negative — spread. Flag these and exclude them from spread
    statistics (do NOT delete). The real fix is a curve dated at the holdings date (the open
    3-31-vs-6-10 calibration-date question), not anything here.
    """
    days = (pd.Timestamp(maturity) - pd.Timestamp(valuation_date)).days
    return days < min_years * 365.25
