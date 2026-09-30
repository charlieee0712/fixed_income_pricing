#!/usr/bin/env bash
# Stand up (or update) the pricing service on Azure App Service. Run from the repo root:
#
#     bash deploy/azure/deploy.sh
#     bash deploy/azure/deploy.sh --no-create      # code only, infrastructure untouched
#
# ⭐ THIS SCRIPT IS THE DEPLOYMENT. There is no second set of steps anybody has to
# remember. Liping's account of her own Web App was "something in the settings was stuck,
# I tried a few times and it inexplicably started working" -- which is the honest
# description of a portal-clicked deployment, and it is exactly what will happen again in
# front of Mario's group if the setup is not a file. Every value that matters is below,
# every one has a comment saying why, and running it twice is safe.
#
# Requires: az CLI, and `az login` already done. Nothing else.
set -euo pipefail

# ------------------------------------------------------------------ what gets created
# ⚠️ This is billed to Mario's card (Lichen's account, confirmed 2026-09-29). B1 Basic is
# about USD 13/month and is the cheapest tier with an always-on option -- the Free tier
# unloads the worker after 20 minutes, so the first request of the day would take a minute
# and Mario's team would conclude the service is broken. If cost matters more than that
# first impression, F1 works and this is the single line to change.
RG="${FIP_RG:-ryse-pricing}"
LOCATION="${FIP_LOCATION:-southeastasia}"   # matches the Cloud Shell region already in use
PLAN="${FIP_PLAN:-ryse-pricing-plan}"
SKU="${FIP_SKU:-B1}"
APP="${FIP_APP:?set FIP_APP to a globally-unique name, e.g. ryse-pricing-urs}"
RUNTIME="${FIP_RUNTIME:-PYTHON:3.12}"       # 3.12 is what Cloud Shell ran 495 tests on

CREATE=1
[[ "${1:-}" == "--no-create" ]] && CREATE=0

echo "app=$APP  rg=$RG  plan=$PLAN($SKU)  region=$LOCATION  runtime=$RUNTIME"

# ------------------------------------------------------------------ 1. infrastructure
if [[ $CREATE -eq 1 ]]; then
  az group create -n "$RG" -l "$LOCATION" -o none
  az appservice plan create -g "$RG" -n "$PLAN" --sku "$SKU" --is-linux -o none
  az webapp create -g "$RG" -p "$PLAN" -n "$APP" --runtime "$RUNTIME" -o none

  # ⚠️⚠️ THE DOOR IS SHUT BEFORE ANY DATA GOES IN, and the ordering is the point of putting
  # it here rather than in a checklist. The app carries the client's portfolio and the
  # engine has no authentication of its own -- endpoints/__init__ says so in as many words.
  #
  # ⚠️ IT IS AN IP RESTRICTION, NOT ENTRA, AND THAT IS A CORRECTION (2026-09-29).
  # The first version of this script enabled Easy Auth here with `--action Return401` and
  # no identity provider configured. That is not "locked", it is "walled up": every request
  # 401s including our own gate, and no token can be obtained because no application is
  # registered to issue one. The `az webapp auth microsoft update` line above it carried
  # `2>/dev/null || true`, so the half that would have said so failed in silence -- a guard
  # that hid the error it was guarding against.
  #
  # ⭐ Entra is still where this ends up; it is just not a prerequisite for finding out
  # whether the app runs. `deploy/azure/enable_entra_auth.sh` does it properly, after the
  # gate is green. An IP allow-rule needs no app registration, no consent and no token, and
  # App Service appends an implicit "deny all" as soon as one Allow rule exists.
  :
fi

# ------------------------------------------------------------------ 1b. the door
# ⚠️ OUTSIDE the create block, and that placement is the point. Cloud Shell's egress IP
# CHANGES between sessions, so this is not a one-time setup step -- it is something every
# run has to refresh, and a later 403 means "new session, new IP", not "the app broke".
# Having it inside `if CREATE` meant a --no-create run silently left the previous session's
# address allowed and this one locked out.
MYIP="$(curl -fsS https://api.ipify.org || true)"
if [[ -z "$MYIP" ]]; then
  echo "REFUSING to continue: could not determine this machine's public IP, and the" >&2
  echo "alternative is publishing a pricing service with client data and no door." >&2
  exit 1
fi
echo "restricting access to $MYIP (implicit deny-all for everyone else)..."
# Idempotent: drop the previous rule if present, then add. `|| true` is safe HERE and only
# here -- a missing rule is the expected state on a first run, not a hidden failure.
az webapp config access-restriction remove -g "$RG" -n "$APP" \
   --rule-name allow-deployer -o none 2>/dev/null || true
az webapp config access-restriction add -g "$RG" -n "$APP" \
   --rule-name allow-deployer --priority 100 --action Allow \
   --ip-address "$MYIP/32" -o none
# `--scm-site` left at its default, so the deployment endpoint stays reachable.

