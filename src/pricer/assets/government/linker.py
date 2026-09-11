"""Inflation-linked government bonds (linkers / TIPS / JGBi) — thin wrappers over
``core.pricing.inflation`` (template: ``assets/government/linker.py``).

Serves the master's **Index Linked Government Bonds** sub-category: 16 rows -> 15 securities,
14 of them priced here. One simple function per output, sharing one input set, as the legacy
"Monthly" dictionary lays them out. Nothing here does arithmetic.

**What is different about a linker's INPUTS** — the most useful thing to know when reading
this next to ``corporate/vanilla.py``:

* the coupon is a **REAL** coupon (input 1). The cash the bond actually pays is that coupon
  multiplied by an index ratio which grows with prices, so the two are never the same number
  and never share a field name.
* two inputs describe the index path instead of a coupon schedule: ``index_ratio`` (11), the
  inflation already accrued when we value the bond, and ``inflation_pct`` (12), the assumption
  about inflation from here on.
* the curve (7) is the ordinary **nominal** government curve. This project has no real-yield
  curves, so the index path is modelled explicitly rather than being read off a curve — a
  documented v1 method, not an approximation nobody noticed.

⚠️ **The calibrated spread is not a credit spread, and its name says so.** For a nominal bond
the number returned by a calibration is compensation for the risk the borrower does not pay.
For a linker priced this way it is something else entirely: with the cash flows projected at
zero inflation and the price taken from the market, the spread has to absorb exactly the
inflation the projection left out. So it comes out **negative**, and it is approximately
**minus the market's breakeven inflation rate**. That is the engine being right, not a sign
error. The function is therefore called :func:`implied_spread_vs_nominal_bp` and never
``implied_oas``; :func:`breakeven_bp` turns it the right way up for a reader.

Units at this layer are the legacy sheet's: prices per 100, spreads in BASIS POINTS, coupons
and inflation in PERCENT. The core engine underneath works in decimals. All functions are
pure — one bond per call, no shared state.
"""
from __future__ import annotations

import math

from pricer.assets.government.bonds_input import validate_linker_inputs
from pricer.core.pricing import inflation as _core

_BP = 1e-4  # one basis point, in decimal


def calculated_price(real_coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                     spread_vs_nominal_bp: float = 0.0, face: float = 100.0, *,
                     index_ratio: float = 1.0, inflation_pct: float = 0.0) -> float:
    """CLEAN price of an inflation-linked bond at a given spread.

    Inputs (see bonds_input.INPUT_CATALOGUE)
    ------
    1. real_coupon          : float — REAL annual coupon in PERCENT.
    2. cpn_freq             : int — coupon payments per year (1, 2, 4, 12).
    3. maturity             : date — bond maturity.
    4. valuation_date       : date — date of valuation.
    5. curve                : ZeroCurve — the NOMINAL own-currency curve.
    6. spread_vs_nominal_bp : float — flat spread over that curve, in BASIS POINTS. May be
       negative, and for a real linker at ``inflation_pct = 0`` it normally is.
    7. face                 : float — ORIGINAL unindexed face (default 100).
    8. index_ratio          : float — the inflation already accrued at valuation.
    9. inflation_pct        : float — assumed annual inflation from here, PERCENT.

    Returns: float — clean price per ``face``, on the same inflation-adjusted basis the
    custodian quotes, so it compares directly with the custodian mark.
    """
    validate_linker_inputs(real_coupon, cpn_freq, index_ratio, inflation_pct)
    return _core.price_ilb(valuation_date, maturity, real_coupon / 100.0, curve,
                           spread_vs_nominal_bp * _BP, index_ratio=index_ratio,
                           inflation=inflation_pct / 100.0, face=face, freq=cpn_freq).clean


