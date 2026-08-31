"""Orchestration for the JSON interface (template: ``endpoints/pricing.py``).

This module contains NO pricing formula. It resolves the curve, calls the approved
``assets.corporate`` functions — the same ones a Python caller uses — and arranges their
output. Cash flows, accrued interest, discount factors, root solving and the sensitivity
arithmetic all stay in the validated modules underneath, which is what makes an endpoint
result identical to a direct function call by construction.

**One entry, seven products.** ``analyze`` dispatches on ``bond.instrument_type`` to one
short function per product. Every one of them runs the same seven steps:

    1. resolve the own-currency curve            (dependencies.curve_for)
    2. get the spread: calibrate it from the clean market price, or take the
       supplied one                              (the product's implied_oas / request)
    3. price at that spread                      (clean / dirty / accrued together)
    4. risk metrics at that spread               (duration / dv01 / convexity)
    5. the two spread scenarios                  (widening / tightening)
    6. package results, keeping non-finite numbers out of the JSON
    7. state what was supplied but not used, and why

They differ only in which engine step 2-5 call and in the one or two extra numbers a
product is worth reporting: the next reset for a floater, the switch and the
price-to-the-switch reference for a hybrid, the volatility response for the three
products that carry an option.

The dispatch is a mapping rather than a chain of ``if``s so that adding the mortgage
engine later is one entry and one function, with no change to the envelope, the error
vocabulary or any caller.
"""
from __future__ import annotations

from pricer.assets.corporate import embedded_option, floating, hybrid, stepped, vanilla
from pricer.assets.corporate.embedded_option import ExerciseScheduleNotRepresentable
from pricer.assets.corporate.bonds_input import (PRICING_CONVENTION, VANILLA_NOT_APPLICABLE,
                                                 VOLATILITY_NOT_APPLICABLE,
                                                 validate_vanilla_inputs)
from pricer.core.market.curves import curve_id
from pricer.core.pricing.analytical import price_fixed_rate_bond
from pricer.core.pricing.floating import price_frn
from pricer.core.pricing.hybrid import price_hybrid
from pricer.endpoints import contracts, dependencies

_BP = 1e-4      # one basis point in decimal — the same constant the wrappers use

CALIBRATED = "calibrated_from_clean_price"
SUPPLIED = "supplied_by_caller"

MARGIN_SUPPLIED = "supplied_by_caller"
MARGIN_ABSORBED = "absorbed_into_the_calibrated_spread"


def analyze(request: dict, warnings: list):
    """Run one normalised request end to end, on the engine its type names.

    Inputs
    ------
    1. request  : dict — normalised request (``contracts.normalize_request``).
    2. warnings : list — warning accumulator, appended in place.

    Returns: ``(market_data, results, applicability)`` — the three response blocks.
    Raises :class:`contracts.RequestError` (validation / calibration / pricing failures)
    or :class:`pricer.core.market.curves.CurveUnavailable` (curve failures).
    """
    kind = request.get("instrument_type", contracts.VANILLA)
    freq = request["coupon_frequency"]
    curve = dependencies.curve_for(request["currency"], request["valuation_date"], freq)
    market_data = {
        "pricing_currency": request["currency"],
        "valuation_date": request["valuation_date"],
        "curve_id": curve_id(request["currency"], curve),
    }
    handler = {
        contracts.VANILLA: _analyze_vanilla,
        contracts.STEPPED: _analyze_stepped,
        contracts.FLOATING: _analyze_floating,
        contracts.FIXED_TO_FLOATING: _analyze_hybrid,
        contracts.CALLABLE: _analyze_embedded_option,
        contracts.PUTTABLE: _analyze_embedded_option,
        contracts.SINKING: _analyze_embedded_option,
    }[kind]
    results, applicability = handler(request, curve, warnings)
    return market_data, results, applicability


# Kept so v1.0 callers and tests that import the vanilla-only entry keep working.
def analyze_vanilla(request: dict, warnings: list):
    """Alias of :func:`analyze` (the v1.0 name, when vanilla was the only product)."""
    return analyze(request, warnings)


# ------------------------------------------------------------------ per-product handlers

