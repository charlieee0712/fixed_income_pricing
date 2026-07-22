"""Phase-2 asset classes (Mario 2026-07-20): Government Agencies / Guaranteed (FDIC-TLGP) /
Index-Linked government bonds — master-sheet loader + per-class mini-universe with engine routes.

Findings basis: ``docs/phase2_inventory_2026-07-20.md`` (read-only recon) + the 2026-07-22 build
recon. Everything here is data-driven off the master ``Fixed Income`` sheet only — none of the
three classes has a terms tab (the corporate-tab join does not apply); the coupon carrier is
**BG "Income rate"** (validated vs the description figures), payment frequency **CB**, maturity
**BW**, call date **AB**.

Class routing (decisions of 2026-07-22, evidence in ``docs/phase2_methods_2026-07-22.md``):
  * **agency** (42 rows / 39 unique) —
      - ``zero``: the 2 Resolution Funding CPN STRIPS (BG ~ 1e-5, CB blank) -> degenerate vanilla.
      - ``callable-lattice``: the 5 with a master AB call date (all genuine gaps, 4.7-20y) ->
        BDT lattice, Bermudan par call @100 from AB (the industry-standard agency-debenture
        assumption — unlike corporate make-whole, par call is the CORRECT default here, not a
        placeholder). Schedule rows live in ``data/call_schedules.csv`` (the single call-terms
        source); sigma = the house 0.15.
      - ``call-passed-vanilla``: 4 whose description shows a maturity/call date PAIR with the call
        in 2006 — passed UNEXERCISED (custodian AB agrees: blank) -> a bullet now; priced vanilla,
        flagged (evidence beats a terms-unavailable mark).
      - ``cmo-tranche``: TNTD04733316 "FHLMC SER 3122 CL ZB" — a REMIC Z-tranche misfiled as an
        agency debenture (Monthly freq, ISIN NULL, $72k). BT-marked for the CMO phase, NOT
        force-priced as a 27y bullet (the Sempra lesson).
      - else ``vanilla`` (FNMA/FHLB/FHLMC bullets + quasi-sovereigns KDB/KEXIM/PEMEX/HQ/Israel/
        KfW/EIB/Farmer Mac; EUR 2 / JPY 1 / AUD 1 route via ``ZeroCurve.from_currency``).
  * **guaranteed** (11 / 9) — all FDIC-TLGP crisis paper -> ``vanilla``, ``group`` =
    ``TLGP-guaranteed``: reported as its OWN bucket, never in bank rating buckets (the credit is
    the FDIC guarantee — the master even rates them AAA/Aaa; a bank-name bucket would distort the
    by-rating table).
  * **linker** (16 / 15) — ``ilb`` where the per-bond index ratio is recoverable as
    ``BG / description real coupon`` (14 TIPS + JGBi; ratios 1.008-1.31, a sensible CPI-accretion
    pattern); the KTBi shows BG == coupon exactly and no description coupon -> the Korea
    indexation convention is unverified -> ``ilb-indexation-unverified`` (BT mark, Mario list).

Data-quality: duplicate asset-ids across accounts are deduped with par (and market value / book
cost) **summed** — with the summed MV the ``BT == BU/par*100`` identity is exact per unique id.
Negative-par rows (shorts) net into the sum and set ``is_short``; the master ``Y``
Asset/Liability indicator does NOT discriminate them (uniformly 'A' — verified 2026-07-22; the
10 negative rows in this book are all Govt-MBS TBA-style hedges, none in these three classes).
"""
from __future__ import annotations

import re

import pandas as pd

from dataio.loaders import GOLDEN_FIELDS, MASTER_COLS, _read_sheet

MASTER_SHEET = "Fixed Income"

# Master letters beyond the corporate set (recon 2026-07-22; header names verified on 47).
PHASE2_MASTER_COLS = {
    **MASTER_COLS,
    "Q": "desc_short",            # 'Asset description - short'
    "T": "desc_long",             # 'Asset description - long'
    "Y": "asset_liability",       # 'Asset/Liability Indicator' (uniformly 'A'; kept as audit)
    "BG": "income_rate",          # 'Income rate' = the coupon carrier (percent; linkers: x ratio)
    "BH": "income_rate_ann",      # 'Income rate - annualized'
    "BX": "orig_face",            # 'Original face value' (empty for the MBS rows)
    "CA": "paydown_factor",       # 'Paydown factor' (== Govt MTGE tab BZ where both exist)
    "CB": "pay_freq",             # 'Payment frequency' (text)
    "AQ": "dur_eff_custodian",    # 'Duration - effective' (free external cross-check)
}

