"""Inflation data: measured price indices, and the index ratios derived from them.

Three tables, deliberately separate, because they are three different kinds of fact:

``data/cpi_index.csv``           MEASURED. A published price index, per country, per month.
``data/index_ratios.csv``        DERIVED per security, with its convention recorded.
``data/inflation_assumption.csv``ASSUMED. A forward view; see the warning below.

Keeping them apart is the same discipline as everywhere else in this project: a measured
series, a derived security term and a forecast have different provenance, different
confidence and different consumers, and one file holding all three would let a forecast be
read as an observation.

Every file is optional. A missing file means no data, never a default — the same contract
as ``dataio.term_overrides``.

⚠️ **The forward assumption does not change any number, and this is arithmetic, not an
omission.** Pricing an inflation-linked bond with a constant inflation assumption ``pi`` at
spread ``s`` is identical to pricing it with zero inflation at ``s - ln(1+pi)``, because
``(1+pi)**t`` is exactly ``exp(t*ln(1+pi))`` and folds into the discount exponent. Measured
on the real book: at 2% every calibrated spread moved by exactly 198.0263 bp = ln(1.02),
the fourteen bonds' shifts agreed to 2.7e-07 bp, and price, duration, DV01 and convexity
did not move at all. A constant assumption and a flat spread are ONE knob. Breaking that
degeneracy needs a term structure of inflation, or the deflation floor — both v2.

So the value in this module is the FIRST table, not the third: the index ratio scales every
cash flow and the accrued, it was recovered from a free-text parse (``BG / desc_coupon``,
guarded only by a plausibility window), and a 1% error in it moves a published breakeven by
about 6 bp.

The reference-index conventions
-------------------------------
Both are three-month-lagged and linearly interpolated, and they differ in the anchor day —
which is why ``anchor_day`` is a parameter here rather than a constant:

* **US TIPS** — Ref CPI on the 1st of month M is CPI-U NSA for month M-3; other days are
  straight-line interpolated across the month. Index Ratio = Ref CPI(settlement) / Ref CPI
  (dated date). (TreasuryDirect.)
* **Japan JGBi** — the same shape anchored on the **10th**, using the CPI excluding fresh
  food, and the coefficient is rounded to five decimals. (Ministry of Finance.)
"""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import os

#: Lag, in months, from the reference index to the price index it is built from.
DEFAULT_LAG_MONTHS = 3

#: Day of the month on which the reference index equals the lagged price index exactly.
#: 1 for US TIPS, 10 for Japanese JGBi.
DEFAULT_ANCHOR_DAY = 1


def _as_date(value):
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.datetime):
        return value.date()
    text = str(value).strip()[:10]
    return dt.date(int(text[0:4]), int(text[5:7]), int(text[8:10]))


def _shift_months(year, month, back):
    month -= back
    while month <= 0:
        month += 12
        year -= 1
    return year, month


def load_cpi_index(path="data/cpi_index.csv"):
    """Published price indices, by country.

    Inputs
    ------
    1. path : str — the CSV. A missing file yields ``{}``; it is data, not a requirement.

    Returns: ``{country: {(year, month): index_value}}``.

    ⚠️ The values carry whatever base year the source publishes. That is harmless and
    deliberate: an index RATIO is base-invariant, so a rebasing cannot change a price.
    """
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            country = (row.get("country") or "").strip().upper()
            period = (row.get("period") or "").strip()
            value = (row.get("index_value") or "").strip()
            if not country or not period or not value:
                continue
            year, month = period.split("-")[:2]
            out.setdefault(country, {})[(int(year), int(month))] = float(value)
    return out


def reference_index(series, date, lag_months=DEFAULT_LAG_MONTHS,
                    anchor_day=DEFAULT_ANCHOR_DAY):
    """The reference index for a calendar date, by the published convention.

    Inputs
    ------
    1. series     : ``{(year, month): value}`` — one country's index, from
       :func:`load_cpi_index`.
    2. date       : the calendar date.
    3. lag_months : int — months between the reference index and the price index (3 for
       both TIPS and JGBi).
    4. anchor_day : int — the day on which the reference index equals the lagged index
       exactly: **1** for US TIPS, **10** for Japanese JGBi.

    Returns: float — the reference index.

    Raises ``KeyError`` naming the missing month rather than interpolating past the end of
    the data, because a silently extrapolated index ratio is wrong in a way nothing checks.
    """
    date = _as_date(date)
    year, month = date.year, date.month
    if date.day < anchor_day:                      # still inside the previous anchor period
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    start = dt.date(year, month, min(anchor_day, calendar.monthrange(year, month)[1]))
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    end = dt.date(ny, nm, min(anchor_day, calendar.monthrange(ny, nm)[1]))

    lo_key = _shift_months(year, month, lag_months)
    hi_key = _shift_months(ny, nm, lag_months)
    for key in (lo_key, hi_key):
        if key not in series:
            raise KeyError(f"no index value for {key[0]}-{key[1]:02d}; "
                           f"the reference index for {date} cannot be built")
    lo, hi = series[lo_key], series[hi_key]
    span = (end - start).days
    return lo + (date - start).days / span * (hi - lo)


