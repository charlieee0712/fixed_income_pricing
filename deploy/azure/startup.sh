#!/usr/bin/env bash
# App Service startup command. Set with a RELATIVE path:
#   az webapp config set --startup-file "bash deploy/azure/startup.sh"
#
# ⚠️⚠️ RELATIVE, AND THAT IS THE WHOLE POINT — an absolute path cost a full round on
# 2026-09-30. Oryx does not leave the built app in /home/site/wwwroot. For a package this
# size it writes ONE FILE, `output.tar.zst`, and the platform's own wrapper extracts it at
# container start into a temporary directory and runs the startup command from THERE. So
# wwwroot contained only:
#
#     .ostype  hostingstart.html  oryx-manifest.toml  output.tar.zst  requirements.txt
#
# — no src/, no data/, no deploy/, no antenv. A startup command pointing at
# /home/site/wwwroot/deploy/azure/startup.sh therefore named a file that did not exist;
# bash exited immediately, App Service restarted it, and the loop presented as six minutes
# of "Starting the site..." followed by "the worker process failed to start within the
# allotted time". The build had in fact succeeded perfectly.
#
# ⚠️ `set -e` is deliberately NOT used. This script's most valuable job is the diagnosis it
# prints when it cannot start, and an early exit would skip it.
set -uo pipefail

# Wherever this file actually is, the app root is two levels up. Works at
# /home/site/wwwroot and equally at /tmp/8dcf1a2b3c4d5e6.
APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$APP_ROOT" || exit 1
echo "startup: app root is $APP_ROOT"

export PYTHONPATH="$APP_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

# ⚠️ FIP_DATA_DIR is set as an app setting to an ABSOLUTE wwwroot path, which is wrong
# whenever the app runs from an extracted directory. Trust the setting only if it points
# somewhere that exists; otherwise compute it from where we actually are. Getting this
# wrong is not fatal and not silent — /health answers 503 and says no curves are visible.
if [[ -z "${FIP_DATA_DIR:-}" || ! -d "${FIP_DATA_DIR:-}" ]]; then
    export FIP_DATA_DIR="$APP_ROOT/data"
fi
echo "startup: data dir $FIP_DATA_DIR ($(ls "$FIP_DATA_DIR" 2>/dev/null | wc -l) files)"

# ⭐ FINDING GUNICORN IS NOT A FORMALITY. Oryx installs into a virtualenv named antenv and
# the platform normally activates it before running the startup command — but the venv can
# sit beside the extracted app OR back in wwwroot, so look in both before giving up.
GUNICORN=""
for cand in "$APP_ROOT/antenv/bin/gunicorn" /home/site/wwwroot/antenv/bin/gunicorn; do
    [[ -x "$cand" ]] && { GUNICORN="$cand"; export PATH="$(dirname "$cand"):$PATH"; break; }
done
[[ -z "$GUNICORN" ]] && GUNICORN="$(command -v gunicorn || true)"

if [[ -z "$GUNICORN" ]]; then
    # ⭐⭐ THE POINT OF THIS BRANCH. Without it the container simply exits, App Service
    # retries for ten minutes and then reports a startup timeout — a message that points
    # at the startup command and says nothing about the cause. These lines turn an
    # undiagnosable timeout into an answer sitting in the container log.
    echo "=====================================================================" >&2
    echo "FATAL: gunicorn not found, so there was nothing to start." >&2
    echo "=====================================================================" >&2
    echo "-- app root ($APP_ROOT):" >&2
    ls -la "$APP_ROOT" 2>&1 | head -30 >&2
    echo "-- wwwroot (if the app is running from somewhere else):" >&2
    ls -la /home/site/wwwroot 2>&1 | head -20 >&2
    echo "-- any antenv?" >&2
    ls -la "$APP_ROOT/antenv/bin" /home/site/wwwroot/antenv/bin 2>&1 | head -20 >&2
    echo "-- python:" >&2
    python3 -V 2>&1 >&2
    exit 1
fi
echo "startup: gunicorn at $GUNICORN"

# ⚠️ $PORT is assigned by the platform and is NOT 8000. Binding a hardcoded port is the
# difference between "the app started" and "the app started and is never reached" — and
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
#   — every worker loads its own numpy, pandas and curve set. FIP_WORKERS=1 if memory is
#   ever the suspect.
# --timeout 300, not the 30s default: the FIRST request on a cold worker imports pandas and
#   bootstraps a curve. A 30s timeout kills it mid-import and the client sees a 502 that
#   never recurs, which is the least debuggable failure available.
