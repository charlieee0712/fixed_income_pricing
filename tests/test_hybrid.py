"""Fixed-then-float hybrid engine invariants (design locked 2026-07-20).

No workbook needed (stub curves) — never skipped. The two degenerate limits compare BIT-FOR-BIT
against the validated engines (they delegate, so equality is by construction and guards the
delegation wiring); the COMPOSITION is validated by the margin-0 telescoping identity (exact on
ANY curve, not just flat) and by near-limit continuity.
"""
import math

from pricing.bond_price import price_bond
from pricing.calibrate import implied_oas
from pricing.frn import price_frn
from pricing.hybrid import hybrid_risk_metrics, implied_oas_hybrid, price_hybrid
from pricing.risk import risk_metrics


class FlatCurve:
    def __init__(self, z=0.04):
        self.z = z

    def zero_rate(self, t, spread=0.0):
        return self.z + spread


class SlopedCurve:
    """z(t) = a + b*t — a non-trivial curve for the any-curve identity checks."""

    def __init__(self, a=0.02, b=0.002):
        self.a, self.b = a, b

    def zero_rate(self, t, spread=0.0):
        return self.a + self.b * t + spread


VAL = "2009-03-31"


# ---------- invariant 1: switch >= maturity == the vanilla fixed engine, bit-for-bit ----------

def test_switch_at_maturity_equals_vanilla_bitwise():
    c = SlopedCurve()
    for oas in (0.0, 0.0234):
        h = price_hybrid(VAL, "2016-05-17", c, oas=oas, fixed_rate=0.07, switch_date="2016-05-17",
                         spread=0.0235, fixed_freq=2, float_freq=4)
        v = price_bond(VAL, "2016-05-17", 0.07, c, oas=oas, freq=2)
        assert h.clean == v.clean and h.dirty == v.dirty and h.accrued == v.accrued


def test_switch_beyond_maturity_equals_vanilla_bitwise():
    c = FlatCurve(0.05)
    h = price_hybrid(VAL, "2014-10-27", c, oas=0.01, fixed_rate=0.04375, switch_date="2020-01-01",
                     fixed_freq=1)
    v = price_bond(VAL, "2014-10-27", 0.04375, c, oas=0.01, freq=1)
    assert h.clean == v.clean and h.dirty == v.dirty


# ---------- invariant 2: switch <= valuation == the FRN engine, bit-for-bit ----------

def test_switch_at_valuation_equals_frn_bitwise():
    c = SlopedCurve()
    for oas in (0.0, 0.0234):
        h = price_hybrid(VAL, "2019-05-06", c, oas=oas, fixed_rate=0.0475, switch_date=VAL,
                         spread=0.0146, fixed_freq=1, float_freq=4)
        f = price_frn(VAL, "2019-05-06", c, oas=oas, current_coupon=None, spread=0.0146, freq=4)
        assert h.clean == f.clean and h.dirty == f.dirty and h.accrued == f.accrued
        assert h.next_switch_t == 0.0


def test_switch_before_valuation_equals_frn_bitwise():
    c = FlatCurve(0.03)
    h = price_hybrid(VAL, "2014-04-01", c, oas=0.005, fixed_rate=0.0375, switch_date="2009-03-01",
                     spread=0.0182, fixed_freq=2, float_freq=4)
    f = price_frn(VAL, "2014-04-01", c, oas=0.005, current_coupon=None, spread=0.0182, freq=4)
    assert h.clean == f.clean and h.dirty == f.dirty


# ---------- invariant 3: margin-0 telescoping — hybrid == fixed bullet TO THE SWITCH ----------
# Stronger than the flat-curve par-floater identity: with spread=0 and oas=0 the floating leg
# telescopes EXACTLY to face*DF(t_switch) on ANY curve, so the whole hybrid equals the
# fixed-to-switch bullet (= the price-to-call reference bond). This is the composition test.

def test_margin0_identity_flat_and_sloped():
    for c in (FlatCurve(0.04), SlopedCurve(0.02, 0.0025)):
        h = price_hybrid(VAL, "2066-05-17", c, oas=0.0, fixed_rate=0.07, switch_date="2016-05-17",
                         spread=0.0, fixed_freq=2, float_freq=4)
        bullet = price_bond(VAL, "2016-05-17", 0.07, c, oas=0.0, freq=2)
        assert abs(h.dirty - bullet.dirty) < 1e-9
        assert abs(h.clean - bullet.clean) < 1e-9


