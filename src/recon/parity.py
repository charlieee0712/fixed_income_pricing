"""
parity.py — legacy-parity pricing mode for the Monthly-sheet reconciliation.

Replicates `BondCalc`'s vanilla chain (`CorpBondOAS` / `CorpBondDuration` /
`CorpBondwidening`; `extracted/project_vba.txt` l.2349–2978, dispatch
l.3331–3810) on the `zeroyield4` replica tables:

  * cash flows on a MONTH-COUNT grid — `maximo = Δyears·12 + Δmonths`, coupons
    every 12/freq months from the valuation month, day-of-month ignored,
    face paid at the LAST coupon index (maturity truncated down to the step);
  * NO accrued interest — PV is compared to the sheet's raw input price;
  * maturities capped at 30y (corporate path only; Government Bonds skip it);
  * curve table chosen by the bond's own coupon frequency;
  * discounting exp(−(z + OAS/1e4)·t), z the replica's continuous zero.

These are reconciliation instruments replicating the legacy's conventions —
NOT production methodology.  Never import from production pricing code.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

CAP_DAYS = 30 * 365            # BondCalc l.3560–3562: valuation + 30·365 days


def month_count(valuation: date, maturity: date, apply_cap: bool = True) -> int:
    """
    The legacy month grid length (Corp* l.2398–2402).

    Inputs
    ------
    1. valuation : valuation date (sheet col O)
    2. maturity  : maturity date (sheet col G)
    3. apply_cap : 30-year cap first (BondCalc l.3560; the Government-Bonds
                   dispatch at l.3389–3405 never reaches it -> False there)

    Returns (Y2−Y1)·12 + (M2−M1); day-of-month is discarded, exactly as legacy.
    """
    if apply_cap and (maturity - valuation).days / 365.0 > 30.0:
        maturity = valuation + timedelta(days=CAP_DAYS)
    return (maturity.year - valuation.year) * 12 + (maturity.month - valuation.month)


def parity_pv(table, freq: int, coupon_pct: float, months: int, oas_bp: float):
    """
    PV per 100 face on the legacy month grid (CorpBondOAS fixed branch,
    l.2490–2502).

    Inputs
    ------
    1. table      : (z, df) dicts from monthly_curve.zeroyield4_tables()[freq]
    2. freq       : coupon frequency (1/2/4/12) — also selected the table
    3. coupon_pct : annual coupon in percent (sheet col C)
    4. months     : month_count() result
    5. oas_bp     : spread in basis points added to the continuous zero

    Returns the PV, or None when the grid is empty (months < one coupon
    period — the legacy output is undefined/garbage there).
    """
    z, _ = table
    salti = 12 // freq
    last = (months // salti) * salti
    if last < salti:
        return None
    s = oas_bp / 10000.0
    acc = 0.0
    dfl = 0.0
    for m in range(salti, last + 1, salti):
        dfl = math.exp(-(z[m] + s) * (m / 12.0))
        acc += dfl
    return acc * coupon_pct / freq + 100.0 * dfl


def implied_oas(table, freq: int, coupon_pct: float, months: int, price: float):
    """
    Solve parity_pv == price for the OAS in bp — the exact root of the
    equation the legacy solved with Veloz (tolerance |PV/price−1| < 1e-4,
    ~0.001bp granularity; search started at +1bp, capped at 1000bp).

    Returns the OAS in bp, or None if undefined/unbracketable.
    """
    if price is None or price <= 0.0:
        return None
    lo, hi = -30000.0, 30000.0
    plo = parity_pv(table, freq, coupon_pct, months, lo)
    phi = parity_pv(table, freq, coupon_pct, months, hi)
    if plo is None:
        return None
    if not (plo - price > 0.0 > phi - price):
        return None
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        pm = parity_pv(table, freq, coupon_pct, months, mid)
        if pm - price > 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def duration_legacy(table, freq: int, coupon_pct: float, months: int, oas_bp: float):
    """
    Effective duration exactly as CorpBondDuration's fixed branch
    (l.2740–2783): −(PV(oas+10bp) − PV(oas−10bp)) / (20/100) / PV(oas) · 100.
    The sheet evaluates it at OASadjustment = the row's own cached OAS (col P).
    """
    p0 = parity_pv(table, freq, coupon_pct, months, oas_bp)
    pp = parity_pv(table, freq, coupon_pct, months, oas_bp + 10.0)
    pm = parity_pv(table, freq, coupon_pct, months, oas_bp - 10.0)
    if not p0:
        return None
    return -((pp - pm) / (20.0 / 100.0) / p0) * 100.0


def buggy_pv(table, freq: int, coupon_pct: float, months: int, oas_bp: float):
    """
    Deliberate BondPrice-style convention MISMATCH (checksum only, Gate-2
    verdict 2): re-express each continuous zero as a semiannual rate and
    discount it with the continuous formula.  Must fit the golden STRICTLY
    WORSE than parity_pv — dynamic confirmation of the Gate-0 static finding
    that `bondcalc` does not carry the `BondPrice` bug.
    """
    z, _ = table
    salti = 12 // freq
    last = (months // salti) * salti
    if last < salti:
        return None
    s = oas_bp / 10000.0
    acc = 0.0
    dfl = 0.0
    for m in range(salti, last + 1, salti):
        z_semi = 2.0 * (math.exp(z[m] / 2.0) - 1.0)
        dfl = math.exp(-(z_semi + s) * (m / 12.0))
        acc += dfl
    return acc * coupon_pct / freq + 100.0 * dfl
