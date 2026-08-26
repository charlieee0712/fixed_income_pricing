"""The v1 request/response contract — normalisation, validation, envelopes.

This module knows the SHAPE of a request and a response and nothing about pricing:
no curve, no cash flow, no spread solving. It is deliberately written with the
standard library only (no Pydantic, no JSON-Schema validator) so the first interface
adds no dependency to server 47 or to a future cloud runner.

Design stance (plan §5): forgiving about presentation, firm about economics.

    forgiven   lowercase currency, blanks around strings, numbers sent as text,
               a missing request id / schema version / operation, unknown fields
               (ignored with an UNUSED_FIELD warning), a face value other than 100
               (echoed, not applied), volatility on a vanilla request
    refused    a missing or unusable currency, a missing economic input, a date sent
               as a NUMBER (an Excel serial), maturity on/before valuation, a
               non-positive price, an unknown operation, and a hand-typed OAS in the
               operation whose whole job is to CALIBRATE the OAS

The date rule is the one place the contract is deliberately unforgiving:
``pandas.Timestamp(39903)`` parses as 1970-01-01 (nanoseconds since the epoch), so an
Excel serial that slipped through would price the bond on a silently wrong date.
"""
from __future__ import annotations

import math
import uuid

SCHEMA_VERSION = "1.0"
ENGINE = "corporate_vanilla"

OPERATION_CALIBRATE = "calibrate_and_risk"      # clean price IN  -> implied OAS OUT
OPERATION_PRICE_AT_OAS = "price_at_oas"         # OAS in bp   IN  -> model price OUT
OPERATIONS = (OPERATION_CALIBRATE, OPERATION_PRICE_AT_OAS)

DEFAULT_SPREAD_SHIFT_BP = 10.0
QUOTE_FACE = 100.0                              # every price in this contract is per 100

# Error vocabulary (plan §6.2) — kept small on purpose.
INVALID_JSON = "INVALID_JSON"
VALIDATION_ERROR = "VALIDATION_ERROR"
UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
CURVE_NOT_FOUND = "CURVE_NOT_FOUND"
CURVE_BUILD_FAILED = "CURVE_BUILD_FAILED"
CALIBRATION_FAILED = "CALIBRATION_FAILED"
PRICING_FAILED = "PRICING_FAILED"
INTERNAL_ERROR = "INTERNAL_ERROR"

# Warning codes.
UNUSED_FIELD = "UNUSED_FIELD"
FACE_VALUE_NOT_APPLIED = "FACE_VALUE_NOT_APPLIED"
NON_FINITE_RESULT = "NON_FINITE_RESULT"

_KNOWN_TOP = {"schema_version", "request_id", "operation",
              "bond", "market", "analysis", "model", "metadata"}
_KNOWN_BOND = {"instrument_id", "currency", "coupon_pct", "coupon_frequency",
               "maturity_date", "face_value", "day_count_label"}
_KNOWN_MARKET = {"valuation_date", "clean_price_per_100"}
_KNOWN_ANALYSIS = {"oas_bp", "spread_shift_bp"}
_KNOWN_MODEL = {"yield_volatility_decimal"}


