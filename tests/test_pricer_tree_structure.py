"""Embedded-option tree locks (Round 2, 2026-08-25).

The tree migrated from ``pricing/lattice.py`` into ``pricer/core/pricing/tree.py`` and now
serves callable and puttable wrappers (sinking follows in its own gate). Three things must
hold and are pinned here:

1. **migration is a move, not a rewrite** — the shim re-exports the same object, and the
   wrappers reproduce the production driver path with ``==``, not a tolerance;
2. **one tree, several rights** — call, put, both, or neither, with the no-schedule case
   degenerating to the straight bond;
3. **contradictions are refused, presentation is forgiven** — a put above a call on one
   date is an error (the core would silently resolve it in the holder's favour), while
   unsorted schedules, numeric-string prices and duplicate entries are absorbed.

Volatility direction tests use deliberately option-active fixtures, as the plan requires:
they are statements about those fixtures, not universal claims about every bond.
"""
import datetime as dt

import pytest

import pricing.lattice as legacy_lattice
from curves.zero_curve import ZeroCurve
from dataio.call_schedules import to_lattice_schedule
from pricer.assets.corporate import callable as callable_bond
from pricer.assets.corporate import embedded_option, puttable
from pricer.core.market.curves import flat_zero_curve
from pricer.core.pricing import tree
from pricing.bond_price import lattice_inputs, price_bond

VAL = "2009-03-31"
MAT = "2016-06-15"
COUPON = 6.75
FREQ = 2
PRICE = 97.5
CALL = [(dt.date(2011, 6, 15), 100.0)]
PUT = [(dt.date(2012, 6, 15), 100.0)]
FLAT = flat_zero_curve(0.04)


def usd_curve():
    """The real production curve — used only where production parity is the point."""
    return ZeroCurve.from_currency("data", "USD", VAL, freq="Semiannual")


# ------------------------------------------------------------------------- migration

def test_shim_re_exports_the_same_object():
    assert legacy_lattice.ShortRateLattice is tree.ShortRateLattice


def test_wrapper_reproduces_the_production_driver_path_exactly():
    """What scripts/callable_risk.py computes, the wrapper must compute — bit for bit."""
    curve = usd_curve()
    coupon_times, accrued = lattice_inputs(VAL, MAT, COUPON / 100.0, freq=FREQ)
    lattice = tree.ShortRateLattice(curve, freq=FREQ, sigma=0.15, coupon_times=coupon_times)
    call_array = lattice.call_array(to_lattice_schedule(CALL, VAL, days_per_year=364.0))

    driver_oas = lattice.implied_oas(PRICE, COUPON / 100.0, call_array, None,
                                     accrued=accrued) * 1e4
    driver_dur = lattice.risk_metrics(COUPON / 100.0, driver_oas * 1e-4, call_array, None,
                                      accrued=accrued)["eff_duration"]

    assert callable_bond.implied_oas(COUPON, FREQ, MAT, VAL, PRICE, curve, CALL) == driver_oas
    assert callable_bond.duration(COUPON, FREQ, MAT, VAL, driver_oas, curve, CALL) == driver_dur


def test_core_schedule_times_matches_the_data_layer_conversion():
    """One ACT/364 axis for exercise dates. The dataio default is still 365.25, which is
    why new code goes through the core helper — the two must agree when it is asked for
    the project convention."""
    schedule = [(dt.date(2011, 6, 15), 100.0), (dt.date(2010, 1, 4), 102.0)]
    assert tree.schedule_times(VAL, schedule) == to_lattice_schedule(schedule, VAL,
                                                                    days_per_year=364.0)


def test_no_schedule_degenerates_to_the_straight_bond():
    on_tree = embedded_option.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, oas=150.0)
    analytic = price_bond(VAL, MAT, COUPON / 100.0, FLAT, oas=150.0 * 1e-4)
    assert abs(on_tree - analytic.clean) < 1e-9


# --------------------------------------------------------------------- one tree, rights

def test_call_lowers_and_put_raises_the_price():
    straight = embedded_option.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, oas=150.0)
    called = callable_bond.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, CALL, 150.0)
    putted = puttable.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, PUT, 150.0)
    assert called <= straight <= putted
    assert called < straight                      # the fixture is genuinely call-active


def test_both_rights_sit_between_the_single_right_prices():
    called = callable_bond.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, CALL, 150.0)
    putted = puttable.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, PUT, 150.0)
    both = embedded_option.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, oas=150.0,
                                            call_schedule=CALL, put_schedule=PUT)
    assert called <= both <= putted


def test_oas_round_trip():
    oas = callable_bond.implied_oas(COUPON, FREQ, MAT, VAL, PRICE, usd_curve(), CALL)
    back = callable_bond.calculated_price(COUPON, FREQ, MAT, VAL, usd_curve(), CALL, oas)
    assert abs(back - PRICE) < 1e-8