SUBCATS = {
    "agency": "Government Agencies",
    "guaranteed": "Guaranteed Fixed Income",
    "linker": "Index Linked Government Bonds",
    "govt_mbs": "Government Mortgage Backed Securities",   # counted only; engine awaits Bloomberg
}

FREQ_FROM_TEXT = {"Semi-Annually": 2, "Annually": 1, "Quarterly": 4, "Monthly": 12}

ZERO_COUPON_MAX_PCT = 0.01        # BG below this (percent) = zero-coupon (the strips carry 1e-5)
RATIO_SANITY = (0.9, 1.6)         # plausible 2009 index-ratio window for held vintages
MAKE_WHOLE_MAX_GAP_DAYS = 7       # same guard as the corporate universe (none trigger here)

# description parsing (the None principle: no number -> None, never a guess)
_CPN_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_CPN_DUE = re.compile(r"(\d+(?:\.\d+)?)\s+DUE\b", re.I)
_DATE_TOKEN = re.compile(r"\d{1,2}[-/^]\d{1,2}[-/^]\d{2,4}")
_DECIMAL = re.compile(r"\d+\.\d+")
# "05-12-2020/05-12-2010" — the agency maturity/call date-pair notation
_DATE_PAIR = re.compile(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\s*/\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}")
_CMO_CLASS = re.compile(r"\bSER\b.{0,12}\bCL\b", re.I)     # "SER 3122 CL ZB" = a REMIC class


def parse_desc_coupon(*texts):
    """Coupon rate in PERCENT parsed from custodian description text, or ``None``.

    Order: an explicit ``x%`` figure; then ``x DUE ...`` (the TIPS style: "2.00 DUE 07-15-2014");
    then the first standalone decimal that is not part of a date token ("FHLB ... 5.53
    11-03-2014"). Values outside (0, 25) are rejected. No number -> ``None`` (a data gap to flag).
    """
    for s in texts:
        if s is None or (isinstance(s, float) and pd.isna(s)):
            continue
        s = str(s)
        for pat in (_CPN_PCT, _CPN_DUE):
            m = pat.search(s)
            if m and 0.0 < float(m.group(1)) < 25.0:
                return float(m.group(1))
        no_dates = _DATE_TOKEN.sub(" ", s)
        for m in _DECIMAL.finditer(no_dates):
            if 0.0 < float(m.group(0)) < 25.0:
                return float(m.group(0))
    return None


def load_master_phase2(path):
    """The master ``Fixed Income`` sheet with the phase-2 column superset (all sub-categories)."""
    return _read_sheet(path, MASTER_SHEET, PHASE2_MASTER_COLS)


def _present(v):
    return not (v is None or pd.isna(v) or str(v).strip() in ("", "NULL"))


def _uniques(cls_rows):
    """One record per Asset ID: par / market value / book cost SUMMED across duplicate account
    legs (so BT == mv/par*100 holds per id), other fields first non-null."""
    c = cls_rows.copy()
    for col in ("par_value", "gold_mkt_value", "book_cost"):
        c[col] = pd.to_numeric(c[col], errors="coerce")
    agg = {col: "first" for col in c.columns if col != "asset_id"}
    for col in ("par_value", "gold_mkt_value", "book_cost"):
        agg[col] = "sum"
    n = c.groupby("asset_id").size().rename("n_rows")
    u = c.groupby("asset_id", as_index=False).agg(agg).merge(n, on="asset_id")
    return u


def _route_agency(r):
    cpn = r["coupon_pct"]
    if pd.notna(cpn) and cpn < ZERO_COUPON_MAX_PCT:
        return "zero"
    desc = f"{r['desc_short']} {r['desc_long']}"
    if r["has_call"]:
        gap = (pd.Timestamp(r["maturity"]) - pd.Timestamp(r["call_date"])).days \
            if _present(r["call_date"]) and pd.notna(r["maturity"]) else None
        if gap is not None and gap <= MAKE_WHOLE_MAX_GAP_DAYS:
            return "vanilla"                       # make-whole guard (corporate rule; none trigger)
        return "callable-lattice"
    if str(r["pay_freq"]).strip() == "Monthly" and _CMO_CLASS.search(desc):
        return "cmo-tranche"
    if _DATE_PAIR.search(desc):
        return "call-passed-vanilla"               # date pair, no AB -> call passed unexercised
    return "vanilla"


