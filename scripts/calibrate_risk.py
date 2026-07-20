"""Calibrate per-bond implied OAS from custodian BT, compute numerical risk metrics, and emit a
by-rating review table — for the canonical corporate universe @ a valuation date.

Each bond is priced on its OWN-currency curve (USD/EUR/GBP), the implied OAS is solved so the model
clean price == BT, and effective duration / DV01 / convexity are bumped off the calibrated model.

Flagging (see `pricing.calibrate.near_maturity`):
  * `near-maturity` — < MIN_YEARS to maturity: implied OAS is unreliable (tiny price gap ÷ a
    near-zero horizon annualises to a huge/negative spread). **Excluded** from the by-rating medians.
  * `recovery-plug`  — BT < DISTRESS_BT: the implied OAS is a calibration plug to a recovery-based
    price, **NOT an economic credit spread**. Kept in the table but annotated; also reported with a
    distress-excluded median.

If a bond's native curve variant (Annual for freq=1) fails to bootstrap (a non-arbitrage-free par
node — happens for GBP @ 2009-06-10), fall back to the Semiannual variant of the same currency.

Run on server 47 (has data + deps):
    cd ~/fixed_income_pricing && PYTHONPATH=src python3 scripts/calibrate_risk.py
Writes outputs/implied_oas.csv (git-ignored). Data paths overridable via FIP_DATA_DIR / FIP_URS_WB.
"""
import os
import sys

sys.path.insert(0, "src")
import numpy as np
import pandas as pd

from credit.oas import oas_on
from curves.zero_curve import ZeroCurve
from dataio.loaders import load_corporate_terms, load_master
from dataio.universe import build_universe
from pricing.calibrate import implied_oas, near_maturity
from dataio.term_overrides import (load_coupon_schedule_overrides, load_frn_spreads,
                                   load_hybrid_terms, load_make_whole_overrides)
from pricing.coupon_schedule import coupon_at, parse_coupon_schedule
from pricing.hybrid import hybrid_risk_metrics, implied_oas_hybrid
from pricing.frn import frn_risk_metrics, implied_oas_frn, parse_frn_spread
from pricing.risk import risk_metrics

DATA_DIR = os.environ.get("FIP_DATA_DIR", "data")
WB = os.environ.get("FIP_URS_WB", os.path.join(DATA_DIR, "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"))
VAL = os.environ.get("FIP_VAL_DATE", "2009-06-10")
OUT = os.environ.get("FIP_OUT", "outputs/implied_oas.csv")  # per-date override avoids clobbering
OAS_WB = os.environ.get("FIP_OAS_WB", os.path.join(DATA_DIR, "Pricing File.xlsm"))  # index OAS source
# Term-override tables (dataio.term_overrides; evidence in docs/isin_lookup_2026-07-20.md).
# All optional: absent file = no overrides.
SCHED_CSV = os.environ.get("FIP_COUPON_SCHED", os.path.join(DATA_DIR, "coupon_schedules.csv"))
FRN_SPREADS_CSV = os.environ.get("FIP_FRN_SPREADS", os.path.join(DATA_DIR, "frn_spreads.csv"))
MW_CSV = os.environ.get("FIP_MAKE_WHOLE", os.path.join(DATA_DIR, "make_whole_overrides.csv"))
HYBRID_CSV = os.environ.get("FIP_HYBRID_TERMS", os.path.join(DATA_DIR, "hybrid_switch_terms.csv"))
MIN_YEARS = 1.0          # below this remaining maturity -> implied OAS unreliable -> excluded
DISTRESS_BT = 50.0       # below this clean price -> implied OAS is a recovery plug -> flagged, kept
PERP_TRUNC_YEARS = 90    # perpetual reset bonds priced by coupon-continuation to a long truncation
                         # (face PV at 90y is negligible under crisis discount rates; noted per bond)
FREQ_VARIANT = {1: "Annual", 2: "Semiannual"}
# FRN engine only: quarterly is legitimate there (several documented FRNs pay quarterly; the
# custodian freq is corrected via data/frn_spreads.csv). Kept separate so the canonical-loop
# guard (`fr not in FREQ_VARIANT`) is unchanged.
FRN_FREQ_VARIANT = {1: "Annual", 2: "Semiannual", 4: "Quarterly"}
RATING_ORDER = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
# Routes whose implied OAS is a clean, model-repriced spread (feed the by-rating medians). The other
# routes (recovery / schedule-unavailable / zero-structured / excluded-no-data) are BT marks or
# anomalous and are reported but kept out of the medians.
PRICED_ROUTES = {"vanilla", "make-whole-as-vanilla", "vanilla-schedule"}

pd.set_option("display.width", 220)


