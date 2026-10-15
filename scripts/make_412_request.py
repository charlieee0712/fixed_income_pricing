"""Build the 2026-10-14 request list for the 412 CMO / CMBS / ABS.

⭐ A LIST, NOT A PACK, and that is the decision this script encodes. The 2026-10-02 pack
(`docs/bloomberg_request_2026-10-02/`) carried four prewired formula sheets because it was
built for an operator who might not have the mortgage entitlement, might open a .csv and see
no functions, and could not be asked to debug a transposed spill. **Mario has since run three
pulls himself** -- 2026-10-07 and 2026-10-14, including a transposed multi-value field that
spilled correctly and a 47-column index file -- so that machinery is overhead for him. He gets
the securities and the field names; he builds the pull with his own tooling. The message offers
a ready-to-run sheet if he would rather have one, or is handing it to someone else.

⚠️ AND THREE OF THAT PACK'S FOUR SHEETS ARE NOW WRONG OR OBSOLETE, which is the other reason
not to send it: `01_CHECK_FIRST` is moot for an operator who has already pulled;
`02_factor_history` asked for 375 securities and should ask for 412 (below);
`03_coupon_monthly` was built from a description-pattern union later measured at 40.3% recall;
and `04_coupon_classify` is answered outright by `Type of Coupon`.

⭐⭐ THE 37 ARE BACK. The old pack could write only 375 request lines because 37 of the 412
carried no ISIN or CUSIP in the custodian file -- a caveat its README had to disclose. Every one
of those 37 now has a well-formed CUSIP, supplied by `data/mtge.xlsx`. This script ASSERTS 412.

TWO SERIES, IN ONE SITTING. `MTG_FACTOR` for all 412 and `CPN` for the 201 whose coupon moves.
⚠️ Not two rounds: a moving-coupon bond needs both, because a balance without a coupon and a
coupon without a balance each give no cash flow. That is the standing rule earned on 2026-09-29
-- never ship a request with a second round baked into it.

Field names and window are the ones that RETURNED COMPLETE in September, reused rather than
re-derived: ``MTG_FACTOR`` / ``CPN``, 2009-03-01 to 2026-09-30, security = ``<CUSIP> Mtge``.

Writes `docs/bloomberg_412_request_2026-10-14.xlsx` and refuses on any failed check.
ASCII output only -- the console here is GBK.
"""
from __future__ import annotations

import os
import re
import sys
import collections

import openpyxl
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

sys.path[:0] = ["src", "scripts"]

from dataio.coupon_structure import load_coupon_structure  # noqa: E402
from make_bloomberg_request import (FACTOR_FIELD, COUPON_FIELD,  # noqa: E402
                                    FACTOR_START, FACTOR_END)

OUT = os.path.join("docs", "bloomberg_412_request_2026-10-14.xlsx")

#: The three securitised classes with no paydown profile of any kind.
CLASSES = ("Non-Government Backed C.M.O.s", "Commercial Mortgage-Backed",
           "Asset Backed Securities")

#: Golden counts. A change here must be a deliberate edit, not a silent drift.
EXPECTED = {"Non-Government Backed C.M.O.s": 264, "Commercial Mortgage-Backed": 69,
            "Asset Backed Securities": 79}
EXPECTED_TOTAL = 412
EXPECTED_NEEDS_COUPON = 201


def build():
    cs = load_coupon_structure()
    rows, fail = [], []
    for asset_id, rec in cs.items():
        if rec["sub_category"] not in CLASSES:
            continue
        cusip = (rec["cusip"] or "").strip()
        if not re.fullmatch(r"[0-9A-Z]{9}", cusip):
            fail.append("%s has no well-formed CUSIP (%r)" % (asset_id, cusip))
            continue
        # ⚠️ NOT `rate_behaviour(...) == "rate-sensitive"`, and the difference is 6 securities.
        # That predicate asks "does the coupon respond to RATES", which correctly excludes STEP
        # -- a stepped coupon moves on known dates, not with an index. The question a data
        # request asks is different: "do we KNOW what the coupon will be?" For a stepped bond we
        # do not, because we hold no step schedule, so its realised coupon history is just as
        # useful. `unresolved` goes in for the same reason: not knowing is a reason to ask.
        moves = rec["coupon_type"] not in ("fixed", "zero")
        rows.append({
            "security": cusip + " Mtge",
            "cusip": cusip,
            "isin": rec["isin"],
            "asset_id": asset_id,
            "asset_class": rec["sub_category"],
            "coupon_type": rec["coupon_type"],
            "series_needed": ("%s + %s" % (FACTOR_FIELD, COUPON_FIELD) if moves
                              else FACTOR_FIELD),
            "description": rec["desc_short"],
        })

    by_class = collections.Counter(r["asset_class"] for r in rows)
    needs_coupon = sum(1 for r in rows if COUPON_FIELD in r["series_needed"])
    dupes = [c for c, n in collections.Counter(r["cusip"] for r in rows).items() if n > 1]

    if len(rows) != EXPECTED_TOTAL:
        fail.append("built %d securities, expected %d" % (len(rows), EXPECTED_TOTAL))
    for cls, n in EXPECTED.items():
        if by_class.get(cls) != n:
            fail.append("%s: %s rows, expected %d" % (cls, by_class.get(cls), n))
    if needs_coupon != EXPECTED_NEEDS_COUPON:
        fail.append("%d need a coupon series, expected %d" % (needs_coupon,
                                                              EXPECTED_NEEDS_COUPON))
    if dupes:
        fail.append("duplicate CUSIPs: %s" % dupes[:5])
    return rows, by_class, needs_coupon, fail