def index_ratio(series, dated_date, settlement, lag_months=DEFAULT_LAG_MONTHS,
                anchor_day=DEFAULT_ANCHOR_DAY, decimals=None):
    """Index ratio = reference index at settlement / reference index at the dated date.

    Inputs
    ------
    1. series      : one country's index.
    2. dated_date  : the security's dated date — the divisor's date.
    3. settlement  : the date the ratio applies to.
    4-5. lag_months / anchor_day : as :func:`reference_index`.
    6. decimals    : int | None — round to this many places. Japan's Ministry of Finance
       publishes the coefficient rounded to **5**; TreasuryDirect does not round, so
       ``None`` leaves it alone.

    Returns: float.
    """
    ratio = (reference_index(series, settlement, lag_months, anchor_day)
             / reference_index(series, dated_date, lag_months, anchor_day))
    return ratio if decimals is None else round(ratio, decimals)


def load_index_ratios(path="data/index_ratios.csv"):
    """Per-security index ratios that OVERRIDE the custodian-derived recovery.

    Inputs
    ------
    1. path : str — the CSV. Missing file yields ``{}``.

    Returns: ``{asset_id: {"index_ratio": float, "ratio_date": str, "dated_date": str,
    "convention": str, "source": str, "status": str, "as_of": str, "note": str}}``.

    ⚠️ ``status`` is carried, never defaulted to something reassuring. Every row sourced
    from the public web is ``provisional``: it is an interim value under Mario's standing
    rule that web-sourced terms are fine to work with and lose to Bloomberg on arrival,
    with the difference logged. An unrecognised status is refused rather than assumed —
    the same rule ``dataio.call_schedules`` applies to exercise terms.
    """
    allowed = {"provisional", "confirmed"}
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            asset = (row.get("asset_id") or "").strip()
            raw = (row.get("index_ratio") or "").strip()
            if not asset or not raw:
                continue
            status = (row.get("status") or "provisional").strip().lower()
            if status not in allowed:
                raise ValueError(f"index ratio for {asset} has status {status!r}; "
                                 f"expected one of {sorted(allowed)}")
            ratio = float(raw)
            if ratio <= 0.0:
                raise ValueError(f"index ratio for {asset} must be > 0; got {ratio!r}")
            out[asset] = {"index_ratio": ratio, "status": status,
                          "ratio_date": (row.get("ratio_date") or "").strip(),
                          "dated_date": (row.get("dated_date") or "").strip(),
                          "convention": (row.get("convention") or "").strip(),
                          "source": (row.get("source") or "").strip(),
                          "as_of": (row.get("as_of") or "").strip(),
                          "note": (row.get("note") or "").strip()}
    return out


def load_inflation_assumptions(path="data/inflation_assumption.csv"):
    """Forward inflation assumptions, per currency.

    Inputs
    ------
    1. path : str — the CSV. Missing file yields ``{}``.

    Returns: ``{currency: {"inflation_pct": float, "source": str, "status": str, ...}}``.

    ⚠️ **Nothing in production reads this yet, on purpose.** A constant assumption cannot
    change a price, a spread that matters, a duration or a convexity — see the module
    docstring for the measurement. The table exists so the field is registered and the
    shape is agreed; it becomes load-bearing when the engine gains a term structure of
    inflation or the deflation floor, and not before. Reporting it as usable today would
    be the sort of claim this project checks rather than makes.
    """
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            ccy = (row.get("currency") or "").strip().upper()
            raw = (row.get("inflation_pct") or "").strip()
            if not ccy or not raw:
                continue
            out[ccy] = {"inflation_pct": float(raw),
                        "basis": (row.get("basis") or "").strip(),
                        "source": (row.get("source") or "").strip(),
                        "status": (row.get("status") or "provisional").strip().lower(),
                        "as_of": (row.get("as_of") or "").strip(),
                        "note": (row.get("note") or "").strip()}
    return out
