"""Monthly-sheet vanilla reconciliation driver (Gates 2-3 of the Rev-B plan).

Prices the golden table's vanilla populations with the legacy-parity mode
(src/recon) on the zeroyield4-replica curves and diffs against the sheet's
own cached outputs:

  core : corp/agency-like asset classes x MTY_typ "AT MATURITY" x FIXED
  govt : asset class "Government Bonds" x FIXED (Corp* dispatch is
         unconditional there; NO 30y cap on that path)
  spec : corp/agency-like x dead MTY_typ cache (0/blank/#NAME?) x FIXED,
         run speculatively for empirical routing (parity-match => was
         at-maturity; else route-unknown)

Per-row metrics: d_pv  = parity PV at the sheet's own OAS  minus V (the
sheet's reprice at that OAS; V==W on the non-option path) — the pure
pricing-function fidelity test, no solver involved; d_oas = our implied OAS
minus P; d_q (duration at legacy P), d_r/d_s (P+-10bp reprices), d_t (T/U
vs reprice on zero-twist rows).

Usage (on 47):
  PYTHONPATH=src FIP_RECON_MODE=pilot python3 scripts/monthly_recon_run.py
  PYTHONPATH=src FIP_RECON_MODE=bulk  python3 scripts/monthly_recon_run.py
Requires outputs/monthly_golden_rows.csv (scripts/monthly_extract_golden.py).
"""

import csv
import os
from collections import Counter, defaultdict
from datetime import date, datetime

from recon.monthly_curve import build_tables, gap_fill_usd, load_pillars
from recon.parity import buggy_pv, duration_legacy, implied_oas, month_count, parity_pv

GOLDEN = os.path.join(os.environ.get("FIP_OUT", "outputs"), "monthly_golden_rows.csv")
OUT_ROWS = os.path.join(os.environ.get("FIP_OUT", "outputs"), "monthly_recon_rows.csv")
MODE = os.environ.get("FIP_RECON_MODE", "pilot")

VAL_DATES = ("2010-03-01", "2012-06-01", "2012-12-12")
CORP_LIKE = ("corporate", "government a", "short term", "fixed income long")
DEAD_AB = ("", "0", "#NAME?")


