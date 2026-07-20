"""Fixed-then-float hybrid pricing — the two validated engines glued at the switch date.

Every fixed-to-float hybrid in the URS book was still in its FIXED leg at 2009-03-31 (ISIN lookup
2026-07-20, ``docs/isin_lookup_2026-07-20.md``; terms in ``data/hybrid_switch_terms.csv``). Such a
bond prices as:

* **fixed leg** (valuation -> switch): vanilla fixed cash flows under the exact
  :mod:`pricing.bond_price` conventions — ACT/364, backward ``round(364/fixed_freq)``-day grid
  anchored at the SWITCH date, coupon ``fixed_rate/fixed_freq * face``, accrued off this grid;
* **floating leg** (switch -> maturity): FRN cash flows under the exact :mod:`pricing.frn`
  conventions — grid anchored backward at MATURITY and truncated at the switch, each coupon =
  simple forward off the same ``ZeroCurve`` over the ACTUAL period + the bond's documented quoted
  margin, face at maturity; the first floating period starts AT the switch (its first reset);
* one curve + one flat implied OAS discount BOTH legs (``exp(-t*(z+shift+oas))``), calibrated to
  the custodian BT. Single-curve = the 2009 convention (OIS dual-curve = future enhancement).

Degenerate limits DELEGATE to the validated engines, so they agree bit-for-bit by construction:
``switch >= maturity`` -> :func:`pricing.bond_price.price_bond` (the curve bump enters as
``oas + curve_shift`` — for fixed cash flows a parallel curve shift and an OAS shift discount
identically); ``switch <= valuation`` -> :func:`pricing.frn.price_frn`.

The COMPOSITION itself is validated by the margin-0 identity (test_hybrid): with ``spread=0`` and
``oas=0`` the floating leg telescopes EXACTLY to ``face * DF(t_switch)`` on ANY curve
(sum of ``(DF(prev)/DF(t)-1)/tau * tau * DF(t)`` chain-cancels), so the hybrid equals a fixed
bullet MATURING AT THE SWITCH — which is also the price-to-call reference bond (par call at the
switch), computed by the driver as a secondary column (reset-6 dual-column convention; for a
deep-discount name the market prices EXTENSION, so the to-call OAS is spurious — reference only).

Effective duration bumps the CURVE (:mod:`pricing.frn` convention): the floating leg reprojects
its forwards, so the post-switch rate risk largely cancels and the hybrid's duration is dominated
by the fixed leg + the discounting of the floating leg's value back from the switch — i.e. roughly
bounded by the switch time, far below a same-maturity pure fixed bond. ``next_switch_t`` (years to
the switch) is returned on every result for per-bond verification.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from scipy.optimize import brentq

from pricing.bond_price import price_bond
from pricing.frn import YEAR_DAYS, _as_date, _df, price_frn, simple_forward


@dataclass
class HybridResult:
    clean: float
    dirty: float
    accrued: float
    next_switch_t: float         # years to the fixed->floating switch (0 if already floating)
    cashflows: list


def price_hybrid(valuation_date, maturity, curve, oas: float = 0.0, *, fixed_rate, switch_date,
                 spread: float = 0.0, fixed_freq: int = 2, float_freq: int | None = None,
                 face: float = 100.0, curve_shift: float = 0.0):
    """Clean/dirty price of a fixed-then-float hybrid (see module docstring).

    ``curve_shift`` parallel-shifts the curve for BOTH the forward projection and the discounting
    (the duration bump); ``oas`` shifts only the discounting. ``spread`` is the documented quoted
    margin of the floating leg (decimal).
    """
    val, mat, sw = _as_date(valuation_date), _as_date(maturity), _as_date(switch_date)
    if float_freq is None:
        float_freq = fixed_freq
    if val > mat:
        return HybridResult(0.0, 0.0, 0.0, 0.0, [])
    if sw >= mat:                        # never floats -> exactly the vanilla fixed engine
        r = price_bond(valuation_date, maturity, fixed_rate, curve, oas=oas + curve_shift,
                       face=face, freq=fixed_freq)
        return HybridResult(r.clean, r.dirty, r.accrued, (mat - val).days / YEAR_DAYS, r.cashflows)
    if sw <= val:                        # already floating -> exactly the FRN engine
        r = price_frn(valuation_date, maturity, curve, oas, current_coupon=None, spread=spread,
                      face=face, freq=float_freq, curve_shift=curve_shift)
        return HybridResult(r.clean, r.dirty, r.accrued, 0.0, r.cashflows)

    # ---- fixed leg: val -> switch. price_bond's grid/accrual anchored at the switch; NO face. ----
    step_f = max(1, round(YEAR_DAYS / fixed_freq))
    period_cpn = fixed_rate / fixed_freq * face
    dirty, cfs = 0.0, []
    d = sw
    while d >= val:
        t = (d - val).days / YEAR_DAYS
        df = _df(curve, t, curve_shift + oas)
        dirty += period_cpn * df
        cfs.append((d, t, fixed_rate, period_cpn, df, period_cpn * df))
        d = d - dt.timedelta(days=step_f)
    accrued = period_cpn * (val - d).days / step_f      # d = fixed coupon date just before valuation

    # ---- floating leg: switch -> maturity. frn grid anchored at maturity, truncated at the
    #      switch; the first floating period starts AT the switch (t_prev = t_switch), so the
    #      margin-0 telescoping to face*DF(t_switch) is exact. ----
    step_v = max(1, round(YEAR_DAYS / float_freq))
    dates, d = [], mat
    while d > sw:                       # payments strictly after the switch (the switch-date coupon
        dates.append(d)                 # is the fixed leg's last payment)
        d = d - dt.timedelta(days=step_v)
    dates.reverse()
    t_sw = (sw - val).days / YEAR_DAYS
    prev_t = t_sw
    for dd in dates:
        t = (dd - val).days / YEAR_DAYS
        tau = t - prev_t
        rate_cf = simple_forward(curve, prev_t, t, curve_shift) + spread
        amount = rate_cf * tau * face + (face if dd == mat else 0.0)
        df = _df(curve, t, curve_shift + oas)
        dirty += amount * df
        cfs.append((dd, t, rate_cf, amount, df, amount * df))
        prev_t = t

    return HybridResult(dirty - accrued, dirty, accrued, t_sw, cfs)


def implied_oas_hybrid(target_clean, valuation_date, maturity, curve, *, fixed_rate, switch_date,
                       spread: float = 0.0, fixed_freq: int = 2, float_freq: int | None = None,
                       face: float = 100.0, lo: float = -0.20, hi: float = 2.0,
                       xtol: float = 1e-10, max_expand: int = 40):
    """Solve the flat OAS s.t. the hybrid clean price == ``target_clean`` (the custodian BT).
    Price is strictly decreasing in the OAS -> bracketed Brent (same pattern as the FRN solver)."""
    def f(o):
        return price_hybrid(valuation_date, maturity, curve, oas=o, fixed_rate=fixed_rate,
                            switch_date=switch_date, spread=spread, fixed_freq=fixed_freq,
                            float_freq=float_freq, face=face).clean - target_clean

    flo, fhi, n = f(lo), f(hi), 0
    while flo < 0 and n < max_expand:
        lo -= 0.20; flo = f(lo); n += 1
    while fhi > 0 and n < max_expand:
        hi += 1.0; fhi = f(hi); n += 1
    if flo * fhi > 0:
        raise ValueError(f"cannot bracket hybrid OAS for target={target_clean}: "
                         f"f({lo:.3f})={flo:.4f}, f({hi:.3f})={fhi:.4f}")
    return brentq(f, lo, hi, xtol=xtol)


def hybrid_risk_metrics(valuation_date, maturity, curve, oas, *, fixed_rate, switch_date,
                        spread: float = 0.0, fixed_freq: int = 2, float_freq: int | None = None,
                        face: float = 100.0, bump: float = 1e-4) -> dict:
    """Effective duration / DV01 / convexity by a parallel **curve** bump (reprojects the floating
    leg AND rediscounts both legs) — the frn convention; ``oas`` held at its calibrated value."""
    def priced(shift):
        return price_hybrid(valuation_date, maturity, curve, oas=oas, fixed_rate=fixed_rate,
                            switch_date=switch_date, spread=spread, fixed_freq=fixed_freq,
                            float_freq=float_freq, face=face, curve_shift=shift)

    base = priced(0.0)
    p0 = base.dirty
    p_up = priced(bump).dirty
    p_dn = priced(-bump).dirty
    if p0 == 0:
        return {"dirty": p0, "clean": base.clean, "dv01": float("nan"),
                "eff_duration": float("nan"), "convexity": float("nan"),
                "next_switch_t": base.next_switch_t}
    return {
        "dirty": p0,
        "clean": base.clean,
        "dv01": (p_dn - p_up) / (2.0 * bump) * 1e-4,
        "eff_duration": (p_dn - p_up) / (2.0 * bump * p0),
        "convexity": (p_up + p_dn - 2.0 * p0) / (bump * bump * p0),
        "next_switch_t": base.next_switch_t,
    }
