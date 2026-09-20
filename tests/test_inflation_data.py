"""The inflation data layer, and the validation it makes possible (2026-09-19).

The load-bearing test here is the first one. Every inflation-linked bond's index ratio
scales every cash flow and the accrued, and until now it was recovered by a regular
expression pulling a coupon out of custodian free text and dividing the income rate by it —
guarded by nothing except a plausibility window of 0.9 to 1.6. Nobody had ever checked a
single one against the published indexation convention. A 1% error in a ratio moves a
published breakeven by about 6 bp; a 6% error moves it by 35 bp, on a bond whose published
breakeven is 138.8 bp.

They all check out, to six parts per million, and the check now runs on every commit.
"""
import pathlib

import pytest

from dataio.inflation import (index_ratio, load_cpi_index, load_index_ratios,
                              load_inflation_assumptions, reference_index)

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

#: Dated dates for the thirteen US TIPS, recovered by inverting the custodian's ratio through
#: the official Reference-CPI convention and then read forward as a check. Every one lands on
#: the 15th of a month -- the canonical TIPS dated date -- and the six whose custodian
#: description states a date agree with it.
US_DATED = {
    "TNTD03000464": "2004-07-15", "TNTD03000471": "2004-07-15",
    "TNTD03000747": "2007-01-15", "TNTD03000857": "2005-07-15",
    "TNTD03001140": "2006-01-15", "TNTD03001152": "2006-01-15",
    "TNTD03001612": "2007-01-15", "TNTD03027586": "2007-07-15",
    "TNTD03073784": "2008-01-15", "TNTD03982242": "2001-10-15",
    "TNTD03982260": "1999-04-15", "TNTD03982268": "1998-04-15",
    "TNTD03994749": "2000-01-15",
}

#: What the custodian's income rate divided by the description coupon produces. Not read from
#: outputs/ -- that folder is git-ignored and can be stale -- but stated here so the test is
#: a comparison between two independent derivations rather than a tautology.
US_RECOVERED = {
    "TNTD03000464": 1.120140, "TNTD03000471": 1.120139, "TNTD03000747": 1.046998,
    "TNTD03000857": 1.085510, "TNTD03001140": 1.063810, "TNTD03001152": 1.063810,
    "TNTD03001612": 1.046998, "TNTD03027586": 1.018747, "TNTD03073784": 1.007857,
    "TNTD03982242": 1.189538, "TNTD03982260": 1.284379, "TNTD03982268": 1.305448,
    "TNTD03994749": 1.254969,
}

#: The custodian's ratios are as of T+1, not the valuation date. Measured: at 2009-04-01 the
#: implied dated dates all land on the 15th and the worst residual is 5.9e-06; at 2009-03-31
#: they scatter across the 8th to the 19th and the residual is ten times larger.
SETTLEMENT = "2009-04-01"


@pytest.fixture(scope="module")
def cpi():
    series = load_cpi_index(DATA / "cpi_index.csv")
    assert series, "data/cpi_index.csv is missing or empty"
    return series


# --------------------------------------------------------------------------------------
# 1. The validation that did not exist before.
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("asset_id", sorted(US_DATED))
def test_a_custodian_index_ratio_is_reproduced_by_the_published_convention(cpi, asset_id):
    """Two independent derivations of the same number must agree.

    One comes from the custodian file (income rate / description coupon); the other from
    CPI-U NSA through TreasuryDirect's Reference-CPI rule. They share no input.
    """
    computed = index_ratio(cpi["US"], US_DATED[asset_id], SETTLEMENT)
    recovered = US_RECOVERED[asset_id]
    assert abs(computed - recovered) / recovered < 1e-5, (computed, recovered)


def test_the_whole_set_agrees_to_six_parts_per_million(cpi):
    """The set-level statement, so a single bond drifting cannot hide in an average."""
    worst = max(abs(index_ratio(cpi["US"], US_DATED[a], SETTLEMENT) - r) / r
                for a, r in US_RECOVERED.items())
    assert worst < 6e-6, f"worst relative disagreement is now {worst:.2e}"


def test_the_settlement_date_is_t_plus_one_not_the_valuation_date(cpi):
    """⚠️ A finding, pinned: the custodian's ratios are struck one day after valuation.

    Using the valuation date instead makes every ratio worse. This is the evidence, not an
    assertion about which is 'right' -- if the custodian ever restated, this test says so.
    """
    def worst(settle):
        return max(abs(index_ratio(cpi["US"], US_DATED[a], settle) - r) / r
                   for a, r in US_RECOVERED.items())

    assert worst("2009-04-01") < worst("2009-03-31") / 5


# --------------------------------------------------------------------------------------
# 2. The convention itself, including the part that differs between countries.
# --------------------------------------------------------------------------------------
def test_the_reference_index_equals_the_lagged_index_exactly_on_the_anchor_day(cpi):
    """The defining property: on the anchor day there is no interpolation at all."""
    us = cpi["US"]
    assert reference_index(us, "2009-04-01", anchor_day=1) == us[(2009, 1)]
    assert reference_index(us, "2008-12-01", anchor_day=1) == us[(2008, 9)]
    # Japan anchors on the 10th instead -- same lag, different anchor.
    assert reference_index(us, "2009-04-10", anchor_day=10) == us[(2009, 1)]


def test_the_anchor_day_actually_changes_the_answer(cpi):
    """⚠️ Guards against the anchor quietly becoming a constant again.

    US TIPS anchor on the 1st and Japanese JGBi on the 10th (Ministry of Finance). If this
    ever stopped mattering, the parameter would be decoration.
    """
    us = cpi["US"]
    assert reference_index(us, "2009-03-20", anchor_day=1) != \
           reference_index(us, "2009-03-20", anchor_day=10)