def _analyze_vanilla(request: dict, curve, warnings: list):
    """Plain fixed-coupon bullet — the v1.0 path, unchanged."""
    coupon, freq = request["coupon_pct"], request["coupon_frequency"]
    val, mat, face = request["valuation_date"], request["maturity_date"], contracts.QUOTE_FACE

    try:                                    # the engine's own input contract
        validate_vanilla_inputs(coupon, freq)
    except ValueError as exc:
        raise contracts.RequestError(contracts.VALIDATION_ERROR, str(exc), field="bond") from None

    oas_bp, oas_source = _spread(
        request, lambda target: vanilla.implied_oas(coupon, freq, mat, val, target, curve,
                                                    face=face))
    with _pricing_errors(request):
        # One core call gives clean, dirty and accrued together. It is the SAME call
        # vanilla.calculated_price makes (same argument order, same unit conversions),
        # so `clean` here is bit-for-bit the wrapper's answer.
        priced = price_fixed_rate_bond(val, mat, coupon / 100.0, curve, oas=oas_bp * _BP,
                                       face=face, freq=freq)
        risk = {
            "eff_duration": vanilla.duration(coupon, freq, mat, val, oas_bp, curve, face=face),
            "dv01": vanilla.dv01(coupon, freq, mat, val, oas_bp, curve, face=face),
            "convexity": vanilla.convexity(coupon, freq, mat, val, oas_bp, curve, face=face),
        }
        shift = request["spread_shift_bp"]
        scenarios = (
            vanilla.tightening(coupon, freq, mat, val, oas_bp, curve, bp_adjust=shift, face=face),
            vanilla.widening(coupon, freq, mat, val, oas_bp, curve, bp_adjust=shift, face=face),
        )

    results = _assemble(request, priced.clean, priced.dirty, priced.accrued, oas_bp,
                        oas_source, risk, scenarios, warnings)
    return results, _applicability(request, contracts.VANILLA)


def _analyze_stepped(request: dict, curve, warnings: list):
    """Known coupon path (stepped / step-up) — the vanilla engine with a time-table."""
    sched, freq = request["coupon_schedule"], request["coupon_frequency"]
    val, mat, face = request["valuation_date"], request["maturity_date"], contracts.QUOTE_FACE

    try:
        stepped.validate_schedule(sched)
    except ValueError as exc:
        raise contracts.RequestError(contracts.VALIDATION_ERROR, str(exc),
                                     field="bond.coupon_schedule") from None

    oas_bp, oas_source = _spread(
        request, lambda target: stepped.implied_oas(sched, freq, mat, val, target, curve,
                                                    face=face))
    with _pricing_errors(request):
        priced = price_fixed_rate_bond(val, mat, 0.0, curve, oas=oas_bp * _BP, face=face,
                                       freq=freq, coupon_schedule=sched)
        risk = {
            "eff_duration": stepped.duration(sched, freq, mat, val, oas_bp, curve, face=face),
            "dv01": stepped.dv01(sched, freq, mat, val, oas_bp, curve, face=face),
            "convexity": stepped.convexity(sched, freq, mat, val, oas_bp, curve, face=face),
        }
        shift = request["spread_shift_bp"]
        scenarios = (
            stepped.tightening(sched, freq, mat, val, oas_bp, curve, bp_adjust=shift, face=face),
            stepped.widening(sched, freq, mat, val, oas_bp, curve, bp_adjust=shift, face=face),
        )

    results = _assemble(request, priced.clean, priced.dirty, priced.accrued, oas_bp,
                        oas_source, risk, scenarios, warnings)
    results["coupon_pct_in_force_at_valuation"] = contracts.finite_or_none(
        stepped.coupon_on(sched, val) * 100.0, "coupon_pct_in_force_at_valuation", warnings)
    return results, _applicability(request, contracts.STEPPED)


