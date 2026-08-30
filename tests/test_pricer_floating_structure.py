"""Floating / hybrid / stepped structure locks (Round 2b, 2026-08-30).

The three engines behind Mario's "Pivot of Corp Bonds" column-F rows 12-16 and 20 moved
into ``pricer/core/pricing/`` and gained thin asset wrappers. Four things must hold and
are pinned here:

1. **the migration is a move, not a rewrite** — every shim re-exports the same object,
   including the PRIVATE helpers the hybrid engine composes its floating leg out of, and
   the core no longer reaches up into the legacy ``pricing`` package for ``coupon_at``;
2. **the wrappers add naming and units, never arithmetic** — every wrapper result equals
   the direct engine call with ``==``, not a tolerance;
3. **the economics of each product** — a floater's duration is its next reset and not its
   maturity; a hybrid's degenerate limits ARE the single-engine answers, bit for bit; a
   flat "schedule" is arithmetically the plain bond;
4. **contradictions and unit mistakes are refused, not absorbed** — an unknown margin, a
   percent-scaled coupon schedule and an unsupported frequency each raise, because each
   would otherwise produce a plausible-looking wrong number.

Invariant fixtures are deliberately simple (flat curves, round dates); where production
parity is the point, the real USD curve is used instead.
"""
import datetime as dt

import pytest

import pricing.coupon_schedule as legacy_sched
import pricing.frn as legacy_frn
import pricing.hybrid as legacy_hybrid
from curves.zero_curve import ZeroCurve
from pricer.assets.corporate import floating, hybrid, stepped, vanilla
from pricer.assets.corporate import bonds_input
from pricer.core.market.curves import flat_zero_curve
from pricer.core.pricing import cashflows
from pricer.core.pricing import coupon_schedule as core_sched
from pricer.core.pricing import floating as core_float
from pricer.core.pricing import hybrid as core_hybrid
from pricing.bond_price import price_bond

VAL = "2009-03-31"
MAT = "2014-04-01"
FREQ = 2
PRICE = 96.5
MARGIN_BP = 45.0
SWITCH = "2011-04-01"
FIXED_CPN = 6.25
FLAT = flat_zero_curve(0.04)

_BP = 1e-4


def usd_curve():
    """The real production curve — used only where production parity is the point."""
    return ZeroCurve.from_currency("data", "USD", VAL, freq="Semiannual")


# ------------------------------------------------------------------- migration is a move

def test_floating_shim_re_exports_the_same_objects():
    for name in ("price_frn", "implied_oas_frn", "frn_risk_metrics", "parse_frn_spread",
                 "simple_forward", "FrnResult", "YEAR_DAYS"):
        assert getattr(legacy_frn, name) is getattr(core_float, name), name


def test_floating_shim_still_carries_the_private_helpers_hybrid_needs():
    """``pricing/hybrid.py`` imported these BY NAME; dropping them breaks it at import."""
    for name in ("_as_date", "_rate", "_df", "simple_forward", "YEAR_DAYS"):
        assert getattr(legacy_frn, name) is getattr(core_float, name), name


def test_hybrid_shim_re_exports_the_same_objects():
    for name in ("price_hybrid", "implied_oas_hybrid", "hybrid_risk_metrics", "HybridResult"):
        assert getattr(legacy_hybrid, name) is getattr(core_hybrid, name), name


def test_coupon_schedule_shim_re_exports_the_same_objects():
    assert legacy_sched.parse_coupon_schedule is core_sched.parse_coupon_schedule
    assert legacy_sched.coupon_at is core_sched.coupon_at


def test_core_no_longer_imports_coupon_at_from_the_legacy_package():
    """The layering violation this migration existed to close: core imports a sibling."""
    assert cashflows.coupon_at is core_sched.coupon_at


def test_hybrid_core_calls_the_pricer_native_engines():
    """The two rewritten import lines must be exact aliases, not lookalike wrappers."""
    from pricer.core.pricing.analytical import price_fixed_rate_bond
    assert core_hybrid.price_bond is price_fixed_rate_bond
    assert core_hybrid.price_frn is core_float.price_frn


