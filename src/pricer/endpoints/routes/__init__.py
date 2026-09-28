"""HTTP routes (template: ``endpoints/routes/``) — the folder the interface reserved.

``endpoints/__init__.py`` said this arrives with the service. It has arrived, and it is
deliberately the thinnest thing that could work:

    handler.py   handle(method, path, body) -> (status, headers, body). NO framework, NO
                 third-party import, no I/O of its own beyond what analyze_payload does.

⭐ **Framework-free on purpose, and the purpose is not minimalism.** Liping is on an Azure
Web App; a Function App is also on the table; a local runner is what we test against today.
Each of those wants a different entry signature, and none of them should be allowed to reach
into the pricing contract. So the routing and the status-code rule live in one pure function
that any of them can call in ten lines, and the choice of host stays a deployment decision
rather than a code decision.

Adapters, when they are written, belong beside this file — ``flask_app.py``,
``function_app.py`` — each doing nothing but translating its host's request object into the
three arguments above and its response back out.

⚠️ **There is no CORS here and no authentication.** A browser calling this from another
origin WILL be refused by the browser, and nothing in the response explains why — the
request never reaches the server. That is the next piece of work, not an oversight, and it
is written here because a JavaScript front end hitting it will otherwise look broken for a
reason nobody can see in the logs.
"""
from pricer.endpoints.routes.handler import handle  # noqa: F401

__all__ = ["handle"]
