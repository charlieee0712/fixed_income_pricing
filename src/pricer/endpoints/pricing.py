"""Vanilla orchestration for the JSON interface (template: ``endpoints/pricing.py``).

This module contains NO pricing formula. It resolves the curve, calls the approved
``assets.corporate.vanilla`` functions — the same ones a Python caller uses — and
arranges their output. Cash flows, accrued interest, discount factors, root solving
and the sensitivity arithmetic all stay in the validated modules underneath, which is
what makes the endpoint result identical to a direct function call by construction.

Both operations run the same seven steps; they differ only in step 2:

    1. resolve the own-currency curve            (dependencies.curve_for)
    2. get the spread: calibrate it from the clean market price, or take the
       supplied one                              (vanilla.implied_oas / request)
    3. price at that spread                      (core price_fixed_rate_bond)
    4. risk metrics at that spread               (vanilla.duration / dv01 / convexity)
    5. the two spread scenarios                  (vanilla.widening / tightening)
    6. package results, keeping non-finite numbers out of the JSON
    7. state what was supplied but not used, and why
"""
from __future__ import annotations

from pricer.assets.corporate import vanilla
from pricer.assets.corporate.bonds_input import (PRICING_CONVENTION, VANILLA_NOT_APPLICABLE,
                                                 validate_vanilla_inputs)
from pricer.core.market.curves import curve_id
from pricer.core.pricing.analytical import price_fixed_rate_bond
from pricer.endpoints import contracts, dependencies

_BP = 1e-4      # one basis point in decimal — the same constant vanilla.py uses

CALIBRATED = "calibrated_from_clean_price"
SUPPLIED = "supplied_by_caller"


def analyze_vanilla(request: dict, warnings: list):
    """Run one normalised vanilla request end to end.

    Inputs
    ------
    1. request  : dict — normalised request (``contracts.normalize_request``).
    2. warnings : list — warning accumulator, appended in place.

    Returns: ``(market_data, results, applicability)`` — the three response blocks.
    Raises :class:`contracts.RequestError` (calibration/pricing failures) or
    :class:`pricer.core.market.curves.CurveUnavailable` (curve failures).
    """
    coupon = request["coupon_pct"]
    freq = request["coupon_frequency"]
    val = request["valuation_date"]
    mat = request["maturity_date"]
    face = contracts.QUOTE_FACE

    try:                                    # the engine's own input contract
        validate_vanilla_inputs(coupon, freq)
    except ValueError as exc:
        raise contracts.RequestError(contracts.VALIDATION_ERROR, str(exc), field="bond") from None

    curve = dependencies.curve_for(request["currency"], val, freq)
    oas_bp, oas_source = _spread(request, curve, coupon, freq, val, mat, face)

    try:
        # One core call gives clean, dirty and accrued together. It is the SAME call
        # vanilla.calculated_price makes (same argument order, same unit conversions),
        # so `clean` here is bit-for-bit the wrapper's answer.
        priced = price_fixed_rate_bond(val, mat, coupon / 100.0, curve, oas=oas_bp * _BP,
                                       face=face, freq=freq)
        duration = vanilla.duration(coupon, freq, mat, val, oas_bp, curve, face=face)
        dv01 = vanilla.dv01(coupon, freq, mat, val, oas_bp, curve, face=face)
        convexity = vanilla.convexity(coupon, freq, mat, val, oas_bp, curve, face=face)
        shift = request["spread_shift_bp"]
        wider = vanilla.widening(coupon, freq, mat, val, oas_bp, curve, bp_adjust=shift, face=face)
        tighter = vanilla.tightening(coupon, freq, mat, val, oas_bp, curve, bp_adjust=shift,
                                     face=face)
    except (ValueError, ArithmeticError) as exc:
        raise contracts.RequestError(
            contracts.PRICING_FAILED,
            f"the bond could not be priced on the {request['currency']} curve for "
            f"{val}: {exc}",
        ) from None

    market_data = {
        "pricing_currency": request["currency"],
        "valuation_date": val,
        "curve_id": curve_id(request["currency"], curve),
    }

    keep = lambda name, value: contracts.finite_or_none(value, name, warnings)  # noqa: E731
    results = {
        "model_clean_price_per_100": keep("model_clean_price_per_100", priced.clean),
        "model_dirty_price_per_100": keep("model_dirty_price_per_100", priced.dirty),
        "accrued_interest_per_100": keep("accrued_interest_per_100", priced.accrued),
        "implied_oas_bp": keep("implied_oas_bp", oas_bp),
        "oas_source": oas_source,
        "effective_duration_years": keep("effective_duration_years", duration),
        "dv01_per_100": keep("dv01_per_100", dv01),
        "convexity": keep("convexity", convexity),
        "price_spread_tighter_per_100": keep("price_spread_tighter_per_100", tighter),
        "price_spread_wider_per_100": keep("price_spread_wider_per_100", wider),
        "calibration_residual_per_100": (
            keep("calibration_residual_per_100", priced.clean - request["clean_price_per_100"])
            if oas_source == CALIBRATED else None
        ),
    }
    return market_data, results, _applicability(request)


def _spread(request: dict, curve, coupon, freq, val, mat, face):
    """Step 2: the spread every later number is computed at.

    Inputs
    ------
    1. request : dict — the normalised request (its operation decides the route).
    2. curve   : ZeroCurve — the resolved discount curve.
    3-7. coupon / freq / val / mat / face — the engine's bond inputs.

    Returns: ``(oas_bp, source)`` — the spread in BASIS POINTS and where it came from
    (``"calibrated_from_clean_price"`` or ``"supplied_by_caller"``).
    """
    if request["operation"] == contracts.OPERATION_PRICE_AT_OAS:
        return request["oas_bp"], SUPPLIED

    target = request["clean_price_per_100"]
    try:
        return vanilla.implied_oas(coupon, freq, mat, val, target, curve, face=face), CALIBRATED
    except ValueError as exc:
        raise contracts.RequestError(
            contracts.CALIBRATION_FAILED,
            f"no spread reprices this bond to a clean price of {target:g} per 100 on the "
            f"{request['currency']} curve for {val} — check the price, the coupon and the "
            f"maturity ({exc.__class__.__name__})",
            field="market.clean_price_per_100",
        ) from None


def _applicability(request: dict) -> dict:
    """Step 7: inputs a generic form may send that vanilla does not use.

    Inputs
    ------
    1. request : dict — the normalised request.

    Returns: dict — one entry per such input, each stating the value received, that it
    was not used, and why. Volatility sensitivities are ``null``, never 0.0: a zero
    would be read as a calculated vega.
    """
    return {
        "yield_volatility": {
            "input_value_decimal": request["yield_volatility"],
            "used": False,
            "price_effect_per_1pct_vol": None,
            "oas_effect_bp_per_1pct_vol": None,
            "reason": VANILLA_NOT_APPLICABLE["volatility"],
        },
        "day_count": {
            "input_value_label": request["day_count_label"],
            "used": False,
            "convention_used": PRICING_CONVENTION,
            "reason": VANILLA_NOT_APPLICABLE["day_count"],
        },
    }