# -------------------------------------------------- wrappers add naming, never arithmetic

def test_floating_wrapper_equals_the_direct_engine_call_exactly():
    curve = usd_curve()
    direct = core_float.price_frn(VAL, MAT, curve, oas=250 * _BP, spread=MARGIN_BP * _BP,
                                  freq=FREQ)
    assert floating.calculated_price(FREQ, MAT, VAL, curve, oas=250.0,
                                     quoted_margin_bp=MARGIN_BP) == direct.clean
    assert floating.accrued_interest(FREQ, MAT, VAL, curve,
                                     quoted_margin_bp=MARGIN_BP) == direct.accrued
    assert floating.next_reset_years(FREQ, MAT, VAL, curve,
                                     quoted_margin_bp=MARGIN_BP) == direct.next_reset_t


def test_floating_implied_oas_wrapper_equals_the_direct_solver_exactly():
    curve = usd_curve()
    direct = core_float.implied_oas_frn(PRICE, VAL, MAT, curve, spread=MARGIN_BP * _BP,
                                        freq=FREQ)
    assert floating.implied_oas(FREQ, MAT, VAL, PRICE, curve,
                                quoted_margin_bp=MARGIN_BP) == direct * 1e4


def test_floating_risk_wrappers_equal_the_direct_metrics_exactly():
    curve = usd_curve()
    oas_bp = floating.implied_oas(FREQ, MAT, VAL, PRICE, curve, quoted_margin_bp=MARGIN_BP)
    direct = core_float.frn_risk_metrics(VAL, MAT, curve, oas_bp * _BP,
                                         spread=MARGIN_BP * _BP, freq=FREQ)
    kw = dict(quoted_margin_bp=MARGIN_BP)
    assert floating.duration(FREQ, MAT, VAL, oas_bp, curve, **kw) == direct["eff_duration"]
    assert floating.dv01(FREQ, MAT, VAL, oas_bp, curve, **kw) == direct["dv01"]
    assert floating.convexity(FREQ, MAT, VAL, oas_bp, curve, **kw) == direct["convexity"]


def test_hybrid_wrapper_equals_the_direct_engine_call_exactly():
    curve = usd_curve()
    direct = core_hybrid.price_hybrid(VAL, MAT, curve, oas=300 * _BP,
                                      fixed_rate=FIXED_CPN / 100.0, switch_date=SWITCH,
                                      spread=MARGIN_BP * _BP, fixed_freq=FREQ)
    kw = dict(quoted_margin_bp=MARGIN_BP)
    assert hybrid.calculated_price(FIXED_CPN, FREQ, MAT, VAL, curve, SWITCH,
                                   oas=300.0, **kw) == direct.clean
    assert hybrid.accrued_interest(FIXED_CPN, FREQ, MAT, VAL, curve, SWITCH,
                                   **kw) == direct.accrued
    assert hybrid.next_switch_years(FIXED_CPN, FREQ, MAT, VAL, curve, SWITCH,
                                    **kw) == direct.next_switch_t


def test_hybrid_risk_wrappers_equal_the_direct_metrics_exactly():
    curve = usd_curve()
    kw = dict(quoted_margin_bp=MARGIN_BP)
    oas_bp = hybrid.implied_oas(FIXED_CPN, FREQ, MAT, VAL, PRICE, curve, SWITCH, **kw)
    direct = core_hybrid.hybrid_risk_metrics(VAL, MAT, curve, oas_bp * _BP,
                                             fixed_rate=FIXED_CPN / 100.0,
                                             switch_date=SWITCH, spread=MARGIN_BP * _BP,
                                             fixed_freq=FREQ)
    args = (FIXED_CPN, FREQ, MAT, VAL, oas_bp, curve, SWITCH)
    assert hybrid.duration(*args, **kw) == direct["eff_duration"]
    assert hybrid.dv01(*args, **kw) == direct["dv01"]
    assert hybrid.convexity(*args, **kw) == direct["convexity"]


