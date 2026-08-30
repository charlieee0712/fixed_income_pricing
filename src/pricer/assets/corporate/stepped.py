"""Stepped / step-up corporate bonds — a coupon TIME-TABLE on the vanilla engine
(template: ``assets/corporate/stepped.py``; the template's input Type 2, "Yield,
Maturity, Coupon Vector").

Serves Mario's "Pivot of Corp Bonds" column-F rows 13 and 20:

  row 13  "7.00% for t<01-Mar-2006 7.50% for t>=01-Mar-2006"   — date-segmented fixed
  row 20  "Step-up schedule"                                    — step-up

**These are not a separate pricing model, and saying so is the point.** The coupon
varies over time but every future payment is *known today*: there is no option, no
projection and no volatility. So the cash flows are deterministic and they price on the
ordinary discounting engine, which simply needs a coupon per date instead of one coupon.
Every function here forwards to ``vanilla``; the only thing this module owns is the
time-table and the rules for reading one.

**Where a schedule comes from, in order of authority:**

1. ``data/coupon_schedules.csv`` — a documented coupon path from a primary source (an
   issuer filing or prospectus). This OUTRANKS the workbook's free text, which has been
   wrong: one bond's "zero coupon" was a custodian data error for a 6.95% fixed bond,
   and two "(VAR)" tags belonged to plain fixed bonds.
2. :func:`parse_schedule` on the workbook's own free-text cell.
3. Nothing — which is a DATA GAP to flag, not a number to invent. "Step-up schedule"
   names a step-up without saying what the steps are; those live only in the prospectus.

⚠️ **Units: a schedule is in DECIMAL** (0.075 = 7.5%), unlike every other input at this
asset layer, which is in percent. That is deliberate rather than an oversight: the
schedule is produced by the parser and by the override CSV, both of which emit decimals,
and converting it at this one layer would create two incompatible dialects of the same
object. :func:`validate_schedule` refuses a schedule that looks like percent rather than
silently pricing a bond at a 750% coupon.
"""
from __future__ import annotations

from pricer.assets.corporate import vanilla
from pricer.core.pricing import coupon_schedule as _core

# Any single coupon at or above this (as a DECIMAL rate) is taken as a units mistake:
# 100% is far above every real coupon in this book, whose widest is 11.875%.
_IMPLAUSIBLE_RATE = 1.0


def parse_schedule(*formula_cells):
    """Read a coupon time-table out of the workbook's free-text coupon cells.

    Inputs
    ------
    1..n. formula_cells : str | None — ``Coupon_Formula2`` / ``Coupon_Formula`` cells,
       tried in order; the first that yields numeric coupons wins.

    Returns: ``[(effective_from | None, rate_decimal), ...]`` sorted by date, where
    ``None`` means "from issuance"; or **None** when the cell carries no numeric coupon.

    ``None`` is a deliberate answer, not a failure to try. A cell reading "Step-up
    schedule" states that steps exist without stating them; guessing a path there would
    put a fabricated coupon into a priced number. The caller flags the bond and sources
    the terms. The parser also refuses when the count of rates and dates does not line
    up, for the same reason.
    """
    return _core.parse_coupon_schedule(*formula_cells)


def coupon_on(schedule, date) -> float:
    """The coupon rate in force on a date.

    Inputs
    ------
    1. schedule : ``[(effective_from | None, rate_decimal), ...]``.
    2. date     : date — the date to look up.

    Returns: float — the rate in DECIMAL from the latest entry effective on or before
    ``date``. Steps that have already reversed by the valuation date therefore fall out
    naturally: one bond's coupon stepped up to 14.875% in 2003 and back to 11.875% by
    2009, and this returns the 11.875% in force.
    """
    validate_schedule(schedule)
    return _core.coupon_at(schedule, date)


def validate_schedule(schedule) -> None:
    """Fail fast on a malformed or wrongly-scaled coupon time-table.

    Inputs
    ------
    1. schedule : the candidate time-table.

    Returns: None. Raises ``ValueError`` naming the problem: an empty schedule, an entry
    that is not ``(date | None, rate)``, a negative rate, or a rate at or above 1.0 —
    which is almost always a schedule handed over in PERCENT when this input takes
    DECIMAL.
    """
    if not schedule:
        raise ValueError("coupon_schedule is empty; pass None to price on a single coupon")
    for entry in schedule:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            raise ValueError(f"coupon_schedule entries must be (effective_from | None, "
                             f"rate_decimal); got {entry!r}")
        _, rate = entry
        if rate is None or rate < 0.0:
            raise ValueError(f"coupon_schedule rate must be >= 0 (DECIMAL, 0.075 = 7.5%); "
                             f"got {rate!r}")
        if rate >= _IMPLAUSIBLE_RATE:
            raise ValueError(f"coupon_schedule rate {rate!r} looks like PERCENT — this "
                             f"input takes DECIMAL (0.075 = 7.5%)")


