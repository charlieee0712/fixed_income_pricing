"""Build ``data/factor_history_412.csv`` from Bloomberg's 2026-10-23 return.

The 412 CMO / CMBS / ABS securities had no paydown profile of any kind until this delivery.
This script turns the workbook into the same three-column shape the September pull already
uses, so one loader can read either.

THE WORKBOOK'S LAYOUT, discovered rather than assumed
-----------------------------------------------------
Sheet ``securities``:

* columns 0-7 carry **our own request table** pasted back, header on row **1**, the 412
  securities on rows 2-413 (``security``, ``cusip``, ``isin``, ``asset_id``, ``asset_class``,
  ``coupon_type``, ``series_needed``, ``description``);
* from column **9**, one ``BDH`` block per security every **4** columns — row 0 a sequence
  number, row 1 the security string, rows 2+ a ``(date, value)`` pair running DOWN. The two
  remaining columns of each block are empty, which is how we know **no coupon series came**.

⚠️ **The block tag is an ISIN**, not the CUSIP string we supplied. The pull was rebuilt from
the ``isin`` column, so the 37 securities that have no ISIN became ``NULL Mtge`` and errored.
That is a keying accident, not a refusal; our request shipped ``<CUSIP> Mtge`` for all 412.

WHAT THIS SCRIPT DOES NOT DO
----------------------------
⚠️⚠️ **It does not shift the month labels.** Bloomberg's own labels are stored verbatim,
exactly as ``data/factor_history.csv`` does, because a stored record should be checkable
against what the terminal returned. Alignment to a valuation date is a separate, per-security
question — see ``docs/three_tier_method_explained_2026-10-06.md`` §3.17. ⚠️ Do **not** assume
this population carries the ``BLOOMBERG_MONTH_LAG`` of the Government MBS pools: measured per
security, most of these do **not** shift.

Run: ``PYTHONPATH=src python scripts/build_factor_history_412.py``
"""

import collections
import csv
import datetime as dt
import os
import sys

import pandas as pd

WORKBOOK = os.path.join("data", "factor_history_412_2026-10-23.xlsx")
SHEET = "securities"
OUT = os.path.join("data", "factor_history_412.csv")

#: Blocks begin here and repeat every FIRST_BLOCK_STRIDE columns; the tag sits on TAG_ROW.
FIRST_BLOCK_COL = 9
BLOCK_STRIDE = 4
TAG_ROW = 1

#: ⚠️ One series came back with a single observation dated 1970-01-01 — an epoch artefact,
#: not a factor in 1970. Observations before this floor are dropped and NAMED, never silently.
EPOCH_FLOOR = dt.date(1990, 1, 1)

#: What the 2026-10-23 delivery contained. Asserted so the record cannot drift unnoticed.
EXPECTED_REQUESTED = 412
EXPECTED_WITH_ISIN = 375
EXPECTED_BLOCKS_WITH_DATA = 372


def _request_table(frame):
    """``[{column: value}]`` for the 412 rows of our own request table, header on row 1."""
    header = [str(frame.iat[TAG_ROW, c]).strip() for c in range(8)]
    rows = []
    for r in range(TAG_ROW + 1, frame.shape[0]):
        rec = {header[c]: (None if pd.isna(frame.iat[r, c]) else frame.iat[r, c])
               for c in range(8)}
        if rec.get("cusip"):
            rows.append(rec)
    return rows


def _blocks(frame):
    """``({tag: {date: factor}}, {tag: error_text})`` over the BDH blocks."""
    series, errors = {}, {}
    for col in range(FIRST_BLOCK_COL, frame.shape[1], BLOCK_STRIDE):
        tag = frame.iat[TAG_ROW, col]
        if not (isinstance(tag, str) and tag.strip()):
            continue
        tag = tag.strip()
        obs, failure = {}, None
        for r in range(TAG_ROW + 1, frame.shape[0]):
            cell = frame.iat[r, col]
            value = frame.iat[r, col + 1] if col + 1 < frame.shape[1] else None
            if isinstance(cell, str) and cell.startswith("#N/A"):
                failure = cell.strip()
                break
            if pd.isna(cell) or pd.isna(value):
                continue
            obs[pd.Timestamp(cell).date()] = float(value)
        if obs:
            series.setdefault(tag, {}).update(obs)
        elif failure:
            errors[tag] = failure
    return series, errors