class RequestError(Exception):
    """A request the interface refuses, carrying the code/field a caller can act on.

    Inputs
    ------
    1. code    : str — one of the error codes above.
    2. message : str — plain-language explanation, safe to show in a cell.
    3. field   : str | None — the JSON path at fault, e.g. ``"bond.currency"``.
    """

    def __init__(self, code: str, message: str, field: str = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


def normalize_request(payload, warnings: list = None):
    """Validate and normalise one request payload.

    Inputs
    ------
    1. payload : Mapping — the parsed JSON request (never mutated).
    2. warnings : list | None - accumulator to append to (a fresh list when omitted), so
       warnings raised before a refusal still travel with the error response.

    Returns: ``(request, warnings)`` — a flat dict of normalised, engine-ready values
    (currency uppercased, dates as ISO strings, numbers as floats, defaults applied)
    and a list of warning dicts. Raises :class:`RequestError` on a refused request.
    """
    if not isinstance(payload, dict):
        raise RequestError(VALIDATION_ERROR, "the request must be a single JSON object")
    if "requests" in payload:
        raise RequestError(
            UNSUPPORTED_OPERATION,
            "batch requests are not supported in v1 — send one bond per request "
            "(the single-bond object stays the canonical unit)",
            field="requests",
        )

    warnings = [] if warnings is None else warnings
    bond = _section(payload, "bond", warnings)
    market = _section(payload, "market", warnings)
    analysis = _section(payload, "analysis", warnings)
    model = _section(payload, "model", warnings)

    _warn_unknown(payload, _KNOWN_TOP, "", warnings)
    _warn_unknown(bond, _KNOWN_BOND, "bond.", warnings)
    _warn_unknown(market, _KNOWN_MARKET, "market.", warnings)
    _warn_unknown(analysis, _KNOWN_ANALYSIS, "analysis.", warnings)
    _warn_unknown(model, _KNOWN_MODEL, "model.", warnings)

    operation = _text(payload.get("operation"), "operation") or OPERATION_CALIBRATE
    if operation not in OPERATIONS:
        raise RequestError(
            UNSUPPORTED_OPERATION,
            f"operation {operation!r} is not supported; use one of {', '.join(OPERATIONS)}",
            field="operation",
        )

    valuation_date = _iso_date(market.get("valuation_date"), "market.valuation_date")
    maturity_date = _iso_date(bond.get("maturity_date"), "bond.maturity_date")
    if maturity_date <= valuation_date:
        raise RequestError(
            VALIDATION_ERROR,
            f"maturity {maturity_date} is on or before the valuation date {valuation_date} — "
            f"there is nothing left to price",
            field="bond.maturity_date",
        )

    currency = _text(bond.get("currency"), "bond.currency", required=True).upper()
    coupon_pct = _number(bond.get("coupon_pct"), "bond.coupon_pct", required=True,
                         minimum=0.0, maximum=40.0)
    coupon_frequency = _frequency(bond.get("coupon_frequency"))

    clean_price = _number(market.get("clean_price_per_100"), "market.clean_price_per_100",
                          required=(operation == OPERATION_CALIBRATE), strictly_positive=True)
    oas_bp = _number(analysis.get("oas_bp"), "analysis.oas_bp",
                     required=(operation == OPERATION_PRICE_AT_OAS))
    if operation == OPERATION_CALIBRATE and oas_bp is not None:
        raise RequestError(
            VALIDATION_ERROR,
            "operation 'calibrate_and_risk' CALIBRATES the OAS from the clean market price, "
            "so it does not accept a supplied 'analysis.oas_bp'. Use operation 'price_at_oas' "
            "to price at a spread you choose.",
            field="analysis.oas_bp",
        )

    shift = _number(analysis.get("spread_shift_bp"), "analysis.spread_shift_bp")
    face_value = _number(bond.get("face_value"), "bond.face_value", strictly_positive=True)
    if face_value is not None and face_value != QUOTE_FACE:
        warnings.append(_warning(
            FACE_VALUE_NOT_APPLIED, "bond.face_value",
            f"face_value {face_value:g} was not applied: every price, accrued figure and DV01 "
            f"in this interface is quoted per {QUOTE_FACE:g} face. Scale a position by "
            f"par / {QUOTE_FACE:g} on your side.",
        ))

    request = {
        "schema_version": _text(payload.get("schema_version"), "schema_version") or SCHEMA_VERSION,
        "request_id": _text(payload.get("request_id"), "request_id") or _generated_id(),
        "operation": operation,
        "instrument_id": _text(bond.get("instrument_id"), "bond.instrument_id"),
        "currency": currency,
        "coupon_pct": coupon_pct,
        "coupon_frequency": coupon_frequency,
        "maturity_date": maturity_date,
        "valuation_date": valuation_date,
        "clean_price_per_100": clean_price,
        "oas_bp": oas_bp,
        "spread_shift_bp": DEFAULT_SPREAD_SHIFT_BP if shift is None else shift,
        "face_value_supplied": face_value,
        "day_count_label": _text(bond.get("day_count_label"), "bond.day_count_label"),
        "yield_volatility": _number(model.get("yield_volatility_decimal"),
                                    "model.yield_volatility_decimal", minimum=0.0),
    }
    return request, warnings


def inputs_used(request: dict) -> dict:
    """Echo of exactly what the engine ran on, after normalisation.

    Inputs
    ------
    1. request : dict — the normalised request from :func:`normalize_request`.

    Returns: dict — the audit block of the response. A wrong cell mapping in the
    Excel bridge shows up here immediately, without anyone reading Python.
    """
    return {
        "instrument_id": request["instrument_id"],
        "currency": request["currency"],
        "coupon_pct": request["coupon_pct"],
        "coupon_frequency": request["coupon_frequency"],
        "maturity_date": request["maturity_date"],
        "valuation_date": request["valuation_date"],
        "clean_price_per_100": request["clean_price_per_100"],
        "oas_bp_supplied": request["oas_bp"],
        "spread_shift_bp": request["spread_shift_bp"],
        "face_value_supplied": request["face_value_supplied"],
        "face_value_per_quote": QUOTE_FACE,
    }


def success_response(request: dict, market_data: dict, results: dict,
                     applicability: dict, warnings: list) -> dict:
    """Assemble the ``status="ok"`` envelope.

    Inputs
    ------
    1. request       : dict — the normalised request.
    2. market_data   : dict — pricing currency / valuation date / curve id.
    3. results       : dict — the numbers.
    4. applicability : dict — what was supplied but not used, and why.
    5. warnings      : list — accumulated warning dicts.

    Returns: dict — the complete response object, JSON-serialisable as-is.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": request["request_id"],
        "status": "ok",
        "engine": ENGINE,
        "operation": request["operation"],
        "inputs_used": inputs_used(request),
        "market_data": market_data,
        "results": results,
        "applicability": applicability,
        "warnings": warnings,
        "errors": [],
    }


def error_response(code: str, message: str, field: str = None,
                   request: dict = None, warnings: list = None) -> dict:
    """Assemble the ``status="error"`` envelope.

    Inputs
    ------
    1. code    : str — an error code from the vocabulary above.
    2. message : str — plain-language explanation (never a traceback or a path).
    3. field   : str | None — the JSON path at fault.
    4. request : dict | None — the normalised request, when normalisation got that far.
    5. warnings : list | None — warnings collected before the failure.

    Returns: dict — the complete error response, JSON-serialisable as-is.
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": (request or {}).get("request_id"),
        "status": "error",
        "engine": ENGINE,
        "operation": (request or {}).get("operation"),
        "inputs_used": inputs_used(request) if request else None,
        "market_data": None,
        "results": None,
        "applicability": None,
        "warnings": warnings or [],
        "errors": [{"code": code, "field": field, "message": message}],
    }


