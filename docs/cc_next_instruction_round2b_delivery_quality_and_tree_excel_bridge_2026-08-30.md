# Final Claude Code Instruction — Round 2b Delivery-Quality Hardening, Plus a Separate Embedded-Option Excel/JSON Attachment

**Date:** 2026-08-30  
**Project:** RYSE Fixed-Income Pricing  
**Execution owner:** Claude Code on the private live repository  
**Expected starting point:** latest clean live HEAD, currently reported as `a5f7c81`, 287 pytest checks green locally and on server 47, origin and 47 synchronized  
**Scope rule:** no new pricing engine, no new bond type, no new production route, and no expansion into MBS or another workstream

---

## 0. Executive direction — two separate workstreams, not one blended task

This instruction contains **two independent workstreams**.

### Workstream A — PRIMARY and mandatory

Improve the delivery quality of the work completed this week:

- the FRN engine reconstruction;
- the fixed-to-floating hybrid reconstruction;
- the coupon-schedule reconstruction;
- Mario's `Pivot of Corp Bonds` column-F request (`F12:F16` and `F20`);
- the GBP/DKK par-yield units correction;
- the resulting coverage and completeness claims.

This is the main purpose of the instruction. It must produce a stronger evidence trail, a cleaner Mario/Google-team handoff, and better protection against silent omissions. It must stand on its own even if Workstream B is delayed.

### Workstream B — SECONDARY and additive

Separately connect the **existing** Excel/VBA–JSON interface to the already-built:

```text
callable
puttable
sinking
```

This is follow-through on the prior report's interface story. It is **not** part of the proof that Mario's six column-F rows were completed, and it must not dilute or replace Workstream A.

The Python endpoint already supports these tree types. The remaining task is the Excel bridge and real-Excel validation. Do not create another engine, another endpoint, or another product type.

### Sequencing rule

```text
Gate 0
→ complete and checkpoint Workstream A
→ only then begin Workstream B
→ final package may contain both, but the report must describe them as separate accomplishments
```

If time becomes constrained, **finish Workstream A fully and defer Workstream B cleanly**. Do not ship a partially evidenced Round 2b deliverable in order to complete the Excel extension.

---

## 1. Source facts and user confirmations

### 1.1 Mario's column-F directive

The Project's source-safe URS workbook predates the later annotations. The user supplied a screenshot of Mario's edited `Pivot of Corp Bonds` sheet. Treat that screenshot as the evidence for the meeting directive.

Transcribe only the visible values:

| Cell | Visible text |
|---|---|
| `F5` | `finished` |
| `F12` | `no` |
| `F13` | `no` |
| `F14` | `no` |
| `F15` | `no` |
| `F16` | `no` |
| `F20` | `no` |
| `F21` | `just corp bond(fixed)` |

Do not infer instructions from blank cells.

Create or confirm one compact internal evidence record:

```text
docs/client_directive_pivot_column_f_2026-08-27.md
```

It should state:

- the sheet and exact cells;
- the exact transcription above;
- that Mario made the annotations during the meeting;
- that the user supplied the screenshot;
- that the source-safe Project copy does not contain the later edits;
- that `finished` is interpreted as “present in the restructured `pricer/` package,” not merely “historically priced”;
- that rows 6–11 were adjacent shared-engine coverage, not six additional explicit requests.

Do **not** modify the authoritative URS workbook merely to insert those annotations.

### 1.2 Project Sources

The user has already cleaned the Project Sources and does not want another source-cleanup task. Do not spend this round searching for or deleting old Project attachments.

### 1.3 Communication status

Record the confirmed facts:

- Mario discussed the 2026-08-25 report in the meeting;
- he agreed with the next-week plan;
- the column-F annotations became the operational request.

Do not mark the 2026-08-30 package as delivered unless the user separately confirms that it was sent or uploaded.

### 1.4 Expected live baseline — verify, do not assume

Expected current state:

```text
pytest                         287 green
Excel bridge checks            23 green
endpoint schema                1.1
endpoint instrument types      7
visible Excel demo             vanilla only
corporate output @ 2009-03-31  565 = 555 priced + 10 flagged
production skipped             0
```

The live repository wins if any of these has moved. Every count used in a report or test must name its source and population.

---

## 2. Global boundaries and locked rules

These apply to both workstreams.

1. Do not change any pricing, cash-flow, accrued-interest, curve, OAS, tree, FRN, hybrid, or risk formula.
2. Do not change ACT/364, the 182-day grid, clean/dirty treatment, dirty-price risk denominator, or per-100 units.
3. `calibrate_and_risk` continues to take clean market price and return implied OAS.
4. `price_at_oas` remains the named operation that accepts an explicit OAS.
5. Currency selects the bond's own-currency curve and performs no FX conversion.
6. Old module paths remain shims unless a separately approved retirement decision is made.
7. No new Mario/Liping data request is opened in this round.
8. A program error is a symptom, not proof of a missing-data problem. Check the raw source before classifying a blocker.
9. Do not use the 2010 Monthly cache as a numeric target.
10. Do not refresh either Claude-web handoff bundle unless the user explicitly asks.
11. Do not add batch JSON mode, HTTP/FastAPI, a cloud service, or a second bridge.
12. Do not decide Mario's final multi-product Excel layout before he answers the open UI question.
13. Do not create a new report for a new product family. This is a quality and integration pass over work already completed.

