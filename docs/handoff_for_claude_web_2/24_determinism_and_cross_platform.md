# 24 — Determinism, and what "the same numbers" means on another machine

*New file, 2026-09-15. This was one bullet in `20_environment_and_execution.md` and a
line in CLAUDE.md. It is now a domain of its own, because a third platform arrived, one
of the documented claims turned out to be false, and two of the checks built to police
it were themselves wrong.*

---

## 1. The three platforms

| | local (Windows) | `47` (Linux, deploy target) | Azure Cloud Shell |
|---|---|---|---|
| Python | 3.13.5 | repo `.venv` | 3.12.14 |
| numpy | 2.3.4 | — | **2.5.3** |
| pandas | 2.3.3 | — | ⭐ **3.0.5** |
| scipy | 1.16.3 | — | **1.18.1** |
| suite | 495 in ~50 s | 495 in ~230 s | 483 in **40 s** (at that commit) |

⭐ **pandas 3.0 is a major version ahead of the development machine and everything
passed** — including the golden-master bootstrap, the workbook loaders, and the universe
funnel with its exact counts (597/135/19, 732, 522). The code is not pinned to one
stack.

⚠️ **But `requirements.txt` says `pandas>=2.0` with no upper bound.** Meeting 3.0 was
luck that happened to pay off; a future pandas 4 could break a cloud build silently.
**Pinning is an open follow-up**, not done.

---

## 2. Why two machines do not produce the same bytes, and why that is correct

Nothing here is a disagreement about what a bond is worth. It is the last bit of a
floating-point number, amplified by formulas that are *supposed* to amplify:

| quantity | how it is computed | amplification |
|---|---|---:|
| price, spread, accrued | direct | ×1 |
| effective duration, DV01 | a bumped price difference ÷ the bump (1e-4) | **×1e4** |
| **convexity** | a second difference ÷ the bump **squared** | **×1e8** |

So a last-digit rounding of 1e-16 in a price shows up as ~1e-12 in a duration and ~1e-8
in a convexity. That is exactly the profile measured, every time.

### Measured: Windows against the Linux host

| | agreement |
|---|---|
| every string, error code, field name, structure | **identical** |
| prices, spreads, accrued | ≤ 6e-16 relative |
| durations, DV01 | ≤ 4e-13 |
| **convexity** | ≤ **7.5e-08 absolute** (the worst anywhere) |

Driver CSVs show the same shape: convexity 3.6e-8 relative on the corporate book, 1.7e-7
on the sovereign book (46-year bonds and 30 STRIPS amplify a little more), spreads
4.8e-11, durations 2.7e-13, **every text column identical**.

### ⚠️ Two quantities look alarming in RELATIVE terms and are machine epsilon in ABSOLUTE

This is the trap a plan will fall into if it reads a relative table without the values:

| field | value | absolute Δ | relative Δ |
|---|---:|---:|---:|
| `calibration_residual_per_100` | 6.6e-09 | 4e-14 | 6.5e-06 |
| `price_effect_per_1pct_vol` (an inactive put) | 1.1e-11 | 7e-15 | 6.6e-04 |

Both are **near zero by construction** — a residual is meant to be zero, and a put that
never binds has no volatility effect. A relative measure on them says nothing.

⇒ **Scale by `max(1, |x|)`, never by `|x|`.** That rule is in the code and in the tests.

---

## 3. ⭐ A documented claim that was false for two weeks

CLAUDE.md said *"the endpoint's JSON output is byte-for-byte the same as 47's"*. That was
written **2026-08-25**, when the endpoint priced **vanilla bonds only**. The lattice
products arrived on 08-31 and **nobody re-checked**.

It was found on 2026-09-13 by `tests/test_excel_fixture_parity.py`, whose first version
asserted exact equality: green locally, **five failures on 47**. Corrected in CLAUDE.md
the same day.

**The transferable part is not the fact but the shape of the mistake:** a claim was true
when made, the thing it described grew, and nothing was attached to the claim that could
notice. The same shape produced the stale module map (a whole round marked `PLANNED`
after shipping) and the stale currency list (six currencies documented while fourteen
were priced).

---

## 4. The tolerance, and why ONE number for everything was wrong

`tests/test_excel_fixture_parity.py` holds the endpoint to a per-quantity bound:

```
convexity          1e-6    measured 2.11e-08   47x headroom
everything else    1e-10   measured 3.87e-13   258x headroom
```

Scaled as `|a − b| / max(1, |b|)`, and non-numeric content is compared **exactly**.

⭐ **The first version used a single 1e-6 for every field and a mutation test caught it
before it shipped.** The reasoning looked sound — 47× headroom over the measured noise —
but the noise it was sized for is *convexity's*. Applied to a **price**, that same bound
let a deliberate 1e-4 perturbation through at 9.6e-07, just inside the limit. The
amplification is a property of the second-difference formula, not of the endpoint, so
only the amplified quantity may have the loose bound.

