"""Clean/dirty price-convention invariance across every calibrated engine (Liping code review,
2026-08-04).

The principle being locked: a model PV of all future cash flows is the DIRTY price; the custodian
``BT`` is CLEAN (the file carries its own separate Accrued-income columns); accrued interest is
date-only — independent of the curve, the OAS and any embedded option — so the two calibration
forms

    solve OAS s.t. model dirty(OAS) == BT + AI          (dirty form)
    solve OAS s.t. model clean(OAS) == BT               (clean form — what the code does)

must return the SAME root, engine by engine. And the AI itself must come from ONE formula —
``pricing.bond_price.accrued_interest`` (legacy ACT/364, 182-day grid) — never re-derived per
engine. Each invariance test therefore solves the dirty form INDEPENDENTLY (a raw brentq on the
engine's dirty output plus the *shared* accrued, not the engine's own) and pins
``|oas_clean - oas_dirty| < 1e-10``. An engine that starts calibrating a dirty PV against the
clean BT, or grows a private accrued formula, fails here mechanically.

Also locked (made exact by the 2026-08-04 lattice fix — real ACT/364 coupon times on the tree):
a straight bond on the lattice reprices ``price_bond`` dirty at any sigma/OAS, so the lattice and
vanilla calibrators agree on the OAS itself for an option-free bond.

Hermetic: synthetic ZeroCurve built in-process, no client data.
"""
import datetime as dtm

import numpy as np
import pandas as pd
import pytest
from scipy.optimize import brentq

from curves.zero_curve import ZeroCurve
from pricing.bond_price import accrued_interest, coupon_dates, lattice_inputs, price_bond
from pricing.calibrate import implied_oas
from pricing.frn import implied_oas_frn, price_frn
from pricing.hybrid import implied_oas_hybrid, price_hybrid
from pricing.ilb import implied_spread_ilb, price_ilb
from pricing.lattice import ShortRateLattice

FREQ = "Semiannual"
VAL = "2009-03-31"
MAT = "2017-11-20"          # NOT coupon-aligned with VAL -> a genuine stub + nonzero accrued
CPN = 0.0625
XTOL = 1e-12                # both solvers; roots of the SAME monotone equation then agree << 1e-10
TOL = 1e-10                 # the invariance tolerance (Liping review)


def curve_from_z(zfun, freq=FREQ, tmax=31):
    months = np.arange(0, int(tmax * 12) + 1) / 12.0
    z = np.array([zfun(t) for t in months])
    grid = pd.DataFrame({"Maturity": months, f"{freq}_Rate": z * 100.0, f"{freq}_DF": np.exp(-z * months)})
    return ZeroCurve(grid, freq=freq)


FLAT3 = lambda t: 0.03
UP = lambda t: 0.02 + 0.003 * t


def _dirty_root(dirty_fn, target_dirty):
    """Independent dirty-form calibration: root of dirty(oas) == target_dirty."""
    return brentq(lambda o: dirty_fn(o) - target_dirty, -0.20, 2.0, xtol=XTOL)


# ---- the single accrued formula ----
def test_accrued_single_source_flat():
    c = curve_from_z(FLAT3)
    r = price_bond(VAL, MAT, CPN, c, oas=0.011)
    ai = accrued_interest(VAL, MAT, CPN)
    assert ai > 0.5                                    # a real, meaty accrued (stub chosen for it)
    assert r.accrued == ai                             # price_bond consumes THE shared formula
    assert r.clean == pytest.approx(r.dirty - ai, abs=1e-12)


def test_accrued_single_source_schedule():
    sched = [(None, 0.05), (dtm.date(2013, 6, 1), 0.07)]
    c = curve_from_z(UP)
    r = price_bond(VAL, MAT, 0.0, c, oas=0.02, coupon_schedule=sched)
    ai = accrued_interest(VAL, MAT, 0.0, coupon_schedule=sched)
    first_cpn_date = coupon_dates(VAL, MAT, 2)[0][0]
    assert first_cpn_date < dtm.date(2013, 6, 1)       # accruing period rate is the PRE-step 5%
    assert ai == pytest.approx(0.05 / 2 * 100 * r.accrued_days / 182, rel=1e-12)
    assert r.accrued == ai


def test_zero_coupon_accrued_zero_clean_equals_dirty():
    c = curve_from_z(UP)
    assert accrued_interest(VAL, MAT, 0.0) == 0.0
    r = price_bond(VAL, MAT, 0.0, c, oas=0.0123)
    assert r.clean == r.dirty                          # the STRIPS/zero route is trivially consistent


