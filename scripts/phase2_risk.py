"""Phase-2 driver: calibrate + risk for the three data-self-sufficient Summary classes —
Government Agencies (39) / Guaranteed FDIC-TLGP (9) / Index-Linked governments (15) — @ a
valuation date. Govt MBS awaits Mario's Bloomberg pull (engine skeleton: ``pricing.mbs``).

Routes (built by ``dataio.phase2.build_phase2_universe``; decisions in
``docs/phase2_methods_2026-07-22.md``):
  * vanilla / call-passed-vanilla / zero -> implied OAS to BT + numerical risk (the corporate
    calibrator, per-ccy curves; TLGP reported as its OWN group, never in bank rating buckets).
  * callable-lattice -> BDT lattice (sigma=FIP_VOL, default 0.15), Bermudan par call @100 from the
    master AB date via ``data/call_schedules.csv`` (the industry-standard agency assumption) —
    callable OAS/duration = MAIN columns + straight-to-maturity as REFERENCE. The Sempra lie
    detector stays on: an absurd calibrated OAS (e.g. far from the straight one on a
    market-says-no-call name) is annotated, not silently accepted.
  * ilb -> implied spread vs the NOMINAL curve at FIP_INFL (default 0). ⚠️ That spread is
    EXPECTED NEGATIVE ~ -(breakeven) at inflation=0 — it is the market's inflation expectation,
    NOT a credit OAS, and lives in its own column ``implied_spread_vs_nominal_bp`` (companion
    ``breakeven_bp`` = -spread when FIP_INFL=0). See ``pricing.ilb``.
  * cmo-tranche / ilb-indexation-unverified -> BT mark + flag (Mario/next-phase list).

Run on 47:
    FIP_VAL_DATE=2009-03-31 PYTHONPATH=src python3 scripts/phase2_risk.py
Writes FIP_OUT (default outputs/phase2_risk.csv, git-ignored)."""
import os
import sys

sys.path.insert(0, "src")
import numpy as np
import pandas as pd

from curves.zero_curve import ZeroCurve
from dataio.call_schedules import load_call_schedules, to_lattice_schedule
from dataio.phase2 import build_phase2_from_path
from pricing.calibrate import implied_oas, near_maturity
from pricing.ilb import ilb_risk_metrics, implied_spread_ilb
from pricing.lattice import ShortRateLattice
from pricing.risk import risk_metrics

DATA_DIR = os.environ.get("FIP_DATA_DIR", "data")
WB = os.environ.get("FIP_URS_WB", os.path.join(DATA_DIR, "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"))
VAL = os.environ.get("FIP_VAL_DATE", "2009-03-31")
OUT = os.environ.get("FIP_OUT", "outputs/phase2_risk.csv")
SIGMA = float(os.environ.get("FIP_VOL", "0.15"))
INFL = float(os.environ.get("FIP_INFL", "0.0"))     # ILB inflation assumption (decimal)
SCHED = os.environ.get("FIP_CALL_SCHED", os.path.join(DATA_DIR, "call_schedules.csv"))
MIN_YEARS = 1.0
FREQ_VARIANT = {1: "Annual", 2: "Semiannual", 4: "Quarterly", 12: "Monthly"}
PRICED_OAS_ROUTES = {"vanilla", "call-passed-vanilla", "zero"}
pd.set_option("display.width", 250)


def _curve_cache():
    cache = {}

    def get(currency, variant):
        key = (str(currency).strip().upper(), variant)
        if key not in cache:
            cache[key] = ZeroCurve.from_currency(DATA_DIR, key[0], VAL, freq=variant)
        return cache[key]

    return get