def accrued_interest(real_coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                     face: float = 100.0, *, index_ratio: float = 1.0,
                     inflation_pct: float = 0.0) -> float:
    """Accrued interest of the current coupon period.

    Inputs: as :func:`calculated_price` without the spread — accrued depends on dates, the
    real coupon and the index ratio, never on the discount spread.

    Returns: float — accrued per ``face``; dirty price = clean + this.

    ⚠️ The accrued is scaled by the ratio **at the valuation date** (t = 0), not by the ratio
    at the end of the period: the inflation compensation a seller has earned is the inflation
    that has actually happened.
    """
    validate_linker_inputs(real_coupon, cpn_freq, index_ratio, inflation_pct)
    return _core.price_ilb(valuation_date, maturity, real_coupon / 100.0, curve, 0.0,
                           index_ratio=index_ratio, inflation=inflation_pct / 100.0,
                           face=face, freq=cpn_freq).accrued


def implied_spread_vs_nominal_bp(real_coupon: float, cpn_freq: int, maturity, valuation_date,
                                 market_price: float, curve, face: float = 100.0, *,
                                 index_ratio: float = 1.0,
                                 inflation_pct: float = 0.0) -> float:
    """Flat spread over the NOMINAL curve that reprices the bond to a market price.

    Inputs
    ------
    1-4. real_coupon / cpn_freq / maturity / valuation_date, as above.
    5. market_price  : float — existing CLEAN price per ``face``. For a linker the custodian
       quotes this on the inflation-ADJUSTED basis, which is the basis the model prices on,
       so no restatement is needed.
    6. curve         : ZeroCurve — the NOMINAL own-currency curve.
    7. face          : float — ORIGINAL unindexed face (default 100).
    8. index_ratio   : float — inflation accrued at valuation.
    9. inflation_pct : float — assumed annual inflation, PERCENT.

    Returns: float — the spread in BASIS POINTS. The price is strictly decreasing in the
    spread, so the root is unique.

    ⚠️ **This is not a credit spread and must never be reported in a column of them.** At
    ``inflation_pct = 0`` it is approximately minus the market's breakeven inflation rate: the
    projection leaves inflation out, so the spread absorbs it. A negative result is the
    expected result. Use :func:`breakeven_bp` when the intended reading is "what inflation is
    the market pricing", which for this book is almost always the interesting question.
    """
    validate_linker_inputs(real_coupon, cpn_freq, index_ratio, inflation_pct)
    return _core.implied_spread_ilb(market_price, valuation_date, maturity,
                                    real_coupon / 100.0, curve, index_ratio=index_ratio,
                                    inflation=inflation_pct / 100.0, face=face,
                                    freq=cpn_freq) * 1e4


def breakeven_bp(real_coupon: float, cpn_freq: int, maturity, valuation_date,
                 market_price: float, curve, face: float = 100.0, *,
                 index_ratio: float = 1.0, inflation_pct: float = 0.0) -> float:
    """The inflation rate the market is pricing into this bond, in BASIS POINTS.

    Inputs: identical to :func:`implied_spread_vs_nominal_bp`.

    Returns: float — the breakeven inflation rate in bp. A POSITIVE number means the market
    expects prices to rise; a negative one means it expects them to fall.

    How it relates to the spread. Pricing with inflation ``pi`` at spread ``s`` is exactly the
    same as pricing with no inflation at spread ``s - ln(1+pi)`` — an identity of the
    exponential discounting, unit-tested in ``tests/test_ilb.py``. So whatever inflation was
    assumed, the market-implied rate is::

        breakeven = ln(1 + inflation) - spread

    and at the production assumption of zero inflation this is simply ``-spread``, which is
    the form ``scripts/phase2_risk.py`` emits. This function is the general statement and
    agrees with the driver exactly at that assumption (asserted in the structure tests).
    """
    spread = implied_spread_vs_nominal_bp(real_coupon, cpn_freq, maturity, valuation_date,
                                          market_price, curve, face,
                                          index_ratio=index_ratio, inflation_pct=inflation_pct)
    return math.log1p(inflation_pct / 100.0) * 1e4 - spread


def _metrics(real_coupon, cpn_freq, maturity, valuation_date, spread_vs_nominal_bp, curve,
             face, index_ratio, inflation_pct) -> dict:
    """Shared metric set (duration / dv01 / convexity) from one spread bump."""
    validate_linker_inputs(real_coupon, cpn_freq, index_ratio, inflation_pct)
    return _core.ilb_risk_metrics(valuation_date, maturity, real_coupon / 100.0, curve,
                                  spread_vs_nominal_bp * _BP, index_ratio=index_ratio,
                                  inflation=inflation_pct / 100.0, face=face, freq=cpn_freq)