### Platform parity rule

The full production CSVs are deterministic **within** each environment, but Windows and Linux can differ in the last convexity digits. Therefore:

- compare local fresh output against the local frozen baseline;
- compare 47 fresh output against the 47 frozen baseline;
- do not require cross-platform CSV byte identity;
- retain exact endpoint-versus-wrapper equality and any verified cross-platform endpoint JSON identity.

---

## 3. Gate 0 — live alignment and freeze

Before changing code, VBA, tests, or documents:

1. Record live HEAD, branch, clean-tree status, remotes, and sync status.
2. Run the full pytest suite locally and on 47.
3. Run every current production driver at:
   - `2009-03-31` baseline;
   - `2009-06-10` control, where the driver already supports it.
4. Freeze and hash every driver output separately on local and 47.
5. Run all existing real-Excel bridge checks in both modes:
   - stand-in/fixture runner;
   - local Python runner.
6. Inventory the live paths and public functions for:

```text
src/pricer/core/pricing/floating.py
src/pricer/core/pricing/hybrid.py
src/pricer/core/pricing/coupon_schedule.py
src/pricer/assets/corporate/floating.py
src/pricer/assets/corporate/hybrid.py
src/pricer/assets/corporate/stepped.py
src/pricer/endpoints/
integrations/excel_vba/
```

7. Confirm the exact live schema-v1.1 field names for all seven instrument types. Do not rebuild field names from memory.
8. Confirm the exact current list of production drivers and their output files.
9. Confirm whether the full-disposition and fifth-callable checks described below already exist.
10. Confirm whether the current VBA request builder is vanilla-specific or already partly generic.

If reality differs from this instruction, edit this file in place, add a dated revision section with evidence, commit the revision first, and then execute.

---

# WORKSTREAM A — Mandatory Round 2b / Column-F Delivery-Quality Hardening

## 4. Objective of Workstream A

Workstream A should make the following statement fully auditable:

> Mario marked six coupon-family rows as not yet restructured. All six now map to migrated core engines, thin asset wrappers, the common endpoint contract, tested production routes, and a cell-by-cell status table. The six securities that do not produce model outputs are blocked by named data/recovery reasons rather than by missing code.

The task is not to add more functionality. It is to prove, explain, package, and guard what was already built.

---

## 5. A1 — Build one authoritative column-F delivery matrix

Create one generated or carefully reconciled artifact, preferably:

```text
docs/column_f_delivery_matrix_2026-08-30.md
```

A companion CSV is useful if it can be generated cheaply:

```text
outputs/column_f_delivery_audit_2026-08-30.csv
```

For each of Mario's six cells, include:

```text
cell
workbook label
pivot-row count
held-position count
priced count
flagged / recovery count
current route or route family
core engine
asset wrapper
endpoint instrument_type
essential input fields
missing-data landing file, if any
validation evidence
one representative output or status
```

The top-level counts should reconcile exactly to the current live source:

| Cell | Coupon family | Pivot rows | Held | Priced | Not priced |
|---|---|---:|---:|---:|---:|
| `F12` | Fixed → Floating | 5 | 5 | 4 | 1 |
| `F13` | 7.00% / 7.50% date-segmented | 2 | 1 | 1 | 0 |
| `F14` | GBP LIBOR + Spread | 1 | 1 | 1 | 0 |
| `F15` | Reference Rate + Spread | 12 | 12 | 11 | 1 |
| `F16` | EURIBOR + Spread | 9 | 9 | 5 | 4 |
| `F20` | Step-up schedule | 1 | 1 | 1 | 0 |
|  | **Total** | **30** | **29** | **23** | **6** |

Verify these at Gate 0 before retaining them.

State the three populations explicitly wherever the table appears:

```text
676 = Corporate Bonds tab / pivot rows
565 = held, rated, matched output rows at 2009-03-31
555 = fully model-priced rows at 2009-03-31
```

Do not merge the adjacent `Fixed → Reset` rows 6–11 into Mario's six-cell count. Report them separately as shared-engine coverage:

```text
6 pivot rows → 6 held → 3 priced
```

Do not count `F21` as a newly built structured-payoff engine. Mario's annotation says it remains an ordinary fixed corporate bond, and that is the current treatment.

---

## 6. A2 — Produce a code-reconstruction manifest

Create or add to the engineering walkthrough one concise reconstruction map:

| Legacy implementation | New core location | Old-path shim | Asset wrapper | Endpoint type | Main proof |
|---|---|---|---|---|---|
| `pricing/frn.py` | `pricer/core/pricing/floating.py` | retained | `assets/corporate/floating.py` | `floating` | body identity + driver hash + direct `==` |
| `pricing/hybrid.py` | `pricer/core/pricing/hybrid.py` | retained | `assets/corporate/hybrid.py` | `fixed_to_floating` | body identity + degenerate limits + direct `==` |
| `pricing/coupon_schedule.py` | `pricer/core/pricing/coupon_schedule.py` | retained | `assets/corporate/stepped.py` | `stepped` | body identity + direct `==` |

Verify and document:

