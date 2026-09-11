# Instruction — restructure the government book into the `pricer/` template

**Directive:** Mario, meeting of 2026-09-10 — next week's delivery is **Government Agencies**
and **Index Linked Government Bonds**, brought onto the code structure he approved on
2026-08-25 (`core/` engines + `assets/` thin wrappers + numbered inputs).

**Scope decision taken here:** **Guaranteed Fixed Income is included.** See §2.

**Written 2026-09-10, before any code.** Unlike the four previous rounds — whose plans each
needed a revision section written after the fact (`§21`, `§16`, `§26`, `§14`) — the alignment
gate is **§1 of this document and runs first**.

---

## §0. Why this round exists, and what it is not

Two of the three classes named below were built in **phase 2 (2026-07-22)** and have priced
correctly ever since. Nothing here is a repair. The ask is that they be **readable in the
structure the Google team will take over**, which today they are not:

| | today | after |
|---|---|---|
| Index-Linked engine | `src/pricing/ilb.py`, 150 lines, **never referenced from `src/pricer/`** | `core/pricing/inflation.py` + a wrapper |
| Agency conventions | `if` branches inside `scripts/phase2_risk.py` | named functions in `assets/government/agency.py` |
| Guaranteed bucket rule | one string literal in the loader | one named function + one test |
| `src/pricer/assets/` | contains **only** `corporate/` | gains `government/` |

⚠️ **The most important sentence in this round's report is a negative one:** Government
Agencies has **no engine of its own**. Every route it uses was migrated in Rounds 2a/2b.
What moves is the wrapper and the routing — not the mathematics. Do not let "we restructured
two classes" imply engine work that did not happen (see §8).

---

## §1. GATE 0 — run these BEFORE writing anything

Each check states the command, the answer expected on 2026-09-10, and what a different
answer means. **A differing answer stops the step and is reported, not worked around.**
Do not trust the counts in this document; the commands are the source.

### G0.1 — the shim contract

```bash
grep -rn "from pricing.ilb import\|from pricing import ilb\|pricing\.ilb\." \
     --include=*.py src/ scripts/ tests/
```

**Expected: exactly three importing sites**, and no import of a private name:

| site | names |
|---|---|
| `scripts/phase2_risk.py:38` | `ilb_risk_metrics`, `implied_spread_ilb` |
| `tests/test_ilb.py:9` | `ilb_risk_metrics`, `implied_spread_ilb`, `price_ilb` |
| `tests/test_price_convention.py:37` | `implied_spread_ilb`, `price_ilb` |

⇒ **the shim must re-export `price_ilb`, `implied_spread_ilb`, `ilb_risk_metrics` and
`IlbResult`.** Unlike the FRN migration, **nothing imports `_as_date` or `YEAR_DAYS` from
this module** — they are `ilb.py`-local. Re-export them anyway (one line, zero cost) but the
*contract* is the four names above.

**If a fourth importing site exists, the contract grew — extend it before moving anything.**

### G0.2 — the byte baseline

```bash
PYTHONPATH=src python scripts/release_facts.py      # or sha256 the 13 files directly
```

Record the sha256 of all **7 production CSVs and 6 disposition sidecars** now. Step 3's exit
test is byte-identity, and byte-identity cannot be proven without a *before*.

⚠️ **Parity is local-fresh vs local-fresh, never local vs 47.** Cross-platform convexity
differs by up to 3.6e-8 by construction (CLAUDE.md, Environment). A cross-platform hash diff
is not a regression and must not be read as one.

At `764022f` the expected values are:

| file | rows | sha256 (first 32) |
|---|---:|---|
| `phase2_risk_2009-03-31.csv` | 63 | `ea732f0ec3d52e74cbb97113492be71f` |
| `phase2_risk_2009-06-10.csv` | 63 | `fadd25a09b6d4128f5782bf3d038cc9c` |
| `implied_oas_2009-03-31.csv` | 566 | `020bdbbc2c81da5038b57d9ef636373c` |
| `implied_oas.csv` | 561 | `7929ff77df17db630c07689bd3799c20` |
| `callable_risk.csv` | 3 | `703292d505475b2e63cd495e008a4106` |
| `sovereign_risk_2009-03-31.csv` | 154 | `40baf346bbb8afbaf5c29cb195dc8df1` |
| `sovereign_risk_2009-06-10.csv` | 154 | `d91e3c8ff42724a48ce5e4ceb0855202` |

### G0.3 — the test baseline

```bash
& "C:\Users\cnc\anaconda3\anaconda2025\python.exe" -m pytest -q
```

