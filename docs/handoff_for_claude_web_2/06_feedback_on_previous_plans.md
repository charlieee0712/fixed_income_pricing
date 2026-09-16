# Feedback on your previous plans

**Update 2026-08-30 — read §5 first.** Round 2b was executed *without a plan from you*: the
ask arrived as annotations Mario wrote on a spreadsheet at the meeting. That round produced
a fifth habit, and §4's five carry-over items are now closed and scored. Everything below
§5 is unchanged and still applies.

---

Two plans you wrote were executed on 2026-08-25. Both were good: correctly scoped, properly
deferential to the live repo, and explicit about what was out of scope. Both also needed
corrections at the alignment gate, and the corrections fall into four repeatable patterns.
This file exists so the next plan does not repeat them.

Nothing here is a complaint. The plans' own instruction — "the live repo wins, adjust the
plan" — is what made the corrections cheap. The point is that most of them could have been
avoided at writing time.

---

## 1. What was corrected, and why

### Plan A — the vanilla JSON/Excel follow-up

| Correction | What the plan said | What was true |
|---|---|---|
| **`price_at_oas` added as a second operation** | Reject a supplied `oas_bp`; a `price_at_oas` operation "may be added if the project needs it" | The legacy per-metric functions (`CorpBondDuration`, `CorpBondwidening`) take a spread as an **input**. Rejecting the field with no named alternative was the plan's one piece of unnecessary strictness. ~15 lines to add. |
| **`face_value` semantics fixed** | listed as optional with a default of 100.0 | The plan never said what happens when it is *not* 100. Applying it while the caller also sends a per-100 mark silently calibrates to the wrong quantity. Decision: echo, warn, do not apply. |
| **The Excel-serial date rule added** | not mentioned | `pandas.Timestamp(39903)` = 1970-01-01. Without an explicit rule this was the interface's worst available failure. |
| **`CURVE_BUILD_FAILED` added** | vocabulary had `CURVE_NOT_FOUND` only | Verified on the server: CHF has no file, KRW has a file but not that date, and **GBP has both but its par curve is not arbitrage-free** — three situations, and reporting the third as "not found" sends someone hunting for a present file. |
| **Path sanitisation made a requirement** | "do not expose … paths" as a general precaution | The live `load_par_curve` puts `data/KRW_Yield_Curve.txt` **into its own exception message**. It was a concrete leak, not a hypothetical. |

### Plan B — Round 2 (embedded options and FRN)

| Correction | What the plan said | What was true |
|---|---|---|
| **Sinking fraction basis decided** | "The source adapter or caller must document whether the fraction is based on original or outstanding principal" | The *implementation* cannot defer this. Only the **outstanding** basis keeps value-per-unit level-free and the node path-independent on a recombining tree; original face needs a strip decomposition. v1 implements outstanding and refuses the other by name. |
| **The call/put conflict rule** | Gate 2 item 5: "add combined call/put low-level support **if not already present**" | Put support *was* present — but the §5.3 refusal the plan itself demanded was **not**. The core applies `min(call)` then `max(put)`, so a contradiction silently favoured the holder. The plan assumed a code state instead of scheduling a check. |
| **`FLOATING = 426 rows`** | quoted as a Monthly-sheet route count | Not in the extract at all: `mty_typ` contains **no** FLOAT label and `calc_typ_des` has **29**. 426 is the URS *production* floating count — a different population. |
| **Callable-family ≈ 449** | estimate | Verified **464** by substring on `mty_typ` (442 CALLABLE + 10 CALL/SINK + 5 PERP/CALL + 4 CALL/PUT + 2 CALL/EXT + 1 CONV/PUT/CALL). The plan's 449 counted a narrower set. Put 7 and sink 18 were exactly right. |
| **Q62:Q71 sharpened** | correctly fixed Q61:Q70 → Q62:Q71 | Correct, and better than remembered: column **P** carries the analysisType number 1–10 and column Q the label; row 67 shows the block is the option list of input #1, `AnalysisType`. |
| **"the clean four-commit result"** | baseline description | Seven commits by the time Round 2 started. Harmless, but it shows a plan hard-coding a state that moves. |

## 2. The four habits that would have prevented nearly all of it

### Habit 1 — say where a number came from, or mark it for verification

The plans' counts were mostly right and occasionally wrong, and nothing in the text
distinguished the two. A count that names its source is checkable in seconds:

> *good:* "callable-family ≈ 449 rows (`mty_typ` substring CALL, from
> `outputs/monthly_golden_rows.csv`) — **verify at Gate 0**"
> *risky:* "callable-family routes ≈ 449 rows"

And be explicit about **which population** a number describes. "FLOATING 426" was a true
number about the wrong universe. The repo has at least three populations that are easy to
conflate: the Monthly workbook rows (2,642), the URS corporate universe (~523–528 canonical),
and the priced output (564).

### Habit 2 — never leave a modelling choice to "the caller"

If the implementation must pick one behaviour, the plan should pick it, or explicitly say
"executor decides and records the reason". The sinking basis looked like a data-sourcing
detail and was actually the difference between a model a recombining tree can represent and
one it cannot. A useful test when writing: *could two readers implement this sentence
differently and both believe they followed the plan?*

### Habit 3 — never assert the current state of code; schedule a check

"if not already present" is a good instinct expressed in a way that produces no action. The
plans already have an alignment gate — put the assumption in it:

> *good:* "Gate 0: confirm whether the core refuses `put > call` on a shared date. It
> currently applies `min(call)` then `max(put)`; if there is no refusal, add one at the
> wrapper layer."

### Habit 4 — name the silent-failure modes

Both rounds' worst risks were things that fail by producing a plausible number or nothing at
all: the date serial, the 365.25-vs-364 axis (since closed), `null` in VBA, Edge writing no PDF. A short
"what could fail quietly here?" pass over a draft plan is high yield, because loud failures
get caught by tests anyway.

## 3. What the plans got conspicuously right — keep doing these

- **The alignment gate.** "The live repo wins; adjust the plan; record the deviation" is why
  every correction above was cheap instead of a re-plan.
- **The strictness/leniency split.** Naming which items are hard guards and which are the
  executor's choice removed nearly all judgement friction. Plan B's §0.1 is the best example
  in either document.
- **Refusing to make the stale 2010 cache a target.** Plan B stated it repeatedly, and it
  was right — all 474 tree-family rows turned out to be in that batch.
- **Deferring rather than half-building.** Plan B's escape hatch ("defer the endpoint
  dispatch without failing the round") was used, and the round is coherent because of it.
- **Explicit out-of-scope lists.** They prevented three plausible scope creeps (MBS,
  hybrid migration, a second Excel UI).
