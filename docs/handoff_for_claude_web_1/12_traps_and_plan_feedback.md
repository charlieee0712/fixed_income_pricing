# Traps, and feedback on your own plans

Two halves, both aimed at the same thing: stopping a plan from being wrong in ways that have
already happened here.

**Part A** is the accumulated silent-failure list — things that produce a plausible wrong
answer, or nothing at all, with no error to notice. **Part B** is what your previous plans got
wrong and the five habits that would have prevented nearly all of it.

Nothing in Part B is a complaint. The plans were well scoped and explicitly deferential to the
live repo, and their own instruction — "the live repo wins, adjust the plan" — is what made the
corrections cheap. The point is that most were avoidable at writing time.

(handoff 2 carries the same material with full forensics: its `05` and `06`.)

---

# Part A — silent failures

These are ordered by how expensive they were, not by likelihood.

## A1 ⭐ A market-data file in the wrong units, reported as bad market data

**The most expensive so far: two months, a standing request to two Bloomberg channels, and a
bond missing from every report we produced.**

`data/*_Yield_Curve.txt` are **not uniform**. 24 of 26 store par yields as decimals
(`0.0304` = 3.04%); **`GBP_Yield_Curve.txt` and `DKK_Yield_Curve.txt` store percent**
(`3.04` = 3.04%). The loader multiplied every file by 100, so the 2009-03-31 gilt curve arrived
as a **73%–415% par curve**, and the bootstrap did the right thing:

```text
Non-positive discount factor at t=3.000 (freq=1);
par curve is not arbitrage-free at this node.
```

That is **true about the curve we built and false about the file**. We recorded it as a
property of the data, wrote "our GBP file has a non-arb 3y node" into the missing-data
registry, and asked Mario *and* Liping for a replacement UK curve. The raw row was
`0.731 / 1.183 / 2.341 / 3.157 / 4.157` all along.

The fix is a **declaration, not a detection** — `curves.bootstrap.PAR_YIELD_UNITS` names the
two percent files — and the reason generalises: no threshold separates a 0.5% Danish yield from
a 0.5 decimal. DKK's median value is 0.543, so a "bigger than 1 ⇒ percent" rule would have got
GBP right and DKK wrong, by luck. A guard now raises `ParYieldUnitError` **before** the
bootstrap when a scaled row exceeds 100%.

**→ Habit 5, in Part B.**

## A2 A bond dropped by the driver without a flag

The same bug hid a second sterling bond, and this is the more instructive half: it was not
flagged, it was silently **skipped**. `TNTG301334W`, a plain fixed 5.50% of 2033, simply did
not appear — no row, no reason, and no count anywhere that went down. It is a
`Coupon_Formula2 = Fixed` bond, i.e. inside the class Mario had already been shown as
*finished*.

**A flagged bond is visible; a skipped one is not.** The driver header had been printing
`skipped=1` for months without anyone reading it. It now prints `skipped=0`.

When reasoning about coverage, the question is not "how many are flagged" but **"do priced +
flagged + excluded reconcile to the universe we started from?"**

## A3 An Excel date serial parsed as nanoseconds

`pandas.Timestamp(39903)` returns **1970-01-01**, not 2009-03-31. A date crossing the JSON
boundary as a *number* would price the bond on the wrong day, on the wrong curve, with every
output looking reasonable. Dates must be ISO **strings**; a number is refused. This is the
single most dangerous input error available in the interface, and the rule extends to dates
**inside schedules** (`bond.call_schedule[0].date`).

## A4 Two different day counts for the exercise-time axis

The coupon grid is ACT/364, but `to_lattice_schedule` still **defaults to 365.25 days/year**.
Both production drivers pass `days_per_year=364.0` explicitly, so production is correct — but a
new caller taking the default puts exercise dates on the wrong axis, silently. Route new code
through `core.pricing.tree.schedule_times`. (Fixing the stale default is a known follow-up.)

## A5 A put silently beating a call

The tree core applies `min(call)` then `max(put)`, so a put priced above a call on the same
date would silently resolve in the holder's favour. Refused at the wrapper layer; the core's
float path is untouched.

## A6 JSON `null` arriving in VBA as `Null`, not `Nothing`

`Set x = Field(response, "applicability")` raised "Object required" on **every** error
response — i.e. exactly when a user most needs to see the reason. Found only by running real
Excel. Fixed with a `FieldObject` accessor; now a regression check.

## A7 Edge headless writing no PDF and exiting 0

The bare `--headless` flag produces no file while still returning success. `--headless=new` is
required, along with a throwaway `--user-data-dir` and `--no-pdf-header-footer`. All three are
inside `scripts/md_to_pdf.py`; do not re-derive them.

## A8 The Drive staging copies breaking pytest

A root-level `pytest` run also walks the git-ignored staging folders, which contain duplicates
of the test files ⇒ "import file mismatch" and **zero tests run**. `pytest.ini` with
`testpaths = tests` is what prevents it — and that file must stay **ASCII**, because pytest
reads it with the system codec (GBK here) and one em dash aborts every run.

## A9 The 2010 Monthly batch looking like a golden

The legacy workbook's ~2,600 saved rows look like a reconciliation target. The 2010-03-01 batch
(the bulk) is a **stale session**: an older code revision run on mixed-vintage cached data.
Only the 2012-12 cohort is a numeric golden. All **474** callable/puttable/sinking rows and the
floating rows are in the stale batch, so those families have **no numeric golden at all** —
which is why the evidence hierarchy in `01` §6 exists.

## A10 Cross-platform CSV comparison showing a difference that is not a regression

