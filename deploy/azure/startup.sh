#!/usr/bin/env bash
# App Service startup command. Set with:
#   az webapp config set --startup-file "bash /home/site/wwwroot/deploy/azure/startup.sh"
set -euo pipefail

# ⚠️ $PORT is assigned by the platform and is NOT 8000. Binding a hardcoded port is the
# difference between "the app started" and "the app started and is never reached" -- and
# the logs look healthy either way.
exec gunicorn \
    --bind="0.0.0.0:${PORT:-8000}" \
    --workers="${FIP_WORKERS:-2}" \
    --timeout=300 \
    --access-logfile=- \
    --error-logfile=- \
    pricer.endpoints.routes.wsgi:application

# --workers 2, not 1: each worker is an independent process, so N of them are exactly the
#   parallel execution Mario's browser front end wants. Not more than 2 on a B1 (1.75 GB)
#   -- every worker loads its own numpy, pandas and curve set.
# --timeout 300, not the 30s default: the FIRST request on a cold worker imports pandas and
#   bootstraps a curve. A 30s timeout kills it mid-import and the client sees a 502 that
#   never recurs, which is the least debuggable failure available.
# PYTHONPATH reaches src/ via an app setting rather than --chdir, so the process still runs
#   from wwwroot and the default relative data directory resolves.
