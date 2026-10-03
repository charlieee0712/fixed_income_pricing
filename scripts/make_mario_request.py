"""Build the Bloomberg request pack for an operator who has never seen this project.

⚠️ THIS IS A SEPARATE GENERATOR FROM ``make_bloomberg_request.py`` ON PURPOSE. That one is
the record of what went to Liping on 2026-09-29 and must keep saying what it said. This one
writes for a different reader, in a different language, with a different failure risk.

## What changed about the reader

The 09-29 pack was written for a colleague who would be back at a terminal if something
went wrong. This pack may be run by somebody doing a favour, once, who has never heard of
the project. Three consequences, each of which changes a file:

  ① **English, and self-contained.** No "same as last time", no "the pilot showed". There
     was no last time for this reader.
  ② **An entitlement probe runs FIRST.** A factor history worked on one terminal; a
     different account may simply not carry the mortgage entitlement, and the way that
     presents is 375 columns of ``#N/A`` with nothing saying why. Three cells answer it
     before anything large runs.
  ③ **No second round.** ⭐ See below — this is the substantive design change.

## ⭐ The design change: no "classify now, pull the movers later"

The 09-29 round-2 sheet asked for a coupon at four dates, to separate fixed from floating,
with the monthly series to be pulled afterwards for whatever moved. That is a second
request wearing the costume of a cheap first one, and a second request is the thing we are
trying not to need.

So the suspects are MEASURED instead, and pulled in full in the same sitting:

    union = {class letter S}  u  {description says FLT/VAR/ADJ/INV/ARM/LIBOR}  u  {I/O}

    156 securities across both populations  ->  monthly series, 211 months
    595 everything else                     ->  four dates, which is enough to prove
                                                the union above missed nobody

⭐ I/O strips are inside the union because the list is mostly ``CL SA`` / ``SB`` /
``SL FLT RT`` — inverse floaters whose coupon moves every month. Four dates would have
classified them and left them unpriced, which is the failure this restructuring exists to
avoid.

The safety net is the point of the 595. If one of them comes back with a coupon that
MOVED across the four dates, the text search missed it, and we learn that from this pull
rather than from a wrong price.

## What is NOT in here, and why

**The deferred registry items (G2-G6) stay out.** The line is: a gap that BLOCKS a security
goes in, a gap that merely CONFIRMS a convention stays out. Every G5 item is
confirmation-only — all eight of those bonds price today. Second reason, and the stronger
one: this pack is a single field family under ``BDH``, already proven to return. G2-G4 are
``DES`` lookups and untested field names, and an untested field in a favour pack is how a
stranger's pull fails without them being able to tell why.

**Nothing is asked about I/O notionals.** That looked like a data gap and is not one:
Bloomberg's factor already agrees with the custodian's own ``paydown_factor`` on 75 of the
76 I/O strips, to a median 3.5e-08 — as well as it agrees on everything else. The two
sources mean the same thing by an I/O's factor, which is the only property the pricing
needs. Settled from data in hand; see ``docs/bloomberg_return_2026-10-01.md``.

## The 37 that cannot be asked for

412 securities are in scope across the three classes; **375 can be requested; 37 carry no
ISIN at all in the custodian file**, so no pull of any shape reaches them. That sentence
belongs in the README and in the message, because 375 != 412 is the first thing a careful
reader notices.
"""
import csv
import pathlib
import re
import sys

import pandas as pd

sys.path[:0] = ["src", "scripts"]

from make_bloomberg_request import (  # noqa: E402  — the proven helpers, reused
    FACTOR_FIELD,
    COUPON_FIELD,
    FACTOR_START,
    FACTOR_END,
    _column_letter,
    _month_ends,
    verify_transposed,
)

PACK = pathlib.Path("docs/bloomberg_request_2026-10-02")

#: The three securitised classes the 09-29 request never reached.
OTHER_CLASSES = ("Non-Government Backed C.M.O.s", "Commercial Mortgage-Backed",
                 "Asset Backed Securities")

