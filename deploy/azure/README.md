# Azure App Service — option B, "everyone with authorized access can run our code"

**Option A** (run it ourselves on Azure) was proved 2026-09-16: Cloud Shell, Python 3.12.14,
**495 tests in 38.6 s**, all four drivers in 40 s, every text digest identical to the
Windows-written record. **Option B is a hosted URL other people can call.**

## Run it

### From Azure Cloud Shell (the shortest path)

Cloud Shell already has `az`, already has a persistent `$HOME`, and reaches GitHub without
the interference the 47 box sees.

```bash
# ⚠️ Do NOT run `az login` here. Cloud Shell is already authenticated as the account that
# opened it, and typing it anyway starts a device-code flow you then have to cancel.
az account show --query "{sub:name, user:user.name}" -o tsv    # confirm the subscription

# ⚠️ The repo is PRIVATE, so a first clone needs credentials. gh is preinstalled.
gh auth login                                                  # once, ever
gh repo clone charlieee0712/fixed_income_pricing
cd fixed_income_pricing        # on later visits: cd ~/fixed_income_pricing && git pull

export FIP_APP=ryse-pricing-urs          # must be globally unique
bash deploy/azure/deploy.sh              # infrastructure + settings + code + data

PYTHONPATH=src python scripts/remote_smoke.py "https://$FIP_APP.azurewebsites.net"

# only once that prints PASS:
bash deploy/azure/enable_entra_auth.sh
```

⚠️ **`$HOME` persisting is a setting, not a guarantee.** It survives when Cloud Shell has a
mounted storage account (`cloud-shell-storage-southeastasia`, configured 2026-09-16). Without
the mount the session is ephemeral and wipes after ~20 minutes idle — which has happened
twice — so a missing repo means "check the mount", not "the clone failed".

### From a machine with the Azure CLI

```bash
az login
export FIP_APP=ryse-pricing-urs
bash deploy/azure/deploy.sh
```

⭐ **Until the gate prints `PASS`, the service is not deployed — it is merely running.**
`remote_smoke.py` checks `/health` for visible curve files, then prices all 11 shipped
fixtures against what the local engine computes: strings identical, numbers inside their
own per-quantity tolerance. **It exits nonzero when anything disagrees**, deliberately
unlike `scripts/platform_parity.py`, which reports and exits 0.

Code-only redeploy, infrastructure untouched: `bash deploy/azure/deploy.sh --no-create`.

## What it stands up, and why each choice

| | choice | why |
|---|---|---|
| service | **App Service (Linux, Python 3.12)** | a persistent warm URL, which is what "run and test our codes" means. Container Apps adds a registry and a Dockerfile for no gain here; Functions adds a cold start in front of a pandas import. 3.12 is the version Cloud Shell ran the suite on. |
| plan | **B1 Basic**, ~USD 13/mo | ⚠️ Mario's card. F1 Free unloads the worker after 20 min idle, so the first request of the day takes a minute and the team concludes it is broken. One line to change if cost wins. |
| workers | **2** | separate processes, so N workers *are* the parallel execution the browser front end wants. Not more on 1.75 GB — each loads its own numpy, pandas and curves. |
| timeout | **300 s** | the first request on a cold worker imports pandas and bootstraps a curve. The 30 s default kills it mid-import and the client sees a 502 that never recurs. |
| data | **shipped in the package** (34 MB) | version-locked with the code, which matters: a curve file drifting under a pinned engine changes numbers silently. Blob Storage is the answer when the data outgrows the package, not before. |
| auth, phase 1 | **IP allow-rule for the deployer**, implicit deny-all | no app registration, no consent, no token — so it cannot wall us out before the app is proven |
| auth, phase 2 | **App Service Easy Auth (Entra ID), `Return401`** | see below |

## ⚠️ Authentication is not optional here

⚠️ **CORRECTED 2026-09-29, on the first real run.** `deploy.sh` originally enabled Easy
Auth here with `--action Return401` and **no identity provider configured**. That is not a
locked door, it is a walled-up one: every request 401s including our own gate, and no token
can be obtained because no application is registered to issue one. The line that would have
reported the problem carried `2>/dev/null || true` — a guard that hid the error it guarded
against, which is this repo's most-catalogued failure shape.

⭐ **So it is two phases now.** `deploy.sh` shuts the door with an **IP allow-rule** (one
command, no prerequisites, App Service adds an implicit deny-all beside it), the gate runs
and proves the app, and `enable_entra_auth.sh` then does the registration properly —
three objects, no `|| true` anywhere, stopping on any failure with the app still reachable.
⚠️ Cloud Shell's egress IP changes between sessions: a later 403 means re-run the one
access-restriction command, not that anything broke.

The engine has none — `endpoints/__init__.py` says so plainly — and this app has the client
portfolio on disk. `deploy.sh` turns Easy Auth on **before the first deploy**, so there is
no window in which the data is up and the door is open.

⭐ **Platform auth, not our code.** We ship no hand-rolled authentication, and "everyone with
authorized access" becomes a membership list in Entra ID rather than a secret in a config
file. Adding a colleague is an Azure permission, not a deployment.

⚠️ `--action Return401` and not the login redirect: this is an **API**, and a browser
redirect in response to a `POST /price` produces an HTML login page where a caller expected
JSON.

## Still open, and ours to decide

* **CORS** — untouched. Mario's browser front end calls from another origin and will be
  refused **by the browser, before the request arrives**, so nothing appears in any server
  log. The allowed origin must be set (`az webapp cors add`) once that page has a home.
* **Always On** — not enabled. Worth it once the audience is real; it is one setting.
* **A second region / scale-out** — nothing here needs it yet.

## What is already true, and did not need Azure to be true

`src/pricer/endpoints/routes/`:

* `handler.py` — `handle(method, path, body) -> (status, headers, body)`, framework-free,
  **33 locks**, including the response over the wire asserted byte-identical to what a
  Python caller gets in the same process.
* `wsgi.py` — this deployment's entry point. **21 locks**, same assertion, plus the
  host-shaped cases a tidy function call never sees: a missing `Content-Length`, a chunked
  body, a malformed header, an oversized body that must not be buffered before it is
  refused, and an escaping exception that must not become a traceback on a public URL.

`scripts/serve_local.py` reaches the same `handle()` through the standard library, so the
whole path can be exercised with no cloud account at all — which is how the gate itself was
verified before it was ever pointed at Azure.