def test_stepped_wrapper_equals_the_vanilla_engine_with_a_schedule_exactly():
    curve = usd_curve()
    sched = [(None, 0.07), (dt.date(2011, 4, 1), 0.075)]
    assert stepped.calculated_price(sched, FREQ, MAT, VAL, curve, oas=200.0) == \
        vanilla.calculated_price(0.0, FREQ, MAT, VAL, curve, oas=200.0,
                                 coupon_schedule=sched)
    assert stepped.implied_oas(sched, FREQ, MAT, VAL, PRICE, curve) == \
        vanilla.implied_oas(0.0, FREQ, MAT, VAL, PRICE, curve, coupon_schedule=sched)


def test_widening_and_tightening_are_the_same_price_at_a_shifted_spread():
    curve = usd_curve()
    kw = dict(quoted_margin_bp=MARGIN_BP)
    base = 300.0
    assert floating.widening(FREQ, MAT, VAL, base, curve, 10.0, **kw) == \
        floating.calculated_price(FREQ, MAT, VAL, curve, oas=base + 10.0, **kw)
    assert floating.tightening(FREQ, MAT, VAL, base, curve, 10.0, **kw) == \
        floating.calculated_price(FREQ, MAT, VAL, curve, oas=base - 10.0, **kw)
    assert hybrid.widening(FIXED_CPN, FREQ, MAT, VAL, base, curve, SWITCH, 10.0, **kw) == \
        hybrid.calculated_price(FIXED_CPN, FREQ, MAT, VAL, curve, SWITCH,
                                oas=base + 10.0, **kw)


# ------------------------------------------------------------------- product economics

def test_a_par_floater_is_worth_par_at_its_last_reset_whatever_rates_do():
    """Spread 0, no calibrated spread: the projected coupons telescope exactly, so the
    note is worth par AS OF ITS LAST RESET, accreted at the curve rate — for any level
    and any maturity. That identity is what the whole projection convention rests on.

    Stated on the DIRTY price, which is where it is exact. The clean price is par to
    within a few cents (pinned separately in test_frn), because clean subtracts a simple
    accrual from a continuously-discounted value.
    """
    import math
    for level in (0.001, 0.04, 0.12):
        for maturity in ("2014-04-01", "2039-04-01"):
            curve = flat_zero_curve(level)
            clean = floating.calculated_price(FREQ, maturity, VAL, curve, oas=0.0)
            accrued = floating.accrued_interest(FREQ, maturity, VAL, curve)
            # t_prev < 0: the last reset, in years before valuation
            t_prev = floating.next_reset_years(FREQ, maturity, VAL, curve) - 1.0 / FREQ
            assert clean + accrued == pytest.approx(100.0 * math.exp(-t_prev * level),
                                                    rel=1e-12)
            assert clean == pytest.approx(100.0, abs=0.05)


def test_floating_implied_oas_round_trips():
    curve = usd_curve()
    oas_bp = floating.implied_oas(FREQ, MAT, VAL, PRICE, curve, quoted_margin_bp=MARGIN_BP)
    back = floating.calculated_price(FREQ, MAT, VAL, curve, oas=oas_bp,
                                     quoted_margin_bp=MARGIN_BP)
    assert back == pytest.approx(PRICE, abs=1e-8)


def test_a_floaters_duration_is_one_coupon_period_not_its_maturity():
    """The signature floating-rate check: a 30-year floater carries the rate risk of a
    single coupon period, while the same-maturity fixed bond carries decades.

    WHICH end of that period depends on one input, and the two cases are exact — worth
    pinning, because a reader who knows only "duration ~ the next reset" will otherwise
    read the negative number as a bug:

    * ``current_coupon_pct`` GIVEN (the real case — the running coupon really was fixed
      at the last reset, and a curve bump cannot change it) -> duration = +time to the
      next reset, and independently of what that coupon is;
    * ``current_coupon_pct`` OMITTED (the current period projected off the curve like
      every other) -> the bump moves that coupon too, and the note behaves like a claim
      struck at the last reset -> duration = -time SINCE the last reset.
    """
    curve = flat_zero_curve(0.04)
    long_mat = "2039-04-01"
    to_next = floating.next_reset_years(FREQ, long_mat, VAL, curve)
    since_last = 1.0 / FREQ - to_next
    fixed_dur = vanilla.duration(4.0, FREQ, long_mat, VAL, 0.0, curve)

    for coupon in (4.0, 6.0):
        dur_fixed_cpn = floating.duration(FREQ, long_mat, VAL, 0.0, curve,
                                          current_coupon_pct=coupon)
        assert dur_fixed_cpn == pytest.approx(to_next, abs=1e-6)

    dur_projected = floating.duration(FREQ, long_mat, VAL, 0.0, curve)
    assert dur_projected == pytest.approx(-since_last, abs=1e-6)

    # both regimes: within one coupon period, and far below the fixed bond's 17 years
    for dur in (dur_projected, floating.duration(FREQ, long_mat, VAL, 0.0, curve,
                                                 current_coupon_pct=4.0)):
        assert abs(dur) <= 1.0 / FREQ
        assert abs(dur) < 0.05 * fixed_dur


