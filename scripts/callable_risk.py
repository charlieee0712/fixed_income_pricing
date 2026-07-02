"""v2 callable pricing: implied OAS + effective duration for the GENUINE fixed callables, on the
BDT-style short-rate lattice (``pricing.lattice``). @ a valuation date, own-currency curve.

Scope (WORKLOG 2026-07-02 decisions 3 & 5): the lattice is applied ONLY to genuine fixed callables —
callable bucket, ``coupon_type == fixed``, and a real call gap (maturity - call_date > GAP_DAYS). The
make-whole majority (gap <= 7d, option value ~ 0) route to the vanilla calibrator and are only counted
here. Structured/floating callables stay excluded (v1).

ASSUMPTIONS (data gaps — NOT market-sourced; flagged for Mario):
  * call price = par (100), American from call_date to maturity  (workbook has only a call DATE, no
    price/schedule; the legacy pulled the schedule from Bloomberg). ``call_price`` is a replaceable input.
  * volatility = flat sigma = FIP_VOL (default 0.18) — a defensible lognormal short-rate level, NOT a
    market vol. Output is annotated accordingly.

Cross-check: effective duration vs the custodian 'Duration - effective' (master col AQ) — a free
external benchmark (the 4th agreed invariant; data-dependent, so it lives here not in pytest).

Run on 47:  FIP_VAL_DATE=2009-03-31 FIP_VOL=0.18 PYTHONPATH=src python3 scripts/callable_risk.py
Writes outputs/callable_risk.csv (git-ignored)."""
import os
import sys

sys.path.insert(0, "src")
import numpy as np
import pandas as pd
import openpyxl
from openpyxl.utils import column_index_from_string

from curves.zero_curve import ZeroCurve
from dataio.loaders import load_corporate_terms, load_master
from dataio.universe import build_universe
from pricing.lattice import ShortRateLattice

DATA_DIR = os.environ.get("FIP_DATA_DIR", "data")
WB = os.environ.get("FIP_URS_WB", os.path.join(DATA_DIR, "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"))
VAL = os.environ.get("FIP_VAL_DATE", "2009-03-31")
SIGMA = float(os.environ.get("FIP_VOL", "0.18"))     # ASSUMED flat short-rate vol (not market)
OUT = os.environ.get("FIP_OUT", "outputs/callable_risk.csv")
GAP_DAYS = 366                                        # > this -> genuine call gap (else make-whole)
FREQ_VARIANT = {1: "Annual", 2: "Semiannual"}
pd.set_option("display.width", 240)