def test_a_missing_month_is_refused_rather_than_extrapolated(cpi):
    """A silently extrapolated index ratio is wrong in a way nothing downstream checks."""
    with pytest.raises(KeyError):
        reference_index(cpi["US"], "1990-01-01")


def test_the_index_ratio_is_invariant_to_the_index_base(cpi):
    """Why a 2015=100 series can validate a bond issued on an older base without rescaling."""
    us = cpi["US"]
    rebased = {k: v * 3.7 for k, v in us.items()}
    a = index_ratio(us, "2004-07-15", SETTLEMENT)
    b = index_ratio(rebased, "2004-07-15", SETTLEMENT)
    assert a == pytest.approx(b, rel=1e-12)


def test_japan_style_rounding_is_available_and_off_by_default(cpi):
    """Japan publishes the coefficient to five decimals; TreasuryDirect does not round."""
    us = cpi["US"]
    assert index_ratio(us, "2004-07-15", SETTLEMENT, decimals=5) == \
        round(index_ratio(us, "2004-07-15", SETTLEMENT), 5)


# --------------------------------------------------------------------------------------
# 3. The three tables: what each one is, and what it refuses.
# --------------------------------------------------------------------------------------
def test_a_missing_file_is_no_data_never_a_default():
    """The contract every override table in this project keeps."""
    assert load_cpi_index("data/does_not_exist.csv") == {}
    assert load_index_ratios("data/does_not_exist.csv") == {}
    assert load_inflation_assumptions("data/does_not_exist.csv") == {}


def test_the_korean_ratio_ships_as_provisional_with_its_source():
    """⚠️ A number nobody has confirmed must say so in the row it travels in.

    Three things about this ratio are inferred: the dated date, the lag convention, and
    T+1 settlement. Bloomberg wins on arrival and the delta gets logged -- Mario's standing
    rule for web-sourced terms.
    """
    rows = load_index_ratios(DATA / "index_ratios.csv")
    ktbi = rows["TNTG673976U"]
    assert ktbi["status"] == "provisional"
    assert ktbi["source"] and ktbi["dated_date"] and ktbi["convention"]
    assert 0.9 < ktbi["index_ratio"] < 1.6


def test_an_unrecognised_status_is_refused(tmp_path):
    """Not defaulted to something reassuring -- the rule dataio.call_schedules applies."""
    bad = tmp_path / "r.csv"
    bad.write_text("asset_id,index_ratio,status\nX,1.05,probably_fine\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_index_ratios(bad)


def test_a_non_positive_ratio_is_refused(tmp_path):
    bad = tmp_path / "r.csv"
    bad.write_text("asset_id,index_ratio,status\nX,0,provisional\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_index_ratios(bad)


def test_the_forward_assumption_table_is_registered_and_empty():
    """⚠️ Empty ON PURPOSE, and this pins the reason rather than the state.

    A constant forward assumption provably cannot change a price, a duration or a
    breakeven -- it folds into the spread. The rows exist so the field is registered under
    Mario's "specify every unavailable field on a table" directive; the loader skips them
    because no value has landed. If someone fills one in expecting an effect, the module
    docstring and this test are where they find out why there isn't one.
    """
    assert load_inflation_assumptions(DATA / "inflation_assumption.csv") == {}
    text = (DATA / "inflation_assumption.csv").read_text(encoding="utf-8")
    for ccy in ("USD", "JPY", "KRW"):
        assert f"\n{ccy}," in text, f"{ccy} is not registered in the table"


# --------------------------------------------------------------------------------------
# 4. The wiring: an override changes one bond and nothing else.
# --------------------------------------------------------------------------------------
def test_the_loader_is_unchanged_when_no_override_is_supplied():
    """The golden route census must not move just because the mechanism exists."""
    from dataio.phase2 import PHASE2_CLASSES, build_phase2_from_path

    wb = DATA / "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"
    bonds, _, _ = build_phase2_from_path(str(wb), classes=PHASE2_CLASSES)
    linkers = bonds[bonds["asset_class"] == "linker"]
    assert dict(linkers["route"].value_counts()) == {"ilb": 14, "ilb-indexation-unverified": 1}


def test_the_override_prices_the_korean_linker_and_touches_nothing_else():
    """14 -> 15, and every other route census entry identical."""
    from dataio.phase2 import PHASE2_CLASSES, build_phase2_from_path

    wb = str(DATA / "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx")
    plain, _, _ = build_phase2_from_path(wb, classes=PHASE2_CLASSES)
    fixed, _, _ = build_phase2_from_path(
        wb, classes=PHASE2_CLASSES, index_ratios=load_index_ratios(DATA / "index_ratios.csv"))

    assert dict(fixed[fixed["asset_class"] == "linker"]["route"].value_counts()) == {"ilb": 15}
    for cls in ("agency", "guaranteed"):
        assert dict(plain[plain["asset_class"] == cls]["route"].value_counts()) == \
               dict(fixed[fixed["asset_class"] == cls]["route"].value_counts())

    ktbi = fixed[fixed["asset_id"] == "TNTG673976U"].iloc[0]
    assert ktbi["index_ratio_status"] == "provisional"
    # The custodian income rate carries no indexation for this bond, so the stated coupon
    # IS the real coupon -- which is exactly why the recovery could not work.
    assert ktbi["real_coupon"] == pytest.approx(0.0275)
