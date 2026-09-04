"""Sovereign driver: calibrate + risk for the two classes Mario marked on the Summary sheet —
Government Bonds (``Summary!K23``, 153 rows -> 147 securities) and Municipal/Provincial Bonds
(``Summary!K55``, 7 -> 7) — at a valuation date.

Separate from ``scripts/phase2_risk.py`` on purpose: that driver's committed CSV is one of the
five production artifacts checked byte-for-byte after every code-bearing commit, and adding
154 rows to it would spend that invariant for nothing. ``dataio.phase2`` is shared; only the
class list differs.

WHAT THE SPREAD MEANS (it is not one thing, and the CSV says which per row)
--------------------------------------------------------------------------
Every bond is discounted on its OWN CURRENCY's curve — the rule the legacy system used
(``zeroyield4(ccy, date)``), the rule ``ZeroCurve.from_currency`` already implements, and the
rule the corporate book follows. For every mapped file but one, that curve IS the currency's
government curve, so the calibrated number is a validation ANCHOR near zero rather than a
credit signal: a Bund reprices at +1.34bp on the German curve, US Treasuries within ~20bp on
the USD curve. Three meanings, carried per row in ``spread_meaning``:

  * ``own-curve-anchor``            the issuer IS the currency's sovereign. Expect ~0.
  * ``relative-to-euro-composite``  EUR_Yield_Curve.txt is a euro-area sovereign COMPOSITE,
    not a swap curve (verified 2026-09-03: strictly between Germany and Italy at every tenor;
    a debt-weighted six-country average reproduces it to 7bp mean / 18bp max). So a euro
    sovereign shows relative value against the euro-area average — Germany rich, the
    periphery cheap. It is NOT an asset-swap spread and must not be reported as one.
  * ``spread-over-government``      a foreign sovereign in USD (Russia, Brazil, 5 Mexican
    MTNs), a province or a municipality against the local government curve. A real spread.

Why per-country curves are the cross-check and not the basis: Ireland has no curve file, so a
per-country rule would put 2 Irish bonds on a different footing from 28 euro peers.

ROUTES (built by ``dataio.phase2._route_sovereign``)
  * ``vanilla`` / ``zero``  -> implied spread to the custodian price + numerical risk.
  * ``callable-lattice``    -> BDT lattice, Bermudan par call from the master AB date, guarded
    by ``check_representable`` so a schedule that reaches no exercise node is refused instead
    of silently pricing as a straight bond (the 2026-08-31 lesson).
  * ``floating-reference-unverified`` / ``coupon-schedule-unavailable`` /
    ``call-after-maturity`` -> custodian mark + a named reason. Never force-priced.

Every one of the 154 candidates is either priced or skipped with a reason, proved over SETS by
``dataio.dispositions.reconcile`` and written to a dated sidecar.

Run:
    FIP_VAL_DATE=2009-03-31 PYTHONPATH=src python3 scripts/sovereign_risk.py
"""
import os
import sys

sys.path.insert(0, "src")
import numpy as np
import pandas as pd

from curves.zero_curve import ZeroCurve
from dataio.call_schedules import (load_call_provenance, load_call_schedules,
                                   to_lattice_schedule)
from dataio.dispositions import reconcile
from dataio.phase2 import SOVEREIGN_CLASSES, build_phase2_from_path
from pricer.assets.corporate.embedded_option import (ExerciseScheduleNotRepresentable,
                                                     check_representable)
from pricer.errors import CalibrationError
from pricing.bond_price import lattice_inputs
from pricing.calibrate import implied_oas, near_maturity
from pricing.lattice import ShortRateLattice
from pricing.risk import risk_metrics

DATA_DIR = os.environ.get("FIP_DATA_DIR", "data")
WB = os.environ.get("FIP_URS_WB", os.path.join(DATA_DIR, "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"))
VAL = os.environ.get("FIP_VAL_DATE", "2009-03-31")
OUT = os.environ.get("FIP_OUT", f"outputs/sovereign_risk_{VAL}.csv")
DISPO = os.environ.get("FIP_DISPO", f"outputs/sovereign_disposition_{VAL}.csv")
SIGMA = float(os.environ.get("FIP_VOL", "0.15"))
SCHED = os.environ.get("FIP_CALL_SCHED", os.path.join(DATA_DIR, "call_schedules.csv"))
MIN_YEARS = 1.0
FREQ_VARIANT = {1: "Annual", 2: "Semiannual", 4: "Quarterly", 12: "Monthly"}
# A model duration this far from the custodian's own effective duration is reported as
# evidence, never acted on. AQ means different things in different classes (it missed the call
# on corporate callables and was option-adjusted on agencies), so it annotates and never routes.
AQ_DIVERGENCE_YEARS = 1.5
pd.set_option("display.width", 250)

