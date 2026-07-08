"""Coupon-schedule parsing + schedule-aware cash flows for stepped / step-up / segmented-fixed bonds.

Mario Step 3 (2026-07-08): some corporate bonds have a time-varying but **known** coupon (a step-up
or a date-segmented fixed rate). Their cash flows are deterministic — only the coupon changes on a
schedule — so they price on the ordinary discounting engine once it is fed a coupon time-table
instead of a single rate.

`parse_coupon_schedule` extracts that time-table from the free-text ``Coupon_Formula`` /
``Coupon_Formula2`` cell. String parsing is fragile, so it is isolated here with its own unit tests
and **returns ``None`` (never a guess)** when the cell carries no numeric coupons — e.g.
"Step-up schedule", whose actual steps live only in Bloomberg / the prospectus (a data gap to flag,
exactly like a missing call schedule).

A *schedule* is a list ``[(effective_from | None, rate_decimal), ...]`` sorted by date, where
``None`` = from issuance. ``coupon_at(schedule, date)`` returns the rate in force on ``date`` (the
latest entry whose effective date is <= date). Rates are **DECIMAL** (0.075), matching
``price_bond``'s ``coupon_rate``.
"""
from __future__ import annotations

import datetime as dt
import re

import pandas as pd

_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_DATE = re.compile(r"(\d{1,2})-([A-Za-z]{3,9})-(\d{2,4})")
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _parse_date(day, mon, year):
    """`01-Mar-2006` -> date, or None if the token is not a valid dd-Mon-yyyy."""
    try:
        y = int(year)
        if y < 100:
            y += 2000 if y < 50 else 1900
        return dt.date(y, _MONTHS[mon[:3].lower()], int(day))
    except (KeyError, ValueError):
        return None


def _parse_one(formula):
    if formula is None or (isinstance(formula, float) and pd.isna(formula)):
        return None
    text = str(formula).replace("≥", ">=").replace("≤", "<=")
    rates = [round(float(r) / 100.0, 10) for r in _PCT.findall(text)]
    if not rates:
        return None                                   # no numeric coupon -> caller flags the bond
    dates, seen = [], set()
    for day, mon, year in _DATE.findall(text):
        d = _parse_date(day, mon, year)
        if d is not None and d not in seen:           # the same switch date can appear twice (t< and t>=)
            seen.add(d)
            dates.append(d)
    if len(rates) == 1:
        return [(None, rates[0])]
    if len(rates) == len(dates) + 1:
        # textual order = chronological: rate[0] applies before dates[0], rate[i] from dates[i-1].
        sched = [(None, rates[0])] + [(dates[i], rates[i + 1]) for i in range(len(dates))]
        sched.sort(key=lambda x: (x[0] is not None, x[0] or dt.date.min))
        return sched
    return None                                       # rate/date counts don't line up -> refuse to guess


def parse_coupon_schedule(*formulas):
    """Parse a coupon time-table from one or more free-text formula cells.

    Tries each argument in order (e.g. ``coupon_formula2`` then ``coupon_formula``) and returns the
    first that yields numeric coupons, else ``None``.
    """
    for formula in formulas:
        s = _parse_one(formula)
        if s is not None:
            return s
    return None


def coupon_at(schedule, date):
    """Rate in force on ``date`` = the latest schedule entry whose effective date is <= date."""
    d = pd.Timestamp(date).date()
    rate = schedule[0][1]
    for eff, r in schedule:
        if eff is None or eff <= d:
            rate = r
        else:
            break
    return rate
