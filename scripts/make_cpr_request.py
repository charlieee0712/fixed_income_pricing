"""Build the Bloomberg request for 2009-dated prepayment speeds.

    PYTHONPATH=src python scripts/make_cpr_request.py

Writes two files:

    outputs/cpr_bdh_pilot.csv       5 securities, FOUR ways of asking -- run this first
    outputs/cpr_bdh_template.csv    505 securities, the full request

⭐ THE PILOT IS THE POINT, and it exists because of what went wrong last time. The July
pull came back complete and unusable: every value was as of the pull date rather than the
valuation date, and one of the eight field names did not exist at all. Both were visible in
the first row and neither was discovered until all 882 had been pulled and shipped. Five
securities cost about a minute at the terminal and would have caught both.

WHY BDH AND NOT BDP
``BDP`` returns the CURRENT value of a field -- that is exactly how we ended up with 2026
prepayment speeds for a 2009 valuation. ``BDH`` takes a date range, which is the only way to
reach a historical value. Liping identified this; the pilot is there because the *syntax*
still has to be settled at the terminal rather than guessed here.

⚠️ THREE THINGS THE PILOT SETTLES, none of which can be answered away from a terminal:

  1. **Does a single-day range return anything?** CPR is published MONTHLY, against a factor
     date. Asking for 2009-03-31 to 2009-03-31 may land between publications and come back
     empty. Column E asks a single day; column F asks the whole month.
  2. **How does the answer lay itself out?** BDH returns an array. Without ``Dts=H`` it also
     returns a date column, and 505 rows each spilling two columns into their neighbour is
     not a spreadsheet anybody can read back.
  3. **Did the override actually take effect?** Column D is the plain BDP -- today's value.
     If a BDH column equals it, the date did NOT apply, and that is the failure that got
     through last time. ⭐ Comparing the two is the check, and it is built into the layout
     rather than left as something to remember.

WHAT IS NOT BEING ASKED FOR, and why the list is 505 rather than 882
  * **WAC is not re-pulled.** Measured on this book: an 0.50pp error in WAC moves the
    calibrated spread by 0.24 bp median, 0.87 bp worst. The 2026 value is good enough.
  * **The 344 REMIC / CMO / IO / PO tranches are excluded.** Their cash flows come from each
    deal's waterfall, so a prepayment speed alone prices none of them. Asking for data we
    cannot yet use would spend a colleague's terminal time on nothing.
"""
from __future__ import annotations

import csv
import pathlib

import pandas as pd

OUT = pathlib.Path("outputs")
RISK = OUT / "pool_risk_2009-03-31.csv"

#: The two valuation dates the drivers run. Written YYYYMMDD so no spreadsheet locale can
#: read 3/31 as the 3rd of an unrelated month.
DATES = (("20090331", "baseline"), ("20090610", "control"))

FIELDS = ("MTG_GEN_CPR_3M", "MTG_GEN_CPR_6M", "MTG_GEN_CPR_12M")

#: Hide the date column and hold each answer to one cell, so 505 rows stay a table.
#: ⚠️ Unverified at a terminal -- this is one of the things the pilot is for.
BDH_OPTS = '"Dts=H","cols=1;rows=1"'


def _bdh(cell: str, field: str, start: str, end: str, opts: str = BDH_OPTS) -> str:
    return f'=BDH({cell},"{field}","{start}","{end}",{opts})'


def _column_letter(index0: int) -> str:
    """0 -> A. Only ever asked about the first 26 here, but written honestly."""
    letters = ""
    n = index0
    while True:
        letters = chr(ord("A") + n % 26) + letters
        n = n // 26 - 1
        if n < 0:
            return letters


def verify(path: pathlib.Path) -> int:
    """Reopen what was written and check the formulas point where they claim to.

    ⭐ This exists because the first draft got it wrong in a way nothing would have caught.
    The pilot's headers were named ``D_today_BDP`` … ``G_no_layout_opts`` while ``security``
    sat in column D, so every one of those names was off by one and the covering note
    described the wrong cells. A colleague would have found it at the terminal, which is the
    most expensive place to find anything.

    The cell reference is the part that actually breaks: ``$D2`` has to be the ticker for
    that row and no other. Point it one column left and it reads a structure label; point it
    one row up and every security silently gets its neighbour's speed -- a spreadsheet full
    of plausible numbers for the wrong bonds.
    """
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]

    tick_col = header.index("security")
    tick_letter = _column_letter(tick_col)

    for r, row in enumerate(body, start=2):          # start=2: row 1 is the header
        assert row[tick_col].endswith(" Mtge"), f"{path.name} row {r}: not a Mtge ticker"
        for c, cell in enumerate(row):
            if not cell.startswith("="):
                continue
            want = f"(${tick_letter}{r},"
            assert want in cell, (
                f"{path.name} row {r} col {_column_letter(c)}: formula references "
                f"{cell[cell.index('(') : cell.index(',')]} but the ticker for this row "
                f"is in {want[1:-1]}")

    # A header whose letter prefix disagrees with where the column actually sits is the
    # exact defect above, so it is checked rather than trusted.
    for c, name in enumerate(header):
        if len(name) > 1 and name[1] == "_" and name[0].isupper():
            assert name[0] == _column_letter(c), (
                f"{path.name}: header {name!r} sits in column {_column_letter(c)}")
    return len(body)


