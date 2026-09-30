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

  # ⚠️⚠️ AUTHENTICATION GOES ON BEFORE ANY DATA DOES, and this ordering is the point of
  # putting it here rather than in a checklist. The app carries the client's portfolio and
  # the engine has no authentication of its own -- endpoints/__init__ says so in as many
  # words. Easy Auth is the platform's, so we ship no hand-rolled auth and "everyone with
  # authorized access" becomes a membership list in Entra ID rather than a secret in a
  # config file.
  echo "enabling Entra ID authentication (unauthenticated requests -> 401)..."
  az webapp auth microsoft update -g "$RG" -n "$APP" \
     --allowed-audiences "api://$APP" -o none 2>/dev/null || true
  az webapp auth update -g "$RG" -n "$APP" \
     --enabled true \
     --action Return401 \
     --redirect-provider AzureActiveDirectory -o none
fi

# ------------------------------------------------------------------ 2. settings
az webapp config appsettings set -g "$RG" -n "$APP" -o none --settings \
  PYTHONPATH=/home/site/wwwroot/src \
  FIP_DATA_DIR=/home/site/wwwroot/data \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  WEBSITES_CONTAINER_START_TIME_LIMIT=600
# PYTHONPATH   so gunicorn can import pricer.* without --chdir
# FIP_DATA_DIR ABSOLUTE. A relative "data" resolves against the worker's cwd, which is not
#              guaranteed to be wwwroot; the failure mode is a 503 from /health, which is
#              at least the one we built a probe for.
# SCM_DO_BUILD ... = Oryx runs pip install against the requirements.txt in the package root
# START_TIME_LIMIT the first boot installs numpy/pandas/scipy; the 230s default is not
#              always enough and the container is killed with no useful message.

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
az webapp deploy -g "$RG" -n "$APP" --src-path "$STAGE/app.zip" --type zip -o none

# ------------------------------------------------------------------ 4. the gate
URL="https://${APP}.azurewebsites.net"
cat <<MSG

deployed -> $URL

⚠️ NOT DONE YET. A deployment that returns 200 has proved nothing; this one has the
client's data behind it and has to reproduce the committed numbers. Run the gate:

    TOKEN=\$(az account get-access-token --resource "api://$APP" --query accessToken -o tsv)
    PYTHONPATH=src python scripts/remote_smoke.py "$URL" --token "\$TOKEN"

It checks /health for visible curve files first (the code shipping without the data is the
likeliest failure), then prices all 11 shipped fixtures and compares every field against
what this machine computes -- strings identical, numbers inside their own per-quantity
tolerance. It EXITS NONZERO if anything disagrees. Until it prints PASS, the service is
not deployed, it is merely running.

Logs, if it does not come up:   az webapp log tail -g $RG -n $APP
MSG
