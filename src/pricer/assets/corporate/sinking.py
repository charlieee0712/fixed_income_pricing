"""Sinking-fund corporate bonds — thin wrappers over the shared embedded-option surface
(template: ``assets/corporate/sinking.py``; legacy ``BondOAS`` analysisType 4 price,
5 OAS, 6 duration).

The product modelled here is **issuer optional redemption**: on scheduled dates the issuer
may retire a fraction of the amount still outstanding at a contractual price. It is priced
on the SAME tree as callable and puttable bonds — a sinking right is an issuer option, so
it belongs beside the call, not in a separate engine.

    sinking_schedule = [(date, fraction, price_per_100), ...]
    fraction_basis   = "outstanding"

Two boundaries, both deliberate and both stated rather than assumed:

* **This is not amortisation.** A pass-through or amortising bond repays principal on a
  known factor schedule — deterministic cash flows, no option, a cash-flow engine problem.
  Routing one of those through this module would price a certainty as an option. The URS
  ``Sinking = Yes`` field does not distinguish the two, so no holding is routed here on the
  strength of that flag; the 13 securities waiting on schedules stay data-gated.
* **The fraction is of the amount OUTSTANDING**, never of original face. That is what keeps
  the value per unit outstanding independent of what was retired earlier, which is what a
  recombining tree can represent (the reasoning is in ``core.pricing.tree``). An
  original-face schedule is refused with a message pointing at the strip decomposition that
  would be needed, rather than silently priced as something else.

Validated on synthetic schedules in this round: no current URS security has documented
sinking terms, and that is reported as-is.
"""
from __future__ import annotations

from pricer.assets.corporate import embedded_option
from pricer.assets.corporate.embedded_option import (DEFAULT_VOL_SCENARIOS,  # noqa: F401
                                                     OUTSTANDING, SIGMA_DEFAULT,
                                                     SINKING_MODE, VOL_POINT)


def describe_mode() -> dict:
    """The diagnostic every sinking result should carry.

    Inputs: none.
    Returns: dict — ``sinking_mode`` (always ``issuer_optional_redemption``) and the
    ``fraction_basis`` this engine implements, so a downstream reader never has to guess
    which of the two sinking-fund products produced a number.
    """
    return {"sinking_mode": SINKING_MODE, "fraction_basis": OUTSTANDING}


def calculated_price(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                     sinking_schedule, oas: float = 0.0, *,
                     fraction_basis: str = OUTSTANDING,
                     volatility: float = SIGMA_DEFAULT) -> float:
    """CLEAN price of a sinking-fund bond at a given spread.

    Inputs
    ------
    1. coupon           : float — annual coupon in PERCENT.
    2. cpn_freq         : int — payments per year (1, 2, 4, 12).
    3. maturity         : date — bond maturity.
    4. valuation_date   : date — date of valuation.
    5. curve            : ZeroCurve — own-currency discount curve.
    6. sinking_schedule : ``[(date, fraction, price_per_100), ...]`` — the issuer's
       optional redemptions; ``fraction`` in (0, 1] of the amount outstanding.
    7. oas              : float — flat spread in BASIS POINTS.
    8. fraction_basis   : str — ``"outstanding"``; anything else is refused.
    9. volatility       : float — short-rate volatility, DECIMAL (default 0.15).

    Returns: float — clean price per 100 face; never above the straight-bond price,
    because the redemption right belongs to the issuer.
    """
    return embedded_option.calculated_price(
        coupon, cpn_freq, maturity, valuation_date, curve, oas=oas,
        volatility=volatility, sinking_schedule=sinking_schedule,
        fraction_basis=fraction_basis)


def implied_oas(coupon: float, cpn_freq: int, maturity, valuation_date,
                market_price: float, curve, sinking_schedule, *,
                fraction_basis: str = OUTSTANDING,
                volatility: float = SIGMA_DEFAULT) -> float:
    """Option-adjusted spread calibrated to a clean market price.

    Inputs
    ------
    1-4. coupon / cpn_freq / maturity / valuation_date.
    5. market_price     : float — existing CLEAN price per 100.
    6. curve            : ZeroCurve.
    7. sinking_schedule : the issuer's optional redemptions.
    8-9. fraction_basis / volatility.

    Returns: float — spread in BASIS POINTS repricing the bond to ``market_price``, with
    the redemption option's value inside the model rather than inside the spread.
    """
    return embedded_option.implied_oas(
        coupon, cpn_freq, maturity, valuation_date, market_price, curve,
        volatility=volatility, sinking_schedule=sinking_schedule,
        fraction_basis=fraction_basis)


def duration(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
             sinking_schedule, *, fraction_basis: str = OUTSTANDING,
             volatility: float = SIGMA_DEFAULT) -> float:
    """Option-adjusted effective duration in YEARS at the calibrated spread.

    Inputs: as :func:`implied_oas`, with ``oas`` (bp) in place of ``market_price``.
    Returns: float — shorter than the straight bond's, since part of the principal can be
    taken away exactly when the bond would otherwise rally.
    """
    return embedded_option.duration(
        coupon, cpn_freq, maturity, valuation_date, oas, curve, volatility=volatility,
        sinking_schedule=sinking_schedule, fraction_basis=fraction_basis)