def load_aq(path):
    """Custodian 'Duration - effective' (master col AQ), keyed by Asset ID (col S)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["Fixed Income"]
    si, ai = column_index_from_string("S") - 1, column_index_from_string("AQ") - 1
    out = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        if len(row) > max(si, ai) and row[si] is not None:
            out[str(row[si])] = row[ai]
    wb.close()
    return out


def main():
    master = load_master(WB)
    terms = load_corporate_terms(WB)
    canon, excl, funnel, extras = build_universe(master, terms, VAL)
    recon = extras["reconciliation"].drop_duplicates("asset_id").set_index("asset_id")
    recon.index = recon.index.astype(str)
    aq = load_aq(WB)

    cb = excl[excl["primary_reason"] == "callable"].copy()      # fixed, rated, matched, callable
    cb["call_date"] = pd.to_datetime(cb["call_date"], errors="coerce")
    cb["maturity"] = pd.to_datetime(cb["maturity"], errors="coerce")
    cb["gap_days"] = (cb["maturity"] - cb["call_date"]).dt.days
    genuine = cb[cb["gap_days"] > GAP_DAYS].copy()
    makewhole = cb[cb["gap_days"] <= 7]
    print(f"# callable_risk @ {VAL}  sigma={SIGMA:.2%} (ASSUMED)  call=par(100) American (ASSUMED)")
    print(f"# callable bucket={len(cb)}  genuine(gap>{GAP_DAYS}d)={len(genuine)}  make-whole(<=7d, ->vanilla)={len(makewhole)}")

    rows, skip = [], []
    for _, b in genuine.iterrows():
        aid = str(b["asset_id"])
        cpn = pd.to_numeric(b["coupon"], errors="coerce")
        ccy = str(b.get("currency")).strip().upper() if b.get("currency") is not None else "USD"
        try:
            fr = int(b["freq"])
        except (TypeError, ValueError):
            skip.append((aid, f"freq={b['freq']!r}")); continue
        if pd.isna(cpn) or pd.isna(b["maturity"]) or pd.isna(b["call_date"]) or fr not in FREQ_VARIANT:
            skip.append((aid, f"cpn={cpn} mat={b['maturity']} call={b['call_date']} fr={fr}")); continue
        bt = pd.to_numeric(recon.loc[aid, "gold_price"], errors="coerce") if aid in recon.index else np.nan
        if pd.isna(bt) or bt <= 0:
            skip.append((aid, f"bt={bt}")); continue

        T = (b["maturity"] - pd.Timestamp(VAL)).days / 365.25
        first_call = max(0.0, (b["call_date"] - pd.Timestamp(VAL)).days / 365.25)
        try:
            curve = ZeroCurve.from_currency(DATA_DIR, ccy, VAL, freq=FREQ_VARIANT[fr])
        except Exception as e:                                   # GBP non-arb node, unmapped ccy, ...
            skip.append((aid, f"curve {ccy}: {e}")); continue

        lat = ShortRateLattice(curve, T, freq=fr, sigma=SIGMA)
        carr = lat.par_call_array(first_call, 100.0)
        # option value at OAS=0 (raw), then calibrate OAS to BT for callable AND straight
        px_str0 = lat.price_bond(float(cpn), 0.0)
        px_cal0 = lat.price_bond(float(cpn), 0.0, call_price=carr)
        try:
            oas_cal = lat.implied_oas(float(bt), float(cpn), call_price=carr)
            oas_str = lat.implied_oas(float(bt), float(cpn))
        except ValueError as e:
            skip.append((aid, f"no-bracket bt={bt:.2f}: {e}")); continue
        rm_cal = lat.risk_metrics(float(cpn), oas_cal, call_price=carr)
        rm_str = lat.risk_metrics(float(cpn), oas_str)
        if oas_cal < 0:                       # BT above the par-call value -> assumption refuted
            note = "par-call-refuted"
        elif abs(oas_cal - oas_str) < 1e-4:   # call never in the money (bond << par)
            note = "call-not-binding"
        else:
            note = "call-active"
        rows.append(dict(
            asset_id=aid, ccy=ccy, rating=b["rating_bucket"], coupon=float(cpn), freq=fr,
            maturity=b["maturity"].date(), call_date=b["call_date"].date(), gap_yrs=round(b["gap_days"] / 365.25, 2),
            ttm=round(T, 2), bt=float(bt), px_straight_oas0=round(px_str0, 3), px_callable_oas0=round(px_cal0, 3),
            opt_val_oas0=round(px_str0 - px_cal0, 3),
            implied_oas_bp_callable=round(oas_cal * 1e4, 1), implied_oas_bp_straight=round(oas_str * 1e4, 1),
            oas_cost_of_call_bp=round((oas_str - oas_cal) * 1e4, 1),
            eff_dur_callable=round(rm_cal["eff_duration"], 3), eff_dur_straight=round(rm_str["eff_duration"], 3),
            dv01_callable=round(rm_cal["dv01"], 5), convexity_callable=round(rm_cal["convexity"], 1),
            aq_custodian=aq.get(aid), dur_vs_aq=(round(rm_cal["eff_duration"] - aq[aid], 3)
                                                 if aq.get(aid) not in (None, "") else None),
            note=note,
        ))

    df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"\npriced={len(df)}  skipped={len(skip)}")
    for aid, why in skip:
        print("  skip", aid, why)
    if len(df):
        cols = ["asset_id", "ccy", "rating", "coupon", "maturity", "call_date", "gap_yrs", "ttm", "bt",
                "px_straight_oas0", "px_callable_oas0", "opt_val_oas0",
                "implied_oas_bp_straight", "implied_oas_bp_callable", "oas_cost_of_call_bp",
                "eff_dur_straight", "eff_dur_callable", "aq_custodian", "dur_vs_aq", "note"]
        print("\n" + df[cols].to_string(index=False))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