# ---- clean-form vs dirty-form calibration roots, engine by engine ----
def test_vanilla_clean_dirty_invariance():
    c = curve_from_z(UP)
    target = price_bond(VAL, MAT, CPN, c, oas=0.0234).clean
    ai = accrued_interest(VAL, MAT, CPN)
    oas_clean = implied_oas(target, VAL, MAT, CPN, c, xtol=XTOL)
    oas_dirty = _dirty_root(lambda o: price_bond(VAL, MAT, CPN, c, oas=o).dirty, target + ai)
    assert abs(oas_clean - oas_dirty) < TOL
    assert oas_clean == pytest.approx(0.0234, abs=1e-9)


def test_vanilla_schedule_clean_dirty_invariance():
    sched = [(None, 0.05), (dtm.date(2013, 6, 1), 0.07)]
    c = curve_from_z(FLAT3)
    target = price_bond(VAL, MAT, 0.0, c, oas=0.0177, coupon_schedule=sched).clean
    ai = accrued_interest(VAL, MAT, 0.0, coupon_schedule=sched)
    oas_clean = implied_oas(target, VAL, MAT, 0.0, c, coupon_schedule=sched, xtol=XTOL)
    oas_dirty = _dirty_root(
        lambda o: price_bond(VAL, MAT, 0.0, c, oas=o, coupon_schedule=sched).dirty, target + ai)
    assert abs(oas_clean - oas_dirty) < TOL


def test_frn_accrued_is_the_shared_formula():
    c = curve_from_z(UP)
    cur = 0.042                                        # the fixed-at-last-reset current coupon
    r = price_frn(VAL, MAT, c, oas=0.015, current_coupon=cur)
    assert r.accrued == pytest.approx(accrued_interest(VAL, MAT, cur), rel=1e-12)


def test_frn_clean_dirty_invariance():
    c = curve_from_z(UP)
    cur = 0.042
    target = price_frn(VAL, MAT, c, oas=0.0288, current_coupon=cur).clean
    ai = accrued_interest(VAL, MAT, cur)
    oas_clean = implied_oas_frn(target, VAL, MAT, c, current_coupon=cur, xtol=XTOL)
    oas_dirty = _dirty_root(
        lambda o: price_frn(VAL, MAT, c, oas=o, current_coupon=cur).dirty, target + ai)
    assert abs(oas_clean - oas_dirty) < TOL


def test_hybrid_accrued_is_the_shared_formula():
    c = curve_from_z(FLAT3)
    sw, fx = "2013-05-10", 0.058                       # fixed-leg grid (and accrual) anchor at the SWITCH
    r = price_hybrid(VAL, MAT, c, oas=0.02, fixed_rate=fx, switch_date=sw, spread=0.02)
    assert r.accrued == pytest.approx(accrued_interest(VAL, sw, fx), rel=1e-12)


def test_hybrid_clean_dirty_invariance():
    c = curve_from_z(UP)
    sw, fx, sp = "2013-05-10", 0.058, 0.021
    kw = dict(fixed_rate=fx, switch_date=sw, spread=sp)
    target = price_hybrid(VAL, MAT, c, oas=0.0311, **kw).clean
    ai = accrued_interest(VAL, sw, fx)
    oas_clean = implied_oas_hybrid(target, VAL, MAT, c, xtol=XTOL, **kw)
    oas_dirty = _dirty_root(lambda o: price_hybrid(VAL, MAT, c, oas=o, **kw).dirty, target + ai)
    assert abs(oas_clean - oas_dirty) < TOL


def test_ilb_accrued_ratio_treatment():
    """TIPS accrued = REAL accrued x index ratio at VAL — the same shared formula scaled by
    ratio_0, matching the inflation-adjusted clean BT (BT == BU/par*100)."""
    c = curve_from_z(FLAT3)
    rc, ratio0 = 0.02, 1.18
    r = price_ilb(VAL, MAT, rc, c, 0.005, index_ratio=ratio0, inflation=0.015)
    assert r.accrued == pytest.approx(accrued_interest(VAL, MAT, rc) * ratio0, rel=1e-12)


def test_ilb_clean_dirty_invariance():
    c = curve_from_z(UP)
    rc, ratio0 = 0.02, 1.18
    kw = dict(index_ratio=ratio0, inflation=0.0)
    target = price_ilb(VAL, MAT, rc, c, -0.009, **kw).clean      # negative spread = the ILB norm
    ai = accrued_interest(VAL, MAT, rc) * ratio0
    s_clean = implied_spread_ilb(target, VAL, MAT, rc, c, xtol=XTOL, **kw)
    s_dirty = _dirty_root(lambda s: price_ilb(VAL, MAT, rc, c, s, **kw).dirty, target + ai)
    assert abs(s_clean - s_dirty) < TOL


