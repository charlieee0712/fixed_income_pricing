"""WSGI adapter — the Azure App Service entry point (option B).

    gunicorn --chdir src pricer.endpoints.routes.wsgi:application

``routes/__init__`` said adapters belong beside ``handler.py``, each "doing nothing but
translating its host's request object into the three arguments above and its response back
out". This is that file for WSGI, which is what an Azure Web App speaks.

⭐ **It is deliberately boring, and boring is the specification.** The whole value of the
framework-free ``handle()`` is that no host gets to have an opinion about a number, so the
only correct adapter is one that adds nothing. ``tests/test_wsgi_adapter.py`` asserts the
bytes out of here equal the bytes out of ``handle()`` for every shipped fixture — if that
ever fails, the transport has started thinking.

⚠️ **gunicorn is a dependency of the DEPLOYMENT, not of the engine.** Nothing under
``src/pricer`` imports it, this file included; it is the platform's worker calling a plain
callable. ``scripts/serve_local.py`` reaches the same ``handle()`` through the standard
library, and the two must agree.

⚠️ **THIS FILE PROVIDES NO AUTHENTICATION.** It is a pricing service with the client's
portfolio on disk beside it. Authentication is App Service's own (Easy Auth / Entra ID),
configured at the platform before the app is reachable — see ``deploy/azure/README.md``.
Putting it in the platform rather than in code is the deliberate choice: we ship no
hand-rolled auth, and "everyone with authorized access" becomes a membership list rather
than a secret in a config file.
"""
from __future__ import annotations

import json
from http import HTTPStatus

from pricer.endpoints.routes.handler import MAX_BODY_BYTES, handle

#: Read at most one byte beyond the limit. ``handle`` refuses anything larger, but it can
#: only refuse what has already been buffered — reading the declared Content-Length would
#: let a client make us hold a gigabyte in memory before we decline it.
_READ_CAP = MAX_BODY_BYTES + 1

#: Returned when something escapes ``handle``, which its docstring says cannot happen.
#: ⚠️ Kept anyway: if it ever does, the WSGI server's default 500 page carries a Python
#: traceback, and the contract forbids a traceback or a filesystem path in anything leaving
#: this process. The cost of the guard is six lines; the cost of being wrong is a stack
#: trace on a public URL with a client portfolio behind it.
_LAST_RESORT = json.dumps({
    "status": "error",
    "errors": [{"code": "INTERNAL_ERROR", "field": None,
                "message": "the service failed to produce a response"}],
}).encode("utf-8")


def _read_body(environ) -> bytes | None:
    """The request body, capped, tolerating a missing or chunked Content-Length."""
    stream = environ.get("wsgi.input")
    if stream is None:
        return None
    raw = environ.get("CONTENT_LENGTH")
    try:
        declared = int(raw) if raw else 0
    except ValueError:                      # a malformed header is not a reason to crash
        declared = 0
    if declared > 0:
        return stream.read(min(declared, _READ_CAP))
    # ⚠️ No Content-Length. Under chunked transfer the server sets `wsgi.input_terminated`
    # and read() ends at EOF; without that flag read() would block forever waiting for a
    # body that is not coming, so an absent length means an absent body.
    if environ.get("wsgi.input_terminated"):
        return stream.read(_READ_CAP)
    return None


def application(environ, start_response):
    """The WSGI callable. Inputs: the WSGI environ and start_response. Returns: an iterable
    of one bytes chunk — the same bytes ``handle()`` returns for the same request."""
    try:
        status, headers, body = handle(
            environ.get("REQUEST_METHOD", "GET"),
            environ.get("PATH_INFO", "/"),        # query string is PATH_INFO-free in WSGI
            _read_body(environ),
        )
    except Exception:                             # noqa: BLE001 — see _LAST_RESORT
        status, headers, body = 500, {"Content-Type": "application/json; charset=utf-8"}, \
            _LAST_RESORT

    try:
        phrase = HTTPStatus(status).phrase
    except ValueError:
        phrase = ""
    out = list(headers.items()) + [("Content-Length", str(len(body)))]
    start_response(f"{status} {phrase}".strip(), out)
    return [body]


#: Some hosts look for ``app``; both names are the same object so neither can drift.
app = application
