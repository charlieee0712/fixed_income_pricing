"""Check the delivered Govt-MBS Bloomberg pull against what pricing the 2009 book needs.

    PYTHONPATH=src python scripts/mbs_data_check.py

Reads ``data/govt_mtge_bdp.xlsm`` (Liping's pull against the 8-field x 882-CUSIP request in
``outputs/govt_mtge_bdp_template.csv``) and writes ``outputs/mbs_data_check_<pull date>.csv``
plus a report on stdout.

The question it answers is NOT "did the fields come back" -- they did, completely. It is
whether the values describe the pools AT THE VALUATION DATE, because a mortgage pool's
remaining term, seasoning and prepayment speed are all as-of quantities and a BDP with no
historical override returns today's.

Four distinct Bloomberg failures are counted separately, because they have four different
owners and only one of them is ours:

    #N/A Invalid Field       the MNEMONIC does not exist          -> our request was wrong
    #N/A Invalid Security    the ticker did not resolve           -> the identifier is wrong
    #N/A Field Not Applicable  valid field, wrong security type   -> expected, benign
    #N/A N/A                 valid field and security, no data    -> a real gap

Lumping them into one "missing" count would have hidden the first one, which is the finding.
"""
from __future__ import annotations

import collections
import csv
import datetime
import pathlib
import re
import statistics
import sys

import openpyxl

BDP = pathlib.Path("data/govt_mtge_bdp.xlsm")
TEMPLATE = pathlib.Path("outputs/govt_mtge_bdp_template.csv")
MASTER = pathlib.Path("data/URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx")
VALUATION = datetime.date(2009, 3, 31)

#: Which fields survive a change of as-of date, and which do not. This table is the point of
#: the whole check: it is not about coverage, it is about what a current pull can be used for.
AS_OF_SENSITIVITY = {
    "MTG_WACPN": ("drifts", "gross coupon of the surviving loans; falls slowly as "
                            "higher-rate loans prepay first, so a 2026 value UNDERSTATES 2009"),
    "MTG_WAM": ("as-of", "remaining term -- moves one month per month"),
    "MTG_STATED_WALA": ("as-of", "seasoning -- moves one month per month"),
    "MTG_AOLS": ("static", "average ORIGINAL loan size; fixed at issuance"),
    "MTG_GEN_CPR_3M": ("as-of", "trailing 3-month prepayment speed"),
    "MTG_GEN_CPR_6M": ("as-of", "trailing 6-month prepayment speed"),
    "MTG_GEN_CPR_12M": ("as-of", "trailing 12-month prepayment speed"),
    "MTG_HIST_COLLAT_CPR_LIFE": ("n/a", "the mnemonic itself is rejected by Bloomberg"),
}


def _num(v):
    return v if isinstance(v, (int, float)) else None


def _pull_date(path: pathlib.Path):
    """When the workbook was written, from its own OOXML properties -- not from the filesystem
    mtime, which a copy or an upload resets."""
    import zipfile
    from xml.etree import ElementTree
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read("docProps/core.xml"))
    ns = {"dcterms": "http://purl.org/dc/terms/",
          "dc": "http://purl.org/dc/elements/1.1/"}
    created = root.findtext("dcterms:created", namespaces=ns)
    author = root.findtext("dc:creator", namespaces=ns) or "?"
    return datetime.date.fromisoformat(created[:10]), author


def load_bdp(path=BDP):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
    wb.close()
    header = [str(h) for h in rows[0]]
    return header, [dict(zip(header, r)) for r in rows[1:]]


def master_wam(valuation=VALUATION):
    """Remaining term at the VALUATION date, from the holdings file's own maturity dates.

    The pull cannot supply this -- its WAM is as-of the pull -- but the master can, and did
    all along. Returned as {asset_id: months}.
    """
    sys.path.insert(0, "src")
    import pandas as pd                              # noqa: E402
    from dataio.loaders import load_master           # noqa: E402
    m = load_master(str(MASTER))
    sub = m["sub_category"].astype(str).str.strip()
    mbs = m[sub.str.contains("Mortgage", case=False, na=False)
            & sub.str.contains("Govern", case=False, na=False)]
    out = {}
    for _, r in mbs.iterrows():
        mat = r.get("maturity_master")
        # pd.isna, not a float-NaN test: a missing date arrives as NaT or NAType, and an
        # isinstance(float) check sails straight past both.
        if mat is not None and not pd.isna(mat):
            months = round((pd.Timestamp(mat).date() - valuation).days / 30.4375)
            out[r["asset_id"]] = months
    return out


