"""Template-layout sample locks (Mario code-structure directive, 2026-08-15).

The ``pricer/`` package must be a faithful RE-EXPRESSION of the validated engines,
never a fork: the old ``pricing.*`` modules delegate to it (same objects), the
per-metric asset wrappers reprice the engine bit-for-bit (only units change:
percent/bp at the asset layer, decimals in core), and the flat-curve input type is
exact. Behavior preservation at scale is pinned by the ENTIRE pre-existing suite
running unchanged on the shims.
"""
import datetime as dt
import math

import pytest

import pricing.bond_price as bond_price
import pricing.calibrate as calibrate
import pricing.risk as risk
from pricer.assets.corporate import bonds_input, vanilla
from pricer.core.market import spreads
from pricer.core.market.curves import flat_zero_curve
from pricer.core.pricing import analytical, cashflows
from pricer.core.risk import sensitivities
from pricer.core.utils import dates

VAL = "2009-03-31"
MAT = "2017-06-26"
CURVE = flat_zero_curve(0.04)


def test_shims_are_the_same_objects():
    assert bond_price.price_bond is analytical.price_fixed_rate_bond
    assert bond_price.accrued_interest is cashflows.accrued_interest
    assert bond_price.lattice_inputs is cashflows.lattice_inputs
    assert bond_price.coupon_dates is dates.coupon_dates
    assert calibrate.near_maturity is spreads.near_maturity


def test_wrapper_reprices_engine_exactly():
    r = bond_price.price_bond(VAL, MAT, 0.065, CURVE, oas=150.0 * 1e-4)
    assert vanilla.calculated_price(6.5, 2, MAT, VAL, CURVE, oas=150.0) == r.clean


def test_implied_oas_roundtrip_and_units():
    px = vanilla.calculated_price(6.5, 2, MAT, VAL, CURVE, oas=150.0)
    oas_bp = vanilla.implied_oas(6.5, 2, MAT, VAL, px, CURVE)
    assert abs(oas_bp - 150.0) < 1e-5                       # bp round-trip
    assert oas_bp == calibrate.implied_oas(px, VAL, MAT, 0.065, CURVE) * 1e4


def test_per_metric_functions_match_risk_metrics():
    rm = risk.risk_metrics(VAL, MAT, 0.065, CURVE, 150.0 * 1e-4)
    assert vanilla.duration(6.5, 2, MAT, VAL, 150.0, CURVE) == rm["eff_duration"]
    assert vanilla.dv01(6.5, 2, MAT, VAL, 150.0, CURVE) == rm["dv01"]
    assert vanilla.convexity(6.5, 2, MAT, VAL, 150.0, CURVE) == rm["convexity"]


def test_widening_tightening_bracket_the_base():
    base = vanilla.calculated_price(6.5, 2, MAT, VAL, CURVE, oas=150.0)
    wide = vanilla.widening(6.5, 2, MAT, VAL, 150.0, CURVE, bp_adjust=10.0)
    tight = vanilla.tightening(6.5, 2, MAT, VAL, 150.0, CURVE, bp_adjust=10.0)
    assert wide < base < tight
    assert wide == vanilla.calculated_price(6.5, 2, MAT, VAL, CURVE, oas=160.0)


def test_flat_curve_zero_coupon_is_exact():
    r = bond_price.price_bond(VAL, MAT, 0.0, CURVE)
    t = (dt.date(2017, 6, 26) - dt.date(2009, 3, 31)).days / dates.YEAR_DAYS
    assert math.isclose(r.clean, 100.0 * math.exp(-0.04 * t), rel_tol=0, abs_tol=1e-9)
    assert r.accrued == 0.0


def test_sensitivity_formulas_pure_arithmetic():
    assert sensitivities.effective_duration_from_prices(99.0, 101.0, 100.0, 1e-4) == 100.0
    assert sensitivities.dv01_from_prices(99.0, 101.0, 1e-4) == 1.0
    assert sensitivities.convexity_from_prices(99.0, 101.0, 100.0, 1e-4) == 0.0


def test_input_catalogue_and_validation():
    table = bonds_input.describe_inputs()
    assert "coupon" in table and "NOT used" in table        # day-count marked unused
    with pytest.raises(ValueError):
        vanilla.calculated_price(6.5, 3, MAT, VAL, CURVE)   # bad frequency
    with pytest.raises(ValueError):
        vanilla.calculated_price(650.0, 2, MAT, VAL, CURVE)  # bp-looking coupon
