"""Vanilla (bullet, fixed-coupon) corporate bonds — thin wrappers over the core
engines (template: ``assets/corporate/vanilla.py``).

One simple function per output, sharing one input set — the shape of the legacy
"Monthly" sheet's demo block, so each function maps 1:1 onto a legacy formula:

    calculated_price  <->  CorpBondwidening(..., 0, ccy) / bondcalc "Calculated Price"
    implied_oas       <->  CorpBondOAS       / bondcalc(analysisType=1)  "OAS"
    duration          <->  CorpBondDuration  / bondcalc(analysisType=2)  "Duration"
    widening          <->  CorpBondwidening(+bp) / bondcalc(4, ..., +10) "Widening"
    tightening        <->  CorpBondwidening(-bp) / bondcalc(4, ..., -10) "Tightening"
    dv01 / convexity  ->   extensions (no legacy counterpart existed)

Steepening / Flattening (bondcalc 5/6, a curve TWIST) need a non-parallel curve bump
— a core.market.curves capability scheduled for the rollout, not sampled here.

Units at this layer are the legacy sheet's: coupon in PERCENT, prices per 100,
spreads in BASIS POINTS (the input dictionary lives in ``bonds_input.py``). The core
engines underneath work in decimals. All functions are pure (no state, no globals):
every row of a portfolio can be priced independently and in parallel.
"""
from __future__ import annotations

from pricer.assets.corporate.bonds_input import validate_vanilla_inputs
from pricer.core.pricing.analytical import price_fixed_rate_bond
from pricer.core.risk.sensitivities import parallel_bump_metrics
from pricer.core.market.spreads import solve_spread_to_price

_BP = 1e-4  # one basis point, in decimal


def calculated_price(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                     oas: float = 0.0, face: float = 100.0,
                     coupon_schedule=None) -> float:
    """CLEAN price of a vanilla bond at a given spread.

    Inputs (see bonds_input.INPUT_CATALOGUE)
    ------
    1. coupon          : float — annual coupon in PERCENT (6.5 = 6.5%).
    2. cpn_freq        : int — payments per year (1, 2, 4, 12).
    3. maturity        : date — bond maturity.
    4. valuation_date  : date — date of valuation.
    5. curve           : ZeroCurve — discount curve (bond's own currency).
    6. oas             : float — flat spread in BASIS POINTS (default 0 = on-curve).
    7. face            : float — face value (default 100).
    8. coupon_schedule : optional dated coupon table (overrides `coupon`).

    Returns: float — clean price per ``face``.
    """
    validate_vanilla_inputs(coupon, cpn_freq)
    return price_fixed_rate_bond(valuation_date, maturity, coupon / 100.0, curve,
                                 oas=oas * _BP, face=face, freq=cpn_freq,
                                 coupon_schedule=coupon_schedule).clean


def implied_oas(coupon: float, cpn_freq: int, maturity, valuation_date,
                market_price: float, curve, face: float = 100.0,
                coupon_schedule=None) -> float:
    """Implied OAS calibrated to a market price (legacy ``CorpBondOAS``).

    Inputs
    ------
    1. coupon          : float — annual coupon in PERCENT.
    2. cpn_freq        : int — payments per year.
    3. maturity        : date — bond maturity.
    4. valuation_date  : date — date of valuation.
    5. market_price    : float — existing CLEAN price per ``face`` (custodian/Bloomberg).
    6. curve           : ZeroCurve — discount curve.
    7. face            : float — face value (default 100).
    8. coupon_schedule : optional dated coupon table.

    Returns: float — the flat spread in BASIS POINTS that reprices the bond to
    ``market_price`` (unique: price is strictly decreasing in the spread).
    """
    validate_vanilla_inputs(coupon, cpn_freq)

    def clean_at(spread: float) -> float:
        return price_fixed_rate_bond(valuation_date, maturity, coupon / 100.0, curve,
                                     oas=spread, face=face, freq=cpn_freq,
                                     coupon_schedule=coupon_schedule).clean

    return solve_spread_to_price(clean_at, market_price) * 1e4


