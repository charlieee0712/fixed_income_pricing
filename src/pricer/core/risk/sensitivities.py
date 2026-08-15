"""Price sensitivities: DV01, effective duration, convexity
(template: ``core/risk/sensitivities.py``).

All engine-agnostic: the three formula functions are pure arithmetic on three prices
(base, rates-up, rates-down), and :func:`parallel_bump_metrics` turns ANY pricing
function into the standard metric set by central finite differences. Because every
engine in this repo adds its spread flat to the discount rate, bumping the spread by
``delta`` is identical to a parallel shift of the whole zero curve — so these are
**effective** (curve-shift) sensitivities, the standard risk-system measure.

Convention: duration / convexity divide by the **DIRTY** (full) price — the actual PV
of the cash flows (clean = dirty - accrued and accrued is yield-independent, so dP/dy
is identical either way; only the divisor differs, and the full price is the correct
one; retained 2026-08-04 after testing both ways against custodian durations).
"""
from __future__ import annotations

ONE_BP = 1e-4


def dv01_from_prices(price_up: float, price_down: float, bump: float) -> float:
    """Price change for a +1 bp parallel shift.

    Inputs
    ------
    1. price_up   : float — price after rates shift UP by ``bump``.
    2. price_down : float — price after rates shift DOWN by ``bump``.
    3. bump       : float — the shift size in DECIMAL (1e-4 = 1 bp).

    Returns: float = (price_down - price_up) / (2 * bump) * 1e-4  (per 1 bp, per face).
    """
    return (price_down - price_up) / (2.0 * bump) * ONE_BP


def effective_duration_from_prices(price_up: float, price_down: float,
                                   price_base: float, bump: float) -> float:
    """Effective (curve-shift) duration in years.

    Inputs
    ------
    1. price_up   : float — price after rates shift UP by ``bump``.
    2. price_down : float — price after rates shift DOWN by ``bump``.
    3. price_base : float — unshifted DIRTY price (the divisor).
    4. bump       : float — the shift size in DECIMAL.

    Returns: float = (price_down - price_up) / (2 * bump * price_base).
    """
    return (price_down - price_up) / (2.0 * bump * price_base)


def convexity_from_prices(price_up: float, price_down: float,
                          price_base: float, bump: float) -> float:
    """Effective convexity in years^2.

    Inputs
    ------
    1. price_up   : float — price after rates shift UP by ``bump``.
    2. price_down : float — price after rates shift DOWN by ``bump``.
    3. price_base : float — unshifted DIRTY price (the divisor).
    4. bump       : float — the shift size in DECIMAL.

    Returns: float = (price_up + price_down - 2 * price_base) / (bump^2 * price_base).
    """
    return (price_up + price_down - 2.0 * price_base) / (bump * bump * price_base)


def parallel_bump_metrics(price_at_shift, bump: float = ONE_BP) -> dict:
    """Standard metric set for any engine, by central finite differences.

    Inputs
    ------
    1. price_at_shift : callable(shift: float) -> result with ``.dirty`` and ``.clean``
       — prices the instrument with the discount rates shifted in parallel by
       ``shift`` (0.0 = base). Each call must be independent (no state).
    2. bump           : float — the shift size in DECIMAL (default 1 bp). Results are
       normalised per-1bp / per-unit-yield, so they are bump-agnostic to leading order.

    Returns: dict ``{dirty, clean, dv01, eff_duration, convexity}``; the sensitivity
    entries are NaN when the base dirty price is 0 (matured / worthless).
    """
    base = price_at_shift(0.0)
    p0 = base.dirty
    p_up = price_at_shift(+bump).dirty       # rates up   -> price down
    p_dn = price_at_shift(-bump).dirty       # rates down -> price up

    if p0 == 0:
        return {"dirty": p0, "clean": base.clean, "dv01": float("nan"),
                "eff_duration": float("nan"), "convexity": float("nan")}

    return {
        "dirty": p0,
        "clean": base.clean,
        "dv01": dv01_from_prices(p_up, p_dn, bump),
        "eff_duration": effective_duration_from_prices(p_up, p_dn, p0, bump),
        "convexity": convexity_from_prices(p_up, p_dn, p0, bump),
    }
