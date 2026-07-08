"""FRN engine invariants (Step 4, Mario 2026-07-08). No workbook needed (flat stub curve) — never
skipped. The duration checks are the signature floating-rate reliability tests."""
from pricing.bond_price import price_bond  # noqa: F401  (kept for parity / future use)
from pricing.frn import (
    frn_risk_metrics,
    implied_oas_frn,
    parse_frn_spread,
    price_frn,
    simple_forward,
)
from pricing.risk import risk_metrics


class FlatCurve:
    def __init__(self, z=0.04):
        self.z = z

    def zero_rate(self, t, spread=0.0):
        return self.z + spread


# ---------- spread parser (None principle, as in Step 3) ----------
def test_parse_frn_spread():
    assert parse_frn_spread("EURIBOR + 45bp") == 0.0045
    assert parse_frn_spread("USD LIBOR + 0.50%") == 0.005
    assert parse_frn_spread("EURIBOR + Spread") is None          # the real URS format -> data gap
    assert parse_frn_spread("Reference Rate + Spread", None) is None


# ---------- invariant 1: a pure floater prices at par, for any curve level (the reset identity) ----------
def test_par_at_reset_flat_curve():
    r = price_frn("2009-06-10", "2019-06-10", FlatCurve(0.04), oas=0.0, current_coupon=None,
                  spread=0.0, freq=2)
    assert abs(r.clean - 100.0) < 0.05


def test_par_holds_under_any_curve_shift():
    c = FlatCurve(0.04)
    for shift in (-0.03, 0.0, 0.05):
        r = price_frn("2009-06-10", "2019-06-10", c, current_coupon=None, spread=0.0, freq=2,
                      curve_shift=shift)
        assert abs(r.clean - 100.0) < 0.05          # floater ~ par regardless of the rate level


# ---------- invariant 2: implied-OAS round-trip ----------
def test_oas_roundtrip():
    c = FlatCurve(0.04)
    val, mat = "2009-06-10", "2016-06-10"
    p = price_frn(val, mat, c, oas=0.0123, current_coupon=0.05, spread=0.0, freq=2).clean
    oas = implied_oas_frn(p, val, mat, c, current_coupon=0.05, spread=0.0, freq=2)
    assert abs(oas - 0.0123) < 1e-8


# ---------- invariant 3: near-par floater has ~ zero rate duration (resets its risk away) ----------
def test_frn_near_par_duration_is_small():
    c = FlatCurve(0.04)
    m = frn_risk_metrics("2009-06-10", "2019-06-10", c, oas=0.001, current_coupon=0.041, spread=0.0,
                         freq=2)
    assert abs(m["eff_duration"]) < 0.2           # ~ 0, not the ~8y of a 10y fixed bond
    assert m["next_reset_t"] < 1.0


# ---------- invariant 4 (THE reliability check): FRN duration <<< same-maturity fixed, even at 78y ----------
def test_frn_duration_far_below_fixed():
    c = FlatCurve(0.04)
    for mat in ("2019-06-10", "2087-03-07"):      # 10y and a 78y note like the real 2087 one
        frn = frn_risk_metrics("2009-06-10", mat, c, oas=0.02, current_coupon=0.05, spread=0.0, freq=2)
        fixed = risk_metrics("2009-06-10", mat, 0.05, c, 0.02, freq=2)
        assert abs(fixed["eff_duration"]) > 6.0                       # the fixed bond is long
        assert abs(frn["eff_duration"]) < 0.7 * abs(fixed["eff_duration"])  # the FRN is far shorter


def test_simple_forward_flat_curve():
    f = simple_forward(FlatCurve(0.04), 1.0, 1.5)
    assert 0.039 < f < 0.041
