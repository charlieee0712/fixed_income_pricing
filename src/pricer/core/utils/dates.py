"""Date operations shared by every pricing engine (template: ``core/utils/dates.py``).

The two constants below ARE the legacy cash-flow calendar (Pricing File.xlsm /
Bootstrapping.bas, VERIFIED 2026-06-29): a year is 364 days and a semiannual coupon
period is 182 days. They differ from true calendar months on purpose — changing them
breaks reconciliation with the legacy tool and with every validated number in this
repo. Real day-count conventions (30/360, ACT/ACT, ...) are carried as *data* only;
the legacy engine documents its own Daycount input as "30/360, but is not used".
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

YEAR_DAYS = 364.0     # legacy: one year = 364 days  (VBA `diasmat / 364`)
HALF_DAYS = 182       # legacy: one semiannual period = 182 days (`fechamobil - 182`)


def as_date(value) -> dt.date:
    """Normalise any date-like value to a ``datetime.date``.

    Inputs
    ------
    1. value : str | datetime | date | pandas.Timestamp — the date in any common form.

    Returns: ``datetime.date``.
    """
    return pd.Timestamp(value).date()


def year_fraction(valuation_date, cash_flow_date) -> float:
    """Year fraction between two dates on the legacy ACT/364 convention.

    Inputs
    ------
    1. valuation_date : date-like — the "as of" date (t = 0).
    2. cash_flow_date : date-like — the future cash-flow date.

    Returns: float years = (cash_flow_date - valuation_date).days / 364.
    """
    return (as_date(cash_flow_date) - as_date(valuation_date)).days / YEAR_DAYS


def exercise_schedule_times(valuation_date, schedule):
    """Convert a DATED exercise schedule to times in years — the project's ONE conversion.

    Inputs
    ------
    1. valuation_date : date-like — the pricing "as of" date, which is time 0.
    2. schedule       : ``[(date, price_per_100), ...]`` for a call or put, or
       ``[(date, fraction, price_per_100), ...]`` for a sinking fund. Any trailing fields
       are carried through untouched, so one conversion serves every kind of right.

    Returns: the same tuples with the date replaced by a year fraction, sorted by time and
    clamped at 0 — a right already exercisable today sits on the valuation node.

    Day count is :data:`YEAR_DAYS` (ACT/364), the same axis the coupon grid is built on, so
    an exercise date and a coupon date are directly comparable. That sharing is the point of
    this function existing: there used to be a second copy of this conversion in the data
    layer whose day count defaulted to 365.25, one unpassed argument away from placing every
    call date on a different axis than the coupons it has to be compared against. Both public
    entry points now delegate here, so there is no second convention left to drift.
    """
    val = as_date(valuation_date)
    return sorted((max(0.0, year_fraction(val, entry[0])),
                   *(float(x) for x in entry[1:])) for entry in schedule)


def coupon_dates(valuation_date, maturity, freq: int = 2):
    """The legacy coupon grid — the ONE schedule walk every date-based engine shares:
    backward from ``maturity`` in ``round(364/freq)``-day steps until just before
    ``valuation_date``.

    Inputs
    ------
    1. valuation_date : date-like — pricing "as of" date.
    2. maturity       : date-like — bond maturity (the last coupon date).
    3. freq           : int — coupon payments per year: 1, 2 (default), 4 or 12.

    Returns: ``(dates, last_coupon_date, step_days)`` where ``dates`` (ascending) are
    all grid dates with ``date >= valuation_date`` (last = maturity),
    ``last_coupon_date`` is the grid date immediately BEFORE the valuation date (the
    accrual anchor), and ``step_days`` is the whole-day period length. If
    ``valuation_date > maturity`` the walk is empty: ``([], maturity, step_days)``.
    """
    val = as_date(valuation_date)
    mat = as_date(maturity)
    step_days = max(1, round(YEAR_DAYS / freq))
    dates, d = [], mat
    while d >= val:
        dates.append(d)
        d = d - dt.timedelta(days=step_days)
    dates.reverse()
    return dates, d, step_days
