"""Invariant tests for the callable/putable short-rate lattice (pricing/lattice.py).

Validation is by INVARIANTS, not a legacy golden — BondOAS cannot be reproduced without Bloomberg
(short-end fixings + call/put/sink schedules) or its bespoke ASCII tables (WORKLOG 2026-07-02). These
tests are hermetic: a synthetic ZeroCurve built in-process, numpy/pandas only (no client data, no
scipy), so they run in the repo .venv.

Invariants covered:
  (i)   arbitrage-free: the lattice reprices the curve's zeros to the curve DFs, and a par-coupon
        bond to 100 (and the straight-bond price is sigma-invariant == direct curve discounting).
  (ii)  option ordering: callable <= straight <= putable (same bond / OAS / sigma).
  (iii) zero-vol degeneracy: sigma=0 -> straight == curve-discounted; callable(sigma=0) == straight
        for an out-of-the-money (discount) bond; and option value grows monotonically with sigma.
The 4th agreed invariant — effective duration vs the custodian 'Duration - effective' (AQ) column —
needs the client workbook, so it lives in the driver (scripts/callable_risk.py), not here.
"""
import numpy as np
import pandas as pd
import pytest

from curves.zero_curve import ZeroCurve
from pricing.lattice import ShortRateLattice

FREQ = "Semiannual"


def curve_from_z(zfun, freq=FREQ, tmax=31):
    """Build a ZeroCurve from a continuous-zero function z(t) (decimal)."""
    months = np.arange(0, int(tmax * 12) + 1) / 12.0
    z = np.array([zfun(t) for t in months])
    grid = pd.DataFrame({"Maturity": months, f"{freq}_Rate": z * 100.0, f"{freq}_DF": np.exp(-z * months)})
    return ZeroCurve(grid, freq=freq)


FLAT3 = lambda t: 0.03
UP = lambda t: 0.02 + 0.003 * t            # rising 2% -> ~4.7% at 9y
DOWN = lambda t: 0.05 - 0.002 * t          # falling


def _par_coupon(curve, lat):
    """Coupon rate that prices to par on the lattice grid using the curve's own DFs."""
    P = np.array([curve.discount_factor(t) for t in lat.t[1:]])
    return (1.0 - P[-1]) * lat.freq / P.sum()


# ---- (i) arbitrage-free ----
@pytest.mark.parametrize("zfun", [FLAT3, UP, DOWN])
@pytest.mark.parametrize("sigma", [0.0, 0.15, 0.30])
def test_zero_reprices_curve_df(zfun, sigma):
    c = curve_from_z(zfun)
    lat = ShortRateLattice(c, T=10, freq=2, sigma=sigma)
    p = lat.price_bond(coupon_rate=0.0, oas=0.0)          # zero-coupon: 100 at maturity only
    assert p / 100.0 == pytest.approx(c.discount_factor(lat.T), abs=1e-8)


@pytest.mark.parametrize("zfun", [FLAT3, UP, DOWN])
@pytest.mark.parametrize("sigma", [0.10, 0.25])
def test_par_bond_reprices_to_100(zfun, sigma):
    c = curve_from_z(zfun)
    lat = ShortRateLattice(c, T=7, freq=2, sigma=sigma)
    cstar = _par_coupon(c, lat)
    assert lat.price_bond(cstar, oas=0.0) == pytest.approx(100.0, abs=1e-6)


@pytest.mark.parametrize("sigma", [0.0, 0.12, 0.28])
def test_straight_price_is_sigma_invariant(sigma):
    """Options off -> the lattice price must equal direct curve discounting for ANY sigma."""
    c = curve_from_z(UP)
    lat = ShortRateLattice(c, T=8, freq=2, sigma=sigma)
    P = np.array([c.discount_factor(t) for t in lat.t[1:]])
    direct = (0.05 / 2 * 100) * P.sum() + 100 * P[-1]
    assert lat.price_bond(0.05, oas=0.0) == pytest.approx(direct, abs=1e-7)


# ---- (ii) option ordering ----
@pytest.mark.parametrize("zfun", [FLAT3, UP, DOWN])
def test_callable_le_straight_le_putable(zfun):
    c = curve_from_z(zfun)
    lat = ShortRateLattice(c, T=10, freq=2, sigma=0.25)
    cr = 0.05
    straight = lat.price_bond(cr, 0.0)
    callable_ = lat.price_bond(cr, 0.0, call_price=lat.call_array([(1.0, 100.0)]))
    putable = lat.price_bond(cr, 0.0, put_price=lat.put_array([(1.0, 100.0)]))
    assert callable_ <= straight + 1e-9
    assert straight <= putable + 1e-9


