"""OAS-curve loader — per-rating ICE BofA OAS history from the project's own workbook.

Source: ``Pricing File.xlsm`` / sheet ``OAS Credit Curves`` — the **authoritative historical
OAS source** for this project: ICE BofA US Corporate/High-Yield Index OAS, full daily history
**1997-01-02 … 2025-11-07** (7 rating buckets), downloaded before ICE/FRED truncated the free
series to a rolling 3-year window in April 2026. Read OAS from here, NOT from the FRED online
API, so any historical valuation date is reproducible locally.

Sheet layout (confirmed 2026-06-27): rows 1-2 = title/link, row 4 = header (cols B..H =
AAA AA A BBB BB B CCC), data rows 5+, column A = date (datetime). Values are DECIMAL spreads
(0.0148 = 1.48% = 148 bp), ready to add to a zero rate.
"""
from __future__ import annotations

import datetime as dt

import openpyxl
import pandas as pd

SHEET = "OAS Credit Curves"
BUCKETS = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC")   # workbook columns B..H


def load_oas_history(path) -> pd.DataFrame:
    """All daily OAS rows as a DataFrame indexed by ``date`` with one column per rating bucket
    (decimal spreads)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[SHEET]
        records = []
        for row in ws.iter_rows(min_row=5, values_only=True):
            d = row[0]
            if isinstance(d, dt.datetime):
                d = d.date()
            elif not isinstance(d, dt.date):
                continue                                  # skip non-date rows
            records.append((d, *(row[i] for i in range(1, 8))))
    finally:
        wb.close()
    return (pd.DataFrame(records, columns=["date", *BUCKETS])
            .dropna(subset=["date"]).set_index("date").sort_index())


def oas_on(path, valuation_date) -> dict:
    """Return ``{bucket: oas_decimal}`` for an EXACT valuation date.

    Raises if the date is absent (no silent nearest-date — explicit, mirroring the par-curve
    loader; the chosen 2009-06-10 is present in the history)."""
    if isinstance(valuation_date, str):
        valuation_date = dt.date.fromisoformat(valuation_date)
    elif isinstance(valuation_date, dt.datetime):
        valuation_date = valuation_date.date()
    hist = load_oas_history(path)
    if valuation_date not in hist.index:
        raise ValueError(
            f"OAS for {valuation_date} not found in '{SHEET}' "
            f"(range {hist.index.min()}..{hist.index.max()}; no nearest-date fallback)."
        )
    row = hist.loc[valuation_date]
    return {b: float(row[b]) for b in BUCKETS}
