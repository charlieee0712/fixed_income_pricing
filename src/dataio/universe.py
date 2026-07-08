"""Deterministic corporate-bond universe pipeline — the MECE funnel.

From the master ``Fixed Income`` holdings + the ``Corporate Bonds`` terms tab, build the
canonical priceable universe and a per-bond exclusion log. Every dropped bond gets exactly
ONE primary reason, assigned by the LOCKED priority (PROJECT_STATUS §3.2):

    terms-unavailable  ->  defaulted  ->  no-rating
        ->  structured/floating  ->  callable  ->  matured

Layer A (join, rating, security type) is date-independent; Layer B (matured) depends on the
valuation date, so changing the date only re-runs the last classifier. ``canonical`` =
plain-fixed, rated, non-callable, held, not matured.
"""
from __future__ import annotations

import pandas as pd

from credit.ratings import DEFAULTED, NO_RATING, classify
from dataio import coupon_types as ct
from dataio.loaders import (
    CORP_SUBCATEGORY,
    GOLDEN_FIELDS,
    load_corporate_terms,
    load_master,
)

# Exclusion reasons in LOCKED priority order (highest precedence first). ``canonical`` is the
# kept set, not an exclusion.
REASON_PRIORITY = (
    "terms-unavailable",
    "defaulted",                # rating-defaulted (D/SD)
    "no-rating",
    "excluded-structured",      # Mario-excluded coupon class: pass-through / amortizing / na / unknown
    "floating",                 # floating + fixed-to-reset -> forward-projection engine (Step 4)
    "special-fixed",            # stepped / step-up / zero / defaulted-coupon -> Step 3 engines
    "callable",
    "matured",
)
FUNNEL_ORDER = ("canonical",) + REASON_PRIORITY

# A "make-whole" call (call date within this many days of maturity) has ~zero option value, so the
# bond is routed to VANILLA pricing (enters canonical) rather than excluded as callable — the embedded
# option is not economically exercised for value (WORKLOG 2026-07-02). Genuine calls (gap > this) stay
# excluded as `callable` and are priced on the v2 lattice (scripts/callable_risk.py).
MAKE_WHOLE_MAX_GAP_DAYS = 7


def _present(v):
    """True when a cell carries a real value (not None / NaN / blank / 'NULL')."""
    return not (v is None or pd.isna(v) or str(v).strip() in ("", "NULL"))


def _corporate_uniques(master):
    """Master corporate rows deduped to one record per Asset ID. Par value is **summed**
    across duplicate holdings (one bond held in several accounts); other fields take the
    first non-null."""
    corp = master[
        master["sub_category"].astype("string").str.strip() == CORP_SUBCATEGORY
    ].copy()
    corp["par_value"] = pd.to_numeric(corp["par_value"], errors="coerce")
    agg = {c: "first" for c in corp.columns if c != "asset_id"}
    agg["par_value"] = "sum"
    uniq = corp.groupby("asset_id", as_index=False, dropna=False).agg(agg)
    return corp, uniq