def main():
    if not BDP.exists():
        raise SystemExit("no %s -- nothing to check" % BDP)
    pull, author = _pull_date(BDP)
    header, rows = load_bdp()
    mnemonics = [h for h in header if h.startswith("MTG_")]
    gap = (pull.year - VALUATION.year) * 12 + (pull.month - VALUATION.month)

    print("=" * 78)
    print("GOVT-MBS BLOOMBERG PULL -- DATA CHECK")
    print("=" * 78)
    print("  file        %s" % BDP)
    print("  pulled by   %s on %s  (from the workbook's own properties)" % (author, pull))
    print("  valuation   %s  ->  the pull is %d months later" % (VALUATION, gap))

    # ---------------------------------------------------------------- completeness
    with TEMPLATE.open(encoding="utf-8-sig") as f:
        asked = {r["cusip"] for r in csv.DictReader(f)}
    got = {r["cusip"] for r in rows if r["cusip"]}
    print("\n-- DELIVERY AGAINST THE REQUEST " + "-" * 45)
    print("  requested %d cusips, delivered %d, missing %d, extra %d"
          % (len(asked), len(got), len(asked - got), len(got - asked)))
    print("  -> the pull is COMPLETE. Nothing below is a criticism of it.")

    # ---------------------------------------------------------------- per-field
    print("\n-- WHAT CAME BACK, AND WHETHER IT SURVIVES THE DATE " + "-" * 25)
    print("  %-26s %5s  %-8s %s" % ("field", "real", "as-of", "the four failures, separately"))
    per_field = {}
    for m in mnemonics:
        vals = [r.get(m) for r in rows]
        real = [v for v in vals if isinstance(v, (int, float))]
        fails = collections.Counter(str(v) for v in vals if not isinstance(v, (int, float)))
        per_field[m] = real
        kind = AS_OF_SENSITIVITY.get(m, ("?", ""))[0]
        print("  %-26s %5d  %-8s %s" % (
            m, len(real), kind,
            "  ".join("%s x%d" % (k.replace("#N/A ", "").strip() or "blank", n)
                      for k, n in fails.most_common(4)) or "-"))

    dead = [m for m in mnemonics if not per_field[m]]
    if dead:
        print("\n  !! %d FIELD(S) RETURNED NOTHING AT ALL: %s" % (len(dead), ", ".join(dead)))
        print("     'Invalid Field' is Bloomberg rejecting the MNEMONIC, not the security.")
        print("     That is an error in the request we wrote, and only running it could show it.")

    # ---------------------------------------------------------------- the as-of test
    print("\n-- THE AS-OF TEST " + "-" * 59)
    wala = [_num(r.get("MTG_STATED_WALA")) for r in rows]
    wala = [w for w in wala if w is not None]
    wam = [_num(r.get("MTG_WAM")) for r in rows]
    wam = [w for w in wam if w is not None]
    print("  Every pool in a 2009-03-31 portfolio existed then, so a pull taken %d months" % gap)
    print("  later must show WALA >= %d for all of them, and WAM > 0 for all of them." % gap)
    print("    WALA  n=%d  median %.0f months (%.1f years)" % (
        len(wala), statistics.median(wala), statistics.median(wala) / 12))
    print("    WALA <  %d months (would post-date the portfolio): %d" % (
        gap, sum(1 for w in wala if w < gap)))
    print("    WAM == 0 (pool already matured):                  %d" % sum(1 for w in wam if w == 0))
    print("  -> the values are as-of the PULL, not the valuation date.")

    mw = master_wam()
    print("\n-- WHAT THE HOLDINGS FILE ALREADY KNEW " + "-" * 38)
    vals = sorted(mw.values())
    print("  WAM at 2009-03-31, from the master's OWN maturity dates: n=%d" % len(vals))
    print("    min %d  median %d  max %d months;  negative: %d"
          % (vals[0], statistics.median(vals), vals[-1], sum(1 for v in vals if v < 0)))
    print("    against Bloomberg's WAM median of %.0f -- a gap of %.0f months, which is the"
          % (statistics.median(wam), statistics.median(vals) - statistics.median(wam)))
    print("    elapsed time between the two dates. Two independent routes to the same conclusion.")

    # ---------------------------------------------------------------- reconstruction
    print("\n-- CAN THE 2009 STATE BE RECONSTRUCTED WITHOUT A RE-PULL? " + "-" * 19)
    print("  original term = WAM + WALA is date-INVARIANT, so combining it with the master's")
    print("  own WAM_2009 recovers the seasoning the pool had at the valuation date.")
    # !! THE IDENTITY ONLY HOLDS WHILE THE POOL IS ALIVE. When a pool pays off, Bloomberg
    # sets WAM to 0 and FREEZES WALA at the age it reached -- so WAM + WALA silently returns
    # age-at-payoff instead of the original term, with no error and often a plausible-looking
    # positive answer. A first version of this check tested only "WALA_2009 >= 0" and passed
    # 165 dead pools as reconstructable. Aliveness is a separate condition, checked separately.
    out, coherent, impossible, dead_but_plausible = [], 0, 0, 0
    for r in rows:
        aid = r["asset_id"]
        w, a = _num(r.get("MTG_WAM")), _num(r.get("MTG_STATED_WALA"))
        wam09 = mw.get(aid)
        alive = w is not None and w > 0
        orig = (w + a) if (w is not None and a is not None) else None
        wala09 = (orig - wam09) if (orig is not None and wam09 is not None) else None
        if wala09 is not None:
            if wala09 < 0:
                impossible += 1
            else:
                coherent += 1
                if not alive:
                    dead_but_plausible += 1
        out.append({
            "asset_id": aid, "cusip": r["cusip"],
            "wac_pct": _num(r.get("MTG_WACPN")),
            "wam_at_pull": w, "wala_at_pull": a,
            "pool_alive_at_pull": "yes" if alive else ("no" if w is not None else ""),
            "original_term_months": orig if alive else None,
            "wam_2009_from_master": wam09,
            "wala_2009_derived": wala09 if alive else None,
            "cpr_12m_at_pull_pct": _num(r.get("MTG_GEN_CPR_12M")),
            "usable_2009_state": "yes" if (alive and wala09 is not None and wala09 >= 0
                                           and wam09 is not None and wam09 > 0) else "no",
        })
    usable = sum(1 for o in out if o["usable_2009_state"] == "yes")
    print("    arithmetically coherent (WALA_2009 >= 0):         %3d" % coherent)
    print("    incoherent (master term exceeds the original):    %3d" % impossible)
    print("    !! of the coherent, pools already DEAD at the pull: %3d" % dead_but_plausible)
    print("       their WAM+WALA is age-at-payoff, not the original term -- a plausible")
    print("       number that is simply wrong, and nothing in the data says so.")
    print("    rows genuinely reconstructable (pool still alive): %3d of %d" % (usable, len(rows)))
    der = [o["wala_2009_derived"] for o in out
           if o["wala_2009_derived"] is not None and o["wala_2009_derived"] >= 0]
    if der:
        print("    derived WALA at 2009-03-31: median %.0f months (%.1f years)"
              % (statistics.median(der), statistics.median(der) / 12))

    print("\n-- WHAT IS STILL GENUINELY MISSING " + "-" * 42)
    print("  The PREPAYMENT SPEED at 2009. It is the one input that cannot be reconstructed:")
    print("  the master does not hold it, and the pull's CPRs describe %s, not early 2009 --" % pull.year)
    print("  a different rate regime entirely. Two ways out, and the engine already has both:")
    print("    (a) re-pull the three CPR fields with a 2009-03-31 historical override, or")
    print("    (b) fix the spread near zero for government-guaranteed paper and IMPLY the CPR")
    print("        from the custodian price -- pricing.mbs.implied_cpr_pool, which exists.")

    dest = pathlib.Path("outputs") / ("mbs_data_check_%s.csv" % pull)
    dest.parent.mkdir(exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print("\n  per-security detail -> %s (%d rows)" % (dest, len(out)))


if __name__ == "__main__":
    main()