def dv01(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
         sinking_schedule, *, fraction_basis: str = OUTSTANDING,
         volatility: float = SIGMA_DEFAULT) -> float:
    """Price change per +1 bp parallel shift (EXTENSION — no legacy counterpart).

    Inputs: identical to :func:`duration`. Returns: float per 100 face.
    """
    return embedded_option.dv01(
        coupon, cpn_freq, maturity, valuation_date, oas, curve, volatility=volatility,
        sinking_schedule=sinking_schedule, fraction_basis=fraction_basis)


def convexity(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
              sinking_schedule, *, fraction_basis: str = OUTSTANDING,
              volatility: float = SIGMA_DEFAULT) -> float:
    """Effective convexity in YEARS^2 (EXTENSION — no legacy counterpart).

    Inputs: identical to :func:`duration`. Returns: float; an in-the-money redemption
    right pulls convexity down, as a call does, in proportion to the fraction retired.
    """
    return embedded_option.convexity(
        coupon, cpn_freq, maturity, valuation_date, oas, curve, volatility=volatility,
        sinking_schedule=sinking_schedule, fraction_basis=fraction_basis)


def widening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
             sinking_schedule, bp_adjust: float = 10.0, *,
             fraction_basis: str = OUTSTANDING,
             volatility: float = SIGMA_DEFAULT) -> float:
    """Scenario clean price after the spread WIDENS by ``bp_adjust`` bp (default 10).

    Inputs: as :func:`duration`, plus ``bp_adjust`` in bp.
    Returns: float — clean price at ``oas + bp_adjust``.
    """
    return embedded_option.widening(
        coupon, cpn_freq, maturity, valuation_date, oas, curve, bp_adjust=bp_adjust,
        volatility=volatility, sinking_schedule=sinking_schedule,
        fraction_basis=fraction_basis)


def tightening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
               sinking_schedule, bp_adjust: float = 10.0, *,
               fraction_basis: str = OUTSTANDING,
               volatility: float = SIGMA_DEFAULT) -> float:
    """Scenario clean price after the spread TIGHTENS by ``bp_adjust`` bp (positive size).

    Inputs: identical to :func:`widening`. Returns: clean price at ``oas - bp_adjust``.
    """
    return embedded_option.tightening(
        coupon, cpn_freq, maturity, valuation_date, oas, curve, bp_adjust=bp_adjust,
        volatility=volatility, sinking_schedule=sinking_schedule,
        fraction_basis=fraction_basis)


def price_at_volatility(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                        sinking_schedule, oas: float,
                        volatilities=DEFAULT_VOL_SCENARIOS, *,
                        fraction_basis: str = OUTSTANDING) -> dict:
    """Price at a FIXED spread across volatility scenarios.

    Inputs
    ------
    1-6. coupon / cpn_freq / maturity / valuation_date / curve / sinking_schedule.
    7. oas            : float — the spread held FIXED, in bp.
    8. volatilities   : iterable of DECIMAL scenarios (default 0.10 / 0.15 / 0.20).
    9. fraction_basis : str — ``"outstanding"``.

    Returns: ``{volatility: clean_price}`` — falling with volatility, as for a callable,
    but scaled by how much of the bond the schedule can actually retire.
    """
    return embedded_option.price_at_volatility(
        coupon, cpn_freq, maturity, valuation_date, curve, oas, volatilities,
        sinking_schedule=sinking_schedule, fraction_basis=fraction_basis)


def implied_oas_at_volatility(coupon: float, cpn_freq: int, maturity, valuation_date,
                              market_price: float, curve, sinking_schedule,
                              volatilities=DEFAULT_VOL_SCENARIOS, *,
                              fraction_basis: str = OUTSTANDING) -> dict:
    """OAS at a FIXED market price across volatility scenarios.

    Inputs
    ------
    1-4. coupon / cpn_freq / maturity / valuation_date.
    5. market_price   : float — the CLEAN price held FIXED.
    6-7. curve / sinking_schedule.
    8. volatilities   : iterable of DECIMAL scenarios.
    9. fraction_basis : str — ``"outstanding"``.

    Returns: ``{volatility: implied_oas_bp}`` — tightening as volatility rises, because
    more of the discount is explained as the cost of the redemption right.
    """
    return embedded_option.implied_oas_at_volatility(
        coupon, cpn_freq, maturity, valuation_date, market_price, curve, volatilities,
        sinking_schedule=sinking_schedule, fraction_basis=fraction_basis)


def volatility_sensitivity(coupon: float, cpn_freq: int, maturity, valuation_date,
                           market_price: float, curve, sinking_schedule, *,
                           fraction_basis: str = OUTSTANDING,
                           baseline_volatility: float = SIGMA_DEFAULT,
                           bump: float = VOL_POINT) -> dict:
    """Both volatility slopes around the baseline, with their units named.

    Inputs: as :func:`implied_oas_at_volatility`, plus ``baseline_volatility`` and
    ``bump`` (DECIMAL; 0.01 = one volatility point).
    Returns: dict — baseline volatility and OAS, ``price_change_per_1_vol_point`` (per 100
    face) and ``oas_change_bp_per_1_vol_point`` (bp).
    """
    return embedded_option.volatility_sensitivity(
        coupon, cpn_freq, maturity, valuation_date, market_price, curve,
        baseline_volatility=baseline_volatility, bump=bump,
        sinking_schedule=sinking_schedule, fraction_basis=fraction_basis)
