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

SCHEMA_VERSION = "1.1"
ENGINE = "corporate_vanilla"                    # engine of a request that names no type

OPERATION_CALIBRATE = "calibrate_and_risk"      # clean price IN  -> implied OAS OUT
OPERATION_PRICE_AT_OAS = "price_at_oas"         # OAS in bp   IN  -> model price OUT
OPERATIONS = (OPERATION_CALIBRATE, OPERATION_PRICE_AT_OAS)

# One dispatch key, seven products. Adding types here rather than adding endpoints keeps
# ONE entry point, one envelope and one set of error codes for every bond in the book.
VANILLA = "vanilla"
STEPPED = "stepped"
FLOATING = "floating"
FIXED_TO_FLOATING = "fixed_to_floating"
CALLABLE = "callable"
PUTTABLE = "puttable"
SINKING = "sinking"
INSTRUMENT_TYPES = (VANILLA, STEPPED, FLOATING, FIXED_TO_FLOATING,
                    CALLABLE, PUTTABLE, SINKING)

# The products priced on the short-rate tree — the only ones with a volatility input.
TREE_TYPES = (CALLABLE, PUTTABLE, SINKING)
# The products whose coupon is a fixed schedule rather than a single rate.
SCHEDULE_TYPES = (STEPPED,)

DEFAULT_VOLATILITY = 0.15                       # Mario v1 short-rate volatility
DEFAULT_SINKING_BASIS = "outstanding"

DEFAULT_SPREAD_SHIFT_BP = 10.0
QUOTE_FACE = 100.0                              # every price in this contract is per 100

# Error vocabulary (plan §6.2) — kept small on purpose.
INVALID_JSON = "INVALID_JSON"
VALIDATION_ERROR = "VALIDATION_ERROR"
UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
UNSUPPORTED_INSTRUMENT = "UNSUPPORTED_INSTRUMENT"
CURVE_NOT_FOUND = "CURVE_NOT_FOUND"
CURVE_BUILD_FAILED = "CURVE_BUILD_FAILED"
CALIBRATION_FAILED = "CALIBRATION_FAILED"
PRICING_FAILED = "PRICING_FAILED"
INTERNAL_ERROR = "INTERNAL_ERROR"

# Warning codes.
UNUSED_FIELD = "UNUSED_FIELD"
FACE_VALUE_NOT_APPLIED = "FACE_VALUE_NOT_APPLIED"
NON_FINITE_RESULT = "NON_FINITE_RESULT"
PROVISIONAL_TERMS = "PROVISIONAL_TERMS"        # priced on terms nobody has confirmed
PROVISIONAL_RISK = "PROVISIONAL_RISK"          # priced on an estimated already-fixed coupon

_KNOWN_TOP = {"schema_version", "request_id", "operation",
              "bond", "market", "analysis", "model", "metadata"}
_KNOWN_BOND = {"instrument_id", "instrument_type", "currency", "coupon_pct",
               "coupon_frequency", "maturity_date", "face_value", "day_count_label",
               # per-product inputs (each used by the types named in bonds_input)
               "coupon_schedule", "quoted_margin_bp", "current_coupon_pct",
               "switch_date", "float_frequency",
               "call_schedule", "put_schedule", "sinking_schedule",
               "sinking_fraction_basis", "exercise_terms_status"}