#: Enough dates to prove a coupon does NOT move. Only ever applied to securities the
#: suspect search has already cleared, so this is a safety net rather than a triage step.
CLASSIFY_DATES = ("20090401", "20100401", "20120401", "20150401")

#: ⚠️ Every way a security in this book could turn out to carry a moving coupon. Union, not
#: intersection: two of these three methods have already been shown unreliable on their own
#: (the class letter called 29 principal-only strips "PACs"; the text search found 2 I/O
#: where there are 76), so the honest move is to take anything any of them flags.
FLOAT_TEXT = r"FLT|FLOAT|VAR\s*RT|VARIABLE|ADJ\s*RT|ADJUSTABLE|INVERSE|\bINV\b|LIBOR|\bARM\b|STEP"
IO_TEXT = r"I\s*/\s*O|INTEREST[ -]ONLY"
PO_TEXT = r"P\s*/\s*O|\bCL\s+PO\b|PRINCIPAL[ -]ONLY"


def _cusip_from_isin(isin):
    """US ISINs carry the CUSIP in positions 3-11. None when it is not that shape.

    ⚠️ ``pd.isna`` rather than a truth test — ``str(isin or "")`` raises "boolean value of
    NA is ambiguous" on a pandas NA, which has now cost this project twice.
    """
    if isin is None or pd.isna(isin):
        return None
    s = str(isin)
    return s[2:11] if len(s) == 12 and s[:2] == "US" else None


def _class_letter_s(desc: str) -> bool:
    """True when the REMIC class token starts with S — the usual inverse-floater letter."""
    m = re.search(r"\bCL\s+([A-Z0-9\-]+)", desc)
    return bool(m) and m.group(1).startswith("S")


def _suspect(desc_upper: pd.Series) -> pd.Series:
    """The union. Anything any method flags as possibly carrying a moving coupon."""
    return (desc_upper.str.contains(FLOAT_TEXT, regex=True)
            | desc_upper.str.contains(IO_TEXT, regex=True)
            | desc_upper.map(_class_letter_s))


# --------------------------------------------------------------------------- populations

def populations():
    """Who needs what, measured rather than assumed.

    Returns ``(need_factor, need_monthly_coupon, need_classify)`` as frames carrying
    ``security`` (the Bloomberg ticker), ``asset_id`` and ``desc_long``.
    """
    import os

    os.environ.setdefault("FIP_DATA_DIR", "data")
    from openpyxl import load_workbook

    import pool_risk as D
    from dataio.phase2 import load_master_phase2

    m = load_master_phase2(D.WB).drop_duplicates("asset_id")
    chk = pd.read_csv("outputs/mbs_data_check_2026-07-30.csv")[["asset_id", "cusip"]]

    # (a) the three classes never requested — these need a FACTOR history
    other = m[m["sub_category"].isin(OTHER_CLASSES)].copy()
    other["cusip"] = other["isin"].map(_cusip_from_isin)
    unreachable = int(other["cusip"].isna().sum())
    other = other[other["cusip"].notna()].copy()

    # (b) the Government-MBS securities whose factor ALREADY came back on 2026-10-01 —
    #     these need only a coupon, and only if they might float
    ws = load_workbook("docs/03_factor_history.xlsx", data_only=True)["data"]
    returned = pd.DataFrame({"cusip": [
        str(ws.cell(row=1, column=c).value or "").replace(" Mtge", "")
        for c in range(2, ws.max_column + 1)]})
    returned = returned.merge(chk, on="cusip", how="left").merge(
        m[["asset_id", "desc_long"]], on="asset_id", how="left")

    for f in (other, returned):
        f["security"] = f["cusip"] + " Mtge"
        f["_u"] = f["desc_long"].fillna("").str.upper()

    everyone = pd.concat([returned.assign(src="govt-mbs (factor already in hand)"),
                          other.assign(src="cmo / cmbs / abs (factor needed)")],
                         ignore_index=True)
    everyone["suspect"] = _suspect(everyone["_u"])
    everyone["po"] = everyone["_u"].str.contains(PO_TEXT, regex=True)

    cols = ["security", "asset_id", "desc_long", "src"]
    return (other[["security", "asset_id", "desc_long"]].copy(),
            everyone.loc[everyone["suspect"], cols].copy(),
            everyone.loc[~everyone["suspect"], cols].copy(),
            unreachable)


