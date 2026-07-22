"""Inflation-linked government bond (ILB / TIPS) pricing + calibration — phase 2, v1 path.

We have NO real-yield curves, so the v1 method (inventory 2026-07-20, built 2026-07-22) prices an
ILB off the **nominal** own-currency :class:`curves.zero_curve.ZeroCurve` with an explicit
inflation assumption for the index path:

    ratio(t) = index_ratio * (1 + inflation)**t          # index_ratio = the bond's ratio at VAL
    coupon cash flow at t = real_coupon/freq * face * ratio(t)
    redemption            = face * ratio(T)
    PV: every flow discounted exp(-t * (z_nominal(t) + spread))     [+ accrued -> clean]

``index_ratio`` (the accrued-inflation starting point) is recovered per bond from the custodian
file itself: master BG "Income rate" = real coupon x current index ratio, so ratio = BG / the
description real coupon (validated pattern 1.008-1.31 by vintage; ``dataio.phase2``). The
custodian ``BT`` is the inflation-ADJUSTED clean price (BT == BU/par*100 exactly), so the model
clean — which carries the ratio — calibrates to BT directly.

**Read this before calling the calibrated spread a bug** (the sign is the whole point):
``implied_spread_vs_nominal`` at the default ``inflation = 0`` is EXPECTED to be **negative**,
roughly **minus the market breakeven inflation**. Mechanism: nominal yield ~ real yield +
expected inflation; with a zero-inflation cash-flow projection matched to the market price, the
spread must absorb exactly the missing inflation accretion, i.e. ``spread ~ -breakeven``
(continuous-compounding identity: pricing with inflation ``pi`` at spread ``s`` equals pricing
with inflation 0 at spread ``s - ln(1+pi)`` — exact under our exp discounting, and a unit test).
At 2009-03-31 (deflation-scare tail: 10y breakeven ~ 1.2-1.5%, short breakevens near/below 0) the
expected pattern is ~ -1.2% mid-curve, closer to 0 (or positive) at the short end. A calibrated
value landing there is *evidence the engine is right*, and ``-spread`` is a free per-bond extract
of the market's inflation expectation. This spread is therefore reported in its OWN column
(``implied_spread_vs_nominal``), never mixed with credit OAS.

v1 simplifications (documented, deliberate):
  * **TIPS deflation floor ignored** — the par floor on redemption (max(ratio_T, 1)) is an
    inflation-vol option; worthless for the seasoned high-ratio holdings, but REAL value in 2009
    for near-par-ratio vintages (the 1.008 / 1.02 bonds) — needs an inflation-vol model, v2 item.
  * Static inflation path -> cash flows do not respond to the curve, so effective duration (a
    ``spread`` bump == parallel nominal shift) is the full PV-weighted duration = a REAL-rate
    duration. Nominal-rate/inflation co-movement (which shortens a TIPS' *nominal* duration) is
    not modelled — v2 with the vol model.
  * Indexation lags / seasonality are not modelled; the ratio path is geometric from VAL.

Conventions mirror :mod:`pricing.bond_price` exactly (ACT/364, backward 182-day schedule, accrued
= period coupon x elapsed/step, clean = dirty - accrued), so ``inflation=0, index_ratio=1``
reproduces ``price_bond`` to machine precision and ``index_ratio=r`` scales it by exactly ``r``
(both are unit tests). JGBi / KTBi route via their own-currency nominal curves.
"""
from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass

import pandas as pd
from scipy.optimize import brentq

YEAR_DAYS = 364.0


def _as_date(x) -> dt.date:
    return pd.Timestamp(x).date()


@dataclass
class IlbResult:
    clean: float
    dirty: float
    accrued: float
    index_ratio: float           # ratio at the valuation date (scales the accrued)
    cashflows: list              # (date, t, ratio_t, amount, df, pv)


