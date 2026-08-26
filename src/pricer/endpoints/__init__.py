"""Interface layer (template: ``endpoints/``) — one request in, one result out.

The internal design is "many small functions"; the EXTERNAL design is deliberately
the opposite: a caller that cannot import Python (Excel/VBA today, an HTTP client
tomorrow) sends one request object and receives every vanilla output in one response.
The two are complementary — the endpoint is a thin arrangement layer over the same
functions a Python caller uses.

    main.py          the public entry: analyze_vanilla_payload(payload) -> response
    contracts.py     the request/response shape: normalisation, validation, envelopes
    pricing.py       vanilla orchestration — calls assets.corporate.vanilla, no formulas
    dependencies.py  the only environment-aware file (where the curve files live)

The template also shows ``endpoints/routes/`` for HTTP routes; with a single
non-HTTP entry point that folder would be empty nesting, so it arrives with the
service. File-based use: ``scripts/price_json.py`` (request file -> response file).
"""
from pricer.endpoints.main import analyze_vanilla_payload  # noqa: F401

__all__ = ["analyze_vanilla_payload"]
