"""The securities of the 412 that came back without a usable factor history.

The 2026-10-23 pull returned 371 of the 412. This script lists the rest with the reason for
each, so the re-ask is a file someone can run rather than a sentence someone has to act on.

⚠️ **37 of them failed for one reason and it is not a refusal.** Our request shipped a
ready-made Bloomberg ticker in its ``security`` column — ``<CUSIP> Mtge``, verified 412 of 412
— and the pull was rebuilt from the ``isin`` column instead. Those 37 securities have no ISIN
in the custodian file, so the rebuilt string came out ``NULL Mtge`` and errored. Re-running
them off the ``security`` column is the whole fix.

The other four are separate and are listed as such rather than folded in, because a reader who
sees 41 rows under one heading will assume one cause:

* 2 carried an ISIN and simply came back with no block at all;
* ``US70337U1007`` returned ``#N/A Invalid Security`` — this is ``70337U100``, whose ``100``
  suffix is an equity shape, so the identifier in the custodian file is the likelier fault
  (``missing_data.md`` G7c) and re-pulling the same mnemonic will not help;
* ``126694LU0`` came back with a single observation dated 1970-01-01, which is an epoch
  artefact rather than a factor.

Run: ``PYTHONPATH=src python scripts/make_37_request.py``
"""

import csv
import os
import sys

import pandas as pd

REQUEST = os.path.join("docs", "bloomberg_412_request_2026-10-14.xlsx")
DELIVERY = os.path.join("data", "factor_history_412_2026-10-23.xlsx")
HISTORY = os.path.join("data", "factor_history_412.csv")
OUT = os.path.join("docs", "bloomberg_37_request_2026-10-24.xlsx")

EXPECTED_TOTAL = 412
EXPECTED_NO_ISIN = 37


def main() -> int:
    asked = pd.read_excel(REQUEST, sheet_name="securities")
    if len(asked) != EXPECTED_TOTAL:
        print("REFUSING: the request file has %d rows, expected %d"
              % (len(asked), EXPECTED_TOTAL))
        return 2

    with open(HISTORY, encoding="utf-8", newline="") as fh:
        delivered = {row["cusip"] for row in csv.DictReader(fh)}

    raw = pd.read_excel(DELIVERY, sheet_name="securities", header=None)
    errored = set()
    for col in range(9, raw.shape[1], 4):
        tag = raw.iat[1, col]
        if not (isinstance(tag, str) and tag.strip()):
            continue
        first = raw.iat[2, col]
        if isinstance(first, str) and first.startswith("#N/A"):
            errored.add(tag.strip())

    rows = []
    for _, rec in asked.iterrows():
        cusip = str(rec["cusip"]).strip()
        if cusip in delivered:
            continue
        isin = "" if pd.isna(rec["isin"]) else str(rec["isin"]).strip()
        if not isin:
            reason = ("no ISIN in the custodian file, so the pull built 'NULL Mtge' "
                      "- use the security column")
        elif isin + " Mtge" in errored:
            reason = "returned #N/A Invalid Security on the ISIN ticker"
        elif cusip == "126694LU0":
            reason = "returned a single observation dated 1970-01-01"
        else:
            reason = "no data block came back"
        rows.append({"security": rec["security"], "cusip": cusip, "isin": isin,
                     "asset_class": rec["asset_class"], "coupon_type": rec["coupon_type"],
                     "description": rec["description"], "what_happened": reason})

    frame = pd.DataFrame(rows)
    no_isin = int((frame["isin"] == "").sum())
    print("OF THE %d REQUESTED, %d CAME BACK WITH A USABLE HISTORY" % (len(asked),
                                                                       len(delivered)))
    print("   still outstanding : %d" % len(frame))
    for reason, n in frame["what_happened"].value_counts().items():
        print("      %-66s %d" % (reason[:66], n))
    if no_isin != EXPECTED_NO_ISIN:
        print("REFUSING: %d rows have no ISIN, expected %d" % (no_isin, EXPECTED_NO_ISIN))
        return 2
    if len(delivered) + len(frame) != EXPECTED_TOTAL:
        print("REFUSING: %d delivered + %d outstanding != %d"
              % (len(delivered), len(frame), EXPECTED_TOTAL))
        return 2

    bad = [s for s in frame["security"] if not str(s).endswith(" Mtge")]
    if bad:
        print("REFUSING: %d security strings are not tickers: %s" % (len(bad), bad[:3]))
        return 2

    readme = pd.DataFrame({"": [
        "MTG_FACTOR, monthly, 1 March 2009 to today, for the securities on the next sheet.",
        "",
        "These are the ones from the 412 that came back without a usable history.",
        "",
        "IMPORTANT: please build the Bloomberg ticker from the 'security' column, which is",
        "already in the right form. The previous run was built from the 'isin' column, and",
        "37 of these securities have no ISIN in the custodian file, so that column is blank",
        "for them and the ticker came out as NULL.",
        "",
        "The 'what_happened' column says why each one is here. Three of them are not a",
        "keying problem and may simply not be retrievable - they are included so the list",
        "is complete, not because we expect all three to come back.",
        "",
        "Any shape of return is fine - one row or one column per security, dates as dates.",
        "If the terminal refuses a security, leaving the error text in place is more useful",
        "to us than a blank.",
    ]})
    with pd.ExcelWriter(OUT, engine="openpyxl") as writer:
        readme.to_excel(writer, sheet_name="README", index=False)
        frame.to_excel(writer, sheet_name="securities", index=False)
    print()
    print("WROTE %s  (%d securities, %d of them the keying case)" % (OUT, len(frame),
                                                                     no_isin))
    return 0


if __name__ == "__main__":
    sys.exit(main())
