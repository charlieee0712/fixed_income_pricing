"""Write docs/release_facts_<date>.md from the files the drivers actually produced.

Every number in an outward-facing document has to be traceable to a run rather than to
memory (the user's standing instruction). This script is the mechanical half of that: it
reads the live outputs, hashes them, and emits the table the report and the walkthrough
quote from. If a driver has not been re-run, its hash changes and the mismatch is visible.

Run AFTER regenerating outputs/:

    PYTHONPATH=src python scripts/release_facts.py

Inputs
------
1. FIP_OUT_DIR : env, default ``outputs`` — where the driver CSVs live.
2. FIP_FACTS   : env, default ``docs/release_facts_<today>.md`` — the file to write.

The file is written as UTF-8 EXPLICITLY. Redirecting this script's stdout on this machine
would encode it as GBK and turn every em dash into mojibake — the same system-codec trap
that `pytest.ini` carries a warning about.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import os
import pathlib
import subprocess
import sys

import pandas as pd

OUT_DIR = pathlib.Path(os.environ.get("FIP_OUT_DIR", "outputs"))
FACTS = pathlib.Path(os.environ.get(
    "FIP_FACTS", f"docs/release_facts_{dt.date.today():%Y-%m-%d}.md"))

PRODUCTION = ("implied_oas_2009-03-31.csv", "implied_oas.csv", "callable_risk.csv",
              "phase2_risk_2009-03-31.csv", "phase2_risk_2009-06-10.csv")
DISPOSITIONS = ("corporate_disposition_2009-03-31.csv", "corporate_disposition_2009-06-10.csv",
                "callable_disposition_2009-03-31.csv", "callable_disposition_2009-06-10.csv")


def sha256(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def rows(name) -> int:
    return len(pd.read_csv(OUT_DIR / name, dtype=str))


def test_count() -> str:
    """The real number, from a real run — not a number anyone typed."""
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q"],
                          capture_output=True, text=True)
    for line in reversed(proc.stdout.splitlines()):
        if "passed" in line or "failed" in line:
            return line.strip()
    return "pytest produced no summary line"


def main() -> None:
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"],
                           capture_output=True, text=True).stdout.strip()
    out = []
    w = out.append

    w("# Release facts — Round 2b hardening\n")
    w(f"**Generated from the live repository at `{head}`"
      f"{' (working tree DIRTY)' if dirty else ''} on {dt.date.today()}.** Every number below is")
    w("read out of a file a driver just wrote. Regenerate with `PYTHONPATH=src python")
    w("scripts/release_facts.py` after any code-bearing change, and re-run the drivers first.\n")

    w("## Production outputs\n")
    w("| file | rows | sha256 (first 32) |")
    w("|---|---:|---|")
    for f in PRODUCTION:
        w(f"| `{f}` | {rows(f)} | `{sha256(OUT_DIR / f)[:32]}` |")

    w("\n## Disposition sidecars — every security accounted for, at both dates\n")
    w("These are the evidence that nothing is silently dropped: the population, the rows that")
    w("reached the output, and a NAMED reason for every one that did not. The filenames are")
    w("dated because an undated default let the 6-10 run overwrite the 3-31 one.\n")
    w("| file | rows | sha256 (first 32) |")
    w("|---|---:|---|")
    for f in DISPOSITIONS:
        w(f"| `{f}` | {rows(f)} | `{sha256(OUT_DIR / f)[:32]}` |")

    w("\n## Corporate coverage\n")
    w("| valuation date | rows in output | with a model spread | carried at the custodian mark |")
    w("|---|---:|---:|---:|")
    for label, f in (("2009-03-31 (baseline)", "implied_oas_2009-03-31.csv"),
                     ("2009-06-10 (control)", "implied_oas.csv")):
        d = pd.read_csv(OUT_DIR / f, dtype=str)
        w(f"| {label} | {len(d)} | {d['implied_oas'].notna().sum()} | {d['implied_oas'].isna().sum()} |")

    baseline = pd.read_csv(OUT_DIR / "implied_oas_2009-03-31.csv", dtype=str)
    w("\n## Routes at the 2009-03-31 baseline\n")
    w("| route | bonds |")
    w("|---|---:|")
    for route, n in baseline["route"].value_counts().items():
        w(f"| `{route}` | {n} |")

    w("\n## Confidence labelling\n")
    w("A number that rests on a term nobody has confirmed, or on an estimate of an observable,")
    w("says so in the row it appears in — not only in prose somewhere else.\n")
    w("| label | count | what it means |")
    w("|---|---:|---|")
    floating = baseline[baseline["route"] == "floating"]
    w(f"| `current_coupon_source=base_curve_proxy` | "
      f"{(floating['current_coupon_source'] == 'base_curve_proxy').sum()} | the coupon already "
      f"running was not in the custodian file, so it is estimated from the curve and held fixed "
      f"while the risk is measured; the sensitivities are provisional |")
    w(f"| `current_coupon_source=supplied` | "
      f"{(floating['current_coupon_source'] == 'supplied').sum()} | the actual fixing was used |")
    callable_rows = pd.read_csv(OUT_DIR / "callable_risk.csv", dtype=str).fillna("")
    phase2 = pd.read_csv(OUT_DIR / "phase2_risk_2009-03-31.csv", dtype=str).fillna("")
    provisional = int((callable_rows["exercise_terms_status"] == "provisional").sum()
                      + (phase2["exercise_terms_status"] == "provisional").sum())
    confirmed = int((callable_rows["exercise_terms_status"] == "confirmed").sum()
                    + (phase2["exercise_terms_status"] == "confirmed").sum())
    w(f"| `exercise_terms_status=provisional` | {provisional} | every lattice-priced bond: a "
      f"custodian date with the par-call convention applied on top, verified by nobody |")
    w(f"| `exercise_terms_status=confirmed` | {confirmed} | no exercise term in this project has "
      f"been confirmed against Bloomberg |")

    w("\n## Test suite\n")
    w(f"`pytest -q` → **{test_count()}** (local, Python 3.13.5).\n")

    FACTS.parent.mkdir(parents=True, exist_ok=True)
    FACTS.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {FACTS}")


if __name__ == "__main__":
    main()