def _analyze_floating(request: dict, curve, warnings: list):
    """Floating-rate note — coupons projected off the curve, plus the quoted margin."""
    freq = request["coupon_frequency"]
    val, mat, face = request["valuation_date"], request["maturity_date"], contracts.QUOTE_FACE
    margin = request["quoted_margin_bp"]
    current = request["current_coupon_pct"]
    kw = dict(quoted_margin_bp=margin, current_coupon_pct=current, face=face)

    oas_bp, oas_source = _spread(
        request, lambda target: floating.implied_oas(freq, mat, val, target, curve, **kw))
    with _pricing_errors(request):
        priced = price_frn(val, mat, curve, oas=oas_bp * _BP,
                           current_coupon=None if current is None else current / 100.0,
                           spread=margin * _BP, face=face, freq=freq)
        risk = {
            "eff_duration": floating.duration(freq, mat, val, oas_bp, curve, **kw),
            "dv01": floating.dv01(freq, mat, val, oas_bp, curve, **kw),
            "convexity": floating.convexity(freq, mat, val, oas_bp, curve, **kw),
        }
        shift = request["spread_shift_bp"]
        scenarios = (
            floating.tightening(freq, mat, val, oas_bp, curve, shift, **kw),
            floating.widening(freq, mat, val, oas_bp, curve, shift, **kw),
        )

    results = _assemble(request, priced.clean, priced.dirty, priced.accrued, oas_bp,
                        oas_source, risk, scenarios, warnings)
    results["next_reset_years"] = contracts.finite_or_none(priced.next_reset_t,
                                                           "next_reset_years", warnings)
    results["quoted_margin_source"] = MARGIN_SUPPLIED if margin else MARGIN_ABSORBED
    results["spread_interpretation"] = (
        "credit spread over the note's index" if margin else
        "discount margin: it absorbs the note's unknown contractual margin as well as "
        "its credit, because no quoted margin was supplied")
    return results, _applicability(request, contracts.FLOATING)


def _analyze_hybrid(request: dict, curve, warnings: list):
    """Fixed-then-floating — one bond, one spread, two legs glued at the switch."""
    coupon, freq = request["coupon_pct"], request["coupon_frequency"]
    val, mat, face = request["valuation_date"], request["maturity_date"], contracts.QUOTE_FACE
    switch, margin = request["switch_date"], request["quoted_margin_bp"]
    float_freq = request["float_frequency"]
    kw = dict(quoted_margin_bp=margin, float_freq=float_freq, face=face)

    oas_bp, oas_source = _spread(
        request, lambda target: hybrid.implied_oas(coupon, freq, mat, val, target, curve,
                                                   switch, **kw))
    with _pricing_errors(request):
        priced = price_hybrid(val, mat, curve, oas=oas_bp * _BP,
                              fixed_rate=coupon / 100.0, switch_date=switch,
                              spread=margin * _BP, fixed_freq=freq,
                              float_freq=float_freq, face=face)
        risk = {
            "eff_duration": hybrid.duration(coupon, freq, mat, val, oas_bp, curve, switch, **kw),
            "dv01": hybrid.dv01(coupon, freq, mat, val, oas_bp, curve, switch, **kw),
            "convexity": hybrid.convexity(coupon, freq, mat, val, oas_bp, curve, switch, **kw),
        }
        shift = request["spread_shift_bp"]
        scenarios = (
            hybrid.tightening(coupon, freq, mat, val, oas_bp, curve, switch, shift, **kw),
            hybrid.widening(coupon, freq, mat, val, oas_bp, curve, switch, shift, **kw),
        )

    results = _assemble(request, priced.clean, priced.dirty, priced.accrued, oas_bp,
                        oas_source, risk, scenarios, warnings)
    results["next_switch_years"] = contracts.finite_or_none(priced.next_switch_t,
                                                            "next_switch_years", warnings)
    results["reference_oas_to_switch_bp"] = _reference_to_switch(request, curve, warnings)
    results["reference_note"] = (
        "reference_oas_to_switch_bp prices the bond as if repaid in full at the switch "
        "date. It is a secondary column and is spurious for a deep discount, where the "
        "market is pricing EXTENSION rather than repayment; implied_oas_bp is the answer.")
    return results, _applicability(request, contracts.FIXED_TO_FLOATING)