1. The numerical bodies remain byte-identical below the permitted docstring/import changes.
2. Old-path shims re-export the same objects, not equal reimplementations.
3. The FRN shim still exposes every private helper required by hybrid compatibility.
4. `core/` no longer reaches upward into the legacy `pricing` package for `coupon_at`.
5. Each asset wrapper contains unit conversion and orchestration only, not duplicated pricing arithmetic.
6. Each endpoint result equals the direct asset-wrapper result with exact equality.
7. Typeless v1.0-style requests remain vanilla and unchanged.
8. `bonds_input.py` accurately marks which fields are used by floating, hybrid, and stepped products and shows the correct JSON paths.

Do not refactor the private-helper coupling in this pass. It is already protected by an explicit compatibility test; rewriting it would reduce auditability rather than improve this week's delivery.

---

## 7. A3 — Strengthen the FRN and hybrid evidence package

The report should not reduce every FRN to the sentence “duration is approximately time to next reset.” That is only one regime.

Create a compact internal evidence memo or expand the round detail with the following controlled checks.

### 7.1 Floating-rate note checks

Prove and show:

1. **Par-floater identity:** with quoted margin = 0 and OAS = 0, the floater remains at par under controlled parallel curve shifts.
2. **OAS round trip:** solve to a clean price, then reprice at the solved OAS.
3. **Current coupon supplied:** effective duration is approximately the positive time to the next reset.
4. **Current coupon omitted/projected:** effective duration is approximately the negative time since the prior reset because the current period's coupon is reprojected.
5. **Deep-discount case:** a long floater can have materially negative duration; explain that this is a spread-annuity effect, not a sign bug.
6. **Fixed-bond comparator:** in all selected examples, compare with a same-maturity fixed bond so the structural risk reduction is visible.
7. **Spread interpretation:** when `quoted_margin_bp` is unknown and set to zero, label the calibrated result as a discount-margin-like number that absorbs both the missing contractual margin and credit. Do not call it a clean credit spread.

Use fresh run values. Do not copy old rounded numbers without recomputing them.

### 7.2 Fixed-to-floating hybrid checks

Prove and show:

1. `switch_date >= maturity` delegates exactly to vanilla.
2. `switch_date <= valuation_date` delegates exactly to the FRN engine.
3. With margin = 0 and OAS = 0, the floating leg telescopes to `face × DF(switch)` on the chosen curve.
4. One curve and one OAS price both legs.
5. `reference_oas_to_switch_bp` is clearly labelled as a reference metric and potentially misleading for deep-discount extension-risk names.
6. Every live hybrid at the baseline is still in its fixed leg, if that remains true in the current data.
7. Missing post-switch margins lead to named BT-marks, not zero-margin half-models.

### 7.3 Scheduled-coupon checks

Show that:

1. a known stepped schedule uses the existing vanilla discounting engine with a coupon table;
2. an unparseable or unsupported schedule is refused rather than guessed;
3. documented override schedules outrank workbook free text;
4. `F13` and `F20` are schedule variations, not new stochastic models.

This evidence should be understandable to the Google team without requiring them to read the full engine files.

---

## 8. A4 — Reconcile every held name behind the six cells

For the 29 held positions behind Mario's six cells, produce a complete disposition table with at least:

```text
Asset ID
security description
column-F cell
coupon family
currency
route
terms source
priced / BT-marked / recovery
missing field, if any
landing CSV, if any
output row present? yes/no
```

Acceptance logic:

```text
29 held
= 23 model-priced
+ 5 hybrid-margin-unavailable
+ 1 recovery
```

Verify the exact category names from the live output.

For the five margin-gapped names:

- confirm each is already on the existing Bloomberg request;
- confirm the missing field lands in the documented CSV;
- confirm a data arrival requires no pricing-code change;
- do not open a new request.

For the defaulted name:

- confirm it is intentionally carried at the recovery/custodian mark;
- confirm no OAS is presented.

This table is internal evidence; the Mario report can show the six-cell aggregate and a concise explanation.

---

## 9. A5 — Harden the GBP/DKK units correction

The GBP issue is the most important quality finding of the round because it was previously misclassified as missing market data and also hid one plain fixed bond completely.

### 9.1 Source-level unit proof

Confirm from the raw files, not from an exception:

- 24 par-yield files use decimal storage;
- `GBP_Yield_Curve.txt` and `DKK_Yield_Curve.txt` use percent storage;
- the explicit registry, not a threshold heuristic, controls conversion.

Do not add a value-sniffing heuristic.

### 9.2 Regression protection

Retain or add focused tests for:

1. explicit file-unit registration;
2. correct conversion of one known GBP row;
3. correct conversion of one known DKK row, including the low/negative-rate regime that would defeat a threshold rule;
4. `ParYieldUnitError` before bootstrap when the scaled row exceeds the allowed guard;
5. synthetic/monkeypatched `CURVE_BUILD_FAILED` mapping, rather than depending on a real file remaining broken;
6. both GBP bonds appearing in the 2009-03-31 output;
7. driver `skipped=0`.

### 9.3 Intentional output-change isolation

Reproduce or verify a focused before/after table for the GBP fix:

```text
France Télécom GBP 7.50% 2011  blocked → priced
UK EMTN fixed 5.50% 2033       absent → present and priced
corporate output               564 → 565
fully priced                   553 → 555
flagged                        11 → 10
```

Use the actual pre-fix commit/output and current run, or the existing frozen evidence if it is already committed and reproducible. Do not reconstruct the values from memory.

Confirm that no unrelated production row changed because of the unit fix.

### 9.4 Active-document audit

