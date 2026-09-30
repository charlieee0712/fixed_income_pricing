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
CREDS="$(az webapp deployment list-publishing-credentials -g "$RG" -n "$APP" \
         --query "[publishingUserName,publishingPassword]" -o tsv 2>/dev/null)"
USER_="$(printf '%s' "$CREDS" | cut -f1)"
PASS_="$(printf '%s' "$CREDS" | cut -f2)"
if [[ -n "$USER_" ]]; then
  curl -fsS -u "$USER_:$PASS_" "https://$APP.scm.azurewebsites.net/api/vfs/site/wwwroot/" \
    | python3 -c 'import json,sys;[print(f"   {e[\"name\"]}") for e in json.load(sys.stdin)]' \
    2>/dev/null || echo "   (could not list wwwroot)"
  echo "   -> 'antenv' present = dependencies installed. Absent = the build never ran."
else
  echo "   (no publishing credentials; basic auth for SCM may be disabled)"
fi

say "4. deployment log"
az webapp log deployment show -g "$RG" -n "$APP" 2>&1 | tail -30

say "5. container log — the last 60 lines before it gave up"
# timeout, because `log tail` streams forever and there is nothing to stream from a
# container that is not running.
timeout 30 az webapp log tail -g "$RG" -n "$APP" 2>&1 | tail -60

say "6. access restrictions"
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
