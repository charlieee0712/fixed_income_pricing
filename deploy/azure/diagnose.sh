#!/usr/bin/env bash
# Everything needed to say WHY the app is not serving, in one command.
#
#     bash deploy/azure/diagnose.sh
#
# ⭐ This is a repo script rather than a block of commands to paste because the Cloud Shell
# browser terminal mangles multi-line pastes — it has now done so twice in this project,
# once concatenating a flag onto a variable and once inserting a literal `\ne`. One line in,
# everything out.
#
# ⚠️ `set -e` is deliberately OFF. A diagnostic that stops at its first failing probe tells
# you the least at the moment you need the most; every check runs and reports.
set -uo pipefail

RG="${FIP_RG:-ryse-pricing}"
APP="${FIP_APP:?set FIP_APP, e.g. ryse-pricing-urs}"
say() { printf '\n=== %s\n' "$1"; }

say "1. app settings — the build turns on here, and 'Build successful, 1s' means it did not"
# SCM_DO_BUILD_DURING_DEPLOYMENT and ENABLE_ORYX_BUILD must BOTH read true. Either one
# missing and Oryx skips pip entirely, the deployment still reports success in about a
# second, and the container then dies looking for gunicorn.
az webapp config appsettings list -g "$RG" -n "$APP" \
   --query "[?contains(name,'SCM')||contains(name,'ORYX')||contains(name,'PYTHON')||contains(name,'FIP')||contains(name,'WEBSITE')].{setting:name,value:value}" \
   -o table

say "2. startup command and runtime"
az webapp config show -g "$RG" -n "$APP" \
   --query "{startup:appCommandLine, runtime:linuxFxVersion, alwaysOn:alwaysOn}" -o json

say "3. what actually landed in wwwroot"
# ⭐ The decisive check. `antenv` is the virtualenv Oryx creates; if it is ABSENT, no
# dependencies were installed and everything else below is a consequence, not a cause.
# ⚠️ A BEARER TOKEN, not publishing credentials. Azure now disables SCM basic
# authentication by DEFAULT on new apps, so `list-publishing-credentials` hands back
# something Kudu then rejects with a flat 401 — which is what happened on the first run
# of this script, costing us the one check that decides the question. Kudu accepts an
# Entra token and every Cloud Shell already holds one.
TOKEN="$(az account get-access-token --resource https://management.core.windows.net/ \
         --query accessToken -o tsv 2>/dev/null)"
if [[ -n "$TOKEN" ]]; then
  curl -fsS -H "Authorization: Bearer $TOKEN" \
       "https://$APP.scm.azurewebsites.net/api/vfs/site/wwwroot/" 2>/dev/null \
    | python3 -c 'import json,sys
for e in sorted(json.load(sys.stdin), key=lambda x: x["name"]):
    print("   " + e["name"])' 2>/dev/null \
    || echo "   (could not list wwwroot even with a bearer token)"
  echo "   -> 'antenv' PRESENT = dependencies installed. ABSENT = the build never ran."
  echo "   -> 'requirements.txt' must be at THIS level or Oryx detects no Python app."
else
  echo "   (could not obtain a token)"
fi

say "4. deployment log — WHICH DEPLOYER, and is there any sign Oryx ran?"
# ⭐ The two things that matter, and section 4 answered the question on 2026-09-30:
# `deployer = OneDeploy` with no "Detecting platforms" and no "Running pip install"
# above it means the build was skipped entirely. That observation is why
# FIP_DEPLOY_METHOD now defaults to zipdeploy.
az webapp log deployment show -g "$RG" -n "$APP" 2>&1 \
  | grep -oE '"message": "[^"]*"' | tail -25
n_build="$(az webapp log deployment show -g "$RG" -n "$APP" 2>&1 \
           | grep -icE 'oryx|detecting platform|pip install|virtual environment')"
echo "   -> $n_build log line(s) mention a build. ZERO means Oryx never ran."

say "5. is container logging even ON? (OFF by default — an empty section 6 then means"
say "   'nothing was being recorded', NOT 'the container said nothing')"
# ⚠️ `az webapp log config show` DOES NOT EXIST — it is `az webapp log show`. The wrong
# spelling printed "unrecognized arguments: show" and this section reported nothing on
# 2026-09-30, which is a diagnostic failing at the one job it has.
az webapp log show -g "$RG" -n "$APP" \
   --query "{docker:httpLogs.fileSystem.enabled, appLevel:applicationLogs.fileSystem.level}" \
   -o json 2>&1 | head -8
echo "   turning filesystem logging on so the NEXT attempt is observable..."
az webapp log config -g "$RG" -n "$APP" --docker-container-logging filesystem \
   --application-logging filesystem --level verbose -o none 2>/dev/null || true

say "6. container log — the last 60 lines before it gave up"
# timeout, because `log tail` streams forever and there is nothing to stream from a
# container that is not running.
timeout 30 az webapp log tail -g "$RG" -n "$APP" 2>&1 | tail -60

say "7. where did Oryx actually put the app?"
# ⭐ The manifest names the extraction target. When wwwroot holds `output.tar.zst` rather
# than loose files, the app runs from a TEMPORARY directory and any absolute
# /home/site/wwwroot path in the startup command names a file that does not exist. That
# was the 2026-09-30 failure: a perfect build, and a startup command aimed at nothing.
if [[ -n "${TOKEN:-}" ]]; then
  curl -fsS -H "Authorization: Bearer $TOKEN" \
       "https://$APP.scm.azurewebsites.net/api/vfs/site/wwwroot/oryx-manifest.toml" \
       2>/dev/null | head -20 || echo "   (no oryx-manifest.toml — loose-file layout)"
fi

say "8. access restrictions"
az webapp config access-restriction show -g "$RG" -n "$APP" \
   --query "ipSecurityRestrictions[].{name:name, action:action, ip:ipAddress, pri:priority}" \
   -o table

cat <<'MSG'

=== reading this
  antenv ABSENT + "Build successful" in ~1s  -> Oryx skipped pip. The two app settings in
                                                section 1 are the cause; deploy.sh now sets
                                                both and verifies them before deploying.
  antenv PRESENT + container log shows an
  import error or ModuleNotFoundError        -> a real code or dependency problem.
  container log shows a port/bind message    -> the startup command, not the build.
MSG