Full 565-bond driver outputs from Windows and server 47 differ by up to **3.6e-8 relative,
entirely in `convexity`** — a second difference divided by the square of a 1 bp bump amplifies
a last-bit difference by 10⁸. Text columns identical; prices, spreads and durations agree to
~1e-12. Compare **local-fresh vs local-fresh**, which is byte-exact and therefore stricter.

## A11 Data traps worth knowing before quoting a number

- **The par-yield exports are not in consistent units** (A1). Assume the same of any *new*
  market-data file until checked against the actual market on a date you can verify.
- **The custodian's coupon columns in the master sheet are EMPTY** — terms come from the
  `Corporate Bonds` tab, joined on Asset ID (100% match), ISIN secondary.
- **`Coupon_Formula2` is column M**, not N. (Mario said N; the header confirms M, N is empty.)
- **Workbook tags are not authoritative.** One "zero coupon" was a custodian data error for a
  6.95% fixed bond (OAS −486 bp → +431 bp); two "(VAR)" / "Fixed→Reset" tags belonged to plain
  fixed bonds. A documented primary source outranks the cell.
- **`BZ > 1` factors are correct**, not corrupt — REMIC accrual (Z/VZ/ZC) tranches.
- **FRED's OAS history was truncated to a rolling 3 years in April 2026.** The full 1997–2025
  archive survives only inside `Pricing File.xlsm` / sheet `OAS Credit Curves`. Treasury `DGS*`
  series are government data and are **not** truncated.

## A12 Process traps

- **Do not re-ask a deferred question** before the next touchpoint (`01` §5).
- **Do not refresh the handoff bundles automatically** — only on explicit request.
- **Keep the handoff bundles out of the Drive package** — they carry internal comms framing and
  are not for Mario.
- **A number quoted from a CSV may be rounded.** A report's volatility table was once computed
  from a CSV's rounded spread and produced a row contradicting the report's own claim. Quote
  from a run, not from a summary.
- **A test fixture must not borrow a data defect.** Two endpoint tests used GBP as their
  "unbuildable curve" example, so fixing the curve broke them. Any fixture of the form "this
  real thing happens to be broken" will one day fail for the right reason and look like a
  regression.

---

# Part B — feedback on your previous plans

## B1 What was corrected, and why

Two plans were executed on 2026-08-25, both needing corrections at the alignment gate:

| plan | correction |
|---|---|
| JSON/Excel follow-up | the second operation's name and semantics; `face_value` semantics; the Excel-serial date hazard was unnamed; `CURVE_BUILD_FAILED` needed separating from `CURVE_NOT_FOUND` |
| Round 2 (embedded options) | the sinking-fund fraction basis was left "to the caller"; the plan asserted a call/put conflict rule already existed when it did not; **"FLOATING 426" was a URS production count attributed to the Monthly sheet**, where the actual label count is 29 |

**Round 2b (2026-08-30) had no plan from you** — the ask arrived as Mario's spreadsheet
annotations. Its five carry-over items from your last plan all landed, and item 2 earned its
place outright: it named in advance that the `frn.py` shim must re-export the **private** names
`_as_date`, `_df`, `YEAR_DAYS`, `simple_forward`, because `hybrid.py` imports them. It does, and
there is now a test named after the reason. **Naming the single most likely breakage in advance
is the highest-value line a plan can contain.**

## B2 The five habits

### Habit 1 — say where a number came from, and over what population

"FLOATING 426" was right as a URS production count and wrong as a Monthly-sheet count. Three
denominators are permanently in play here: **676** tab rows · **565** held positions · **555**
priced. Any count in a plan should carry its source and its population, or be marked for
verification at the gate.

### Habit 2 — never leave a modelling choice to "the caller"

The sinking-fund plan left the fraction basis (outstanding vs original face) to the caller.
Only *outstanding* is representable on a recombining tree; original face needs a strip
decomposition. Leaving it open would have shipped a parameter with one legal value and no
statement of why. **If a choice changes the mathematics, the plan makes it.**

### Habit 3 — never assert the current state of code; schedule a check

A plan stated that a call/put conflict rule existed. It did not. Write it as a gate item —
"confirm X exists; if not, add it" — rather than as a fact. You cannot see the tree.

### Habit 4 — name the silent-failure modes

The most valuable lines in these plans have been the ones naming what would fail *quietly*.
Every entry in Part A above was cheap to prevent and expensive to discover.

### Habit 5 ⭐ — a claimed data gap needs evidence from the SOURCE, not from our own error

Round 2b's largest finding was that a two-month-old registry entry — with a standing request to
both Bloomberg channels behind it — was our own bug (A1). Its only evidence had been our own
error message. Checking it against the raw file took minutes.

Two kinds of claim, and they are not the same:

| claim | status |
|---|---|
| "Bloomberg has not sent the pool factors" | a real gap — the absence is observable |
| "our engine reports the curve is not arbitrage-free" | a **symptom** — schedule a check against the raw source |

This is Habit 1 and Habit 3 extended to a third thing plans assert without checking: **the
reason something is blocked.** If a plan's scope depends on a blocker, put "reproduce the
blocker against the raw source" in the gate.

## B3 What the plans got conspicuously right — keep doing these

- **The alignment gate itself.** "The live repo wins; adjust the plan and record the
  adjustment" is why every correction above was cheap rather than a rewrite.
- **A strict/lenient boundary stated up front.** "Forgiving about presentation, firm about
  economics" survived contact with real Excel unchanged.
- **Refusing to treat stale caches as a target.** The plans never proposed reconciling to the
  2010 batch.
- **Preferring deferral to half-work.** Moving FRN out of Round 2a was right, and the reasoning
  given for it was the reasoning that held.
- **Leaving genuine scope calls to the execution side** where it has evidence you don't — e.g.
  "move FRN to next week if this is too much".