# Reasons a bond is not priced. Kept here so the text a reader sees is written once.
BLOCKED = {
    "floating-reference-unverified": (
        "description says FRN and no reference rate or margin for it exists anywhere in our "
        "data. The 15y JGB series resets off the 10-year JGB auction yield, which the "
        "simple-forward FRN engine does not represent, and the custodian's own effective "
        "duration (-0.475) is inconsistent with a short-rate floater at 97.64. Pricing it "
        "would be half-modelling: custodian mark"),
    "coupon-schedule-unavailable": (
        "description says STEP UP and we hold no coupon path, the same treatment the "
        "corporate book gives a step-up with no schedule. Independently, the custodian's "
        "effective duration of 4.08 against a 21y 7.5% bullet's ~10 says the notional "
        "amortises, which we also cannot represent: custodian mark"),
    "call-after-maturity": (
        "master call date falls after the maturity date, which is a data error, not a "
        "contract: custodian mark"),
}


def _curve_cache():
    cache = {}

    def get(currency, variant):
        key = (str(currency).strip().upper(), variant)
        if key not in cache:
            cache[key] = ZeroCurve.from_currency(DATA_DIR, key[0], VAL, freq=variant)
        return cache[key]

    return get


def _basis(ccy):
    """The curve a row was discounted on, named for a reader of the CSV."""
    return "EUR euro-area sovereign composite" if ccy == "EUR" else f"{ccy} government curve"