**Same shape as the `PAR_YIELD_UNITS` lesson: one rule covering two populations hides the
smaller one.**

A **set-level** check sits beside the per-fixture gates: the worst deviation anywhere, as
a fraction of its own budget, must stay under **10%** (measured 2.1%). Without it the
noise floor could grow tenfold with every per-fixture test still passing.

---

## 5. ⭐ The text fingerprint — the check that survives a library upgrade

`src/dataio/output_digest.py`. One rule, one owner:

> **a column is TEXT if any non-empty value in it fails to parse as a float**

Dates, identifiers, routes, flags and reason codes fail; prices, spreads and durations
pass. The digest hashes the full header plus the text columns' raw strings, so a rename,
a reorder, or a numeric column inserted between two text ones all move it.

**Why it matters:** text columns carry **no arithmetic**. They are decided by logic, so
they must be identical on every machine. A differing sha256 with a matching text digest
is rounding; **a differing text digest is a defect** — and the kind that hides. On
2026-09-03 a driver flag embedded a filesystem path and read
`data\KRW_Yield_Curve.txt` on Windows against `data/…` on Linux. A human found it by
diffing two CSVs. This is the comparison that would have found it automatically.

### ⚠️ Its first version was built on pandas, and pandas was the first thing to break it

It went through `pandas.read_csv(...).select_dtypes(...).to_csv()`. The first machine it
met was Azure Cloud Shell on **pandas 3.0**, comparing against a record written under
pandas 2.3. **All thirteen digests differed**, the report said "that is a defect" by its
own documentation, and nothing in the output could distinguish *the text changed* from
*the serializer changed*.

**A check meant to be invariant across platforms cannot rest on a library whose
behaviour varies across versions.** It is now standard-library `csv` only, and a test
asserts the module imports neither pandas nor numpy.

`tests/test_output_digest.py` pins the two properties that pull against each other:

* a float moving in its last digits — exactly what another processor produces — must
  **not** move the digest;
* any changed identifier, route, date or flag **must**.

### Reference values are published

`scripts/release_facts.py` now writes a **text-fingerprint table** into
`docs/release_facts_<date>.md` beside the hashes, so the comparison is automatic on any
machine instead of two people comparing two terminals.

---

## 6. The tools

| tool | answers |
|---|---|
| `scripts/release_facts.py` | *what did this machine produce* — rows, sha256, text digest, the real pytest line. **Written UTF-8 explicitly.** Quote docs from this, never from memory |
| `scripts/platform_parity.py` | *does THIS machine reproduce the published numbers* — `--run` executes every driver first, then compares rows / bytes / text against the newest record, and reports the endpoint tolerance budget |
| `tests/test_excel_fixture_parity.py` | the nine shipped v1.1 fixtures must reproduce; the two v1.0 ones are a **frozen corpus** held to a superset standard |

⚠️ **`platform_parity.py` exits 0 even when files differ. It is a report, not a gate.**
On another processor a differing hash is the expected reading, and an exit code calling
that failure would train people to ignore the text-column line, which is the one that
means something.

⚠️ **Driver order is load-bearing in that script**: `callable_risk.py` writes an UNDATED
CSV while its disposition sidecar is dated, so June runs **before** March. That leaves
both dated sidecars on disk and the undated file holding March, which is the run the
record was written from.

### Two reporting flaws the same first run exposed, both fixed

* a differing file printed `differs` and **not the hash it actually got**, so there was
  nothing to compare;
* the endpoint budget printed `0.00% at none`, which is **indistinguishable from a loop
  that never ran**. It now reports how many fixtures it compared. *A measurement that
  cannot tell you it measured nothing is not one.*

---

## 7. Rules a plan must not get wrong

1. **For byte-exact parity, compare local-fresh against local-fresh.** A cross-platform
   `sha256` diff of a driver CSV shows a difference that is NOT a regression. This has
   been the rule since Round 2b and it now extends to the endpoint JSON.
2. **Never assert that two platforms agree byte-for-byte.** Measure it, and re-measure
   when the thing being described grows. §3 is what happens otherwise.
3. **Row count and text digest are the regression signals.** A changed row count, or a
   changed text digest, is real. A changed hash alone is not.
4. **Scale numeric comparisons by `max(1, |x|)`.** Several published quantities are near
   zero by construction.
5. **A tolerance sized for the noisiest quantity is not a tolerance for the others.**

---

## 8. Open

* **The Azure text-digest question is UNRESOLVED as of 2026-09-15.** The run that raised
  it used the broken pandas-based check; the standard-library version has been pushed but
  not yet run there. Until it has, *do not record either "Azure matches" or "Azure
  differs"*.
* **`requirements.txt` has no upper version bounds.** Meeting pandas 3.0 was luck.
* **The Excel gate (57 fixture / 61 live) has not been re-run since 2026-08-31.** Nothing
  in its dependency chain changed, and the fixture measurement is stronger evidence for
  the Python side — but it must run before the next delivery that touches `endpoints/`
  or the `.bas`.
