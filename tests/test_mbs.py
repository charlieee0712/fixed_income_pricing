"""Static-CPR pool engine invariants (phase 2 skeleton; synthetic pools, never skipped).

The four contracted invariants: CPR=0 degenerates to a level annuity; principal is conserved at
any CPR; WAC-flat-curve + CPR=0 prices par exactly; duration falls monotonically in CPR. Plus the
Bloomberg 8-field interface (zero-change data plug-in) and the solve round-trips."""
import math

import pytest

from pricing.mbs import (
    PoolTerms,
    implied_cpr_pool,
    implied_spread_pool,
    pool_cash_flows,
    pool_risk_metrics,
    price_pool,
    select_cpr,
    smm_from_cpr,
)


class FlatCurve:
    def __init__(self, z):
        self.z = z

    def zero_rate(self, t, spread=0.0):
        return self.z + spread


# ---------- invariant 1: CPR=0 -> level-pay annuity, amortises to zero at WARM ----------
def test_cpr0_is_level_annuity():
    flows = pool_cash_flows(0.065, 240, 0.0)
    assert len(flows) == 240
    pays = [f.total for f in flows]
    assert max(pays) - min(pays) < 1e-9              # constant total payment
    assert abs(flows[-1].balance_end) < 1e-9         # fully amortised at WARM
    assert all(f.prepayment == 0.0 for f in flows)


# ---------- invariant 2: principal conservation at any CPR ----------
@pytest.mark.parametrize("cpr", [0.0, 0.06, 0.30, 1.0])
def test_principal_conservation(cpr):
    flows = pool_cash_flows(0.06, 360, cpr, balance=100.0)
    principal = sum(f.sched_principal + f.prepayment for f in flows)
    assert abs(principal - 100.0) < 1e-9
    if cpr == 1.0:
        assert len(flows) == 1                       # SMM=1 pays the pool off in month 1


def test_servicing_strip_conserves_principal():
    flows = pool_cash_flows(0.065, 240, 0.10, net_coupon=0.06)   # 50bp strip
    assert abs(sum(f.sched_principal + f.prepayment for f in flows) - 100.0) < 1e-9
    assert abs(flows[0].interest - 100.0 * 0.06 / 12) < 1e-12    # interest at the NET rate


# ---------- invariant 3: discount at the WAC (monthly-compounded), CPR=0 -> par exactly ----------
def test_par_at_wac_discount():
    wac = 0.065
    z = 12.0 * math.log(1.0 + wac / 12.0)            # continuous equivalent of monthly wac/12
    for cpr in (0.0, 0.25):                          # holds at ANY CPR: every flow is on-coupon
        p = price_pool(FlatCurve(z), wac, 360, cpr)
        assert abs(p - 100.0) < 1e-9


# ---------- invariant 4: duration strictly decreasing in CPR ----------
@pytest.mark.parametrize("z,label", [(0.04, "premium"), (0.08, "discount")])
def test_duration_monotone_in_cpr(z, label):
    c = FlatCurve(z)
    durs = [pool_risk_metrics(c, 0.06, 360, cpr, 0.0)["eff_duration"] for cpr in (0.0, 0.06, 0.30)]
    assert durs[0] > durs[1] > durs[2] > 0
    wals = [pool_risk_metrics(c, 0.06, 360, cpr, 0.0)["wal"] for cpr in (0.0, 0.06, 0.30)]
    assert wals[0] > wals[1] > wals[2] > 0


# ---------- the Bloomberg 8-field interface (data drops in with zero code change) ----------
def test_pool_terms_from_bloomberg():
    row = {"MTG_WACPN": 6.5, "MTG_WAM": 287.0, "MTG_STATED_WALA": 61.0, "MTG_AOLS": 145000.0,
           "MTG_GEN_CPR_3M": 12.0, "MTG_GEN_CPR_6M": 14.0, "MTG_GEN_CPR_12M": 16.0,
           "MTG_HIST_COLLAT_CPR_LIFE": 9.5}
    t = PoolTerms.from_bloomberg(row, net_coupon_pct=6.0)
    assert t.wac == pytest.approx(0.065)
    assert t.wam_months == 287
    assert t.cpr_12m == pytest.approx(0.16)
    assert t.net_coupon == pytest.approx(0.06)
    assert select_cpr(t, "auto") == pytest.approx(0.16)          # prefers 12m
    assert select_cpr(t, "3m") == pytest.approx(0.12)
    assert select_cpr(t, 0.08) == 0.08                            # numeric passthrough

    t2 = PoolTerms.from_bloomberg({"MTG_WACPN": 6.0, "MTG_WAM": 120, "MTG_GEN_CPR_3M": 7.0})
    assert select_cpr(t2, "auto") == pytest.approx(0.07)          # falls back 12m->6m->3m
    assert select_cpr(t2, "life") is None                         # absent -> None, never a guess
    with pytest.raises(ValueError):
        PoolTerms.from_bloomberg({"MTG_GEN_CPR_3M": 7.0})         # wac/wam required


# ---------- solve round-trips ----------
def test_spread_roundtrip():
    c = FlatCurve(0.05)
    p = price_pool(c, 0.065, 300, 0.12, spread=0.0135)
    got = implied_spread_pool(p, c, 0.065, 300, 0.12)
    assert abs(got - 0.0135) < 1e-8


def test_implied_cpr_roundtrip_premium_pool():
    c = FlatCurve(0.04)                              # wac 6.5 vs 4% curve -> premium, price falls in CPR
    p = price_pool(c, 0.065, 300, 0.18)
    got = implied_cpr_pool(p, c, 0.065, 300)
    assert abs(got - 0.18) < 1e-7


def test_smm_bounds():
    assert smm_from_cpr(0.0) == 0.0
    assert abs(smm_from_cpr(1.0) - 1.0) < 1e-12
    assert abs((1.0 - smm_from_cpr(0.06)) ** 12 - 0.94) < 1e-12
    with pytest.raises(ValueError):
        smm_from_cpr(1.5)
