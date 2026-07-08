"""Numerical risk metrics for a calibrated bond: effective duration, DV01, convexity.

Computed by perturbing the discount rate by +/- a small bump and repricing (central finite
differences). Because :func:`pricing.bond_price.price_bond` adds the OAS *flat* to the continuous
zero rate, bumping the OAS by ``delta`` is identical to a parallel shift of the whole zero curve
by ``delta`` — so these are **effective** (curve-shift) sensitivities, the standard risk-system
measure. No curve object is mutated; only the OAS argument moves.

Conventions:
  * duration / convexity use the **DIRTY** (full) price as the base — the actual PV of the cash
    flows. (Clean = dirty - accrued, and accrued is yield-independent, so dP/dy is the same either
    way; only the divisor differs, and the full price is the correct one.)
  * ``dv01`` is the price change (per ``face``) for a **+1 bp** parallel shift. Multiply by
    ``par / face`` for a position's dollar DV01.
"""
from __future__ import annotations

from pricing.bond_price import price_bond

ONE_BP = 1e-4


def risk_metrics(valuation_date, maturity, coupon_rate, curve, oas, *,
                 face: float = 100.0, freq: int = 2, vba_compat: bool = False,
                 coupon_schedule=None, bump: float = ONE_BP) -> dict:
    """Return ``{dirty, clean, dv01, eff_duration, convexity}`` for the calibrated bond.

    ``oas`` should be the calibrated implied OAS (so ``dirty``/``clean`` reproduce the mark).
    ``bump`` is the parallel-shift size for the central difference (default 1 bp); the results are
    normalised to per-1bp (DV01) / per-unit-yield (duration, convexity) and so are bump-agnostic
    to leading order.
    """
    def priced(o: float):
        return price_bond(valuation_date, maturity, coupon_rate, curve, oas=o,
                          face=face, vba_compat=vba_compat, freq=freq,
                          coupon_schedule=coupon_schedule)

    base = priced(oas)
    p0 = base.dirty
    p_up = priced(oas + bump).dirty        # rates up   -> price down
    p_dn = priced(oas - bump).dirty        # rates down -> price up

    if p0 == 0:
        return {"dirty": p0, "clean": base.clean, "dv01": float("nan"),
                "eff_duration": float("nan"), "convexity": float("nan")}

    dv01 = (p_dn - p_up) / (2.0 * bump) * ONE_BP          # price drop per +1 bp
    eff_duration = (p_dn - p_up) / (2.0 * bump * p0)      # years
    convexity = (p_up + p_dn - 2.0 * p0) / (bump * bump * p0)  # years^2
    return {
        "dirty": p0,
        "clean": base.clean,
        "dv01": dv01,
        "eff_duration": eff_duration,
        "convexity": convexity,
    }
