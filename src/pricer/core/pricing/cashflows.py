"""Cash-flow generation for fixed-rate bonds (template: ``core/pricing/cashflows.py``).

Builds the deterministic cash-flow table (dates + amounts) of a plain fixed bond —
including the zero-coupon degenerate case and Step-3 coupon *schedules* (stepped /
step-up / date-segmented rates). Discounting lives in ``core.pricing.discounting``;
this module never touches a curve.

Accrued interest also lives here: it is the ONE accrued formula shared by every
engine, including the callable lattice's calibration (Liping code review 2026-08-04).
Accrued depends only on dates — never on the curve, the OAS, or any embedded option —
so solving ``dirty(OAS) = target + AI`` and ``clean(OAS) = target`` give the SAME root
(pinned by the clean/dirty invariance tests).
"""
from __future__ import annotations

from pricer.core.utils.dates import YEAR_DAYS, as_date, coupon_dates, year_fraction
# NOTE: pricing.coupon_schedule is a real (not-yet-migrated) module, NOT one of the
# compatibility shims — it moves into core/ in a later rollout step; importing it
# here does not violate the "never import the shims" rule.
from pricing.coupon_schedule import coupon_at


def period_coupon_amount(coupon_rate: float, freq: int = 2, face: float = 100.0) -> float:
    """Coupon paid each period.

    Inputs
    ------
    1. coupon_rate : float — annual coupon rate in DECIMAL (0.065 = 6.5%).
    2. freq        : int — payments per year (1, 2, 4, 12).
    3. face        : float — face value the coupon is paid on (default 100).

    Returns: float = coupon_rate / freq * face.
    """
    return coupon_rate / freq * face


def bond_cashflows(valuation_date, maturity, coupon_rate: float, freq: int = 2,
                   face: float = 100.0, coupon_schedule=None):
    """Remaining cash flows of a fixed-rate bond, in date order.

    Inputs
    ------
    1. valuation_date  : date-like — pricing "as of" date.
    2. maturity        : date-like — bond maturity.
    3. coupon_rate     : float — annual coupon in DECIMAL; 0.0 = zero-coupon bond.
    4. freq            : int — payments per year (1, 2, 4, 12).
    5. face            : float — principal repaid at maturity (default 100).
    6. coupon_schedule : optional ``[(effective_from | None, rate_decimal), ...]`` —
       a time-table of coupon rates (stepped / step-up bonds); when given, each
       period's rate is looked up by its date and ``coupon_rate`` is ignored.

    Returns: list of ``(date, amount)`` ascending; the last amount includes ``face``.
    """
    dates, _last, _step = coupon_dates(valuation_date, maturity, freq)
    mat = as_date(maturity)
    flows = []
    for d in dates:
        if coupon_schedule is not None:
            cpn = coupon_at(coupon_schedule, d) / freq * face
        else:
            cpn = coupon_rate / freq * face
        amount = cpn + (face if d == mat else 0.0)
        flows.append((d, amount))
    return flows


def accrued_interest(valuation_date, maturity, coupon_rate: float, freq: int = 2,
                     face: float = 100.0, coupon_schedule=None) -> float:
    """THE accrued-interest formula (legacy ACT/364, 182-day grid) — single source
    for every engine.

    Inputs
    ------
    1. valuation_date  : date-like — pricing "as of" date.
    2. maturity        : date-like — bond maturity (anchors the backward grid).
    3. coupon_rate     : float — annual coupon in DECIMAL.
    4. freq            : int — payments per year.
    5. face            : float — face value (default 100).
    6. coupon_schedule : optional coupon time-table — the ACCRUING period's rate is
       used when given.

    Returns: float accrued per ``face`` =
    (rate / freq * face) * days-since-prior-coupon / step_days.
    """
    val = as_date(valuation_date)
    dates, last_cpn_date, step_days = coupon_dates(valuation_date, maturity, freq)
    if not dates:
        return 0.0
    rate = coupon_at(coupon_schedule, dates[0]) if coupon_schedule is not None else coupon_rate
    return rate / freq * face * (val - last_cpn_date).days / step_days


def lattice_inputs(valuation_date, maturity, coupon_rate: float, freq: int = 2,
                   face: float = 100.0):
    """Real-schedule inputs for the callable lattice, on exactly the analytical
    engine's conventions (so a straight bond on the lattice reprices the closed form
    to machine precision).

    Inputs
    ------
    1. valuation_date : date-like — pricing "as of" date.
    2. maturity       : date-like — bond maturity.
    3. coupon_rate    : float — annual coupon in DECIMAL.
    4. freq           : int — payments per year.
    5. face           : float — face value (default 100).

    Returns: ``(coupon_times, accrued)`` — ACT/364 year-fractions of the strictly
    future coupon dates, and the accrued to subtract from the tree's root PV (= dirty)
    so ``tree_PV - accrued`` is the model CLEAN price. A coupon falling exactly ON the
    valuation date (the analytical engine puts it in dirty and nets it out with a full
    period of accrued) is folded into the returned accrued, keeping the clean identity
    in that corner too.
    """
    val = as_date(valuation_date)
    dates, _last, _step = coupon_dates(valuation_date, maturity, freq)
    times = [year_fraction(val, d) for d in dates if (d - val).days > 0]
    if not times:
        raise ValueError(f"no future coupon dates between {valuation_date} and {maturity}")
    ai = accrued_interest(valuation_date, maturity, coupon_rate, freq=freq, face=face)
    t0_cpn = coupon_rate / freq * face if (dates and dates[0] == val) else 0.0
    return times, ai - t0_cpn