def build_universe(master, terms, val_date):
    """Build the universe.

    Returns ``(canonical, excluded, funnel, extras)``:
      * ``canonical`` — DataFrame of priceable bonds (golden marks stripped).
      * ``excluded``  — DataFrame with one ``primary_reason`` per dropped bond.
      * ``funnel``    — pandas Series, MECE count per stage (sums to unique corporates).
      * ``extras``    — dict of cross-check counts + ``tab_only`` ids + a ``reconciliation``
                        frame (asset_id/isin + custodian gold_* marks).
    """
    val_ts = pd.Timestamp(val_date)
    _, uniq = _corporate_uniques(master)

    # ---- terms join: Asset ID <-> Asset Code, tab deduped by Asset Code ----
    terms_u = terms.dropna(subset=["asset_id"]).drop_duplicates(subset="asset_id", keep="first")
    tab_ids = set(terms_u["asset_id"].astype(str))
    master_ids = set(uniq["asset_id"].astype(str))
    merged = uniq.merge(
        terms_u[["asset_id", "coupon", "coupon_type", "freq", "maturity",
                 "coupon_formula", "coupon_formula2"]],
        on="asset_id",
        how="left",
    )

    # ---- rating via the locked notch-map (S&P primary, Moody fallback, default precedence) ----
    classified = [classify(sp, mo) for sp, mo in zip(merged["sp_rating"], merged["moody_rating"])]
    merged["rating_bucket"] = [c[0] for c in classified]
    merged["rating_source"] = [c[1] for c in classified]

    # ---- per-bond classifiers ----
    merged["matched"] = merged["asset_id"].astype(str).isin(tab_ids)
    merged["is_callable"] = merged["call_date"].map(_present)
    merged["is_fixed"] = (
        merged["coupon_type"].astype("string").str.strip().str.lower().eq("fixed")
    )
    maturity = pd.to_datetime(merged["maturity"], errors="coerce")
    merged["maturity"] = maturity
    merged["is_matured"] = maturity.notna() & (maturity < val_ts)
    # make-whole call (call date ~ maturity) -> option value ~ 0 -> price as vanilla (canonical). A NaN
    # gap (missing call date or maturity) -> not make-whole -> the bond stays callable-excluded.
    call_date = pd.to_datetime(merged["call_date"], errors="coerce")
    gap_days = (maturity - call_date).dt.days
    merged["is_make_whole"] = merged["is_callable"] & gap_days.le(MAKE_WHOLE_MAX_GAP_DAYS)

    # ---- coupon-structure class + engine route (Mario 2026-07-08: read Coupon_Formula2, route by
    #      type). Data-driven; supersedes the coupon_type(E) "fixed" test for canonical membership. ----
    merged["coupon_class"] = merged["coupon_formula2"].map(ct.classify_coupon_formula)
    merged["route"] = merged["coupon_class"].map(ct.route_for)

    # ---- single primary reason by LOCKED priority ----
    def _reason(r):
        if not r["matched"]:
            return "terms-unavailable"
        if r["rating_bucket"] == DEFAULTED:
            return "defaulted"
        if r["rating_bucket"] == NO_RATING:
            return "no-rating"
        cc = r["coupon_class"]                             # data-driven from Coupon_Formula2
        if cc in ct.EXCLUDED_CLASSES:                      # pass-through / amortizing / na / unknown
            return "excluded-structured"
        if cc in (ct.FLOATING, ct.FIXED_TO_RESET):         # -> forward-projection engine (Step 4)
            return "floating"
        if cc in (ct.STEPPED, ct.STEP_UP, ct.ZERO, ct.DEFAULTED):   # -> Step 3 engines
            return "special-fixed"
        # cc == F (plain fixed): the vanilla path — genuine call / maturity still apply
        if r["is_callable"] and not r["is_make_whole"]:   # make-whole falls through to vanilla/canonical
            return "callable"
        if r["is_matured"]:
            return "matured"
        return "canonical"

    merged["primary_reason"] = merged.apply(_reason, axis=1)

    canonical = merged[merged["primary_reason"] == "canonical"].copy()
    excluded = merged[merged["primary_reason"] != "canonical"].copy()

    counts = merged["primary_reason"].value_counts()
    funnel = pd.Series({k: int(counts.get(k, 0)) for k in FUNNEL_ORDER}, name="count")
    funnel["TOTAL_unique_corporates"] = int(len(merged))

    # ---- cross-checks (raw, pre-priority) + side outputs ----
    in_matched = merged["matched"]
    extras = {
        "matched": int(in_matched.sum()),
        "master_only": int((~in_matched).sum()),
        "tab_only_count": len(tab_ids - master_ids),
        "tab_only_ids": sorted(tab_ids - master_ids),
        "rating_covered": int((~merged["rating_bucket"].isin([DEFAULTED, NO_RATING])).sum()),
        "rating_defaulted": int((merged["rating_bucket"] == DEFAULTED).sum()),
        "rating_no_rating": int((merged["rating_bucket"] == NO_RATING).sum()),
        "raw_non_fixed_in_matched": int((in_matched & ~merged["is_fixed"]).sum()),
        "raw_callable_in_matched": int((in_matched & merged["is_callable"]).sum()),
        "make_whole_total": int(merged["is_make_whole"].sum()),
        "make_whole_as_vanilla": int((merged["is_make_whole"] & (merged["primary_reason"] == "canonical")).sum()),
        # coupon-structure classification (Mario 2026-07-08). ``coupon_class_pivot`` = raw 676-row tab
        # pivot -> reconciles to Mario's targets exactly; ``route_counts`` = engine assignment over the 732.
        "coupon_class_pivot": {
            k: int(v)
            for k, v in terms["coupon_formula2"].map(ct.classify_coupon_formula).value_counts().items()
        },
        "route_counts": {k: int(v) for k, v in merged["route"].value_counts().items()},
        "reconciliation": merged[
            ["asset_id", "isin"] + [c for c in GOLDEN_FIELDS if c in merged.columns]
        ].copy(),
    }

    # golden marks never travel with the pricing inputs
    canonical = canonical.drop(columns=[c for c in GOLDEN_FIELDS if c in canonical.columns])
    return canonical, excluded, funnel, extras


def build_universe_from_path(path, val_date):
    """Convenience: load the workbook and build the universe in one call."""
    return build_universe(load_master(path), load_corporate_terms(path), val_date)
