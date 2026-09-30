"""Puttable corporate bonds — thin wrappers over the shared embedded-option surface
(template: ``assets/corporate/puttable.py``; legacy ``BondOAS`` analysisType 3 price,
5 OAS, 6 duration).

**What is different here, and it is the only thing:** the option is the HOLDER'S, not the
issuer's. Same tree, same units, same outputs as ``callable.py``; the product-specific
input is the put schedule, ``[(date, price_per_100), ...]``.

Everything follows from whose right it is. The holder's option can only ADD value, so a
puttable is never worth less than the straight bond, its duration is SHORTER (the put
floors the price when rates rise), and higher volatility RAISES the price — each of those
the mirror of the callable.

No URS holding routes here. The surface is validated on the shared core and on controlled
fixtures, stated plainly rather than implied, so that a real puttable prices the day its
terms arrive with no new engine.

Shared inputs, once
-------------------
Every function below takes these in this order; only the differences are noted per
function. Authoritative dictionary: ``bonds_input.INPUT_CATALOGUE`` (Mario's reference
sheet keeps its input dictionary in its own block too, rows 61-98, separate from the
per-metric functions in rows 47-60).

1. coupon         : float — annual coupon in PERCENT.
2. cpn_freq       : int — payments per year (1, 2, 4, 12).
3. maturity       : date — bond maturity.
4. valuation_date : date — date of valuation.
5. curve          : ZeroCurve — own-currency discount curve.
6. put_schedule   : ``[(date, price_per_100), ...]`` — the holder's put rights.
   oas            : float — flat spread in BASIS POINTS (calibrated, or supplied).
   market_price   : float — existing CLEAN price per 100, where a function calibrates.
   volatility     : float — short-rate volatility, DECIMAL (default 0.15). Every
                    option-adjusted number here is conditional on it.
   bp_adjust      : float — scenario size in bp, positive in both directions.
"""
from __future__ import annotations

from pricer.assets.corporate import embedded_option
from pricer.assets.corporate.embedded_option import (DEFAULT_VOL_SCENARIOS,  # noqa: F401
                                                     SIGMA_DEFAULT, VOL_POINT)


def calculated_price(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                     put_schedule, oas: float = 0.0, *,
                     volatility: float = SIGMA_DEFAULT) -> float:
    """CLEAN price of a puttable bond at a given spread.

    Returns: clean price per 100 face; never BELOW the straight-bond price.
    """
    return embedded_option.calculated_price(coupon, cpn_freq, maturity, valuation_date,
                                            curve, oas=oas, volatility=volatility,
                                            put_schedule=put_schedule)


def implied_oas(coupon: float, cpn_freq: int, maturity, valuation_date,
                market_price: float, curve, put_schedule, *,
                volatility: float = SIGMA_DEFAULT) -> float:
    """Option-adjusted spread calibrated to a clean market price.

    Returns: spread in BASIS POINTS repricing the bond to ``market_price``. The holder's
    option is worth something, so the residual credit spread is WIDER than a
    straight-bond spread on the same price.
    """
    return embedded_option.implied_oas(coupon, cpn_freq, maturity, valuation_date,
                                       market_price, curve, volatility=volatility,
                                       put_schedule=put_schedule)


def duration(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
             put_schedule, *, volatility: float = SIGMA_DEFAULT) -> float:
    """Option-adjusted effective duration in YEARS at the calibrated spread.

    Returns: SHORTER than the straight-bond duration — the put floors the price when
    rates rise, so the bond loses less than the straight bond.
    """
    return embedded_option.duration(coupon, cpn_freq, maturity, valuation_date, oas,
                                    curve, volatility=volatility,
                                    put_schedule=put_schedule)


def dv01(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
         put_schedule, *, volatility: float = SIGMA_DEFAULT) -> float:
    """Price change per +1 bp parallel shift (EXTENSION — no legacy counterpart).

    Returns: float per 100 face.
    """
    return embedded_option.dv01(coupon, cpn_freq, maturity, valuation_date, oas, curve,
                                volatility=volatility, put_schedule=put_schedule)


