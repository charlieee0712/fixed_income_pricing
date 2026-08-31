"""Column-F delivery audit — the six cells Mario marked, reconciled to the live output.

Mario annotated a new column F on the workbook's ``Pivot of Corp Bonds`` sheet at the
2026-08-27 meeting and marked six coupon-family rows ``no``. This script is the
machine-checkable answer: it joins the pivot's own labels to the production output and
emits one row per held security behind those cells, plus the per-cell aggregate.

It exists so no number in the Mario-facing report is typed by hand. Every count in that
report should be traceable to a line of this file's output.

⚠️ **Four populations, and they are easy to confuse.** The script prints all four and
labels every count with the one it belongs to:

    676  ROWS on the Corporate Bonds tab — what Mario's pivot counts
    617  unique SECURITIES on that tab: 59 asset IDs are listed more than once
    565  held / rated / matched positions in the output at 2009-03-31
    555  of those, fully model-priced

The row/security distinction is not pedantry. Mario's F13 shows a pivot count of **2**, and
those two rows are the SAME security (``TNTD04283895``) listed twice — one bond, held once,
priced once. Reporting "2 tab rows, 1 held" invites the reading "one of them is not a
holding", which is false. The right sentence is "the tab lists it twice".

Run:  FIP_VAL_DATE=2009-03-31 PYTHONPATH=src python scripts/column_f_audit.py
Writes ``outputs/column_f_delivery_audit_<date>.csv`` (git-ignored) and prints the tables.
"""
import os
import sys

sys.path.insert(0, "src")
import pandas as pd

from dataio.coupon_types import classify_coupon_formula
from dataio.loaders import load_corporate_terms, load_master
from dataio.universe import build_universe
from dataio.term_overrides import load_make_whole_overrides

DATA_DIR = os.environ.get("FIP_DATA_DIR", "data")
WB = os.environ.get("FIP_URS_WB",
                    os.path.join(DATA_DIR, "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"))
VAL = os.environ.get("FIP_VAL_DATE", "2009-03-31")
PRICED = os.environ.get("FIP_PRICED", f"outputs/implied_oas_{VAL}.csv")
OUT = os.environ.get("FIP_OUT", f"outputs/column_f_delivery_audit_{VAL}.csv")
pd.set_option("display.width", 250)

# The six cells, transcribed from the workbook's own sheet6 (not from memory). The label is
# the exact `Coupon_Formula2` string the pivot groups on, so the join cannot drift.
COLUMN_F = {
    "F12": "Fixed → Floating",
    "F13": "7.00% for  t<01-Mar-2006 7.50% for t≥01-Mar-2006",
    "F14": "GBP LIBOR + Spread",
    "F15": "Reference Rate + Spread",
    "F16": "EURIBOR + Spread",
    "F20": "Step-up schedule",
}
# Adjacent, and deliberately NOT part of Mario's six: the same hybrid engine serves these.
ADJACENT_LABEL_CONTAINS = "Reset"

ENGINE = {           # route -> (core engine, asset wrapper, endpoint instrument_type)
    "vanilla": ("core/pricing/analytical.py", "assets/corporate/vanilla.py", "vanilla"),
    "make-whole-as-vanilla": ("core/pricing/analytical.py", "assets/corporate/vanilla.py", "vanilla"),
    "vanilla-schedule": ("core/pricing/coupon_schedule.py + analytical.py",
                         "assets/corporate/stepped.py", "stepped"),
    "floating": ("core/pricing/floating.py", "assets/corporate/floating.py", "floating"),
    "hybrid": ("core/pricing/hybrid.py", "assets/corporate/hybrid.py", "fixed_to_floating"),
    "hybrid-margin-unavailable": ("(not priced)", "assets/corporate/hybrid.py", "fixed_to_floating"),
    "recovery": ("(not priced: carried at the custodian mark)", "-", "-"),
    "frn-curve-blocked": ("(not priced)", "assets/corporate/floating.py", "floating"),
}
LANDING = {          # route -> the data file whose arrival unblocks it
    "hybrid-margin-unavailable": "data/hybrid_switch_terms.csv (post-switch margin)",
}


def tab_rows(path):
    """Every Corporate Bonds tab row with its raw `Coupon_Formula2` label — the pivot's own
    population, before any held/rated/matched filtering."""
    terms = load_corporate_terms(path)
    col = "coupon_formula2" if "coupon_formula2" in terms.columns else None
    if col is None:
        raise SystemExit(f"no coupon_formula2 column in {path}; have {list(terms.columns)}")
    out = terms[["asset_id", col]].copy()
    out.columns = ["asset_id", "label"]
    out["asset_id"] = out["asset_id"].astype(str)
    out["coupon_class"] = out["label"].map(classify_coupon_formula)
    return out                                   # ROWS, duplicates intact — the pivot's own view


