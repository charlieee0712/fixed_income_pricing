"""Static-CPR pass-through pool engine — the Govt-MBS skeleton (phase 2, built ahead of data).

The URS ``Govt MTGE`` tab's analytics block (WAC/WARM/WALA/AOLS/CPR, cols DV-EC) is dead cached
``#NAME?`` Bloomberg formulas (0/888) — Mario is pulling the 8 surviving field mnemonics for the
882 unique CUSIPs. This module is built NOW against exactly that interface so the data drops in
with ZERO code change: :meth:`PoolTerms.from_bloomberg` consumes a ``{mnemonic: value}`` mapping
in Bloomberg's native units (percent), everything internal is decimal.

Model (v1, static): a fixed-rate level-pay pool amortising over ``wam_months`` at ``wac``, with
prepayment at a constant CPR (annualised, converted to the monthly SMM). Investor receives
interest at ``net_coupon`` (the pass-through rate, tab BE; defaults to ``wac`` when not given —
the servicing strip is then zero), scheduled principal and prepayments:

    g = wac/12;  SMM = 1 - (1-CPR)^(1/12)
    level payment on balance B with n months left:  A = B*g / (1 - (1+g)^-n)
    scheduled principal = A - B*g;   prepayment = (B - sched) * SMM;   interest = B*net/12

Pricing: month-grid flows ``t_k = k/12`` discounted ``exp(-t*(z(t)+spread))`` off the nominal
:class:`curves.zero_curve.ZeroCurve` — per 100 CURRENT face (the tab's BS golden quote basis).
The valuation date anchors the grid (no intra-month accrued / payment-delay conventions yet —
those land with the real data). Static CPR means the cash flows do NOT respond to rates, so the
risk metrics are spread-durations of fixed flows; the CPR(rate) response (negative convexity) is
the v2 prepayment model. One price cannot identify CPR and OAS together — with data either take
CPR from the Bloomberg fields and imply the spread, or fix the spread (~0 for GNMA) and use
:func:`implied_cpr_pool` (the inventory's fallback discussion).

Invariants (``tests/test_mbs.py``): CPR=0 degenerates to a level annuity that amortises to zero
at WARM; principal is conserved (sum of principal flows == opening balance) for any CPR; pricing
at a flat curve equal to the WAC (monthly-compounded) with CPR=0 gives par exactly; duration is
strictly decreasing in CPR.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from scipy.optimize import brentq

MONTHS_PER_YEAR = 12

# Bloomberg mnemonic -> PoolTerms field (+ percent -> decimal). EXACTLY the 8-field x 882-CUSIP
# request drafted for Mario (docs/phase2_inventory_2026-07-20.md); keys are matched as returned.
BLOOMBERG_FIELDS = {
    "MTG_WACPN": ("wac", 0.01),
    "MTG_WAM": ("wam_months", 1.0),
    "MTG_STATED_WALA": ("wala_months", 1.0),
    "MTG_AOLS": ("aols", 1.0),
    "MTG_GEN_CPR_3M": ("cpr_3m", 0.01),
    "MTG_GEN_CPR_6M": ("cpr_6m", 0.01),
    "MTG_GEN_CPR_12M": ("cpr_12m", 0.01),
    "MTG_HIST_COLLAT_CPR_LIFE": ("cpr_life", 0.01),
}


@dataclass
class PoolTerms:
    """One pool's static terms — decimals/months internally, Bloomberg units at the boundary."""
    wac: float                            # gross weighted-average coupon (decimal)
    wam_months: int                       # weighted-average remaining maturity (months)
    wala_months: Optional[float] = None   # weighted-average loan age (months)
    aols: Optional[float] = None          # average original loan size ($)
    cpr_3m: Optional[float] = None        # trailing CPRs (decimal)
    cpr_6m: Optional[float] = None
    cpr_12m: Optional[float] = None
    cpr_life: Optional[float] = None
    net_coupon: Optional[float] = None    # pass-through rate (tab BE, decimal); None -> wac

    @classmethod
    def from_bloomberg(cls, values: dict, *, net_coupon_pct=None):
        """Build from a ``{mnemonic: value}`` row of the 8-field request (percent units in, as
        Bloomberg returns them). Missing/None optional fields stay None; ``MTG_WACPN`` and
        ``MTG_WAM`` are required. ``net_coupon_pct`` = the tab's BE Income rate (percent)."""
        kw = {}
        for mnemonic, (field, scale) in BLOOMBERG_FIELDS.items():
            v = values.get(mnemonic)
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                kw[field] = float(v) * scale if scale != 1.0 else float(v)
        missing = [m for m, (f, _) in BLOOMBERG_FIELDS.items() if f in ("wac", "wam_months") and f not in kw]
        if missing:
            raise ValueError(f"required Bloomberg field(s) missing/blank: {missing}")
        kw["wam_months"] = int(round(kw["wam_months"]))
        if net_coupon_pct is not None:
            kw["net_coupon"] = float(net_coupon_pct) / 100.0
        return cls(**kw)


