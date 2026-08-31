"""Floating-rate note (FRN) pricing + risk (template: ``core/pricing/floating.py``).

MOVED VERBATIM from ``pricing/frn.py`` (Round 2b, 2026-08-30) — byte-for-byte the code
that produced every published floating-rate number; ``pricing.frn`` is now a shim over
this module and re-exports its private helpers, because ``core/pricing/hybrid.py``
composes the FRN leg out of them.

Which bonds this serves (Mario's "Pivot of Corp Bonds" sheet, column F):
  row 14  "GBP LIBOR + Spread"        ( 1 tab row)
  row 15  "Reference Rate + Spread"   (12 tab rows)
  row 16  "EURIBOR + Spread"          ( 9 tab rows)
Row 12 ("Fixed -> Floating", 5 tab rows) uses this engine for its post-switch leg only
— see ``core/pricing/hybrid.py``.

Originally Step 4 (Mario 2026-07-08).

Ports the legacy ``BondOAS`` analysisType 7/8/9 approach (Step-1 recon) with OUR data: each future
floating coupon is projected as the simple forward off our bootstrapped ``ZeroCurve``
(``F(t0,t1) = (DF(t0)/DF(t1) - 1)/(t1-t0)``) plus a spread, and every cash flow is discounted on the
**same** curve plus a flat implied OAS. Single-curve — the 2009 convention; **multi-curve / OIS
discounting is a documented future enhancement**, not modelled here.

The spread is usually absent from this workbook ("EURIBOR + Spread", no number) so it is folded into
the calibrated OAS: the implied OAS is then a discount-margin-type spread (quoted spread + credit).
The **risk metrics are robust to this** — an FRN's rate sensitivity is structural, not spread-level.

Conventions mirror :mod:`pricing.bond_price` (ACT/364, backward ``round(364/freq)``-day schedule,
accrued) so FRN and vanilla numbers are comparable. For freq 1 and 2 the period fraction is exactly
``1/freq`` (364/1, 182/2), so the classic par identity holds exactly.

⚠️ **Effective duration bumps the CURVE, not the OAS.** Under a parallel curve shift the projected
forwards rise with the discount rate and (largely) offset it, so an FRN's effective duration is
~ the time to the next reset — far shorter than a same-maturity fixed bond. Bumping only the OAS
(which leaves the forwards fixed) would wrongly make the FRN look like a fixed bond. This is the
signature floating-rate check.

Duration regimes (so a NEGATIVE eff-dur is never mistaken for a bug):
  * near par            -> eff-dur ~ the time to the next reset (the note resets its rate risk away);
  * deep discount (below par on credit) -> price = par - OAS*annuity_PV, so a rate rise discounts that
    annuity harder, the below-par gap shrinks, and the price RISES -> a NEGATIVE
    (credit-spread-annuity) duration of magnitude ~ OAS * annuity_duration. Self-consistent on the
    real book: a 57y BT~50 floater has gap ~50 * annuity-dur ~10 / price ~50 ~ -10 (observed -10.6);
  * universally |eff-dur| <<< a same-maturity FIXED bond -- the reliability invariant.

Spread convention (confirmed 2026-07-08): all 27 URS ``coupon_formula`` are generic ("... + Spread",
no number), so the 18 priced FRNs use ``spread=0`` and the implied OAS ABSORBS the unknown quoted
spread. The calibrated price reprices BT exactly and the duration is (to leading order)
spread-independent; once a real spread is supplied it can be separated back out of the OAS.
"""
from __future__ import annotations

import datetime as dt
import math
import re
from dataclasses import dataclass

import pandas as pd
from scipy.optimize import brentq

from pricer.core.pricing.discounting import curve_discount_factor, curve_rate
from pricer.core.utils.dates import as_date
from pricer.errors import CalibrationError

YEAR_DAYS = 364.0

_SPREAD_BP = re.compile(r"\+\s*(\d+(?:\.\d+)?)\s*bp", re.I)
_SPREAD_PCT = re.compile(r"\+\s*(\d+(?:\.\d+)?)\s*%")


# Back-compat aliases. These three were the module's own private helpers, and
# `core/pricing/hybrid.py` imported them BY THEIR PRIVATE NAMES across a module boundary --
# a seam no refactor could see and no reader could rely on. They are now the canonical public
# functions, kept under the old names because `src/pricing/frn.py` (the legacy shim) re-exports
# them and the hybrid shim resolves them through it. Same objects, so nothing can drift.
_as_date = as_date
_rate = curve_rate
_df = curve_discount_factor