def test_hybrid_degenerates_to_the_vanilla_engine_when_it_never_floats():
    """Switch at/after maturity: the answer must BE the fixed engine's, bit for bit."""
    curve = usd_curve()
    got = hybrid.calculated_price(FIXED_CPN, FREQ, MAT, VAL, curve, MAT, oas=250.0,
                                  quoted_margin_bp=MARGIN_BP)
    assert got == price_bond(VAL, MAT, FIXED_CPN / 100.0, curve, oas=250 * _BP,
                             freq=FREQ).clean


def test_hybrid_degenerates_to_the_floating_engine_when_already_floating():
    """Switch at/before valuation: the answer must BE the FRN engine's, bit for bit."""
    curve = usd_curve()
    got = hybrid.calculated_price(FIXED_CPN, FREQ, MAT, VAL, curve, "2008-01-01",
                                  oas=250.0, quoted_margin_bp=MARGIN_BP)
    assert got == floating.calculated_price(FREQ, MAT, VAL, curve, oas=250.0,
                                            quoted_margin_bp=MARGIN_BP)


def test_with_a_zero_margin_a_hybrid_is_exactly_a_bullet_to_the_switch():
    """The composition test. At margin 0 and spread 0 the floating leg telescopes to
    face x DF(switch) on ANY curve, so the hybrid IS the bond maturing at the switch."""
    for level in (0.01, 0.04, 0.09):
        curve = flat_zero_curve(level)
        glued = hybrid.calculated_price(FIXED_CPN, FREQ, MAT, VAL, curve, SWITCH,
                                        oas=0.0, quoted_margin_bp=0.0)
        bullet = vanilla.calculated_price(FIXED_CPN, FREQ, SWITCH, VAL, curve, oas=0.0)
        assert glued == pytest.approx(bullet, abs=1e-9)


def test_a_hybrids_duration_is_bounded_by_its_switch_not_its_maturity():
    curve = flat_zero_curve(0.04)
    far_mat, near_switch = "2066-04-01", "2016-04-01"
    kw = dict(quoted_margin_bp=MARGIN_BP)
    dur = hybrid.duration(FIXED_CPN, FREQ, far_mat, VAL, 300.0, curve, near_switch, **kw)
    switch_t = hybrid.next_switch_years(FIXED_CPN, FREQ, far_mat, VAL, curve,
                                        near_switch, **kw)
    fixed_dur = vanilla.duration(FIXED_CPN, FREQ, far_mat, VAL, 300.0, curve)
    assert 0.0 < dur < switch_t + 1.0
    assert dur < 0.25 * fixed_dur


def test_a_flat_schedule_is_arithmetically_the_plain_bond():
    curve = usd_curve()
    assert stepped.calculated_price([(None, 0.0625)], FREQ, MAT, VAL, curve, oas=200.0) \
        == pytest.approx(vanilla.calculated_price(6.25, FREQ, MAT, VAL, curve, oas=200.0),
                         abs=1e-12)


