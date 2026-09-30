"""Does the DEPLOYED service reproduce the record? A gate, not a report.

    PYTHONPATH=src python scripts/remote_smoke.py https://<app>.azurewebsites.net
    ... --token "$(az account get-access-token --resource api://<appId> -o tsv --query accessToken)"
    ... --vs-local        # also compare against a live local engine (needs numpy/pandas)

⭐ **THE GATE NEEDS NOTHING BUT THE STANDARD LIBRARY**, and that is a correction.

The first version imported ``pricer.endpoints.main`` to compute a local reference, and so
it needed numpy, pandas and scipy on whatever machine was asking. On 2026-09-30 it died on
the very machine that had just deployed the service:

    ModuleNotFoundError: No module named 'pandas'

Azure Cloud Shell's system python has no scientific stack. But the venv was never the real
problem — the design was. A gate that only runs where the engine runs cannot be run by the
people option B exists for: Mario's team, a colleague checking the URL is healthy, a CI
runner. ⚠️ It is also a soft form of this project's habit 6, *a verification tool must not
depend on what it verifies*.

⭐ And the fixture comparison is the BETTER question anyway. Comparing the deployment
against a live local run asks "does Azure agree with this machine right now". Comparing it
against the **committed response fixtures** asks "does Azure reproduce the record" — which
is the claim being made, and the same question ``platform_parity.py`` asks of the driver
CSVs against ``release_facts``.

⚠️ **It EXITS NONZERO on failure.** A deliberate difference from ``platform_parity.py``,
which reports and exits 0. A report is right for exploring a platform; a gate is right for
something Mario's team will open.

## What "right" means here

Not "it returns 200". For each shipped fixture the deployed response must match the
committed one:

* **every string, code, field name and structure IDENTICAL** — decided by logic, not
  rounding, so any difference is a defect rather than a platform;
* **every number within its own bound** — ``pricer/endpoints/tolerances.py``, the same rule
  ``tests/test_excel_fixture_parity.py`` applies between Windows and 47. Convexity gets
  1e-6 because a second difference over a squared bump amplifies a last bit by 1e8;
  everything else gets 1e-10.

⚠️ **The two ``_v1`` fixtures are a FROZEN v1.0 corpus and are deliberately not equal to
what today's engine emits** — today's answer carries ``schema_version`` 1.1 and an added
``inputs_used.instrument_type``, which is the additive contract working. They are checked
for ACCEPTANCE (right status, right error code) and exempted from the strict comparison,
exactly as the parity test exempts them. Comparing them strictly would manufacture two
failures out of a working service.

⭐ ``/health`` is checked first and alone, because the single most likely way a cloud
deployment of this breaks is that **the code ships and the data does not**. A liveness
probe that only proves the process started would answer 200 while every real request came
back CURVE_NOT_FOUND. ``curves_visible`` is what separates those two worlds.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

EXAMPLES = pathlib.Path("integrations/excel_vba/examples")
TIMEOUT = 120           # a cold App Service worker imports pandas before it answers

# ⚠️ Loaded BY PATH, not as ``from pricer.endpoints import tolerances``. That import runs
# ``pricer/endpoints/__init__.py``, which eagerly imports ``main``, which imports pandas —
# so the ordinary import would drag the entire scientific stack in just to read four
# constants. The module itself is standard library only, by design; this keeps it that way
# at the call site too.
_TOL_PATH = pathlib.Path("src/pricer/endpoints/tolerances.py")
_spec = importlib.util.spec_from_file_location("_fip_tolerances", _TOL_PATH)
tol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tol)


def _request(url, data=None, token=None):
    """One HTTP call. Returns (status, parsed_json_or_None, raw_text)."""
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw, status = r.read().decode("utf-8", "replace"), r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read().decode("utf-8", "replace"), e.code
    except Exception as e:                                # noqa: BLE001
        return None, None, f"{type(e).__name__}: {e}"
    try:
        return status, json.loads(raw), raw
    except json.JSONDecodeError:
        return status, None, raw


def pairs():
    """Every (request, response, generation) fixture pair on disk.

    The pairing rule is copied from ``tests/test_excel_fixture_parity.py`` deliberately —
    ⚠️ raises rather than skipping when a request has no partner, so a fixture whose name
    breaks the convention fails loudly instead of vanishing from the run.
    """
    out = []
    for request in sorted(EXAMPLES.glob("*request*.json")):
        response = EXAMPLES / request.name.replace("_request", "_response")
        if not response.exists():                    # the error pair is named differently
            response = EXAMPLES / request.name.replace("_request", "")
        if not response.exists():
            raise SystemExit(f"{request.name} has no response fixture beside it")
        out.append((request, response, "1.1" if "_v1_1" in request.name else "1.0"))
    return out


def diff(committed, live, path=""):
    """Every disagreement, as (path, kind, committed, live).

    ``kind`` is "text" for anything decided by logic and "number" for anything decided by
    arithmetic — judged by different rules, and reported separately so a reader can tell a
    defect from a platform.
    """
    out = []
    if isinstance(committed, dict) and isinstance(live, dict):
        for k in sorted(set(committed) | set(live)):
            if k not in committed or k not in live:
                out.append((f"{path}.{k}".lstrip("."), "text",
                            committed.get(k, "<absent>"), live.get(k, "<absent>")))
            else:
                out += diff(committed[k], live[k], f"{path}.{k}".lstrip("."))
    elif isinstance(committed, list) and isinstance(live, list):
        if len(committed) != len(live):
            out.append((path, "text", f"{len(committed)} items", f"{len(live)} items"))
        else:
            for i, (a, b) in enumerate(zip(committed, live)):
                out += diff(a, b, f"{path}[{i}]")
    elif isinstance(committed, bool) or isinstance(live, bool):
        if committed != live:                        # bool before number: bool IS an int
            out.append((path, "text", committed, live))
    elif isinstance(committed, (int, float)) and isinstance(live, (int, float)):
        if tol.budget_used(path, float(committed), float(live)) > 1.0:
            out.append((path, "number", committed, live))
    elif committed != live:
        out.append((path, "text", committed, live))
    return out


def worst(committed, live, path=""):
    """The largest fraction-of-budget consumed anywhere, AND how many numbers were read.

    ⭐ The count is not decoration. "worst 0.0% of budget" looks identical whether every
    number agreed or no number was examined, and this project has shipped that confusion
    twice -- a parity check that matched zero files and reported success, and a
    parametrized test over an empty glob. A measurement must be able to say it measured
    nothing.

    Returns: (worst_fraction, its_path, numbers_compared).
    """
    w, where, n = 0.0, "", 0
    if isinstance(committed, dict) and isinstance(live, dict):
        for k in set(committed) & set(live):
            a, p, c = worst(committed[k], live[k], f"{path}.{k}".lstrip("."))
            n += c
            if a > w:
                w, where = a, p
    elif isinstance(committed, list) and isinstance(live, list):
        for i, (a_, b_) in enumerate(zip(committed, live)):
            a, p, c = worst(a_, b_, f"{path}[{i}]")
            n += c
            if a > w:
                w, where = a, p
    elif (isinstance(committed, (int, float)) and isinstance(live, (int, float))
            and not isinstance(committed, bool) and not isinstance(live, bool)):
        w, where, n = tol.budget_used(path, float(committed), float(live)), path, 1
    return w, where, n


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gate a deployed pricing service.")
    ap.add_argument("base_url", help="e.g. https://ryse-pricing-urs.azurewebsites.net")
    ap.add_argument("--token", default=os.environ.get("FIP_SMOKE_TOKEN"),
                    help="bearer token, when App Service authentication is on")
    ap.add_argument("--vs-local", action="store_true",
                    help="ALSO compare against a live local engine (needs numpy/pandas)")
    a = ap.parse_args(argv)
    base = a.base_url.rstrip("/")

    print(f"target  : {base}")
    print(f"auth    : {'bearer token supplied' if a.token else 'none'}")
    print(f"compare : committed fixtures"
          + (" + a live local engine" if a.vs_local else " (no engine needed)"))

    # ------------------------------------------------ 1. can it price at all?
    status, body, raw = _request(f"{base}/health", token=a.token)
    if status != 200 or not isinstance(body, dict):
        print(f"\nFAIL  /health -> {status}  {raw[:300]}")
        if status in (401, 403):
            print("      401/403: authentication is on with no usable token, or the IP "
                  "allow-rule does not include this machine. A new Cloud Shell session "
                  "gets a new egress IP — re-add the rule.")
        return 1
    curves = body.get("curves_visible", 0)
    print(f"health  : {status}  curves_visible={curves}  {body.get('detail')}")
    if not curves:
        # ⭐ The failure this endpoint exists to catch: the code shipped, the data did not.
        print("\nFAIL  the app runs but sees no curve files. The code deployed and the "
              "data did not — nothing below would mean anything.")
        return 1

    analyze = None
    if a.vs_local:
        sys.path.insert(0, "src")
        from pricer.endpoints.main import analyze_payload as analyze   # noqa: F401

    # ------------------------------------------------ 2. does it reproduce the record?
    fixtures = pairs()
    if len(fixtures) < 9:
        print(f"\nFAIL  only {len(fixtures)} fixture pairs found; refusing to report a "
              "pass on a set that small")           # a check over nothing passes silently
        return 1

    failures, checked, worst_used, worst_at, worst_fix = [], 0, 0.0, "", ""
    numbers = 0                      # how many values were actually put side by side
    print(f"\nfixtures: {len(fixtures)}")
    for req_path, resp_path, generation in fixtures:
        payload = json.loads(req_path.read_text(encoding="utf-8"))
        committed = json.loads(resp_path.read_text(encoding="utf-8"))
        status, live, raw = _request(f"{base}/price",
                                     data=json.dumps(payload).encode("utf-8"),
                                     token=a.token)
        if live is None:
            failures.append((req_path.name, [("<transport>", "text", "json", raw[:160])]))
            print(f"   FAIL  {req_path.name:40s} {status}  {raw[:70]}")
            continue

        if generation == "1.0":
            # ⚠️ Frozen backward-compatibility corpus. Today's engine answers these at 1.1
            # with an added ``inputs_used.instrument_type``, BY DESIGN, so plain equality
            # would invent two failures out of the additive contract working.
            #
            # ⭐ But "accepted" is too weak a check: a response with status ok and wholly
            # wrong numbers would have passed it, and these two are the plain vanilla
            # bonds -- the most basic products in the book. ``shortfalls`` asks the right
            # question instead: is today's answer a SUPERSET of the frozen one? Every
            # field still present, every number within tolerance, extra fields allowed.
            short = tol.shortfalls(committed, live)
            checked += 1
            if short:
                failures.append((req_path.name,
                                 [(s, "text", "frozen v1.0", "today") for s in short]))
                print(f"   FAIL  {req_path.name:40s} v1.0 guarantee broken: {len(short)}")
            else:
                _, _, n_here = worst(committed, live)
                numbers += n_here
                print(f"   ok    {req_path.name:40s} {status}  v1.0 superset holds "
                      f"({n_here} numbers)")
            continue

        checked += 1
        d = diff(committed, live)
        used, at, n_here = worst(committed, live)
        numbers += n_here
        if used > worst_used:
            worst_used, worst_at, worst_fix = used, at, req_path.name
        if d:
            failures.append((req_path.name, d))
            print(f"   FAIL  {req_path.name:40s} {len(d)} difference(s)")
        else:
            print(f"   ok    {req_path.name:40s} {status}  {n_here:3d} numbers, "
                  f"worst {used:7.1%} of budget")

    # ------------------------------------------------ 3. optional: agree with here, now
    if analyze is not None:
        print("\nalso vs a live local engine:")
        for req_path, _, _ in fixtures:
            payload = json.loads(req_path.read_text(encoding="utf-8"))
            status, live, _ = _request(f"{base}/price",
                                       data=json.dumps(payload).encode("utf-8"),
                                       token=a.token)
            d = diff(analyze(payload), live) if live is not None else [("x", "text", 1, 2)]
            print(f"   {'ok  ' if not d else 'FAIL'}  {req_path.name}")
            if d:
                failures.append((req_path.name + " (vs local)", d))

    # ------------------------------------------------ 4. the verdict
    print()
    if failures:
        for name, diffs in failures:
            print(f"--- {name}")
            for p, kind, c, l in diffs[:8]:
                flag = "DEFECT" if kind == "text" else "over tolerance"
                print(f"    {flag:14s} {p}\n        committed {c!r}\n        deployed  {l!r}")
        print(f"\nFAIL  {len(failures)} of {len(fixtures)} fixtures disagree.")
        print("      A TEXT difference is a defect — those are decided by logic, not "
              "rounding.")
        return 1

    # ⚠️ A pass over nothing is the failure this count exists to make impossible. The
    # floor is deliberately loose -- it is a smoke alarm for "the traversal broke", not a
    # golden count that would need updating whenever a fixture gains a field.
    MIN_NUMBERS = 100
    if numbers < MIN_NUMBERS:
        print(f"FAIL  only {numbers} numeric fields were compared, against roughly 156 "
              f"in the committed fixtures. Something stopped the comparison descending, "
              f"and a green result here would mean nothing.")
        return 1

    print(f"numbers compared: {numbers}")
    print(f"worst deviation anywhere: {worst_used:.2%} of its budget "
          f"({worst_at or 'n/a'}, {worst_fix or 'n/a'})")
    if worst_used > tol.BUDGET_USED_MAX:
        # ⚠️ Every fixture passed and the floor still moved. A separate gate on purpose:
        # the noise floor can grow tenfold with every per-field check still green.
        print(f"FAIL  the noise floor exceeds {tol.BUDGET_USED_MAX:.0%} of budget. "
              "Nothing is wrong yet, and that is exactly when to look.")
        return 1
    print(f"\nPASS  the deployed service reproduces the record: {checked} fixtures, "
          f"{numbers} numbers, worst {worst_used:.2%} of tolerance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