_KNOWN_MARKET = {"valuation_date", "clean_price_per_100"}
_KNOWN_ANALYSIS = {"oas_bp", "spread_shift_bp", "volatility_scenarios"}
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

    instrument_type = (_text(bond.get("instrument_type"), "bond.instrument_type")
                       or VANILLA).lower().replace("-", "_").replace(" ", "_")
    if instrument_type not in INSTRUMENT_TYPES:
        raise RequestError(
            UNSUPPORTED_INSTRUMENT,
            f"instrument_type {instrument_type!r} is not supported; use one of "
            f"{', '.join(INSTRUMENT_TYPES)}",
            field="bond.instrument_type",
        )

    currency = _text(bond.get("currency"), "bond.currency", required=True).upper()
    # A floating note has NO fixed coupon input; a stepped bond carries a schedule
    # instead of a rate. Requiring one everywhere would force callers to invent a number.
    coupon_required = instrument_type not in (FLOATING,) + SCHEDULE_TYPES
    coupon_pct = _number(bond.get("coupon_pct"), "bond.coupon_pct",
                         required=coupon_required, minimum=0.0, maximum=40.0)
    if instrument_type == FLOATING and coupon_pct is not None:
        warnings.append(_warning(
            UNUSED_FIELD, "bond.coupon_pct",
            "a floating-rate note has no fixed coupon: 'bond.coupon_pct' was ignored. "
            "The already-fixed coupon of the CURRENT period goes in "
            "'bond.current_coupon_pct'; the contractual spread goes in "
            "'bond.quoted_margin_bp'.",
        ))
        coupon_pct = None
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

    product = _product_inputs(bond, analysis, instrument_type, valuation_date,
                              maturity_date, warnings)

    request = {
        "schema_version": _text(payload.get("schema_version"), "schema_version") or SCHEMA_VERSION,
        "request_id": _text(payload.get("request_id"), "request_id") or _generated_id(),
        "operation": operation,
        "instrument_id": _text(bond.get("instrument_id"), "bond.instrument_id"),
        "instrument_type": instrument_type,
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
    request.update(product)
    return request, warnings


def _product_inputs(bond: dict, analysis: dict, instrument_type: str, valuation_date: str,
                    maturity_date: str, warnings: list) -> dict:
    """Normalise the inputs that belong to one product only.

    Inputs
    ------
    1. bond            : dict — the request's bond section.
    2. analysis        : dict — the request's analysis section.
    3. instrument_type : str — the dispatch key, already validated.
    4. valuation_date  : str — normalised ISO date.
    5. maturity_date   : str — normalised ISO date.
    6. warnings        : list — accumulator, appended in place.

    Returns: dict of engine-ready per-product values, with every key present for every
    type (``None`` where the product does not use it) so the response shape never
    depends on which branch ran. Raises :class:`RequestError` for a missing input the
    product cannot be priced without.
    """
    out = {
        "coupon_schedule": None,
        "quoted_margin_bp": None,
        "current_coupon_pct": None,
        "switch_date": None,
        "float_frequency": None,
        "call_schedule": None,
        "put_schedule": None,
        "sinking_schedule": None,
        "sinking_fraction_basis": None,
        "volatility_scenarios": None,
    }

    if instrument_type in SCHEDULE_TYPES:
        out["coupon_schedule"] = _coupon_schedule(bond.get("coupon_schedule"))

    if instrument_type in (FLOATING, FIXED_TO_FLOATING):
        # A hybrid MUST have its post-switch margin: pricing one on a placeholder zero
        # would report a half-modelled bond as a whole one. A plain floater may be
        # priced with the margin absorbed into the calibrated spread, and the response
        # says which happened, so the number is never read as a clean credit spread.
        margin = _number(bond.get("quoted_margin_bp"), "bond.quoted_margin_bp",
                         required=(instrument_type == FIXED_TO_FLOATING),
                         minimum=0.0, maximum=5000.0)
        if margin is None:
            margin = 0.0
            warnings.append(_warning(
                UNUSED_FIELD, "bond.quoted_margin_bp",
                "no quoted margin was supplied, so the calibrated spread ABSORBS the "
                "note's contractual margin as well as its credit. The price is exact and "
                "the risk numbers are unaffected, but do not read the spread as a clean "
                "credit spread until a margin is supplied.",
            ))
        out["quoted_margin_bp"] = margin

    if instrument_type == FLOATING:
        out["current_coupon_pct"] = _number(bond.get("current_coupon_pct"),
                                            "bond.current_coupon_pct",
                                            minimum=0.0, maximum=40.0)
        if out["current_coupon_pct"] is None:
            # The coupon now running was fixed at the last reset and is a KNOWN amount. Without
            # it we estimate one off the curve and hold it fixed through the risk bumps, which
            # is the right treatment but is still an estimate of an observable.
            warnings.append(_warning(
                PROVISIONAL_RISK, "bond.current_coupon_pct",
                "the coupon already running was not supplied, so it is estimated from the "
                "curve and held fixed while the risk is measured. The price is unaffected; "
                "the sensitivities are PROVISIONAL until the actual fixing is supplied.",
            ))

    if instrument_type == FIXED_TO_FLOATING:
        switch = _iso_date(bond.get("switch_date"), "bond.switch_date")
        if switch <= valuation_date:
            warnings.append(_warning(
                UNUSED_FIELD, "bond.switch_date",
                f"the switch date {switch} is on or before the valuation date — this bond "
                f"is already floating, and it is priced on the floating-rate engine.",
            ))
        out["switch_date"] = switch
        if bond.get("float_frequency") is not None:
            out["float_frequency"] = _frequency(bond.get("float_frequency"),
                                                field="bond.float_frequency")

    if instrument_type in TREE_TYPES:
        out["call_schedule"] = _exercise_schedule(bond.get("call_schedule"),
                                                  "bond.call_schedule")
        out["put_schedule"] = _exercise_schedule(bond.get("put_schedule"),
                                                 "bond.put_schedule")
        out["sinking_schedule"] = _sinking_schedule(bond.get("sinking_schedule"))
        out["sinking_fraction_basis"] = _text(bond.get("sinking_fraction_basis"),
                                              "bond.sinking_fraction_basis")
        _require_matching_schedule(instrument_type, out)
        if out["sinking_schedule"]:
            _check_sinking_basis(out["sinking_fraction_basis"])
        out["volatility_scenarios"] = _volatility_scenarios(
            analysis.get("volatility_scenarios"))

        # An exercise price is a CONTRACT TERM, and 100.0 looks the same whether it came from
        # a prospectus or from a convention someone applied to a custodian date. Every schedule
        # this project prices today is the latter. A caller who has confirmed terms says so;
        # anyone who does not gets told, in the response, what they are looking at.
        status = _text(bond.get("exercise_terms_status"), "bond.exercise_terms_status")
        status = (status or "provisional").strip().lower()
        if status not in ("confirmed", "provisional"):
            raise RequestError(VALIDATION_ERROR,
                               f"exercise_terms_status must be 'confirmed' or 'provisional', "
                               f"not {status!r}.", "bond.exercise_terms_status")
        out["exercise_terms_status"] = status
        if status != "confirmed":
            warnings.append(_warning(
                PROVISIONAL_TERMS, "bond.exercise_terms_status",
                "the exercise schedule is not marked as confirmed, so these results are "
                "PROVISIONAL: an exercise date or price taken from a convention rather than "
                "from the documents changes the option value and the risk. Send "
                "exercise_terms_status='confirmed' once the terms are verified.",
            ))

    return out


def _check_sinking_basis(basis) -> None:
    """A sinking schedule must say what its fractions are fractions OF.

    Inputs
    ------
    1. basis : str | None — ``bond.sinking_fraction_basis``.

    Returns: None. Raises :class:`RequestError` when it is missing or not
    ``"outstanding"``.

    The engine already refuses both cases, but it does so from inside the spread solver,
    where the failure surfaces as "no spread reprices this bond — check the price, the
    coupon and the maturity". That message sends the reader hunting in the wrong place.
    Refusing here names the actual field.
    """
    if basis is None:
        raise RequestError(
            VALIDATION_ERROR,
            "'bond.sinking_fraction_basis' is required with a sinking schedule: this "
            f"engine retires a fraction of the amount still OUTSTANDING, so send "
            f"{DEFAULT_SINKING_BASIS!r}. It is not defaulted, because a caller who meant "
            f"fractions of the ORIGINAL face would otherwise get the other model without "
            f"being told.",
            field="bond.sinking_fraction_basis",
        )
    if basis.strip().lower() != DEFAULT_SINKING_BASIS:
        raise RequestError(
            VALIDATION_ERROR,
            f"'bond.sinking_fraction_basis' {basis!r} is not implemented; this engine "
            f"supports {DEFAULT_SINKING_BASIS!r} only. Retiring a fixed share of the "
            f"ORIGINAL face works against a shrinking base, which a recombining tree "
            f"cannot represent — that structure needs one callable sub-bond per sink "
            f"date. Convert the schedule rather than relabelling it.",
            field="bond.sinking_fraction_basis",
        )


def _require_matching_schedule(instrument_type: str, product: dict) -> None:
    """A tree product must carry the right the caller says it has.

    Inputs
    ------
    1. instrument_type : str — callable / puttable / sinking.
    2. product         : dict — the normalised per-product inputs.

    Returns: None. Raises :class:`RequestError` when the schedule naming the product's
    own right is absent — a callable bond with no call schedule is a straight bond, and
    silently pricing it as one would answer a question nobody asked.
    """
    needed = {CALLABLE: ("call_schedule", "a call schedule"),
              PUTTABLE: ("put_schedule", "a put schedule"),
              SINKING: ("sinking_schedule", "a sinking-fund schedule")}[instrument_type]
    if not product[needed[0]]:
        raise RequestError(
            VALIDATION_ERROR,
            f"instrument_type '{instrument_type}' needs {needed[1]} in "
            f"'bond.{needed[0]}'; without one the bond is a straight bond and should be "
            f"sent as instrument_type 'vanilla'",
            field=f"bond.{needed[0]}",
        )


def inputs_used(request: dict) -> dict:
    """Echo of exactly what the engine ran on, after normalisation.

    Inputs
    ------
    1. request : dict — the normalised request from :func:`normalize_request`.

    Returns: dict — the audit block of the response. A wrong cell mapping in the
    Excel bridge shows up here immediately, without anyone reading Python.
    """
    used = {
        "instrument_id": request["instrument_id"],
        "instrument_type": request.get("instrument_type", VANILLA),
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
    # Per-product inputs are echoed only where the product uses them, so a vanilla
    # response is unchanged from v1.0 and a floating one is not padded with nulls.
    extras = {
        STEPPED: ("coupon_schedule",),
        FLOATING: ("quoted_margin_bp", "current_coupon_pct"),
        FIXED_TO_FLOATING: ("quoted_margin_bp", "switch_date", "float_frequency"),
        CALLABLE: ("call_schedule", "put_schedule"),
        PUTTABLE: ("call_schedule", "put_schedule"),
        SINKING: ("sinking_schedule", "sinking_fraction_basis", "call_schedule",
                  "put_schedule"),
    }.get(request.get("instrument_type"), ())
    for name in extras:
        used[name] = _echo(name, request.get(name))
    return used


def _echo(name: str, value):
    """Echo one per-product input in the SHAPE THE CALLER SENT IT.

    Inputs
    ------
    1. name  : str — the field name.
    2. value : the normalised, engine-ready value.

    Returns: JSON-ready value. Schedules go back out as objects with the request's own
    field names and units — ``rate_pct``, not the engine's decimal — because the audit
    block exists so a wrong cell mapping in the spreadsheet is visible without reading
    Python. An echo in different units than the request would defeat that.
    """
    if value is None:
        return None
    if name == "coupon_schedule":
        # round only the ECHO: 0.07 * 100 is 7.000000000000001, and an audit line that
        # does not match the cell it came from is worse than useless
        return [{"effective_from": _iso(eff), "rate_pct": round(rate * 100.0, 10)}
                for eff, rate in value]
    if name in ("call_schedule", "put_schedule"):
        return [{"date": _iso(date), "price_per_100": price} for date, price in value]
    if name == "sinking_schedule":
        return [{"date": _iso(date), "fraction": fraction, "price_per_100": price}
                for date, fraction, price in value]
    return value


def _iso(value):
    """A date as an ISO string; ``None`` passes through."""
    return None if value is None else value.isoformat()


def engine_for(instrument_type) -> str:
    """Engine name reported in the response envelope.

    Inputs
    ------
    1. instrument_type : str | None — the dispatch key.

    Returns: str — ``corporate_<type>``; a request that names no type keeps the v1.0
    value ``corporate_vanilla`` exactly.
    """
    return f"corporate_{instrument_type or VANILLA}"


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
        "engine": engine_for(request.get("instrument_type")),
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
        "engine": engine_for((request or {}).get("instrument_type")),
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


def _frequency(value, field: str = "bond.coupon_frequency") -> int:
    """Coupon payments per year, restricted to the four supported schedules."""
    if value is None:
        raise RequestError(VALIDATION_ERROR, f"'{field}' is required", field=field)
    try:
        freq = int(float(value))
    except (TypeError, ValueError):
        freq = None
    if freq not in (1, 2, 4, 12):
        raise RequestError(
            VALIDATION_ERROR,
            f"'{field}' must be 1 (annual), 2 (semiannual), 4 (quarterly) "
            f"or 12 (monthly); got {value!r}",
            field=field,
        )
    return freq


def _entries(value, field: str):
    """A schedule section as a list of JSON objects; absent -> None, wrong shape -> error."""
    if value is None or value == []:
        return None
    if not isinstance(value, list) or not all(isinstance(e, dict) for e in value):
        raise RequestError(
            VALIDATION_ERROR,
            f"'{field}' must be a list of objects, e.g. "
            f"[{{\"date\": \"2014-08-15\", \"price_per_100\": 100}}]",
            field=field,
        )
    return value


def _coupon_schedule(value):
    """``bond.coupon_schedule`` -> the engine's ``[(date | None, rate_decimal), ...]``.

    Inputs
    ------
    1. value : list — ``[{"effective_from": "YYYY-MM-DD" | null, "rate_pct": 7.5}, ...]``.

    Returns: the engine-shaped schedule, sorted with the open-ended entry first.

    ⚠️ The JSON says **rate_pct** and the engine takes decimals; this boundary is the one
    place that conversion happens, so an external caller sees percent everywhere (as it
    does for ``coupon_pct``) and the engine keeps its single internal convention.
    A stepped bond with no schedule is refused: its whole definition is the schedule.
    """
    import pandas as pd  # noqa: F401  (kept local, like _iso_date)

    entries = _entries(value, "bond.coupon_schedule")
    if not entries:
        raise RequestError(
            VALIDATION_ERROR,
            "instrument_type 'stepped' needs 'bond.coupon_schedule', e.g. "
            "[{\"effective_from\": null, \"rate_pct\": 7.0}, "
            "{\"effective_from\": \"2006-03-01\", \"rate_pct\": 7.5}]. A step-up whose "
            "steps are not known is a data gap to report, not a schedule to invent.",
            field="bond.coupon_schedule",
        )
    out = []
    for i, entry in enumerate(entries):
        where = f"bond.coupon_schedule[{i}]"
        raw = entry.get("effective_from")
        eff = None if raw is None or (isinstance(raw, str) and not raw.strip()) \
            else _iso_date(raw, f"{where}.effective_from")
        rate = _number(entry.get("rate_pct"), f"{where}.rate_pct", required=True,
                       minimum=0.0, maximum=40.0)
        out.append((eff, rate / 100.0))
    out.sort(key=lambda e: (e[0] is not None, e[0] or ""))
    # the open-ended entry ("from issuance") keeps its None; the engine reads it as
    # "in force before every dated step"
    return [(None if eff is None else _as_date(eff), rate) for eff, rate in out]


def _exercise_schedule(value, field: str):
    """``bond.call_schedule`` / ``put_schedule`` -> ``[(date, price_per_100), ...]``.

    Inputs
    ------
    1. value : list — ``[{"date": "2014-08-15", "price_per_100": 100.0}, ...]``.
    2. field : str — the JSON path, for error messages.

    Returns: the engine-shaped schedule, or ``None`` when absent. Ordering and duplicate
    handling are the asset layer's job (it normalises there for every caller, not only
    this one).
    """
    entries = _entries(value, field)
    if not entries:
        return None
    out = []
    for i, entry in enumerate(entries):
        where = f"{field}[{i}]"
        date = _as_date(_iso_date(entry.get("date"), f"{where}.date"))
        price = _number(entry.get("price_per_100"), f"{where}.price_per_100",
                        required=True, strictly_positive=True)
        out.append((date, price))
    return out


def _sinking_schedule(value):
    """``bond.sinking_schedule`` -> ``[(date, fraction, price_per_100), ...]``.

    Inputs
    ------
    1. value : list — ``[{"date": ..., "fraction": 0.05, "price_per_100": 100.0}, ...]``.

    Returns: the engine-shaped schedule, or ``None`` when absent. ``fraction`` is the
    share of the amount OUTSTANDING the issuer may retire on that date, as a DECIMAL in
    [0, 1] — not a percentage, and not a share of the original face.
    """
    entries = _entries(value, "bond.sinking_schedule")
    if not entries:
        return None
    out = []
    for i, entry in enumerate(entries):
        where = f"bond.sinking_schedule[{i}]"
        date = _as_date(_iso_date(entry.get("date"), f"{where}.date"))
        fraction = _number(entry.get("fraction"), f"{where}.fraction", required=True,
                           minimum=0.0, maximum=1.0)
        price = _number(entry.get("price_per_100"), f"{where}.price_per_100",
                        required=True, strictly_positive=True)
        out.append((date, fraction, price))
    return out


def _volatility_scenarios(value):
    """``analysis.volatility_scenarios`` -> a tuple of DECIMAL volatilities, or None.

    Inputs
    ------
    1. value : list of numbers — e.g. ``[0.10, 0.15, 0.20]``.

    Returns: tuple of floats, or ``None`` when the caller did not ask for the scenario
    table. The local slopes around the baseline are always returned; the table is extra
    work (two solved lattices per scenario) and is therefore opt-in.
    """
    if value is None or value == []:
        return None
    if not isinstance(value, list):
        raise RequestError(VALIDATION_ERROR,
                           "'analysis.volatility_scenarios' must be a list of numbers, "
                           "e.g. [0.10, 0.15, 0.20]",
                           field="analysis.volatility_scenarios")
    return tuple(_number(v, f"analysis.volatility_scenarios[{i}]", required=True,
                         minimum=0.0, maximum=2.0) for i, v in enumerate(value))


def _as_date(iso: str):
    """Normalised ISO string -> ``datetime.date`` (what the engines take)."""
    import datetime as dt

    return dt.date.fromisoformat(iso)


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
