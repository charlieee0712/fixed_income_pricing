"""Gate-1 locks for the Monthly-sheet reconciliation curve replica.

Covers: pillar-data lineage (H.15 CSV vs the tracked *_Yield_Curve.txt
history, incl. the txt's interpolated 20y point), the zeroyield4 gap-fill
arithmetic (quirks included), deposit identities, the par-reprice self-check
(the Gate-1 pass condition: formula cells in the sheet are dead, so the
rebuilt curve must reprice its own par instruments), and the legacy-parity
grid conventions (month-count truncation, 30y cap, OAS round-trip).
"""

import math
import os
from datetime import date

import pytest

from curves.bootstrap import load_par_curve
from recon.monthly_curve import (
    TERM2_TENORS,
    build_tables,
    gap_fill_usd,
    load_pillars,
)
from recon.parity import duration_legacy, implied_oas, month_count, parity_pv

DATA = os.environ.get("FIP_DATA_DIR", "data")
DATES = ("2010-03-01", "2012-06-01", "2012-12-12")

# txt tenor -> Term2 row (1-based); the txt 20y is excluded (interpolated point).
TXT_TO_ROW = {0.25: 3, 0.5: 6, 1.0: 12, 2.0: 13, 3.0: 14, 5.0: 16, 10.0: 21, 30.0: 41}


@pytest.fixture(scope="module")
def tables_2010():
    return build_tables("2010-03-01")


def _txt_row(d):
    tenors, par_pct = load_par_curve(os.path.join(DATA, "USD_Yield_Curve.txt"), d)
    return dict(zip(tenors, par_pct))


@pytest.mark.parametrize("d", DATES)
def test_pillar_csv_vs_txt_history(d):
    """The tracked txt history and the H.15 pillar CSV are independent records
    of the same par curve: agree within 5bp at shared tenors..."""
    txt = _txt_row(d)
    pil = load_pillars(d)
    for tenor, row in TXT_TO_ROW.items():
        assert abs(txt[tenor] - pil[row]) <= 0.05, (d, tenor, txt[tenor], pil[row])


@pytest.mark.parametrize("d", DATES)
def test_txt_20y_is_interpolated_point(d):
    """...EXCEPT 20y: the txt files fabricate it as (10y+30y)/2 exactly
    (lineage finding, Gate 1) while zeroyield4 pulled the real H15T20Y —
    which sits ~30bp above the midpoint in 2010."""
    txt = _txt_row(d)
    assert abs(txt[20.0] - (txt[10.0] + txt[30.0]) / 2.0) < 1e-9


def test_gap_fill_replicates_vba_quirks():
    pil = {1: 1.0, 3: 2.0, 6: 3.0, 12: 4.0, 13: 5.0, 14: 6.0, 16: 7.0,
           18: 8.0, 21: 9.0, 31: 10.0, 41: 11.0}
    r = gap_fill_usd(pil)
    assert r[1] == (1.0 + 2.0) / 2.0                       # 2M = avg(1M, 3M)
    # monthly rows step by the PER-YEAR slope (the VBA quirk): 4M = 3M + (6M-3M)/0.25
    assert r[3] == pytest.approx(2.0 + (3.0 - 2.0) / 0.25)
    assert r[10] == pytest.approx(3.0 + 5 * (4.0 - 3.0) / 0.5)   # 11M row = 6M + 5 steps
    assert r[14] == (6.0 + 7.0) / 2.0                      # 4y = avg(3y, 5y)
    assert r[16] == pytest.approx(7.0 + (8.0 - 7.0) / 2.0)  # 6y on the 5-7y slope
    # annual rows are exact linear: 19y = 10y + 9/10 * (20y - 10y)
    assert r[29] == pytest.approx(9.0 + 9.0 * (10.0 - 9.0) / 10.0)
    assert r[40] == pytest.approx(11.0)                     # 30y = pull
    assert r[39] == pytest.approx(10.0 + 9.0 * (11.0 - 10.0) / 10.0)  # 29y


def test_deposit_identities(tables_2010):
    par41 = gap_fill_usd(load_pillars("2010-03-01"))
    for freq in (1, 2, 4, 12):
        z, df = tables_2010[freq]
        for i in range(1, 13):
            expect = 1.0 / (1.0 + par41[i - 1] / 100.0 * TERM2_TENORS[i - 1])
            assert df[i] == pytest.approx(expect, abs=1e-15)
            assert z[i] == pytest.approx(-math.log(expect) / (i / 12.0), abs=1e-12)


def test_pillar_par_reprice(tables_2010):
    """Gate-1 pass condition: each annual par instrument reprices to 100 on its
    own frequency table (deposits are inputs; pillars are solved nodes)."""
    par41 = gap_fill_usd(load_pillars("2010-03-01"))
    for freq in (1, 2, 4, 12):
        table = tables_2010[freq]
        for pm in range(24, 361, 12):
            par = par41[pm // 12 + 10]
            pv = parity_pv(table, freq, par, pm, 0.0)
            assert pv == pytest.approx(100.0, abs=1e-8), (freq, pm)


def test_parity_grid_truncation(tables_2010):
    """Months not on the coupon step are truncated down (face at the last
    coupon index) — 87 months at freq 2 prices identically to 84."""
    table = tables_2010[2]
    assert parity_pv(table, 2, 5.5, 87, 150.0) == parity_pv(table, 2, 5.5, 84, 150.0)
    assert parity_pv(table, 2, 5.5, 5, 150.0) is None       # below one period


def test_month_count_cap():
    """(Y,M) difference, day ignored; 30y cap = valuation + 30*365 days
    (corporate path); the govt path passes apply_cap=False."""
    assert month_count(date(2010, 3, 1), date(2017, 6, 26)) == 87
    assert month_count(date(2010, 3, 1), date(2045, 1, 1)) == 359      # capped: 2040-02-22
    assert month_count(date(2010, 3, 1), date(2045, 1, 1), apply_cap=False) == 418


def test_implied_oas_roundtrip(tables_2010):
    table = tables_2010[2]
    price = parity_pv(table, 2, 6.25, 120, 137.5)
    oas = implied_oas(table, 2, 6.25, 120, price)
    assert oas == pytest.approx(137.5, abs=1e-6)


def test_duration_positive_and_sane(tables_2010):
    table = tables_2010[2]
    d = duration_legacy(table, 2, 6.25, 120, 137.5)
    assert 6.0 < d < 9.0
