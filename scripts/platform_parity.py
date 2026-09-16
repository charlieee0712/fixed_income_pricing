#!/usr/bin/env python3
"""Does THIS machine reproduce the published numbers?

Run it on any machine that has the code and the data, and it answers one question:
are the files this computer produces the same files the reports were written from?

    PYTHONPATH=src python3 scripts/platform_parity.py --run

``--run`` executes all four pricing drivers first. Without it the script only reads
what is already in ``outputs/``.

Why this exists
---------------
The numbers in every report are backed by a sha256 recorded in the dated
``docs/release_facts_<date>.md``. Until now the only way to check a new machine
against that record was to type a long command by hand — which is how this script was
born, after a multi-line paste arrived mangled in a browser terminal. A script in the
repository cannot be mangled, and it is the same check for everyone.

⚠️ **A difference is not automatically a regression, and the report says which kind.**
Floating-point arithmetic is not identical across processors and library versions, and
two quantities in this project amplify that on purpose:

* a **duration** divides a bumped price difference by the bump (1e-4), multiplying a
  last-digit rounding by ten thousand;
* a **convexity** divides a second difference by the bump squared, multiplying it by a
  hundred million.

So the useful questions are not "is the hash the same" alone. They are: does the row
count match (a real regression usually changes it), do the TEXT columns match
byte-for-byte (they carry no arithmetic, so they must), and how much of the agreed
numerical tolerance does the endpoint consume? This script answers all three.

Measured before this script existed: Windows against the Linux host, every string and
structure identical, prices within 6e-16 relative, durations within 4e-13, convexity up
to 7.5e-08 absolute — 2.1% of the tolerance budget.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import time

# The console this runs on is unknown -- a Chinese Windows box encodes GBK, the
# Azure container UTF-8. A diagnostic that raises UnicodeEncodeError instead of
# printing is worse than useless, so the stream is widened before anything is
# written to it. The printed strings are ASCII anyway; this covers what arrives
# from filenames and exception messages.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"

#: Every driver, with the environment that names its output the way the record does.
#: ⚠️ ``callable_risk.py`` writes an UNDATED file — a known carry-over — so running it
#: at the June date would overwrite the March one. Only the March run is listed.
DRIVERS = [
    ("scripts/phase2_risk.py", {"FIP_VAL_DATE": "2009-03-31",
                                "FIP_OUT": "outputs/phase2_risk_2009-03-31.csv"}),
    ("scripts/phase2_risk.py", {"FIP_VAL_DATE": "2009-06-10",
                                "FIP_OUT": "outputs/phase2_risk_2009-06-10.csv"}),
    ("scripts/sovereign_risk.py", {"FIP_VAL_DATE": "2009-03-31",
                                   "FIP_OUT": "outputs/sovereign_risk_2009-03-31.csv"}),
    ("scripts/sovereign_risk.py", {"FIP_VAL_DATE": "2009-06-10",
                                   "FIP_OUT": "outputs/sovereign_risk_2009-06-10.csv"}),
    ("scripts/calibrate_risk.py", {"FIP_VAL_DATE": "2009-03-31",
                                   "FIP_OUT": "outputs/implied_oas_2009-03-31.csv"}),
    ("scripts/calibrate_risk.py", {"FIP_VAL_DATE": "2009-06-10",
                                   "FIP_OUT": "outputs/implied_oas.csv"}),
    ("scripts/callable_risk.py", {"FIP_VAL_DATE": "2009-03-31"}),
]


def newest_release_facts():
    """The most recent release record in ``docs/``.

    Inputs: none.
    Returns: pathlib.Path. Raises SystemExit with a plain message if there is none.
    """
    found = sorted(ROOT.glob("docs/release_facts_*.md"))
    if not found:
        raise SystemExit("no docs/release_facts_*.md in this checkout — nothing to compare against")
    return found[-1]


def published(record_path):
    """The rows and sha256 the record claims for each output file.

    Inputs
    ------
    1. record_path : pathlib.Path — a ``release_facts_<date>.md``.

    Returns: dict ``{filename: (rows, sha256_first_32)}``.
    """
    text = record_path.read_text(encoding="utf-8")
    rows = re.findall(r"\|\s*`([^`]+\.csv)`\s*\|\s*(\d+)\s*\|\s*`([0-9a-f]{32})`", text)
    return {name: (int(n), h) for name, n, h in rows}


def text_column_digest(path):
    """A sha256 over the NON-NUMERIC columns only.

    Inputs
    ------
    1. path : pathlib.Path — a driver output CSV.

    Returns: str — the first 16 hex characters, or ``"unreadable"``.

    ⚠️ This is the column set that carries no arithmetic — identifiers, routes, flags,
    dates, provenance labels. It must be identical on every machine, and when it is
    not, that is a real defect rather than rounding: a driver message once embedded a
    filesystem path and so read differently on Windows and Linux, and this is the
    comparison that would have caught it.

    Selecting by "not a number" rather than by ``object`` dtype is deliberate — pandas
    3.0 gives strings their own dtype, so an ``object`` filter silently returns nothing
    there and the check would pass by finding nothing to check.
    """
    try:
        import pandas as pd
        text = pd.read_csv(path).select_dtypes(exclude=["number"])
        if text.shape[1] == 0:
            return "no text columns"
        blob = text.to_csv(index=False).encode("utf-8")
        return f"{hashlib.sha256(blob).hexdigest()[:16]} ({text.shape[1]} cols)"
    except Exception as exc:                       # noqa: BLE001 - a diagnostic, never fatal
        return f"unreadable ({type(exc).__name__})"


def run_drivers():
    """Execute every pricing driver, in the order the record was built.

    Inputs: none (uses :data:`DRIVERS`).
    Returns: None. Prints one line per driver with its wall time.
    """
    print("Running the drivers. Several minutes; the corporate book is the slow one.\n")
    env_base = {**os.environ, "PYTHONPATH": "src"}
    env_base.setdefault("FIP_DATA_DIR", "data")
    OUTPUTS.mkdir(exist_ok=True)
    for script, env in DRIVERS:
        started = time.time()
        done = subprocess.run([sys.executable, script], cwd=str(ROOT),
                              env={**env_base, **env}, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")
        label = f"{pathlib.Path(script).name} @ {env.get('FIP_VAL_DATE', '')}"
        if done.returncode == 0:
            print(f"  {label:44s} {time.time() - started:6.1f}s")
        else:
            print(f"  {label:44s} FAILED rc={done.returncode}")
            print("    " + (done.stderr or done.stdout or "").strip().splitlines()[-1][:160])
    print()


def compare_outputs():
    """Compare every output file against the newest published record.

    Inputs: none.
    Returns: int — the number of files that differ (0 is the good answer).
    """
    record = newest_release_facts()
    want = published(record)
    print(f"Against {record.name} -- {len(want)} files\n")
    print(f"  {'file':42s} {'rows':>6}  {'sha256':10s}  text columns")
    print(f"  {'-' * 42} {'-' * 6}  {'-' * 10}  {'-' * 30}")
    differing = 0
    for name, (want_rows, want_hash) in want.items():
        path = OUTPUTS / name
        if not path.exists():
            print(f"  {name:42s} {'--':>6}  not produced")
            differing += 1
            continue
        raw = path.read_bytes()
        got_hash = hashlib.sha256(raw).hexdigest()[:32]
        lines = raw.decode("utf-8", "replace").count("\n") + (0 if raw.endswith(b"\n") else 1)
        got_rows = lines - 1                       # the header is not a row
        same = got_hash == want_hash
        rows_note = f"{got_rows:>6}" if got_rows == want_rows else f"{got_rows:>6}!"
        verdict = "IDENTICAL" if same else "differs"
        if not same:
            differing += 1
        print(f"  {name:42s} {rows_note}  {verdict:10s}  {text_column_digest(path)}")
    print()
    if differing:
        print("  NOTE: A differing hash with a MATCHING row count and MATCHING text columns is the")
        print("     expected cross-platform result, not a regression -- see the module docstring.")
        print("     A changed row count, or changed text columns, is a real difference.")
    else:
        print("  Every published file reproduced byte-for-byte on this machine.")
    return differing


def endpoint_budget():
    """How much of the agreed numerical tolerance this machine consumes.

    Inputs: none.
    Returns: None. Prints the worst deviation across the nine shipped Excel fixtures,
    as a fraction of the tolerance it is allowed.

    Unlike the CSVs — whose reference is only a hash — the fixtures are committed in
    full, so this comparison is quantitative and says exactly which field moved.
    """
    spec = importlib.util.spec_from_file_location(
        "_fixture_parity", ROOT / "tests" / "test_excel_fixture_parity.py")
    if spec is None or spec.loader is None:
        print("  (fixture parity test not found -- skipped)")
        return
    os.environ.setdefault("FIP_DATA_DIR", str(ROOT / "data"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from pricer.endpoints.main import analyze_payload

    worst = (0.0, "none")
    for request_path, response_path, _ in module._GOLDEN:
        _, seen = module._compare(
            json.loads(response_path.read_text(encoding="utf-8")),
            analyze_payload(json.loads(request_path.read_text(encoding="utf-8"))))
        worst = max(worst, seen)
    print(f"  worst deviation: {worst[0]:.2%} of its tolerance, at {worst[1]}")
    print(f"  (Windows against the Linux host measured 2.1%; the suite fails above 100%,")
    print(f"   and the set-level check warns above 10%.)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", action="store_true",
                        help="execute the four pricing drivers before comparing")
    args = parser.parse_args()

    print("=" * 78)
    print("  Platform parity check")
    print("=" * 78)
    print(f"  {platform.system()} {platform.machine()} | Python {platform.python_version()}")
    for name in ("numpy", "pandas", "scipy"):
        try:
            print(f"  {name:8s} {__import__(name).__version__}")
        except ImportError:
            print(f"  {name:8s} MISSING")
    print()

    if args.run:
        run_drivers()

    print("-" * 78)
    print("  1. Driver outputs against the published record")
    print("-" * 78)
    differing = compare_outputs()

    print("-" * 78)
    print("  2. The JSON endpoint against the shipped Excel fixtures")
    print("-" * 78)
    endpoint_budget()
    print()
    # ⚠️ Always exit 0, even when files differ. This is a REPORT, not a gate: on a
    # different processor a differing hash is the expected result, and an exit code
    # that called it failure would train people to ignore the one case that matters.
    # The row counts and the text-column digests above are what to read.
    _ = differing
    return 0


if __name__ == "__main__":
    sys.exit(main())