def test_a_step_already_in_the_past_prices_at_the_rate_now_in_force():
    """Row 13's actual shape: 7.00% before 01-Mar-2006, 7.50% after — at a 2009 valuation
    only the 7.50% is left, so the bond is a plain 7.50% bond."""
    curve = usd_curve()
    sched = stepped.parse_schedule("7.00% for t<01-Mar-2006 7.50% for t>=01-Mar-2006")
    assert sched == [(None, 0.07), (dt.date(2006, 3, 1), 0.075)]
    assert stepped.coupon_on(sched, dt.date(2009, 3, 31)) == 0.075
    assert stepped.calculated_price(sched, FREQ, MAT, VAL, curve, oas=200.0) == \
        pytest.approx(vanilla.calculated_price(7.5, FREQ, MAT, VAL, curve, oas=200.0),
                      abs=1e-12)


# ------------------------------------------------ unknowns are refused, not guessed

def test_an_unnumbered_margin_reads_as_a_data_gap_not_a_zero():
    assert floating.quoted_margin_bp_from_text("EURIBOR + Spread") is None
    assert floating.quoted_margin_bp_from_text("3M USD LIBOR + 45bp") == 45.0
    assert floating.quoted_margin_bp_from_text("LIBOR + 0.50%") == 50.0


def test_a_step_up_without_its_steps_reads_as_a_data_gap_not_a_guess():
    assert stepped.parse_schedule("Step-up schedule") is None
    assert stepped.parse_schedule(None, "") is None


def test_a_missing_margin_cannot_reach_the_hybrid_engine():
    with pytest.raises(ValueError, match="data gap"):
        hybrid.calculated_price(FIXED_CPN, FREQ, MAT, VAL, FLAT, SWITCH,
                                quoted_margin_bp=None)


def test_a_margin_sent_in_the_wrong_units_is_refused():
    with pytest.raises(ValueError, match="BASIS POINTS"):
        floating.calculated_price(FREQ, MAT, VAL, FLAT, quoted_margin_bp=9999.0)
    with pytest.raises(ValueError, match=">= 0"):
        floating.calculated_price(FREQ, MAT, VAL, FLAT, quoted_margin_bp=-1.0)


def test_a_percent_scaled_coupon_schedule_is_refused():
    """7.5 where 0.075 was meant would price a 750% coupon and look like a huge spread."""
    with pytest.raises(ValueError, match="PERCENT"):
        stepped.calculated_price([(None, 7.5)], FREQ, MAT, VAL, FLAT)
    with pytest.raises(ValueError, match="empty"):
        stepped.calculated_price([], FREQ, MAT, VAL, FLAT)


def test_an_unsupported_frequency_is_refused_on_every_product():
    with pytest.raises(ValueError, match="1, 2, 4 or 12"):
        floating.calculated_price(3, MAT, VAL, FLAT)
    with pytest.raises(ValueError, match="1, 2, 4 or 12"):
        hybrid.calculated_price(FIXED_CPN, 3, MAT, VAL, FLAT, SWITCH)
    with pytest.raises(ValueError, match="1, 2, 4 or 12"):
        stepped.calculated_price([(None, 0.07)], 3, MAT, VAL, FLAT)


def test_a_current_coupon_sent_as_a_decimal_is_refused():
    """0.0625 where 6.25 was meant is a 6-basis-point coupon — plausible, and wrong."""
    with pytest.raises(ValueError, match="PERCENT"):
        floating.calculated_price(FREQ, MAT, VAL, FLAT, current_coupon_pct=625.0)


# ------------------------------------------------------------------- input catalogue

def test_the_catalogue_documents_every_new_products_inputs():
    fields = {row["field"] for row in bonds_input.INPUT_CATALOGUE}
    assert {"quoted_margin_bp", "switch_date", "float_freq", "current_coupon",
            "coupon_schedule"} <= fields


def test_volatility_is_declared_inapplicable_with_a_reason_per_option_free_product():
    for kind in ("vanilla", "stepped", "floating", "fixed_to_floating"):
        assert kind in bonds_input.VOLATILITY_NOT_APPLICABLE
        assert len(bonds_input.VOLATILITY_NOT_APPLICABLE[kind]) > 40
    # the products that DO consume it must not be listed as inapplicable
    for kind in ("callable", "puttable", "sinking"):
        assert kind not in bonds_input.VOLATILITY_NOT_APPLICABLE
