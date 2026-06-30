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

from curves.zero_curve import ZeroCurve
from dataio.loaders import load_corporate_terms, load_master, to_usd
from dataio.universe import build_universe
from pricing.calibrate import implied_oas, near_maturity
from pricing.risk import risk_metrics

DATA_DIR = os.environ.get("FIP_DATA_DIR", "data")
WB = os.environ.get("FIP_URS_WB", os.path.join(DATA_DIR, "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"))
VAL = os.environ.get("FIP_VAL_DATE", "2009-06-10")
MIN_YEARS = 1.0          # below this remaining maturity -> implied OAS unreliable -> excluded
DISTRESS_BT = 50.0       # below this clean price -> implied OAS is a recovery plug -> flagged, kept
FREQ_VARIANT = {1: "Annual", 2: "Semiannual"}
# v1 index rating OAS @ 2009-06-10 (percent), for the implied-vs-index comparison (WORKLOG).
INDEX_OAS_PCT = {"AAA": 1.48, "AA": 2.27, "A": 3.02, "BBB": 4.53, "BB": 7.41, "B": 9.45, "CCC": 17.04}
RATING_ORDER = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]

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
        rows.append(dict(
            asset_id=aid, isin=b.get("isin"), ccy=ccy, fx=fx, rating=b["rating_bucket"], src=b["rating_source"],
            coupon=float(cpn), freq=fr, maturity=pd.Timestamp(mat).date(), ttm=round(ttm, 3), par=par,
            bt=float(bt), clean=rm["clean"], implied_oas=oas, implied_bp=oas * 1e4,
            implied_bp_usd_curve=(oas_usd * 1e4 if pd.notna(oas_usd) else np.nan),
            eff_dur=rm["eff_duration"], dv01=rm["dv01"], convexity=rm["convexity"],
            our_mv_usd=(to_usd(rm["clean"] / 100.0 * par, fx) if pd.notna(par) else np.nan),
            near_maturity=nm, recovery_plug=rp,
            flag=("near-maturity" if nm else ("recovery-plug" if rp else "")),
        ))

    df = pd.DataFrame(rows)
    os.makedirs("outputs", exist_ok=True)
    df.to_csv("outputs/implied_oas.csv", index=False)

    # ---- integrity ----
    print(f"# calibrate_risk @ {VAL}  canonical={len(canon)} priced={len(df)} skipped={len(skipped)}")
    for aid, why in skipped[:25]:
        print("  skip", aid, why)
    print(f"[calibration] |clean(implied_oas) - BT| max={(df['clean'] - df['bt']).abs().max():.2e}")
    print(f"[flags] near-maturity={int(df['near_maturity'].sum())} "
          f"recovery-plug(non-NM)={int((df['recovery_plug'] & ~df['near_maturity']).sum())} "
          f"clean={int((df['flag'] == '').sum())}")

    # ---- caveat 2: EUR/GBP own-ccy vs USD-curve implied OAS ----
    nonusd = df[df["ccy"] != "USD"]
    print(f"\n[EUR/GBP FIX] {len(nonusd)} non-USD bonds — implied OAS own-ccy vs v1 USD-curve (bp):")
    if len(nonusd):
        print(nonusd.sort_values(["ccy", "ttm"])[
            ["asset_id", "ccy", "rating", "maturity", "ttm", "bt", "implied_bp", "implied_bp_usd_curve", "flag"]
        ].to_string(index=False))

    # ---- by-rating review table, EXCLUDING near-maturity (caveat 1) ----
    review = df[~df["near_maturity"]]
    idx = [r for r in RATING_ORDER if r in set(review["rating"])]
    g = review.groupby("rating")["implied_bp"].agg(["count", "median", "min", "max"]).reindex(idx)
    g["index_oas_bp"] = [INDEX_OAS_PCT.get(r, np.nan) * 100 for r in g.index]
    g["median_excl_distress"] = review[~review["recovery_plug"]].groupby("rating")["implied_bp"].median().reindex(g.index)
    print(f"\n[BY-RATING IMPLIED OAS — review, EXCLUDING {int(df['near_maturity'].sum())} near-maturity (<{MIN_YEARS:g}y)] (bp)")
    print(g.round(0).to_string())
    print(f"(median_excl_distress also drops {int(review['recovery_plug'].sum())} recovery-plug names, BT<{DISTRESS_BT:g})")
    print("\nwrote outputs/implied_oas.csv")


if __name__ == "__main__":
    main()