def main():
    tab = tab_rows(WB)
    priced = pd.read_csv(PRICED)
    priced["asset_id"] = priced["asset_id"].astype(str)
    master = load_master(WB)
    master["asset_id"] = master["asset_id"].astype(str)
    desc = master.set_index("asset_id")

    canon, excl, _funnel, _extras = build_universe(
        load_master(WB), load_corporate_terms(WB), VAL,
        make_whole_overrides=load_make_whole_overrides(
            os.path.join(DATA_DIR, "make_whole_overrides.csv")))

    print(f"# column_f_audit @ {VAL}")
    print(f"# populations: tab ROWS={len(tab)}  unique SECURITIES on the tab="
          f"{tab['asset_id'].nunique()}  output rows={len(priced)}  "
          f"model-priced={int(priced['implied_bp'].notna().sum())}")
    print(f"#   ({len(tab) - tab['asset_id'].nunique()} asset IDs are listed more than once "
          f"on the tab; the pivot counts ROWS)")
    print()

    rows = []
    for cell, label in COLUMN_F.items():
        ids = set(tab.loc[tab["label"] == label, "asset_id"])
        held = priced[priced["asset_id"].isin(ids)]
        for _, b in held.iterrows():
            aid = b["asset_id"]
            route = str(b["route"])
            core, wrapper, itype = ENGINE.get(route, ("?", "?", "?"))
            rows.append(dict(
                cell=cell, workbook_label=label, asset_id=aid,
                security=str(desc.loc[aid].get("description", "")) if aid in desc.index else "",
                currency=b.get("ccy"), coupon=b.get("coupon"), maturity=b.get("maturity"),
                route=route, core_engine=core, asset_wrapper=wrapper, endpoint_type=itype,
                priced=pd.notna(b.get("implied_bp")),
                implied_oas_bp=b.get("implied_bp"), eff_duration=b.get("eff_dur"),
                custodian_price=b.get("bt"),
                missing_field=("post-switch margin" if route == "hybrid-margin-unavailable"
                               else ("n/a — defaulted" if route == "recovery" else "")),
                landing_file=LANDING.get(route, ""),
                in_output=True,
            ))
        # tab rows that are not held positions are stated, not silently dropped
        for aid in sorted(ids - set(held["asset_id"])):
            rows.append(dict(cell=cell, workbook_label=label, asset_id=aid, security="",
                             currency="", coupon="", maturity="", route="not-a-held-position",
                             core_engine="-", asset_wrapper="-", endpoint_type="-", priced=False,
                             implied_oas_bp="", eff_duration="", custodian_price="",
                             missing_field="", landing_file="", in_output=False))

    audit = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    audit.to_csv(OUT, index=False)

    # ---- per-cell aggregate: the table the report shows ----
    print("Mario's six cells  (pivot ROWS -> unique SECURITIES -> held -> priced)")
    print(f"{'cell':<6}{'workbook label':<46}{'rows':>6}{'secs':>6}{'held':>6}{'priced':>8}"
          f"{'not priced':>12}")
    tot = dict(rows=0, secs=0, held=0, priced=0)
    for cell, label in COLUMN_F.items():
        block = audit[audit["cell"] == cell]
        n_rows = int((tab["label"] == label).sum())          # what the pivot counts
        n_secs, n_held = len(block), int(block["in_output"].sum())
        n_priced = int(block["priced"].sum())
        for k, v in (("rows", n_rows), ("secs", n_secs), ("held", n_held), ("priced", n_priced)):
            tot[k] += v
        print(f"{cell:<6}{label[:44]:<46}{n_rows:>6}{n_secs:>6}{n_held:>6}{n_priced:>8}"
              f"{n_held - n_priced:>12}")
    print(f"{'':<6}{'TOTAL':<46}{tot['rows']:>6}{tot['secs']:>6}{tot['held']:>6}"
          f"{tot['priced']:>8}{tot['held'] - tot['priced']:>12}")
    if tot["rows"] != tot["secs"]:
        dup = tot["rows"] - tot["secs"]
        print(f"       ^ the {dup} row/security difference is a DUPLICATE LISTING, not a "
              f"security that is missing from the book")

    # ---- the six that do not price, named ----
    print("\nnot model-priced, with the reason and what unblocks each")
    unpriced = audit[(audit["in_output"]) & (~audit["priced"])]
    for _, r in unpriced.iterrows():
        print(f"  {r['cell']}  {r['asset_id']:<14}{r['route']:<28}{r['missing_field']:<22}"
              f"{r['landing_file']}")

    # ---- adjacent rows 6-11, reported separately as the plan requires ----
    adj = set(tab.loc[tab["label"].astype(str).str.contains(ADJACENT_LABEL_CONTAINS, na=False),
                      "asset_id"])
    adj_held = priced[priced["asset_id"].isin(adj)]
    print(f"\nadjacent (Fixed -> Reset, rows 6-11; NOT part of the six-cell ask): "
          f"tab={len(adj)} held={len(adj_held)} priced={int(adj_held['implied_bp'].notna().sum())}")
    print(f"\nwrote {OUT}  ({len(audit)} rows)")


if __name__ == "__main__":
    main()
