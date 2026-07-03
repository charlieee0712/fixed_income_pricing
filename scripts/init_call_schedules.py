"""Seed ``data/call_schedules.csv`` from the current genuine-callable universe (one-off bootstrap).

Mario (2026-07-03): the lattice must read its exercise schedule from a standalone data table
(``dataio.call_schedules``). This seeds that table for the genuine fixed callables with the approved
v1 assumption — ``call_date`` = master col AB (via the universe pipeline), ``call_price`` = 100 (par
call). The schema supports multiple rows per asset; the seed writes one row each.

When a real (Bloomberg / FISD) schedule arrives, EDIT THE CSV — do NOT re-run this script: it refuses
to overwrite an existing file, so a hand-/vendor-populated table is never clobbered. That is the whole
point of the data/logic split — the pricing code never changes, only this CSV.

Run on 47:  FIP_VAL_DATE=2009-03-31 PYTHONPATH=src python3 scripts/init_call_schedules.py
Writes data/call_schedules.csv (git-ignored — holds client asset_ids)."""
import os
import sys

sys.path.insert(0, "src")
import pandas as pd

from dataio.loaders import load_corporate_terms, load_master
from dataio.universe import build_universe

DATA_DIR = os.environ.get("FIP_DATA_DIR", "data")
WB = os.environ.get("FIP_URS_WB", os.path.join(DATA_DIR, "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"))
VAL = os.environ.get("FIP_VAL_DATE", "2009-03-31")
OUT = os.environ.get("FIP_CALL_SCHED", os.path.join(DATA_DIR, "call_schedules.csv"))
GAP_DAYS = 366                 # > this -> genuine call gap (matches scripts/callable_risk.py)
CALL_PRICE = 100.0             # v1 par-call assumption (Mario); replace per-row with the real schedule


def main():
    if os.path.exists(OUT):
        print(f"{OUT} already exists -- refusing to overwrite (edit it directly to add real schedules).")
        return
    master = load_master(WB)
    terms = load_corporate_terms(WB)
    _, excl, _, _ = build_universe(master, terms, VAL)
    cb = excl[excl["primary_reason"] == "callable"].copy()
    cb["call_date"] = pd.to_datetime(cb["call_date"], errors="coerce")
    cb["maturity"] = pd.to_datetime(cb["maturity"], errors="coerce")
    cb["gap_days"] = (cb["maturity"] - cb["call_date"]).dt.days
    genuine = cb[cb["gap_days"] > GAP_DAYS].copy()

    rows = [{"asset_id": str(b["asset_id"]), "call_date": b["call_date"].date(), "call_price": CALL_PRICE}
            for _, b in genuine.iterrows() if pd.notna(b["call_date"])]
    df = pd.DataFrame(rows, columns=["asset_id", "call_date", "call_price"]).sort_values("asset_id")
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"wrote {OUT}: {len(df)} genuine callable(s), call_price={CALL_PRICE} par, call_date <- master AB")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
