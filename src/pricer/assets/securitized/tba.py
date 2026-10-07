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

⭐⭐ AND IT IS THE ONE PLACE IN THIS BOOK WHERE DV01 AND CS01 ARE DIFFERENT NUMBERS
---------------------------------------------------------------------------------------
Every other security here is discounted at ``z(t) + s``, so a parallel curve bump and a spread
bump are the same arithmetic and the two sensitivities are one number wearing two names (the
Tier-1 table's ``dv01`` and ``cs01`` columns are identical on all 757 rows priced before these
forwards -- maximum difference exactly 0.0). A forward separates them, because **the spread
sits in the numerator only**:

    F(d) = [ Σ c_i e^{-(t_i+u)(z_i + d + s)} ] / e^{-u(z(u) + d)}

Differentiating the log in ``d`` (a parallel rate shift) picks up ``+u`` from the denominator;
differentiating in ``s`` does not, because the financing leg carries the rate and not the
spread. So, exactly:

    rate_duration  ==  spread_duration  −  settle

⚠️ **Which means all three metrics on one published row must come from the same bump.** A rate
duration beside a spread convexity cannot be used together to approximate a move, and the two
are not interchangeable here even though they are everywhere else. :func:`duration`,
:func:`dv01` and :func:`convexity` bump the SPREAD; :func:`rate_duration`,
:func:`rate_dv01` and :func:`rate_convexity` bump the CURVE.

⚠️ **The static duration is one-sided here, not merely approximate.** All 27 forwards in
this book are premiums (custodian price 101.66 to 105.31, coupon 0.85% below to 1.65% above the
prevailing 30-year rate), so fixed cash flows overstate their life in the SAME direction for
every one of them. MEASURED at the 2009-03-31 curve and a 25% CPR: median spread duration
**2.894y**, median rate duration **2.851y**, against a custodian median of **1.821y** — a
median absolute gap of 1.05y, with 5 of the 27 beyond the 1.5y reporting threshold. The 478
spot pools show the same shape and nearly the same proportion (2.799 vs 2.280, 102 of 478 =
21% beyond 1.5y) but scattered in both directions. The gap IS the prepayment option that
Tier 1 does not model, which is why it is published with the custodian's own figure beside it
rather than withheld.

⚠️ **A short's dollar duration carries the sign of its position, and that sign lives on the
par column alone.** 5 of these 27 are shorts (−124.4M against +400.5M long, net +276.1M par),
and the metrics below are properties of the SECURITY: dollar duration is ``par × dv01`` with
par's own sign. An aggregation that takes an absolute value of par will get the book's net
mortgage risk badly wrong, and nothing in these numbers can warn it.
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

#: Size of the central bump used by every metric below, in BASIS POINTS. The same 1 bp
#: ``core.pricing.prepayment.pool_risk_metrics`` uses, so a TBA number and a pool number are
#: produced by the same arithmetic and may sit in the same column.
RISK_BUMP_BP = 1.0


class _Shifted:
    """``curve`` with every zero rate moved by a parallel shift, in DECIMALS.

    ⭐ Here rather than in ``core/market/curves.py`` on purpose: the forward is the only
    instrument in this layer whose rate bump is not a spread bump, so it is the only caller.
    Relocation trigger = a second one. Deliberately duck-typed on ``zero_rate(t)`` alone, so
    it wraps a real :class:`~curves.zero_curve.ZeroCurve` and a one-line test curve alike.
    """

    __slots__ = ("_curve", "_shift")

    def __init__(self, curve, shift: float):
        self._curve = curve
        self._shift = shift

    def zero_rate(self, t):
        return float(self._curve.zero_rate(t)) + self._shift


def _priced(coupon, term_months, cpr, curve, settle, spread, wac, face, what, bp):
    """One repricing with either the SPREAD or the whole CURVE moved by ``bp`` basis points."""
    if what == "spread":
        return forward_price(coupon, term_months, cpr, curve, settle, spread + bp, wac, face)
    return forward_price(coupon, term_months, cpr, _Shifted(curve, bp * _BP), settle,
                         spread, wac, face)


def _metrics(coupon, term_months, cpr, curve, settle, spread, wac, face, what) -> dict:
    """Central-difference duration / DV01 / convexity, in the shape the pool engine returns.

    ``what`` is ``"spread"`` or ``"rate"`` and is the whole difference between the two metric
    families; see the module docstring for why a forward has two.
    """
    def at(bp):
        return _priced(coupon, term_months, cpr, curve, settle, spread, wac, face, what, bp)

    p0 = forward_price(coupon, term_months, cpr, curve, settle, spread, wac, face)
    p_up, p_dn = at(RISK_BUMP_BP), at(-RISK_BUMP_BP)
    h = RISK_BUMP_BP * _BP
    if p0 == 0:
        return {"price": p0, "dv01": float("nan"), "eff_duration": float("nan"),
                "convexity": float("nan")}
    return {
        "price": p0,
        "dv01": (p_dn - p_up) / (2.0 * h) * 1e-4,
        "eff_duration": (p_dn - p_up) / (2.0 * h * p0),
        "convexity": (p_up + p_dn - 2.0 * p0) / (h * h * p0),
    }


