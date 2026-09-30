#!/usr/bin/env bash
# Put Entra ID authentication in front of the pricing service — phase 2.
#
#     export FIP_APP=ryse-pricing-urs
#     bash deploy/azure/enable_entra_auth.sh
#
# ⭐ RUN THIS ONLY AFTER scripts/remote_smoke.py PRINTS PASS. Authentication is not what
# makes a deployment correct, and putting it first cost us a round: the first version of
# deploy.sh enabled Easy Auth with `--action Return401` and no identity provider, which is
# not a locked door but a walled-up one — every request 401s, ours included, and no token
# can be obtained because no application exists to issue one.
#
# ⚠️ WHY IT IS THREE COMMANDS AND NOT ONE. Easy Auth does not create its own app
# registration from the CLI; the portal's "create new app registration" button has no flag
# equivalent. The registration, the identifier URI and the provider wiring are separate
# objects, and a failure in any one of them leaves the app in a state that looks enabled.
# So: no `|| true` anywhere in this file. If a step fails, everything stops, with the app
# still reachable behind its IP rule.
set -euo pipefail

RG="${FIP_RG:-ryse-pricing}"
APP="${FIP_APP:?set FIP_APP, e.g. ryse-pricing-urs}"

TENANT="$(az account show --query tenantId -o tsv)"
echo "tenant : $TENANT"

# ---------------------------------------------------------------- 1. the registration
# Reused if it already exists, so this script is safe to run twice.
APP_ID="$(az ad app list --display-name "$APP" --query "[0].appId" -o tsv)"
if [[ -z "$APP_ID" || "$APP_ID" == "None" ]]; then
  echo "creating the Entra application registration..."
  APP_ID="$(az ad app create --display-name "$APP" --sign-in-audience AzureADMyOrg \
            --query appId -o tsv)"
fi
echo "app id : $APP_ID"

# ⚠️ The identifier URI is api://<APP_ID>, NOT api://<name>. A name-based URI needs a
# verified domain; the appId form is accepted unconditionally, and it is the audience the
# token has to carry. Getting this wrong produces AADSTS500011 ("resource principal not
# found") at token time, which reads like a permissions problem and is not one.
az ad app update --id "$APP_ID" --identifier-uris "api://$APP_ID"

# ---------------------------------------------------------------- 2. wire the provider
echo "wiring Easy Auth to that registration..."
az webapp auth microsoft update -g "$RG" -n "$APP" \
   --client-id "$APP_ID" \
   --issuer "https://sts.windows.net/$TENANT/" \
   --allowed-audiences "api://$APP_ID" \
   --yes -o none

# ---------------------------------------------------------------- 3. turn it on
# ⚠️ Return401, never the login redirect. This is an API: answering POST /price with an
# HTML sign-in page gives a caller a 200 full of markup where it expected JSON, which is
# far harder to diagnose than a 401.
az webapp auth update -g "$RG" -n "$APP" \
   --enabled true \
   --unauthenticated-client-action Return401 \
   --redirect-provider AzureActiveDirectory -o none

URL="https://${APP}.azurewebsites.net"
cat <<MSG

authentication ON. Everything below the platform is unchanged — no line of engine code
knows this happened, which is the point of using the platform's auth rather than our own.

Re-run the gate WITH a token, and confirm it still passes:

    TOKEN=\$(az account get-access-token --resource "api://$APP_ID" --query accessToken -o tsv)
    PYTHONPATH=src python scripts/remote_smoke.py "$URL" --token "\$TOKEN"

⭐ And confirm the door is actually shut, which the gate cannot tell you:

    curl -s -o /dev/null -w '%{http_code}\\n' "$URL/health"     # expect 401

Adding someone (this is what "everyone with authorized access" now means — a membership
list, not a secret in a config file):

    az ad app owner add --id $APP_ID --owner-object-id <their-object-id>
    # then assign them to the app in Entra ID > Enterprise applications > $APP

⚠️ The IP allow-rule from deploy.sh is still in place and is now redundant. Leave it while
testing; remove it when Mario's team needs in from their own networks:

    az webapp config access-restriction remove -g $RG -n $APP --rule-name allow-deployer
MSG
