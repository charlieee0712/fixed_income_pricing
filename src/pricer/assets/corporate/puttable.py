"""Puttable corporate bonds — thin wrappers over the shared embedded-option surface
(template: ``assets/corporate/puttable.py``; legacy ``BondOAS`` analysisType 3 price,
5 OAS, 6 duration).

Same outputs, same units and the same shared tree as ``callable.py``; the only
product-specific input is the **put schedule** — the holder's right to sell the bond
back to the issuer:

    put_schedule = [(date, price_per_100), ...]

The economics mirror the callable exactly, with the option in the other party's hands:
the holder's right can only ADD value, so a puttable bond is never worth less than the
straight bond, its duration is shorter than the straight bond's (the put floors the price
when rates rise), and higher volatility RAISES the price.

No URS holding currently routes here — the puttable surface is validated on the shared
core and on controlled fixtures. That is stated plainly rather than implied, and the
route exists so that a real puttable prices the day its terms arrive, with no new engine.
"""
from __future__ import annotations

from pricer.assets.corporate import embedded_option
from pricer.assets.corporate.embedded_option import (DEFAULT_VOL_SCENARIOS,  # noqa: F401
                                                     SIGMA_DEFAULT, VOL_POINT)


def calculated_price(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                     put_schedule, oas: float = 0.0, *,
                     volatility: float = SIGMA_DEFAULT) -> float:
    """CLEAN price of a puttable bond at a given spread.

    Inputs
    ------
    1. coupon         : float — annual coupon in PERCENT.
    2. cpn_freq       : int — payments per year (1, 2, 4, 12).
    3. maturity       : date — bond maturity.
    4. valuation_date : date — date of valuation.
    5. curve          : ZeroCurve — own-currency discount curve.
    6. put_schedule   : ``[(date, price_per_100), ...]`` — the holder's put rights.
    7. oas            : float — flat spread in BASIS POINTS.
    8. volatility     : float — short-rate volatility, DECIMAL (default 0.15).

    Returns: float — clean price per 100 face; never BELOW the straight-bond price.
    """
    return embedded_option.calculated_price(coupon, cpn_freq, maturity, valuation_date,
                                            curve, oas=oas, volatility=volatility,
                                            put_schedule=put_schedule)


def implied_oas(coupon: float, cpn_freq: int, maturity, valuation_date,
                market_price: float, curve, put_schedule, *,
                volatility: float = SIGMA_DEFAULT) -> float:
    """Option-adjusted spread calibrated to a clean market price.

    Inputs
    ------
    1-4. coupon / cpn_freq / maturity / valuation_date.
    5. market_price  : float — existing CLEAN price per 100.
    6. curve         : ZeroCurve.
    7. put_schedule  : the holder's put rights.
    8. volatility    : float — DECIMAL; the OAS is conditional on it.

    Returns: float — spread in BASIS POINTS repricing the bond to ``market_price``. The
    holder's option is worth something, so the residual credit spread is WIDER than a
    straight-bond spread on the same price.
    """
    return embedded_option.implied_oas(coupon, cpn_freq, maturity, valuation_date,
                                       market_price, curve, volatility=volatility,
                                       put_schedule=put_schedule)


def duration(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
             put_schedule, *, volatility: float = SIGMA_DEFAULT) -> float:
    """Option-adjusted effective duration in YEARS at the calibrated spread.

    Inputs: as :func:`implied_oas`, with ``oas`` (bp) in place of ``market_price``.
    Returns: float — shorter than the straight-bond duration: the put floors the price
    when rates rise, so the bond loses less than the straight bond.
    """
    return embedded_option.duration(coupon, cpn_freq, maturity, valuation_date, oas,
                                    curve, volatility=volatility,
                                    put_schedule=put_schedule)


def dv01(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
         put_schedule, *, volatility: float = SIGMA_DEFAULT) -> float:
    """Price change per +1 bp parallel shift (EXTENSION — no legacy counterpart).

    Inputs: identical to :func:`duration`. Returns: float per 100 face.
    """
    return embedded_option.dv01(coupon, cpn_freq, maturity, valuation_date, oas, curve,
                                volatility=volatility, put_schedule=put_schedule)