def test_spread_and_oas_monotonicity():
    c = FlatCurve(0.04)
    kw = dict(fixed_rate=0.06, switch_date="2016-05-17", fixed_freq=2, float_freq=4)
    base = price_hybrid(VAL, "2036-05-17", c, oas=0.0, spread=0.0, **kw).clean
    up = price_hybrid(VAL, "2036-05-17", c, oas=0.0, spread=0.0150, **kw).clean
    dn = price_hybrid(VAL, "2036-05-17", c, oas=0.02, spread=0.0, **kw).clean
    assert up > base                 # a positive quoted margin adds value
    assert dn < base                 # price strictly decreasing in the OAS


# ---------- implied-OAS round-trip ----------

def test_hybrid_oas_roundtrip():
    c = SlopedCurve()
    kw = dict(fixed_rate=0.06375, switch_date="2017-11-15", spread=0.02289,
              fixed_freq=2, float_freq=4)
    p = price_hybrid(VAL, "2067-11-15", c, oas=0.0345, **kw).clean
    oas = implied_oas_hybrid(p, VAL, "2067-11-15", c, **kw)
    assert abs(oas - 0.0345) < 1e-8


# ---------- invariant 4: duration bounded by the switch, << same-maturity fixed ----------

def test_duration_dominated_by_fixed_leg():
    c = FlatCurve(0.04)
    hy = hybrid_risk_metrics(VAL, "2039-03-31", c, oas=0.005, fixed_rate=0.06,
                             switch_date="2016-03-31", spread=0.0150, fixed_freq=2, float_freq=4)
    fx = risk_metrics(VAL, "2039-03-31", 0.06, c, 0.005, freq=2)
    t_sw = hy["next_switch_t"]
    assert 6.5 < t_sw < 7.5                              # ~7y to the switch, reported per bond
    assert hy["eff_duration"] < 0.65 * fx["eff_duration"]  # << the same-maturity pure fixed
    assert 0.0 < hy["eff_duration"] < t_sw + 2.5         # roughly bounded by the switch time


# ---------- near-limit continuity (the composition approaches the delegated engines) ----------

def test_continuity_near_limits():
    c = FlatCurve(0.04)
    # switch 1 day after valuation ~ FRN (fixed_rate ~ curve level, so the single remaining fixed
    # period barely differs from the FRN's forward estimate of it)
    h = price_hybrid(VAL, "2019-05-06", c, oas=0.01, fixed_rate=0.04, switch_date="2009-04-01",
                     spread=0.0, fixed_freq=2, float_freq=2)
    f = price_frn(VAL, "2019-05-06", c, oas=0.01, current_coupon=None, spread=0.0, freq=2)
    assert abs(h.clean - f.clean) < 1.0
    # switch 10 days before maturity ~ vanilla (10-day floating stub + a 10-day grid shift)
    h2 = price_hybrid(VAL, "2016-05-17", c, oas=0.01, fixed_rate=0.07, switch_date="2016-05-07",
                      spread=0.0, fixed_freq=2, float_freq=2)
    v2 = price_bond(VAL, "2016-05-17", 0.07, c, oas=0.01, freq=2)
    assert abs(h2.clean - v2.clean) < 1.5


# ---------- invariant 5: perpetual truncation + deep-discount to-call spuriousness ----------

def test_perp_truncation_finite_and_face_negligible():
    c = FlatCurve(0.04)
    # BNP-shaped: fixed 7.195% to 2037-06-25, then fwd+129bp, 90y truncation, crisis-size OAS
    r = price_hybrid(VAL, "2099-03-31", c, oas=0.10, fixed_rate=0.07195,
                     switch_date="2037-06-25", spread=0.0129, fixed_freq=2, float_freq=4)
    assert 0.0 < r.clean < 80.0
    assert 100.0 * math.exp(-90.0 * (0.04 + 0.10)) < 0.01   # the truncation face is worthless


def test_deep_discount_to_call_oas_is_spurious_vs_hybrid():
    # UniCredit-shaped: BT 36 deep discount. The market prices EXTENSION, so the to-call OAS
    # (fixed bullet to the switch) blows far past the hybrid OAS -> reference column only.
    c = FlatCurve(0.04)
    bt = 36.0
    o_h = implied_oas_hybrid(bt, VAL, "2099-03-31", c, fixed_rate=0.04028,
                             switch_date="2015-10-27", spread=0.0176, fixed_freq=1, float_freq=4)
    o_tc = implied_oas(bt, VAL, "2015-10-27", 0.04028, c, freq=1)
    assert o_tc > 1.5 * o_h
    assert o_tc - o_h > 0.05
