"""Tests for the coupon-formula loader (``dataio.coupon_formula``).

Contract tests are hermetic. The last four read the tracked `data/coupon_formula.csv` and lock
the facts it exists to carry — Mario's "same bond, different dates" structure, the five
grammars, and ⭐ the refusal that stops a leveraged inverse floater publishing a coupon of minus
fourteen thousand percent.
"""
import datetime as dt

import pytest

from dataio.coupon_formula import (COUPON_BAND_PCT, CouponRuleNotEvaluable,
                                   coupon_from_rule, load_coupon_formulas, rule_in_force)
from pricer.errors import ContractTermsError

HEADER = ("cusip,isin,identifier,period,effective_date,kind,multiplier,index,margin_pct,"
          "formula_raw,day_count,freq_token,payments_per_year,source_file,source,as_of\n")


def _write(tmp_path, body):
    p = tmp_path / "coupon_formula.csv"
    p.write_text(HEADER + body)
    return str(p)


def test_missing_file_is_no_data_not_an_error(tmp_path):
    assert load_coupon_formulas(str(tmp_path / "absent.csv")) == {}


def test_a_security_with_several_dated_periods_loads_in_order(tmp_path):
    """⭐ Mario's own example: one bond, several dated formulas, the margin stepping up."""
    path = _write(
        tmp_path,
        "39538WHF8,US39538WHF86,US39538WHF86,2,2019-07-25,float,1.0,US0001M,0.42,"
        "1.000 * US0001M + 0.420%,ACT/360,MNT,12,mtge.xlsx,s,2026-10-14\n"
        "39538WHF8,US39538WHF86,US39538WHF86,1,2006-04-28,float,1.0,US0001M,0.21,"
        "1.000 * US0001M + 0.210%,ACT/360,MNT,12,mtge.xlsx,s,2026-10-14\n")
    got = load_coupon_formulas(path)
    ps = got["39538WHF8"]
    assert [p["period"] for p in ps] == [1, 2]          # sorted even though written 2 then 1
    assert ps[0]["effective_date"] == dt.date(2006, 4, 28)
    assert ps[0]["margin_pct"] == 0.21 and ps[1]["margin_pct"] == 0.42
    assert ps[0]["payments_per_year"] == 12


def test_a_non_us_security_keys_on_its_isin(tmp_path):
    """⚠️ The files carry XS and DE issues — that is how both EUR Resona tranches resolved."""
    path = _write(
        tmp_path,
        ",XS0229704886,XS0229704886,1,2005-09-15,fixed,,,4.125,4.125000% Fixed,"
        "ACT/ACT,ANN,1,corp.xlsx,s,2026-10-14\n")
    got = load_coupon_formulas(path)
    assert list(got) == ["XS0229704886"]
    assert got["XS0229704886"][0]["payments_per_year"] == 1


def test_an_unrecognised_kind_is_refused(tmp_path):
    path = _write(tmp_path, "AAA,,AAA,1,2006-01-01,inverse,,,1.0,x,ACT/360,MNT,12,f,s,d\n")
    with pytest.raises(ValueError, match="unrecognised coupon rule kind"):
        load_coupon_formulas(path)


def test_a_repeated_period_is_refused(tmp_path):
    """The builder collapses 18 exact duplicates and refuses disagreeing ones, so a duplicate
    reaching the loader means the table was hand-edited."""
    row = ("AAA,,AAA,1,2006-01-01,fixed,,,5.0,5.000000% Fixed,30/360,MNT,12,f,s,d\n")
    with pytest.raises(ValueError, match="two rows for period 1"):
        load_coupon_formulas(_write(tmp_path, row + row))


# --------------------------------------------------------------------------- in force

def _p(period, eff, **kw):
    base = dict(period=period, effective_date=eff, kind="float", multiplier=1.0,
                index="US0001M", margin_pct=0.21, formula_raw="r", day_count="ACT/360",
                freq_token="MNT", payments_per_year=12)
    base.update(kw)
    return base


def test_rule_in_force_picks_the_latest_period_on_or_before_the_date():
    ps = [_p(1, dt.date(2006, 4, 28)), _p(2, dt.date(2019, 7, 25), margin_pct=0.42)]
    assert rule_in_force(ps, dt.date(2009, 3, 31))["period"] == 1
    assert rule_in_force(ps, dt.date(2020, 1, 1))["period"] == 2
    assert rule_in_force(ps, dt.date(2006, 4, 28))["period"] == 1   # inclusive


def test_rule_in_force_returns_none_when_every_period_starts_later():
    """⚠️ A real and common answer: at 2009-03-31 every fixed-to-float corporate hybrid was
    still in its first period, and a floating period beginning in 2016 governs nothing yet."""
    assert rule_in_force([_p(1, dt.date(2016, 9, 1))], dt.date(2009, 3, 31)) is None
    assert rule_in_force([_p(1, None)], dt.date(2009, 3, 31)) is None


# --------------------------------------------------------------------------- evaluation

def test_a_fixed_rule_needs_no_index():
    assert coupon_from_rule(_p(1, None, kind="fixed", multiplier=None, index=None,
                               margin_pct=6.5)) == 6.5