def _analyze_embedded_option(request: dict, curve, warnings: list):
    """Callable / puttable / sinking — the one shared tree, and the volatility answer."""
    coupon, freq = request["coupon_pct"], request["coupon_frequency"]
    val, mat, face = request["valuation_date"], request["maturity_date"], contracts.QUOTE_FACE
    if face != contracts.QUOTE_FACE:                    # defensive: the contract fixes it
        raise contracts.RequestError(contracts.VALIDATION_ERROR, "prices are quoted per 100")
    vol = request["yield_volatility"]
    if vol is None:
        vol = contracts.DEFAULT_VOLATILITY
    rights = {
        "call_schedule": request["call_schedule"],
        "put_schedule": request["put_schedule"],
        "sinking_schedule": request["sinking_schedule"],
        "fraction_basis": request["sinking_fraction_basis"],
    }

    try:
        validate_vanilla_inputs(coupon, freq)
    except ValueError as exc:
        raise contracts.RequestError(contracts.VALIDATION_ERROR, str(exc), field="bond") from None

    oas_bp, oas_source = _spread(
        request, lambda target: embedded_option.implied_oas(coupon, freq, mat, val, target,
                                                            curve, volatility=vol, **rights))
    with _pricing_errors(request):
        priced = embedded_option.price_detail(coupon, freq, mat, val, curve, oas=oas_bp,
                                              volatility=vol, **rights)
        risk = {
            "eff_duration": embedded_option.duration(coupon, freq, mat, val, oas_bp, curve,
                                                     volatility=vol, **rights),
            "dv01": embedded_option.dv01(coupon, freq, mat, val, oas_bp, curve,
                                         volatility=vol, **rights),
            "convexity": embedded_option.convexity(coupon, freq, mat, val, oas_bp, curve,
                                                   volatility=vol, **rights),
        }
        shift = request["spread_shift_bp"]
        scenarios = (
            embedded_option.tightening(coupon, freq, mat, val, oas_bp, curve, shift,
                                       volatility=vol, **rights),
            embedded_option.widening(coupon, freq, mat, val, oas_bp, curve, shift,
                                     volatility=vol, **rights),
        )

    results = _assemble(request, priced["clean"], priced["dirty"], priced["accrued"],
                        oas_bp, oas_source, risk, scenarios, warnings)
    results["volatility_used_decimal"] = vol
    return results, _applicability(request, request["instrument_type"], curve=curve, vol=vol,
                                   rights=rights, warnings=warnings)


# ------------------------------------------------------------------------ shared steps

def _spread(request: dict, calibrate):
    """Step 2: the spread every later number is computed at.

    Inputs
    ------
    1. request   : dict — the normalised request (its operation decides the route).
    2. calibrate : callable — ``target_clean -> spread_bp`` for this product's engine.

    Returns: ``(oas_bp, source)`` — the spread in BASIS POINTS and where it came from
    (``"calibrated_from_clean_price"`` or ``"supplied_by_caller"``).
    """
    if request["operation"] == contracts.OPERATION_PRICE_AT_OAS:
        return request["oas_bp"], SUPPLIED

    target = request["clean_price_per_100"]
    try:
        return calibrate(target), CALIBRATED
    except ExerciseScheduleNotRepresentable:
        # A contract the model grid cannot represent is NOT a calibration failure. Letting
        # it fall through would report "no spread reprices this bond - check the price, the
        # coupon and the maturity", sending the reader to the wrong three fields entirely.
        # (The same mistake the sinking-basis refusal used to make.)
        raise
    except ValueError as exc:
        raise contracts.RequestError(
            contracts.CALIBRATION_FAILED,
            f"no spread reprices this bond to a clean price of {target:g} per 100 on the "
            f"{request['currency']} curve for {request['valuation_date']} — check the "
            f"price, the coupon and the maturity ({exc.__class__.__name__})",
            field="market.clean_price_per_100",
        ) from None


class _pricing_errors:
    """Context manager mapping an engine failure onto ``PRICING_FAILED``.

    Inputs
    ------
    1. request : dict — the normalised request (named in the message).

    Every product wraps steps 3-5 in this, so an arithmetic failure comes back as a
    response with a reason rather than as an exception, and no path or traceback leaks.
    """

    def __init__(self, request):
        self.request = request

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None and issubclass(exc_type, ExerciseScheduleNotRepresentable):
            return False                    # a contract problem, not a pricing failure
        if exc_type is None or not issubclass(exc_type, (ValueError, ArithmeticError)):
            return False
        raise contracts.RequestError(
            contracts.PRICING_FAILED,
            f"the bond could not be priced on the {self.request['currency']} curve for "
            f"{self.request['valuation_date']}: {exc}",
        ) from None