**Expected: 424 passed.** Every later step re-runs this; new tests are additions, and a
number that *drops* is a regression regardless of what replaced it.

### G0.4 — is the landing site clean?

```bash
ls src/pricer/assets/ src/pricer/core/pricing/
```

**Expected: `assets/` contains only `corporate/`; `core/pricing/` has no `inflation.py`.**
If either already exists, someone started this round — reconcile before writing.

### G0.5 — the population, from the artifact rather than from this page

```bash
python -c "import pandas as pd; d=pd.read_csv('outputs/phase2_risk_2009-03-31.csv'); \
print(d.groupby(['asset_class','route']).size()); print(len(d))"
```

**Expected (source: the production CSV at 2009-03-31; population: the three phase-2 classes
of the master's `Asset sub category`):**

```
agency       call-passed-vanilla        4
             callable-lattice           5
             cmo-tranche                1
             vanilla                   27
             zero                       2
guaranteed   vanilla                    9
linker       ilb                       14
             ilb-indexation-unverified  1
                                      ---
                                       63
```

### G0.6 — is the module map still wrong?

```bash
sed -n '19,24p' src/pricer/__init__.py
```

**Expected: `tree.py`, `assets/corporate/callable.py` and `assets/corporate/floating.py` are
still marked `PLANNED`** although all three shipped in Rounds 2a/2b. If already corrected,
Step 4 shrinks accordingly.

---

## §2. Scope — and why Guaranteed cannot be left out

**Source: `src/dataio/phase2.py` (`PHASE2_CLASSES`), `scripts/phase2_risk.py`, and the
production CSV read in G0.5. Population: the master's `Asset sub category` column.**

| class | master rows | unique securities | engines it uses |
|---|---:|---:|---|
| Government Agencies | 42 | **39** | all already migrated |
| Index Linked Government Bonds | 16 | **15** | `pricing/ilb.py` — **not migrated** |
| Guaranteed Fixed Income | 11 | **9** | all already migrated |
| **total** | **69** | **63** | |

The three classes share **one loader** (`dataio/phase2.py`), **one driver**
(`scripts/phase2_risk.py`) and **one output file** — `phase2_risk_2009-03-31.csv`, 63 rows,
one of the hashed production artifacts.

Restructuring two of the three would leave the third as an un-migrated island inside migrated
code: one file owning half a decision, which is the shape this project has found and closed
five times (`TNTD04920858`; the `defaulted` class/reason collision; the `coupon_at` layering
violation; the GBP units registry; the two path-leaking flags). Guaranteed is **nine `vanilla`
securities with one reporting rule** — the `TLGP-guaranteed` bucket, which must never merge
into a bank rating bucket. It costs one function and one test.

**The work is not evenly distributed and the report must say so:**

- **Index-Linked = the only real engine migration.**
- **Agencies = wrapper and routing only.** No engine moves.
- **Guaranteed = a bucket rule.**

---

## §3. The two decisions already taken

Both were put to the user on 2026-09-10 with the evidence in hand, and both were adopted.

### ① Index-Linked does **not** get an endpoint type this round

`endpoints/contracts.py` carries seven `INSTRUMENT_TYPES`, all corporate. Adding an eighth
would touch the contract, the dispatch table and `schema_version`.

**Reason to decline:** the Excel side has **no ILB cells** — no index ratio, no real coupon,
no inflation assumption. The **7 / 5 / 5** discipline established on 2026-08-31 exists exactly
to stop a type becoming reachable from a worksheet whose layout Mario has not chosen. Migrating
the engine and the wrapper satisfies his ask; the endpoint is a separate contract decision.

⇒ **`contracts.py`, `pricing.py`, `schema_version` and the `.bas` bridge are untouched this
round.** Offer it in the report as ready when the sheet has the cells.

### ② `sovereign_risk.py` gets a thin government-side import path, not a rewrite

Last week's driver imports `pricer.assets.corporate.embedded_option` to price a **US
Treasury** (`scripts/sovereign_risk.py:57`). The module is **mis-located, not mis-written** —
it is the shared lattice surface, used by corporate callables, agency debentures and one
callable Treasury alike.

**Do not move it.** Relocating it would touch the corporate tree cluster and its hashed CSVs
for a naming gain. Instead, `assets/government/` provides a government-side path to the same
objects, so government code stops reaching into a corporate module by name.

⇒ **No driver rewrite.** The relocation of `embedded_option.py` to a shared level is recorded
in §7 as a named follow-up with its own criteria, not left implicit.

---

## §4. The steps, in risk order

Highest numerical risk first, so that a problem surfaces while the tree is still small.

### Step 1 — the ILB engine moves to `core/pricing/inflation.py`

**Do:**
1. Copy `src/pricing/ilb.py` to `src/pricer/core/pricing/inflation.py`. **The body below the
   module docstring is byte-identical** — same statements, same order, same float operations.
   Only the docstring is rewritten (numbered Inputs block, per the rollout rules).
2. Repoint its imports if any reach into `pricing.*`. **The core module must not import from
   the legacy `pricing` package** — that is the layering violation already closed once in
   `core/pricing/cashflows.py`.
3. `src/pricing/ilb.py` becomes a shim re-exporting the G0.1 contract.

**Naming, decided here, not left to the implementer:** the module is `inflation.py`, not
`ilb.py`. `core/` is named for the mathematics (`analytical`, `tree`, `floating`, `hybrid`,
`coupon_schedule`, `discounting`); `assets/` is named for the product. "ILB" is a product
name and belongs on the wrapper.

**Exit test:** `pytest -q` still **424**, and both `phase2_risk_*.csv` byte-identical to G0.2.
No new tests yet — the point of this step is that nothing observable changed.

**Silent-failure mode:** ⚠️ **a shim that re-exports a *different* object.** Tests import by
name and pass while production quietly runs a second copy. The structure test must assert
`pricing.ilb.price_ilb is pricer.core.pricing.inflation.price_ilb` — object identity, not
importability. This is the assertion pattern already used for the `lattice` and `frn` shims.

### Step 2 — `assets/government/` — the wrappers

New package, mirroring `assets/corporate/`'s shape:

| file | contents |
|---|---|
| `bonds_input.py` | the government input catalogue — numbered, with used-flags |
| `linker.py` | per-metric functions over `core.pricing.inflation` |
| `agency.py` | the agency conventions, currently `if` branches in the driver |
| `guaranteed.py` | the TLGP bucket rule |
| `sovereign.py` | the government-side path for §3② + last week's routing conventions |

**`linker.py` surface**, modelled on `assets/corporate/floating.py` (12 per-metric functions,
legacy units — percent and basis points):

```
calculated_price · accrued_interest · implied_spread_vs_nominal_bp · breakeven_bp
duration · dv01 · convexity · index_ratio
```

⚠️ **`implied_spread_vs_nominal_bp` keeps that exact name. It is never `implied_oas`.** The
number is approximately **minus the breakeven inflation rate**, not a credit spread; it is
negative for a healthy linker. A government module exposing a function called `implied_oas`
invites precisely the mix-up the separate output column was built to prevent.

**Input numbering, decided here:** government gets its **own** `INPUT_CATALOGUE`, starting
its own sequence and labelled as the government dictionary. It does not extend or renumber
corporate's 1–17. The catalogue mirrors the Monthly sheet's *per-family* input dictionary,
and a reader cross-referencing the wrong family is a silent failure (§6.3). Corporate's file
is not edited, so the 424 cannot move.

**`agency.py` — the conventions to name**, all currently implicit in `scripts/phase2_risk.py`:

- **Bermudan par call at 100 from the custodian AB date**, σ = 0.15 — the industry agency
  default, and the reason five debentures reach the lattice at all.
- **The call-passed rule** — a description carrying a one-time call date already in the past
  (`".../2006"`) with a blank AB is a bullet, flagged, not a callable.
- **The CMO-tranche refusal** — `TNTD04733316` ("SER 3122 CL ZB") is a REMIC Z-tranche
  misfiled as an agency debenture; it is carried at the custodian mark and priced in the CMO
  phase. **It is refused, never force-priced** (the Sempra lesson).
- Each carries its provenance in the docstring, matching the `exercise_terms_status`
  labelling already on all 8 lattice-priced bonds (0 confirmed, 9 of 9 rows provisional).

**Exit test:** new structure tests pass; all 7 production CSVs still byte-identical — nothing
imports the wrappers yet, so a moved number here would mean the *engine* moved.

### Step 3 — the driver

Two changes, and only the second can alter a number.

**3a — imports switch to `pricer.*`.** `scripts/phase2_risk.py:38` moves from `pricing.ilb`
to `pricer.core.pricing.inflation`. Drivers already import `pricer.errors`, and
`sovereign_risk.py` imports a `pricer.assets` module — but **every driver still reaches its
pricing engines through a `pricing.*` shim**, which is why criterion 1 of
`docs/shim_exit_policy_2026-08-31.md` reads "not met". This makes `phase2_risk.py` the first
driver to take an **engine** from the `pricer.*` path. Retire no shim; the corporate drivers
are untouched, so criterion 1 stays unmet and that is the intended state.

⚠️ **Which layer the driver calls, decided here: `core`, not `assets`.** The assets wrapper
is a *parallel* surface in legacy units (percent/bp) mirroring the Monthly sheet — it is not
a layer the driver passes through. `scripts/calibrate_risk.py` does not route through
`assets/corporate/vanilla.py` either. Sending the driver through the wrapper would push unit
conversion into the driver and break byte-identity for no gain.

Because Step 1 asserted the shim and the core export the **same object**, this import switch
*cannot* change a number — and byte-identity is the proof, not the hope.

**3b — `check_representable` is added to the agency lattice block.** `phase2_risk.py` builds
its call array by hand and, unlike `sovereign_risk.py:208`, never checks that the schedule
reaches an exercise node. This is the named carry-over from 2026-09-03 and the same defect
class as `TNTD04920858`, whose "option value = 0.000000" was the option never being evaluated.

⚠️ **This guard can only ever *refuse*, never reprice.** Expected outcome: all five agency
schedules reach a node ⇒ numerically inert ⇒ CSV byte-identical.

- **If the CSV stays byte-identical:** the guard was latent, exactly as on the corporate side.
  Say so — "latent, not live" — and do not dress it up as a fix.
- **If any row moves:** the guard is wrong. It must not reprice.
- **If a bond is now refused:** that is a **real finding** and the agency counterpart of
  `TNTD04920858`. It is reported with the bond named, and the refusal appears as a **named
  route in the output**, never as a missing row.

**Exit test:** both `phase2_risk_*.csv` byte-identical to G0.2; `pytest -q` green; the
driver's disposition arithmetic still accounts for every one of the 63.

### Step 4 — the map and the documents

- `src/pricer/__init__.py` lines 19–24: `tree.py`, `assets/corporate/callable.py`,
  `assets/corporate/floating.py` are marked `PLANNED` and have shipped. Correct them and add
  the new entries. ⚠️ This file is the **first stop in the code walkthrough** — an engineer
  reading it today is told the round-2 work does not exist.
- `CLAUDE.md`: a section for this round; update the sub-category table's status column.
- `WORKLOG.md`, `COVERAGE.md`.
- `docs/missing_data.md`: **no new entry.** The KTBi gap is already G5/G6 and is on the
  confirmation-only deferred queue.

### Step 5 — the Mario report

See §8.

---

## §5. What must not change

| | |
|---|---|
| All 7 production CSVs + 6 sidecars | **byte-identical**, local-fresh vs local-fresh |
| `pytest -q` | 424 → 424 + additions, never fewer |
| The Excel gate (57 fixture / 61 live) | untouched — `contracts.py` and the `.bas` are out of scope |
| `schema_version` | stays **1.1** |
| The counts | 63 rows · agency 39 · guaranteed 9 · linker 15 |
| `assets/corporate/` | not edited |
| The authoritative URS workbook | never written to |

---

## §6. Silent-failure modes named for this round

Listed in cost order, per the habit established in the handoff bundle's `05_traps_and_gotchas`.

1. **A shim re-exporting a different object.** Tests pass by name; production runs a second
   copy that can drift. ⇒ `is`-identity assertion, not an import check. (§4 Step 1.)
2. **`check_representable` changing a price instead of refusing one.** The guard tests
   *representability*, not economic activity — a fraction of 0 on a sinking date is a
   legitimate contract, and conflating the two broke two Round-2a tests once already.
   ⇒ byte-identity is the test; a refusal must surface as a named route.
3. **The government input catalogue renumbering or reusing corporate's 1–17.** A reader
   cross-referencing the Monthly sheet lands in the wrong dictionary and reads the wrong
   field description — wrong, and quiet. ⇒ own sequence, explicitly labelled.
4. **`implied_spread_vs_nominal_bp` renamed by a consistency pass.** A government function
   called `implied_oas` makes a breakeven read as credit. ⇒ a test that fails if the string
   `implied_oas` appears in `assets/government/linker.py`.
5. **A `core/` module importing from the legacy `pricing` package.** The result looks migrated
   and is not — the exact violation closed in `core/pricing/cashflows.py`. ⇒ a structure test
   over the new module's imports.
6. **Comparing the wrong output file.** The phase-2 CSVs are dated, so this one is already
   closed here; `outputs/callable_risk.csv` is still undated and remains a named carry-over
   (§7), not this round's problem.

---

## §7. Explicitly out of scope

| item | why, and what would reopen it |
|---|---|
| `src/pricing/mbs.py` (223 lines, un-migrated) | awaiting Mario's Bloomberg pull; not in this directive |
| An ILB endpoint type, `contracts.py`, `schema_version` | §3① — reopens when the worksheet has index-ratio / real-coupon / inflation cells |
| Rewriting `scripts/sovereign_risk.py` | §3② — thin import path only |
| Relocating `embedded_option.py` out of `assets/corporate/` | it is the shared lattice surface; moving it touches the corporate hashed CSVs. Reopens when a third non-corporate caller appears, or alongside the securitized layer |
| `outputs/callable_risk.csv` still undated | named carry-over from 2026-09-03; a 6-10 run overwrites a 3-31 run |
| Retiring any shim | `shim_exit_policy_2026-08-31.md` criterion 1 stays unmet for the other three drivers |
| **Any new Mario or Liping data request** | standing instruction. The KTBi terms, the KRW 3-31 curve row and the agency call schedules stay on the confirmation-only deferred queue until Mario returns the MBS data |

---

## §8. The report — what it should actually say

⚠️ **This round moves no number.** 63 securities before, 63 after, every file byte-identical.
That is the *proof of correctness*, but it is not a subject, and "we restructured two classes"
is a weak thing to put in front of Mario and the Google team in person.

**The subject is already computed and has never been in an outward report: what the
Index-Linked output means.**

- An inflation-linked bond's calibrated number is **approximately minus the breakeven
  inflation rate** — it reads the market's expectation of prices, not the borrower's credit.
  It is negative for a healthy linker, and that is correct, not an error.
- At **2009-03-31** those breakevens are the **deflation panic itself**, in the shape of a
  curve: short maturities pricing falling prices, long maturities still pricing inflation.
  The Japanese linker's sign flips the other way, and flips *correctly*.
- ⚠️ **Re-read those figures from `outputs/phase2_risk_2009-03-31.csv` at writing time.**
  Do not copy them from `CLAUDE.md` or from this document. Every number in a report is
  traceable to a run, not to memory (standing instruction).

**Then, in plain order:**

1. **Index-Linked** — the engine moved into the shared structure, and here is what it computes.
2. **Agencies** — say plainly that they were **already running on migrated engines**; what
   moved is the wrapper and the routing. Overstating this is the one honesty risk in the round.
3. **Guaranteed** — rode along, and *why it could not be separated*: one loader, one driver,
   one 63-row file. This is a good, concrete illustration of the structure for a finance reader.
4. **The proof** — 63 before, 63 after, every production file hash-identical. If 3b refuses a
   bond, that becomes finding 4 and is named.

Audience rules unchanged: plain language throughout, every bond term defined where it first
appears, and **one clearly-labelled engineering section** the finance reader can skip.

---

## §9. Exit checklist

- [ ] G0.1–G0.6 run and recorded, before any file was written
- [ ] `core/pricing/inflation.py` body byte-identical to `pricing/ilb.py` below the docstring
- [ ] `pricing/ilb.py` shim re-exports the four contract names; **object identity asserted**
- [ ] `assets/government/{bonds_input,linker,agency,guaranteed,sovereign}.py` exist
- [ ] `implied_spread_vs_nominal_bp` present; `implied_oas` absent from `linker.py` (tested)
- [ ] Government input catalogue numbered independently of corporate's
- [ ] `phase2_risk.py` imports `pricer.*`; `check_representable` guards the lattice block
- [ ] All 7 production CSVs + 6 sidecars byte-identical to G0.2 — **or a moved row explained
      and named**
- [ ] `pytest -q` ≥ 424, green locally **and on 47**
- [ ] Excel gate re-run only if anything under `endpoints/` or `integrations/` was touched
      (it should not have been)
- [ ] `src/pricer/__init__.py` map corrected
- [ ] `CLAUDE.md`, `WORKLOG.md`, `COVERAGE.md` updated; **no new entry in `missing_data.md`**
- [ ] `scripts/release_facts.py` re-run; the report quotes **that file**, not memory
- [ ] Report written per §8; delivery folder `code_structure_sample/` refreshed **after** any
      late edit to the source documents
- [ ] Handoff bundles **not** refreshed (explicit-request-only protocol; they are a round
      stale and still carry the "F13 = 2 rows, 1 held" error to fix at the next refresh)