# --------------------------------------------------------------------------- writers

def _write(name: str, header, rows) -> pathlib.Path:
    path = PACK / name
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def verify_rowwise(path: pathlib.Path, n_rows: int, n_formula_cols: int) -> None:
    """Every formula on a row must read THAT row's ticker out of column A.

    The row-wise twin of :func:`verify_transposed`. Same defect class: a sheet of entirely
    plausible numbers attributed to the wrong security, with nothing on its face to show it.
    """
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    body = rows[1:]
    assert len(body) == n_rows, f"{path.name}: {len(body)} rows, expected {n_rows}"
    for i, row in enumerate(body, start=2):          # sheet row number
        assert len(row) == n_formula_cols + 1, (
            f"{path.name}: row {i} has {len(row)} cells, expected {n_formula_cols + 1}")
        for cell in row[1:]:
            assert cell.startswith("=BDH($A"), f"{path.name}: row {i} is not a BDH formula"
            assert f"($A{i}," in cell, (
                f"{path.name}: row {i} reads {cell[cell.index('(') : cell.index(',')]}, "
                f"not its own ticker in $A{i}")


def _transposed(name: str, df: pd.DataFrame, field: str, note: str) -> pathlib.Path:
    """A securities-across / months-down sheet — the layout that returned 79,336 of 79,336.

    ⚠️ The formula row must carry the FIRST month, because each formula spills DOWNWARD
    from where it stands. 03 shipped for one commit with the formulas one row above their
    labels; ``verify_transposed`` is the only reason that was caught.
    """
    months = _month_ends(FACTOR_START, FACTOR_END)
    n = len(months)
    header = [f"date  ({note})"] + list(df["security"])
    ident = ["asset_id"] + list(df["asset_id"])
    blank = [""] * (len(df) + 1)
    formulas = [months[0]] + [
        f'=BDH({_column_letter(i + 1)}$1,"{field}","{FACTOR_START}","{FACTOR_END}",'
        f'"Per=M","Dts=H","Fill=B","cols=1;rows={n}")' for i in range(len(df))]
    rows = [ident, blank, blank, formulas] + [[mm] + [""] * len(df) for mm in months[1:]]
    p = _write(name, header, rows)
    verify_transposed(p, n_securities=len(df), months=months)
    return p


