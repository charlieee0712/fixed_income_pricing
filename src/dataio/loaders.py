"""Excel loaders for the URS workbook: the master ``Fixed Income`` sheet and the
``Corporate Bonds`` terms tab.

Column positions were confirmed against ``URS …FI Positions V Mainak.xlsx`` on 2026-06-27
(see WORKLOG). Header is row 1; data starts at row 2. ``data_only=True`` returns the cached
values Excel last wrote (numbers, ``datetime``, text); the literal text ``"NULL"`` and empty
cells are normalised to NA.

The custodian's own marks (Market price / Market value / Yield to maturity = ``BT``/``BU``/
``DI``) are loaded under ``gold_*`` names and kept **out of the pricing inputs** — they are an
independent reconciliation cross-check, not a model input (input / truth separation).
"""
from __future__ import annotations

import openpyxl
import pandas as pd
from openpyxl.utils import column_index_from_string

MASTER_SHEET = "Fixed Income"
TAB_SHEET = "Corporate Bonds"
CORP_SUBCATEGORY = "Corporate Bonds"   # the only corporate sub-category in this book

# Master ``Fixed Income`` — Excel column letter -> canonical field name.
# (``DL`` duplicates ``S``=Asset ID and master ``DO``/``DP`` coupon cols are ~empty, so terms
#  still come from the tab — see WORKLOG 2026-06-27.)
MASTER_COLS = {
    "S": "asset_id",           # join key (Asset ID)
    "X": "isin",
    "U": "sub_category",
    "R": "super_category",
    "CM": "sp_rating",         # 'Quality rating - S & P'
    "CL": "moody_rating",      # 'Quality rating - Moody'
    "CK": "fitch_rating",      # empty in this book
    "CV": "par_value",         # 'Shares/Par value'  (par held)
    "Z": "book_cost",          # 'Book cost value - base'  (for EIR)
    "AB": "call_date",         # 'Call date'  (callable flag)
    "BW": "maturity_master",   # 'Maturity date'
    "AL": "last_priced",       # 'Date of last pricing' = 2009-03-31
    # --- custodian golden master: reconciliation only, never a pricing input ---
    "BT": "gold_price",
    "BU": "gold_mkt_value",
    "DI": "gold_ytm",
}

# ``Corporate Bonds`` tab — letter -> canonical field name.
TAB_COLS = {
    "A": "asset_id",           # 'Asset Code'  (join key)
    "B": "isin",
    "C": "maturity",
    "D": "coupon",
    "E": "coupon_type",        # Fixed / Floating / Hybrid / Structured / ...
    "F": "freq",
    "L": "coupon_formula",
    "M": "coupon_formula2",
}

# Custodian marks — keep these out of any pricing-input frame.
GOLDEN_FIELDS = ("gold_price", "gold_mkt_value", "gold_ytm")


def _read_sheet(path, sheet, colmap):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet]
        idx = {column_index_from_string(letter) - 1: name for letter, name in colmap.items()}
        last = max(idx)
        records = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if len(row) <= last:                       # right-pad short rows
                row = tuple(row) + (None,) * (last + 1 - len(row))
            records.append({name: row[i] for i, name in idx.items()})
    finally:
        wb.close()
    df = pd.DataFrame.from_records(records, columns=list(colmap.values()))
    return df.replace({"NULL": pd.NA})


def load_master(path):
    """Every master ``Fixed Income`` holding (all asset types). Filter by ``sub_category``
    downstream — the corporate universe is ``sub_category == 'Corporate Bonds'``."""
    return _read_sheet(path, MASTER_SHEET, MASTER_COLS)


def load_corporate_terms(path):
    """The ``Corporate Bonds`` terms tab (coupon / type / freq / maturity), pre-dedupe
    (676 rows / 616 unique Asset Codes — dedupe in the universe pipeline)."""
    return _read_sheet(path, TAB_SHEET, TAB_COLS)