def select_cpr(terms: PoolTerms, policy="auto"):
    """The CPR to price with: a numeric ``policy`` passes through; ``"3m"/"6m"/"12m"/"life"``
    select that field; ``"auto"`` prefers 12m -> 6m -> 3m -> life (the least-noisy trailing
    window first). Returns ``None`` when the requested/available field is absent — the caller
    decides (None principle), never a silent default."""
    if isinstance(policy, (int, float)):
        return float(policy)
    order = {"3m": ["cpr_3m"], "6m": ["cpr_6m"], "12m": ["cpr_12m"], "life": ["cpr_life"],
             "auto": ["cpr_12m", "cpr_6m", "cpr_3m", "cpr_life"]}
    if policy not in order:
        raise ValueError(f"unknown CPR policy {policy!r}")
    for f in order[policy]:
        v = getattr(terms, f)
        if v is not None:
            return float(v)
    return None


def smm_from_cpr(cpr: float) -> float:
    """Monthly prepayment rate: ``SMM = 1 - (1-CPR)^(1/12)``."""
    if not 0.0 <= cpr <= 1.0:
        raise ValueError(f"CPR must be in [0, 1]; got {cpr}")
    return 1.0 - (1.0 - cpr) ** (1.0 / MONTHS_PER_YEAR)


@dataclass
class PoolFlow:
    month: int
    t: float                  # years = month/12
    balance_start: float
    interest: float           # at the net (pass-through) coupon
    sched_principal: float
    prepayment: float
    total: float
    balance_end: float


def pool_cash_flows(wac, wam_months, cpr, *, net_coupon=None, balance: float = 100.0):
    """Monthly investor cash flows of the static pool (list of :class:`PoolFlow`).

    Scheduled amortisation is the level-pay annuity recomputed on the surviving balance each
    month (the standard treatment: prepayments re-amortise the pool over its REMAINING term);
    prepayment applies the SMM to the post-scheduled balance; interest accrues at ``net_coupon``
    (default ``wac``). Stops early when the balance is exhausted (CPR=1 pays off in month 1)."""
    net = wac if net_coupon is None else net_coupon
    g = wac / MONTHS_PER_YEAR
    s = smm_from_cpr(cpr)
    n = int(wam_months)
    if n <= 0 or balance <= 0:
        return []
    B, out = float(balance), []
    for m in range(1, n + 1):
        rem = n - m + 1
        if g > 0:
            pay = B * g / (1.0 - (1.0 + g) ** (-rem))
            sched = min(pay - B * g, B)
        else:
            sched = B / rem
        prepay = (B - sched) * s
        interest = B * net / MONTHS_PER_YEAR
        end = B - sched - prepay
        out.append(PoolFlow(m, m / MONTHS_PER_YEAR, B, interest, sched, prepay,
                            interest + sched + prepay, end))
        B = end
        if B <= 1e-12:
            break
    return out


