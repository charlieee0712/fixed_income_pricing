#!/usr/bin/env bash
# App Service startup command. Set with:
#   az webapp config set --startup-file "bash /home/site/wwwroot/deploy/azure/startup.sh"
#
# ⚠️ `set -e` is deliberately NOT used. This script's most valuable job is the diagnosis it
# prints when it cannot start, and an early exit would skip it.
set -uo pipefail

ROOT=/home/site/wwwroot
VENV="$ROOT/antenv"

# ⭐ FINDING GUNICORN IS NOT A FORMALITY, it is where this failed twice on 2026-09-30.
# Oryx installs dependencies into a virtualenv at $ROOT/antenv and its own generated
# startup script activates it first. A CUSTOM startup command does not reliably inherit
# that PATH, so a bare `gunicorn` can be missing even when the build worked perfectly.
if [[ -x "$VENV/bin/gunicorn" ]]; then
    export PATH="$VENV/bin:$PATH"
    export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"
    GUNICORN="$VENV/bin/gunicorn"
    echo "startup: using the Oryx virtualenv at $VENV"
elif command -v gunicorn >/dev/null 2>&1; then
    GUNICORN="$(command -v gunicorn)"
    echo "startup: using gunicorn on PATH at $GUNICORN (no antenv found)"
else
    # ⭐⭐ THE POINT OF THIS BRANCH. Without it the container simply exits, App Service
    # retries it for ten minutes and then reports "the worker process failed to start
    # within the allotted time" -- which points at the startup command and says nothing
    # about the cause. These fifteen lines turn an undiagnosable timeout into an answer
    # sitting in the container log.
    echo "=====================================================================" >&2
    echo "FATAL: gunicorn is not installed, so there was nothing to start." >&2
    echo "The Oryx build did not run. Everything below is evidence for why." >&2
    echo "=====================================================================" >&2
    echo "-- is there a virtualenv?" >&2
    ls -la "$VENV/bin" 2>&1 | head -20 >&2 || echo "   no $VENV at all" >&2
    echo "-- what is in wwwroot? (requirements.txt MUST be at this level)" >&2
    ls -la "$ROOT" 2>&1 | head -30 >&2
    echo "-- requirements.txt, if it is there:" >&2
    head -20 "$ROOT/requirements.txt" 2>&1 >&2 || echo "   ABSENT -- Oryx had nothing to detect" >&2
    echo "-- python and pip:" >&2
    python3 -V 2>&1 >&2; python3 -m pip --version 2>&1 >&2
    exit 1
fi

# ⚠️ $PORT is assigned by the platform and is NOT 8000. Binding a hardcoded port is the
# difference between "the app started" and "the app started and is never reached" -- and
# the logs look healthy either way.
echo "startup: binding 0.0.0.0:${PORT:-8000} with ${FIP_WORKERS:-2} worker(s)"
exec "$GUNICORN" \
    --bind="0.0.0.0:${PORT:-8000}" \
    --workers="${FIP_WORKERS:-2}" \
    --timeout=300 \
    --access-logfile=- \
    --error-logfile=- \
    pricer.endpoints.routes.wsgi:application

# --workers 2, not 1: each worker is an independent process, so N of them are exactly the
#   parallel execution Mario's browser front end wants. Not more than 2 on a B1 (1.75 GB)
#   -- every worker loads its own numpy, pandas and curve set. FIP_WORKERS=1 if memory is
#   ever the suspect.
# --timeout 300, not the 30s default: the FIRST request on a cold worker imports pandas and
#   bootstraps a curve. A 30s timeout kills it mid-import and the client sees a 502 that
#   never recurs, which is the least debuggable failure available.
# PYTHONPATH reaches src/ via an app setting, and is re-exported above as a belt-and-braces
#   in case the custom startup command did not inherit the app settings either.
