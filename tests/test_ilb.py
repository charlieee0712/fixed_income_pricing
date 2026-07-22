"""ILB engine invariants (phase 2). Flat stub curve — no workbook needed, never skipped.

The load-bearing checks: exact degeneration to ``price_bond`` (same conventions), exact ratio
scaling, and the inflation/spread equivalence that PROVES the negative-spread-at-zero-inflation
mechanism (spread ~ -breakeven) is arithmetic, not a bug."""
import math

from pricing.bond_price import price_bond
from pricing.ilb import ilb_risk_metrics, implied_spread_ilb, price_ilb
from pricing.risk import risk_metrics


class FlatCurve:
    def __init__(self, z=0.04):
        self.z = z

    def zero_rate(self, t, spread=0.0):
        return self.z + spread


VAL = "2009-03-31"


# ---------- exact degeneration: inflation=0, ratio=1 == the vanilla engine ----------
def test_degenerates_to_price_bond():
    c = FlatCurve(0.03)
    for cpn, mat in ((0.02375, "2025-01-15"), (0.06, "2016-01-15"), (0.0, "2018-07-15")):
        v = price_bond(VAL, mat, cpn, c, oas=0.005)
        i = price_ilb(VAL, mat, cpn, c, spread=0.005, index_ratio=1.0, inflation=0.0)
        assert abs(i.clean - v.clean) < 1e-9
        assert abs(i.dirty - v.dirty) < 1e-9
        assert abs(i.accrued - v.accrued) < 1e-9


# ---------- exact scaling: ratio r multiplies clean/dirty/accrued by r ----------
def test_index_ratio_scales_price():
    c = FlatCurve(0.035)
    r = 1.284379                                     # the 2029 TIPS recovered ratio
    v = price_bond(VAL, "2029-04-15", 0.03875, c, oas=-0.01)
    i = price_ilb(VAL, "2029-04-15", 0.03875, c, spread=-0.01, index_ratio=r)
    assert abs(i.clean - r * v.clean) < 1e-9
    assert abs(i.dirty - r * v.dirty) < 1e-9
    assert abs(i.accrued - r * v.accrued) < 1e-9


# ---------- the -breakeven mechanism, as an exact identity ----------
def test_inflation_equals_spread_shift():
    # (1+pi)^t * exp(-t(z+s)) == exp(-t(z + s - ln(1+pi))): pricing WITH inflation pi at spread s
    # is pricing at ZERO inflation at spread s - ln(1+pi). Hence at inflation=0 the calibrated
    # spread sits ~ -ln(1+breakeven) ~ -breakeven BELOW the credit-free level: negative by design.
    c = FlatCurve(0.04)
    pi = 0.013                                       # a 2009-03-ish 10y breakeven
    a = price_ilb(VAL, "2019-01-15", 0.02, c, spread=0.002, index_ratio=1.1, inflation=pi)
    b = price_ilb(VAL, "2019-01-15", 0.02, c, spread=0.002 - math.log1p(pi), index_ratio=1.1)
    assert abs(a.clean - b.clean) < 1e-9

    target = price_ilb(VAL, "2019-01-15", 0.02, c, spread=0.0, index_ratio=1.1, inflation=pi).clean
    s0 = implied_spread_ilb(target, VAL, "2019-01-15", 0.02, c, index_ratio=1.1, inflation=0.0)
    assert abs(s0 - (-math.log1p(pi))) < 1e-8        # zero-inflation spread == -breakeven, exactly


# ---------- calibration round-trip (negative spreads are the normal regime) ----------
def test_spread_roundtrip():
    c = FlatCurve(0.04)
    for s in (-0.013, 0.0, 0.021):
        p = price_ilb(VAL, "2027-01-15", 0.02375, c, spread=s, index_ratio=1.047).clean
        got = implied_spread_ilb(p, VAL, "2027-01-15", 0.02375, c, index_ratio=1.047)
        assert abs(got - s) < 1e-8


# ---------- duration: ratio cancels; static inflation -> the full (real-rate) duration ----------
def test_duration_equals_vanilla():
    c = FlatCurve(0.04)
    i = ilb_risk_metrics(VAL, "2028-01-15", 0.0175, c, -0.012, index_ratio=1.008)
    v = risk_metrics(VAL, "2028-01-15", 0.0175, c, -0.012)
    assert abs(i["eff_duration"] - v["eff_duration"]) < 1e-6
    assert i["eff_duration"] > 10                    # a long TIPS is a LONG real-rate instrument


# ---------- degenerate shapes ----------
def test_zero_real_coupon_single_flow():
    c = FlatCurve(0.05)
    r = price_ilb(VAL, "2018-07-15", 0.0, c, index_ratio=1.2, inflation=0.02)
    assert r.accrued == 0.0
    assert len([cf for cf in r.cashflows if cf[3] > 0]) == 1     # only the indexed redemption pays
    t = r.cashflows[-1][1]
    expect = 100.0 * 1.2 * (1.02 ** t) * math.exp(-t * 0.05)
    assert abs(r.dirty - expect) < 1e-9


def test_matured_is_zero():
    assert price_ilb("2010-01-01", "2009-06-30", 0.02, FlatCurve()).clean == 0.0
