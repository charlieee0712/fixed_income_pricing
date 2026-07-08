"""Unit tests for the coupon-schedule parser + schedule-aware pricing (Step 3, Mario 2026-07-08).

String parsing is fragile, so the parser is tested exhaustively. The pricing tests use a flat stub
curve, so they run anywhere (no workbook needed — never skipped)."""
import datetime as dt

from pricing.bond_price import price_bond
from pricing.coupon_schedule import coupon_at, parse_coupon_schedule


# ---------- parser ----------
def test_parse_segmented_ge_lt():
    # the real URS stepped bond (note the double space and the ≥ glyph)
    s = parse_coupon_schedule("7.00% for  t<01-Mar-2006 7.50% for t≥01-Mar-2006")
    assert s == [(None, 0.07), (dt.date(2006, 3, 1), 0.075)]


def test_parse_until_then():
    s = parse_coupon_schedule("6.25% until 15-Jun-2015, then 8.00%")
    assert s == [(None, 0.0625), (dt.date(2015, 6, 15), 0.08)]


def test_parse_single_fixed():
    assert parse_coupon_schedule("Fixed 6.00%") == [(None, 0.06)]


def test_parse_no_numbers_returns_none():
    assert parse_coupon_schedule("Step-up schedule") is None
    assert parse_coupon_schedule("Zero coupon / structured payoff") is None
    assert parse_coupon_schedule(None) is None
    assert parse_coupon_schedule(float("nan")) is None


def test_parse_ambiguous_returns_none():
    # two rates but no date -> cannot place the step -> refuse to guess (flag, don't mis-price)
    assert parse_coupon_schedule("steps between 5.00% and 6.00%") is None


def test_parse_first_nonempty_of_several():
    s = parse_coupon_schedule("Step-up schedule", "5.00% until 01-Jan-2010, then 6.00%")
    assert s == [(None, 0.05), (dt.date(2010, 1, 1), 0.06)]


# ---------- coupon_at ----------
def test_coupon_at_boundaries():
    s = [(None, 0.07), (dt.date(2006, 3, 1), 0.075)]
    assert coupon_at(s, dt.date(2005, 1, 1)) == 0.07
    assert coupon_at(s, dt.date(2006, 3, 1)) == 0.075   # >= boundary takes the new rate
    assert coupon_at(s, dt.date(2009, 6, 10)) == 0.075


# ---------- schedule-aware pricing ----------
class FlatCurve:
    def __init__(self, z=0.04):
        self.z = z

    def zero_rate(self, t):
        return self.z


def test_past_step_reduces_to_flat():
    # switch date before valuation -> every remaining coupon is the post-step rate -> identical to flat
    c = FlatCurve(0.04)
    val, mat = "2009-06-10", "2011-03-01"
    sched = [(None, 0.07), (dt.date(2006, 3, 1), 0.075)]
    p_sched = price_bond(val, mat, 0.075, c, coupon_schedule=sched).clean
    p_flat = price_bond(val, mat, 0.075, c).clean
    assert abs(p_sched - p_flat) < 1e-9


def test_future_step_priced_between_flats():
    # a genuine future step (4% then 8%) prices strictly between flat-4% and flat-8%
    c = FlatCurve(0.05)
    val, mat = "2010-01-01", "2020-01-01"
    sched = [(None, 0.04), (dt.date(2015, 1, 1), 0.08)]
    p_sched = price_bond(val, mat, 0.0, c, coupon_schedule=sched).clean
    p_lo = price_bond(val, mat, 0.04, c).clean
    p_hi = price_bond(val, mat, 0.08, c).clean
    assert p_lo < p_sched < p_hi


def test_zero_is_single_discounted_face():
    # coupon 0 -> the only non-zero cash flow is the face at maturity (degenerate vanilla)
    c = FlatCurve(0.05)
    r = price_bond("2009-06-10", "2037-08-15", 0.0, c)
    assert all(cf.amount in (0.0, 100.0) for cf in r.cashflows)
    assert r.cashflows[-1].amount == 100.0
    assert 0.0 < r.clean < 100.0