def calculated_price(coupon_schedule, cpn_freq: int, maturity, valuation_date, curve,
                     oas: float = 0.0, face: float = 100.0) -> float:
    """CLEAN price of a bond with a known coupon path, at a given spread.

    Inputs (see bonds_input.INPUT_CATALOGUE)
    ------
    1. coupon_schedule : ``[(effective_from | None, rate_decimal), ...]`` — the coupon
       time-table. **DECIMAL rates.**
    2. cpn_freq        : int — payments per year (1, 2, 4, 12).
    3. maturity        : date — bond maturity.
    4. valuation_date  : date — date of valuation.
    5. curve           : ZeroCurve — own-currency discount curve.
    6. oas             : float — flat spread in BASIS POINTS.
    7. face            : float — face value (default 100).

    Returns: float — clean price per ``face``. Each coupon date is paid at the rate in
    force on that date; the accrued interest uses the rate of the accruing period.
    """
    validate_schedule(coupon_schedule)
    return vanilla.calculated_price(0.0, cpn_freq, maturity, valuation_date, curve,
                                    oas=oas, face=face, coupon_schedule=coupon_schedule)


def implied_oas(coupon_schedule, cpn_freq: int, maturity, valuation_date,
                market_price: float, curve, face: float = 100.0) -> float:
    """Spread calibrated to a clean market price.

    Inputs
    ------
    1-4. coupon_schedule / cpn_freq / maturity / valuation_date, as above.
    5. market_price    : float — existing CLEAN price per ``face``.
    6. curve           : ZeroCurve.
    7. face            : float — face value (default 100).

    Returns: float — the flat spread in BASIS POINTS repricing the bond to
    ``market_price``, computed over the stepped cash flows rather than a flat coupon.
    Using the wrong coupon path here moves the answer a long way: correcting one bond
    from a mistaken 0% to its documented 6.95% moved its spread from -486 bp to +431 bp.
    """
    validate_schedule(coupon_schedule)
    return vanilla.implied_oas(0.0, cpn_freq, maturity, valuation_date, market_price,
                               curve, face=face, coupon_schedule=coupon_schedule)


def duration(coupon_schedule, cpn_freq: int, maturity, valuation_date, oas: float,
             curve, face: float = 100.0) -> float:
    """Effective duration in YEARS at the calibrated spread.

    Inputs: as :func:`implied_oas`, with ``oas`` (bp) in place of ``market_price``.
    Returns: float — effective (parallel-shift) duration, dirty-price base.
    """
    validate_schedule(coupon_schedule)
    return vanilla.duration(0.0, cpn_freq, maturity, valuation_date, oas, curve,
                            face=face, coupon_schedule=coupon_schedule)


def dv01(coupon_schedule, cpn_freq: int, maturity, valuation_date, oas: float, curve,
         face: float = 100.0) -> float:
    """Price change per +1 bp parallel shift.

    Inputs: identical to :func:`duration`.
    Returns: float — price drop per ``face`` for a +1 bp shift.
    """
    validate_schedule(coupon_schedule)
    return vanilla.dv01(0.0, cpn_freq, maturity, valuation_date, oas, curve, face=face,
                        coupon_schedule=coupon_schedule)


def convexity(coupon_schedule, cpn_freq: int, maturity, valuation_date, oas: float,
              curve, face: float = 100.0) -> float:
    """Effective convexity in YEARS^2.

    Inputs: identical to :func:`duration`.
    Returns: float — (P+ + P- - 2·P0) / (bump² · P0), dirty-price base.
    """
    validate_schedule(coupon_schedule)
    return vanilla.convexity(0.0, cpn_freq, maturity, valuation_date, oas, curve,
                             face=face, coupon_schedule=coupon_schedule)


def widening(coupon_schedule, cpn_freq: int, maturity, valuation_date, oas: float,
             curve, bp_adjust: float = 10.0, face: float = 100.0) -> float:
    """Scenario price after the spread WIDENS by ``bp_adjust`` bp.

    Inputs: as :func:`duration`, plus ``bp_adjust`` (spread move in bp, legacy ±10).
    Returns: float — clean price at ``oas + bp_adjust``.
    """
    validate_schedule(coupon_schedule)
    return vanilla.widening(0.0, cpn_freq, maturity, valuation_date, oas, curve,
                            bp_adjust=bp_adjust, face=face,
                            coupon_schedule=coupon_schedule)


def tightening(coupon_schedule, cpn_freq: int, maturity, valuation_date, oas: float,
               curve, bp_adjust: float = 10.0, face: float = 100.0) -> float:
    """Scenario price after the spread TIGHTENS by ``bp_adjust`` bp.

    Inputs: identical to :func:`widening`; ``bp_adjust`` is the tightening SIZE (positive).
    Returns: float — clean price at ``oas - bp_adjust``.
    """
    validate_schedule(coupon_schedule)
    return vanilla.tightening(0.0, cpn_freq, maturity, valuation_date, oas, curve,
                              bp_adjust=bp_adjust, face=face,
                              coupon_schedule=coupon_schedule)
