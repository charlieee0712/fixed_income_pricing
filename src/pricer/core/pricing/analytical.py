"""Analytical (discounted-cash-flow) engine for fixed-rate bonds
(template: ``core/pricing/analytical.py``).

Port of the legacy ``BondPrice`` (Pricing File.xlsm / Bootstrapping.bas, curva = 1),
recomposed as an orchestration of simple single-purpose functions:

    coupon_dates (core.utils.dates)      -> the 364/182-day schedule walk
    bond_cashflows (core.pricing.cashflows) -> (date, amount) table
    discount_factor / present_value (core.pricing.discounting) -> PV per flow
    accrued_interest (core.pricing.cashflows) -> the ONE accrued formula
    clean = dirty - accrued

Conventions (copied from the VBA, kept as-is): ACT/364 day count, backward 182-day
coupon schedule, accrued = (rate/freq*face) * days-since-prior-coupon / step_days.
Discounting is *corrected* by default (``exp(-t * (z_cont + oas))`` — reprices par to
100); ``vba_compat=True`` reproduces the legacy semiannual-zero-in-continuous-formula
bug EXACTLY (see ``core.pricing.discounting``) for reconciliation.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from pricer.core.pricing.cashflows import accrued_interest, bond_cashflows
from pricer.core.pricing.discounting import discount_factor, present_value, vba_semiannual_rate
from pricer.core.utils.dates import YEAR_DAYS, as_date, coupon_dates


@dataclass
class CashFlow:
    n: int
    date: dt.date
    days: int
    t: float
    zero_cont: float    # continuous zero (decimal), monthly-grid interpolation
    zero_semi: float    # legacy semiannual zero used in vba_compat (decimal), 0.5y-grid interp
    df: float           # discount factor actually applied (depends on vba_compat) incl. oas
    amount: float       # cash flow per 100 face
    pv: float           # amount * df


@dataclass
class PriceResult:
    clean: float                # dirty - accrued (the price convention of custodian marks)
    dirty: float                # full PV of the remaining cash flows
    accrued: float              # accrued interest per face (the ONE shared formula)
    accrued_days: int           # days since the prior grid coupon date
    last_coupon_date: dt.date   # the accrual anchor (grid date just before valuation)
    cashflows: list             # per-flow detail rows (CashFlow)
    vba_compat: bool            # True = legacy-bug discounting was used (reconciliation)


def price_fixed_rate_bond(valuation_date, maturity, coupon_rate, curve, oas: float = 0.0,
                          face: float = 100.0, vba_compat: bool = False, freq: int = 2,
                          coupon_schedule=None) -> PriceResult:
    """Price a fixed-rate bullet bond by discounting each cash flow (returns CLEAN
    price inside a full :class:`PriceResult`).

    Inputs
    ------
    1. valuation_date  : date-like — pricing "as of" date.
    2. maturity        : date-like — bond maturity.
    3. coupon_rate     : float — annual coupon in DECIMAL (0.065 = 6.5%); 0 = zero-coupon.
    4. curve           : ZeroCurve — the discount curve (serves continuous zeros).
    5. oas             : float — flat spread added to every discount rate, DECIMAL.
    6. face            : float — principal (default 100).
    7. vba_compat      : bool — True reproduces the legacy discounting bug bit-for-bit
       (reconciliation only; semiannual-frequency bonds only).
    8. freq            : int — coupon payments per year (1, 2, 4, 12).
    9. coupon_schedule : optional coupon time-table for stepped / step-up bonds
       (see ``core.pricing.cashflows.bond_cashflows``).

    Returns: :class:`PriceResult` — clean, dirty, accrued, per-cash-flow detail.
    """
    val = as_date(valuation_date)
    mat = as_date(maturity)
    if val > mat:                                       # legacy: past maturity -> 0
        return PriceResult(0.0, 0.0, 0.0, 0, mat, [], vba_compat)

    _dates, last_cpn_date, _step = coupon_dates(valuation_date, maturity, freq)
    flows = bond_cashflows(valuation_date, maturity, coupon_rate, freq=freq, face=face,
                           coupon_schedule=coupon_schedule)

    cfs, dirty = [], 0.0
    for d, amount in reversed(flows):                   # maturity first, as the VBA walks it
        days = (d - val).days
        t = days / YEAR_DAYS
        z_cont = float(curve.zero_rate(t))              # continuous, monthly-grid interp
        z_semi = vba_semiannual_rate(curve, t)          # legacy semiannual, 0.5y-grid interp
        df = discount_factor(z_semi if vba_compat else z_cont, t, oas)
        pv = present_value(amount, df)
        dirty += pv
        cfs.append(CashFlow(0, d, days, t, z_cont, z_semi, df, amount, pv))

    accrued_days = (val - last_cpn_date).days
    accrued = accrued_interest(valuation_date, maturity, coupon_rate, freq=freq, face=face,
                               coupon_schedule=coupon_schedule)   # the ONE AI formula (shared)
    clean = dirty - accrued
    cfs.reverse()
    for i, cf in enumerate(cfs, start=1):
        cf.n = i
    return PriceResult(clean, dirty, accrued, accrued_days, last_cpn_date, cfs, vba_compat)