def finite_or_none(value, name: str, warnings: list):
    """Keep NaN/inf out of the JSON: return ``None`` and warn instead.

    Inputs
    ------
    1. value    : float — a computed result.
    2. name     : str — the result field name (for the warning).
    3. warnings : list — warning accumulator, appended in place.

    Returns: float | None. A ``null`` is honest about a number we could not produce;
    a numeric placeholder would be read as a real result.
    """
    number = float(value)
    if math.isfinite(number):
        return number
    warnings.append(_warning(NON_FINITE_RESULT, name,
                             f"{name} could not be computed as a finite number"))
    return None


def _warning(code: str, field: str, message: str) -> dict:
    """One warning entry (same shape as an error entry, but never fatal)."""
    return {"code": code, "field": field, "message": message}


def _generated_id() -> str:
    """A request id for callers that did not send one."""
    return f"auto-{uuid.uuid4().hex[:12]}"


def _section(payload: dict, name: str, warnings: list) -> dict:
    """Return one request section as a dict; absent -> empty, wrong type -> error."""
    value = payload.get(name)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RequestError(VALIDATION_ERROR, f"'{name}' must be a JSON object", field=name)
    return value


def _warn_unknown(section: dict, known: set, prefix: str, warnings: list) -> None:
    """Ignore unknown fields, but say so — they must never change a calculation."""
    for key in section:
        if key not in known:
            warnings.append(_warning(
                UNUSED_FIELD, f"{prefix}{key}",
                f"'{prefix}{key}' is not part of the v1 contract and was ignored "
                f"(put caller-specific information under 'metadata')",
            ))