def price_ilb(valuation_date, maturity, real_coupon, curve, spread: float = 0.0, *,
              index_ratio: float = 1.0, inflation: float = 0.0,
              face: float = 100.0, freq: int = 2):
    """CLEAN/dirty price of an inflation-linked bond per ``face`` ORIGINAL (unindexed) face.

    ``real_coupon`` is the REAL coupon (decimal); every flow is scaled by
    ``index_ratio * (1+inflation)**t`` and the redemption by the ratio at maturity. ``spread``
    (decimal, may be negative) adds flat to the nominal zero — the calibration handle.
    """
    val, mat = _as_date(valuation_date), _as_date(maturity)
    if val > mat:
        return IlbResult(0.0, 0.0, 0.0, index_ratio, [])
    step_days = max(1, round(YEAR_DAYS / freq))
    per_cpn_real = real_coupon / freq * face
    cfs, dirty, d = [], 0.0, mat
    while d >= val:
        days = (d - val).days
        t = days / YEAR_DAYS
        ratio_t = index_ratio * (1.0 + inflation) ** t
        z = float(curve.zero_rate(t))
        df = math.exp(-t * (z + spread))
        amount = per_cpn_real * ratio_t + (face * ratio_t if d == mat else 0.0)
        dirty += amount * df
        cfs.append((d, t, ratio_t, amount, df, amount * df))
        d = d - dt.timedelta(days=step_days)
    accrued_days = (val - d).days
    accrued = per_cpn_real * index_ratio * accrued_days / step_days   # ratio at VAL (t=0)
    cfs.reverse()
    return IlbResult(dirty - accrued, dirty, accrued, index_ratio, cfs)


def implied_spread_ilb(target_clean, valuation_date, maturity, real_coupon, curve, *,
                       index_ratio: float = 1.0, inflation: float = 0.0,
                       face: float = 100.0, freq: int = 2,
                       lo: float = -0.20, hi: float = 2.0, xtol: float = 1e-10,
                       max_expand: int = 40) -> float:
    """Solve the flat spread vs the NOMINAL curve s.t. model clean == ``target_clean`` (BT).

    Price is strictly decreasing in the spread -> unique root, Brent with auto-widened bracket.
    NEGATIVE results are the norm at ``inflation=0`` (~ -breakeven; see the module docstring).
    """
    def f(s):
        return price_ilb(valuation_date, maturity, real_coupon, curve, s, index_ratio=index_ratio,
                         inflation=inflation, face=face, freq=freq).clean - target_clean

    flo, fhi, n = f(lo), f(hi), 0
    while flo < 0 and n < max_expand:
        lo -= 0.20; flo = f(lo); n += 1
    while fhi > 0 and n < max_expand:
        hi += 1.0; fhi = f(hi); n += 1
    if flo * fhi > 0:
        raise ValueError(f"cannot bracket ILB spread for target={target_clean}: "
                         f"f({lo:.3f})={flo:.4f}, f({hi:.3f})={fhi:.4f}")
    return brentq(f, lo, hi, xtol=xtol)


def ilb_risk_metrics(valuation_date, maturity, real_coupon, curve, spread, *,
                     index_ratio: float = 1.0, inflation: float = 0.0,
                     face: float = 100.0, freq: int = 2, bump: float = 1e-4) -> dict:
    """Effective duration / DV01 / convexity by a central ``spread`` bump (== a parallel nominal
    shift, since the static-inflation cash flows do not depend on the curve). DIRTY base, as
    :mod:`pricing.risk`. This is a REAL-rate duration — see the module docstring."""
    def priced(s):
        return price_ilb(valuation_date, maturity, real_coupon, curve, s, index_ratio=index_ratio,
                         inflation=inflation, face=face, freq=freq)

    base = priced(spread)
    p0 = base.dirty
    p_up = priced(spread + bump).dirty
    p_dn = priced(spread - bump).dirty
    if p0 == 0:
        return {"dirty": p0, "clean": base.clean, "dv01": float("nan"),
                "eff_duration": float("nan"), "convexity": float("nan")}
    return {
        "dirty": p0,
        "clean": base.clean,
        "dv01": (p_dn - p_up) / (2.0 * bump) * 1e-4,
        "eff_duration": (p_dn - p_up) / (2.0 * bump * p0),
        "convexity": (p_up + p_dn - 2.0 * p0) / (bump * bump * p0),
    }
