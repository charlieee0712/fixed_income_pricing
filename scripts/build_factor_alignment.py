"""Build ``data/factor_alignment.csv`` — which Bloomberg month each security's factor
label actually describes.

WHY THIS TABLE EXISTS
---------------------
``src/dataio/factor_history.py`` carries ``BLOOMBERG_MONTH_LAG = 1``: Bloomberg's ``2009-04``
column is the 2009-03-31 position. Measured on 2026-10-23 that is right for the Government
MBS pools it serves — **238 of the 241 that can be decided** — and wrong for most of the 412
CMO / CMBS / ABS securities, where 168 of 191 do **not** shift.

⚠️⚠️ **And it is not an asset-class rule either.** 23 CMOs and 13 ABS go the other way from
their own class; two private-label CMOs with opposite alignment are ``US007036TB25``
(``2009-03``) and ``US000780LD65`` (``2009-04``). A class rule gets 36 securities wrong, and
gets them wrong invisibly, because a factor one month out is still a plausible factor.

THE METHOD: ask each series about itself
----------------------------------------
We hold the custodian's own ``paydown_factor`` at the valuation date for almost all of these.
So rather than reason about publication conventions, invert against a number already trusted —
the move that recovered the TIPS index ratios in September:

    which of your own months equals this number?

The answer is the lag, per security, with its residual recorded so a reader can see why.

⚠️ **A security whose factor did not move cannot answer**, and silence is not agreement: those
rows get the class majority as a **named default** (``lag_source``), never a quiet pick. The
choice is inert at the valuation date — that is what made them silent — but it shifts the
whole forward path, so the row says so.

WHAT IS IN THE TABLE, AND WHAT USES IT
--------------------------------------
Both populations get a row: the 371 CMO / CMBS / ABS securities of the 2026-10-23 delivery
and the 376 Government MBS pools of the September pull. ⚠️ **Writing a row changes nothing on
its own.** ``factor_history.py`` still applies its constant to the Government MBS, and
``tests/test_factor_alignment.py`` pins the fact that the table agrees with that constant
except on three named securities. Switching those over moves a published artifact, so it is a
deliberate step of its own, never a side effect of building this table.

Run: ``PYTHONPATH=src python scripts/build_factor_alignment.py``
"""

import collections
import csv
import os
import sys

import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

import pool_risk as D                                               # noqa: E402
from dataio.factor_history import (BLOOMBERG_MONTH_LAG,             # noqa: E402
                                   load_factor_history)
from dataio.phase2 import load_master_phase2                        # noqa: E402

HISTORY_412 = os.path.join("data", "factor_history_412.csv")
WORKBOOK_412 = os.path.join("data", "factor_history_412_2026-10-23.xlsx")
OUT = os.path.join("data", "factor_alignment.csv")

VALUATION = (2009, 3)

#: Two months are "the same number" below this relative gap. The securities that match do so
#: at ~1e-8 and the one that does not is at 2.3e-4, so this separates cleanly; it is not a
#: knob to tune.
TOL_EXACT = 1e-6

#: No month matched exactly, but one is close enough to be the same security's figure rather
#: than a coincidence. ``008684AA0`` sits at 2.3e-4. Beyond this the row is left undetermined.
TOL_NEAREST = 1e-3

#: Alignment is a question about neighbouring months. A match four months away is not an
#: alignment, it is a different balance that happens to be equal.
MAX_OFFSET = 2

FIELDS = ["cusip", "month_lag", "status", "lag_source", "residual", "matched_month",
          "sub_category", "population"]


def _offset(label):
    y, m = (int(x) for x in label.split("-"))
    return (y * 12 + m - 1) - (VALUATION[0] * 12 + VALUATION[1] - 1)


def _load_history(path):
    out = collections.defaultdict(dict)
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            out[row["cusip"]][row["bloomberg_month"]] = float(row["factor"])
    return out


def _custodian():
    master = load_master_phase2(D.WB)
    master["paydown_factor"] = pd.to_numeric(master["paydown_factor"], errors="coerce")
    factor, klass, by_isin = {}, {}, {}
    for aid, isin, pf, sub in zip(master["asset_id"], master["isin"],
                                  master["paydown_factor"], master["sub_category"]):
        if aid is None:
            continue
        aid = str(aid)
        if pd.notna(pf):
            factor.setdefault(aid, float(pf))
        klass.setdefault(aid, str(sub))
        if isinstance(isin, str) and len(isin.strip()) >= 11:
            by_isin.setdefault(isin.strip()[2:11], aid)
    return factor, klass, by_isin


