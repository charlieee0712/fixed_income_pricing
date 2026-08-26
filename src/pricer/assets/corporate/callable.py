"""Callable corporate bonds — thin wrappers over the shared embedded-option surface
(template: ``assets/corporate/callable.py``; legacy ``BondOAS`` analysisType 2 price,
5 OAS, 6 duration).

One simple function per requested output, sharing one input set, exactly as the legacy
"Monthly" dictionary lays them out. The only product-specific input is the **call
schedule** — the issuer's right to retire the bond early:

    call_schedule = [(date, price_per_100), ...]

Every function delegates to ``embedded_option``, which prices on the ONE shared tree in
``core.pricing.tree``. Nothing here does arithmetic. Units are the legacy sheet's:
coupon in PERCENT, prices per 100, spreads in BASIS POINTS, volatility in DECIMAL.

(The module name shadows the ``callable()`` builtin only if imported bare; import the
module — ``from pricer.assets.corporate import callable as callable_bond`` — or use the
package path, as the tests do.)
"""
from __future__ import annotations

from pricer.assets.corporate import embedded_option
from pricer.assets.corporate.embedded_option import (DEFAULT_VOL_SCENARIOS,  # noqa: F401
                                                     SIGMA_DEFAULT, VOL_POINT)


def calculated_price(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                     call_schedule, oas: float = 0.0, *,
                     volatility: float = SIGMA_DEFAULT) -> float:
    """CLEAN price of a callable bond at a given spread.

    Inputs
    ------
    1. coupon         : float — annual coupon in PERCENT.
    2. cpn_freq       : int — payments per year (1, 2, 4, 12).
    3. maturity       : date — bond maturity.
    4. valuation_date : date — date of valuation.
    5. curve          : ZeroCurve — own-currency discount curve.
    6. call_schedule  : ``[(date, price_per_100), ...]`` — the issuer's call rights.
    7. oas            : float — flat spread in BASIS POINTS.
    8. volatility     : float — short-rate volatility, DECIMAL (default 0.15).

    Returns: float — clean price per 100 face; never above the straight-bond price,
    because the issuer's option can only take value away from the holder.
    """
    return embedded_option.calculated_price(coupon, cpn_freq, maturity, valuation_date,
                                            curve, oas=oas, volatility=volatility,
                                            call_schedule=call_schedule)


def implied_oas(coupon: float, cpn_freq: int, maturity, valuation_date,
                market_price: float, curve, call_schedule, *,
                volatility: float = SIGMA_DEFAULT) -> float:
    """Option-adjusted spread calibrated to a clean market price.

    Inputs
    ------
    1-4. coupon / cpn_freq / maturity / valuation_date, as above.
    5. market_price   : float — existing CLEAN price per 100 (custodian or Bloomberg).
    6. curve          : ZeroCurve.
    7. call_schedule  : the issuer's call rights.
    8. volatility     : float — DECIMAL; the OAS is conditional on it (see
       :func:`implied_oas_at_volatility`).

    Returns: float — the spread in BASIS POINTS that reprices the bond to
    ``market_price``. "Option-adjusted" is literal here: the call's value is inside the
    model, so what is left is the credit spread.
    """
    return embedded_option.implied_oas(coupon, cpn_freq, maturity, valuation_date,
                                       market_price, curve, volatility=volatility,
                                       call_schedule=call_schedule)


def duration(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
             call_schedule, *, volatility: float = SIGMA_DEFAULT) -> float:
    """Option-adjusted effective duration in YEARS at the calibrated spread.

    Inputs: as :func:`implied_oas`, with ``oas`` (bp) in place of ``market_price``.
    Returns: float — shorter than the same bond's straight duration, because the call
    truncates the price rally when rates fall.
    """
    return embedded_option.duration(coupon, cpn_freq, maturity, valuation_date, oas,
                                    curve, volatility=volatility,
                                    call_schedule=call_schedule)


def dv01(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
         call_schedule, *, volatility: float = SIGMA_DEFAULT) -> float:
    """Price change per +1 bp parallel shift (EXTENSION — no legacy counterpart).

    Inputs: identical to :func:`duration`.
    Returns: float — per 100 face; scale by par / 100 for a position's dollar DV01.
    """
    return embedded_option.dv01(coupon, cpn_freq, maturity, valuation_date, oas, curve,
                                volatility=volatility, call_schedule=call_schedule)


