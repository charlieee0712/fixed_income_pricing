"""Call / put schedule table — the single source of embedded-option exercise terms.

Mario (2026-07-03) requires the lattice to read its exercise schedule from a standalone DATA table,
never from hard-coded logic, so that swapping in a real (Bloomberg-sourced) schedule is a data-only
change. This module loads that table; :class:`pricing.lattice.ShortRateLattice` consumes the resulting
schedule and builds the exercise array. Data (this CSV) and logic (the lattice) stay separated — there
is no par-call baked into the engine.

File: ``data/call_schedules.csv`` — columns ``asset_id | call_date | call_price``. One row per call
date; MULTIPLE rows per asset express a step-function schedule (e.g. callable @102 in 2011, @101 in
2012, @100 in 2013+). Today each genuine callable seeds a single row (``call_date`` = master col AB,
``call_price`` = 100 = the par-call v1 assumption Mario approved); the schema is already multi-row, so
the real schedule drops straight in with zero code change. Tracked under ``data/`` (client data is
committed in-repo since 2026-07-08; the repo stays private). Seed it with
``scripts/init_call_schedules.py``. Documented make-whole-only bonds do NOT belong here — they go in
``data/make_whole_overrides.csv`` (``dataio.term_overrides``) and route make-whole -> vanilla.
"""
from __future__ import annotations

import pandas as pd

from pricer.core.utils.dates import exercise_schedule_times

REQUIRED_COLUMNS = ("asset_id", "call_date", "call_price")


def load_call_schedules(path):
    """Read the call-schedule table.

    Returns ``{asset_id: [(call_date: Timestamp, call_price: float), ...]}`` with each list sorted by
    (date, price). Multiple rows per ``asset_id`` => a multi-date Bermudan schedule. Raises if a
    required column is missing (a malformed table must fail loudly, not silently price as a straight).
    """
    df = pd.read_csv(path, dtype={"asset_id": str})
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing required column(s) {missing}; have {list(df.columns)}")
    df["call_date"] = pd.to_datetime(df["call_date"])
    df["call_price"] = pd.to_numeric(df["call_price"], errors="raise")
    out = {}
    for aid, g in df.groupby("asset_id", sort=False):
        out[str(aid)] = sorted((r.call_date, float(r.call_price)) for r in g.itertuples())
    return out


def to_lattice_schedule(date_entries, val_date):
    """Convert ``[(call_date, price), ...]`` -> ``[(time_years, price), ...]`` relative to
    ``val_date``: times clamped at 0 (already callable today), sorted by time — the form
    ``pricing.lattice.ShortRateLattice.call_array`` consumes. The lattice stays date-agnostic;
    it works purely in years from t0.

    The conversion is :func:`pricer.core.utils.dates.exercise_schedule_times`, shared with
    ``core.pricing.tree.schedule_times``. This signature USED to carry a ``days_per_year``
    argument defaulting to 365.25 while the coupon grid ran on ACT/364. Both production
    drivers passed ``364.0`` explicitly, so no shipped number was ever wrong — but a new
    caller taking the default would have silently placed exercise dates on a different axis
    than the coupons they are compared against, with no error and no visible symptom. The
    argument is gone rather than re-defaulted: the convention is not a caller's choice.
    """
    return exercise_schedule_times(val_date, date_entries)