def fnum(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return v


def fdate(s):
    s = (s or "").strip()
    if not s or s.upper() == "NULL":
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%m/%d/%Y").date()
    except ValueError:
        return None


def classify(row):
    an = row["asset_sub_class"].strip().lower()
    if row["cpn_typ"].strip().upper() != "FIXED":
        return None
    if an.startswith("government b"):
        return "govt"
    if any(an.startswith(p) for p in CORP_LIKE):
        ab = row["mty_typ"].strip().upper()
        if ab == "AT MATURITY":
            return "core"
        if ab in DEAD_AB:
            return "spec"
    return None


def process(row, tables):
    """Returns a result dict with 'reason' and (where computable) metrics."""
    out = {
        "sheet_row": row["sheet_row"], "set": row["_set"], "val": row["valuation"],
        "name": row["name"][:42], "sec_id": row["sec_id"], "ccy": row["ccy"].strip(),
        "freq": None, "months": None, "cpn": None, "B": None, "P": None,
        "our_oas": None, "d_oas": None, "V": None, "pv_P": None, "d_pv": None,
        "Q": None, "q_ours": None, "d_q": None, "d_r": None, "d_s": None,
        "zero_twist": "", "d_t": None,
        "bbg_I": None, "d_i_ours": None, "d_i_legacy": None,
        "bbg_AD": None, "d_ad_ours": None, "d_ad_legacy": None, "reason": "",
    }
    if out["ccy"].upper() != "USD":
        out["reason"] = "non-usd-deferred"
        return out
    praw = row["P_oas"].strip()
    P = fnum(praw)
    if P is None:
        out["reason"] = "sheet-stale-cache"
        return out
    out["P"] = P
    B = fnum(row["price"])
    out["B"] = B
    C = fnum(row["cpn"])
    out["cpn"] = C
    freq = fnum(row["cpn_freq"])
    freq = int(freq) if freq is not None else None
    out["freq"] = freq
    mat = fdate(row["maturity"])
    val = fdate(row["valuation"])
    dead_terms = (C is None or C <= 0.0 or freq not in (1, 2, 4, 12)
                  or B is None or B <= 0.0)
    if P == 0.0:
        out["reason"] = "legacy-dead"
        return out
    if dead_terms:
        out["reason"] = "anomaly-unexpected-live"
        return out
    if mat is None or val is None:
        out["reason"] = "term-missing"
        return out
    months = month_count(val, mat, apply_cap=(row["_set"] != "govt"))
    out["months"] = months
    salti = 12 // freq
    if (months // salti) * salti < salti:
        out["reason"] = "near-maturity-undefined"
        return out
    if months > 360:
        out["reason"] = "beyond-curve"
        return out

    table = tables[row["valuation"]][freq]
    pv_P = parity_pv(table, freq, C, months, P)
    out["pv_P"] = pv_P
    V, W = fnum(row["V_vol_up"]), fnum(row["W_vol_base"])
    if V is not None and W is not None and abs(V - W) < 5e-3:
        out["V"] = V
        out["d_pv"] = pv_P - V
    our = implied_oas(table, freq, C, months, B)
    out["our_oas"] = our
    Q = fnum(row["Q_dur"])
    out["Q"] = Q
    q_ours = duration_legacy(table, freq, C, months, P)
    out["q_ours"] = q_ours
    if Q is not None and q_ours is not None:
        out["d_q"] = q_ours - Q
    R, S = fnum(row["R_widen"]), fnum(row["S_tighten"])
    if R is not None:
        out["d_r"] = parity_pv(table, freq, C, months, P + 10.0) - R
    if S is not None:
        out["d_s"] = parity_pv(table, freq, C, months, P - 10.0) - S
    T, U = fnum(row["T_steep"]), fnum(row["U_flat"])
    if T is not None and U is not None and abs(T - U) < 5e-3:
        out["zero_twist"] = "y"
        out["d_t"] = pv_P - T
    # three-way legs (session-independent): Bloomberg eff-dur (col I) and OAS (col AD)
    bbg_i = fnum(row["bbg_eff_dur"])
    if bbg_i is not None and bbg_i != 0.0:
        out["bbg_I"] = bbg_i
        q_full = duration_legacy(table, freq, C, months, our if our is not None else P)
        if q_full is not None:
            out["d_i_ours"] = q_full - bbg_i
        if Q is not None:
            out["d_i_legacy"] = Q - bbg_i
    bbg_ad = fnum(row["AD_bbg_oas"])
    if bbg_ad is not None and bbg_ad != 0.0:
        out["bbg_AD"] = bbg_ad
        if our is not None:
            out["d_ad_ours"] = our - bbg_ad
        out["d_ad_legacy"] = P - bbg_ad
    if P >= 999.0:
        out["reason"] = "legacy-solver-cap"
    else:
        out["reason"] = "compared"
        if our is not None:
            out["d_oas"] = our - P
    return out


def pct(sorted_abs, q):
    if not sorted_abs:
        return None
    k = min(len(sorted_abs) - 1, int(q * len(sorted_abs)))
    return sorted_abs[k]


def fmt(v, nd=3):
    return "" if v is None else f"{v:.{nd}f}"


def summarize(results):
    print("\n=== summary by set x valuation date ===")
    groups = defaultdict(list)
    for r in results:
        groups[(r["set"], r["val"])].append(r)
    for (s, v), rs in sorted(groups.items()):
        reasons = Counter(r["reason"] for r in rs)
        comp = [r for r in rs if r["reason"] == "compared"]
        print(f"\n[{s} @ {v}] n={len(rs)}  reasons: {dict(reasons)}")
        if not comp:
            continue
        doas = sorted(abs(r["d_oas"]) for r in comp if r["d_oas"] is not None)
        dpv = sorted(abs(r["d_pv"]) for r in comp if r["d_pv"] is not None)
        dq = sorted(abs(r["d_q"]) for r in comp if r["d_q"] is not None)
        dr = sorted(abs(r["d_r"]) for r in comp if r["d_r"] is not None)
        dt = sorted(abs(r["d_t"]) for r in comp if r["d_t"] is not None)
        if doas:
            le2 = sum(1 for x in doas if x <= 2.0) / len(doas)
            le10 = sum(1 for x in doas if x <= 10.0) / len(doas)
            print(f"  |d_oas| bp   n={len(doas)}  med={fmt(pct(doas,0.5))} "
                  f"p90={fmt(pct(doas,0.9))} p95={fmt(pct(doas,0.95))} "
                  f"max={fmt(doas[-1],1)}  <=2bp {le2:.0%}  <=10bp {le10:.0%}")
        if dpv:
            print(f"  |d_pv| /100  n={len(dpv)}  med={fmt(pct(dpv,0.5),4)} "
                  f"p95={fmt(pct(dpv,0.95),4)} max={fmt(dpv[-1],4)}")
        if dq:
            le05 = sum(1 for x in dq if x <= 0.05) / len(dq)
            print(f"  |d_q| yrs    n={len(dq)}  med={fmt(pct(dq,0.5),4)} "
                  f"p95={fmt(pct(dq,0.95),4)} max={fmt(dq[-1],3)}  <=0.05y {le05:.0%}")
        if dr:
            print(f"  |d_r| /100   n={len(dr)}  med={fmt(pct(dr,0.5),4)} max={fmt(dr[-1],4)}")
        if dt:
            print(f"  |d_t| /100   n={len(dt)} (zero-twist rows)  med={fmt(pct(dt,0.5),4)} "
                  f"max={fmt(dt[-1],4)}")
        both_i = [(abs(r["d_i_ours"]), abs(r["d_i_legacy"])) for r in rs
                  if r["d_i_ours"] is not None and r["d_i_legacy"] is not None]
        if both_i:
            o = sorted(x for x, _ in both_i)
            l = sorted(x for _, x in both_i)
            win = sum(1 for x, y in both_i if x <= y) / len(both_i)
            print(f"  vs Bbg dur I n={len(both_i)}  med|ours-I|={fmt(pct(o,0.5),3)} "
                  f"med|legacyQ-I|={fmt(pct(l,0.5),3)}  ours-closer {win:.0%}")
        both_ad = [(abs(r["d_ad_ours"]), abs(r["d_ad_legacy"])) for r in rs
                   if r["d_ad_ours"] is not None and r["d_ad_legacy"] is not None]
        if both_ad:
            o = sorted(x for x, _ in both_ad)
            l = sorted(x for _, x in both_ad)
            win = sum(1 for x, y in both_ad if x <= y) / len(both_ad)
            print(f"  vs Bbg OAS AD n={len(both_ad)}  med|ours-AD|={fmt(pct(o,0.5),1)}bp "
                  f"med|legacyP-AD|={fmt(pct(l,0.5),1)}bp  ours-closer {win:.0%}")


def pilot_pick(results):
    core = [r for r in results
            if r["set"] == "core" and r["val"] == "2010-03-01"
            and r["reason"] in ("compared", "legacy-solver-cap")]
    core.sort(key=lambda r: r["months"])
    picks = []
    if core:
        n = len(core)
        idxs = sorted({round(i * (n - 1) / 15) for i in range(16)})
        picks = [core[i] for i in idxs]
        by_cpn = sorted(core, key=lambda r: r["cpn"])
        by_b = sorted(core, key=lambda r: r["B"])
        for extra in (by_cpn[0], by_cpn[-1], by_b[0], by_b[-1]):
            if extra not in picks:
                picks.append(extra)
    govt = [r for r in results
            if r["set"] == "govt" and "TREASURY" in r["name"].upper()
            and r["reason"] == "compared"]
    govt.sort(key=lambda r: r["months"])
    if govt:
        n = len(govt)
        idxs = sorted({round(i * (n - 1) / 4) for i in range(5)})
        picks += [govt[i] for i in idxs]
    return picks


def main():
    tables = {d: build_tables(d) for d in VAL_DATES}
    with open(GOLDEN, newline="") as fh:
        rows = list(csv.DictReader(fh))
    print(f"golden rows loaded: {len(rows)}")

    selected = []
    for row in rows:
        tag = classify(row)
        if tag and row["valuation"] in VAL_DATES:
            row["_set"] = tag
            selected.append(row)
    print(f"selected (core/govt/spec, FIXED): {len(selected)}  "
          f"{Counter(r['_set'] for r in selected)}")

    results = [process(r, tables) for r in selected]

    if MODE == "pilot":
        picks = pilot_pick(results)
        print(f"\n=== Gate-2 pilot ({len(picks)} rows) ===")
        hdr = (f"{'row':>5} {'set':4} {'name':42} {'cpn':>6} {'mo':>4} "
               f"{'B':>8} {'P':>8} {'ours':>9} {'d_oas':>7} "
               f"{'V':>8} {'pv@P':>9} {'d_pv':>8} {'Q':>7} {'q_ours':>7} {'d_q':>7}")
        print(hdr)
        for r in picks:
            print(f"{r['sheet_row']:>5} {r['set']:4} {r['name']:42.42} "
                  f"{fmt(r['cpn'],3):>6} {r['months'] or 0:>4} "
                  f"{fmt(r['B'],3):>8} {fmt(r['P'],1):>8} {fmt(r['our_oas'],2):>9} "
                  f"{fmt(r['d_oas'],2):>7} {fmt(r['V'],3):>8} {fmt(r['pv_P'],3):>9} "
                  f"{fmt(r['d_pv'],4):>8} {fmt(r['Q'],3):>7} {fmt(r['q_ours'],3):>7} "
                  f"{fmt(r['d_q'],4):>7}")
        print("\n--- two-mode checksum (consistent vs deliberate BondPrice-style bug) ---")
        shown = 0
        for r in picks:
            if r["d_pv"] is None or shown >= 3:
                continue
            row = next(x for x in selected if x["sheet_row"] == r["sheet_row"])
            table = tables[r["val"]][r["freq"]]
            bug = buggy_pv(table, r["freq"], r["cpn"], r["months"], r["P"])
            print(f"  row {r['sheet_row']}: |pv-V| consistent={abs(r['d_pv']):.4f}  "
                  f"buggy={abs(bug - r['V']):.4f}")
            shown += 1
        summarize(picks)
        try:
            import numpy as np
            from curves.bootstrap import _bootstrap_frequency
            par41 = gap_fill_usd(load_pillars("2010-03-01"))
            _, z_pct, _ = _bootstrap_frequency(np.array(par41), 2)
            zrep = tables["2010-03-01"][2][0]
            print("\n--- replica vs production bootstrap.py (Semiannual z, bp) @2010-03-01 ---")
            for m in (24, 60, 120, 240, 360):
                if m < len(z_pct):
                    print(f"  t={m/12:5.1f}y  replica={zrep[m]*100:.4f}%  "
                          f"auditable={z_pct[m]:.4f}%  diff={(zrep[m]*100-z_pct[m])*100:+.2f}bp")
        except Exception as e:  # noqa: BLE001
            print(f"(bootstrap.py comparison skipped: {e})")
    else:
        cols = ["sheet_row", "set", "val", "name", "sec_id", "ccy", "freq", "months",
                "cpn", "B", "P", "our_oas", "d_oas", "V", "pv_P", "d_pv", "Q",
                "q_ours", "d_q", "d_r", "d_s", "zero_twist", "d_t",
                "bbg_I", "d_i_ours", "d_i_legacy", "bbg_AD", "d_ad_ours",
                "d_ad_legacy", "reason"]
        with open(OUT_ROWS, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            for r in results:
                w.writerow([r[c] for c in cols])
        print(f"wrote {OUT_ROWS}: {len(results)} rows")
        summarize(results)
        spec = [r for r in results if r["set"] == "spec" and r["reason"] == "compared"]
        if spec:
            match = sum(1 for r in spec if r["d_oas"] is not None and abs(r["d_oas"]) <= 10.0)
            print(f"\nspec (dead-AB) empirical routing: {match}/{len(spec)} rows "
                  f"match vanilla within 10bp -> were at-maturity; rest = route-unknown")


if __name__ == "__main__":
    main()