Search the **active outward-facing package**, open-questions file, and missing-data registry for stale statements such as:

```text
GBP curve is missing
GBP curve is not arbitrage-free
replacement GBP curve required
one GBP bond remains blocked
```

Correct active statements and add supersession notes where history must remain. Do not rewrite old historical reports as though the mistake never happened.

---

## 10. A6 — Close silent-disappearance and callable-count gaps

### 10.1 Full-disposition invariant

The plain GBP bond showed that a security can be neither priced nor flagged and disappear from every headline.

Inspect the current test suite. If it does not already prove full set equality, add one high-value Asset-ID-level invariant:

```text
eligible starting population
=
priced output
∪ named BT-marks / flags
∪ locked intentional exclusions
```

Require:

- mutual exclusivity;
- exhaustiveness;
- clear failure output listing missing or multiply classified Asset IDs;
- `skipped=0` as an operational guard.

Do not settle for count equality alone.

### 10.2 The five-name corporate callable bucket

The current summary says:

```text
callable bucket = 5
3 lattice-priced
1 AssuredGty awaiting a schedule
```

That accounts for four. Derive the complete five-name set from the live universe and route output.

Document for each:

```text
Asset ID
security
why it is in the callable bucket
current route
schedule source/status
priced / BT-marked / excluded
output row present? yes/no
```

Do not assume the fifth is the historical short-gap callable. Verify it.

Update the current-state and coverage documents so a count of five is followed by five named dispositions.

This is a bookkeeping and completeness closure. Do not change a route merely to make the table neat.

---

## 11. A7 — Improve the Mario/Google-team report and walkthrough

The current report's main story remains:

1. Mario marked six column-F cells.
2. All six are now covered in the restructured package.
3. 30 pivot rows correspond to 29 held positions, 23 model-priced and 6 intentionally not model-priced.
4. F14 exposed our GBP units bug, not missing data.
5. One additional plain fixed GBP bond had been silently omitted and is now present.

### 11.1 Report quality requirements

Review the active weekly report against a fresh run and ensure it:

- names the three denominators before presenting counts;
- explains `finished` as “migrated into `pricer/`,” not merely “priced”;
- treats rows 6–11 as adjacent shared-engine coverage, not part of the explicit six-cell ask;
- explains that five unpriced names await margins and one is defaulted;
- says those six are not code/model gaps;
- distinguishes a quoted-margin credit spread from a discount-margin-like result when the contractual margin is unknown;
- describes the two FRN duration regimes and avoids a universal “time to next reset” claim;
- states the GBP correction plainly as our bug;
- withdraws the replacement-GBP-curve request;
- explains that `skipped=0` is now enforced, not merely observed;
- includes one clearly labelled engineering section for the Google team;
- does not claim a polished seven-type Excel demo;
- keeps the existing question to Mario about final worksheet layout.

Every number in the report must be recomputed from a current output or committed evidence artifact. Do not copy from a summary table without checking the underlying row.

### 11.2 Engineering walkthrough

Update the walkthrough so the Google team can follow, in file order:

```text
raw workbook coupon family
→ router / override table
→ migrated core engine
→ thin asset wrapper
→ endpoint instrument_type
→ production driver / JSON output
→ validation evidence
```

Include a short “what changed numerically” section:

```text
migration changes             none
intentional GBP-units change  two GBP securities and headline counts only
```

### 11.3 Package QA

Before staging:

- regenerate PDFs with the existing script;
- verify the files actually exist and are non-empty;
- rebuild staging with `robocopy /E`, never `/MIR`;
- exclude handoff files, internal planning prompts, `__pycache__`, and wholesale `docs/` copies;
- include only the project-built demo workbook, never the authoritative URS workbook;
- ensure the active report, walkthrough, interface reference, code, tests, and examples agree on the current test count and interface status;
- verify the zip opens and list its members;
- put commit, test count, package date, and the primary run commands in `00_README.md`.

---

## 12. Workstream A tests and acceptance criteria

Do not target an arbitrary number of new tests. Add only tests that close a real evidence gap.

Workstream A is complete when:

1. The full suite is green locally and on 47.
2. Production outputs are unchanged from the current post-GBP baseline within each environment.
3. The only documented intentional historical change remains the GBP-unit correction.
4. The six-cell matrix reconciles `30 pivot → 29 held → 23 priced + 6 named non-priced`.
5. Every one of the 29 held names has a unique disposition.
6. Every migrated engine has body/shim/wrapper/endpoint parity evidence.
7. FRN and hybrid economic identities are demonstrated with fresh runs.
8. The report accurately distinguishes both FRN duration regimes.
9. The spread-interpretation caveat is visible wherever unknown margins are represented by zero.
10. Both GBP bonds are present, `frn-curve-blocked` is empty, and `skipped=0`.
11. The full eligible corporate population has a mutually exclusive, exhaustive disposition.
12. All five callable-bucket names have documented statuses.
13. The current report and walkthrough contain no stale active GBP-gap claim.
14. The delivery package passes content, PDF, zip, and confidentiality checks.
15. No new bond type, pricing model, data request, or production route has been opened.

### Mandatory checkpoint

Commit and record completion of Workstream A before beginning Workstream B. At this point, the week's core deliverable must already be ready to send even if Workstream B is stopped.

---

# WORKSTREAM B — Separate Excel/JSON Attachment for Callable, Puttable, and Sinking

