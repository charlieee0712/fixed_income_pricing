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
the real schedule drops straight in with zero code change. The file holds client asset_ids, so it is
git-ignored (``data/`` in .gitignore) and lives on the server only. Seed it with
``scripts/init_call_schedules.py``.
"""
from __future__ import annotations

import pandas as pd

DAYS_PER_YEAR = 365.25
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


def to_lattice_schedule(date_entries, val_date, days_per_year=DAYS_PER_YEAR):
    """Convert ``[(call_date, price), ...]`` -> ``[(time_years, price), ...]`` relative to ``val_date``
    (times clamped at 0 = already callable at the valuation date), sorted by time — the form
    :meth:`pricing.lattice.ShortRateLattice.call_array` consumes. Centralises the day-count convention
    so the lattice stays date-agnostic (it already works purely in years from t0)."""
    val_ts = pd.Timestamp(val_date)
    entries = [(max(0.0, (pd.Timestamp(d) - val_ts).days / days_per_year), float(p)) for d, p in date_entries]
    return sorted(entries)