def _assemble(request: dict, clean, dirty, accrued, oas_bp, oas_source, risk, scenarios,
              warnings: list) -> dict:
    """Step 6: the result block every product shares, non-finite values excluded.

    Inputs
    ------
    1. request    : dict — the normalised request.
    2-4. clean / dirty / accrued : float — the priced values, per 100.
    5. oas_bp     : float — the spread everything was computed at, bp.
    6. oas_source : str — calibrated or supplied.
    7. risk       : dict — ``{eff_duration, dv01, convexity}``.
    8. scenarios  : tuple — ``(price_tighter, price_wider)``.
    9. warnings   : list — accumulator, appended in place.

    Returns: dict — the shared part of ``results``; each handler adds its own extras.
    """
    keep = lambda name, value: contracts.finite_or_none(value, name, warnings)  # noqa: E731
    tighter, wider = scenarios
    return {
        "model_clean_price_per_100": keep("model_clean_price_per_100", clean),
        "model_dirty_price_per_100": keep("model_dirty_price_per_100", dirty),
        "accrued_interest_per_100": keep("accrued_interest_per_100", accrued),
        "implied_oas_bp": keep("implied_oas_bp", oas_bp),
        "oas_source": oas_source,
        "effective_duration_years": keep("effective_duration_years", risk["eff_duration"]),
        "dv01_per_100": keep("dv01_per_100", risk["dv01"]),
        "convexity": keep("convexity", risk["convexity"]),
        "price_spread_tighter_per_100": keep("price_spread_tighter_per_100", tighter),
        "price_spread_wider_per_100": keep("price_spread_wider_per_100", wider),
        "calibration_residual_per_100": (
            keep("calibration_residual_per_100", clean - request["clean_price_per_100"])
            if oas_source == CALIBRATED else None
        ),
    }


def _reference_to_switch(request: dict, curve, warnings: list):
    """The hybrid's secondary "priced to the switch" column, or ``None``.

    Inputs
    ------
    1. request  : dict — the normalised request.
    2. curve    : ZeroCurve.
    3. warnings : list — accumulator.

    Returns: float | None — the spread in bp of a bullet maturing at the switch. Only
    meaningful when a market price was supplied; a failure to solve it is NOT an error
    for the request, because this column is a reference and the main answer stands
    without it.
    """
    if request["operation"] != contracts.OPERATION_CALIBRATE:
        return None
    if request["switch_date"] <= request["valuation_date"]:
        return None
    try:
        value = hybrid.reference_implied_oas_to_switch(
            request["coupon_pct"], request["coupon_frequency"], request["valuation_date"],
            request["clean_price_per_100"], curve, request["switch_date"])
    except (ValueError, ArithmeticError):
        warnings.append({"code": contracts.NON_FINITE_RESULT,
                         "field": "reference_oas_to_switch_bp",
                         "message": "the price-to-the-switch reference could not be "
                                    "solved; it is a secondary column and the main "
                                    "spread is unaffected"})
        return None
    return contracts.finite_or_none(value, "reference_oas_to_switch_bp", warnings)


def _applicability(request: dict, kind: str, curve=None, vol=None, rights=None,
                   warnings=None) -> dict:
    """Step 7: inputs a generic form may send that this product does not use.

    Inputs
    ------
    1. request : dict — the normalised request.
    2. kind    : str — the instrument type.
    3-6. curve / vol / rights / warnings — supplied only for the tree products, whose
       volatility block carries real numbers instead of a reason.

    Returns: dict — one entry per such input, each stating the value received, whether it
    was used, and why. For an option-free product the volatility sensitivities are
    ``null``, never 0.0: a zero would be read as a calculated vega.
    """
    block = {
        "day_count": {
            "input_value_label": request["day_count_label"],
            "used": False,
            "convention_used": PRICING_CONVENTION,
            "reason": VANILLA_NOT_APPLICABLE["day_count"],
        },
    }
    if kind in contracts.TREE_TYPES:
        block["yield_volatility"] = _volatility_block(request, curve, vol, rights, warnings)
    else:
        block["yield_volatility"] = {
            "input_value_decimal": request["yield_volatility"],
            "used": False,
            "price_effect_per_1pct_vol": None,
            "oas_effect_bp_per_1pct_vol": None,
            "reason": VOLATILITY_NOT_APPLICABLE[kind],
        }
    return block