def write_probe(need_factor: pd.DataFrame, suspects: pd.DataFrame) -> pathlib.Path:
    """⭐ Three securities, both fields, run before anything large.

    A different terminal may not carry the mortgage entitlement, and the way that presents
    is hundreds of columns of ``#N/A`` with nothing naming the cause. This costs under a
    minute and converts that outcome into a sentence the operator can send back.
    """
    picks = [(need_factor.iloc[0], "a CMO / CMBS / ABS tranche — sheet 02"),
             (need_factor.iloc[len(need_factor) // 2], "another one, from a different deal"),
             (suspects.iloc[0], "a possible floating-rate security — sheet 03")]
    header = ["security", "what it is", "FACTOR, 12 months", "COUPON, 12 months"]
    rows = []
    for i, (r, what) in enumerate(picks, start=2):
        rows.append([
            r["security"], what,
            f'=BDH($A{i},"{FACTOR_FIELD}","20090301","20100201","Per=M","Dts=H","cols=1;rows=12")',
            f'=BDH($A{i},"{COUPON_FIELD}","20090301","20100201","Per=M","Dts=H","cols=1;rows=12")',
        ])
    return _write("01_CHECK_FIRST.csv", header, rows)


def write_classify(df: pd.DataFrame) -> pathlib.Path:
    """Four dates for everyone the suspect search cleared.

    ⭐ This is a CHECK, not triage. If any of these returns a coupon that moved, the search
    missed it and we find out here instead of in a price. The principal-only strips are
    left in deliberately for the same reason: a P/O that reports a non-zero coupon would
    mean our reading of it is wrong, and that is worth four cells to know.
    """
    header = ["security"] + [f"coupon {d[:4]}-{d[4:6]}" for d in CLASSIFY_DATES]
    rows = [[r["security"]] + [
        f'=BDH($A{i},"{COUPON_FIELD}","{d}","{d}","Dts=H","cols=1;rows=1")'
        for d in CLASSIFY_DATES] for i, r in enumerate(df.to_dict("records"), start=2)]
    p = _write("04_coupon_classify.csv", header, rows)
    verify_rowwise(p, n_rows=len(df), n_formula_cols=len(CLASSIFY_DATES))
    return p


# --------------------------------------------------------------------------- xlsx

def write_xlsx(csv_path: pathlib.Path, lines) -> pathlib.Path:
    """Real Excel, instruction tab first, in English.

    ⚠️ A .csv is text Excel interprets; whether ``=BDH(...)`` becomes a formula depends on
    the version, the locale, Protected View and CSV-injection defences. ⭐ The one-line
    check, verified through COM on 2026-10-01: a correct container reports
    ``HasFormula=True`` and displays ``#NAME?`` — Excel parsed the function and could not
    find the add-in. A broken one reports ``HasFormula=False`` and shows the literal text.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))

    wb = Workbook()
    note = wb.active
    note.title = "READ ME"
    for i, line in enumerate(lines, start=1):
        c = note.cell(row=i, column=1, value=line)
        if i == 1:
            c.font = Font(bold=True, size=14)
    note.column_dimensions["A"].width = 86

    ws = wb.create_sheet("data")
    head, grey = Font(bold=True), PatternFill("solid", fgColor="EEEEEE")
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val if val != "" else None)
            if r == 1:
                cell.font, cell.fill = head, grey
                cell.alignment = Alignment(wrap_text=False)
    ws.freeze_panes = "B2"
    for c in range(1, min(len(rows[0]), 40) + 1):
        ws.column_dimensions[get_column_letter(c)].width = 24 if c == 1 else 17

    out = csv_path.with_suffix(".xlsx")
    wb.save(out)
    csv_path.unlink()                      # one format, not two — two is confusion
    return out


# --------------------------------------------------------------------------- the words
#
# ⚠️ Written for somebody who has never seen this project and is doing us a favour at a
# terminal. No jargon from our side of the work, no "as before", no reference to a pull
# they did not run. Every sheet says what it is, what to press, and what a good result
# looks like, on its own.

PROBE_NOTE = [
    "SHEET 01  —  RUN THIS ONE FIRST  (under a minute)",
    "",
    "Three securities, two fields each. It exists only to confirm this terminal can",
    "return mortgage data before you spend time on the large sheets.",
    "",
    "WHAT TO DO",
    "   Open the 'data' tab. The grey cells should fill with numbers.",
    "   If they do not, press Ctrl+Alt+F9 to force a recalculation.",
    "",
    "WHAT A GOOD RESULT LOOKS LIKE",
    "   Each formula fills a short column of 12 monthly numbers going downward.",
    "   The factor numbers are between 0 and 1 and get smaller as you go down.",
    "   The coupon numbers are percentages, roughly 3 to 9.",
    "",
    "IF IT DOES NOT WORK",
    "   #N/A N/A Field  ->  the field name is not recognised on this terminal",
    "   #N/A Invalid Security  ->  the ticker is not recognised",
    "   Blank or #NAME?  ->  the Bloomberg Excel add-in is not loaded",
    "",
    "   Any of those, please just tell us what the cells say and stop here.",
    "   It saves you the other three sheets. Nothing is wasted.",
]

FACTOR_NOTE = [
    "SHEET 02  —  MONTHLY FACTOR HISTORY  (the important one)",
    "",
    "375 securities, 211 months each, March 2009 through September 2026.",
    "",
    "HOW IT IS LAID OUT",
    "   Securities run ACROSS row 1.  Months run DOWN column A.",
    "   Row 5 holds one formula per security. Each one fills the 211 rows",
    "   below itself automatically — so only row 5 has formulas in it.",
    "",
    "WHAT TO DO",
    "   Open the 'data' tab and let it calculate. Ctrl+Alt+F9 if nothing happens.",
    "   Then save the file and send it back. Please do not re-sort or delete",
    "   columns — each column is matched to a security by its position.",
    "",
    "WHAT A GOOD RESULT LOOKS LIKE",
    "   Every column is a series of numbers between 0 and 1 that never increases",
    "   as you read downward. A column that reaches 0 and then goes blank is a",
    "   security that has been fully repaid. That is normal and expected.",
    "",
    "HOW LONG",
    "   A sheet of this size and shape has been run on a terminal before and came",
    "   back complete in one sitting. It is the volume, not the difficulty.",
]

COUPON_NOTE = [
    "SHEET 03  —  MONTHLY COUPON HISTORY",
    "",
    "156 securities, the same 211 months.",
    "",
    "WHY ONLY THESE 156",
    "   These are the ones whose interest rate may change over time. For the rest,",
    "   a rate that never moves can be confirmed with four readings instead of 211,",
    "   which is sheet 04.",
    "",
    "   Same layout as sheet 02: securities across row 1, months down column A,",
    "   formulas on row 5 only.",
    "",
    "WHAT A GOOD RESULT LOOKS LIKE",
    "   Percentages, mostly between 0 and 15. Unlike the factors, these may go up",
    "   as well as down — that is the whole reason this sheet exists.",
]

CLASSIFY_NOTE = [
    "SHEET 04  —  COUPON AT FOUR DATES  (quick)",
    "",
    "595 securities, four readings each — about 2,400 numbers in total.",
    "",
    "WHY",
    "   We believe each of these pays a rate that never changes. Four readings",
    "   spread over six years confirms it. If all four match, the security is",
    "   settled; if one differs, we need to look at it again.",
    "",
    "   One security per row, four formulas across. Ordinary layout.",
    "",
    "WHAT A GOOD RESULT LOOKS LIKE",
    "   Four identical percentages on most rows.",
    "   Some rows will read 0 — those are securities that pay no interest at all",
    "   by design, and 0 is the correct answer for them.",
    "   Blank on the later dates means the security had already been repaid.",
]

README = """BLOOMBERG DATA REQUEST
URS fixed income pricing project
Prepared 2026-10-02

--------------------------------------------------------------------------
WHAT THIS IS
--------------------------------------------------------------------------

Four Excel files. Each one already contains the Bloomberg formulas; nothing
needs to be typed. Open the file on a machine with the Bloomberg Excel
add-in, let it calculate, save, and send it back.

We are valuing a bond portfolio as it stood on 31 March 2009. For mortgage
and asset-backed securities we need to know how much of each one was repaid
in each month since then, and what interest rate it paid. Both are published
monthly facts with a date, which is what these formulas ask for.

--------------------------------------------------------------------------
PLEASE RUN THEM IN THIS ORDER
--------------------------------------------------------------------------

   01_CHECK_FIRST.xlsx       3 securities      under a minute
   02_factor_history.xlsx    375 securities    the important one
   03_coupon_monthly.xlsx    156 securities
   04_coupon_classify.xlsx   595 securities    quick

Sheet 01 is three cells' worth of work and it answers whether this terminal
can return this kind of data at all. If it comes back empty, please tell us
what the cells say and stop — the other three would fail the same way, and
there is no point spending the time.

If time runs short after that, 02 is the one that matters most.

--------------------------------------------------------------------------
EVERY FILE WORKS THE SAME WAY
--------------------------------------------------------------------------

   * The first tab, "READ ME", says what that sheet is and what a good
     result looks like. The second tab, "data", is the sheet itself.

   * If the cells do not fill in on their own, press Ctrl+Alt+F9.

   * Please save as .xlsx and send the files back as they are. Sorting,
     deleting or inserting rows and columns would separate the numbers
     from the securities they belong to.

   * Blank cells at the bottom or the right of a column are normal. They
     mean that security had already been repaid by that date.

--------------------------------------------------------------------------
ONE THING WE CANNOT ASK FOR
--------------------------------------------------------------------------

There are 412 securities in these three categories. 375 of them are in
sheet 02. The remaining 37 have no ISIN recorded in the custodian file we
were given, so there is no identifier to look them up by. That is a gap on
our side, not something this request can close, and it is noted here so the
difference between 412 and 375 is not a mystery.

--------------------------------------------------------------------------
IF ANYTHING LOOKS WRONG
--------------------------------------------------------------------------

Please send the file back as it is, with the error text showing. An error
message tells us exactly which field or which security the terminal did not
accept, and that is genuinely more useful to us than a blank sheet or a
partial one. Nothing here is wasted effort.

Thank you very much for doing this.
"""


def main():
    PACK.mkdir(parents=True, exist_ok=True)
    need_factor, suspects, cleared, unreachable = populations()

    print(f"building {PACK}/\n")
    print(f"   populations measured, not assumed:")
    print(f"      factor needed (CMO/CMBS/ABS)      {len(need_factor):4d}"
          f"   !! {unreachable} more have no ISIN and cannot be requested")
    print(f"      monthly coupon (possible floaters) {len(suspects):4d}"
          f"   = text OR class-letter-S OR I/O, across BOTH populations")
    print(f"      four-date check (believed fixed)   {len(cleared):4d}")
    print()

    sheets = [
        (write_probe(need_factor, suspects), PROBE_NOTE),
        (_transposed("02_factor_history.csv", need_factor, FACTOR_FIELD,
                     "formulas on row 5 fill 211 rows downward"), FACTOR_NOTE),
        (_transposed("03_coupon_monthly.csv", suspects, COUPON_FIELD,
                     "formulas on row 5 fill 211 rows downward"), COUPON_NOTE),
        (write_classify(cleared), CLASSIFY_NOTE),
    ]
    for path, note in sheets:
        x = write_xlsx(path, note)
        print(f"   {x.name:28s} real formulas + an English READ ME tab")

    (PACK / "00_README.txt").write_text(README, encoding="utf-8-sig")
    print(f"   {'00_README.txt':28s} written")

    months = len(_month_ends(FACTOR_START, FACTOR_END))
    total = (len(need_factor) + len(suspects)) * months + len(cleared) * len(CLASSIFY_DATES)
    print(f"\n   {total:,} data points in one sitting "
          f"(the comparable sheet in September was 79,336 and returned complete)")

    # ⭐ THE PRE-SEND RULE, RUN RATHER THAN REMEMBERED: diff the request against the CLAIM.
    # The September pack was well-formed and incomplete — four audits checked whether the
    # files were CORRECT and none asked whether they covered what we had told the client we
    # needed. Asserting it here is the only version of that rule that cannot be forgotten.
    covered = set(need_factor.security) | set(suspects.security) | set(cleared.security)
    assert len(need_factor) + unreachable == 412, (
        f"claim check: {len(need_factor)} + {unreachable} unreachable != the 412 in scope")
    assert len(suspects) + len(cleared) == 751, (
        f"claim check: {len(suspects)} + {len(cleared)} != the 751 needing a coupon answer")
    print(f"   claim check PASSED: 412 in scope = {len(need_factor)} requested "
          f"+ {unreachable} with no ISIN; {len(covered)} distinct securities in the pack")


if __name__ == "__main__":
    main()