def test_callable_duration_is_shorter_than_the_straight_bond():
    curve = usd_curve()
    oas = callable_bond.implied_oas(COUPON, FREQ, MAT, VAL, PRICE, curve, CALL)
    called = callable_bond.duration(COUPON, FREQ, MAT, VAL, oas, curve, CALL)
    straight = embedded_option.duration(COUPON, FREQ, MAT, VAL, oas, curve)
    assert called < straight


def test_widening_and_tightening_bracket_the_base():
    base = callable_bond.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, CALL, 150.0)
    wide = callable_bond.widening(COUPON, FREQ, MAT, VAL, 150.0, FLAT, CALL)
    tight = callable_bond.tightening(COUPON, FREQ, MAT, VAL, 150.0, FLAT, CALL)
    assert wide < base < tight


# -------------------------------------------------------------------------- refusals

def test_put_above_call_on_the_same_date_is_refused():
    """The core applies min(call) then max(put): a contradiction would silently resolve
    in the holder's favour, so it must never reach the core."""
    with pytest.raises(ValueError, match="put price"):
        embedded_option.calculated_price(
            COUPON, FREQ, MAT, VAL, FLAT, oas=150.0,
            call_schedule=[(dt.date(2011, 6, 15), 99.0)],
            put_schedule=[(dt.date(2011, 6, 15), 101.0)])


def test_put_below_call_on_the_same_date_is_allowed():
    price = embedded_option.calculated_price(
        COUPON, FREQ, MAT, VAL, FLAT, oas=150.0,
        call_schedule=[(dt.date(2011, 6, 15), 103.0)],
        put_schedule=[(dt.date(2011, 6, 15), 97.0)])
    assert price > 0


def test_entirely_post_maturity_schedule_is_refused():
    """Otherwise the caller believes they priced a callable and got a straight bond."""
    with pytest.raises(ValueError, match="entirely inert"):
        callable_bond.calculated_price(COUPON, FREQ, MAT, VAL, FLAT,
                                       [(dt.date(2030, 1, 1), 100.0)], 150.0)


def test_same_date_two_prices_is_refused_but_an_exact_duplicate_is_absorbed():
    with pytest.raises(ValueError, match="two different prices"):
        callable_bond.calculated_price(
            COUPON, FREQ, MAT, VAL, FLAT,
            [(dt.date(2011, 6, 15), 100.0), (dt.date(2011, 6, 15), 101.0)], 150.0)

    with pytest.warns(UserWarning, match="duplicate"):
        deduped = callable_bond.calculated_price(
            COUPON, FREQ, MAT, VAL, FLAT,
            [(dt.date(2011, 6, 15), 100.0), (dt.date(2011, 6, 15), 100.0)], 150.0)
    assert deduped == callable_bond.calculated_price(COUPON, FREQ, MAT, VAL, FLAT,
                                                     CALL, 150.0)


def test_volatility_outside_the_contract_is_refused():
    with pytest.raises(ValueError, match="volatility"):
        callable_bond.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, CALL, 150.0,
                                       volatility=0.0)


# ------------------------------------------------------------------------- leniency

def test_unsorted_schedules_and_numeric_strings_are_absorbed():
    tidy = [(dt.date(2011, 6, 15), 100.0), (dt.date(2012, 6, 15), 100.0)]
    messy = [("2012-06-15", "100"), ("2011-06-15", "100.0")]
    assert (callable_bond.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, messy, 150.0)
            == callable_bond.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, tidy, 150.0))


# ------------------------------------------------------- the volatility question (§10)

def test_call_active_fixture_price_falls_and_oas_tightens_with_volatility():
    curve = usd_curve()
    oas = callable_bond.implied_oas(COUPON, FREQ, MAT, VAL, PRICE, curve, CALL)
    prices = callable_bond.price_at_volatility(COUPON, FREQ, MAT, VAL, curve, CALL, oas)
    spreads = callable_bond.implied_oas_at_volatility(COUPON, FREQ, MAT, VAL, PRICE,
                                                      curve, CALL)
    assert prices[0.10] > prices[0.15] > prices[0.20]      # issuer's option gains value
    assert spreads[0.10] > spreads[0.15] > spreads[0.20]   # less spread left as credit
    assert abs(prices[0.15] - PRICE) < 1e-8                # baseline reproduces the mark


def test_put_active_fixture_price_rises_with_volatility():
    prices = puttable.price_at_volatility(COUPON, FREQ, MAT, VAL, FLAT, PUT, 200.0)
    assert prices[0.10] < prices[0.15] < prices[0.20]


def test_volatility_sensitivity_reports_both_slopes_with_units():
    out = callable_bond.volatility_sensitivity(COUPON, FREQ, MAT, VAL, PRICE,
                                               usd_curve(), CALL)
    assert set(out) == {"baseline_volatility", "baseline_implied_oas_bp",
                        "price_change_per_1_vol_point", "oas_change_bp_per_1_vol_point"}
    assert out["baseline_volatility"] == 0.15
    assert out["price_change_per_1_vol_point"] < 0        # call-active: price falls
    assert out["oas_change_bp_per_1_vol_point"] < 0       # ...and the spread tightens
