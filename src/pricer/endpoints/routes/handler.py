"""One pure function that turns an HTTP request into an HTTP response.

    handle(method, path, body) -> (status, headers, body)

No framework, no third-party import, no global state. Every host adapter — a local
``http.server``, an Azure Web App behind gunicorn, a Function App — calls this and does
nothing else.

TWO ROUTES
    POST /price    one bond in, one complete answer out. The body is the same request
                   object ``scripts/price_json.py`` reads from a file and the Excel bridge
                   builds from cells; the answer is byte-for-byte the same response.
    GET  /health   whether this instance can actually price anything — see below.

THE STATUS CODE IS DERIVED, NOT TABULATED
``analyze_payload`` never raises: it returns a response whose ``status`` is "ok" or "error",
and an error carries a ``code``. So the rule here is two lines —

    ok                -> 200
    INTERNAL_ERROR    -> 500
    any other error   -> 400

⭐ and it is written as a rule rather than a lookup table on purpose. A table mapping each
of the contract's error codes to a status would be a second owner of that list, and it would
go stale the first time ``contracts.py`` gains a code — silently, returning 500 for something
the caller could have fixed. The single distinction that matters is whether the caller can
act on it, and ``INTERNAL_ERROR`` is the only code that says they cannot.

⚠️ **The body is the complete response either way**, identical to what the file runner
writes. A caller that ignores the status line and reads the JSON gets exactly what the Excel
bridge gets; a caller that reads the status line gets something a gateway or a monitor can
aggregate. Neither reading is second class.

WHAT /health IS FOR, AND WHY IT DOES WORK
A health check that only proves the process is alive is worth nothing here: the most likely
way this deployment fails is that the code is up and the **curve data is not there** —
``FIP_DATA_DIR`` unset, or the data directory never uploaded. That failure would answer every
health probe with a cheerful 200 and every real request with CURVE_NOT_FOUND. So the check
counts the par-curve exports it can see, and reports **503 when there are none**.
"""
from __future__ import annotations

import json
import os

from pricer.endpoints import dependencies
from pricer.endpoints.main import analyze_payload

#: Largest request body accepted, in bytes. A single-bond request is a few kilobytes even
#: with a long call schedule, so this is generous by two orders of magnitude while still
#: refusing the request that exists to exhaust memory. Refused before any parsing.
MAX_BODY_BYTES = 256 * 1024

#: The contract's one code that the caller cannot act on. Everything else is their request.
_CALLER_CANNOT_FIX = "INTERNAL_ERROR"

_JSON = {"Content-Type": "application/json; charset=utf-8"}


def _json_body(obj) -> bytes:
    # sort_keys=False keeps the contract's field order, which the fixtures are written in
    # and which a human diffing two responses relies on.
    return json.dumps(obj, ensure_ascii=False, allow_nan=False).encode("utf-8")


def _error(status: int, code: str, message: str):
    """A transport-level refusal, shaped like the contract's errors so a caller needs only
    one parser. These requests never reached the pricing layer, so the envelope is minimal —
    but the ``errors`` ARRAY of ``{code, field, message}`` is the contract's own shape, not
    an approximation of it.

    ⚠️ The first version of this used ``{"error": {...}}``, singular, invented from memory
    rather than read from ``contracts.error_response``. A caller would then have needed two
    parsers to read one service, which is exactly what this function claims to prevent.
    """
    return status, dict(_JSON), _json_body(
        {"status": "error",
         "errors": [{"code": code, "field": None, "message": message}]})


def health() -> tuple[int, dict, bytes]:
    """Whether this instance can price, not merely whether it is running.

    Inputs: none (reads the configured data directory).
    Returns: the usual (status, headers, body). **503 when no curve files are visible.**
    """
    directory = dependencies.data_dir()
    try:
        curves = sorted(f for f in os.listdir(directory) if f.endswith("_Yield_Curve.txt"))
    except OSError:
        curves = []
    ok = bool(curves)
    return (200 if ok else 503), dict(_JSON), _json_body({
        "status": "ok" if ok else "error",
        "service": "ryse-fixed-income-pricing",
        "curves_visible": len(curves),
        # The DIRECTORY is deliberately absent: the contract forbids a path in any message
        # leaving this process, and a health endpoint is the easiest place to forget that.
        "detail": ("ready" if ok else
                   "no par-curve exports are visible to this instance; the data directory "
                   "is unset or empty"),
    })


def handle(method: str, path: str, body: bytes | None = None):
    """Route one request. Never raises.

    Inputs
    ------
    1. method : str — the HTTP method.
    2. path   : str — the path, query string already stripped by the adapter.
    3. body   : bytes | None — the raw request body.

    Returns: ``(status:int, headers:dict, body:bytes)``.
    """
    route = (path or "/").rstrip("/") or "/"

    if route == "/health":
        if method != "GET":
            return _error(405, "METHOD_NOT_ALLOWED", "/health accepts GET")
        return health()

    if route != "/price":
        return _error(404, "NOT_FOUND",
                      "unknown path; this service exposes POST /price and GET /health")

    if method != "POST":
        return _error(405, "METHOD_NOT_ALLOWED",
                      "/price accepts POST with a JSON request body")

    raw = body or b""
    if len(raw) > MAX_BODY_BYTES:
        return _error(413, "REQUEST_TOO_LARGE",
                      f"the request body exceeds {MAX_BODY_BYTES} bytes; this service "
                      "prices one bond per request")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        # ⚠️ The parser's own message is NOT forwarded: it quotes the offending input, and
        # the request may carry a client's position. The caller knows what they sent.
        return _error(400, "MALFORMED_JSON",
                      "the request body is not valid UTF-8 JSON")
    if not isinstance(payload, dict):
        return _error(400, "MALFORMED_JSON",
                      "the request body must be a JSON object, not an array or a scalar")

    response = analyze_payload(payload)
    # `errors` is an ARRAY of {code, field, message} -- read from contracts.error_response,
    # not assumed. A singular `error` object was the first guess here and it silently broke
    # the 500 branch: every failure fell through to 400, including the one case the caller
    # cannot act on. The default was plausible enough to hide the bug.
    codes = {e.get("code") for e in (response.get("errors") or []) if isinstance(e, dict)}
    if response.get("status") == "ok":
        status = 200
    elif _CALLER_CANNOT_FIX in codes:
        status = 500
    else:
        status = 400
    return status, dict(_JSON), _json_body(response)
