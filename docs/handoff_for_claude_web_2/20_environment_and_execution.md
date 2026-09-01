# Environment and execution mechanics

How work actually gets done. A plan does not need to specify these, but a plan that assumes
the wrong ones produces steps the executor has to rewrite.

---

## 1. Two machines

| | Windows dev box | server 47 |
|---|---|---|
| Role | authoring, Excel, PDFs, and now full test runs | deployment target and parity reference |
| Python | `…\anaconda3\anaconda2025\python.exe` — 3.13.5, numpy 2.3.4, pandas 2.3.3, scipy 1.16.3, pytest 8.3.4 | conda env `PengSX`; pytest lives in the repo `.venv` |
| Suite | **390** green in ~35 s | **390** green in ~29 s |
| Repo | `C:\Users\cnc\fixed_income_pricing` | `/home/PengSX/fixed_income_pricing` |

**Correction worth flagging** (2026-08-25): the long-standing note that there was "no usable
local Python" was **wrong**, and it had been shaping the whole workflow. `python` on PATH is
only the Microsoft Store stub; the real installs appear only in the registry. The `anaconda3`
*base* env is 3.8.8 with a broken numpy (mkl-service) and must not be used.

Consequence: a quick check no longer needs ssh. The endpoint's JSON output is
**byte-identical** on both machines, which is also a free cross-platform determinism result.

## 2. Sync

```text
local → GitHub    reliable
local → 47        reliable        git push 47 main   (47 has receive.denyCurrentBranch=updateInstead)
47   → GitHub     GFW-flaky       TCP connects, TLS is blackholed. Do not rely on it.
```

So **47 is synced by pushing to it from local**, not by pulling on it. A dirty tree on 47
makes the push refuse — that guardrail protects any scp quick-edits sitting there.

Pushes are written `GIT_TERMINAL_PROMPT=0 git push …`: the prefix matches an existing
permission rule and prevents a credential-dialog hang.

Windows `scp` to 47 leaves CRLF working-tree copies that later block `git pull`. Fix:
confirm `git diff --ignore-cr-at-eol` is empty, discard, pull.

## 3. Running things

```text
tests          python -m pytest -q                        (pytest.ini pins testpaths=tests)
drivers        PYTHONPATH=src python scripts/<driver>.py  (FIP_VAL_DATE, FIP_OUT, FIP_DATA_DIR)
one bond       python scripts/price_json.py --input req.json --output resp.json
PDF            python scripts/md_to_pdf.py --input X.md --output Y.pdf
Excel bridge   powershell -File integrations/excel_vba/tests/Run-BridgeTests.ps1 [-PythonExe …]
demo workbook  powershell -File integrations/excel_vba/demo/Build-DemoWorkbook.ps1 -PythonExe …
```

The three production drivers run locally in 6 s, 4 s and 7 s — fast enough that freezing and
re-comparing their output after every commit is routine rather than a chore.

`pytest.ini` is **load-bearing**: without `testpaths = tests`, a root-level run also walks
the git-ignored Drive staging copies, finds duplicate test filenames, and aborts the whole
run. It must also stay ASCII — pytest reads it with the system codec (GBK here) and one em
dash breaks every run.

## 4. Documents and deliverables

PDF generation is now **one local command** (`scripts/md_to_pdf.py`): the local Python has
`markdown` and Edge is installed, so the old pandoc-on-47-then-Edge-locally dance is retired.

Three Edge flags are load-bearing and each fails **silently** — `--headless=new` (the bare
`--headless` writes no PDF and still exits 0), a throwaway `--user-data-dir`, and
`--no-pdf-header-footer`. They are inside the script; do not re-derive them.

The Drive staging folder `code_structure_sample/` and its dated zip are git-ignored and
regenerated with `robocopy /E` — **never `/MIR`**, which trips a path-protection guard, and
never in the same command as a `Remove-Item`, which gets the whole script rejected.

## 5. Excel automation

Building or driving Excel from a script needs "Trust access to the VBA project object model"
(off by default). Every script here enables it and restores the previous state in a `finally`
block, and kills only the Excel processes it started.

Two hard-won rules:

- **do the cell I/O in VBA**, not from PowerShell. The COM binder types a property from its
  first use per call site, so writing a string and then a number through the same site throws;
- **never let a test call a MsgBox path** — a modal dialog in an invisible Excel hangs the
  automation until timeout.

## 6. How a plan is executed here

1. the user drops the plan into `docs/`;
2. the CLI session reads it, runs an **alignment gate** against the live tree, and records
   the true baseline (commit, test count, file layout);
3. where reality differs, the session **edits the plan in place** and adds a revision
   section stating what changed and why;
4. it commits the plan revision **first**, then executes gate by gate;
5. the full suite runs after every code-bearing commit, and production outputs are re-hashed;
6. records (`WORKLOG.md`, `CLAUDE.md`, `PROJECT_STATUS.md`) are updated at the end.

Two consequences for how a plan should be written: gates are welcome and used; and an
instruction like "if not already present" produces no action unless it is attached to a gate.

## 7. The CLI session's own memory

`CLAUDE.md` (verbatim file `30`) is the execution side's operating memory — conventions,
locked decisions, environment facts, and explicit *don't re-derive this* notes. It is the
single most useful file for predicting what the executor will do, and it is updated at the
end of every round.

---

## Update 2026-08-30

**Determinism has a documented limit now.** Local Windows and server 47 produce byte-identical
results for the **test suite** and for the **single-bond endpoint JSON**, but **not** for the
full 566-bond driver CSVs: those differ by up to **3.6e-8 relative, entirely in `convexity`**
(a second difference ÷ bump² amplifies a last-bit rounding by 10⁸). Text columns are identical
and prices/spreads/durations agree to ~1e-12.

Consequences:

- a cross-platform `sha256` diff of a driver CSV **shows a difference that is not a
  regression** — do not chase it;
- **production parity is asserted local-fresh vs local-fresh**, which is byte-exact and
  therefore stricter. Two local runs of the same driver were verified byte-identical before
  this was relied on;
- the `outputs/*.csv` checked into the working tree are now **locally produced**. 47 remains
  the deployment target and should be re-run at deployment.

**Timings.** Full suite ~21 s local, ~34 s on 47. Each driver run loads the 3.4 MB workbook,
so a five-driver parity sweep is a few minutes — run it in the background while writing the
next piece rather than waiting on it.

**Excel-side tests** (`integrations/excel_vba/tests/Run-BridgeTests.ps1`, **57 checks, 61 with
a live interpreter**) drive a
hidden real Excel instance and take about a minute. They are outside pytest and must be run
deliberately — this round they were re-run to verify the v1.1 dispatch had not disturbed the
bridge, rather than assumed from the fact that nothing in the .bas changed.