def main():
    bonds, recon, counts = build_phase2_from_path(WB, classes=SOVEREIGN_CLASSES)
    recon = recon.drop_duplicates("asset_id").set_index("asset_id")
    recon.index = recon.index.astype(str)
    schedules = load_call_schedules(SCHED)
    provenance = load_call_provenance(SCHED)
    UNCONFIRMED = {"exercise_terms_status": "provisional", "exercise_terms_source": "unspecified",
                   "exercise_price_source": "unspecified", "exercise_terms_as_of": ""}
    get_curve = _curve_cache()

    print(f"# sovereign_risk @ {VAL}  sigma={SIGMA:.2%}  classes:",
          {k: f"{v['rows']}->{v['unique']}" for k, v in counts.items()})

    candidates = [str(a) for a in bonds["asset_id"]]
    priced, skipped, rows = [], {}, []

    for _, b in bonds.iterrows():
        aid = str(b["asset_id"])
        route = b["route"]
        ccy = str(b.get("currency")).strip().upper() if b.get("currency") is not None else "USD"
        mat = b["maturity"]
        fr = int(b["freq"]) if pd.notna(b["freq"]) else 2        # the strips carry a blank freq
        quotation = b["price_quotation"]
        bt_raw = pd.to_numeric(recon.loc[aid, "gold_price"], errors="coerce") if aid in recon.index else np.nan
        bt = pd.to_numeric(recon.loc[aid, "bt_per_100"], errors="coerce") if aid in recon.index else np.nan
        mv = pd.to_numeric(recon.loc[aid, "gold_mkt_value"], errors="coerce") if aid in recon.index else np.nan
        di = pd.to_numeric(recon.loc[aid, "gold_ytm"], errors="coerce") if aid in recon.index else np.nan
        aq = pd.to_numeric(b.get("dur_eff_custodian"), errors="coerce")
        ttm = (pd.Timestamp(mat) - pd.Timestamp(VAL)).days / 365.25 if pd.notna(mat) else np.nan

        row = dict(
            asset_id=aid, asset_class=b["asset_class"], group=b["group"], route=route,
            isin=b.get("isin"), ccy=ccy, rating_sp=b.get("sp_rating"),
            rating_moody=b.get("moody_rating"),
            coupon=(float(b["coupon"]) if pd.notna(b["coupon"]) else np.nan), freq=fr,
            maturity=(pd.Timestamp(mat).date() if pd.notna(mat) else None),
            ttm=(round(ttm, 3) if pd.notna(ttm) else np.nan),
            par_face=pd.to_numeric(b.get("par_face"), errors="coerce"),
            price_quotation=quotation, bt=(float(bt) if pd.notna(bt) else np.nan),
            bt_raw=(float(bt_raw) if pd.notna(bt_raw) else np.nan),
            mv_base_usd=mv, di_ytm_custodian=di,
            clean=np.nan, implied_spread_bp=np.nan, spread_basis=_basis(ccy),
            spread_meaning=b.get("spread_meaning"),
            eff_dur=np.nan, dv01=np.nan, convexity=np.nan, near_maturity=False,
            implied_spread_bp_straight=np.nan, eff_dur_straight=np.nan, call_date=None,
            accrued=np.nan, aq_custodian=(float(aq) if pd.notna(aq) else np.nan),
            aq_divergence=np.nan, terms_note=b.get("terms_note", ""),
            exercise_terms_status="", exercise_terms_source="", exercise_price_source="",
            exercise_terms_as_of="", flag="",
        )

        def emit(code, text, **update):
            row.update(clean=(float(bt) if pd.notna(bt) else np.nan), flag=text, **update)
            skipped[aid] = (code, text)
            rows.append(row)

        if not str(quotation).startswith(("currency-face", "titles-of-")):
            emit(quotation, "price/par quotation could not be resolved (" + str(quotation) +
                 "); the custodian identity BT == market value / par did not hold in either "
                 "the currency-face or the titles form: custodian mark")
            continue
        if pd.notna(mat) and pd.Timestamp(mat) < pd.Timestamp(VAL):
            emit("matured", f"matured before {VAL}", route="matured")
            continue
        if route in BLOCKED:
            emit(route, BLOCKED[route])
            continue
        if pd.isna(bt) or bt <= 0 or pd.isna(mat):
            emit(f"{route}-no-data", f"missing custodian price or maturity (bt={bt})")
            continue

        variant = FREQ_VARIANT.get(fr, "Semiannual")
        try:
            curve = get_curve(ccy, variant)
        except Exception as e:                      # no file, no row for the date, non-arb node
            emit(f"{route}-curve-blocked", f"curve {ccy}/{variant} unavailable @ {VAL}: {e}")
            continue

        cpn = float(b["coupon"])

        # ---- callable: BDT lattice, Bermudan par call from the master AB date -------------
        if route == "callable-lattice":
            if aid not in schedules:
                emit("call-schedule-missing", "no row in " + os.path.basename(SCHED) +
                     " for this asset; seed the AB par-call row")
                continue
            sched = to_lattice_schedule(schedules[aid], VAL)
            times, ai = lattice_inputs(VAL, mat, cpn, freq=fr)
            lat = ShortRateLattice(curve, freq=fr, sigma=SIGMA, coupon_times=times)
            carr = lat.call_array(sched)
            try:                                    # the SAME rule the wrapper layer applies
                check_representable("call", schedules[aid], bool(np.isfinite(carr).any()),
                                    VAL, mat, fr)
            except ExerciseScheduleNotRepresentable as e:
                emit("call-schedule-not-representable-on-current-grid", str(e))
                continue
            try:
                oas_cal = lat.implied_oas(float(bt), cpn, call_price=carr, accrued=ai)
                oas_str = lat.implied_oas(float(bt), cpn, accrued=ai)
            except (CalibrationError, ValueError) as e:
                emit("callable-no-bracket", f"no spread reprices this bond ({e})")
                continue
            rm = lat.risk_metrics(cpn, oas_cal, call_price=carr, accrued=ai)
            rm_str = lat.risk_metrics(cpn, oas_str, accrued=ai)
            note = "call-not-binding" if abs(oas_cal - oas_str) < 1e-4 else "call-active"
            if oas_str - oas_cal > 0.0100:
                # A 12.5% coupon against a par call four months out is called with near
                # certainty, so almost the whole gap to the custodian mark is option value,
                # not credit. Said here because the straight column is a number a reader
                # could otherwise quote as a sovereign spread.
                note += (f"; the option accounts for the gap -- straight-to-maturity would "
                         f"need {oas_str * 1e4:.0f}bp to reach the same price, which is NOT "
                         f"a sovereign credit spread and must not be quoted as one")
            row.update(
                clean=float(bt), implied_spread_bp=oas_cal * 1e4, eff_dur=rm["eff_duration"],
                dv01=rm["dv01"], convexity=rm["convexity"],
                implied_spread_bp_straight=oas_str * 1e4,
                eff_dur_straight=rm_str["eff_duration"],
                call_date=schedules[aid][0][0].date(), accrued=round(ai, 4),
                **{k: provenance.get(aid, UNCONFIRMED)[k] for k in UNCONFIRMED},
                flag=(f"lattice sigma={SIGMA:.0%}, Bermudan par@100 from the master AB date; "
                      f"{note}. Par call is the Treasury convention for this vintage but is "
                      f"NOT Bloomberg-confirmed (exercise_terms_status=provisional)"))
        else:
            # ---- vanilla / zero: the corporate calibrator ---------------------------------
            try:
                oas = implied_oas(float(bt), VAL, mat, cpn, curve, freq=fr)
            except (CalibrationError, ValueError) as e:
                emit(f"{route}-no-bracket", f"no spread reprices this bond ({e})")
                continue
            rm = risk_metrics(VAL, mat, cpn, curve, oas, freq=fr)
            nm = near_maturity(VAL, mat, MIN_YEARS)
            notes = []
            if nm:
                notes.append("near-maturity")
            if route == "zero":
                notes.append("stripped Treasury: degenerate vanilla, a single face flow")
            if row["terms_note"]:
                notes.append(row["terms_note"])
            row.update(clean=rm["clean"], implied_spread_bp=oas * 1e4,
                       eff_dur=rm["eff_duration"], dv01=rm["dv01"], convexity=rm["convexity"],
                       near_maturity=nm, flag="; ".join(notes))

        # duration cross-check against the custodian's own number -- reported, never acted on
        if pd.notna(aq) and pd.notna(row["eff_dur"]) and abs(row["eff_dur"] - aq) > AQ_DIVERGENCE_YEARS:
            row["aq_divergence"] = round(float(row["eff_dur"]) - float(aq), 3)
            extra = (f"model duration {row['eff_dur']:.2f}y vs custodian {aq:.2f}y "
                     f"(reported, not acted on)")
            row["flag"] = "; ".join(x for x in [row["flag"], extra] if x)
        priced.append(aid)
        rows.append(row)

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    df.to_csv(OUT, index=False)

    # ---- every candidate has exactly one named outcome, proved over SETS ----------------
    disposition = reconcile(candidates, priced, skipped)
    disposition.to_csv(DISPO, index=False)
    print(f"[disposition] population={len(candidates)} = {len(priced)} priced + "
          f"{len(skipped)} named -> {DISPO}")

    cal = df[df["implied_spread_bp"].notna() & (df["route"] != "callable-lattice")]
    if len(cal):
        print(f"[calibration] |clean - BT| max = {(cal['clean'] - cal['bt']).abs().max():.2e} "
              f"over {len(cal)} calibrated")

    show = ["asset_id", "ccy", "route", "spread_meaning", "coupon", "maturity", "ttm", "bt",
            "implied_spread_bp", "eff_dur", "aq_custodian", "near_maturity", "flag"]
    for cls, label in (("municipal", "MUNICIPAL / PROVINCIAL"), ("government", "GOVERNMENT BONDS")):
        sub = df[df["asset_class"] == cls].sort_values(["spread_meaning", "ccy", "ttm"])
        print(f"\n[{label}] {len(sub)} securities")
        print(sub[show].to_string(index=False))

    print("\n[BY MEANING AND CURRENCY - anchors should sit near zero]")
    ok = df[df["implied_spread_bp"].notna() & ~df["near_maturity"]]
    if len(ok):
        g = (ok.groupby(["spread_meaning", "ccy"])["implied_spread_bp"]
               .agg(n="size", median="median", lo="min", hi="max").round(1))
        print(g.to_string())
    print(f"\nwrote {OUT} ({len(df)} rows)")
    return df


if __name__ == "__main__":
    main()