def convexity(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
              put_schedule, *, volatility: float = SIGMA_DEFAULT) -> float:
    """Effective convexity in YEARS^2 (EXTENSION — no legacy counterpart).

    Returns: the put ADDS convexity — the opposite sign contribution to a call's.
    """
    return embedded_option.convexity(coupon, cpn_freq, maturity, valuation_date, oas,
                                     curve, volatility=volatility,
                                     put_schedule=put_schedule)


def widening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
             put_schedule, bp_adjust: float = 10.0, *,
             volatility: float = SIGMA_DEFAULT) -> float:
    """Scenario clean price after the spread WIDENS by ``bp_adjust`` bp (default 10).

    Returns: clean price at ``oas + bp_adjust``; the put cushions the fall.
    """
    return embedded_option.widening(coupon, cpn_freq, maturity, valuation_date, oas,
                                    curve, bp_adjust=bp_adjust, volatility=volatility,
                                    put_schedule=put_schedule)


def tightening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
               put_schedule, bp_adjust: float = 10.0, *,
               volatility: float = SIGMA_DEFAULT) -> float:
    """Scenario clean price after the spread TIGHTENS by ``bp_adjust`` bp (positive size).

    Returns: clean price at ``oas - bp_adjust``.
    """
    return embedded_option.tightening(coupon, cpn_freq, maturity, valuation_date, oas,
                                      curve, bp_adjust=bp_adjust, volatility=volatility,
                                      put_schedule=put_schedule)


def price_at_volatility(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                        put_schedule, oas: float,
                        volatilities=DEFAULT_VOL_SCENARIOS) -> dict:
    """Price at a FIXED spread across volatility scenarios.

    Differs: ``volatilities`` — iterable of DECIMAL scenarios (default 0.10/0.15/0.20) —
    replaces the single ``volatility``.

    Returns: ``{volatility: clean_price}``, RISING with volatility. The mirror image of
    the callable: the holder's option gains value.
    """
    return embedded_option.price_at_volatility(coupon, cpn_freq, maturity,
                                               valuation_date, curve, oas, volatilities,
                                               put_schedule=put_schedule)


def implied_oas_at_volatility(coupon: float, cpn_freq: int, maturity, valuation_date,
                              market_price: float, curve, put_schedule,
                              volatilities=DEFAULT_VOL_SCENARIOS) -> dict:
    """OAS at a FIXED market price across volatility scenarios.

    Differs: ``volatilities`` replaces the single ``volatility``; ``market_price`` is
    held fixed and the spread is solved.

    Returns: ``{volatility: implied_oas_bp}``, WIDENING as volatility rises — the
    holder's option is worth more, so a wider credit spread is needed to hold the price
    still.
    """
    return embedded_option.implied_oas_at_volatility(
        coupon, cpn_freq, maturity, valuation_date, market_price, curve, volatilities,
        put_schedule=put_schedule)


def volatility_sensitivity(coupon: float, cpn_freq: int, maturity, valuation_date,
                           market_price: float, curve, put_schedule, *,
                           baseline_volatility: float = SIGMA_DEFAULT,
                           bump: float = VOL_POINT) -> dict:
    """Both volatility slopes around the baseline, with their units named.

    Differs: ``baseline_volatility`` and ``bump`` (DECIMAL; 0.01 = one volatility point)
    replace the single ``volatility``.

    Returns: dict — the baseline volatility and OAS, ``price_change_per_1_vol_point`` and
    ``oas_change_bp_per_1_vol_point``. Both signs mirror the callable's.
    """
    return embedded_option.volatility_sensitivity(
        coupon, cpn_freq, maturity, valuation_date, market_price, curve,
        baseline_volatility=baseline_volatility, bump=bump, put_schedule=put_schedule)
