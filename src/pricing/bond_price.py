"""Python port of ``BondPrice`` from Pricing File.xlsm / Bootstrapping.bas (``curva = 1``
spot pricing), producing the CLEAN price of a plain-fixed semiannual bond.

This is a **dedicated, corrected pricing module**, not a bit-for-bit copy of the legacy sheet.
The cash-flow conventions are copied verbatim from the VBA (that is where a port silently
diverges); the discounting is *corrected* (see the z_semi note), with a ``vba_compat`` switch
to reproduce the legacy output for reconciliation.

Conventions copied from the VBA (Bootstrapping.bas, lines 766-818) — kept as-is:
  * day count        : **ACT/364** — t = (cf_date - valuation).days / 364.            [diasmat/364]
                       VBA convention; differs from the custodian's ACT/ACT or 30/360 — a known
                       source of gap vs BT/BU/DI, NOT a bug.
  * coupon schedule  : **backward from maturity in 182-day steps**.                   [l.782-815]
                       VBA convention; the dates drift from the true calendar coupon dates
                       (182d != 6 calendar months) — another known BT-gap source, NOT a bug.
  * coupon / face    : semiannual coupon = rate/2 * 100; principal 100 at maturity.   [l.808-812]
  * accrued interest : (rate/2 * 100) * (days since the prior coupon date) / 182.     [l.817]
  * clean = dirty - accrued.                                                          [l.817-818]

Discounting — **CORRECTED** (the one place we deviate, on purpose):
  The VBA discounts each cash flow as ``cf * exp(-t * z_semi)`` where z_semi is the SEMIANNUAL-
  compounded zero. That mixes a semiannual rate into a continuous-compounding formula: it does
  NOT recover the bootstrap's own discount factor (``exp(-t*z_semi) < DF`` for z>0), so it
  under-prices by ~0.08% at 5y growing to ~0.3% at 10y. The VBA computes the correct DF
  (``DisCF``) internally and then discards it — a methodology bug, not a convention.
  CEO asked for a correct, extensible module, so by default this module discounts with the
  bootstrapped factor ``DF = exp(-t * z_cont)`` (continuous zero), i.e. ``cf * DF * exp(-t*oas)``.
  Pass ``vba_compat=True`` to reproduce the legacy ``exp(-t * z_semi)`` exactly (0.5y-grid
  linear interpolation of z_semi, as the VBA does) — used only to explain the gap in reconciliation.

OAS (the rating spread) is added flat to the discount rate; ``oas = 0`` is risk-free.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import pandas as pd

YEAR_DAYS = 364.0     # VBA: a year is 364 days (diasmat / 364)
HALF_DAYS = 182       # VBA: coupon period is 182 days (fechamobil - 182)
_VBA_MAX_TENOR = 25.0  # the VBA's Zerout spans only 0.5..25y


def _cont_to_semi(z_cont: float) -> float:
    """Continuous zero -> semiannual-compounded zero: z_semi = 2*(exp(z_cont/2) - 1)."""
    return 2.0 * (math.exp(z_cont / 2.0) - 1.0)


def _vba_semi_rate(curve, t: float) -> float:
    """The VBA's discount rate at ``t``: semiannual zero, linearly interpolated on the 0.5y grid
    (replicates BondPrice anterior/posterior, lines 784-806). Rate lookups are clamped at 25y."""
    tc = min(t, _VBA_MAX_TENOR)
    anterior = math.floor(tc / 0.5) * 0.5
    if anterior <= 0:
        anterior = 0.5
    posterior = anterior + 0.5
    z_ant = _cont_to_semi(float(curve.zero_rate(anterior)))
    z_post = _cont_to_semi(float(curve.zero_rate(posterior)))
    if t >= _VBA_MAX_TENOR:
        return z_ant
    return (z_ant - z_post) / 0.5 * (posterior - t) + z_post


@dataclass
class CashFlow:
    n: int
    date: dt.date
    days: int
    t: float
    zero_cont: float    # continuous zero (decimal), monthly-grid interpolation
    zero_semi: float    # VBA's semiannual zero used in vba_compat (decimal), 0.5y-grid interp
    df: float           # discount factor actually applied (depends on vba_compat) incl. oas
    amount: float       # cash flow per 100 face
    pv: float           # amount * df


@dataclass
class PriceResult:
    clean: float
    dirty: float
    accrued: float
    accrued_days: int
    last_coupon_date: dt.date
    cashflows: list
    vba_compat: bool


def _as_date(x) -> dt.date:
    return pd.Timestamp(x).date()


def price_bond(valuation_date, maturity, coupon_rate, curve, oas: float = 0.0,
               face: float = 100.0, vba_compat: bool = False, freq: int = 2):
    """Port of BondPrice (curva = 1). Returns a :class:`PriceResult` with the CLEAN price.

    By default discounts with the bootstrapped factor exp(-t*(z_cont+oas)); ``vba_compat=True``
    reproduces the legacy exp(-t*(z_semi+oas)). Cash-flow schedule, day count and accrual are
    identical in both modes (the VBA conventions).

    ``freq`` is the coupon frequency. The VBA is hard-wired semiannual (freq=2 -> 182-day steps);
    other frequencies are the natural generalisation (step = round(364/freq) days, coupon =
    rate/freq*face) and are only meaningful in the corrected (default) mode — ``vba_compat`` is
    semiannual-only.
    """
    val = _as_date(valuation_date)
    mat = _as_date(maturity)
    if val > mat:                                       # VBA: Tiempo > BondMat And curva = 1 -> 0
        return PriceResult(0.0, 0.0, 0.0, 0, mat, [], vba_compat)

    step_days = max(1, round(YEAR_DAYS / freq))         # 182 for semiannual (the VBA), 364 for annual
    period_cpn = coupon_rate / freq * face
    cfs, dirty, d = [], 0.0, mat
    while d >= val:
        days = (d - val).days
        t = days / YEAR_DAYS
        z_cont = float(curve.zero_rate(t))              # continuous, monthly-grid interp
        z_semi = _vba_semi_rate(curve, t)               # VBA semiannual, 0.5y-grid interp
        rate = (z_semi if vba_compat else z_cont) + oas
        df = math.exp(-t * rate)
        amount = period_cpn + (face if d == mat else 0.0)
        pv = amount * df
        dirty += pv
        cfs.append(CashFlow(0, d, days, t, z_cont, z_semi, df, amount, pv))
        d = d - dt.timedelta(days=step_days)

    accrued_days = (val - d).days                       # d = coupon date just before valuation
    accrued = period_cpn * accrued_days / step_days
    clean = dirty - accrued
    cfs.reverse()
    for i, cf in enumerate(cfs, start=1):
        cf.n = i
    return PriceResult(clean, dirty, accrued, accrued_days, d, cfs, vba_compat)