def _text(value, field: str, required: bool = False):
    """Trimmed string, or None. Numbers are stringified; blanks count as absent."""
    if value is None:
        if required:
            raise RequestError(VALIDATION_ERROR, f"'{field}' is required", field=field)
        return None
    text = str(value).strip()
    if not text:
        if required:
            raise RequestError(VALIDATION_ERROR, f"'{field}' is required", field=field)
        return None
    return text


def _number(value, field: str, required: bool = False, minimum: float = None,
            maximum: float = None, strictly_positive: bool = False):
    """Finite float, or None. Numeric strings are accepted; booleans are not."""
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise RequestError(VALIDATION_ERROR, f"'{field}' is required", field=field)
        return None
    if isinstance(value, bool):
        raise RequestError(VALIDATION_ERROR, f"'{field}' must be a number", field=field)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise RequestError(VALIDATION_ERROR,
                           f"'{field}' must be a number; got {value!r}", field=field) from None
    if not math.isfinite(number):
        raise RequestError(VALIDATION_ERROR, f"'{field}' must be a finite number", field=field)
    if strictly_positive and number <= 0:
        raise RequestError(VALIDATION_ERROR, f"'{field}' must be greater than zero", field=field)
    if minimum is not None and number < minimum:
        raise RequestError(VALIDATION_ERROR,
                           f"'{field}' must be >= {minimum:g}; got {number:g}", field=field)
    if maximum is not None and number > maximum:
        raise RequestError(
            VALIDATION_ERROR,
            f"'{field}' must be <= {maximum:g}; got {number:g} — note that this interface "
            f"takes a coupon in PERCENT (6.5 = 6.5%)", field=field)
    return number


def _frequency(value) -> int:
    """Coupon payments per year, restricted to the four supported schedules."""
    if value is None:
        raise RequestError(VALIDATION_ERROR, "'bond.coupon_frequency' is required",
                           field="bond.coupon_frequency")
    try:
        freq = int(float(value))
    except (TypeError, ValueError):
        freq = None
    if freq not in (1, 2, 4, 12):
        raise RequestError(
            VALIDATION_ERROR,
            f"'bond.coupon_frequency' must be 1 (annual), 2 (semiannual), 4 (quarterly) "
            f"or 12 (monthly); got {value!r}",
            field="bond.coupon_frequency",
        )
    return freq


def _iso_date(value, field: str) -> str:
    """ISO date STRING -> normalised ``YYYY-MM-DD``. A number is refused on purpose.

    An Excel serial (39903) would be parsed by pandas as nanoseconds since the epoch,
    i.e. 1970-01-01, and the bond would be priced on the wrong date with no error
    anywhere. Converting serials is the caller's (VBA bridge's) job.
    """
    import pandas as pd

    if value is None or (isinstance(value, str) and not value.strip()):
        raise RequestError(VALIDATION_ERROR, f"'{field}' is required (ISO date, YYYY-MM-DD)",
                           field=field)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        raise RequestError(
            VALIDATION_ERROR,
            f"'{field}' must be a date STRING (YYYY-MM-DD), not the number {value!r}. "
            f"An Excel date serial would be read as 1970-01-01 and price the bond on the "
            f"wrong date — convert it with Format(cell, \"yyyy-mm-dd\") before sending.",
            field=field,
        )
    try:
        return pd.Timestamp(str(value).strip()).date().isoformat()
    except (ValueError, TypeError):
        raise RequestError(VALIDATION_ERROR,
                           f"'{field}' is not a readable date: {value!r} (use YYYY-MM-DD)",
                           field=field) from None