def write(rows, needs_coupon):
    wb = openpyxl.Workbook()
    bold = Font(bold=True)

    ws = wb.active
    ws.title = "README"
    for line in [
        "Bloomberg request - 412 securitised holdings with no repayment history",
        "Ryse / URS portfolio, prepared 2026-10-14",
        "",
        "WHAT IS NEEDED - two series, please in one sitting rather than one then the other.",
        "",
        "  1. %s   monthly, %s to %s, for ALL %d securities on the next sheet."
        % (FACTOR_FIELD, FACTOR_START, FACTOR_END, len(rows)),
        "     This is the fraction of the original balance still outstanding each month, and it",
        "     is the same field and window as the pull that came back complete in September -",
        "     just pointed at the securities that request never covered.",
        "",
        "  2. %s   monthly, same window, for the %d whose coupon moves."
        % (COUPON_FIELD, needs_coupon),
        "     The `series_needed` column on the next sheet marks which ones.",
        "",
        "WHY BOTH TOGETHER. For a bond whose coupon moves, a balance with no coupon and a",
        "coupon with no balance each give us no cash flow. Splitting them would mean coming",
        "back a second time for the other half.",
        "",
        "THE SECURITY STRING is the CUSIP followed by a space and Mtge, already built in the",
        "first column of the next sheet so it can be pasted straight in.",
        "",
        "RETURNING IT. Any shape is fine - one row or one column per security, dates as dates.",
        "If the terminal refuses a field or a security, leaving the error text in place is more",
        "useful to us than a blank, because it says which of the two it was.",
        "",
        "NO FORMULAS ARE PREWIRED IN THIS FILE. That is deliberate - the last three pulls came",
        "back clean, so this assumes you would rather build it your own way. If a ready-to-run",
        "sheet would be easier, or if someone else is running it, say so and we will send one.",
    ]:
        ws.append([line])
    ws["A1"].font = bold
    ws.column_dimensions["A"].width = 92

    ws2 = wb.create_sheet("securities")
    cols = ["security", "cusip", "isin", "asset_id", "asset_class", "coupon_type",
            "series_needed", "description"]
    ws2.append(cols)
    for c in ws2[1]:
        c.font = bold
    for r in sorted(rows, key=lambda r: (r["asset_class"], r["cusip"])):
        ws2.append([r[c] for c in cols])
    for i, w in enumerate((16, 12, 14, 15, 32, 13, 24, 46), start=1):
        ws2.column_dimensions[get_column_letter(i)].width = w
    ws2.freeze_panes = "A2"

    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    wb.save(OUT)


def main():
    rows, by_class, needs_coupon, fail = build()
    print("securities built: %d" % len(rows))
    for cls, n in sorted(by_class.items()):
        print("   %-34s %4d" % (cls, n))
    print("   %-34s %4d  (%s + %s)" % ("...whose coupon moves", needs_coupon,
                                       FACTOR_FIELD, COUPON_FIELD))
    print("   %-34s %4d  (%s only)" % ("...fixed or zero", len(rows) - needs_coupon,
                                       FACTOR_FIELD))
    months = 211
    print("\n   request size: %d x %d + %d x %d = %d values"
          % (len(rows), months, needs_coupon, months,
             len(rows) * months + needs_coupon * months))
    print("   (September's pull returned complete at 79,336)")
    if fail:
        print("\nREFUSING TO WRITE -- %d check(s) failed:" % len(fail))
        for f in fail[:10]:
            print("   - %s" % f)
        return 1
    write(rows, needs_coupon)
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
