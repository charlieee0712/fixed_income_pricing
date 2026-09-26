"""To-be-announced forward on a generic pool (template: ``assets/securitized/tba.py``).

A TBA is an agreement to buy an unspecified pool of a given issuer, term and coupon on a
stated settlement date; which pools actually deliver is announced 48 hours beforehand. The
custodian carries these as full-value positions — ``MV == par * BT/100`` holds on 29 of 29 —
so reproducing BT is the same job as for a pass-through, with one difference: **the price is
a FORWARD price, struck for a settlement date weeks after the valuation date.**

The forward is a deterministic consequence of the spot curve, not another assumption:

    F * DF(t0, t1)  =  PV_t0( cash flows that begin at t1 )

so ``F = PV_t0(flows from t1) / DF(t0, t1)``, using only the valuation-date curve. At
``settle == valuation`` the wrapper DELEGATES to the spot path rather than re-deriving it, so
the forward reduces to the engine bit-for-bit — the same discipline ``hybrid.py`` uses for its
degenerate limits, and the reason this is a forward ON the pool engine rather than a second
engine beside it.

WHAT IS ASSUMED HERE, AND WHAT EACH ASSUMPTION IS WORTH (measured 2026-09-25, not argued)
------------------------------------------------------------------------------------------
* **The gross WAC: 0.1 bp.** A TBA delivers a newly issued pool, so its WAC is the coupon
  plus servicing and guarantee fees. We do not know the 2009 fee level, and it turns out not
  to matter: moving the WAC from coupon+0.50 to coupon+1.00 moves the calibrated spread by
  **one tenth of a basis point**. Scheduled amortisation is negligible in a 360-month pool's
  first years, so the flows are interest (at the net coupon, which we know exactly) plus
  prepayment (at the CPR). ⭐ This is why the Bloomberg pull's 2026-dated WAC — an as-of error
  everywhere else in this book — is harmless here. It is not used.
* **The settlement DAY: about 4 bp.** SIFMA sets one settlement date per month per class and
  the 2009 calendar is not published online any more, so :data:`TBA_SETTLE_DAY` is the 15th.
  The forward adjustment is worth 17.4 bp over the 45 days to a May settle, so a ten-day
  error in the date is roughly **4 bp**. Class A (30-year) really settles nearer the 12th-14th
  and Class B (15-year) later, which would move these in opposite directions by less than that.
* **The CPR: about 21 bp over the plausible range**, identical to the pass-through book and
  handled the same way — a grid, not a point. See ``scripts/pool_risk.py``.

So a TBA carries exactly one real assumption, the same one every other pool in this book
carries, plus a settlement date worth single-digit basis points.
"""
from __future__ import annotations

import datetime
import math

from scipy.optimize import brentq

from pricer.assets.securitized import pool
from pricer.core.pricing.prepayment import pool_cash_flows

#: Day of the settlement month used when the SIFMA calendar is unavailable. Worth ~4 bp per
#: ten days of error; see the module docstring. Named rather than inlined so the assumption
#: has somewhere to be found and changed.
TBA_SETTLE_DAY = 15

#: Gross WAC over the pass-through coupon — servicing plus guarantee fee. MEASURED to be worth
#: 0.1 bp across the plausible range, so the value is a convention rather than an input worth
#: sourcing. NY Fed Staff Report 674 uses the same 50 bp for the same reason.
TBA_SERVICING_SPREAD_PCT = 0.50

_BP = 1e-4
_PCT = 1e-2


def settlement_date(valuation_date, settle_month: int, settle_day: int = TBA_SETTLE_DAY):
    """The settlement date a description's month refers to.

    Inputs
    ------
    1. valuation_date : date — the valuation date.
    2. settle_month   : int — calendar month 1-12, read off the description.
    3. settle_day     : int — day of month (default :data:`TBA_SETTLE_DAY`).

    Returns: date — always in the VALUATION YEAR. A month already past yields a date before
    the valuation date, which :func:`settle_years` then refuses.

    ⚠️ **No year roll.** An earlier version advanced the year when the settle month had
    passed, reasoning that a December valuation quoting a January settle means next January.
    Re-valuing this book at the 2009-06-10 control date exposed the flaw: the holdings file is
    a 2009-03-31 snapshot, so "SETTLES APRIL" means April 2009, and the roll turned a contract
    that had already delivered into a forward fourteen months out. Priced without complaint.
    Nothing in a description distinguishes "next January" from "last April", so the ambiguity
    is refused rather than resolved by a rule that is right half the time.
    """
    return datetime.date(valuation_date.year, settle_month, settle_day)