def _metrics(coupon, cpn_freq, maturity, valuation_date, oas, curve, face,
             coupon_schedule) -> dict:
    """Shared bump-and-reprice metric set (duration / dv01 / convexity)."""
    def priced(shift: float):
        return price_fixed_rate_bond(valuation_date, maturity, coupon / 100.0, curve,
                                     oas=oas * _BP + shift, face=face, freq=cpn_freq,
                                     coupon_schedule=coupon_schedule)

    return parallel_bump_metrics(priced)


def duration(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float,
             curve, face: float = 100.0, coupon_schedule=None) -> float:
    """Effective duration in YEARS at the calibrated spread (legacy ``CorpBondDuration``).

    Inputs
    ------
    1. coupon          : float — annual coupon in PERCENT.
    2. cpn_freq        : int — payments per year.
    3. maturity        : date — bond maturity.
    4. valuation_date  : date — date of valuation.
    5. oas             : float — the bond's implied OAS in BASIS POINTS.
    6. curve           : ZeroCurve — discount curve.
    7. face            : float — face value (default 100).
    8. coupon_schedule : optional dated coupon table.

    Returns: float — effective (parallel-curve-shift) duration, dirty-price base.
    """
    validate_vanilla_inputs(coupon, cpn_freq)
    return _metrics(coupon, cpn_freq, maturity, valuation_date, oas, curve, face,
                    coupon_schedule)["eff_duration"]


def dv01(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float,
         curve, face: float = 100.0, coupon_schedule=None) -> float:
    """Price change per +1 bp parallel shift (EXTENSION — no legacy counterpart).

    Inputs: identical to :func:`duration`.
    Returns: float — price drop per ``face`` for a +1 bp shift; multiply by
    par / ``face`` for a position's dollar DV01.
    """
    validate_vanilla_inputs(coupon, cpn_freq)
    return _metrics(coupon, cpn_freq, maturity, valuation_date, oas, curve, face,
                    coupon_schedule)["dv01"]


def convexity(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float,
              curve, face: float = 100.0, coupon_schedule=None) -> float:
    """Effective convexity in YEARS^2 (EXTENSION — no legacy counterpart).

    Inputs: identical to :func:`duration`.
    Returns: float — (P+ + P- - 2·P0) / (bump² · P0), dirty-price base.
    """
    validate_vanilla_inputs(coupon, cpn_freq)
    return _metrics(coupon, cpn_freq, maturity, valuation_date, oas, curve, face,
                    coupon_schedule)["convexity"]


def widening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float,
             curve, bp_adjust: float = 10.0, face: float = 100.0,
             coupon_schedule=None) -> float:
    """Scenario price after the spread WIDENS by ``bp_adjust`` bp
    (legacy ``CorpBondwidening`` / bondcalc analysisType 4 with +bp).

    Inputs
    ------
    1-6. as :func:`duration` (`oas` = the bond's calibrated spread in bp).
    7. bp_adjust       : float — spread move in bp (default +10).
    8. face            : float — face value (default 100).
    9. coupon_schedule : optional dated coupon table.

    Returns: float — clean price at ``oas + bp_adjust`` (widening -> lower price).
    """
    return calculated_price(coupon, cpn_freq, maturity, valuation_date, curve,
                            oas=oas + bp_adjust, face=face,
                            coupon_schedule=coupon_schedule)


def tightening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float,
               curve, bp_adjust: float = 10.0, face: float = 100.0,
               coupon_schedule=None) -> float:
    """Scenario price after the spread TIGHTENS by ``bp_adjust`` bp
    (legacy Tightening column = ``CorpBondwidening`` with -bp).

    Inputs: identical to :func:`widening`; ``bp_adjust`` is the tightening SIZE (positive).
    Returns: float — clean price at ``oas - bp_adjust`` (tightening -> higher price).
    """
    return widening(coupon, cpn_freq, maturity, valuation_date, oas, curve,
                    bp_adjust=-bp_adjust, face=face, coupon_schedule=coupon_schedule)
