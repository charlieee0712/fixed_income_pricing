"""Interface layer (template: ``endpoints/``) — one request in, one result out.

The internal design is "many small functions"; the EXTERNAL design is deliberately
the opposite: a caller that cannot import Python (Excel/VBA today, an HTTP client
tomorrow) sends one request object and receives every output for that bond in one
response. The two are complementary — the endpoint is a thin arrangement layer over
the same functions a Python caller uses.

    main.py          the public entry: analyze_payload(payload) -> response
    contracts.py     the request/response shape: normalisation, validation, envelopes
    pricing.py       orchestration per instrument type — calls assets.corporate.*,
                     no formulas of its own
    dependencies.py  the only environment-aware file (where the curve files live)

``bond.instrument_type`` selects the engine — vanilla, stepped, floating,
fixed_to_floating, callable, puttable, sinking — so one integration prices every
corporate bond in the book. A payload that names no type is a vanilla bond, which is
why ``analyze_vanilla_payload`` (the v1.0 name) still returns exactly what it did.

    routes/          the HTTP door (2026-09-28) — ``handle(method, path, body)``,
                     framework-free, so a Web App, a Function App and the local runner
                     each reach the same contract without any of them owning it

Three ways in, one contract: ``scripts/price_json.py`` (request file -> response file),
the Excel/VBA bridge, and now HTTP. ⭐ What goes over the wire is asserted byte-for-byte
equal to what a Python caller gets from the same request in the same process
(``tests/test_http_routes.py``), so the transport cannot become a place where a number
changes. ⚠️ No CORS and no authentication yet — a browser on another origin is refused
by the browser itself, before the request arrives, which is invisible in any server log.
"""
from pricer.endpoints.main import analyze_payload, analyze_vanilla_payload  # noqa: F401

__all__ = ["analyze_payload", "analyze_vanilla_payload"]