def convexity(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
              put_schedule, *, volatility: float = SIGMA_DEFAULT) -> float:
    """Effective convexity in YEARS^2 (EXTENSION — no legacy counterpart).

    Inputs: identical to :func:`duration`. Returns: float — the put ADDS convexity
    (the opposite sign contribution to a call's).
    """
    return embedded_option.convexity(coupon, cpn_freq, maturity, valuation_date, oas,
                                     curve, volatility=volatility,
                                     put_schedule=put_schedule)


def widening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
             put_schedule, bp_adjust: float = 10.0, *,
             volatility: float = SIGMA_DEFAULT) -> float:
    """Scenario clean price after the spread WIDENS by ``bp_adjust`` bp (default 10).

    Inputs: as :func:`duration`, plus ``bp_adjust`` in bp.
    Returns: float — clean price at ``oas + bp_adjust``; the put cushions the fall.
    """
    return embedded_option.widening(coupon, cpn_freq, maturity, valuation_date, oas,
                                    curve, bp_adjust=bp_adjust, volatility=volatility,
                                    put_schedule=put_schedule)


def tightening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
               put_schedule, bp_adjust: float = 10.0, *,
               volatility: float = SIGMA_DEFAULT) -> float:
    """Scenario clean price after the spread TIGHTENS by ``bp_adjust`` bp (positive size).

    Inputs: identical to :func:`widening`. Returns: clean price at ``oas - bp_adjust``.
    """
    return embedded_option.tightening(coupon, cpn_freq, maturity, valuation_date, oas,
                                      curve, bp_adjust=bp_adjust, volatility=volatility,
                                      put_schedule=put_schedule)


def price_at_volatility(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                        put_schedule, oas: float,
                        volatilities=DEFAULT_VOL_SCENARIOS) -> dict:
    """Price at a FIXED spread across volatility scenarios.

    Inputs
    ------
    1-6. coupon / cpn_freq / maturity / valuation_date / curve / put_schedule.
    7. oas          : float — the spread held FIXED, in bp.
    8. volatilities : iterable of DECIMAL scenarios (default 0.10 / 0.15 / 0.20).

    Returns: ``{volatility: clean_price}`` — RISING with volatility, the mirror image of
    the callable: the holder's option gains value.
    """
    return embedded_option.price_at_volatility(coupon, cpn_freq, maturity,
                                               valuation_date, curve, oas, volatilities,
                                               put_schedule=put_schedule)


def implied_oas_at_volatility(coupon: float, cpn_freq: int, maturity, valuation_date,
                              market_price: float, curve, put_schedule,
                              volatilities=DEFAULT_VOL_SCENARIOS) -> dict:
    """OAS at a FIXED market price across volatility scenarios.

    Inputs
    ------
    1-4. coupon / cpn_freq / maturity / valuation_date.
    5. market_price : float — the CLEAN price held FIXED.
    6-7. curve / put_schedule.
    8. volatilities : iterable of DECIMAL scenarios.

    Returns: ``{volatility: implied_oas_bp}`` — WIDENING as volatility rises: the holder's
    option is worth more, so a wider credit spread is needed to hold the price still.
    """
    return embedded_option.implied_oas_at_volatility(
        coupon, cpn_freq, maturity, valuation_date, market_price, curve, volatilities,
        put_schedule=put_schedule)


def volatility_sensitivity(coupon: float, cpn_freq: int, maturity, valuation_date,
                           market_price: float, curve, put_schedule, *,
                           baseline_volatility: float = SIGMA_DEFAULT,
                           bump: float = VOL_POINT) -> dict:
    """Both volatility slopes around the baseline, with their units named.

    Inputs: as :func:`implied_oas_at_volatility`, plus ``baseline_volatility`` and
    ``bump`` (DECIMAL; 0.01 = one volatility point).
    Returns: dict — baseline volatility and OAS, ``price_change_per_1_vol_point`` and
    ``oas_change_bp_per_1_vol_point``; both signs mirror the callable's.
    """
    return embedded_option.volatility_sensitivity(
        coupon, cpn_freq, maturity, valuation_date, market_price, curve,
        baseline_volatility=baseline_volatility, bump=bump, put_schedule=put_schedule)
