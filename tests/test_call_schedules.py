"""Hermetic tests for the call-schedule loader (``dataio.call_schedules``).

No client data — a temp CSV is written per test. These prove the data/logic split that Mario asked for
(2026-07-03): MULTI-ROW (step-function) schedules load and group correctly, asset ids stay strings (the
join key), a malformed table fails loudly, and the date->time conversion (relative to the valuation
date, clamped at 0) is centralised in one helper.
"""
import pandas as pd
import pytest

from dataio.call_schedules import load_call_schedules, to_lattice_schedule


def _write(tmp_path, text):
    p = tmp_path / "call_schedules.csv"
    p.write_text(text)
    return str(p)


def test_single_and_multi_row_grouping(tmp_path):
    """One row => one-entry schedule; several rows for one asset => a sorted step schedule."""
    path = _write(
        tmp_path,
        "asset_id,call_date,call_price\n"
        "AAA,2012-06-15,100\n"
        "BBB,2011-01-01,102\n"        # BBB is a 3-row step-down schedule, deliberately out of order
        "BBB,2013-01-01,100\n"
        "BBB,2012-01-01,101\n",
    )
    sched = load_call_schedules(path)
    assert set(sched) == {"AAA", "BBB"}
    assert sched["AAA"] == [(pd.Timestamp("2012-06-15"), 100.0)]
    assert [d.strftime("%Y-%m-%d") for d, _ in sched["BBB"]] == ["2011-01-01", "2012-01-01", "2013-01-01"]
    assert [p for _, p in sched["BBB"]] == [102.0, 101.0, 100.0]


def test_asset_id_kept_as_string(tmp_path):
    """A numeric-looking asset id must not be coerced to int — the join key is a string everywhere."""
    path = _write(tmp_path, "asset_id,call_date,call_price\n0012345,2012-06-15,100\n")
    assert "0012345" in load_call_schedules(path)


def test_missing_column_raises(tmp_path):
    path = _write(tmp_path, "asset_id,call_date\nAAA,2012-06-15\n")
    with pytest.raises(ValueError, match="call_price"):
        load_call_schedules(path)


def test_to_lattice_schedule_relative_and_clamped():
    """Dates -> years from the valuation date, sorted; a pre-valuation call date clamps to 0.0."""
    val = "2009-03-31"
    entries = [(pd.Timestamp("2014-08-16"), 100.0), (pd.Timestamp("2008-01-01"), 101.0)]  # 2nd precedes val
    out = to_lattice_schedule(entries, val)
    assert out[0] == (0.0, 101.0)                                  # clamped + sorted first
    assert out[1][1] == 100.0
    assert out[1][0] == pytest.approx((pd.Timestamp("2014-08-16") - pd.Timestamp(val)).days / 364.0)


def test_the_day_count_is_act_364_and_is_not_a_caller_choice():
    """This assertion used to read 365.25, and that was the defect.

    The coupon grid runs on ACT/364. While this converter defaulted to 365.25, an exercise
    date and a coupon date sat on different axes unless the caller remembered to say
    otherwise — both drivers did, so no shipped number was wrong, but nothing would have
    reported it if one had forgotten. The argument no longer exists, so the two functions
    below cannot disagree.
    """
    from pricer.core.pricing import tree
    from pricer.core.utils.dates import YEAR_DAYS

    assert YEAR_DAYS == 364.0
    with pytest.raises(TypeError):
        to_lattice_schedule([(pd.Timestamp("2014-08-16"), 100.0)], "2009-03-31",
                            days_per_year=365.25)

    # a span containing two leap days, where 364 and 365.25 differ by over a month
    schedule = [(pd.Timestamp("2020-02-29"), 100.0), (pd.Timestamp("2014-08-16"), 102.0)]
    assert to_lattice_schedule(schedule, "2009-03-31") == tree.schedule_times("2009-03-31", schedule)
    assert to_lattice_schedule(schedule, "2009-03-31")[1][0] == pytest.approx(
        (pd.Timestamp("2020-02-29") - pd.Timestamp("2009-03-31")).days / 364.0)