# ---- the lattice on real coupon times: dirty root PV, shared accrued, vanilla-exact straight ----
def test_lattice_straight_reprices_price_bond():
    c = curve_from_z(UP)
    times, ai = lattice_inputs(VAL, MAT, CPN)
    dates, _, _ = coupon_dates(VAL, MAT, 2)
    assert len(times) == len(dates)                    # no coupon dropped/invented by the grid
    assert ai == pytest.approx(accrued_interest(VAL, MAT, CPN), abs=1e-15)
    for sigma in (0.0, 0.15, 0.30):
        lat = ShortRateLattice(c, freq=2, sigma=sigma, coupon_times=times)
        for oas in (0.0, 0.0345):
            pb = price_bond(VAL, MAT, CPN, c, oas=oas)
            assert lat.price_bond(CPN, oas) == pytest.approx(pb.dirty, abs=1e-6)
            assert lat.price_bond(CPN, oas) - ai == pytest.approx(pb.clean, abs=1e-6)


def test_lattice_clean_dirty_invariance_with_call():
    c = curve_from_z(FLAT3)
    times, ai = lattice_inputs(VAL, MAT, CPN)
    lat = ShortRateLattice(c, freq=2, sigma=0.20, coupon_times=times)
    carr = lat.call_array([(3.0, 100.0)])
    target = lat.price_bond(CPN, 0.028, call_price=carr) - ai    # clean target with a known root
    oas_clean = lat.implied_oas(target, CPN, call_price=carr, accrued=ai, xtol=XTOL)
    oas_dirty = _dirty_root(lambda o: lat.price_bond(CPN, o, call_price=carr), target + ai)
    assert abs(oas_clean - oas_dirty) < TOL
    assert oas_clean == pytest.approx(0.028, abs=1e-9)


def test_lattice_straight_oas_matches_vanilla_calibrator():
    """Same clean target -> the lattice (no options) and the vanilla calibrator agree on the OAS:
    the two engines share one calibration equation, not merely one philosophy."""
    c = curve_from_z(UP)
    times, ai = lattice_inputs(VAL, MAT, CPN)
    lat = ShortRateLattice(c, freq=2, sigma=0.15, coupon_times=times)
    target = price_bond(VAL, MAT, CPN, c, oas=0.0187).clean
    oas_lat = lat.implied_oas(target, CPN, accrued=ai, xtol=XTOL)
    oas_van = implied_oas(target, VAL, MAT, CPN, c, xtol=XTOL)
    assert abs(oas_lat - oas_van) < 1e-8


def test_lattice_valuation_on_coupon_date_corner():
    """VAL exactly on a grid coupon date: price_bond books that coupon in dirty and nets it out
    with a full period of accrued; lattice_inputs folds it into the returned accrued (which then
    nets to zero) — the clean identity must survive the corner."""
    c = curve_from_z(FLAT3)
    mat2 = (pd.Timestamp(VAL) + pd.Timedelta(days=182 * 14)).date()
    dates, _, _ = coupon_dates(VAL, mat2, 2)
    assert dates[0] == pd.Timestamp(VAL).date()        # the corner is real
    times, ai_eff = lattice_inputs(VAL, mat2, CPN)
    assert len(times) == len(dates) - 1                # the t=0 coupon is not a tree node
    assert ai_eff == pytest.approx(0.0, abs=1e-15)     # full-period accrued minus the t=0 coupon
    lat = ShortRateLattice(c, freq=2, sigma=0.15, coupon_times=times)
    pb = price_bond(VAL, mat2, CPN, c, oas=0.01)
    assert lat.price_bond(CPN, 0.01) - ai_eff == pytest.approx(pb.clean, abs=1e-6)


def test_lattice_risk_metrics_reports_clean_dirty():
    c = curve_from_z(UP)
    times, ai = lattice_inputs(VAL, MAT, CPN)
    lat = ShortRateLattice(c, freq=2, sigma=0.15, coupon_times=times)
    rm = lat.risk_metrics(CPN, 0.02, accrued=ai)
    assert rm["dirty"] - rm["clean"] == pytest.approx(ai, abs=1e-12)
    assert rm["price"] == rm["dirty"]                  # duration divides by the DIRTY base (pricing.risk)
    assert rm["eff_duration"] > 0
