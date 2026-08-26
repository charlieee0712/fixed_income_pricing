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
from pricer.assets.corporate import embedded_option, puttable, sinking
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


# ------------------------------------------------------- sinking fund (Gate 3, new work)

SINK = [(dt.date(2011, 6, 15), 0.30, 100.0), (dt.date(2013, 6, 15), 0.50, 100.0)]
BASIS = {"fraction_basis": "outstanding"}


def test_full_fraction_reduces_to_the_call_path_exactly():
    """THE anchor: retiring 100% of the outstanding at P on a date IS a call at P on that
    date, so the two must agree bit-for-bit — not to a tolerance.

    The comparison is made at the core, on ONE step, because the two rights differ in
    persistence and not only in size: a sinking redemption fires on its scheduled date
    alone, while ``call_array`` builds a step function that stays exercisable from its
    date to maturity. Comparing the wrappers would therefore be comparing a European
    right with a Bermudan one — a real difference, and the reason this test reaches past
    them to the node rule itself.
    """
    lattice, accrued = tree.bond_tree(VAL, MAT, COUPON / 100.0, FLAT, freq=FREQ)
    sink_f, sink_p = lattice.sink_arrays([(tree.year_fraction(VAL, dt.date(2011, 6, 15)),
                                           1.0, 100.0)])
    step = int(sink_f.nonzero()[0][0])

    call_only_here = tree.np.full(lattice.N + 1, tree.np.inf)
    call_only_here[step] = 100.0

    as_sink = lattice.price_bond(COUPON / 100.0, 150.0 * 1e-4, None, None, sink_f, sink_p)
    as_call = lattice.price_bond(COUPON / 100.0, 150.0 * 1e-4, call_only_here, None)
    assert as_sink == as_call


def test_zero_fraction_prices_as_the_straight_bond():
    inert = [(dt.date(2011, 6, 15), 0.0, 100.0)]
    assert (sinking.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, inert, 150.0)
            == embedded_option.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, oas=150.0))


def test_value_falls_as_the_redeemable_fraction_rises():
    """The right belongs to the issuer, so more of it can only cost the holder."""
    prices = [sinking.calculated_price(COUPON, FREQ, MAT, VAL, FLAT,
                                       [(dt.date(2011, 6, 15), f, 100.0)], 150.0)
              for f in (0.0, 0.25, 0.50, 1.00)]
    assert prices == sorted(prices, reverse=True)
    assert prices[0] > prices[-1]                 # the fixture is genuinely in the money


def test_sinking_price_never_exceeds_the_straight_bond():
    straight = embedded_option.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, oas=150.0)
    assert sinking.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, SINK, 150.0) <= straight


def test_sinking_oas_round_trip_and_shorter_duration():
    curve = usd_curve()
    oas = sinking.implied_oas(COUPON, FREQ, MAT, VAL, PRICE, curve, SINK)
    back = sinking.calculated_price(COUPON, FREQ, MAT, VAL, curve, SINK, oas)
    assert abs(back - PRICE) < 1e-7          # the solver's own noise floor on the spread
    assert (sinking.duration(COUPON, FREQ, MAT, VAL, oas, curve, SINK)
            < embedded_option.duration(COUPON, FREQ, MAT, VAL, oas, curve))


def test_sinking_price_falls_with_volatility():
    curve = usd_curve()
    oas = sinking.implied_oas(COUPON, FREQ, MAT, VAL, PRICE, curve, SINK)
    prices = sinking.price_at_volatility(COUPON, FREQ, MAT, VAL, curve, SINK, oas)
    assert prices[0.10] > prices[0.15] > prices[0.20]


def test_original_face_basis_is_refused_not_reinterpreted():
    """Relabelling a basis the engine does not implement would silently change the number."""
    with pytest.raises(ValueError, match="strip decomposition"):
        sinking.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, SINK, 150.0,
                                 fraction_basis="original")
    with pytest.raises(ValueError, match="fraction_basis is required"):
        embedded_option.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, oas=150.0,
                                         sinking_schedule=SINK)


def test_out_of_range_fraction_is_refused():
    with pytest.raises(ValueError, match="must be in"):
        sinking.calculated_price(COUPON, FREQ, MAT, VAL, FLAT,
                                 [(dt.date(2011, 6, 15), 1.5, 100.0)], 150.0)


def test_sinking_date_colliding_with_a_call_is_refused():
    """Two rights on one node need a defined order; none is tested, so refuse."""
    with pytest.raises(ValueError, match="coincides with a call/put date"):
        embedded_option.calculated_price(
            COUPON, FREQ, MAT, VAL, FLAT, oas=150.0, call_schedule=CALL,
            sinking_schedule=[(dt.date(2011, 6, 15), 0.3, 100.0)], **BASIS)


def test_two_redemptions_in_one_coupon_period_are_refused():
    """The tree resolves exercise on coupon dates; a finer schedule would be coarsened."""
    with pytest.raises(ValueError, match="same coupon period"):
        sinking.calculated_price(
            COUPON, FREQ, MAT, VAL, FLAT,
            [(dt.date(2011, 8, 1), 0.2, 100.0), (dt.date(2011, 9, 1), 0.2, 100.0)],
            150.0)


def test_mode_diagnostic_names_the_product():
    assert sinking.describe_mode() == {"sinking_mode": "issuer_optional_redemption",
                                       "fraction_basis": "outstanding"}