def price_pool(curve, wac, wam_months, cpr, spread: float = 0.0, *,
               net_coupon=None, face: float = 100.0) -> float:
    """PV per ``face`` current face: month-grid flows discounted ``exp(-t*(z(t)+spread))``."""
    flows = pool_cash_flows(wac, wam_months, cpr, net_coupon=net_coupon, balance=face)
    return sum(f.total * math.exp(-f.t * (float(curve.zero_rate(f.t)) + spread)) for f in flows)


def _solve_decreasing(f, lo, hi, xtol=1e-10, max_expand=40, what="root"):
    flo, fhi, n = f(lo), f(hi), 0
    while flo < 0 and n < max_expand:
        lo -= 0.20; flo = f(lo); n += 1
    while fhi > 0 and n < max_expand:
        hi += 1.0; fhi = f(hi); n += 1
    if flo * fhi > 0:
        raise ValueError(f"cannot bracket {what}: f({lo:.3f})={flo:.4f}, f({hi:.3f})={fhi:.4f}")
    return brentq(f, lo, hi, xtol=xtol)


def implied_spread_pool(target_price, curve, wac, wam_months, cpr, *,
                        net_coupon=None, face: float = 100.0,
                        lo: float = -0.20, hi: float = 2.0) -> float:
    """Flat spread s.t. ``price_pool == target_price`` (e.g. the tab BS golden), CPR given."""
    return _solve_decreasing(
        lambda s: price_pool(curve, wac, wam_months, cpr, s, net_coupon=net_coupon, face=face) - target_price,
        lo, hi, what=f"pool spread for target={target_price}")


def implied_cpr_pool(target_price, curve, wac, wam_months, *, spread: float = 0.0,
                     net_coupon=None, face: float = 100.0, xtol: float = 1e-10) -> float:
    """Constant CPR s.t. ``price_pool == target_price`` at a FIXED spread (the one-unknown
    fallback: defensible with spread ~ 0 for GNMA). Price is monotone in CPR away from par
    (premium pools cheapen as CPR rises, discounts richen); raises when the target is not
    bracketed on [0, 0.99] — e.g. a par-priced pool, where CPR is unidentifiable."""
    def f(c):
        return price_pool(curve, wac, wam_months, c, spread, net_coupon=net_coupon, face=face) - target_price

    f0, f99 = f(0.0), f(0.99)
    if f0 == 0.0:
        return 0.0
    if f0 * f99 > 0:
        raise ValueError(f"CPR not bracketed on [0,0.99]: f(0)={f0:.4f}, f(0.99)={f99:.4f} "
                         "(par-priced pool, or target outside the attainable range)")
    return brentq(f, 0.0, 0.99, xtol=xtol)


def pool_risk_metrics(curve, wac, wam_months, cpr, spread, *,
                      net_coupon=None, face: float = 100.0, bump: float = 1e-4) -> dict:
    """Duration / DV01 / convexity by a central spread bump (static flows -> spread-duration;
    the CPR(rate) response is the v2 prepayment model). Adds the WAL (years) of the flows."""
    def priced(s):
        return price_pool(curve, wac, wam_months, cpr, s, net_coupon=net_coupon, face=face)

    p0 = priced(spread)
    p_up, p_dn = priced(spread + bump), priced(spread - bump)
    flows = pool_cash_flows(wac, wam_months, cpr, net_coupon=net_coupon, balance=face)
    prin = sum(f.sched_principal + f.prepayment for f in flows)
    wal = sum((f.sched_principal + f.prepayment) * f.t for f in flows) / prin if prin > 0 else float("nan")
    if p0 == 0:
        return {"price": p0, "dv01": float("nan"), "eff_duration": float("nan"),
                "convexity": float("nan"), "wal": wal}
    return {
        "price": p0,
        "dv01": (p_dn - p_up) / (2.0 * bump) * 1e-4,
        "eff_duration": (p_dn - p_up) / (2.0 * bump * p0),
        "convexity": (p_up + p_dn - 2.0 * p0) / (bump * bump * p0),
        "wal": wal,
    }