def _volatility_block(request: dict, curve, vol, rights, warnings) -> dict:
    """The volatility answer for a product that actually has one.

    Inputs
    ------
    1. request  : dict — the normalised request.
    2. curve    : ZeroCurve.
    3. vol      : float — the baseline volatility actually used, DECIMAL.
    4. rights   : dict — the exercise schedules.
    5. warnings : list — accumulator.

    Returns: dict with the baseline, the two local slopes, and — only when the caller
    asked via ``analysis.volatility_scenarios`` — the full scenario table.

    The two slopes answer two DIFFERENT questions and are reported separately, never
    added or averaged: one moves the PRICE at a fixed spread, the other moves the SPREAD
    at a fixed price. Both need a market price, so on a ``price_at_oas`` request only the
    first is available and the second is ``null`` with a reason.
    """
    coupon, freq = request["coupon_pct"], request["coupon_frequency"]
    val, mat = request["valuation_date"], request["maturity_date"]
    out = {"input_value_decimal": request["yield_volatility"], "used": True,
           "baseline_volatility_decimal": vol}

    if request["operation"] != contracts.OPERATION_CALIBRATE:
        out.update({
            "price_effect_per_1pct_vol": None,
            "oas_effect_bp_per_1pct_vol": None,
            "reason": "both volatility experiments are anchored on a market price; send "
                      "operation 'calibrate_and_risk' with market.clean_price_per_100 to "
                      "get them",
        })
        return out

    price = request["clean_price_per_100"]
    try:
        slopes = embedded_option.volatility_sensitivity(
            coupon, freq, mat, val, price, curve, baseline_volatility=vol, **rights)
    except (ValueError, ArithmeticError):
        out.update({"price_effect_per_1pct_vol": None, "oas_effect_bp_per_1pct_vol": None,
                    "reason": "the volatility experiments could not be solved for this "
                              "bond; the priced result above is unaffected"})
        return out

    out["price_effect_per_1pct_vol"] = contracts.finite_or_none(
        slopes["price_change_per_1_vol_point"], "price_effect_per_1pct_vol", warnings)
    out["oas_effect_bp_per_1pct_vol"] = contracts.finite_or_none(
        slopes["oas_change_bp_per_1_vol_point"], "oas_effect_bp_per_1pct_vol", warnings)
    out["reason"] = ("price effect = change in clean price per +1 volatility POINT at a "
                     "FIXED spread; oas effect = change in the calibrated spread per +1 "
                     "volatility point at a FIXED market price. Different questions — "
                     "never combine them.")

    scenarios = request.get("volatility_scenarios")
    if scenarios:
        out["scenarios"] = _volatility_scenarios(request, curve, scenarios,
                                                 slopes["baseline_implied_oas_bp"], rights)
    return out


def _volatility_scenarios(request: dict, curve, scenarios, base_oas, rights) -> list:
    """The opt-in scenario table: both experiments at each requested volatility.

    Inputs
    ------
    1. request   : dict — the normalised request.
    2. curve     : ZeroCurve.
    3. scenarios : tuple of float — DECIMAL volatilities.
    4. base_oas  : float — the baseline spread held fixed in the price experiment, bp.
    5. rights    : dict — the exercise schedules.

    Returns: list of ``{volatility_decimal, clean_price_at_baseline_oas,
    implied_oas_bp_at_market_price}`` — one row per scenario, the shape of the table in
    the weekly report.
    """
    coupon, freq = request["coupon_pct"], request["coupon_frequency"]
    val, mat = request["valuation_date"], request["maturity_date"]
    price = request["clean_price_per_100"]
    prices = embedded_option.price_at_volatility(coupon, freq, mat, val, curve, base_oas,
                                                 scenarios, **rights)
    spreads = embedded_option.implied_oas_at_volatility(coupon, freq, mat, val, price,
                                                        curve, scenarios, **rights)
    return [{"volatility_decimal": v,
             "clean_price_at_baseline_oas": prices[v],
             "implied_oas_bp_at_market_price": spreads[v]} for v in sorted(prices)]