def main():
    if not RISK.exists():
        raise SystemExit(f"missing {RISK}; run scripts/pool_risk.py first")
    d = pd.read_csv(RISK)
    d = d[d["route"].isin(("pool", "tba-forward"))].copy()

    # The pull workbook keys on "<cusip> Mtge", the same as the July request -- and that
    # request's OUTCOME per security is what the pilot strata are cut from, so the whole
    # check table is carried, not just the identifier.
    chk_full = pd.read_csv(OUT / "mbs_data_check_2026-07-30.csv")
    d = d.merge(chk_full[["asset_id", "cusip"]], on="asset_id", how="left")
    missing = d["cusip"].isna().sum()
    if missing:
        raise SystemExit(f"{missing} priced securities have no cusip in the check table")
    d = d.sort_values("cusip")
    d["security"] = d["cusip"].astype(str) + " Mtge"

    # ---------------------------------------------------------------- the full request
    path = OUT / "cpr_bdh_template.csv"
    header = ["cusip", "asset_id", "structure", "security"]
    for stamp, label in DATES:
        header += [f"{f}_{stamp}" for f in FIELDS]
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        for i, (_, r) in enumerate(d.iterrows(), start=2):
            cell = f"$D{i}"
            row = [r["cusip"], r["asset_id"], r["structure"], r["security"]]
            for stamp, _label in DATES:
                row += [_bdh(cell, f, stamp, stamp) for f in FIELDS]
            w.writerow(row)
    n = verify(path)
    assert n == len(d)
    print(f"wrote {path}  ({n} securities x {len(FIELDS)} fields x {len(DATES)} dates "
          f"= {n * len(FIELDS) * len(DATES)} data points)  [verified]")

    # ---------------------------------------------------------------- the pilot
    # ⭐ STRATIFIED, not a sample. Each of the five rows answers a different question, and
    # the strata come from what the July pull actually returned for these same securities:
    #
    #   486 of the 505 came back with a value in July. So the security identifiers resolve
    #   and MTG_GEN_CPR_3M is a real field -- neither of those is what the pilot is testing.
    #   The only open question is whether BDH applies the DATE, and how the answer lays out.
    #
    # ⚠️ 215 of the 221 pools that are already PAID OFF still return a CPR today. Bloomberg
    # freezes the last value rather than blanking it, exactly as it freezes WALA -- the trap
    # the July data check hit from the other direction. A frozen number looks like a live
    # one, which is why row 2 is in here.
    d = d.merge(chk_full.drop(columns=["cusip", "wac_pct"]), on="asset_id", how="left")
    has = d["cpr_12m_at_pull_pct"].notna()
    live = d["pool_alive_at_pull"].eq("yes")
    pool = d["structure"].eq("pass-through")
    tba = d["structure"].eq("tba-forward")

    strata = [
        (pool & live & has,
         "LIVE pool with a value today. D is a genuine 2026 speed; 2009 was a refi wave, "
         "so D and E must differ by a lot. If they match, the date did not apply."),
        (pool & ~live & has,
         "PAID-OFF pool -- D is FROZEN at whenever it died, and looks like a live number. "
         "If E differs from D the date reached back past the payoff, which is the strongest "
         "single confirmation on this sheet."),
        (pool & live & ~has,
         "LIVE pool with NO value today (5 of these, all ARM-like). Does the history hold "
         "what the current field does not?"),
        (tba & has,
         "TBA generic that answered in July -- confirms the generic carries a cohort speed."),
        (tba & ~has,
         "TBA generic that did NOT answer in July. If it stays empty we price the 27 TBAs "
         "off the cohort grid instead, which is already built -- so an empty answer here "
         "costs us nothing and is worth knowing."),
    ]

    pilot = OUT / "cpr_bdh_pilot.csv"
    with pilot.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        # ⚠️ The letters in these names are the REAL spreadsheet columns. `security` is
        # column D, so the first formula lands in E -- naming it "D_..." would send a
        # colleague looking one column to the left of the thing being described.
        w.writerow(["cusip", "asset_id", "structure", "security",
                    "E_value_today_BDP", "F_single_day_BDH", "G_whole_month_BDH",
                    "H_no_layout_options", "why_this_row_is_here"])
        rows = 0
        for i, (mask, why) in enumerate(strata, start=2):
            sel = d[mask]
            if sel.empty:                       # a stratum can empty out as the book changes
                raise SystemExit(f"pilot stratum {i - 1} is empty: {why[:40]}")
            r = sel.iloc[0]
            cell = f"$D{i}"
            w.writerow([
                r["cusip"], r["asset_id"], r["structure"], r["security"],
                f'=BDP({cell},"MTG_GEN_CPR_3M")',
                _bdh(cell, "MTG_GEN_CPR_3M", "20090331", "20090331"),
                _bdh(cell, "MTG_GEN_CPR_3M", "20090301", "20090331"),
                f'=BDH({cell},"MTG_GEN_CPR_3M","20090331","20090331")',
                why,
            ])
            rows += 1
    assert verify(pilot) == rows
    print(f"wrote {pilot}  ({rows} securities, one per stratum, 4 ways of asking)  [verified]")
    print("\n   !! Send the PILOT first. The July pull came back complete and unusable, and")
    print("   both reasons were visible in its first row.")


if __name__ == "__main__":
    main()