def _hybrid_route(row, hb, bt, ccy, get_curve):
    """Route a bond with documented fixed-to-float terms (``data/hybrid_switch_terms.csv``).

    Margin known -> the fixed-then-float engine (:mod:`pricing.hybrid`) as the MAIN column +
    price-to-call as a REFERENCE column (the fixed-to-switch bullet — every documented hybrid is
    par-callable at its switch; reset-6 dual-column convention: for a deep-discount name the market
    prices EXTENSION, so a to-call OAS is spurious). Margin missing -> BT-mark
    ``hybrid-margin-unavailable`` (the Mario/Bloomberg list) — never half-modelled.
    """
    if hb.get("margin") is None or hb.get("fixed_rate") is None or hb.get("switch_date") is None:
        row.update(route="hybrid-margin-unavailable",
                   clean=(float(bt) if pd.notna(bt) else np.nan),
                   flag="fixed-to-float structure documented (data/hybrid_switch_terms.csv) but the "
                        "post-switch margin is not public — Mario/Bloomberg list; BT mark")
        return
    if pd.isna(bt) or bt <= 0:
        row.update(route="hybrid-no-data", flag=f"hybrid terms known but no BT (bt={bt})")
        return
    fr_fix = hb.get("fixed_freq") or 2
    fr_flt = hb.get("float_freq") or fr_fix
    variant = FRN_FREQ_VARIANT.get(fr_fix, "Semiannual")
    try:
        curve = get_curve(ccy, variant)
    except Exception as e:
        row.update(route="hybrid-curve-blocked", clean=float(bt),
                   flag=f"hybrid terms known but curve {ccy}/{variant} blocked: {e}")
        return
    perp = hb.get("maturity") is None
    mat = ((pd.Timestamp(VAL) + pd.DateOffset(years=PERP_TRUNC_YEARS)).date() if perp
           else hb["maturity"])
    sw = hb["switch_date"]
    try:
        oas = implied_oas_hybrid(float(bt), VAL, mat, curve, fixed_rate=hb["fixed_rate"],
                                 switch_date=sw, spread=hb["margin"], fixed_freq=fr_fix,
                                 float_freq=fr_flt)
        rm = hybrid_risk_metrics(VAL, mat, curve, oas, fixed_rate=hb["fixed_rate"], switch_date=sw,
                                 spread=hb["margin"], fixed_freq=fr_fix, float_freq=fr_flt)
    except ValueError as e:
        row.update(route="hybrid-no-bracket", clean=float(bt), flag=f"hybrid OAS not bracketable ({e})")
        return
    oas_tc, dur_tc = np.nan, np.nan
    try:
        oas_tc = implied_oas(float(bt), VAL, sw, hb["fixed_rate"], curve, freq=fr_fix)
        dur_tc = risk_metrics(VAL, sw, hb["fixed_rate"], curve, oas_tc, freq=fr_fix)["eff_duration"]
    except ValueError:
        pass
    ttm = np.nan if perp else round((pd.Timestamp(mat) - pd.Timestamp(VAL)).days / 365.25, 3)
    row.update(route="hybrid", coupon=hb["fixed_rate"], freq=fr_fix,
               maturity=(None if perp else mat), ttm=ttm,
               clean=rm["clean"], implied_oas=oas, implied_bp=oas * 1e4,
               eff_dur=rm["eff_duration"], dv01=rm["dv01"], convexity=rm["convexity"],
               next_switch_t=rm["next_switch_t"],
               implied_bp_to_call=(oas_tc * 1e4 if pd.notna(oas_tc) else np.nan),
               eff_dur_to_call=dur_tc, call_date_used=sw,
               flag=(f"fixed-then-float: {hb['fixed_rate'] * 100:.3f}% to {sw}, then fwd+"
                     f"{hb['margin'] * 1e4:.1f}bp"
                     + ("; perp truncated at 90y" if perp else "")
                     + "; price-to-call REFERENCE only"))


def _apply_schedule_override(row, sched, bt, mat, fr, curve):
    """Price on an authoritative coupon path (``data/coupon_schedules.csv``) and fill ``row``.

    The override carries primary-source coupon terms the workbook lacks or mis-states (step-up
    levels, rating-step levels in force, custodian coupon errors — docs/isin_lookup_2026-07-20.md),
    so it beats the free-text parse, the degenerate-zero branch and the FRN fallback.
    """
    try:
        eff = coupon_at(sched, pd.Timestamp(VAL).date())
        oas = implied_oas(float(bt), VAL, mat, eff, curve, freq=fr, coupon_schedule=sched)
        rm = risk_metrics(VAL, mat, eff, curve, oas, freq=fr, coupon_schedule=sched)
        nm = near_maturity(VAL, mat, MIN_YEARS)
        row.update(route="vanilla-schedule", coupon=eff, clean=rm["clean"], implied_oas=oas,
                   implied_bp=oas * 1e4, eff_dur=rm["eff_duration"], dv01=rm["dv01"],
                   convexity=rm["convexity"], near_maturity=nm,
                   flag=("near-maturity" if nm else
                         f"coupon path from data/coupon_schedules.csv ({eff * 100:.3f}% at VAL; ISIN lookup 2026-07-20)"))
    except ValueError as e:
        row.update(route="schedule-unavailable", clean=float(bt), flag=f"override schedule price failed ({e})")