def duration(coupon: float, term_months: int, cpr: float, curve, settle: float,
             spread: float = 0.0, wac=None, face: float = 100.0) -> float:
    """SPREAD duration of the forward price, in YEARS.

    Inputs: 1-8 as :func:`forward_price`.
    Returns: float — relative price move per unit parallel SPREAD shift.

    ⚠️ Under a constant CPR the cash flows do not move when rates move, so this is the
    discounting effect only; a real pool prepays faster as rates fall, which shortens it
    exactly when a bond would lengthen. That missing response is the negative convexity
    mortgage investors are paid for, and it is absent here by construction.

    ⚠️ **Not the same number as :func:`rate_duration`** — it is longer by exactly ``settle``,
    because the forward's own discount leg carries the rate and not the spread.
    """
    return _metrics(coupon, term_months, cpr, curve, settle, spread, wac, face,
                    "spread")["eff_duration"]


def dv01(coupon: float, term_months: int, cpr: float, curve, settle: float,
         spread: float = 0.0, wac=None, face: float = 100.0) -> float:
    """Forward-price change per +1 bp of SPREAD, per 100 face (this is the CS01).

    Inputs: 1-8 as :func:`forward_price`. Returns: float — same sign convention as the
    bond and pool surfaces. See :func:`rate_dv01` for the rate bump, which differs.
    """
    return _metrics(coupon, term_months, cpr, curve, settle, spread, wac, face,
                    "spread")["dv01"]


def convexity(coupon: float, term_months: int, cpr: float, curve, settle: float,
              spread: float = 0.0, wac=None, face: float = 100.0) -> float:
    """Second-order SPREAD sensitivity of the forward price.

    Inputs: 1-8 as :func:`forward_price`. Returns: float — convexity of the FIXED flows.

    ⚠️ Positive, like any fixed stream; the market's mortgage convexity is negative. The
    difference is the entire prepayment option, and quoting this as a TBA's convexity without
    that sentence attached would be a real misstatement.
    """
    return _metrics(coupon, term_months, cpr, curve, settle, spread, wac, face,
                    "spread")["convexity"]


def rate_duration(coupon: float, term_months: int, cpr: float, curve, settle: float,
                  spread: float = 0.0, wac=None, face: float = 100.0) -> float:
    """Effective duration of the forward price under a parallel CURVE shift, in YEARS.

    Inputs: 1-8 as :func:`forward_price`.
    Returns: float — relative price move per unit parallel shift of the whole zero curve.

    ⭐ **Shorter than :func:`duration` by exactly ``settle``** — see the module docstring for
    the one-line derivation. This is the number comparable to the custodian's own effective
    duration, and the one the Tier-1 table publishes, because that table's ``dv01`` column is
    a rate bump on every other row too (where it happens to coincide with the spread bump).
    """
    return _metrics(coupon, term_months, cpr, curve, settle, spread, wac, face,
                    "rate")["eff_duration"]


def rate_dv01(coupon: float, term_months: int, cpr: float, curve, settle: float,
              spread: float = 0.0, wac=None, face: float = 100.0) -> float:
    """Forward-price change per +1 bp parallel CURVE shift, per 100 face.

    Inputs: 1-8 as :func:`forward_price`. Returns: float — smaller in magnitude than
    :func:`dv01` by ``settle × price × 1e-4``, which is the carry on the financing leg.
    """
    return _metrics(coupon, term_months, cpr, curve, settle, spread, wac, face,
                    "rate")["dv01"]


def rate_convexity(coupon: float, term_months: int, cpr: float, curve, settle: float,
                   spread: float = 0.0, wac=None, face: float = 100.0) -> float:
    """Second-order sensitivity of the forward price to a parallel CURVE shift.

    Inputs: 1-8 as :func:`forward_price`. Returns: float.

    ⚠️ Carried as its own function for one reason: a convexity-adjusted move needs the
    SECOND derivative that matches the FIRST one it is used with. Mixing this with
    :func:`dv01`, or :func:`convexity` with :func:`rate_dv01`, silently prices the wrong
    adjustment. Same positive-sign caveat as :func:`convexity`.
    """
    return _metrics(coupon, term_months, cpr, curve, settle, spread, wac, face,
                    "rate")["convexity"]