def test_an_ordinary_floater_evaluates():
    got = coupon_from_rule(_p(1, None, margin_pct=0.21), index_level_pct=0.50063)
    assert abs(got - 0.71063) < 1e-9


def test_an_inverse_floater_is_ordinary_not_exotic():
    """285 of the 451 float periods have |multiplier| = 1, inverse ones among them."""
    got = coupon_from_rule(_p(1, None, multiplier=-1.0, margin_pct=5.07),
                           index_level_pct=0.50063)
    assert abs(got - 4.56937) < 1e-9


def test_a_float_rule_without_an_index_level_refuses_rather_than_guessing():
    with pytest.raises(CouponRuleNotEvaluable, match="needs a level"):
        coupon_from_rule(_p(1, None))


def test_a_margin_only_rule_refuses():
    with pytest.raises(CouponRuleNotEvaluable, match="names no index"):
        coupon_from_rule(_p(1, None, kind="margin-only", multiplier=None, index=None,
                            margin_pct=2.205))


def test_the_leveraged_inverse_floater_refuses_instead_of_returning_minus_14000_percent():
    """⭐⭐ The reason this refusal exists. `2370.000 * US0001M - 15405.000%` is a real record
    and at the 2009 one-month LIBOR of 0.50063% it returns about -14,219%."""
    rule = _p(1, None, multiplier=2370.0, margin_pct=-15405.0,
              formula_raw="2370.000 * US0001M - 15405.000%")
    raw = rule["multiplier"] * 0.50063 + rule["margin_pct"]
    assert raw < -14000                                    # the number we must never publish
    with pytest.raises(CouponRuleNotEvaluable, match="outside the measured band"):
        coupon_from_rule(rule, index_level_pct=0.50063)


def test_a_moderately_leveraged_rule_also_refuses_when_it_leaves_the_band():
    """⚠️ The BAND is the test, not the multiplier. This one sits inside the continuous
    multiplier range (|mult| runs smoothly to 7.083) and is still unusable."""
    rule = _p(1, None, multiplier=-4.0, margin_pct=28.6,
              formula_raw="-4.000 * US0001M + 28.600%")
    with pytest.raises(CouponRuleNotEvaluable, match="outside the measured band"):
        coupon_from_rule(rule, index_level_pct=0.50063)


def test_the_refusal_is_not_a_ValueError():
    """The spread solvers catch ValueError; a swallowed refusal would come back as 'no spread
    reprices this security', which is a different and false statement."""
    assert issubclass(CouponRuleNotEvaluable, ContractTermsError)
    assert not issubclass(CouponRuleNotEvaluable, ValueError)


# --------------------------------------------------------------------------- the real table

def test_the_tracked_table_carries_the_dated_structure():
    got = load_coupon_formulas()
    if not got:
        pytest.skip("data/coupon_formula.csv not present")
    assert len(got) == 1227
    assert sum(len(v) for v in got.values()) == 1411
    widths = {}
    for v in got.values():
        widths[len(v)] = widths.get(len(v), 0) + 1
    assert widths == {1: 1076, 2: 118, 3: 33}, widths
    assert max(widths) == 3, "the export carries only three period columns"


def test_the_tracked_table_contains_marios_own_example():
    """⭐ GREENPOINT MTG FDG TR 2006-AR3: LIBOR+21bp from 2006, +42bp from 2019, then Term
    SOFR — which is the structure his note described."""
    got = load_coupon_formulas()
    if not got:
        pytest.skip("data/coupon_formula.csv not present")
    ps = got["39538WHF8"]
    assert [p["effective_date"] for p in ps] == [dt.date(2006, 4, 28), dt.date(2019, 7, 25),
                                                 dt.date(2023, 7, 25)]
    assert [round(p["margin_pct"], 3) for p in ps] == [0.21, 0.42, 0.534]
    assert rule_in_force(ps, dt.date(2009, 3, 31))["period"] == 1


def test_every_rule_in_the_tracked_table_either_evaluates_or_refuses_cleanly():
    """No rule may raise anything other than the named refusal — a stray TypeError or
    ZeroDivisionError from a formula shape nobody anticipated is the failure this catches."""
    got = load_coupon_formulas()
    if not got:
        pytest.skip("data/coupon_formula.csv not present")
    evaluated = refused = 0
    for key, ps in got.items():
        for p in ps:
            try:
                value = coupon_from_rule(p, index_level_pct=0.50063)
            except CouponRuleNotEvaluable:
                refused += 1
            else:
                evaluated += 1
                lo, hi = COUPON_BAND_PCT
                assert lo <= value <= hi, (key, p["formula_raw"], value)
    assert evaluated + refused == 1411
    assert refused > 0, "the leveraged records must be refused, not silently evaluated"


def test_the_fixed_records_dominate_and_are_all_evaluable():
    got = load_coupon_formulas()
    if not got:
        pytest.skip("data/coupon_formula.csv not present")
    fixed = [p for ps in got.values() for p in ps if p["kind"] == "fixed"]
    assert len(fixed) == 959
    for p in fixed:
        coupon_from_rule(p)        # must not raise: no index needed
