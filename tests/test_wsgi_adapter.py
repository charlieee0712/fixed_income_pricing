"""Locks for the WSGI adapter (2026-09-29) — the Azure App Service entry point.

The adapter's job is to add nothing. So the load-bearing test is the same one the HTTP
layer has: **the bytes a WSGI host sends equal the bytes ``handle()`` returns**, for every
shipped fixture. Everything else here is about the ways a real host differs from a tidy
function call — a missing Content-Length, a chunked body, a header a client got wrong —
none of which should be able to change a number or leak a traceback.

Driven through ``wsgiref.util.setup_testing_defaults`` and a captured ``start_response``,
so no server is started and these run in the ordinary suite.
"""
import io
import json
import os
from wsgiref.util import setup_testing_defaults

import pytest

from pricer.endpoints.routes import handle
from pricer.endpoints.routes.wsgi import application

EXAMPLES = "integrations/excel_vba/examples"
REQUESTS = sorted(f for f in os.listdir(EXAMPLES)
                  if f.endswith(("_request_v1.json", "_request_v1_1.json")))


class _Capture:
    def __init__(self):
        self.status = None
        self.headers = None

    def __call__(self, status, headers):
        self.status, self.headers = status, headers


def _call(method="POST", path="/price", body=b"", *, length=True, terminated=False):
    environ = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path
    environ["wsgi.input"] = io.BytesIO(body)
    if length:
        environ["CONTENT_LENGTH"] = str(len(body))
    else:
        environ.pop("CONTENT_LENGTH", None)
        if terminated:
            environ["wsgi.input_terminated"] = True
    cap = _Capture()
    chunks = application(environ, cap)
    return cap, b"".join(chunks)


# ------------------------------------------------------------------ the load-bearing one

@pytest.mark.parametrize("name", REQUESTS)
def test_wsgi_returns_exactly_what_handle_returns(name):
    """⭐ Transport, not translation — asserted on the raw BYTES, not the decoded object.

    A re-serialisation that reordered keys would pass an ``==`` on dicts and still break
    any consumer diffing two responses.
    """
    raw = open(os.path.join(EXAMPLES, name), "rb").read()
    cap, body = _call(body=raw)
    direct_status, _, direct_body = handle("POST", "/price", raw)

    assert body == direct_body
    assert cap.status.startswith(str(direct_status))


def test_every_shipped_fixture_is_exercised():
    """A parametrized test over a glob that matched nothing passes silently — this project
    has shipped that failure twice."""
    assert len(REQUESTS) >= 9, f"only found {len(REQUESTS)} request fixtures"


# ------------------------------------------------------------------ host-shaped edge cases

def test_the_status_line_carries_a_reason_phrase():
    cap, _ = _call(method="GET", path="/health", body=b"")
    assert cap.status in ("200 OK", "503 Service Unavailable")


def test_content_length_header_matches_the_body_sent():
    """A wrong Content-Length truncates the response in the client, not in any log."""
    cap, body = _call(method="GET", path="/health", body=b"")
    sent = dict(cap.headers)
    assert int(sent["Content-Length"]) == len(body)


def test_a_missing_content_length_is_an_empty_body_not_a_hang():
    """⚠️ Without the guard, ``read()`` on a non-terminated stream blocks forever waiting
    for a body that is not coming. An empty body is a clean 400, which is the right answer
    to a POST with nothing in it."""
    cap, body = _call(body=b'{"x":1}', length=False)
    assert cap.status.startswith("400")
    assert json.loads(body)["errors"][0]["code"] == "MALFORMED_JSON"


def test_a_chunked_body_is_read_when_the_server_says_it_is_terminated():
    raw = open(os.path.join(EXAMPLES, "vanilla_request_v1.json"), "rb").read()
    cap, body = _call(body=raw, length=False, terminated=True)
    assert cap.status.startswith("200")
    assert body == handle("POST", "/price", raw)[2]


def test_a_malformed_content_length_does_not_crash():
    environ = {}
    setup_testing_defaults(environ)
    environ.update(REQUEST_METHOD="POST", PATH_INFO="/price",
                   CONTENT_LENGTH="not-a-number", **{"wsgi.input": io.BytesIO(b"{}")})
    cap = _Capture()
    body = b"".join(application(environ, cap))
    assert cap.status.startswith("400")
    assert b"Traceback" not in body


def test_an_oversized_body_is_not_fully_buffered():
    """⭐ The cap is on the READ, not on the declared length. Reading Content-Length would
    let a client make us hold the whole thing in memory before declining it."""
    huge = b"x" * (2 * 1024 * 1024)
    cap, body = _call(body=huge)
    assert cap.status.startswith("413")
    assert json.loads(body)["errors"][0]["code"] == "REQUEST_TOO_LARGE"


# ------------------------------------------------------------------ the last-resort guard

def test_an_escaping_exception_becomes_a_clean_contract_error(monkeypatch):
    """⚠️ ``handle`` says it never raises. This asserts what happens if that is ever
    untrue, because the WSGI server's own 500 page carries a Python traceback and the
    contract forbids a traceback or a path in anything leaving this process.

    Mutation-checked: remove the try/except in wsgi.py and this test errors out rather
    than failing politely, which is the signature of a real escape.
    """
    from pricer.endpoints.routes import wsgi

    def boom(*a, **k):
        raise RuntimeError(r"C:\Users\cnc\fixed_income_pricing\data\secret.txt")

    monkeypatch.setattr(wsgi, "handle", boom)
    cap, body = _call(body=b"{}")
    text = body.decode()
    assert cap.status.startswith("500")
    assert json.loads(body)["errors"][0]["code"] == "INTERNAL_ERROR"
    assert "Traceback" not in text and "secret.txt" not in text and "C:" not in text


def test_the_adapter_imports_no_web_framework():
    """⭐ gunicorn is the deployment's dependency, not the engine's. If this file ever
    imports a framework, the host has started reaching into the contract."""
    import ast
    tree = ast.parse(open("src/pricer/endpoints/routes/wsgi.py", encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported & {"flask", "fastapi", "django", "starlette", "gunicorn",
                            "werkzeug", "uvicorn"}), sorted(imported)


def test_app_and_application_are_the_same_object():
    """Two names, one object — so a host picking either cannot get a stale one."""
    from pricer.endpoints.routes import wsgi
    assert wsgi.app is wsgi.application