## 13. Objective and positioning of Workstream B

Workstream B is a separate integration follow-through:

> Extend the existing Excel/VBA bridge so it can send the already-supported callable, puttable, and sinking schema-v1.1 requests and display their common results, without changing the pricing engine or choosing the final customer-facing workbook layout.

It must not be described as proof of Mario's column-F reconstruction. It may appear in the report only under a separate heading such as:

```text
Additional integration follow-through — embedded-option bonds through Excel
```

If Workstream B is not completed before delivery, omit that claim and deliver Workstream A without weakening it.

---

## 14. B1 — Architecture decision

Reuse the existing:

```text
RysePricingBridge.bas
VBA-JSON parser
runner command
scripts/price_json.py
pricer.endpoints.main.analyze_payload
schema-v1.1 envelopes
```

Do not create:

- a second bridge;
- a second parser;
- a tree-specific endpoint;
- a second JSON contract;
- a `combined_option` instrument type;
- pricing logic in VBA;
- a new polished workbook design.

Refactor the existing bridge only enough to separate:

```text
common scalar inputs
operation selection
instrument-type selection
instrument-specific fields
schedule-table serialization
runner invocation
common response mapping
```

Preserve all existing public macro/button entry points. A vanilla-specific public macro may become a compatibility wrapper over a generic internal builder, but must not disappear.

A request with no `instrument_type` must remain the exact current vanilla path.

---

## 15. B2 — Layout-neutral Excel QA surface

Mario has not yet chosen:

```text
one adaptive worksheet
versus
one small worksheet per product type
```

Do not answer that question for him.

Preferred implementation:

- keep the existing polished vanilla demo unchanged;
- extend the real-Excel test harness and, if useful, add a clearly labelled engineering/QA sheet or builder-generated test workbook;
- use workbook-level named ranges and named Excel Tables so the bridge is independent of final sheet placement;
- label any visible engineering surface:

```text
Technical QA surface — not the final daily-use layout
```

Avoid dynamic show/hide logic, UserForms, ActiveX controls, and a worksheet per product in this pass.

---

## 16. B3 — Stable Excel identifiers

Adapt names to the live convention rather than duplicating equivalents.

Suggested optional scalar names:

```text
FIP_InstrumentType
FIP_Operation
FIP_OASBp
FIP_SinkingFractionBasis
```

Reuse existing common names for:

```text
currency
coupon
frequency
maturity
valuation date
clean price
spread shift
volatility
runner command
```

Compatibility defaults:

- missing `FIP_InstrumentType` → current vanilla behavior;
- missing `FIP_Operation` → `calibrate_and_risk`;
- `FIP_OASBp` read only for `price_at_oas`;
- no new named range should be required for the existing vanilla workbook to keep working.

### Variable-length schedule tables

Use named Excel Tables (`ListObject`) rather than fixed cell blocks:

```text
FIP_CallSchedule
    Date | PricePer100

FIP_PutSchedule
    Date | PricePer100

FIP_SinkingSchedule
    Date | FractionOutstanding | PricePer100
```

The exact names may follow the live repo's naming style.

Rules:

1. Wholly blank data rows are ignored.
2. A partially filled row produces a clear Excel-side error naming table and row.
3. Every date becomes an ISO `YYYY-MM-DD` string before JSON serialization.
4. Numeric Excel dates must never appear in the JSON.
5. Row order is preserved.
6. VBA does not sort, deduplicate, infer continuation, or default values.
7. Empty optional tables are omitted rather than sent as guessed schedules.
8. Missing required schedules are handled by the existing Python validation response.
9. Exercise prices stay per 100.
10. Sinking fractions stay fractions of the amount outstanding.

---

## 17. B4 — Exact instrument mappings

Use the current live v1.1 contract.

### Callable

```text
instrument_type = callable
required        coupon_pct + call_schedule
optional        put_schedule + volatility
```

### Puttable

```text
instrument_type = puttable
required        coupon_pct + put_schedule
optional        call_schedule + volatility
```

### Sinking

```text
instrument_type = sinking
required        coupon_pct + sinking_schedule + sinking_fraction_basis
optional        call_schedule + put_schedule + volatility
```

Do not silently set a missing call/put price to par.

Do not silently set a missing sinking fraction to zero.

Do not infer a schedule from the custodian's first-call-date column.

`original` sinking basis must receive the existing controlled refusal; do not transform it to `outstanding`.

Combined rights use the existing optional schedules. Do not invent a new combined type.

---

## 18. B5 — Operations and volatility proof

For at least one callable example, prove both existing operations from Excel:

### `calibrate_and_risk`

```text
fixed clean market price
+ selected volatility
→ implied OAS and risk
```

### `price_at_oas`

```text
fixed OAS
+ selected volatility
→ model price and risk
```

This is the Excel-level version of Mario's two volatility questions.

Do not add a scenario-array operation. A 10% / 15% / 20% table is three ordinary single-bond calls.

For puttable and sinking:

- use controlled synthetic fixtures;
- state clearly that they validate model/interface behavior, not a live URS cohort;
- do not manufacture a portfolio claim.

---

## 19. B6 — Response handling

Keep the existing common output cells and semantics:

```text
model clean price
model dirty price
accrued interest
implied OAS
effective duration
DV01
convexity
tighter price
wider price
curve ID
warnings
errors
```