def convexity(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
              call_schedule, *, volatility: float = SIGMA_DEFAULT) -> float:
    """Effective convexity in YEARS^2 (EXTENSION — no legacy counterpart).

    Inputs: identical to :func:`duration`.
    Returns: float — frequently NEGATIVE for a callable trading near its call price;
    that is the correct signature of the issuer's option, not an error.
    """
    return embedded_option.convexity(coupon, cpn_freq, maturity, valuation_date, oas,
                                     curve, volatility=volatility,
                                     call_schedule=call_schedule)


def widening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
             call_schedule, bp_adjust: float = 10.0, *,
             volatility: float = SIGMA_DEFAULT) -> float:
    """Scenario clean price after the spread WIDENS by ``bp_adjust`` bp (default 10).

    Inputs: as :func:`duration`, plus ``bp_adjust`` — the spread move in bp.
    Returns: float — clean price at ``oas + bp_adjust`` (widening lowers the price).
    """
    return embedded_option.widening(coupon, cpn_freq, maturity, valuation_date, oas,
                                    curve, bp_adjust=bp_adjust, volatility=volatility,
                                    call_schedule=call_schedule)


def tightening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
               call_schedule, bp_adjust: float = 10.0, *,
               volatility: float = SIGMA_DEFAULT) -> float:
    """Scenario clean price after the spread TIGHTENS by ``bp_adjust`` bp (positive size).

    Inputs: identical to :func:`widening`.
    Returns: float — clean price at ``oas - bp_adjust``; the call caps how much the price
    can rise, which is exactly what the tree captures.
    """
    return embedded_option.tightening(coupon, cpn_freq, maturity, valuation_date, oas,
                                      curve, bp_adjust=bp_adjust, volatility=volatility,
                                      call_schedule=call_schedule)


def price_at_volatility(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                        call_schedule, oas: float,
                        volatilities=DEFAULT_VOL_SCENARIOS) -> dict:
    """Price at a FIXED spread across volatility scenarios (Mario's question, part 1).

    Inputs
    ------
    1-6. coupon / cpn_freq / maturity / valuation_date / curve / call_schedule.
    7. oas          : float — the spread held FIXED, in bp.
    8. volatilities : iterable of DECIMAL scenarios (default 0.10 / 0.15 / 0.20).

    Returns: ``{volatility: clean_price}`` — falling with volatility for a call-active
    bond, because the issuer's option is worth more.
    """
    return embedded_option.price_at_volatility(coupon, cpn_freq, maturity,
                                               valuation_date, curve, oas, volatilities,
                                               call_schedule=call_schedule)


def implied_oas_at_volatility(coupon: float, cpn_freq: int, maturity, valuation_date,
                              market_price: float, curve, call_schedule,
                              volatilities=DEFAULT_VOL_SCENARIOS) -> dict:
    """OAS at a FIXED market price across volatility scenarios (Mario's question, part 2).

    Inputs
    ------
    1-4. coupon / cpn_freq / maturity / valuation_date.
    5. market_price : float — the CLEAN price held FIXED.
    6-7. curve / call_schedule.
    8. volatilities : iterable of DECIMAL scenarios.

    Returns: ``{volatility: implied_oas_bp}`` — tightening as volatility rises, because
    more of the same discount is explained as the cost of the call.
    """
    return embedded_option.implied_oas_at_volatility(
        coupon, cpn_freq, maturity, valuation_date, market_price, curve, volatilities,
        call_schedule=call_schedule)


def volatility_sensitivity(coupon: float, cpn_freq: int, maturity, valuation_date,
                           market_price: float, curve, call_schedule, *,
                           baseline_volatility: float = SIGMA_DEFAULT,
                           bump: float = VOL_POINT) -> dict:
    """Both volatility slopes around the baseline, with their units named.

    Inputs
    ------
    1-7. as :func:`implied_oas_at_volatility`.
    8. baseline_volatility : float — DECIMAL centre (default 0.15).
    9. bump                : float — DECIMAL half-step (0.01 = one volatility point).

    Returns: dict — baseline volatility and OAS, ``price_change_per_1_vol_point`` (per
    100 face) and ``oas_change_bp_per_1_vol_point`` (bp).
    """
    return embedded_option.volatility_sensitivity(
        coupon, cpn_freq, maturity, valuation_date, market_price, curve,
        baseline_volatility=baseline_volatility, bump=bump,
        call_schedule=call_schedule)