- **Offering the executor a scope decision** ("move FRN to next week if the week is too
  full") — that produced a better split than either extreme.

## 4. For the next plan (Round 2b) — CLOSED, and how they scored

Specific things folded in (verdicts added 2026-08-30):

1. **Re-derive the FRN cohort** from `outputs/monthly_golden_rows.csv`; do not reuse 426.
2. Schedule a Gate-0 check that the `frn.py` shim must re-export the **private** names
   `_as_date`, `_df`, `YEAR_DAYS`, `simple_forward` — `hybrid.py` imports them, and that is
   the single most likely way the FRN migration breaks.
3. State that hybrid outputs must be frozen **before** the migration and compared after, the
   same way the tree migration was proven.
4. Decide up front what the endpoint's `instrument_type` contract looks like for a floater
   (quoted margin, reset anchor, current coupon) rather than leaving it to the gate — the
   input set genuinely differs from the tree instruments'.
5. Say explicitly whether sinking joins the endpoint in the same change or stays deferred
   with a documented field map.

**How those five landed:**

1. ✅ Moot, in a useful way. The FRN cohort never needed re-deriving, because the round's
   population turned out to be **Mario's six pivot cells** (30 tab rows → 29 held), not a
   Monthly-sheet cohort. The warning was still right: 426 would have been the wrong number.
2. ✅ **This one earned its place.** The `frn.py` shim does re-export `_as_date`, `_rate`,
   `_df`, `simple_forward` and `YEAR_DAYS`, and there is now a test named after the reason
   (`test_floating_shim_still_carries_the_private_helpers_hybrid_needs`). Naming the single
   most likely breakage in advance is the highest-value line a plan can contain.
2. ✅ Hybrid outputs were frozen before and compared after — all five driver CSVs, hashed,
   after every code-bearing commit.
4. ✅ Decided up front, and the input set does differ: a floater has **no `coupon` field at
   all**, and gains `quoted_margin_bp` + `current_coupon_pct`. Deciding it before the gate
   was right.
5. ✅ **Sinking joined in the same change — and so did callable, puttable, hybrid and
   stepped.** All seven types landed in one contract change. Splitting it would have meant
   two, which is exactly what deferring dispatch to this round was meant to avoid.

---

## 5. Round 2b (2026-08-30) — no plan, and a fifth habit

**There was no plan from you this round.** Mario went down the coupon-type pivot at the
meeting and annotated a new column F: `finished` against the plain-fixed row, `no` against
six others. That column was the ask.

Two things are worth carrying into how you write the next one.

### The ambiguity that did not need resolving

"Finished" is genuinely ambiguous — it could mean "priced" or "in the new package". The
execution side did **not** stop to ask, because it checked and found that *both readings are
satisfied by the same work*: migrate the engines, produce the numbers, and hand back a
cell-by-cell status table. That is worth imitating. Before escalating an ambiguity, test
whether the candidate readings actually diverge in what you would do. Often they don't, and
the question costs a day.

### ⭐ Habit 5 — a claimed data gap needs evidence from the source, not from our own error

This round's largest finding was that a two-month-old entry in the missing-data registry —
"our GBP file has a non-arb 3y node", which had generated a standing request to *both*
Bloomberg channels — was **our bug**. The file stores par yields in percent while 24 of the
26 store decimals; our loader scaled it by 100 and the bootstrap correctly refused the
resulting 73%–415% curve. Full account: `05_traps_and_gotchas.md` §1.9.

The registry entry's only evidence had been our own error message. Checking it against the
raw file took minutes and would have shown a normal gilt curve.

**What this means for a plan.** When a plan cites a blocker, say **where the evidence comes
from**, and treat these two as different kinds of claim:

| claim | status |
|---|---|
| "Bloomberg has not sent the pool factors" | a real gap — the absence is observable |
| "our engine reports the curve is not arbitrage-free" | **a symptom**, not a gap — schedule a check against the raw source |

This is the same shape as Habit 1 (name a count's source and population) and Habit 3 (never
assert code state — schedule a gate check), extended to a third thing plans assert without
checking: **the reason something is blocked.** If a plan's scope depends on a blocker, put
"reproduce the blocker against the raw source" in the gate. It is cheap, and here it was the
difference between two priced bonds and a request to a client for data we already had.

### One more, smaller: don't let a test borrow a data defect

Two endpoint tests used GBP as their "unbuildable curve" fixture. Fixing the curve broke
them — correctly, but confusingly, because the subject of those tests was the error *mapping*,
not the state of a file. If a plan specifies a test whose fixture is "this real thing happens
to be broken", say so and prefer a constructed fixture.


---

## 6. The four rounds since (2026-08-31 -> 2026-09-15), and what they say about planning

None of these came from a web plan. Two came from a user-written instruction document,
one from the words "ultrathink start", and one from a question. That is not an argument
against planning -- it is the evidence for where a plan earns its cost, below.

| round | how it was specified | outcome |
|---|---|---|
| **08-31** Round 2b hardening | instruction doc, **Gate-0 revision in its 14, written BEFORE implementation** (6 adjustments) | 390 tests, 3 silent failures closed |
| **09-03** Government + Municipal | no document at all -- "ultrathink start" | 423 tests, 154 securities, 3 genuine findings, all 9 prior artifacts byte-identical |
| **09-10** Government book -> template | instruction doc written HERE, ⭐ **Gate 0 as section 1** | 468 tests, 63 securities unchanged, zero output moved |
| **09-13/15** interface sync + Azure | a question, then a request | 495 tests, 2 stale docs corrected, 1 false CLAUDE.md claim retracted |

### ⭐ The measurable finding: put the alignment gate FIRST, not last

**Four plans in a row each needed a revision section written after the fact** -- the
vanilla JSON follow-up (16), Round 2a (21), the Round 2b delivery-quality pass (26), and
the hardening instruction (14). Four for four. The cause is structural, not carelessness:
**a plan written away from the repository always drifts from it, and the drift surfaces
on contact.**

The 2026-09-10 instruction document therefore put the gate in its **section 1** and ran
it before a line was written: the shim's real contract, the hashes of all thirteen
production artifacts, the test baseline, whether the landing site was clean, the
population read from the artifact rather than from the page, and whether the module map
was still wrong. **All six passed and the thirteen hashes matched the record exactly**,
so the files on disk *were* the record and a valid baseline.

⚠️ **Front-loading the gate did NOT prevent the document from being wrong.** It claimed
the agency conventions were `if` branches inside the driver. They were not -- routing
already had a clean, well-named owner in `dataio.phase2._route_agency`. The difference is
that this was found in the first hour rather than after the code was written, and it was
**recorded as a correction in the document rather than quietly fixed**, so the next
reader sees both the claim and its retraction.

**For the next plan: state the gate as section 1, with the exact command and the exact
expected answer for each check, and say what a different answer means.** A gate whose
expected answers are not written down is a to-do list, not a gate.

### The round with no plan at all went fine, and that is also data

2026-09-03 went from "ultrathink start" to shipped: 154 securities, a locked curve
convention with a Fable consult before any code, three genuine findings, every
pre-existing artifact byte-identical. **A plan is worth its round trip when there are
open decisions or new modelling. It is overhead when the procedure is established and
the only decisions are already made.** The 09-10 round had exactly two open decisions,
both settled in one exchange before the document was written.

---

## 7. Three more habits, earned since

### ⭐ Habit 6 -- a verification tool must not depend on what it verifies

Two instances in three days, and both were tools built to catch other people's mistakes:

* the cross-platform **text digest** was computed through
  `pandas.select_dtypes(...).to_csv()`. Its first machine ran pandas 3.0 against a record
  written under 2.3; all thirteen digests differed and nothing could say whether the text
  had changed or the serializer had. A check meant to be invariant across platforms
  cannot rest on a library whose behaviour varies across versions.
* the endpoint **tolerance** used one bound for every field, sized from the noisiest
  quantity's noise. Applied to a price it let a 1e-4 perturbation through.

**Before shipping a check, ask what the check itself depends on, and whether that thing
is more stable than the thing being checked.** If not, the check will fail first and
will fail confusingly.

### ⭐ Habit 7 -- mutation-test every new lock, or it may be decorative

Every lock added since 2026-09-10 was verified by **making it fail on purpose** and then
restoring. It was not ceremony; two of them were weak:

* the fixture-parity tolerance passed a deliberate 1e-4 price change (Habit 6 above);
* a threshold-consistency test had an `or` fallback on a hardcoded string, so half the
  assertion did not reference the constant it claimed to pin.

Both were found by mutation and both were fixed before shipping. The module-map locks
were validated the same way -- reverting to the historical map turned all three red,
which is the only reason we know they bind rather than merely pass.

**A test that has never been seen to fail is a hypothesis.**

### ⭐ Habit 8 -- do not hand-maintain a number that has an authoritative source

Three separate instances in one week, all found by accident:

| what said it | what it said | truth |
|---|---|---|
| `pricer/__init__.py` module map | tree/callable/floating `PLANNED` | shipped months earlier |
| `bonds_input.py` input catalogue | 6 currencies | 14 |
| the interface document's header | "194 automatic checks", "Scope: vanilla" | 495, seven types |

Each was a **prose copy of a fact that lives somewhere authoritative**. The fixes were
the same in shape: compute it (`" / ".join(supported_currencies())`), stop quoting it
(point at the dated `release_facts`), or attach a test that fails when the copy and the
source disagree.

⚠️ **The direction that rots is not always the obvious one.** Two of the three module-map
tests written that day would have missed the actual failure; the load-bearing one was
*"nothing marked PLANNED may already exist"* -- an entry that is present, parses fine,
and is simply untrue.

---

## 8. What the recent rounds got right -- keep doing these

* **Byte-identity as the exit test for a restructure.** "63 securities before, 63 after,
  every one of 22 output files identical after re-running every driver" is a
  restructuring proving it was one. It is also what made the 09-10 report honest.
* **Recording a correction instead of quietly fixing it.** The 09-10 instruction
  document keeps its wrong claim visible above the retraction; CLAUDE.md keeps the
  false cross-platform claim above its correction. A reader learns the shape of the
  mistake, not just the current state.
* **Reporting a guard that found nothing as having found nothing.** `check_representable`
  was added to the agency lattice and refused nothing -- all five schedules reach a node.
  The report says **"latent, not live"** rather than dressing it as a fix.
* **Naming the population beside the median.** The linker breakeven is *85 bp over 13
  linkers, near-maturity excluded -- the driver's own population*. All 14 gives 82.
* **Leading a report with the finance, not the refactor.** The 09-10 round moved no
  number, so the report leads with what the inflation-linked output *means* -- a
  deflation curve from -34 bp to +139 bp, and a Japanese bond at -229 bp whose sign flips
  the right way. "We restructured two classes" would have been a weak thing to present.