# ------------------------------------------------------------------ 2. settings
az webapp config appsettings set -g "$RG" -n "$APP" -o none --settings \
  PYTHONPATH=/home/site/wwwroot/src \
  FIP_DATA_DIR=/home/site/wwwroot/data \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  ENABLE_ORYX_BUILD=true \
  WEBSITES_CONTAINER_START_TIME_LIMIT=900
# PYTHONPATH   so gunicorn can import pricer.* without --chdir
# FIP_DATA_DIR ABSOLUTE. A relative "data" resolves against the worker's cwd, which is not
#              guaranteed to be wwwroot; the failure mode is a 503 from /health, which is
#              at least the one we built a probe for.
# SCM_DO_BUILD + ENABLE_ORYX_BUILD  ⚠️ BOTH, and the second was missing on 2026-09-30.
#              With only the first, `az webapp deploy --type zip` skips pip ENTIRELY,
#              reports "Build successful" in about ONE SECOND, and the container then
#              spends ten minutes failing to find gunicorn. Nothing in that sequence says
#              "no dependencies were installed" — the deployment reports success and the
#              site reports a startup timeout, which points at the startup command.
# START_TIME_LIMIT  900, up from 600: the first boot compiles nothing but does download and
#              install numpy, pandas and scipy. 615s was not enough on a B1.

# ⭐ READ IT BACK. An app setting that did not apply is invisible, and this project's own
# rule is to schedule a gate check rather than assert state. The cost of skipping this was
# the ten-minute failure above.
for want in SCM_DO_BUILD_DURING_DEPLOYMENT ENABLE_ORYX_BUILD; do
  got="$(az webapp config appsettings list -g "$RG" -n "$APP" \
         --query "[?name=='$want'].value|[0]" -o tsv)"
  [[ "$got" == "true" ]] || { echo "REFUSING to deploy: $want reads '$got', not true. " \
     "Oryx would skip pip and the container would fail to start." >&2; exit 1; }
done
echo "build settings verified"

az webapp config set -g "$RG" -n "$APP" -o none \
  --startup-file "bash /home/site/wwwroot/deploy/azure/startup.sh"

# ------------------------------------------------------------------ 3. package
# Staged rather than zipping the repo: the pinned requirements must land at the package
# ROOT, because that is the only one Oryx reads.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
echo "staging into $STAGE ..."
for d in src data scripts deploy integrations tests; do
  [[ -d "$d" ]] && cp -r "$d" "$STAGE/"
done
cp deploy/azure/requirements.txt "$STAGE/requirements.txt"     # the PINNED one, at the root
cp pytest.ini conftest.py "$STAGE/" 2>/dev/null || true
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$STAGE" -name '.pytest_cache' -type d -prune -exec rm -rf {} + 2>/dev/null || true
echo "package: $(du -sh "$STAGE" | cut -f1)"

( cd "$STAGE" && zip -qr app.zip . )
echo "deploying — the FIRST build installs numpy/pandas/scipy and takes several minutes."
echo "⚠️ If this reports 'Build successful' in about a second, the build did NOT run."
az webapp deploy -g "$RG" -n "$APP" --src-path "$STAGE/app.zip" --type zip -o none

# ⭐ The platform's own verdict is not the one that matters. Poll until the app answers, so
# a failure here is "it never came up" rather than a green deployment and a dead URL.
echo "waiting for the app to answer /health ..."
for i in $(seq 1 60); do
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 \
          "https://${APP}.azurewebsites.net/health" || true)"
  case "$code" in
    200) echo "  /health -> 200 after ~$((i*10))s"; break ;;
    503) echo "  /health -> 503: it is RUNNING but sees no curve files — the code shipped"
         echo "  and the data did not. Check FIP_DATA_DIR."; break ;;
    403) echo "  /health -> 403: the IP allow-rule does not include this machine."
         echo "  Cloud Shell's egress IP changes between sessions; re-add the rule."; break ;;
    *)   printf '  %ss: %s\r' "$((i*10))" "${code:-no answer}"; sleep 10 ;;
  esac
done
echo

# ------------------------------------------------------------------ 4. the gate
URL="https://${APP}.azurewebsites.net"
cat <<MSG

deployed -> $URL

⚠️ NOT DONE YET. A deployment that returns 200 has proved nothing; this one has the
client's data behind it and has to reproduce the committed numbers. Run the gate:

    PYTHONPATH=src python scripts/remote_smoke.py "$URL"

No token: access is currently an IP allow-rule for this machine only, so the gate runs
as itself. Entra comes after this passes -- deploy/azure/enable_entra_auth.sh, which is
also what turns "authorized access" into a membership list Mario's team can be added to.

It checks /health for visible curve files first (the code shipping without the data is the
likeliest failure), then prices all 11 shipped fixtures and compares every field against
what this machine computes -- strings identical, numbers inside their own per-quantity
tolerance. It EXITS NONZERO if anything disagrees. Until it prints PASS, the service is
not deployed, it is merely running.

Logs, if it does not come up:   az webapp log tail -g $RG -n $APP
MSG