# ---- (iii) zero-vol degeneracy + monotonicity ----
def test_zero_vol_straight_equals_curve():
    c = curve_from_z(UP)
    lat = ShortRateLattice(c, T=8, freq=2, sigma=0.0)
    P = np.array([c.discount_factor(t) for t in lat.t[1:]])
    direct = (0.03 / 2 * 100) * P.sum() + 100 * P[-1]
    assert lat.price_bond(0.03, 0.0) == pytest.approx(direct, abs=1e-7)


def test_zero_vol_callable_equals_straight_when_otm():
    """Deep-discount bond: par call never in the money -> callable == straight at sigma=0."""
    c = curve_from_z(UP)
    lat = ShortRateLattice(c, T=8, freq=2, sigma=0.0)
    cr = 0.01
    s = lat.price_bond(cr, 0.0)
    k = lat.price_bond(cr, 0.0, call_price=lat.call_array([(1.0, 100.0)]))
    assert s < 100.0                                   # confirm it is a discount bond
    assert k == pytest.approx(s, abs=1e-9)


def test_option_value_monotone_in_sigma():
    c = curve_from_z(FLAT3)
    ov = []
    for sig in (0.0, 0.10, 0.20, 0.35):
        lat = ShortRateLattice(c, T=10, freq=2, sigma=sig)
        st = lat.price_bond(0.05, 0.0)
        cl = lat.price_bond(0.05, 0.0, call_price=lat.call_array([(1.0, 100.0)]))
        ov.append(st - cl)
    assert all(ov[i] <= ov[i + 1] + 1e-9 for i in range(len(ov) - 1))   # non-decreasing
    assert ov[-1] > ov[0] + 1e-6                                        # real option value at high sigma


# ---- implied OAS round-trips, and effective duration is shorter for a callable ----
def test_implied_oas_roundtrip():
    c = curve_from_z(UP)
    lat = ShortRateLattice(c, T=9, freq=2, sigma=0.2)
    cp = lat.call_array([(2.0, 100.0)])
    target = lat.price_bond(0.06, oas=0.0123, call_price=cp)
    solved = lat.implied_oas(target, 0.06, call_price=cp)
    assert solved == pytest.approx(0.0123, abs=1e-6)


def test_callable_duration_shorter_than_straight():
    c = curve_from_z(FLAT3)
    lat = ShortRateLattice(c, T=12, freq=2, sigma=0.25)
    cr = 0.06                                          # premium coupon -> call bites
    cp = lat.call_array([(1.0, 100.0)])
    dur_straight = lat.risk_metrics(cr, 0.0)["eff_duration"]
    dur_callable = lat.risk_metrics(cr, 0.0, call_price=cp)["eff_duration"]
    assert dur_callable < dur_straight


# ---- schedule API (Mario 2026-07-03): single-entry contents + multi-date (step) schedule ----
def test_call_array_single_entry_contents():
    """A one-row schedule => inactive (+inf) at root/terminal, the call price at every step on/after
    the call time — pins the exact semantics the old hard-coded par_call_array used to bake in."""
    c = curve_from_z(FLAT3)
    lat = ShortRateLattice(c, T=5, freq=2, sigma=0.2)          # N = 10 steps
    arr = lat.call_array([(2.0, 100.0)])
    assert np.isposinf(arr[0]) and np.isposinf(arr[lat.N])     # never callable at issue or redemption
    for i in range(1, lat.N):
        assert arr[i] == (100.0 if lat.t[i] >= 2.0 - 1e-9 else np.inf)


def test_multi_date_call_schedule_monotone():
    """A step-down schedule (call @102 early -> @100 late) must price BETWEEN the flat-@100 and
    flat-@102 callables — exercises the multi-date machinery with a golden-free ordering invariant
    (lattice price is monotone non-decreasing in the call cap)."""
    c = curve_from_z(FLAT3)
    lat = ShortRateLattice(c, T=10, freq=2, sigma=0.25)
    cr = 0.06                                                  # premium coupon -> the call bites
    p_step = lat.price_bond(cr, 0.0, call_price=lat.call_array([(1.0, 102.0), (5.0, 100.0)]))
    p_hi = lat.price_bond(cr, 0.0, call_price=lat.call_array([(1.0, 102.0)]))
    p_lo = lat.price_bond(cr, 0.0, call_price=lat.call_array([(1.0, 100.0)]))
    assert p_lo <= p_step + 1e-9
    assert p_step <= p_hi + 1e-9
    assert p_lo < p_hi                                         # the schedule genuinely changes the price


def test_put_array_from_schedule():
    """put_array mirrors call_array: -inf inactive, floors at the put price on/after the put time."""
    c = curve_from_z(UP)
    lat = ShortRateLattice(c, T=6, freq=2, sigma=0.2)          # N = 12 steps
    arr = lat.put_array([(3.0, 100.0)])
    assert np.isneginf(arr[0]) and np.isneginf(arr[lat.N])
    for i in range(1, lat.N):
        assert arr[i] == (100.0 if lat.t[i] >= 3.0 - 1e-9 else -np.inf)