def main():
    bonds, recon, counts = build_phase2_from_path(WB)
    recon = recon.drop_duplicates("asset_id").set_index("asset_id")
    recon.index = recon.index.astype(str)
    schedules = load_call_schedules(SCHED)
    get_curve = _curve_cache()

    print(f"# phase2_risk @ {VAL}  sigma={SIGMA:.2%}  FIP_INFL={INFL:.2%}  classes:",
          {k: f"{v['rows']}->{v['unique']}" for k, v in counts.items() if k != "govt_mbs"})

    rows = []
    for _, b in bonds.iterrows():
        aid = str(b["asset_id"])
        route = b["route"]
        ccy = str(b.get("currency")).strip().upper() if b.get("currency") is not None else "USD"
        mat = b["maturity"]
        fr = int(b["freq"]) if pd.notna(b["freq"]) else 2       # zeros carry a blank freq
        bt = pd.to_numeric(recon.loc[aid, "gold_price"], errors="coerce") if aid in recon.index else np.nan
        mv = pd.to_numeric(recon.loc[aid, "gold_mkt_value"], errors="coerce") if aid in recon.index else np.nan
        di = pd.to_numeric(recon.loc[aid, "gold_ytm"], errors="coerce") if aid in recon.index else np.nan
        ttm = (pd.Timestamp(mat) - pd.Timestamp(VAL)).days / 365.25 if pd.notna(mat) else np.nan
        row = dict(
            asset_id=aid, asset_class=b["asset_class"], group=b["group"], route=route,
            isin=b.get("isin"), ccy=ccy, rating_sp=b.get("sp_rating"), rating_moody=b.get("moody_rating"),
            coupon=(float(b["coupon"]) if pd.notna(b["coupon"]) else np.nan), freq=fr,
            maturity=(pd.Timestamp(mat).date() if pd.notna(mat) else None),
            ttm=(round(ttm, 3) if pd.notna(ttm) else np.nan),
            par=pd.to_numeric(b.get("par_value"), errors="coerce"), is_short=bool(b.get("is_short")),
            bt=(float(bt) if pd.notna(bt) else np.nan), mv_base_usd=mv, di_ytm_custodian=di,
            clean=np.nan, implied_bp=np.nan, implied_spread_vs_nominal_bp=np.nan, breakeven_bp=np.nan,
            index_ratio0=np.nan, eff_dur=np.nan, dv01=np.nan, convexity=np.nan, near_maturity=False,
            implied_bp_straight=np.nan, eff_dur_straight=np.nan, call_date=None,
            aq_custodian=b.get("dur_eff_custodian"), flag="",
        )
        if pd.notna(mat) and pd.Timestamp(mat) < pd.Timestamp(VAL):
            row.update(route="matured", flag=f"matured before {VAL}")
            rows.append(row); continue

        # ---- BT-mark routes (never force-priced) ----
        if route == "cmo-tranche":
            row.update(clean=row["bt"],
                       flag="FHLMC SER 3122 CL ZB = REMIC Z-tranche misfiled as agency debenture; "
                            "BT mark, price in the CMO phase (Sempra lesson: no force-pricing)")
            rows.append(row); continue
        if route in ("ilb-indexation-unverified", "ilb-ratio-implausible"):
            row.update(clean=row["bt"],
                       flag="KTBi: BG==coupon exactly (no ratio embedded) and description carries no "
                            "coupon -> index ratio not derivable; Korea indexation convention = "
                            "Mario/Bloomberg item; BT mark" if ccy == "KRW" else
                            f"index ratio not derivable/plausible (route {route}); BT mark")
            rows.append(row); continue
        if pd.isna(bt) or bt <= 0 or pd.isna(mat):
            row.update(route=f"{route}-no-data", flag=f"missing BT/maturity (bt={bt})")
            rows.append(row); continue

        variant = FREQ_VARIANT.get(fr, "Semiannual")
        try:
            curve = get_curve(ccy, variant)
        except Exception as e:                     # val date absent for the ccy, non-arb node, ...
            row.update(route=f"{route}-curve-blocked", clean=float(bt),
                       flag=f"curve {ccy}/{variant} unavailable @ {VAL}: {e}")
            rows.append(row); continue

        # ---- ILB: implied spread vs nominal (own column; ~ -breakeven at INFL=0) ----
        if route == "ilb":
            ratio0 = float(b["index_ratio0"])
            rc = float(b["real_coupon"])
            try:
                sp = implied_spread_ilb(float(bt), VAL, mat, rc, curve, index_ratio=ratio0,
                                        inflation=INFL, freq=fr)
            except ValueError as e:
                row.update(route="ilb-no-bracket", clean=float(bt), flag=f"spread not bracketable ({e})")
                rows.append(row); continue
            rm = ilb_risk_metrics(VAL, mat, rc, curve, sp, index_ratio=ratio0, inflation=INFL, freq=fr)
            nm = near_maturity(VAL, mat, MIN_YEARS)
            row.update(coupon=rc, clean=rm["clean"], implied_spread_vs_nominal_bp=sp * 1e4,
                       breakeven_bp=(-sp * 1e4 if INFL == 0.0 else np.nan), index_ratio0=ratio0,
                       eff_dur=rm["eff_duration"], dv01=rm["dv01"], convexity=rm["convexity"],
                       near_maturity=nm,
                       flag=("near-maturity" if nm else
                             f"ILB @ infl={INFL:.2%}: spread ~ -(breakeven), NOT credit OAS; "
                             "deflation floor ignored (v1)"))
            rows.append(row); continue

        # ---- callable agency debentures: BDT lattice, par call @100 from AB ----
        if route == "callable-lattice":
            if aid not in schedules:
                row.update(route="call-schedule-missing", clean=float(bt),
                           flag=f"no row in {SCHED} — seed the AB par-call row")
                rows.append(row); continue
            sched = to_lattice_schedule(schedules[aid], VAL)
            T = (pd.Timestamp(mat) - pd.Timestamp(VAL)).days / 365.25
            lat = ShortRateLattice(curve, T, freq=fr, sigma=SIGMA)
            carr = lat.call_array(sched)
            cpn = float(b["coupon"])
            try:
                oas_cal = lat.implied_oas(float(bt), cpn, call_price=carr)
                oas_str = lat.implied_oas(float(bt), cpn)
            except ValueError as e:
                row.update(route="callable-no-bracket", clean=float(bt), flag=f"no bracket ({e})")
                rows.append(row); continue
            rm_cal = lat.risk_metrics(cpn, oas_cal, call_price=carr)
            rm_str = lat.risk_metrics(cpn, oas_str)
            if oas_cal < 0:
                note = (f"LIE-DETECTOR: negative callable OAS ({oas_cal * 1e4:.0f}bp) — Bermudan "
                        f"par-call from AB conflicts with BT {bt:.2f}; suspect one-time call terms")
            elif oas_cal - oas_str > 0.0100:
                note = (f"callable OAS {oas_cal * 1e4:.0f}bp >> straight {oas_str * 1e4:.0f}bp: "
                        "market pricing extension (2009 agencies often did not call) or the "
                        "Bermudan-par-call assumption is too strong for this MTN — flagged, kept")
            elif abs(oas_cal - oas_str) < 1e-4:
                note = "call-not-binding"
            else:
                note = "call-active"
            row.update(clean=float(bt), implied_bp=oas_cal * 1e4, eff_dur=rm_cal["eff_duration"],
                       dv01=rm_cal["dv01"], convexity=rm_cal["convexity"],
                       implied_bp_straight=oas_str * 1e4, eff_dur_straight=rm_str["eff_duration"],
                       call_date=schedules[aid][0][0].date(),
                       flag=f"lattice sigma={SIGMA:.0%}, Bermudan par@100 from AB; {note}")
            rows.append(row); continue

        # ---- vanilla / call-passed-vanilla / zero: the corporate calibrator ----
        cpn = float(b["coupon"])
        try:
            oas = implied_oas(float(bt), VAL, mat, cpn, curve, freq=fr)
        except ValueError as e:
            row.update(route=f"{route}-no-bracket", clean=float(bt), flag=f"no bracket ({e})")
            rows.append(row); continue
        rm = risk_metrics(VAL, mat, cpn, curve, oas, freq=fr)
        nm = near_maturity(VAL, mat, MIN_YEARS)
        notes = []
        if nm:
            notes.append("near-maturity")
        if route == "call-passed-vanilla":
            notes.append("desc maturity/call pair with 2006 call PASSED unexercised (AB blank) -> bullet")
        if route == "zero":
            notes.append("Resolution Funding CPN STRIP: degenerate vanilla (single face flow)")
        row.update(clean=rm["clean"], implied_bp=oas * 1e4, eff_dur=rm["eff_duration"],
                   dv01=rm["dv01"], convexity=rm["convexity"], near_maturity=nm, flag="; ".join(notes))
        rows.append(row)

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    df.to_csv(OUT, index=False)

    # ---- integrity + per-class review ----
    cal = df[df["implied_bp"].notna() & df["route"].isin(PRICED_OAS_ROUTES)]
    if len(cal):
        print(f"[calibration] |clean - BT| max = {(cal['clean'] - cal['bt']).abs().max():.2e} over {len(cal)} OAS-calibrated")
    ilb_ok = df[df["route"] == "ilb"]
    if len(ilb_ok):
        print(f"[ILB] |clean - BT| max = {(ilb_ok['clean'] - ilb_ok['bt']).abs().max():.2e} over {len(ilb_ok)}")

    show = ["asset_id", "ccy", "route", "coupon", "maturity", "ttm", "bt", "implied_bp",
            "eff_dur", "dv01", "near_maturity", "flag"]
    for cls, label in (("agency", "GOVERNMENT AGENCIES"), ("guaranteed", "GUARANTEED (FDIC-TLGP)")):
        sub = df[df["asset_class"] == cls].sort_values(["route", "ttm"])
        print(f"\n[{label}] {len(sub)} bonds")
        print(sub[show].to_string(index=False))
        pr = sub[sub["route"].isin(PRICED_OAS_ROUTES) & ~sub["near_maturity"]]
        if len(pr):
            print(f"  -> {label} median implied OAS = {pr['implied_bp'].median():.0f}bp "
                  f"(n={len(pr)}, excl near-maturity; group='{sub['group'].iloc[0]}' — TLGP kept out of bank buckets)")
    cb = df[df["route"].str.startswith("callable")]
    if len(cb):
        print("\n[AGY CALLABLES — lattice main vs straight reference]")
        print(cb[["asset_id", "coupon", "maturity", "call_date", "bt", "implied_bp",
                  "implied_bp_straight", "eff_dur", "eff_dur_straight", "aq_custodian", "flag"]]
              .to_string(index=False))

    il = df[df["asset_class"] == "linker"].sort_values("ttm")
    print(f"\n[INDEX-LINKED] {len(il)} bonds @ FIP_INFL={INFL:.2%} — implied spread vs NOMINAL curve "
          f"(EXPECTED ~ -(breakeven) at 0; NOT credit OAS; own column)")
    print(il[["asset_id", "ccy", "route", "coupon", "maturity", "ttm", "index_ratio0", "bt",
              "implied_spread_vs_nominal_bp", "breakeven_bp", "di_ytm_custodian", "eff_dur", "flag"]]
          .to_string(index=False))
    pr = il[(il["route"] == "ilb") & ~il["near_maturity"]]
    if len(pr):
        print(f"  -> median implied spread = {pr['implied_spread_vs_nominal_bp'].median():.0f}bp "
              f"(median breakeven {pr['breakeven_bp'].median():.0f}bp; 2009-03 10y market breakeven ~ 120-150bp)")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