def main() -> int:
    frame = pd.read_excel(WORKBOOK, sheet_name=SHEET, header=None)
    asked = _request_table(frame)
    series, errors = _blocks(frame)

    by_isin = {}
    for rec in asked:
        isin = str(rec["isin"]).strip() if rec.get("isin") else ""
        if isin:
            by_isin[isin + " Mtge"] = str(rec["cusip"]).strip()

    print("THE ASK, from the request table the workbook carries")
    print("   securities           : %d" % len(asked))
    print("   with an ISIN         : %d" % len(by_isin))
    print("   marked MTG_FACTOR+CPN: %d"
          % sum(1 for a in asked if "CPN" in str(a.get("series_needed"))))
    if len(asked) != EXPECTED_REQUESTED or len(by_isin) != EXPECTED_WITH_ISIN:
        print("REFUSING: expected %d requested / %d with an ISIN"
              % (EXPECTED_REQUESTED, EXPECTED_WITH_ISIN))
        return 2

    print()
    print("WHAT CAME BACK")
    print("   blocks with data     : %d" % len(series))
    print("   blocks with an error : %d" % len(errors))
    for tag, text in sorted(errors.items()):
        print("      %-24s %s" % (tag, text))
    if len(series) != EXPECTED_BLOCKS_WITH_DATA:
        print("REFUSING: expected %d blocks with data" % EXPECTED_BLOCKS_WITH_DATA)
        return 2

    rows, dropped, unmapped = [], collections.Counter(), []
    seen: dict = {}
    for tag, obs in sorted(series.items()):
        cusip = by_isin.get(tag)
        if cusip is None:
            unmapped.append(tag)
            continue
        for when, factor in sorted(obs.items()):
            if when < EPOCH_FLOOR:
                dropped[cusip] += 1
                continue
            if factor < 0:
                print("REFUSING: negative factor %r for %s at %s" % (factor, cusip, when))
                return 2
            label = "%04d-%02d" % (when.year, when.month)
            key = (cusip, label)
            if key in seen and seen[key] != factor:
                print("REFUSING: %s has two different factors in %s (%r, %r)"
                      % (cusip, label, seen[key], factor))
                return 2
            if key in seen:
                continue
            seen[key] = factor
            rows.append((cusip, label, factor))

    if unmapped:
        print("REFUSING: %d block tags map to no CUSIP: %s" % (len(unmapped), unmapped[:5]))
        return 2

    print()
    print("DROPPED AS PRE-EPOCH (named, not hidden)")
    if dropped:
        for cusip, n in dropped.most_common():
            print("   %-12s %d observation(s) before %s" % (cusip, n, EPOCH_FLOOR))
    else:
        print("   none")

    with open(OUT, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cusip", "bloomberg_month", "factor"])
        writer.writerows(rows)

    securities = sorted({r[0] for r in rows})
    months = sorted({r[1] for r in rows})
    counts = collections.Counter(r[0] for r in rows)
    ordered = sorted(counts.values())
    print()
    print("WROTE %s" % OUT)
    print("   securities           : %d" % len(securities))
    print("   rows                 : %d" % len(rows))
    print("   months span          : %s .. %s" % (months[0], months[-1]))
    print("   observations each    : median %d  min %d  max %d"
          % (ordered[len(ordered) // 2], ordered[0], ordered[-1]))
    print("   carrying 2009-03     : %d" % sum(1 for c in securities
                                               if (c, "2009-03") in seen))
    print("   carrying 2009-04     : %d" % sum(1 for c in securities
                                               if (c, "2009-04") in seen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
