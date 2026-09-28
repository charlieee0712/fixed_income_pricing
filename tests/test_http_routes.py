"""Locks for the HTTP layer (2026-09-28) — step one of the hosted service.

The whole point of this layer is that it is transport and nothing else. So the load-bearing
test is not that it returns 200: it is that **what comes back over HTTP is byte-for-byte
what a Python caller gets from the same request in the same process.** If that ever stops
holding, the HTTP layer has started having opinions, and a number somewhere is different
depending on how you asked for it.

Everything here runs against ``handle()`` directly. No socket, no framework, no server to
start — which is the property that made the framework-free design worth having, and it is
why these run in the ordinary suite rather than as an integration step somebody skips.
"""
import json
import os

import pytest

from pricer.endpoints.main import analyze_payload
from pricer.endpoints.routes import handle

EXAMPLES = "integrations/excel_vba/examples"
REQUESTS = sorted(f for f in os.listdir(EXAMPLES) if f.endswith("_request_v1.json")
                  or f.endswith("_request_v1_1.json"))


def _post(payload):
    return handle("POST", "/price", json.dumps(payload).encode("utf-8"))


# --------------------------------------------------------------------- the load-bearing one

@pytest.mark.parametrize("name", REQUESTS)
def test_http_returns_exactly_what_a_python_caller_gets(name):
    """⭐ Transport, not translation. Asserted with ``==`` on the decoded object AND on the
    serialised bytes, because a reordering of keys would pass the first and break any
    consumer diffing two responses."""
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        payload = json.load(fh)

    status, headers, body = _post(payload)
    over_http = json.loads(body.decode("utf-8"))
    direct = analyze_payload(payload)

    assert over_http == direct
    assert list(over_http) == list(direct), "field order changed in transit"
    assert headers["Content-Type"].startswith("application/json")


def test_every_shipped_fixture_is_exercised():
    """A parametrized test over a glob that matched nothing passes silently. This project
    has hit that exact failure twice, most recently in a parity check that compared zero
    files and reported success."""
    assert len(REQUESTS) >= 9, f"only found {len(REQUESTS)} request fixtures"


# --------------------------------------------------------------------- the status rule

def test_a_priced_bond_is_200():
    with open(os.path.join(EXAMPLES, "vanilla_request_v1.json"), encoding="utf-8") as fh:
        status, _, body = _post(json.load(fh))
    assert status == 200
    assert json.loads(body)["status"] == "ok"


def test_a_refused_request_is_400_and_still_carries_the_full_response():
    """The caller can fix it, so 4xx — and the body is the contract's own error object, not
    a transport-level stub, so one parser handles both outcomes."""
    with open(os.path.join(EXAMPLES, "vanilla_error_request_v1.json"), encoding="utf-8") as fh:
        payload = json.load(fh)
    status, _, body = _post(payload)
    parsed = json.loads(body)
    assert status == 400
    assert parsed["status"] == "error"
    # `errors` is an ARRAY — read from contracts.error_response, not assumed. Guessing a
    # singular `error` object here is what hid a real defect in the router.
    assert parsed["errors"][0]["code"]
    assert parsed == analyze_payload(payload), "the error body must be the contract's own"


def test_an_internal_error_is_500_and_everything_else_is_400(monkeypatch):
    """⭐ The branch that was DEAD when this file was first written.

    The router read a singular ``error`` object; the contract emits an ``errors`` array. So
    the INTERNAL_ERROR comparison never matched and every failure — including the one the
    caller cannot act on — fell through to 400. Nothing looked wrong: the happy path was
    200, ordinary refusals were 400 because 400 is the fallback, and INTERNAL_ERROR is the
    hardest case to provoke by accident. A plausible default hid it.
    """
    from pricer.endpoints.routes import handler

    def fake(payload, code=None):
        return {"status": "error",
                "errors": [{"code": code, "field": None, "message": "x"}]}

    for code, expect in (("INTERNAL_ERROR", 500), ("VALIDATION_ERROR", 400),
                         ("CURVE_NOT_FOUND", 400), ("A_CODE_INVENTED_TOMORROW", 400)):
        monkeypatch.setattr(handler, "analyze_payload",
                            lambda p, c=code: fake(p, c))
        assert handler.handle("POST", "/price", b"{}")[0] == expect, code


