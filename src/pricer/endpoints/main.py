"""Public entry point of the pricing interface (template: ``endpoints/main.py``).

ONE transport-independent function: a payload dict in, a response dict out, never an
exception. Whatever carries the payload — a JSON file written by Excel today, an HTTP
POST from the cloud service later — calls this and serialises what comes back.

    from pricer.endpoints.main import analyze_payload
    response = analyze_payload(json.loads(text))
    response["status"]                      # "ok" | "error"

The bond's type travels IN the payload (``bond.instrument_type``: vanilla, stepped,
floating, fixed_to_floating, callable, puttable, sinking) rather than in the function
called or the URL requested. That is deliberate: a caller integrates once and prices any
bond in the book, and a new engine later adds a value here rather than a second entry
point, a second envelope and a second set of error codes to keep in step.

Failures are values, not exceptions: every error path returns the same envelope with
``status="error"`` and one entry in ``errors``. Nothing here formats JSON, touches a
file, knows a path, or computes a price.
"""
from __future__ import annotations

from pricer.assets.corporate.embedded_option import ExerciseScheduleNotRepresentable
from pricer.core.market.curves import CurveUnavailable
from pricer.endpoints import contracts, pricing


def analyze_payload(payload) -> dict:
    """Price one corporate bond of any supported type from one request payload.

    Inputs
    ------
    1. payload : Mapping — the parsed request object (see ``contracts`` for the
       contract; the payload is never mutated).

    Returns: dict — the complete response object, always JSON-serialisable, with
    ``status`` "ok" or "error".
    """
    warnings = []
    request = None
    try:
        request, warnings = contracts.normalize_request(payload, warnings)
        market_data, results, applicability = pricing.analyze(request, warnings)
        return contracts.success_response(request, market_data, results, applicability, warnings)

    except contracts.RequestError as err:
        return contracts.error_response(err.code, err.message, err.field, request, warnings)

    except ExerciseScheduleNotRepresentable as err:
        # The caller sent a right the model's time grid cannot place. Name the field they
        # sent it in, so the answer points at the schedule rather than at the price.
        return contracts.error_response(
            contracts.VALIDATION_ERROR, str(err), f"bond.{err.right}_schedule",
            request, warnings)

    except CurveUnavailable as err:
        code = (contracts.CURVE_NOT_FOUND if err.reason == "not_found"
                else contracts.CURVE_BUILD_FAILED)
        return contracts.error_response(code, str(err), "bond.currency", request, warnings)

    except Exception as err:                        # last resort: never leak internals
        return contracts.error_response(
            contracts.INTERNAL_ERROR,
            f"the request could not be completed ({type(err).__name__}); "
            f"the details are in the server log, not in this response",
            None, request, warnings,
        )


def analyze_vanilla_payload(payload) -> dict:
    """The v1.0 name for :func:`analyze_payload`, kept so existing callers do not change.

    Inputs
    ------
    1. payload : Mapping — the parsed request object.

    Returns: dict — identical to :func:`analyze_payload`. A payload that names no
    ``bond.instrument_type`` is a vanilla bond, so a v1.0 caller reaching this name gets
    byte-for-byte the response it got before, and one that names a type is dispatched
    normally rather than refused.
    """
    return analyze_payload(payload)
