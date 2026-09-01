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