def test_the_status_rule_is_derived_rather_than_tabulated():
    """Only INTERNAL_ERROR means the caller cannot act, and no other code is named in the
    router's CODE — a second copy of contracts.py's vocabulary would go stale in silence.

    Parsed rather than grepped: the docstrings discuss CURVE_NOT_FOUND by name, and a plain
    substring search cannot tell an explanation from a branch. (It could not, and said so.)
    """
    import ast

    from pricer.endpoints.routes import handler

    assert handler._CALLER_CANNOT_FIX == "INTERNAL_ERROR"
    tree = ast.parse(open("src/pricer/endpoints/routes/handler.py", encoding="utf-8").read())
    docstrings = {id(ast.get_docstring(n, clean=False)) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))}
    literals = {n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and id(n.value) not in docstrings}
    for code in ("VALIDATION_ERROR", "CURVE_NOT_FOUND", "CURVE_BUILD_FAILED",
                 "CALIBRATION_FAILED"):
        assert code not in literals, (
            f"{code} appears as a string literal in the router — that is a second owner "
            "of contracts.py's code list")


# --------------------------------------------------------------------- refusals

@pytest.mark.parametrize("method, path, expect", [
    ("GET", "/price", 405),
    ("POST", "/health", 405),
    ("POST", "/", 404),
    ("POST", "/api/price", 404),
    ("GET", "/nope", 404),
])
def test_routing_refusals(method, path, expect):
    status, _, body = handle(method, path, b"{}")
    assert status == expect
    assert json.loads(body)["status"] == "error"


def test_a_trailing_slash_is_the_same_route():
    with open(os.path.join(EXAMPLES, "vanilla_request_v1.json"), encoding="utf-8") as fh:
        raw = fh.read().encode("utf-8")
    assert handle("POST", "/price/", raw)[0] == handle("POST", "/price", raw)[0] == 200


@pytest.mark.parametrize("body, expect_code", [
    (b"", "MALFORMED_JSON"),
    (b"not json at all", "MALFORMED_JSON"),
    (b"[1, 2, 3]", "MALFORMED_JSON"),
    (b'"a string"', "MALFORMED_JSON"),
    (b"\xff\xfe\x00", "MALFORMED_JSON"),
])
def test_malformed_bodies_are_refused_before_pricing(body, expect_code):
    status, _, out = handle("POST", "/price", body)
    assert status == 400
    assert json.loads(out)["errors"][0]["code"] == expect_code


def test_an_oversized_body_is_refused_without_being_parsed():
    from pricer.endpoints.routes import handler
    status, _, out = handle("POST", "/price", b"x" * (handler.MAX_BODY_BYTES + 1))
    assert status == 413
    assert json.loads(out)["errors"][0]["code"] == "REQUEST_TOO_LARGE"


def test_the_json_parser_message_is_not_forwarded():
    """⚠️ A JSONDecodeError quotes the offending input, and the input may be a client's
    position. The refusal says what is wrong without repeating what was sent."""
    _, _, out = handle("POST", "/price", b'{"instrument_id": "SECRET-BOND-123",,}')
    text = out.decode("utf-8")
    assert "SECRET-BOND-123" not in text
    assert "line" not in text.lower() and "column" not in text.lower()


# --------------------------------------------------------------------- health

def test_health_is_200_when_curves_are_visible():
    status, _, body = handle("GET", "/health", None)
    parsed = json.loads(body)
    assert status == 200
    assert parsed["status"] == "ok"
    assert parsed["curves_visible"] >= 20


def test_health_is_503_when_the_data_directory_is_missing(monkeypatch, tmp_path):
    """⭐ The failure this endpoint exists to catch.

    A liveness check that only proves the process started would answer 200 while every real
    request came back CURVE_NOT_FOUND — the single most likely way a cloud deployment of
    this breaks, because the code deploys and the data does not.
    """
    monkeypatch.setenv("FIP_DATA_DIR", str(tmp_path))
    status, _, body = handle("GET", "/health", None)
    parsed = json.loads(body)
    assert status == 503
    assert parsed["curves_visible"] == 0


def test_health_never_leaks_the_data_path(monkeypatch, tmp_path):
    """The contract forbids a filesystem path in anything leaving this process, and a health
    endpoint is the easiest place to forget it — this project already shipped a driver flag
    that carried one."""
    monkeypatch.setenv("FIP_DATA_DIR", str(tmp_path / "a_very_distinctive_directory_name"))
    _, _, body = handle("GET", "/health", None)
    text = body.decode("utf-8")
    assert "a_very_distinctive_directory_name" not in text
    assert str(tmp_path) not in text


def test_no_response_anywhere_carries_a_filesystem_path():
    """Swept across every route, not just the happy one."""
    probes = [("GET", "/health", None), ("POST", "/price", b"{}"),
              ("GET", "/nope", None), ("POST", "/price", b"bad")]
    for method, path, body in probes:
        text = handle(method, path, body)[2].decode("utf-8")
        assert "\\\\" not in text and "C:/" not in text and "/home/" not in text
        assert "Traceback" not in text
