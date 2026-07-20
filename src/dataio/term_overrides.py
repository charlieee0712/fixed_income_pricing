"""Security-term overrides — the data layer for terms the URS workbook lacks or mis-states.

Each table is per-bond, sourced from primary documents (prospectuses / 20-F / annual reports —
see ``docs/isin_lookup_2026-07-20.md`` for the per-bond evidence) or from Mario/Bloomberg fills.
Only HIGH-confidence, source-cited terms are written to these files; anything weaker stays a
documented gap. All three tables are OPTIONAL: a missing file means "no overrides" (so the
pipeline still runs on a bare checkout), but a present file with wrong columns raises loudly.

* ``data/coupon_schedules.csv`` — ``asset_id | effective_date | coupon_rate [| source]``.
  A deterministic coupon path for bonds the workbook cannot price numerically (step-up /
  rating-step levels in force / custodian coupon-field errors). Blank ``effective_date`` = from
  issuance; rates are DECIMAL. Grouped into the ``[(date|None, rate), ...]`` schedule that
  :func:`pricing.bond_price.price_bond` consumes; the driver routes any bond present here to
  ``vanilla-schedule`` (the override beats both the free-text parse and the degenerate-zero path).
* ``data/frn_spreads.csv`` — ``asset_id | quoted_margin_bp [| freq | ...]``. The quoted margin
  for FRNs whose formula text carries no number ("EURIBOR + Spread"): the FRN engine then prices
  forward+margin instead of folding the margin into the calibrated OAS. Optional ``freq``
  corrects a wrong custodian payment frequency (e.g. quarterly FRNs recorded as semiannual).
* ``data/make_whole_overrides.csv`` — ``asset_id [| ...]``. Securities DOCUMENTED as carrying a
  continuous make-whole call only (no fixed-price/par call): their custodian "next call" sits far
  from maturity, so :data:`dataio.universe.MAKE_WHOLE_MAX_GAP_DAYS` cannot recognise them;
  ``build_universe(..., make_whole_overrides=...)`` routes them make-whole -> vanilla instead of
  callable -> lattice.
* ``data/hybrid_switch_terms.csv`` — fixed-to-float hybrid terms (fixed rate/freq, switch date,
  post-switch index+margin, call, maturity or perp) for :mod:`pricing.hybrid`. A row WITH a margin
  prices on the fixed-then-float engine; a row WITHOUT one BT-marks the bond
  ``hybrid-margin-unavailable`` (the Mario/Bloomberg request list).
"""
from __future__ import annotations

import datetime as dt
import os

import pandas as pd


def _read_optional(path, required):
    """Read an optional override CSV: missing file -> None; missing column -> ValueError."""
    if path is None or not os.path.exists(path):
        return None
    df = pd.read_csv(path, dtype={"asset_id": str})
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing required column(s) {missing}; have {list(df.columns)}")
    return df


def load_coupon_schedule_overrides(path):
    """``data/coupon_schedules.csv`` -> ``{asset_id: [(effective_date|None, rate_decimal), ...]}``.

    Blank/NaN ``effective_date`` = base rate (from issuance). Schedules sort base-first then by
    date — the exact shape :func:`pricing.coupon_schedule.coupon_at` expects.
    """
    df = _read_optional(path, ("asset_id", "effective_date", "coupon_rate"))
    if df is None or df.empty:
        return {}
    out = {}
    for aid, g in df.groupby("asset_id", sort=False):
        entries = []
        for r in g.itertuples():
            raw = r.effective_date
            blank = raw is None or (isinstance(raw, float) and pd.isna(raw)) or str(raw).strip() == ""
            eff = None if blank else pd.Timestamp(raw).date()
            entries.append((eff, float(r.coupon_rate)))
        entries.sort(key=lambda x: (x[0] is not None, x[0] or dt.date.min))
        out[str(aid)] = entries
    return out


def load_frn_spreads(path):
    """``data/frn_spreads.csv`` -> ``{asset_id: {"spread": decimal, "freq": int|None}}``.

    ``quoted_margin_bp`` is in BASIS POINTS in the file (auditable against the prospectus) and
    converted to the decimal the FRN engine takes. ``freq`` (optional column / blank cell) is a
    payment-frequency correction; None = keep the workbook value.
    """
    df = _read_optional(path, ("asset_id", "quoted_margin_bp"))
    if df is None or df.empty:
        return {}
    out = {}
    for r in df.itertuples():
        freq = None
        if "freq" in df.columns:
            f = getattr(r, "freq")
            if not (f is None or (isinstance(f, float) and pd.isna(f)) or str(f).strip() == ""):
                freq = int(f)
        out[str(r.asset_id)] = {"spread": float(r.quoted_margin_bp) / 1e4, "freq": freq}
    return out


def load_make_whole_overrides(path):
    """``data/make_whole_overrides.csv`` -> set of asset_ids documented make-whole-only."""
    df = _read_optional(path, ("asset_id",))
    if df is None or df.empty:
        return set()
    return {str(a) for a in df["asset_id"].dropna()}


def _blank(v):
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ""


def load_hybrid_terms(path):
    """``data/hybrid_switch_terms.csv`` -> ``{asset_id: {...}}`` for the fixed-then-float engine.

    Per bond: ``fixed_rate`` (decimal), ``fixed_freq``, ``switch_date`` (date), ``margin``
    (decimal, from ``float_margin_bp``; **None = the post-switch margin is a documented data gap**
    -> the driver BT-marks the bond ``hybrid-margin-unavailable`` instead of half-modelling it),
    ``float_freq``, ``maturity`` (date; **None = perpetual** -> driver truncates), ``first_call``
    (date), ``confidence``. Blank cells -> None throughout (the None principle).
    """
    df = _read_optional(path, ("asset_id", "fixed_rate", "fixed_freq", "switch_date",
                               "float_margin_bp", "float_freq", "maturity"))
    if df is None or df.empty:
        return {}
    out = {}
    for r in df.itertuples():
        out[str(r.asset_id)] = {
            "fixed_rate": None if _blank(r.fixed_rate) else float(r.fixed_rate),
            "fixed_freq": None if _blank(r.fixed_freq) else int(r.fixed_freq),
            "switch_date": None if _blank(r.switch_date) else pd.Timestamp(r.switch_date).date(),
            "margin": None if _blank(r.float_margin_bp) else float(r.float_margin_bp) / 1e4,
            "float_freq": None if _blank(r.float_freq) else int(r.float_freq),
            "maturity": None if _blank(r.maturity) else pd.Timestamp(r.maturity).date(),
            "first_call": (None if "first_call_date" not in df.columns or _blank(r.first_call_date)
                           else pd.Timestamp(r.first_call_date).date()),
            "confidence": (None if "confidence" not in df.columns or _blank(r.confidence)
                           else str(r.confidence)),
        }
    return out