def simple_forward(curve, t0, t1, shift: float = 0.0):
    """Annualised simple forward between ``t0`` and ``t1`` off the (shifted) curve:
    ``(DF(t0)/DF(t1) - 1) / (t1 - t0)``."""
    tau = t1 - t0
    if tau <= 0:
        return _rate(curve, max(t1, 1e-6), shift)
    return (_df(curve, t0, shift) / _df(curve, t1, shift) - 1.0) / tau


def parse_frn_spread(*formulas):
    """Spread over the index as a DECIMAL, or ``None`` if the formula carries no number.

    "EURIBOR + 45bp" -> 0.0045, "LIBOR + 0.50%" -> 0.005, "EURIBOR + Spread" -> None (a data gap to
    flag, never a guess — the None principle, as in :mod:`pricing.coupon_schedule`).
    """
    for f in formulas:
        if f is None:
            continue
        s = str(f)
        m = _SPREAD_BP.search(s)
        if m:
            return round(float(m.group(1)) / 1e4, 10)
        m = _SPREAD_PCT.search(s)
        if m:
            return round(float(m.group(1)) / 100.0, 10)
    return None


@dataclass
class FrnResult:
    clean: float
    dirty: float
    accrued: float
    next_reset_t: float          # years to the next coupon/reset date (~ the effective duration)
    cashflows: list


def price_frn(valuation_date, maturity, curve, oas: float = 0.0, *, current_coupon=None,
              spread: float = 0.0, face: float = 100.0, freq: int = 2, curve_shift: float = 0.0):
    """Clean/dirty price of an FRN. Future coupons = simple forward (off the curve, incl.
    ``curve_shift``) + ``spread``; the current period's coupon is ``current_coupon`` if known (the
    already-fixed reset), else the forward. Discounting adds ``oas`` (flat) to the shifted curve.

    ``curve_shift`` parallel-shifts the curve for BOTH projection and discounting — it is how
    effective duration is taken (reprojecting the forwards). ``oas`` shifts only the discounting.
    """
    val, mat = _as_date(valuation_date), _as_date(maturity)
    if val > mat:
        return FrnResult(0.0, 0.0, 0.0, 0.0, [])
    step_days = max(1, round(YEAR_DAYS / freq))
    dates, d = [], mat
    while d >= val:
        dates.append(d)
        d = d - dt.timedelta(days=step_days)
    last_reset = d                                    # coupon date just before valuation
    dates.reverse()                                   # ascending: d_1 < ... < d_N = mat

    dirty, cfs = 0.0, []
    for i, dd in enumerate(dates):
        t = (dd - val).days / YEAR_DAYS
        prev = dates[i - 1] if i > 0 else last_reset
        t_prev = (prev - val).days / YEAR_DAYS
        tau = t - t_prev
        if i == 0 and current_coupon is not None:
            rate_cf = current_coupon                  # this period was fixed at the last reset
        else:
            # use the ACTUAL period start (t_prev < 0 for the stub period before valuation) so the
            # par-floater telescoping is exact -> a pure floater holds par under any curve level
            rate_cf = simple_forward(curve, t_prev, t, curve_shift) + spread
        amount = rate_cf * tau * face + (face if dd == mat else 0.0)
        df = _df(curve, t, curve_shift + oas)
        dirty += amount * df
        cfs.append((dd, t, rate_cf, amount, df, amount * df))

    t1 = (dates[0] - val).days / YEAR_DAYS
    cur_rate = current_coupon if current_coupon is not None else \
        simple_forward(curve, (last_reset - val).days / YEAR_DAYS, t1, curve_shift) + spread
    accrued = cur_rate * ((val - last_reset).days / YEAR_DAYS) * face
    return FrnResult(dirty - accrued, dirty, accrued, t1, cfs)


def implied_oas_frn(target_clean, valuation_date, maturity, curve, *, current_coupon=None,
                    spread: float = 0.0, face: float = 100.0, freq: int = 2,
                    lo: float = -0.20, hi: float = 2.0, xtol: float = 1e-10, max_expand: int = 40):
    """Solve the flat OAS s.t. the FRN clean price == ``target_clean`` (the custodian BT). Price is
    strictly decreasing in the OAS, so bracketing (Brent) is robust."""
    def f(o):
        return price_frn(valuation_date, maturity, curve, oas=o, current_coupon=current_coupon,
                         spread=spread, face=face, freq=freq).clean - target_clean

    flo, fhi, n = f(lo), f(hi), 0
    while flo < 0 and n < max_expand:
        lo -= 0.20; flo = f(lo); n += 1
    while fhi > 0 and n < max_expand:
        hi += 1.0; fhi = f(hi); n += 1
    if flo * fhi > 0:
        raise CalibrationError(f"cannot bracket FRN OAS for target={target_clean}: "
                         f"f({lo:.3f})={flo:.4f}, f({hi:.3f})={fhi:.4f}")
    return brentq(f, lo, hi, xtol=xtol)


