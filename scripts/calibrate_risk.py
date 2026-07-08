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
from pricing.coupon_schedule import coupon_at, parse_coupon_schedule
from pricing.risk import risk_metrics

DATA_DIR = os.environ.get("FIP_DATA_DIR", "data")
WB = os.environ.get("FIP_URS_WB", os.path.join(DATA_DIR, "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"))
VAL = os.environ.get("FIP_VAL_DATE", "2009-06-10")
OUT = os.environ.get("FIP_OUT", "outputs/implied_oas.csv")  # per-date override avoids clobbering
OAS_WB = os.environ.get("FIP_OAS_WB", os.path.join(DATA_DIR, "Pricing File.xlsm"))  # index OAS source
MIN_YEARS = 1.0          # below this remaining maturity -> implied OAS unreliable -> excluded
DISTRESS_BT = 50.0       # below this clean price -> implied OAS is a recovery plug -> flagged, kept
FREQ_VARIANT = {1: "Annual", 2: "Semiannual"}
RATING_ORDER = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
# Routes whose implied OAS is a clean, model-repriced spread (feed the by-rating medians). The other
# routes (recovery / schedule-unavailable / zero-structured / excluded-no-data) are BT marks or
# anomalous and are reported but kept out of the medians.
PRICED_ROUTES = {"vanilla", "make-whole-as-vanilla", "vanilla-schedule"}

pd.set_option("display.width", 220)


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
    canon, _excluded, _funnel, extras = build_universe(master, terms, VAL)
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
    sp = df[~df["route"].isin({"vanilla", "make-whole-as-vanilla"})]
    if len(sp):
        print(f"\n[STEP-3 special coupon types] {len(sp)} bonds routed by structure:")
        print(sp[["asset_id", "route", "rating", "maturity", "ttm", "coupon", "bt", "clean",
                  "implied_bp", "eff_dur", "flag"]].to_string(index=False))

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
