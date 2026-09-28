"""Serve the pricing endpoint over HTTP on this machine, with the standard library only.

    PYTHONPATH=src python scripts/serve_local.py
    curl -s -X POST localhost:8000/price \
         --data-binary @integrations/excel_vba/examples/vanilla_request_v1.json
    curl -s localhost:8000/health

⭐ **This exists to prove the HTTP layer changes no number, before any of it touches Azure.**
It adds no dependency, so it can be run by anyone who can already run the tests, and it
carries exactly the same routing and status-code rule the cloud adapters will
(``pricer.endpoints.routes.handle`` — this file is a socket and nothing more).

⚠️ **Not a production server, and the standard library says so itself.** ``http.server`` is
single-threaded and has no timeouts, no request limits beyond the one the handler applies,
and no TLS. On Azure this is replaced by the platform's own worker — gunicorn behind an App
Service, or the Functions host — calling the same ``handle``. What it IS good for is being
the thing a test can start in-process and a colleague can curl in one command.

⚠️ **Binds 127.0.0.1 by default**, so it is not reachable from the network. ``--host 0.0.0.0``
is deliberate rather than default: this endpoint has no authentication yet, and the cost of
getting that wrong is a pricing service for the whole network to enjoy.
"""
from __future__ import annotations

import argparse
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

sys.path.insert(0, "src")

from pricer.endpoints.routes import handle  # noqa: E402

#: Azure App Service tells a container which port to listen on this way; honouring it costs
#: one line and is the difference between "starts" and "starts and is never reached".
PORT_ENV = "PORT"


class _Handler(BaseHTTPRequestHandler):
    server_version = "ryse-pricing/1.0"
    protocol_version = "HTTP/1.1"

    def _run(self, method: str):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        status, headers, payload = handle(method, urlsplit(self.path).path, body)
        self.send_response(status)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        self._run("POST")

    def do_GET(self):
        self._run("GET")

    def log_message(self, fmt, *args):
        # The default logs the full request line. A query string could carry request
        # content, and this project's contract keeps client data out of anything emitted.
        sys.stderr.write("%s %s %s\n" % (self.command, urlsplit(self.path).path, args[1]
                                         if len(args) > 1 else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--host", default="127.0.0.1",
                    help="0.0.0.0 to accept from the network (no auth yet — be deliberate)")
    ap.add_argument("--port", type=int, default=int(os.environ.get(PORT_ENV, 8000)))
    args = ap.parse_args()

    srv = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(f"serving on http://{args.host}:{args.port}   "
          f"POST /price   GET /health   (data dir: "
          f"{os.environ.get('FIP_DATA_DIR', 'data')})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