def duration(real_coupon: float, cpn_freq: int, maturity, valuation_date,
             spread_vs_nominal_bp: float, curve, face: float = 100.0, *,
             index_ratio: float = 1.0, inflation_pct: float = 0.0) -> float:
    """Effective duration in YEARS, on the dirty-price base.

    Inputs
    ------
    1-4. real_coupon / cpn_freq / maturity / valuation_date, as above.
    5. spread_vs_nominal_bp : float — the bond's calibrated spread in bp.
    6. curve                : ZeroCurve.
    7. face / 8. index_ratio / 9. inflation_pct — as above.

    Returns: float — effective duration in years.

    ⚠️ **This is a REAL-rate duration.** The index path here is static, so the cash flows do
    not move when the curve moves and the measured sensitivity is the full PV-weighted one.
    A real linker's *nominal* duration is shorter, because rates and inflation tend to move
    together and the indexation offsets part of the rate move. Modelling that needs an
    inflation-volatility model — a documented v2 item, not a defect in this number.
    """
    return _metrics(real_coupon, cpn_freq, maturity, valuation_date, spread_vs_nominal_bp,
                    curve, face, index_ratio, inflation_pct)["eff_duration"]


def dv01(real_coupon: float, cpn_freq: int, maturity, valuation_date,
         spread_vs_nominal_bp: float, curve, face: float = 100.0, *,
         index_ratio: float = 1.0, inflation_pct: float = 0.0) -> float:
    """Price change per 1 bp of spread, per ``face``.

    Inputs: as :func:`duration`.
    Returns: float — DV01 in price units (positive: the price falls as the spread rises).
    """
    return _metrics(real_coupon, cpn_freq, maturity, valuation_date, spread_vs_nominal_bp,
                    curve, face, index_ratio, inflation_pct)["dv01"]


def convexity(real_coupon: float, cpn_freq: int, maturity, valuation_date,
              spread_vs_nominal_bp: float, curve, face: float = 100.0, *,
              index_ratio: float = 1.0, inflation_pct: float = 0.0) -> float:
    """Convexity — the curvature of the price/spread relationship.

    Inputs: as :func:`duration`.
    Returns: float — convexity on the dirty-price base.
    """
    return _metrics(real_coupon, cpn_freq, maturity, valuation_date, spread_vs_nominal_bp,
                    curve, face, index_ratio, inflation_pct)["convexity"]


def widening(real_coupon: float, cpn_freq: int, maturity, valuation_date,
             spread_vs_nominal_bp: float, curve, bp_adjust: float = 10.0,
             face: float = 100.0, *, index_ratio: float = 1.0,
             inflation_pct: float = 0.0) -> float:
    """Scenario price after the spread WIDENS by ``bp_adjust`` bp.

    Inputs: as :func:`duration`, plus ``bp_adjust`` (float, bp, default +10).
    Returns: float — clean price per ``face`` at the wider spread.
    """
    return calculated_price(real_coupon, cpn_freq, maturity, valuation_date, curve,
                            spread_vs_nominal_bp + bp_adjust, face,
                            index_ratio=index_ratio, inflation_pct=inflation_pct)


def tightening(real_coupon: float, cpn_freq: int, maturity, valuation_date,
               spread_vs_nominal_bp: float, curve, bp_adjust: float = 10.0,
               face: float = 100.0, *, index_ratio: float = 1.0,
               inflation_pct: float = 0.0) -> float:
    """Scenario price after the spread TIGHTENS by ``bp_adjust`` bp.

    Inputs: as :func:`widening`.
    Returns: float — clean price per ``face`` at the tighter spread.
    """
    return calculated_price(real_coupon, cpn_freq, maturity, valuation_date, curve,
                            spread_vs_nominal_bp - bp_adjust, face,
                            index_ratio=index_ratio, inflation_pct=inflation_pct)
