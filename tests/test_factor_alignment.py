"""Locks on ``data/factor_alignment.csv`` and the per-security month lag it carries.

The lag used to be one module constant. Measured on 2026-10-23 against the custodian's own
``paydown_factor``, it is a property of the **security**: the Government MBS pools shift by a
month, most of the 412 CMO / CMBS / ABS securities do not, and 36 of them disagree with their
own asset class. These tests exist so that stops being something a reader has to remember.

⚠️ The load-bearing one is :func:`test_the_government_pools_agree_with_the_constant_bar_three`.
A fourth disagreement appearing, or one of the three going away, means the data or the
derivation moved and somebody has to look before a published artifact changes underneath us.
"""
import csv
import datetime as dt
import os

import pytest

from dataio import factor_history as FH

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TABLE = os.path.join(DATA, FH.ALIGNMENT_FILE)

pytestmark = pytest.mark.skipif(not os.path.exists(TABLE),
                                reason="data/factor_alignment.csv is absent")

#: The Government MBS pools whose own factor picks a different month from the constant.
#: Residuals 1.2e-07, 1.6e-07 and 1.2e-08 — clean unique matches, not noise.
GOVT_EXCEPTIONS = {"31393LFM0": 0, "31393U4Q3": 0, "31397RTS5": 2}


@pytest.fixture(scope="module")
def alignment():
    return FH.load_factor_alignment(DATA)


def test_a_missing_table_is_no_data_not_an_error(tmp_path):
    assert FH.load_factor_alignment(str(tmp_path)) == {}


def test_the_table_covers_both_deliveries(alignment):
    by_population = {}
    for row in alignment.values():
        by_population.setdefault(row["population"], 0)
        by_population[row["population"]] += 1
    assert by_population == {"376-2026-09-25": 376, "412-2026-10-23": 371}
    assert len(alignment) == 747


def test_the_government_pools_agree_with_the_constant_bar_three(alignment):
    """⭐ The lock. Only these three Government MBS pools disagree, and by these amounts."""
    disagree = {
        cusip: row["month_lag"]
        for cusip, row in alignment.items()
        if row["population"] == "376-2026-09-25"
        and row["lag_source"] == "custodian-paydown-factor"
        and row["month_lag"] != FH.BLOOMBERG_MONTH_LAG
    }
    assert disagree == GOVT_EXCEPTIONS


def test_no_class_rule_could_replace_the_per_security_lag(alignment):
    """Two private-label CMOs, same sub-category, opposite alignment.

    This is why the lag is stored per security rather than per asset class.
    """
    adjustable, abn = alignment["007036TB2"], alignment["000780LD6"]
    assert adjustable["sub_category"] == abn["sub_category"]
    assert adjustable["month_lag"] == 0
    assert abn["month_lag"] == 1
    assert adjustable["lag_source"] == abn["lag_source"] == "custodian-paydown-factor"


def test_most_of_the_412_do_not_shift_and_a_real_minority_does(alignment):
    lags = [row["month_lag"] for row in alignment.values()
            if row["population"] == "412-2026-10-23"
            and row["lag_source"] == "custodian-paydown-factor"]
    assert sorted(set(lags)) == [0, 1]
    assert lags.count(0) == 199 and lags.count(1) == 53


def test_a_default_lag_is_labelled_as_one(alignment):
    """A security whose factor did not move cannot choose; the row must say so."""
    sources = {row["lag_source"] for row in alignment.values()}
    assert sources == {"custodian-paydown-factor", "class-majority-default"}
    defaulted = [r for r in alignment.values() if r["lag_source"] == "class-majority-default"]
    assert len(defaulted) == 254
    assert all(r["status"] in {"tied", "no-custodian-factor", "unmatched", "out-of-range"}
               for r in defaulted)


def test_an_unrecognised_status_is_refused(tmp_path):
    path = tmp_path / FH.ALIGNMENT_FILE
    path.write_text("cusip,month_lag,status,lag_source,residual,matched_month,"
                    "sub_category,population\nAAA,1,probably,x,,,,p\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unrecognised status"):
        FH.load_factor_alignment(str(tmp_path))


def test_a_lag_beyond_two_months_is_not_an_alignment(tmp_path):
    path = tmp_path / FH.ALIGNMENT_FILE
    path.write_text("cusip,month_lag,status,lag_source,residual,matched_month,"
                    "sub_category,population\nAAA,7,matched,x,,,,p\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not an alignment"):
        FH.load_factor_alignment(str(tmp_path))


def test_a_repeated_cusip_is_refused(tmp_path):
    path = tmp_path / FH.ALIGNMENT_FILE
    path.write_text("cusip,month_lag,status,lag_source,residual,matched_month,"
                    "sub_category,population\nAAA,1,matched,x,,,,p\n"
                    "AAA,0,matched,x,,,,p\n", encoding="utf-8")
    with pytest.raises(ValueError, match="appears twice"):
        FH.load_factor_alignment(str(tmp_path))


def test_the_lag_actually_changes_the_path_it_returns():
    """Without an alignment the constant applies; with one, the security's own lag does."""
    history = {"X": {"2009-03": 0.90, "2009-04": 0.80, "2009-05": 0.70}}
    as_of = dt.date(2009, 3, 31)
    assert FH.factor_path(history, "X", as_of) == [0.80, 0.70]
    unshifted = {"X": {"month_lag": 0, "status": "matched",
                       "lag_source": "custodian-paydown-factor"}}
    assert FH.factor_path(history, "X", as_of, unshifted) == [0.90, 0.80, 0.70]


def test_an_absent_security_falls_back_to_the_constant():
    history = {"X": {"2009-04": 0.80, "2009-05": 0.70}}
    other = {"Y": {"month_lag": 0, "status": "matched", "lag_source": "x"}}
    assert FH.lag_for("X", other) == FH.BLOOMBERG_MONTH_LAG
    assert FH.factor_path(history, "X", dt.date(2009, 3, 31), other) == [0.80, 0.70]


def test_the_412_history_loads_through_the_same_loader():
    history = FH.load_factor_history(DATA, FH.FACTOR_FILE_412)
    if not history:
        pytest.skip("data/factor_history_412.csv is absent")
    assert len(history) == 371
    assert sum(len(v) for v in history.values()) == 96120
    assert set(history) & set(FH.load_factor_history(DATA)) == set()


def test_every_row_of_the_table_names_a_security_we_hold_a_path_for(alignment):
    held = set(FH.load_factor_history(DATA)) | set(
        FH.load_factor_history(DATA, FH.FACTOR_FILE_412))
    if not held:
        pytest.skip("no factor history on disk")
    assert set(alignment) == held


def test_the_residual_backs_the_status_it_claims(alignment):
    """A row claiming the security chose its own month must carry a residual that small."""
    for cusip, row in alignment.items():
        if row["status"] == "matched":
            assert float(row["residual"]) < 1e-6, cusip
        if row["status"] == "nearest":
            assert 1e-6 <= float(row["residual"]) < 1e-3, cusip


def test_the_table_on_disk_is_what_the_loader_reports(alignment):
    """Guard against the loader quietly dropping rows the file actually carries."""
    with open(TABLE, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(alignment)
    assert {r["cusip"] for r in rows} == set(alignment)
