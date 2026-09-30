"""Does the DEPLOYED service reproduce the record? A gate, not a report.

    PYTHONPATH=src python scripts/remote_smoke.py https://<app>.azurewebsites.net
    PYTHONPATH=src python scripts/remote_smoke.py https://... --token "$(az account get-access-token --query accessToken -o tsv)"

⭐ **This is the whole reason the Azure work is not a pile of remembered portal clicks.**
Liping's account of her own Web App was "something in the settings was stuck, I tried a
few times and it inexplicably started working". A deployment nobody can verify will
un-work just as inexplicably, in front of Mario's group, with nobody able to say what
changed. This script is the answer to "is it actually right?" — asked from outside, over
the wire, against the committed fixtures.

⚠️ **It EXITS NONZERO on failure.** That is a deliberate difference from
``scripts/platform_parity.py``, which reports and exits 0. A report is the right shape for
exploring a new platform; a gate is the right shape for something Mario's team will open.

## What "right" means here

Not "it returns 200". For each shipped fixture the deployed response must equal what this
machine computes in-process:

* **every string, code, field name and structure IDENTICAL** — those are decided by logic,
  not by rounding, so any difference is a defect rather than a platform;
* **every number within its own bound** — ``pricer.endpoints.tolerances``, the same rule
  ``tests/test_excel_fixture_parity.py`` applies between Windows and 47. Convexity gets
  1e-6 because a second difference divided by a squared bump amplifies a last bit by 1e8;
  everything else gets 1e-10.

⭐ **/health is checked first and on its own**, because the single most likely way a cloud
deployment of this breaks is that **the code ships and the data does not**. A liveness
probe that only proves the process started would answer 200 while every real request came
back CURVE_NOT_FOUND. ``curves_visible`` is what distinguishes those two worlds.

⚠️ **Standard library only, no third-party HTTP client.** This has to run on whatever
machine is asking the question, including a bare Cloud Shell, and adding a dependency to
the thing that verifies a deployment is the shape of trap this project files under "a
verification tool built on the thing it cannot control".
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, "src")

from pricer.endpoints import tolerances as tol            # noqa: E402
from pricer.endpoints.main import analyze_payload         # noqa: E402

EXAMPLES = pathlib.Path("integrations/excel_vba/examples")
TIMEOUT = 120           # a cold App Service worker loads pandas before it answers anything


def _request(url, data=None, token=None):
    """One HTTP call. Returns (status, parsed_json_or_None, raw_text)."""
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read().decode("utf-8", "replace"), e.code
    except Exception as e:                                # noqa: BLE001
        return None, None, f"{type(e).__name__}: {e}"
    try:
        return status, json.loads(raw), raw
    except json.JSONDecodeError:
        return status, None, raw


def _diff(local, remote, path=""):
    """Every disagreement between two responses, as (path, kind, local, remote).

    ``kind`` is "text" for anything decided by logic and "number" for anything decided by
    arithmetic — they are judged by different rules and reported separately so a reader
    can tell a defect from a platform.
    """
    out = []
    if isinstance(local, dict) and isinstance(remote, dict):
        for k in sorted(set(local) | set(remote)):
            if k not in local or k not in remote:
                out.append((f"{path}.{k}".lstrip("."), "text",
                            local.get(k, "<absent>"), remote.get(k, "<absent>")))
            else:
                out += _diff(local[k], remote[k], f"{path}.{k}".lstrip("."))
    elif isinstance(local, list) and isinstance(remote, list):
        if len(local) != len(remote):
            out.append((path, "text", f"{len(local)} items", f"{len(remote)} items"))
        else:
            for i, (a, b) in enumerate(zip(local, remote)):
                out += _diff(a, b, f"{path}[{i}]")
    elif isinstance(local, bool) or isinstance(remote, bool):
        if local != remote:                               # bool before number: bool is an int
            out.append((path, "text", local, remote))
    elif isinstance(local, (int, float)) and isinstance(remote, (int, float)):
        used = tol.budget_used(path, float(local), float(remote))
        if used > 1.0:
            out.append((path, "number", local, remote))
    elif local != remote:
        out.append((path, "text", local, remote))
    return out


def _worst(local, remote, path=""):
    """The largest fraction-of-budget used anywhere in the pair."""
    worst, where = 0.0, ""
    if isinstance(local, dict) and isinstance(remote, dict):
        for k in set(local) & set(remote):
            w, p = _worst(local[k], remote[k], f"{path}.{k}".lstrip("."))
            if w > worst:
                worst, where = w, p
    elif isinstance(local, list) and isinstance(remote, list):
        for i, (a, b) in enumerate(zip(local, remote)):
            w, p = _worst(a, b, f"{path}[{i}]")
            if w > worst:
                worst, where = w, p
    elif (isinstance(local, (int, float)) and isinstance(remote, (int, float))
            and not isinstance(local, bool) and not isinstance(remote, bool)):
        worst, where = tol.budget_used(path, float(local), float(remote)), path
    return worst, where


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("base_url", help="e.g. https://ryse-pricing.azurewebsites.net")
    ap.add_argument("--token", default=os.environ.get("FIP_SMOKE_TOKEN"),
                    help="bearer token, when App Service authentication is on")
    a = ap.parse_args(argv)
    base = a.base_url.rstrip("/")
    failures = []

    print(f"target : {base}")
    print(f"auth   : {'bearer token supplied' if a.token else 'none'}")

    # -------------------------------------------------- 1. can it price at all?
    status, body, raw = _request(f"{base}/health", token=a.token)
    if status != 200 or not isinstance(body, dict):
        print(f"\nFAIL  /health -> {status}  {raw[:300]}")
        if status in (401, 403):
            print("      authentication is on and no usable token was supplied "
                  "(--token, or FIP_SMOKE_TOKEN)")
        return 1
    curves = body.get("curves_visible", 0)
    print(f"health : {status}  curves_visible={curves}  {body.get('detail')}")
    if not curves:
        # ⭐ The failure this endpoint exists to catch: the code deployed, the data did not.
        print("\nFAIL  the app is running but sees no curve files. The code shipped and "
              "the data did not — nothing else below would mean anything.")
        return 1

    # -------------------------------------------------- 2. does it reproduce the record?
    requests = sorted(p for p in EXAMPLES.glob("*request*.json"))
    if len(requests) < 9:
        print(f"\nFAIL  only {len(requests)} fixtures found; refusing to report a pass "
              "on a set that small")          # a check over nothing passes silently
        return 1

    worst_used, worst_at, worst_fix = 0.0, "", ""
    print(f"\nfixtures: {len(requests)}")
    for path in requests:
        payload = json.loads(path.read_text(encoding="utf-8"))
        local = analyze_payload(payload)
        status, remote, raw = _request(f"{base}/price",
                                       data=json.dumps(payload).encode("utf-8"),
                                       token=a.token)
        if remote is None:
            failures.append((path.name, [("<transport>", "text", "json", raw[:160])]))
            print(f"   FAIL  {path.name:38s} {status}  {raw[:80]}")
            continue
        d = _diff(local, remote)
        used, at = _worst(local, remote)
        if used > worst_used:
            worst_used, worst_at, worst_fix = used, at, path.name
        if d:
            failures.append((path.name, d))
            print(f"   FAIL  {path.name:38s} {len(d)} difference(s)")
        else:
            print(f"   ok    {path.name:38s} {status}  worst {used:7.1%} of budget")

    # -------------------------------------------------- 3. the verdict
    print()
    if failures:
        for name, diffs in failures:
            print(f"--- {name}")
            for p, kind, lo, re_ in diffs[:8]:
                flag = "DEFECT" if kind == "text" else "over tolerance"
                print(f"    {flag:14s} {p}\n        local  {lo!r}\n        remote {re_!r}")
        print(f"\nFAIL  {len(failures)} of {len(requests)} fixtures disagree.")
        print("      A TEXT difference is a defect — those are decided by logic, not "
              "rounding.")
        return 1

    print(f"worst deviation anywhere: {worst_used:.2%} of its budget "
          f"({worst_at or 'n/a'}, {worst_fix or 'n/a'})")
    if worst_used > tol.BUDGET_USED_MAX:
        # ⚠️ Every fixture passed and the floor still moved. Separate gate on purpose: the
        # noise floor can grow tenfold with every per-field check still green.
        print(f"FAIL  the noise floor exceeds {tol.BUDGET_USED_MAX:.0%} of budget. Nothing "
              "is wrong yet, and that is exactly when to look.")
        return 1
    print(f"\nPASS  the deployed service reproduces the record on all {len(requests)} "
          "fixtures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