def build_phase2_universe(master):
    """Per-class mini-universe for the three phase-2 classes (MBS counted only).

    Returns ``(bonds, recon, counts)``:
      * ``bonds`` — one row per unique asset id, classes agency/guaranteed/linker, with
        ``asset_class``/``group``/``route``/``flag``, terms (coupon decimal, freq int, maturity,
        call_date), position fields (par summed, ``is_short``), and for linkers
        ``real_coupon`` (decimal) + ``index_ratio0`` (= BG / description coupon @ the file date).
        Custodian golden marks are STRIPPED (input/truth separation, as the corporate universe).
      * ``recon`` — asset_id + gold_price / gold_mkt_value (summed) / gold_ytm.
      * ``counts`` — per class: rows, unique, negative-par rows, route counts (golden-testable).
    """
    m = master.copy()
    m["sub"] = m["sub_category"].astype("string").str.strip()

    frames, counts = [], {}
    for cls, sub in SUBCATS.items():
        rows = m[m["sub"] == sub]
        counts[cls] = {"rows": int(len(rows)), "unique": int(rows["asset_id"].nunique()),
                       "negative_par_rows": int((pd.to_numeric(rows["par_value"], errors="coerce") < 0).sum())}
        if cls == "govt_mbs":                      # inventoried; engine awaits the Bloomberg pull
            continue
        u = _uniques(rows)
        u["asset_class"] = cls
        u["coupon_pct"] = pd.to_numeric(u["income_rate"], errors="coerce")
        u["freq"] = u["pay_freq"].astype("string").str.strip().map(FREQ_FROM_TEXT)
        u["maturity"] = pd.to_datetime(u["maturity_master"], errors="coerce")
        u["has_call"] = u["call_date"].map(_present)
        u["call_date"] = pd.to_datetime(u["call_date"].where(u["has_call"]), errors="coerce")
        u["is_short"] = u["par_value"] < 0

        if cls == "agency":
            u["group"] = "agency"
            u["route"] = u.apply(_route_agency, axis=1)
            u["real_coupon"] = pd.NA
            u["index_ratio0"] = pd.NA
        elif cls == "guaranteed":
            u["group"] = "TLGP-guaranteed"         # own bucket: the credit is the FDIC guarantee
            u["route"] = "vanilla"
            u["real_coupon"] = pd.NA
            u["index_ratio0"] = pd.NA
        else:                                      # linker
            u["group"] = "linker"
            u["real_coupon_pct"] = [parse_desc_coupon(t, q) for t, q in zip(u["desc_long"], u["desc_short"])]
            u["index_ratio0"] = u["coupon_pct"] / u["real_coupon_pct"]
            ok = u["real_coupon_pct"].notna() & u["index_ratio0"].between(*RATIO_SANITY)
            u["route"] = "ilb-indexation-unverified"
            u.loc[ok, "route"] = "ilb"
            u.loc[u["real_coupon_pct"].notna() & ~u["index_ratio0"].between(*RATIO_SANITY),
                  "route"] = "ilb-ratio-implausible"
            u["real_coupon"] = u["real_coupon_pct"] / 100.0
        frames.append(u)

    bonds = pd.concat(frames, ignore_index=True)
    bonds["coupon"] = bonds["coupon_pct"] / 100.0                    # decimal
    bonds.loc[bonds["route"] == "zero", "coupon"] = 0.0              # the 1e-5 strips are zeros

    for cls in ("agency", "guaranteed", "linker"):
        sel = bonds[bonds["asset_class"] == cls]
        counts[cls]["routes"] = {k: int(v) for k, v in sel["route"].value_counts().items()}
        counts[cls]["shorts"] = int(sel["is_short"].sum())

    recon = bonds[["asset_id", "asset_class"] + [c for c in GOLDEN_FIELDS if c in bonds.columns]].copy()
    bonds = bonds.drop(columns=[c for c in GOLDEN_FIELDS if c in bonds.columns])
    return bonds, recon, counts


def build_phase2_from_path(path):
    return build_phase2_universe(load_master_phase2(path))