def _curve_cache():
    """Lazy per-(currency, freq-variant) ZeroCurve, so each curve is bootstrapped at most once."""
    cache = {}

    def get(currency, variant):
        key = (str(currency).strip().upper(), variant)
        if key not in cache:
            cache[key] = ZeroCurve.from_currency(DATA_DIR, key[0], VAL, freq=variant)
        return cache[key]

    return get


def main():
    master = load_master(WB)
    terms = load_corporate_terms(WB)
    csv_scheds = load_coupon_schedule_overrides(SCHED_CSV)   # {aid: [(date|None, rate), ...]}
    frn_over = load_frn_spreads(FRN_SPREADS_CSV)             # {aid: {"spread": dec, "freq": int|None}}
    mw_over = load_make_whole_overrides(MW_CSV)              # {aid, ...} documented make-whole-only
    hyb_terms = load_hybrid_terms(HYBRID_CSV)                # {aid: fixed-to-float terms} (margin None = gap)
    canon, _excluded, _funnel, extras = build_universe(master, terms, VAL,
                                                       make_whole_overrides=mw_over)
    recon = extras["reconciliation"].drop_duplicates("asset_id").set_index("asset_id")
    recon.index = recon.index.astype(str)
    get_curve = _curve_cache()
    usd_curve = {v: get_curve("USD", v) for v in ("Annual", "Semiannual")}  # for the v1 "before"

    rows, skipped = [], []
    for _, b in canon.iterrows():
        aid = str(b["asset_id"])
        cpn = pd.to_numeric(b["coupon"], errors="coerce")
        mat = b["maturity"]
        ccy = str(b.get("currency")).strip().upper() if b.get("currency") is not None else "USD"
        try:
            fr = int(b["freq"])
        except (TypeError, ValueError):
            skipped.append((aid, f"freq={b['freq']!r}")); continue
        if fr not in FREQ_VARIANT or pd.isna(cpn) or pd.isna(mat):
            skipped.append((aid, f"cpn={cpn} fr={fr} mat={mat}")); continue
        bt = pd.to_numeric(recon.loc[aid, "gold_price"], errors="coerce") if aid in recon.index else np.nan
        if pd.isna(bt) or bt <= 0:
            skipped.append((aid, f"bt={bt}")); continue

        # own-currency curve (USD/EUR/GBP). bootstrap() builds ALL freq variants together, so a
        # non-arb-free node in any variant fails the whole curve (GBP @ 2009-06-10 dies at the 3y
        # annual node) -> those bonds are skipped + flagged, NOT silently mispriced on the USD curve.
        variant = FREQ_VARIANT[fr]
        try:
            curve = get_curve(ccy, variant)
        except Exception as e:                       # unmapped ccy, val date absent, or non-arb node
            skipped.append((aid, f"curve {ccy}/{variant}: {e}")); continue

        try:
            oas = implied_oas(float(bt), VAL, mat, float(cpn), curve, freq=fr)
        except ValueError as e:
            skipped.append((aid, f"no-bracket bt={bt:.2f}: {e}")); continue
        rm = risk_metrics(VAL, mat, float(cpn), curve, oas, freq=fr)

        oas_usd = np.nan                             # what v1 got (non-USD priced on USD curve)
        if ccy != "USD":
            try:
                oas_usd = implied_oas(float(bt), VAL, mat, float(cpn), usd_curve[variant], freq=fr)
            except (ValueError, KeyError):
                pass

        par = pd.to_numeric(b.get("par_value"), errors="coerce")
        fx = b.get("fx_rate")
        ttm = (pd.Timestamp(mat) - pd.Timestamp(VAL)).days / 365.25
        nm = near_maturity(VAL, mat, MIN_YEARS)
        rp = float(bt) < DISTRESS_BT
        mw = bool(b.get("is_make_whole"))
        rows.append(dict(
            asset_id=aid, isin=b.get("isin"), ccy=ccy, fx=fx, rating=b["rating_bucket"], src=b["rating_source"],
            coupon=float(cpn), freq=fr, maturity=pd.Timestamp(mat).date(), ttm=round(ttm, 3), par=par,
            bt=float(bt), clean=rm["clean"], implied_oas=oas, implied_bp=oas * 1e4,
            implied_bp_usd_curve=(oas_usd * 1e4 if pd.notna(oas_usd) else np.nan),
            eff_dur=rm["eff_duration"], dv01=rm["dv01"], convexity=rm["convexity"],
            mv_base_usd=(pd.to_numeric(recon.loc[aid, "gold_mkt_value"], errors="coerce")
                        if aid in recon.index else np.nan),   # custodian 'Market value - base' (already USD)
            near_maturity=nm, recovery_plug=rp, route=("make-whole-as-vanilla" if mw else "vanilla"),
            flag=("near-maturity" if nm else ("recovery-plug" if rp else "")),
        ))

    # ---- Step-3 special coupon types: zero / stepped / step-up / defaulted (from the excluded frame) ----
    # Priced where possible: zero as a degenerate vanilla (single face cash flow), stepped via its
    # parsed coupon schedule. Defaulted = recovery mark (BT, no OAS — solving an OAS for a defaulted
    # bond is meaningless). Step-up whose steps aren't in the workbook = schedule-unavailable (BT mark,
    # flagged for a terms source, exactly like a missing call schedule).
    special = _excluded[_excluded["coupon_class"].isin(["zero", "stepped", "step-up", "defaulted"])]
    for _, b in special.iterrows():
        aid = str(b["asset_id"])
        cc = b["coupon_class"]
        mat = b["maturity"]
        ccy = str(b.get("currency")).strip().upper() if b.get("currency") is not None else "USD"
        bt = pd.to_numeric(recon.loc[aid, "gold_price"], errors="coerce") if aid in recon.index else np.nan
        mv = pd.to_numeric(recon.loc[aid, "gold_mkt_value"], errors="coerce") if aid in recon.index else np.nan
        try:
            fr = int(b["freq"])
        except (TypeError, ValueError):
            fr = 2
        ttm = (pd.Timestamp(mat) - pd.Timestamp(VAL)).days / 365.25 if pd.notna(mat) else np.nan
        row = dict(
            asset_id=aid, isin=b.get("isin"), ccy=ccy, fx=b.get("fx_rate"),
            rating=b["rating_bucket"], src=b.get("rating_source"), coupon=np.nan, freq=fr,
            maturity=(pd.Timestamp(mat).date() if pd.notna(mat) else None),
            ttm=(round(ttm, 3) if pd.notna(ttm) else np.nan),
            par=pd.to_numeric(b.get("par_value"), errors="coerce"),
            bt=(float(bt) if pd.notna(bt) else np.nan), clean=np.nan, implied_oas=np.nan,
            implied_bp=np.nan, implied_bp_usd_curve=np.nan, eff_dur=np.nan, dv01=np.nan,
            convexity=np.nan, mv_base_usd=mv, near_maturity=False, recovery_plug=False,
            route="", flag="",
        )

        if cc == "defaulted":
            row.update(route="recovery", clean=(float(bt) if pd.notna(bt) else np.nan),
                       flag="recovery mark: BT used as price, not model-priced (no OAS for a defaulted bond)")
            rows.append(row); continue
        if pd.isna(bt) or bt <= 0 or pd.isna(mat):
            row.update(route="excluded-no-data", flag=f"missing BT/maturity (bt={bt})")
            rows.append(row); continue

        variant = FREQ_VARIANT.get(fr, "Semiannual")
        try:
            curve = get_curve(ccy, variant)
        except Exception as e:
            row.update(route="schedule-unavailable", clean=float(bt), flag=f"curve {ccy}/{variant} failed: {e}")
            rows.append(row); continue

        # terms-override first: a documented coupon path beats the degenerate-zero branch AND the
        # free-text parse (e.g. Comcast 20030NAV3 "zero" = a custodian coupon error, really 6.95%;
        # Aquila step-up = flat 11.875% for the remaining life).
        if aid in csv_scheds:
            _apply_schedule_override(row, csv_scheds[aid], bt, mat, fr, curve)
            rows.append(row); continue

        if cc == "zero":                                # degenerate vanilla: single face cash flow
            try:
                oas = implied_oas(float(bt), VAL, mat, 0.0, curve, freq=fr)
                rm = risk_metrics(VAL, mat, 0.0, curve, oas, freq=fr)
                row.update(route="zero-structured", coupon=0.0, clean=rm["clean"], implied_oas=oas,
                           implied_bp=oas * 1e4, eff_dur=rm["eff_duration"], dv01=rm["dv01"],
                           convexity=rm["convexity"],
                           flag="zero-structured: BT inconsistent with a pure-discount zero (structured payoff) -> OAS not a clean spread; excluded from medians")
            except ValueError as e:
                row.update(route="zero-structured", clean=float(bt), flag=f"zero: OAS not bracketable ({e})")
            rows.append(row); continue

        # stepped / step-up: need a numeric coupon schedule parsed from the formula text
        sched = parse_coupon_schedule(b.get("coupon_formula2"), b.get("coupon_formula"))
        if sched is None:                               # e.g. "Step-up schedule" with no numbers in the book
            row.update(route="schedule-unavailable", clean=float(bt),
                       flag="coupon schedule not in workbook (needs a terms source, like the call schedule)")
            rows.append(row); continue
        try:
            eff = coupon_at(sched, VAL)                 # coupon in force at valuation (steps before VAL are settled)
            oas = implied_oas(float(bt), VAL, mat, eff, curve, freq=fr, coupon_schedule=sched)
            rm = risk_metrics(VAL, mat, eff, curve, oas, freq=fr, coupon_schedule=sched)
            nm = near_maturity(VAL, mat, MIN_YEARS)
            row.update(route="vanilla-schedule", coupon=eff, clean=rm["clean"], implied_oas=oas,
                       implied_bp=oas * 1e4, eff_dur=rm["eff_duration"], dv01=rm["dv01"],
                       convexity=rm["convexity"], near_maturity=nm,
                       flag=("near-maturity" if nm else f"coupon schedule: {len(sched)} step(s), {eff * 100:.3f}% from {VAL}"))
        except ValueError as e:
            row.update(route="schedule-unavailable", clean=float(bt), flag=f"schedule price failed ({e})")
        rows.append(row)

    # ---- Step-4 floating-rate notes (coupon_class == "floating"): FRN forward-projection engine ----
    # Coupons project as the simple forward off our ZeroCurve + spread; the spread is absent from this
    # workbook ("... + Spread", no number) so it is folded into the calibrated OAS (a discount-margin
    # -type spread). Effective duration bumps the CURVE (reprojects), so it is ~ time to the next reset,
    # far below a same-maturity fixed bond. Fixed->Floating (needs a switch date), perpetual/no-maturity,
    # defaulted and curve-blocked names are flagged, NOT force-priced.
    floaters = _excluded[_excluded["coupon_class"] == "floating"]
    for _, b in floaters.iterrows():
        aid = str(b["asset_id"])
        mat = b["maturity"]
        ccy = str(b.get("currency")).strip().upper() if b.get("currency") is not None else "USD"
        bt = pd.to_numeric(recon.loc[aid, "gold_price"], errors="coerce") if aid in recon.index else np.nan
        mv = pd.to_numeric(recon.loc[aid, "gold_mkt_value"], errors="coerce") if aid in recon.index else np.nan
        cpn_d = pd.to_numeric(b.get("coupon"), errors="coerce")
        try:
            fr = int(b["freq"])
        except (TypeError, ValueError):
            fr = 2
        ttm = (pd.Timestamp(mat) - pd.Timestamp(VAL)).days / 365.25 if pd.notna(mat) else np.nan
        low = str(b.get("coupon_formula")).lower()
        row = dict(
            asset_id=aid, isin=b.get("isin"), ccy=ccy, fx=b.get("fx_rate"),
            rating=b["rating_bucket"], src=b.get("rating_source"),
            coupon=(float(cpn_d) if pd.notna(cpn_d) else np.nan), freq=fr,
            maturity=(pd.Timestamp(mat).date() if pd.notna(mat) else None),
            ttm=(round(ttm, 3) if pd.notna(ttm) else np.nan),
            par=pd.to_numeric(b.get("par_value"), errors="coerce"),
            bt=(float(bt) if pd.notna(bt) else np.nan), clean=np.nan, implied_oas=np.nan,
            implied_bp=np.nan, implied_bp_usd_curve=np.nan, eff_dur=np.nan, dv01=np.nan,
            convexity=np.nan, mv_base_usd=mv, near_maturity=False, recovery_plug=False,
            next_reset_t=np.nan, route="", flag="",
        )
        if b["primary_reason"] == "defaulted" or (pd.notna(bt) and bt <= 1.0):
            row.update(route="recovery", clean=(float(bt) if pd.notna(bt) else np.nan),
                       flag="recovery mark: defaulted floater, BT used, no OAS")
            rows.append(row); continue
        # fixed-to-float hybrids (data/hybrid_switch_terms.csv): the fixed-then-float engine — or a
        # hybrid-margin-unavailable BT-mark when the post-switch margin is a documented gap. The CSV
        # is authoritative for switch/maturity (it resolves e.g. the Shinsei "no-maturity" pair).
        if aid in hyb_terms:
            _hybrid_route(row, hyb_terms[aid], bt, ccy, get_curve)
            rows.append(row); continue
        # terms-override: several workbook "(VAR)"/floating tags turned out to be rating-step or
        # plain-FIXED bonds with a deterministic coupon path (BT 8.625/9.125, Sogerim 7.50,
        # TI-2012 7.25, Anglian 5.375, RBS 6.00, FT-GBP 7.50 — docs/isin_lookup_2026-07-20.md).
        # A data/coupon_schedules.csv entry re-routes them off the FRN engine to vanilla-schedule.
        if aid in csv_scheds and pd.notna(mat) and pd.notna(bt) and bt > 0:
            variant = FREQ_VARIANT.get(fr, "Semiannual")
            try:
                curve = get_curve(ccy, variant)
            except Exception as e:                       # e.g. the GBP non-arb 3y node
                row.update(route="frn-curve-blocked", clean=float(bt),
                           flag=f"coupon path known (override) but curve {ccy}/{variant} blocked: {e}")
                rows.append(row); continue
            _apply_schedule_override(row, csv_scheds[aid], bt, mat, fr, curve)
            rows.append(row); continue
        if pd.isna(mat):
            row.update(route="frn-no-maturity", clean=(float(bt) if pd.notna(bt) else np.nan),
                       flag="no maturity (perpetual?) — needs terms; BT mark")
            rows.append(row); continue
        if "fixed" in low and "float" in low:
            row.update(route="frn-switch-unavailable", clean=(float(bt) if pd.notna(bt) else np.nan),
                       flag="Fixed->Floating: switch date not in workbook (may still be fixed) — BT mark")
            rows.append(row); continue
        if pd.isna(bt) or bt <= 0:
            row.update(route="frn-no-data", flag=f"missing BT (bt={bt})")
            rows.append(row); continue

        # documented quoted margin / payment-frequency fix (data/frn_spreads.csv): the margin then
        # prices explicitly instead of being folded into the OAS, and a wrong custodian freq
        # (e.g. quarterly FRNs recorded semiannual) is corrected before the curve variant is chosen.
        over = frn_over.get(aid)
        if over and over.get("freq"):
            fr = over["freq"]
            row["freq"] = fr
        variant = FRN_FREQ_VARIANT.get(fr, "Semiannual")
        try:
            curve = get_curve(ccy, variant)
        except Exception as e:
            row.update(route="frn-curve-blocked", clean=float(bt), flag=f"curve {ccy}/{variant} blocked: {e}")
            rows.append(row); continue

        spread = over["spread"] if over else parse_frn_spread(b.get("coupon_formula"), b.get("coupon_formula2"))
        cur = float(cpn_d) if pd.notna(cpn_d) else None      # current reset coupon (master D) if numeric
        try:
            oas = implied_oas_frn(float(bt), VAL, mat, curve, current_coupon=cur,
                                  spread=(spread or 0.0), freq=fr)
            rm = frn_risk_metrics(VAL, mat, curve, oas, current_coupon=cur, spread=(spread or 0.0), freq=fr)
            note = ("spread from data/frn_spreads.csv (ISIN lookup 2026-07-20)" if over else
                    "spread parsed" if spread is not None else
                    "spread unknown->0, OAS absorbs it (price exact for BT calib; dur ~spread-independent; separable later)")
            row.update(route="floating", clean=rm["clean"], implied_oas=oas, implied_bp=oas * 1e4,
                       eff_dur=rm["eff_duration"], dv01=rm["dv01"], convexity=rm["convexity"],
                       next_reset_t=rm["next_reset_t"],
                       flag=f"FRN; {note}" + ("" if cur is not None else "; current coupon 'Variable'->forward"))
        except ValueError as e:
            row.update(route="frn-no-bracket", clean=float(bt), flag=f"FRN OAS not bracketable ({e})")
        rows.append(row)

    # ---- Reset-6 (fixed-to-reset hybrids, Mario 2026-07-08 plan): coupon-continuation MAIN column +
    #      price-to-call SECONDARY. Known-coupon bonds price as their current fixed coupon continued
    #      (perpetual -> long truncation; the OAS absorbs the unknown reset terms). Variable-coupon
    #      ones are BT-marked pending terms. Price-to-call is a reference only: for a deep-discount name
    #      the market prices EXTENSION, not the call, so a to-call OAS is spurious (see WORKLOG).
    resets = _excluded[_excluded["coupon_class"] == "fixed-to-reset"]
    for _, b in resets.iterrows():
        aid = str(b["asset_id"])
        mat = b["maturity"]
        ccy = str(b.get("currency")).strip().upper() if b.get("currency") is not None else "USD"
        bt = pd.to_numeric(recon.loc[aid, "gold_price"], errors="coerce") if aid in recon.index else np.nan
        mv = pd.to_numeric(recon.loc[aid, "gold_mkt_value"], errors="coerce") if aid in recon.index else np.nan
        cur = pd.to_numeric(b.get("coupon"), errors="coerce")
        call = pd.to_datetime(b.get("call_date"), errors="coerce")
        try:
            fr = int(b["freq"])
        except (TypeError, ValueError):
            fr = 2
        ttm = (pd.Timestamp(mat) - pd.Timestamp(VAL)).days / 365.25 if pd.notna(mat) else np.nan
        row = dict(
            asset_id=aid, isin=b.get("isin"), ccy=ccy, fx=b.get("fx_rate"),
            rating=b["rating_bucket"], src=b.get("rating_source"),
            coupon=(float(cur) if pd.notna(cur) else np.nan), freq=fr,
            maturity=(pd.Timestamp(mat).date() if pd.notna(mat) else None),
            ttm=(round(ttm, 3) if pd.notna(ttm) else np.nan),
            par=pd.to_numeric(b.get("par_value"), errors="coerce"),
            bt=(float(bt) if pd.notna(bt) else np.nan), clean=np.nan, implied_oas=np.nan,
            implied_bp=np.nan, implied_bp_usd_curve=np.nan, eff_dur=np.nan, dv01=np.nan,
            convexity=np.nan, mv_base_usd=mv, near_maturity=False, recovery_plug=False,
            next_reset_t=np.nan, implied_bp_to_call=np.nan, eff_dur_to_call=np.nan,
            call_date_used=(call.date() if pd.notna(call) else None), route="", flag="",
        )
        # fixed-to-float hybrids among the resets (BNP/UniCredit perp T1: margin known -> hybrid
        # engine, perp truncated; Chuo/Resona: margin gap -> hybrid-margin-unavailable BT-mark,
        # replacing the coupon-continuation column until Mario's margins arrive).
        if aid in hyb_terms:
            _hybrid_route(row, hyb_terms[aid], bt, ccy, get_curve)
            rows.append(row); continue
        # terms-override: a workbook "Fixed -> Reset" tag can be plain wrong — e.g. the TI/Olivetti
        # 7.75% 2033 notes are a documented PLAIN FIXED bullet (docs/isin_lookup_2026-07-20.md).
        # A data/coupon_schedules.csv entry prices them on their real deterministic path.
        if aid in csv_scheds and pd.notna(mat) and pd.notna(bt) and bt > 0:
            variant = FREQ_VARIANT.get(fr, "Semiannual")
            try:
                curve = get_curve(ccy, variant)
            except Exception as e:
                row.update(route="reset-terms-unavailable", clean=float(bt),
                           flag=f"coupon path known (override) but curve {ccy}/{variant} blocked: {e}")
                rows.append(row); continue
            _apply_schedule_override(row, csv_scheds[aid], bt, mat, fr, curve)
            rows.append(row); continue

        if pd.isna(cur) or pd.isna(bt) or bt <= 0:      # Variable coupon / no mark -> awaiting terms
            row.update(route="reset-terms-unavailable", clean=(float(bt) if pd.notna(bt) else np.nan),
                       flag="Variable coupon / no BT — awaiting reset terms (BT mark)")
            rows.append(row); continue
        variant = FREQ_VARIANT.get(fr, "Semiannual")
        try:
            curve = get_curve(ccy, variant)
        except Exception as e:
            row.update(route="reset-terms-unavailable", clean=float(bt), flag=f"curve {ccy}/{variant} blocked: {e}")
            rows.append(row); continue

        perp = pd.isna(mat)
        cont_mat = (pd.Timestamp(VAL) + pd.DateOffset(years=PERP_TRUNC_YEARS)) if perp else mat
        try:
            oas = implied_oas(float(bt), VAL, cont_mat, float(cur), curve, freq=fr)
            rm = risk_metrics(VAL, cont_mat, float(cur), curve, oas, freq=fr)
        except ValueError as e:
            row.update(route="reset-terms-unavailable", clean=float(bt), flag=f"continuation price failed ({e})")
            rows.append(row); continue

        oas_call = eff_call = np.nan                     # secondary: price-to-call reference
        if pd.notna(call) and pd.Timestamp(call) > pd.Timestamp(VAL):
            try:
                oas_call = implied_oas(float(bt), VAL, call, float(cur), curve, freq=fr)
                eff_call = risk_metrics(VAL, call, float(cur), curve, oas_call, freq=fr)["eff_duration"]
            except ValueError:
                pass
        trunc = (f"; perp truncated at {PERP_TRUNC_YEARS}y (face PV~{100 * curve.discount_factor(float(PERP_TRUNC_YEARS), oas):.2f})"
                 if perp else "")
        callref = (f"; price-to-call REFERENCE only" + (", deep-discount->extension priced" if float(bt) < DISTRESS_BT else "")
                   if pd.notna(oas_call) else "")
        row.update(route="reset-continuation", clean=rm["clean"], implied_oas=oas, implied_bp=oas * 1e4,
                   eff_dur=rm["eff_duration"], dv01=rm["dv01"], convexity=rm["convexity"],
                   implied_bp_to_call=(oas_call * 1e4 if pd.notna(oas_call) else np.nan), eff_dur_to_call=eff_call,
                   flag="reset-terms-unavailable; coupon-continuation (main)" + trunc + callref)
        rows.append(row)

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    df.to_csv(OUT, index=False)

    # ---- integrity ----
    print(f"# calibrate_risk @ {VAL}  canonical={len(canon)} priced={len(df)} skipped={len(skipped)}")
    for aid, why in skipped[:25]:
        print("  skip", aid, why)
    print(f"[calibration] |clean(implied_oas) - BT| max={(df['clean'] - df['bt']).abs().max():.2e}")
    print(f"[flags] near-maturity={int(df['near_maturity'].sum())} "
          f"recovery-plug(non-NM)={int((df['recovery_plug'] & ~df['near_maturity']).sum())} "
          f"clean={int((df['flag'] == '').sum())}")
    print(f"[make-whole-as-vanilla] {int((df['route'] == 'make-whole-as-vanilla').sum())} bonds priced as vanilla (gap<=7d call)")

    # ---- Step-3 special coupon types (zero / stepped / step-up / defaulted) ----
    fl_ids = set(floaters["asset_id"].astype(str))
    sp = df[~df["route"].isin({"vanilla", "make-whole-as-vanilla"}) & ~df["asset_id"].astype(str).isin(fl_ids)]
    if len(sp):
        print(f"\n[STEP-3 special coupon types] {len(sp)} bonds routed by structure:")
        print(sp[["asset_id", "route", "rating", "maturity", "ttm", "coupon", "bt", "clean",
                  "implied_bp", "eff_dur", "flag"]].to_string(index=False))

    # ---- Step-4 floating-rate notes (eff_dur = curve-bump duration ~ time to next reset) ----
    flt = df[df["asset_id"].astype(str).isin(fl_ids)]
    if len(flt):
        print(f"\n[STEP-4 FLOATING-RATE NOTES] {len(flt)} bonds (eff_dur ~ time to next reset, NOT maturity):")
        print(flt.sort_values(["route", "ttm"])[
            ["asset_id", "ccy", "route", "rating", "maturity", "ttm", "coupon", "bt",
             "implied_bp", "eff_dur", "next_reset_t", "flag"]].to_string(index=False))
        pr = flt[flt["route"] == "floating"]
        if len(pr):
            print(f"\n  priced FRNs: {len(pr)}  eff_dur range [{pr['eff_dur'].min():.2f}, {pr['eff_dur'].max():.2f}]"
                  f"  for maturities up to {pr['ttm'].max():.0f}y  -> durations SHORT = the reset feature")

    # ---- Reset-6 fixed-to-reset (coupon-continuation main + price-to-call secondary) ----
    rs_df = df[df["route"].isin(["reset-continuation", "reset-terms-unavailable"])]
    if len(rs_df):
        print(f"\n[RESET-6 fixed-to-reset] {len(rs_df)} bonds — main=coupon-continuation, 2nd=price-to-call:")
        print(rs_df.sort_values("route")[
            ["asset_id", "ccy", "route", "rating", "coupon", "maturity", "bt", "implied_bp", "eff_dur",
             "implied_bp_to_call", "eff_dur_to_call", "call_date_used", "flag"]].to_string(index=False))

    # ---- caveat 2: EUR/GBP own-ccy vs USD-curve implied OAS ----
    nonusd = df[df["ccy"] != "USD"]
    print(f"\n[EUR/GBP FIX] {len(nonusd)} non-USD bonds — implied OAS own-ccy vs v1 USD-curve (bp):")
    if len(nonusd):
        print(nonusd.sort_values(["ccy", "ttm"])[
            ["asset_id", "ccy", "rating", "maturity", "ttm", "bt", "implied_bp", "implied_bp_usd_curve", "flag"]
        ].to_string(index=False))

    # ---- by-rating review table, EXCLUDING near-maturity (caveat 1) ----
    # Index OAS = ICE BofA rating OAS on the SAME valuation date (date-matched via oas_on), a
    # historical reference only (OAS redefined 2026-06-30 as a per-bond calibration factor).
    try:
        index_oas = oas_on(OAS_WB, VAL)                      # {bucket: decimal} on VAL
    except Exception as e:                                   # date absent / workbook missing
        print(f"[index OAS] unavailable for {VAL}: {e}")
        index_oas = {}
    # Only clean-OAS routes feed the medians: vanilla + make-whole + parsed schedule. The BT-mark /
    # anomalous routes (recovery, schedule-unavailable, zero-structured) carry no meaningful spread.
    review = df[df["route"].isin(PRICED_ROUTES) & ~df["near_maturity"]]
    idx = [r for r in RATING_ORDER if r in set(review["rating"])]
    g = review.groupby("rating")["implied_bp"].agg(["count", "median", "min", "max"]).reindex(idx)
    g["index_oas_bp"] = [index_oas[r] * 1e4 if r in index_oas else np.nan for r in g.index]
    g["median_excl_distress"] = review[~review["recovery_plug"]].groupby("rating")["implied_bp"].median().reindex(g.index)
    print(f"\n[BY-RATING IMPLIED OAS — review, EXCLUDING {int(df['near_maturity'].sum())} near-maturity (<{MIN_YEARS:g}y)] (bp; index @ {VAL})")
    print(g.round(0).to_string())
    print(f"(median_excl_distress also drops {int(review['recovery_plug'].sum())} recovery-plug names, BT<{DISTRESS_BT:g})")
    mw = df[df["route"] == "make-whole-as-vanilla"]
    if len(mw):
        mwr = mw[~mw["near_maturity"]]
        mwg = mwr.groupby("rating")["implied_bp"].agg(["count", "median"]).reindex(
            [r for r in RATING_ORDER if r in set(mwr["rating"])])
        print(f"\n[make-whole-as-vanilla subset (n={len(mw)}), implied OAS bp by rating, excl near-mat]")
        print(mwg.round(0).to_string())
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