def settle_years(valuation_date, settle_date) -> float:
    """Act/365 time from valuation to settlement. Negative is refused, not clamped."""
    days = (settle_date - valuation_date).days
    if days < 0:
        raise ValueError(
            f"settlement {settle_date} precedes valuation {valuation_date}: this forward had "
            "already delivered at the valuation date")
    return days / 365.0


def forward_price(coupon: float, term_months: int, cpr: float, curve,
                  settle: float, spread: float = 0.0, wac=None,
                  face: float = 100.0) -> float:
    """Forward price per 100 of a generic pool delivering at ``settle``.

    Inputs
    ------
    1. coupon      : float — pass-through coupon in PERCENT; what the investor receives.
    2. term_months : int — ORIGINAL term of the delivered pool (180 or 360). A TBA delivers
       new production, so the remaining term at settlement is the full original term.
    3. cpr         : float — constant prepayment rate in PERCENT per year.
    5. curve       : ZeroCurve — the VALUATION-date curve. No forward curve is built; the
       no-arbitrage relation needs only this one.
    6. settle      : float — years from valuation to settlement.
    7. spread      : float — flat spread in BASIS POINTS.
    4. wac         : float | None — gross WAC in PERCENT; defaults to the coupon plus
       :data:`TBA_SERVICING_SPREAD_PCT`, which is measurably worth 0.1 bp.
    8. face        : float — per-100 basis (default 100).

    Returns: float — the forward price, directly comparable to a TBA market quote.
    """
    gross = coupon + TBA_SERVICING_SPREAD_PCT if wac is None else wac
    if settle == 0.0:
        # Delegate rather than re-derive: the forward MUST reduce to the spot engine exactly,
        # and an independently written zero-settle branch is how two paths start to disagree.
        return pool.calculated_price(gross, term_months, cpr, curve, spread=spread,
                                     net_coupon=coupon, face=face)
    flows = pool_cash_flows(gross * _PCT, int(term_months), cpr * _PCT,
                            net_coupon=coupon * _PCT, balance=face)
    s = spread * _BP
    pv = sum(f.total * math.exp(-(f.t + settle) * (float(curve.zero_rate(f.t + settle)) + s))
             for f in flows)
    return pv / math.exp(-settle * float(curve.zero_rate(settle)))


def implied_spread_bp(coupon: float, term_months: int, cpr: float, market_price: float,
                      curve, settle: float, wac=None, face: float = 100.0) -> float:
    """Flat spread reproducing a quoted TBA forward price at a GIVEN CPR.

    Inputs: 1-8 as :func:`forward_price`, with ``market_price`` the quoted forward per 100.
    Returns: float — the implied spread in BASIS POINTS.

    ⚠️ Solves for the spread, never for the CPR. The pass-through book showed that fixing the
    spread near zero and implying the prepayment rate produces a median 66% and pools no CPR
    can reach; the same discount-rate gap applies here and for the same reason.
    """
    def f(bp):
        return forward_price(coupon, term_months, cpr, curve, settle, bp, wac, face) - market_price

    lo, hi = -200.0, 2000.0
    guard = 0
    while f(lo) < 0 and guard < 20:
        lo -= 200.0
        guard += 1
    while f(hi) > 0 and guard < 40:
        hi += 1000.0
        guard += 1
    if f(lo) * f(hi) > 0:
        raise ValueError(
            f"no spread reproduces {market_price} for a {coupon}% {term_months}-month TBA "
            f"at CPR {cpr}% (bracketed {f(lo) + market_price:.3f} to {f(hi) + market_price:.3f})")
    return brentq(f, lo, hi, xtol=1e-8)


def weighted_average_life(coupon: float, term_months: int, cpr: float, wac=None,
                          face: float = 100.0) -> float:
    """WAL in years of the delivered pool, measured from SETTLEMENT.

    Inputs: 1-4 and 8 as :func:`forward_price`.
    Returns: float — principal-weighted average time, in years after settlement.

    The settlement lag is deliberately not added: WAL describes the security being delivered,
    and adding the few weeks before delivery would make it a property of the trade date.
    """
    gross = coupon + TBA_SERVICING_SPREAD_PCT if wac is None else wac
    return pool.weighted_average_life(gross, term_months, cpr, net_coupon=coupon, face=face)