def frn_risk_metrics(valuation_date, maturity, curve, oas, *, current_coupon=None, spread: float = 0.0,
                     face: float = 100.0, freq: int = 2, bump: float = 1e-4) -> dict:
    """Effective duration / DV01 / convexity by a parallel **curve** bump (reprojects the forwards
    AND rediscounts) — the correct FRN rate sensitivity. ``oas`` is held at its calibrated value.

    Inputs
    ------
    1. valuation_date : date-like — pricing "as of" date.
    2. maturity       : date-like — final coupon and redemption date.
    3. curve          : ZeroCurve — projection AND discounting curve (2009 single-curve convention).
    4. oas            : float — the calibrated flat spread, DECIMAL, held fixed across the bumps.
    5. current_coupon : float | None — the coupon already fixed at the last reset, DECIMAL. When
       None it is projected off the curve; see the note below, which is what this function does
       differently from a plain repricing.
    6. spread         : float — quoted margin over the index, DECIMAL.
    7. face           : float — redemption amount, default 100.
    8. freq           : int — resets per year.
    9. bump           : float — parallel curve shift for the difference quotients, default 1bp.

    THE CURRENT COUPON IS FROZEN ACROSS THE BUMPS. It was fixed at the last reset date, which is
    in the past, so it is a KNOWN cash flow: moving today's curve cannot change it. Supplying
    ``current_coupon`` always froze it. Leaving it None did not — the stub was reprojected off the
    bumped curve, so the bump silently repriced a coupon that had already been set. That gave the
    projected case a duration of MINUS the time SINCE the last reset, against PLUS the time TO the
    next reset for an otherwise identical bond whose coupon happened to be recorded. Two bonds, one
    economic exposure, opposite-signed answers, decided by a data field.

    When the coupon is not observed we freeze a BASE-CURVE PROXY instead: the stub rate the
    unbumped curve implies, read back off the engine's own cash-flow grid so it uses the true
    period start (before the valuation date) and already includes the quoted margin. At zero shift
    the proxy reproduces the unfrozen number exactly, so PRICE AND CALIBRATED OAS DO NOT MOVE —
    only the sensitivities do, and both regimes now agree.
    """
    # the proxy is read off the engine's own grid: cashflows[0] is the stub period, and its rate is
    # already `simple_forward(true period start ... ) + spread`. Rebuilding it here would risk
    # dropping the margin or mis-dating the period start.
    frozen = current_coupon
    if frozen is None:
        probe = price_frn(valuation_date, maturity, curve, oas=oas, current_coupon=None,
                          spread=spread, face=face, freq=freq)
        if probe.cashflows:
            frozen = probe.cashflows[0][2]

    def priced(shift):
        return price_frn(valuation_date, maturity, curve, oas=oas, current_coupon=frozen,
                         spread=spread, face=face, freq=freq, curve_shift=shift)

    # provenance: a reader must be able to tell an OBSERVED fixing from one we estimated,
    # because the second is a modelling choice and the first is a fact about the note.
    provenance = {
        "current_coupon": frozen,
        "current_coupon_source": "supplied" if current_coupon is not None else "base_curve_proxy",
        "risk_status": "final" if current_coupon is not None else "provisional",
    }

    base = priced(0.0)
    p0 = base.dirty
    p_up = priced(bump).dirty        # curve up -> price down
    p_dn = priced(-bump).dirty
    if p0 == 0:
        return {"dirty": p0, "clean": base.clean, "dv01": float("nan"),
                "eff_duration": float("nan"), "convexity": float("nan"),
                "next_reset_t": base.next_reset_t, **provenance}
    return {
        "dirty": p0,
        "clean": base.clean,
        "dv01": (p_dn - p_up) / (2.0 * bump) * 1e-4,
        "eff_duration": (p_dn - p_up) / (2.0 * bump * p0),
        "convexity": (p_up + p_dn - 2.0 * p0) / (bump * bump * p0),
        "next_reset_t": base.next_reset_t,
        **provenance,
    }
