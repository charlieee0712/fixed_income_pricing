#!/usr/bin/env python3
"""Does THIS machine reproduce the published numbers?

Run it wherever the code and the data are, and it answers the question a new machine
actually raises:

    PYTHONPATH=src python3 scripts/platform_parity.py --run

``--run`` executes every pricing driver first. Without it the script only reads what is
already in ``outputs/``.

Why the answer is not one number
--------------------------------
Two machines running this code do not produce byte-identical CSVs, and they are not
supposed to. A duration divides a bumped price difference by the bump (1e-4) and so
multiplies a last-digit rounding by ten thousand; a convexity divides a second
difference by the bump squared and multiplies it by a hundred million. So a differing
sha256 across processors is the expected result, and a script that called that failure
would teach people to ignore the one case that matters.

The report therefore has three parts, and the middle one is the load-bearing one:

  * **sha256**  -- byte identity. The strongest statement when it holds, and routinely
    and harmlessly false across platforms.
  * **text**    -- a digest over the columns that carry NO arithmetic: identifiers,
    routes, dates, flags, reason codes. Those are decided by logic, so they must be
    identical on every machine. ⚠️ A differing text digest is a defect, and the kind
    that hides -- on 2026-09-03 a driver flag embedded a filesystem path, so one failure
    read two different ways on Windows and on Linux.
  * **rows**    -- a real regression almost always changes the count.

⚠️ **The text digest is built on the standard library on purpose.** Its first version
went through ``pandas.read_csv(...).select_dtypes(...).to_csv()`` and the first machine
it met was Azure Cloud Shell on **pandas 3.0**, comparing against a record written under
pandas 2.3. Every digest differed and nothing could say whether the text had changed or
the serializer had. A check meant to be invariant across platforms cannot rest on a
library whose behaviour varies across versions. The definition now has one owner,
:mod:`dataio.output_digest`, and the reference values are published in the same
``docs/release_facts_<date>.md`` as the hashes.
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

# The console this runs on is unknown -- a Chinese Windows box encodes GBK, the Azure
# container UTF-8. A diagnostic that raises UnicodeEncodeError instead of printing is
# worse than useless, so the stream is widened before anything is written to it. Every
# printed string below is ASCII anyway; this covers filenames and exception messages.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
sys.path.insert(0, str(ROOT / "src"))

from dataio.output_digest import column_digests, text_digest   # noqa: E402

#: Every driver, with the environment that names its output the way the record does.
#: ⚠️ ``callable_risk.py`` writes an UNDATED ``callable_risk.csv`` -- a known carry-over
#: -- while its disposition sidecar IS dated. So June runs FIRST and March second: that
#: way both dated sidecars exist and the undated file ends up holding March, which is
#: the run the record was written from. Order is load-bearing here, not cosmetic.
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
    ("scripts/callable_risk.py", {"FIP_VAL_DATE": "2009-06-10"}),
    ("scripts/callable_risk.py", {"FIP_VAL_DATE": "2009-03-31"}),
]


def newest_release_facts():
    """The most recent release record in ``docs/``.

    Inputs: none.
    Returns: pathlib.Path. Exits with a plain message when there is none.
    """
    found = sorted(ROOT.glob("docs/release_facts_*.md"))
    if not found:
        raise SystemExit("no docs/release_facts_*.md in this checkout to compare against")
    return found[-1]


def published(record_path):
    """What the record claims for each output file.

    Inputs
    ------
    1. record_path : pathlib.Path -- a ``release_facts_<date>.md``.

    Returns: dict ``{filename: {"rows": int, "sha": str, "text": str | None}}``.

    The two tables are matched by hash LENGTH: a sha256 prefix is 32 hex characters and
    a text digest is 16, so the patterns cannot collide.
    """
    text = record_path.read_text(encoding="utf-8")
    out = {}
    for name, rows, sha in re.findall(
            r"\|\s*`([^`]+\.csv)`\s*\|\s*(\d+)\s*\|\s*`([0-9a-f]{32})`\s*\|", text):
        out[name] = {"rows": int(rows), "sha": sha, "text": None}
    for name, _cols, digest in re.findall(
            r"\|\s*`([^`]+\.csv)`\s*\|\s*(\d+)\s*\|\s*`([0-9a-f]{16})`\s*\|", text):
        if name in out:
            out[name]["text"] = digest
    return out


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
            tail = (done.stderr or done.stdout or "").strip().splitlines()
            print(f"  {label:44s} FAILED rc={done.returncode}")
            print("    " + (tail[-1][:160] if tail else "no output"))
    print()


def compare_outputs():
    """Compare every output file against the newest published record.

    Inputs: none.
    Returns: tuple ``(bytes_differ, text_differ)`` -- counts, where the second is the
    one that means something is wrong.
    """
    record = newest_release_facts()
    want = published(record)
    have_text = sum(1 for v in want.values() if v["text"])
    print(f"Against {record.name} -- {len(want)} files, "
          f"{have_text} with a published text digest\n")
    if not have_text:
        print("  NOTE: this record predates text fingerprints. Regenerate it with")
        print("        PYTHONPATH=src python scripts/release_facts.py to get the")
        print("        comparison that survives a library upgrade.\n")
    print(f"  {'file':42s} {'rows':>6}  {'bytes':9s}  {'text':9s}  digest")
    print(f"  {'-' * 42} {'-' * 6}  {'-' * 9}  {'-' * 9}  {'-' * 16}")

    bytes_differ = text_differ = 0
    detail = []
    for name, claim in want.items():
        path = OUTPUTS / name
        if not path.exists():
            print(f"  {name:42s} {'--':>6}  not produced")
            continue
        raw = path.read_bytes()
        got_sha = hashlib.sha256(raw).hexdigest()[:32]
        lines = raw.decode("utf-8", "replace").count("\n") + (0 if raw.endswith(b"\n") else 1)
        got_rows = lines - 1                       # the header is not a row
        got_text = text_digest(path)

        same_bytes = got_sha == claim["sha"]
        same_text = claim["text"] is None or got_text == claim["text"]
        bytes_differ += 0 if same_bytes else 1
        text_differ += 0 if same_text else 1
        if not same_text:
            detail.append((name, path, claim["text"], got_text))

        rows_cell = f"{got_rows:>6}" if got_rows == claim["rows"] else f"{got_rows:>5}!"
        print(f"  {name:42s} {rows_cell}  "
              f"{'identical' if same_bytes else 'differ   '}  "
              f"{('MATCHES  ' if claim['text'] else 'no ref   ') if same_text else 'DIFFERS !'}  "
              f"{got_text}")
        if not same_bytes:
            print(f"  {'':42s} {'':>6}  this machine: {got_sha}")

    print()
    if text_differ:
        print("  !! TEXT COLUMNS DIFFER. That is not rounding. Per-column breakdown:\n")
        for name, path, want_digest, got in detail:
            print(f"    {name}   published {want_digest} / here {got}")
            for column, digest in column_digests(path).items():
                print(f"      {column:34s} {digest}")
            print()
    elif bytes_differ:
        print(f"  {bytes_differ} file(s) differ byte-for-byte, and EVERY text column matches.")
        print("  That is the expected cross-platform result: the arithmetic columns carry")
        print("  last-digit rounding, and nothing decided by logic moved.")
    else:
        print("  Every published file reproduced byte-for-byte on this machine.")
    return bytes_differ, text_differ


def endpoint_budget():
    """How much of the agreed numerical tolerance this machine consumes.

    Inputs: none.
    Returns: None.

    Unlike the CSVs -- whose reference is only a hash -- the Excel fixtures are
    committed in full, so this comparison is quantitative and names the field that moved.

    ⚠️ It prints how many fixtures were compared. The first version did not, and its
    first real report read "0.00% at none", which is indistinguishable from a loop that
    never ran. A measurement that cannot tell you it measured nothing is not one.
    """
    spec = importlib.util.spec_from_file_location(
        "_fixture_parity", ROOT / "tests" / "test_excel_fixture_parity.py")
    if spec is None or spec.loader is None:
        print("  the fixture parity test is not in this checkout -- skipped")
        return
    os.environ.setdefault("FIP_DATA_DIR", str(ROOT / "data"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from pricer.endpoints.main import analyze_payload

    worst, compared = (0.0, "none"), 0
    for request_path, response_path, _ in module._GOLDEN:
        _, seen = module._compare(
            json.loads(response_path.read_text(encoding="utf-8")),
            analyze_payload(json.loads(request_path.read_text(encoding="utf-8"))))
        worst = max(worst, seen)
        compared += 1
    if compared == 0:
        print("  NO FIXTURES COMPARED -- the examples folder is missing or empty.")
        return
    print(f"  {compared} fixtures compared, worst deviation {worst[0]:.2%} of its tolerance")
    print(f"  at {worst[1]}")
    print("  (Windows against the Linux host measured 2.1%; the suite fails above 100%,")
    print("   and the set-level check warns above 10%.)")


def main():
    parser = argparse.ArgumentParser(description="Does this machine reproduce the published numbers?")
    parser.add_argument("--run", action="store_true",
                        help="execute every pricing driver before comparing")
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
    compare_outputs()

    print("-" * 78)
    print("  2. The JSON endpoint against the shipped Excel fixtures")
    print("-" * 78)
    endpoint_budget()
    print()
    # Always exit 0. This is a report, not a gate: a differing hash on another processor
    # is the expected reading, and an exit code calling it failure would train people to
    # ignore the text-column line, which is the one that means something.
    return 0


if __name__ == "__main__":
    sys.exit(main())