For the QA harness, optional additional outputs may include:

```text
engine
instrument_type used
volatility used
```

Do not design a final type-specific result panel yet. The full request and response JSON already provide the detailed audit trail.

Every failed request must:

- show the structured error;
- clear stale numerical results;
- handle JSON `null` as VBA `Null` safely;
- retain request/response JSON in the QA surface;
- never show a raw traceback or local path.

---

## 20. B7 — Real-Excel test matrix

Extend the existing real-Excel PowerShell/VBA harness. Preserve all original checks unchanged.

### 20.1 Callable

Use one live call-active URS case for private regression if permitted, plus a sanitized committed fixture.

Verify:

1. instrument type is serialized;
2. a multi-row call schedule is an ordered JSON array;
3. schedule dates are ISO strings;
4. volatility reaches the engine and is reported as used;
5. common outputs equal the endpoint/direct-wrapper results;
6. both operations work;
7. 10% / 15% / 20% runs preserve the documented price/OAS direction for the call-active fixture;
8. VBA never defaults the schedule to par.

### 20.2 Puttable

Use a synthetic put-active fixture.

Verify:

1. put schedule serialization;
2. exact response/direct-call equality;
3. higher volatility increases price at fixed OAS in the selected active fixture;
4. a same-date contradictory `put_price > call_price` produces the existing controlled refusal;
5. stale cells clear on error;
6. documentation labels the case synthetic.

### 20.3 Sinking

Use synthetic fixtures.

Verify:

1. ISO date, fraction outstanding, and price per 100 serialize exactly;
2. basis `outstanding` is transmitted;
3. basis `original` receives the controlled refusal;
4. a partial table row fails clearly before Python;
5. endpoint and direct-wrapper values agree exactly;
6. no documentation conflates optional sinking redemption with deterministic amortisation or pass-through principal schedules.

### 20.4 Cross-cutting tests

Verify:

- optional empty tables omitted;
- combined call+put schedules transmitted together;
- combined call+sinking represented through the existing sinking type plus call schedule;
- table row order preserved;
- numeric date values never appear in generated JSON;
- missing required schedules return structured Python errors rather than VBA crashes;
- runner waiting still works;
- `Null` handling still works;
- all original vanilla tests and the original demo result remain unchanged.

### Equality standard

For every successful fixture:

```text
Excel-displayed value
=
parsed response JSON value
=
endpoint result
=
direct asset-wrapper result
```

Use exact equality wherever the current harness supports it. Do not introduce bridge-specific rounding.

---

## 21. B8 — Fixtures and documentation

Generate all numerical responses by running the live endpoint.

Suggested fixtures, adapted to the current examples directory:

```text
callable_calibrate_request_v1_1.json
callable_calibrate_response_v1_1.json
callable_price_at_oas_request_v1_1.json
callable_price_at_oas_response_v1_1.json
puttable_request_v1_1.json
puttable_response_v1_1.json
sinking_request_v1_1.json
sinking_response_v1_1.json
call_put_conflict_error_v1_1.json
sinking_original_basis_error_v1_1.json
```

Use sanitized IDs and synthetic terms in reusable examples. Real URS details may remain in private regression fixtures or the Mario-only report where appropriate.

Update the existing interface reference and Excel README rather than creating a parallel interface document.

The top-level status should distinguish four layers:

| Layer | Vanilla | Callable | Puttable | Sinking |
|---|---:|---:|---:|---:|
| Python wrapper | verified | verified | verified | verified |
| JSON endpoint | verified | verified | verified | verified |
| Real Excel bridge | verified | verified | verified | verified |
| Final visible customer layout | complete | pending Mario | pending Mario | pending Mario |
| Live URS cohort | yes | yes | none | none |

If Workstream B completes before the package is built, add a **separate** short report section titled along the lines of:

```text
Additional integration follow-through — embedded-option bonds through Excel
```

Do not insert it into the six-cell results table or describe it as part of the FRN/column-F reconstruction.

---

## 22. Workstream B acceptance criteria

Workstream B is complete when:

1. All original real-Excel tests remain green and unchanged.
2. New real-Excel tests pass for callable, puttable, and sinking in fixture and local-Python modes.
3. The current vanilla demo request and output remain unchanged.
4. The bridge emits the live schema-v1.1 field names.
5. Schedule dates are ISO strings and row order is preserved.
6. No exercise price, fraction, basis, or schedule is guessed.
7. Both existing operations are proven through Excel for the callable fixture.
8. Puttable and sinking fixtures are labelled synthetic.
9. Errors clear stale values and display controlled messages.
10. No new endpoint, parser, engine, schema branch, or final UI is created.
11. Production drivers and Workstream A evidence remain unchanged.
12. The report separates this integration work from the column-F deliverable.

---

## 23. Suggested commit sequence

Adapt names to the live repo, but preserve the separation between the two workstreams.

### Workstream A

```text
1. docs: align this directive and record Mario's column-F screenshot directive
2. test: add/strengthen full-disposition and five-callable accounting guards
3. test/docs: build the column-F delivery matrix and reconstruction evidence
4. docs: strengthen FRN/hybrid/schedule evidence and GBP-unit audit
5. docs: update weekly report, walkthrough, persistent records, and package QA
6. checkpoint: commit a fully sendable Workstream-A deliverable
```

### Workstream B

