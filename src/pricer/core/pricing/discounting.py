"""Discount factors and present value (template: ``core/pricing/discounting.py``).

Default convention: **continuous compounding** on the bootstrapped zero curve —
``DF(t) = exp(-t * (z_cont + spread))`` — which reprices the curve's own par bonds to
exactly 100. The flat ``spread`` term is how a credit spread / OAS enters every
discount factor.

Legacy reconciliation (VERIFIED 2026-06-29): the legacy ``BondPrice`` stores a
SEMIANNUAL zero but discounts it with the CONTINUOUS formula ``exp(-t * z_semi)``
(Bootstrapping.bas l.449) — a convention mismatch that systematically UNDER-prices
(10y par bond -> 99.67, node DF -0.43% @10y, clean ~-0.2% @8y). The two ``vba_*``
functions below reproduce that legacy rate EXACTLY (0.5y-grid interpolation, clamped
at 25y) so the corrected engine can still replicate legacy output bit-for-bit when
asked (``vba_compat`` mode) — reconciliation only, never the default.
"""
from __future__ import annotations

import math

_VBA_MAX_TENOR = 25.0  # the legacy Zerout grid spans only 0.5..25y


def discount_factor(zero_rate: float, t: float, spread: float = 0.0) -> float:
    """Continuous-compounding discount factor.

    Inputs
    ------
    1. zero_rate : float — continuous zero rate at ``t``, DECIMAL (0.03 = 3%).
    2. t         : float — time in years (ACT/364 by repo convention).
    3. spread    : float — flat credit spread / OAS added to the rate, DECIMAL.

    Returns: float DF = exp(-t * (zero_rate + spread)).
    """
    return math.exp(-t * (zero_rate + spread))


def present_value(amount: float, df: float) -> float:
    """Present value of one cash flow.

    Inputs
    ------
    1. amount : float — the cash flow (same units as face).
    2. df     : float — its discount factor.

    Returns: float PV = amount * df.
    """
    return amount * df


def semiannual_from_continuous(z_cont: float) -> float:
    """Continuous zero -> semiannual-compounded zero (legacy reconciliation only).

    Inputs
    ------
    1. z_cont : float — continuous zero rate, DECIMAL.

    Returns: float z_semi = 2 * (exp(z_cont / 2) - 1).
    """
    return 2.0 * (math.exp(z_cont / 2.0) - 1.0)


def vba_semiannual_rate(curve, t: float) -> float:
    """The legacy discount rate at ``t``: semiannual zero, linearly interpolated on
    the 0.5y grid (replicates BondPrice ``anterior``/``posterior``, lines 784-806);
    lookups clamp at 25y. Legacy reconciliation only.

    Inputs
    ------
    1. curve : ZeroCurve — serves continuous zeros via ``curve.zero_rate(t)``.
    2. t     : float — time in years.

    Returns: float — the semiannual-compounded rate the legacy engine would use.
    """
    tc = min(t, _VBA_MAX_TENOR)
    anterior = math.floor(tc / 0.5) * 0.5
    if anterior <= 0:
        anterior = 0.5
    posterior = anterior + 0.5
    z_ant = semiannual_from_continuous(float(curve.zero_rate(anterior)))
    z_post = semiannual_from_continuous(float(curve.zero_rate(posterior)))
    if t >= _VBA_MAX_TENOR:
        return z_ant
    return (z_ant - z_post) / 0.5 * (posterior - t) + z_post
