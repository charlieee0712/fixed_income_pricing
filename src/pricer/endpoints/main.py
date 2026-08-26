"""Public entry point of the pricing interface (template: ``endpoints/main.py``).

ONE transport-independent function: a payload dict in, a response dict out, never an
exception. Whatever carries the payload — a JSON file written by Excel today, an HTTP
POST from the cloud service later — calls this and serialises what comes back.

    from pricer.endpoints.main import analyze_vanilla_payload
    response = analyze_vanilla_payload(json.loads(text))
    response["status"]                      # "ok" | "error"

Failures are values, not exceptions: every error path returns the same envelope with
``status="error"`` and one entry in ``errors``. Nothing here formats JSON, touches a
file, knows a path, or computes a price.
"""
from __future__ import annotations

from pricer.core.market.curves import CurveUnavailable
from pricer.endpoints import contracts, pricing


def analyze_vanilla_payload(payload) -> dict:
    """Price one vanilla corporate bond from one request payload.

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
        market_data, results, applicability = pricing.analyze_vanilla(request, warnings)
        return contracts.success_response(request, market_data, results, applicability, warnings)

    except contracts.RequestError as err:
        return contracts.error_response(err.code, err.message, err.field, request, warnings)

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