```text
7. refactor: make the existing VBA request builder instrument-aware without changing vanilla
8. feat: add call/put/sinking named-table serialization and operation inputs
9. test: add real-Excel fixture and live-Python checks for the three tree types
10. docs: update the interface reference, Excel README, fixtures, and separate report section
11. chore: rebuild final package, update records, push origin and 47
```

Run the full pytest suite and relevant production drivers after every code-bearing commit. Run the complete Excel suite after every VBA or workbook-builder commit.

---

## 24. Stop conditions

Stop the affected gate and diagnose before proceeding if:

- any current production route, price, OAS, duration, DV01, convexity, or flag changes;
- any original vanilla endpoint or Excel fixture changes;
- a report count cannot be reconciled to a named population;
- a data blocker is supported only by an internal exception rather than the raw source;
- an eligible bond disappears from all dispositions;
- schedule serialization requires guessing a term;
- the bridge work requires a second endpoint or duplicated pricing logic;
- the work starts designing the final multi-product workbook UI;
- Workstream B expands its Excel scope to floating, hybrid, stepped, MBS, ILB, EIR, CreditMetrics, or batch mode; Workstream A may audit floating/hybrid/stepped only as specified above;
- a synthetic puttable/sinking example is being presented as live portfolio evidence.

If a new real defect is discovered:

1. isolate it;
2. verify it against source data;
3. preserve a failing regression case;
4. report it to the user before changing production behavior;
5. do not bury it inside “delivery hardening.”

---

## 25. Final self-review record

This instruction was re-reviewed specifically to correct the prior conflation.

### Correction 1 — delivery quality and Excel expansion are now separate

The primary workstream is explicitly the quality of this week's FRN/hybrid/schedule and Mario column-F deliverable. The Excel tree-type connection is a second, additive workstream with its own scope, tests, claims, and acceptance criteria.

### Correction 2 — Workstream A can ship without Workstream B

A mandatory checkpoint now requires a fully sendable Round 2b package before the Excel extension begins. Interface work cannot become a reason to leave the main client deliverable half-finished.

### Correction 3 — the report narrative is protected

The six-cell table remains about `F12:F16` and `F20`. Callable/puttable/sinking Excel support, if completed, appears only in a separate integration section and never inside the column-F counts.

### Correction 4 — no new type is opened

Workstream A documents and hardens already completed floating/hybrid/stepped code. Workstream B exposes already-built callable/puttable/sinking contracts through Excel. No new engine, route, or asset type is created.

### Correction 5 — the highest-value recent failures are addressed

The instruction includes:

- source-level proof before declaring a data gap;
- the GBP/DKK explicit unit registry;
- a full-disposition invariant against silent disappearance;
- complete five-callable accounting;
- same-environment production parity;
- exact wrapper/endpoint equality;
- fresh-run report numbers.

### Correction 6 — FRN nuances are not flattened

The quality pass explicitly covers both duration regimes, the deep-discount negative-duration case, and the distinction between clean credit spread and discount-margin-like calibration when the quoted margin is unknown.

### Correction 7 — Mario's UI decision remains open

The Excel work uses stable names, Tables, and a QA harness. It does not choose adaptive-sheet versus separate-sheet layout, and it does not claim that the polished customer demo already supports every product.

### Correction 8 — the source screenshot is handled honestly

The column-F values are transcribed from the user-supplied screenshot; the source-safe holdings workbook remains untouched, and blank cells are not interpreted.

### Final judgment

This is the correct next instruction for the current week because it first makes the completed FRN/column-F reconstruction more defensible, easier to review, and safer to hand over, and only then completes the separate Excel bridge promise for the already-built tree products. It improves delivery quality without opening another modelling workstream.

---

# 26. Gate-0 revision — 2026-08-31, recorded before execution

Run per §3. The instruction's own rule applies: the live repository wins. Six adjustments,
one of which is a genuine defect that §24 requires be reported to the user before any
production behaviour changes.

## 26.1 Gate-0 results — the expected baseline is confirmed

| check | expected by §1.4 | live |
|---|---|---|
| HEAD | `a5f7c81` | **`694e849`** — two doc-only commits since (handoff refresh, handoff1 restructure) |
| tree / remotes | clean, synced | clean; origin and 47 both at `694e849` |
| pytest local | 287 | **287** |
| pytest on 47 | 287 | **287** |
| Excel bridge, fixture runner | 23 | **23/23** |
| Excel bridge, live-Python runner | 23 | **23/23** |
| endpoint schema | 1.1 | **1.1**, 7 types, field names read from the live contract |
| visible Excel demo | vanilla only | **vanilla only** — `PriceVanillaBond` / `BuildVanillaRequest` / `PopulateVanillaOutputs` |
| corporate output @3-31 | 565 = 555 + 10 | **565 = 555 + 10** |
| production `skipped` | 0 | **0** (calibration driver) |
| five driver CSVs | frozen | reproduce **byte-identically** to the committed local baseline |

**§5's six-cell table re-verified against the live 565-row output and retained unchanged:**
`30 pivot rows → 29 held → 23 priced + 6 not`, per cell 5/5/4 · 2/1/1 · 1/1/1 · 12/12/11 ·
9/9/5 · 1/1/1. The three populations (676 / 565 / 555) are confirmed.

**§3.9 answers:** a full-disposition test **does not exist**. Five-callable accounting **does
not exist** in any document, test or output.