def _decide(months, pf):
    """``(status, lag, residual, matched_month)`` from one series and one custodian factor."""
    if pf is None or pf <= 0:
        return "no-custodian-factor", None, None, None
    near = [(lab, val) for lab, val in months.items() if abs(_offset(lab)) <= MAX_OFFSET]
    if not near:
        return "out-of-range", None, None, None
    scored = sorted((abs(val - pf) / pf, lab) for lab, val in near)
    exact = [lab for res, lab in scored if res < TOL_EXACT]
    if len(exact) == 1:
        res = next(r for r, lab in scored if lab == exact[0])
        return "matched", _offset(exact[0]), res, exact[0]
    if len(exact) > 1:
        return "tied", None, scored[0][0], ",".join(sorted(exact))
    res, lab = scored[0]
    if res < TOL_NEAREST:
        return "nearest", _offset(lab), res, lab
    return "unmatched", None, res, lab


def main() -> int:
    history = _load_history(HISTORY_412)
    govt = load_factor_history()
    factor, klass, isin2aid = _custodian()

    overlap = sorted(set(history) & set(govt))
    if overlap:
        print("REFUSING: %d CUSIPs appear in both factor files: %s"
              % (len(overlap), overlap[:5]))
        return 2

    raw = pd.read_excel(WORKBOOK_412, sheet_name="securities", header=None)
    cusip2aid = {}
    for r in range(2, raw.shape[0]):
        cu, aid = raw.iat[r, 1], raw.iat[r, 3]
        if not pd.isna(cu) and not pd.isna(aid):
            cusip2aid[str(cu).strip()] = str(aid).strip()

    decided = {}
    for cusip, months in history.items():
        aid = cusip2aid.get(cusip, "")
        decided[cusip] = (_decide(months, factor.get(aid)), klass.get(aid, "unknown"),
                          "412-2026-10-23")
    for cusip, months in govt.items():
        aid = isin2aid.get(cusip, "")
        decided[cusip] = (_decide(months, factor.get(aid)), klass.get(aid, "unknown"),
                          "376-2026-09-25")

    # the class majority, computed only from the rows that answered for themselves
    votes = collections.defaultdict(collections.Counter)
    for (status, lag, _res, _lab), sub, _pop in decided.values():
        if status == "matched":
            votes[sub][lag] += 1
    default = {sub: c.most_common(1)[0][0] for sub, c in votes.items()}

    print("WHAT EACH SERIES SAYS ABOUT ITSELF")
    table = collections.defaultdict(collections.Counter)
    for (status, _lag, _res, _lab), sub, pop in decided.values():
        table[(pop, sub)][status] += 1
    for pop, sub in sorted(table):
        tot = sum(table[(pop, sub)].values())
        print("   %-16s %-34s n=%3d  class default %+d"
              % (pop, sub[:34], tot, default.get(sub, 0)))
        for status, n in table[(pop, sub)].most_common():
            print("      %-22s %3d" % (status, n))

    rows, applied = [], collections.Counter()
    for cusip in sorted(decided):
        (status, lag, res, lab), sub, pop = decided[cusip]
        if lag is None:
            lag = default.get(sub, BLOOMBERG_MONTH_LAG)
            if status == "tied" and lab:
                lag = sorted((_offset(x) for x in lab.split(",")),
                             key=lambda o, d=lag: (abs(o - d), o))[0]
            source = "class-majority-default"
        else:
            source = "custodian-paydown-factor"
        applied[(pop, status, lag)] += 1
        rows.append({"cusip": cusip, "month_lag": lag, "status": status,
                     "lag_source": source,
                     "residual": ("" if res is None else "%.3e" % res),
                     "matched_month": lab or "", "sub_category": sub, "population": pop})

    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print()
    print("WROTE %s  (%d securities)" % (OUT, len(rows)))
    for (pop, status, lag), n in sorted(applied.items()):
        print("   %-16s %-22s lag %+d  %3d" % (pop, status, lag, n))
    own = sum(n for (_p, s, _l), n in applied.items() if s in ("matched", "nearest"))
    print("   decided by the security itself : %d of %d (%.0f%%)"
          % (own, len(rows), 100.0 * own / len(rows)))

    disagree = [r for r in rows
                if r["population"] == "376-2026-09-25"
                and r["lag_source"] == "custodian-paydown-factor"
                and r["month_lag"] != BLOOMBERG_MONTH_LAG]
    print()
    print("THE GOVERNMENT MBS POOLS vs THE CONSTANT (BLOOMBERG_MONTH_LAG = %d)"
          % BLOOMBERG_MONTH_LAG)
    print("   securities whose OWN factor disagrees with it: %d" % len(disagree))
    for r in disagree:
        print("      %-12s says %+d (matched %s, residual %s)"
              % (r["cusip"], r["month_lag"], r["matched_month"], r["residual"]))
    print("   NOT acted on here: the loader still applies the constant to this population,")
    print("   and a test pins these three as the only disagreement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