**§3.10 answer:** the VBA request builder is **vanilla-specific**. The live named-range
convention is `FIP_*`, so §16's suggested `FIP_InstrumentType` / `FIP_Operation` / `FIP_OASBp`
/ `FIP_SinkingFractionBasis` fit it without adaptation.

## 26.2 Adjustment 1 — §1.1 provenance is wrong for this repository

§1.1 says the source-safe workbook predates the annotations and directs that a user-supplied
screenshot be treated as the evidence. That is true of the **Project copy** web-Claude can see.
It is **not** true of the live repo: Mario's column F is present in
`data/URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx`, sheet `Pivot of Corp Bonds`
(`xl/worksheets/sheet6.xml`), and was committed in `a5f7c81` for exactly this reason. A
`git show` of an earlier revision proves the column did not exist before 2026-08-27.

So `docs/client_directive_pivot_column_f_2026-08-27.md` will cite the **tracked workbook** —
stronger evidence than a screenshot — and record the screenshot as the user's corroboration.
§1.1's prohibition stands and was already honoured: we committed what Mario left, we did not
author the annotations.

## 26.3 Adjustment 2 — §10.2's fifth callable is a DEFECT, not bookkeeping

§10.2 was right to say "do not assume the fifth is the historical short-gap callable. Verify
it." Verified, and the fifth name is a security that is **priced by nothing and named nowhere**.

```text
callable bucket @2009-03-31 and @2009-06-10 = 5

  TNTD04441873  gap  7243 d   lattice-priced
  TNTG701850W   gap  1809 d   lattice-priced
  TNTD04115619  gap  1096 d   lattice-priced
  TNTD04923866  gap 20819 d   SKIPPED, with a printed reason (no call_schedules.csv row)
  TNTD04920858  gap    90 d   DROPPED SILENTLY  <-- the defect
```

`TNTD04920858` / `US828807BX41` — a US real-estate issuer, "Callable Notes", fixed 5.00%,
semiannual, maturing 2012-03-01, callable at par from 2011-12-02. **Held: par 850,000,
market value 723,542, custodian price 85.12, YTM 11.11%, rated A− / A3**, present at both
valuation dates.

**Root cause: two thresholds in two files, with a hole between them.**

```text
dataio/universe.py       MAKE_WHOLE_MAX_GAP_DAYS = 7    gap <= 7   -> route vanilla
                                                        gap >  7   -> exclude as "callable"
scripts/callable_risk.py GAP_DAYS = 366                 gap > 366  -> price on the lattice

        gap in (7, 366]  ->  excluded from the vanilla output AND never seen by the lattice
```

It is therefore absent from `implied_oas_*.csv`, absent from `callable_risk.csv`, and absent
from every document — with **no message anywhere**, unlike `TNTD04923866`, which at least
prints a `skip` line naming its blocker.

This is a second instance of the failure class that produced the GBP omission: neither priced
nor flagged, and invisible to every headline count.

**Per §24, the routing decision is escalated to the user and is NOT taken inside this
hardening pass.** §10.2's own rule — "do not change a route merely to make the table neat" —
is respected. This revision commits the finding and a failing regression case; the fix waits
for a decision.

## 26.4 Adjustment 3 — §10.1's invariant as written would NOT catch this

The reconciliation §10.1 proposes balances perfectly and still hides the bug:

```text
732 funnel population = 565 corporate output + 3 lattice output + 164 excluded-with-a-reason
```

`TNTD04920858` sits in that 164 carrying `primary_reason = "callable"`, so "every bond has a
named disposition" is **satisfied**. The problem is that `callable` is not a disposition at
all — it is a **routing instruction** meaning "this goes to the lattice driver", and two of
the five never arrive.

The invariant will therefore be strengthened to:

```text
1. exhaustive + mutually exclusive  (as §10.1 asks), AND
2. every exclusion reason that denotes ROUTING is honoured by its destination:
   every bond excluded as "callable" appears in the lattice output
   OR carries an explicit, printed, named blocker
```

Under (2), `TNTD04923866` passes (its blocker is printed) and `TNTD04920858` fails. The
remaining 164 are checked against reasons that are genuine terminal dispositions:
terms-unavailable 135 · excluded-structured 15 · no-rating 9 · defaulted 2 · callable 2 ·
matured 1.

## 26.5 Adjustment 4 — a smaller inconsistency, recorded not fixed

Four bonds carry `primary_reason = defaulted`. Two (`TNTD03037967`, `TNTD04769276`) appear in
the corporate output on route `recovery` at the custodian mark; two (`TNTD03044683`,
`TNTD03067251`) are excluded and appear in no output. Both are named in the exclusion log, so
neither is silent — but the treatment is inconsistent. It will be reported as a line in the
A4 disposition table, not changed.

## 26.6 Adjustment 5 — §1.4 and §12.2 baselines re-pointed

Baseline HEAD is `694e849`; the frozen driver hashes recorded at this gate are the comparison
reference for §12 acceptance criterion 2. No production output has moved.

## 26.7 What is unchanged

Everything else in this instruction is adopted as written, including: the A/B split and the
mandatory checkpoint; the §2 boundaries; the §14 decision to reuse the existing bridge, parser,
runner and endpoint; §15's refusal to pre-empt Mario's layout choice; §16's named-Table
approach; §20's equality standard; and §24's stop conditions.
