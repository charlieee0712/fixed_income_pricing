# CC Execution Directive — Post–Round 2b Decision Closure, Hardening, and Release Candidate

**Date:** 2026-08-31  
**Project:** RYSE Fixed-Income Pricing  
**Basis reviewed:** `01_weekly_report_2026-08-30.md`, `technical_note_for_review_2026-08-31.md`, and `code_walkthrough_2026-08-31.md`  
**Purpose:** close the review questions exposed by Round 2b, improve the quality and truthfulness of this week’s delivery, and produce a clean Mario/Google-team release candidate.  
**Scope rule:** **do not start another asset type.** No MBS, pass-through, ILB, CreditMetrics, batch API, HTTP/cloud service, or final seven-product worksheet design in this round.

---

## 0. Executive direction

Round 2b is substantively successful. The next work should not expand product scope. It should convert the week’s findings into durable controls and ensure the client package says exactly what the live code does.

Run this as one focused post-round hardening pass with four outcomes:

1. **Correct the outward-facing documents before they are sent.** The weekly report is strong, but it currently conflates the seven-type Python endpoint with the narrower Excel bridge, and the walkthrough contains stale counts and stale interface statements.
2. **Close the silent-failure seams already identified.** In particular: domain exceptions must not be swallowed as generic `ValueError`; ACT/364 must have one authoritative conversion; and the disposition invariant must be covered both at runtime and in pytest.
3. **Correct the production interpretation of the current FRN coupon.** The coupon already running at valuation is fixed. When its observed fixing is unavailable, a base-curve proxy may be used transparently, but that proxy must remain frozen during risk bumps.
4. **Improve confidence labelling without inventing data.** Provisional call schedules may continue to produce provisional results, but the provenance must be visible; synthetic put/sink validation must remain clearly distinguished from live-portfolio validation.

The live repository remains authoritative. Begin with an alignment gate and edit this directive in place if filenames or current facts differ.

---

## 1. Decisions on the technical note’s §4 questions

These decisions govern execution; do not leave them to individual callers.

| Technical-note item | Decision | Required action |
|---|---|---|
| **4.1 Short-gap callable** | **Keep `TNTD04920858` refused and named in production for now. Do not route it to vanilla and do not insert a raw exercise node as a quick patch.** | Produce a separate design memo and, only if cheap, a non-production prototype. A production exercise-date grid must first settle irregular-step calibration, off-coupon accrued/call-price treatment, and event ordering. |
| **4.2 `ExerciseTermsError(ValueError)`** | **Move exercise/contract refusals onto a project-domain exception base derived from `Exception`, not `ValueError`.** | Audit all `except ValueError` sites first; narrow solver catches to actual calibration/root-finding errors; preserve endpoint/CLI structured-error behavior. |
| **4.3 Disposition invariant only in drivers** | **Keep the runtime check and add CI coverage. Both are needed.** | Unit-test the pure set reconciliation directly, plus one temporary-output integration test that runs against fresh data rather than a git-ignored stale CSV. |
| **4.4 Synthetic put/sink evidence** | **Sufficient to say the implementation and model invariants are working; not sufficient to claim live-portfolio validation.** | Keep the existing exact anchors, add one independently hand-computed small-tree fixture per right if not already present, and retain explicit “synthetic; no URS holding” labels. |
| **4.5 FRN current coupon** | **The running coupon is fixed at valuation. Supplied or estimated once, it must remain frozen under curve bumps.** | If supplied, use it. If absent, derive one transparent base-curve proxy once, freeze it in the bumped valuations, and mark the risk result provisional. Do not reproject the current period separately in the up/down curves. |
| **4.6 365.25 default** | **No silent alternative day count may remain on the production exercise-date path. ACT/364 is the project law, not a caller preference.** | Prefer removing the argument and delegating to the canonical ACT/364 function. If compatibility requires retaining it, default to the canonical constant and reject any non-364 value explicitly. |
| **4.7 Provisional call terms** | **Continue pricing on provisional terms, but never present those results as confirmed terms.** | Add machine-readable provenance/status to outputs and reports. Keep Bloomberg confirmation in the existing deferred queue; do not open a new request in this round. |

### External cross-checks used for these decisions

- QuantLib’s discretized callable-bond implementation includes **callability times, coupon times, and redemption time** in the lattice’s mandatory times. Its source also contains explicit logic for call dates near coupon dates. This supports treating an exercise-date node as a genuine model design, not a one-line routing patch.
- QuantLib’s Ibor coupon logic treats a coupon as fixed once its fixing date has passed and forecasts only when it has not fixed. That supports freezing the current coupon under a valuation-date curve shock.
- Python’s official guidance recommends module-specific user exceptions under `Exception`; a project-domain hierarchy is preferable to relying on a broad builtin category that unrelated solver code already catches.

These are external sanity checks, not replacements for the project’s locked conventions or live-repo evidence.

---

## 2. Non-negotiable project locks

Do not reopen or drift any of the following:

- valuation baseline `2009-03-31`, with `2009-06-10` as control;
- OAS as a per-bond calibration output in `calibrate_and_risk`;
- clean custodian `BT`, dirty model PV, one shared accrued-interest function;
- duration/DV01/convexity denominator based on dirty price;
- ACT/364 and the 182-day semiannual schedule convention;
- per-100 prices and DV01; `face_value` is echoed, not applied;
- own-currency curve routing with no silent USD fallback;
- single-curve FRN/hybrid methodology for the 2009 framework;
- one shared tree for call/put/sink;
- outstanding-balance sinking basis only;
- old imports remain compatibility shims;
- no new counterparty request, and no edit to the authoritative URS holdings workbook.

---

## 3. Gate 0 — align to the live repository and freeze the release baseline

Before editing code or documents:

1. Record live HEAD, branch, local/47 sync state, and working-tree status.
2. Run the complete pytest suite locally and on 47; record the **actual** count rather than carrying `302` from a document.
3. Run all five production drivers and freeze their outputs **within each environment**.
4. Run the Excel bridge in both modes and record the actual fixture/live counts.
5. Run:
   - `scripts/column_f_audit.py`;
   - the corporate disposition reconciliation;
   - the seven-type endpoint inventory from live code;
   - a direct inventory of what the VBA builder can actually emit by instrument type.
6. Confirm whether the visible demonstration workbook is still vanilla-only and whether the bridge/test harness supports only vanilla + tree types or all seven types.
7. Inventory every `except ValueError`, every call to `to_lattice_schedule`, every import of floating private helpers, and every duplicated routing/maturity-gap threshold.
8. Re-derive the four defaulted securities and their current terminal dispositions from live objects, not from a document.

Add a revision section to this directive with the verified facts before implementation begins.

### Gate-0 stop conditions

Stop and report before continuing only if:

- the live endpoint/Excel scope differs materially from both the weekly report and technical note;
- any existing priced output cannot be reproduced within its own environment;
- `TNTD04920858` is no longer the only non-representable short-gap corporate callable;
- a documented external caller is proven to require `ExerciseTermsError` to be a `ValueError`.

---

## 4. Workstream A — make the client deliverables factually exact

This is the first deliverable, but finalize it **after** code hardening and fresh reruns so the numbers cannot become stale again.

### 4.1 Correct the weekly report

Keep its current client-facing structure and tone. Make these corrections:

1. **Separate endpoint scope from Excel scope.** The Python/JSON endpoint supports seven instrument types. State exactly which types the VBA bridge and engineering test workbook can currently construct from cells. Do not say “the spreadsheet can ask for any of seven” unless the live VBA builder truly emits all seven request shapes.
2. Keep §4.1 explicitly separate from Mario’s six column-F cells.
3. Replace “the tests prove the model” for puttable/sinking with:
   - implementation parity and economic invariants are validated;
   - no live URS holding exists for portfolio validation.
4. Revise the FRN-duration explanation after Workstream C. Do not retain “both are correct” as an undifferentiated production statement.
5. Identify provisional call-term results as provisional wherever a live callable number is discussed.
6. Recompute every count, spread, duration, and test number from fresh artifacts. Do not copy from the technical note or prior report.
7. Keep the UK-curve correction and withdrawal request prominent; it is both honest and important.
8. Keep only one client question: the final daily-use Excel layout. Do not send the technical-note decisions to Mario as a new questionnaire.

### 4.2 Rebuild the walkthrough from the live facts

The attached walkthrough is not release-ready. At minimum it currently contains stale references to `223`, `300`, `23/23`, and `analyze_vanilla_payload`, and it blurs the visible demo with the engineering bridge.

Refresh all of the following:

- opening date/session language;
- test count and runtime;
- Excel fixture/live check counts;
- `analyze_payload` as the general entry point, with the vanilla name described only as a compatibility alias;
- exact Excel-builder coverage;
- short-gap callable refusal and the set-level disposition invariant;
- cross-platform wording: single-bond JSON may be byte-identical, but full driver CSV parity is environment-local because of convexity last-bit differences;
- “new bond type = new asset file” should be qualified: this is true when existing core mathematics applies; genuinely new cash-flow dynamics may require a new core engine;
- “what is not built yet” must distinguish the visible daily-use demo layout from the already working engineering bridge.

Keep the walkthrough to about 15 minutes. Remove duplicate explanation rather than extending it.

### 4.3 Create one generated release-facts artifact

Add a small generated internal artifact, using the live repo’s preferred location, containing:

```text
HEAD / date
pytest count and runtime
Excel fixture-mode and live-mode counts
five driver hashes per environment
corporate output/disposition counts
column-F 30 / 29 / 23 / 6 audit
endpoint instrument types
VBA-builder instrument types
five corporate callable dispositions by Asset ID
```

The report and walkthrough must be checked against this artifact immediately before PDF/zip generation. It is internal evidence and should not be sent as a client report unless useful.

---

## 5. Workstream B — close the exception, day-count, and disposition-control seams

### 5.1 Domain exception hierarchy

Introduce or consolidate a small domain hierarchy, adapting names to the live repo:

```text
PricingDomainError(Exception)
├── ContractTermsError
│   └── ExerciseTermsError
├── CalibrationError
└── CurveResolutionError   # only if an equivalent hierarchy does not already exist
```

Requirements:

- `ExerciseTermsError` must no longer inherit from `ValueError` unless Gate 0 proves a documented consumer contract requires it.
- Root solvers must not catch broad `ValueError` around the pricing callback.
- Catch only errors the solver can actually interpret as calibration failure.
- Endpoint and CLI must continue returning structured values, not exceptions.
- The JSON path and actionable message carried by exercise errors must survive to Excel.
- Add regressions for sinking-basis refusal, call/put conflict, and non-representable schedule so none can become `CALIBRATION_FAILED` again.

### 5.2 Canonical ACT/364 schedule conversion

Eliminate the latent 365.25 path:

- make `core.pricing.tree.schedule_times` or the canonical date utility the one implementation;
- make `dataio.call_schedules.to_lattice_schedule` delegate to it;
- preferred: remove `days_per_year` from the production-facing signature;
- compatibility fallback: retain it as keyword-only, default to canonical `YEAR_DAYS`, and reject a supplied value that is not 364;
- add a test proving every production, endpoint, and Excel route uses the same conversion;
- do not alter the old validated coupon calendar itself.

### 5.3 Runtime + pytest disposition guarantees

Keep the runtime driver reconciliation. Add CI coverage without reading stale git-ignored outputs:

1. Unit-test `dataio.dispositions.reconcile` directly with constructed ID sets:
   - complete and disjoint;
   - missing candidate;
   - duplicate disposition;
   - routing reason not discharged;
   - terminal reason accepted.
2. Add one integration test that runs the relevant driver/audit into `tmp_path` or another fresh temporary destination, then validates the generated sets.
3. Test the five current corporate callable dispositions by ID, but also retain a general set-equality invariant so future bucket-size changes do not require rewriting the logic.

### 5.4 Remove the private-helper coupling

Refactor the floating/hybrid seam without changing arithmetic:

- promote the helpers that hybrid legitimately composes from to stable public names in the migrated `pricer` layer;
- update hybrid to import those public names;
- keep the old private names as aliases in the compatibility shim for now;
- assert alias identity and production output parity;
- do not relocate unrelated floating code.

---

## 6. Workstream C — correct the FRN current-coupon risk treatment

This is the only intentional methodology/output change in the hardening pass. Isolate it in its own commit and evidence table.

### 6.1 Production rule

For the coupon period already running at the valuation date:

```text
if current_coupon_pct is supplied:
    use it for base, up-bump, and down-bump valuations
else:
    project one proxy from the BASE curve at the true last reset
    use that same frozen proxy for base, up-bump, and down-bump valuations
```

Future coupons after the next reset continue to reproject from each bumped curve.

### 6.2 Output transparency

Expose, using the existing result/warning style:

```text
current_coupon_pct_used
current_coupon_source = supplied | projected_proxy
current_coupon_status = supplied_input | unavailable_projected_proxy
risk_current_coupon_treatment = frozen
risk_quality = supplied_input | provisional_current_coupon
```

Names may adapt to the live schema, but the information must be present in Python results and JSON responses.

### 6.3 Evidence and acceptance

- Base clean price and calibrated OAS must remain identical to the pre-change result when the same base proxy is used.
- Supplied-current-coupon cases must remain unchanged.
- Near-par synthetic FRN duration should align with time to next reset under the frozen-current-coupon treatment.
- Do **not** assert that every FRN duration is positive: deep-discount spread-annuity effects may still produce negative duration.
- Produce a per-live-FRN before/after table with:
  - Asset ID;
  - current coupon source;
  - old duration;
  - new duration;
  - delta;
  - next reset time;
  - clean price and OAS checksum.
- Update the missing-data registry to state that observed current coupon/reset fixing is needed for fully authoritative FRN risk. Add it to an existing future Bloomberg landing path; do not send a new request now.

If the base price or OAS changes unexpectedly, stop and diagnose rather than accepting a broader drift.

---

## 7. Workstream D — confidence/provenance and disposition consistency

### 7.1 Provisional call schedules

Keep the three currently priced corporate callable bonds priced, subject to the existing model, but make their status explicit.

Add or standardize fields such as:

```text
exercise_terms_status = confirmed | provisional
exercise_terms_source = bloomberg | filing | custodian_AB_seed | other
exercise_price_source
exercise_terms_as_of
```

Requirements:

- `custodian_AB_seed + par@100` must be visibly provisional in output, endpoint response, and internal delivery matrix.
- Do not silently promote a seeded schedule to confirmed.
- Keep straight-vs-callable comparison and option cost available for review.
- Add the three corporate call schedules to the existing **confirmation-only/deferred** queue. Do not message Mario or Liping again in this round.
- Give `TNTD04115619` a named internal review note because its 1993.6 bp result makes term provenance especially important; do not invent a new numerical threshold or automatically reject it.

### 7.2 Defaulted-bond consistency

Derive the four `primary_reason=defaulted` securities from the live universe and apply one rule:

> Every held, matched, in-scope defaulted security with a usable custodian mark must emit a named `recovery`/BT-mark disposition and no OAS. If it is intentionally outside the output, its terminal reason must state the actual reason rather than merely `defaulted`.

Do not add rows only to make a table look tidy. Document the facts for each of the four IDs, then apply the rule. Any resulting output/count change is intentional and must be isolated from migration parity.

### 7.3 Decision-ownership sweep

Run a focused audit for the pattern “two thresholds, one decision”:

- route/maturity-gap thresholds;
- frequency acceptance;
- rating or default cutoffs;
- date-window filters;
- curve/currency support checks.

For each duplicate, record:

```text
decision
current owners/call sites
authoritative owner
whether the downstream site should consume or re-decide
```

Fix only proven duplicated ownership that can silently omit or reroute a security. Do not turn this into a broad cleanup or architecture rewrite.

---

## 8. Workstream E — short-gap callable design note, not a production patch

Create a concise internal decision memo for `TNTD04920858` covering:

1. Current refusal and why the zero option value was invalid.
2. The two rejected shortcuts:
   - route all sub-year calls to vanilla;
   - insert a call date and cap value at 100 without handling accrued/event ordering.
3. A proper exercise-date-aware grid design:
   - grid includes coupon, exercise, and redemption times;
   - variable time steps;
   - exact curve calibration at all grid times;
   - coupons only on coupon dates;
   - call/put/sink only on their own dates;
   - clean-vs-dirty exercise price and accrued at an off-coupon call date explicitly defined;
   - root and redemption behavior explicit;
   - no schedule entry may disappear during mapping.
4. Required tests before production adoption:
   - straight-tree equality on the enriched grid;
   - zero-volatility limit;
   - manual small-tree anchor;
   - call/put bounds;
   - coupon-date call parity with the current engine;
   - off-coupon call with accrued;
   - TNT repricing at several volatilities;
   - all eight existing live call-term bonds unchanged unless their grid genuinely changes.

A prototype may be committed only behind a non-production helper/test path. Do not route production to it in this pass. Record it as the preferred future solution over a blanket short-gap threshold.

---

## 9. Shim and migration policy

Do not retire any shim now.

Adopt these exit criteria:

1. every in-repo production caller imports the new `pricer.*` path;
2. the Google team has received and exercised the new public surface;
3. at least one release cycle has passed with deprecation documented;
4. removal has its own migration plan and golden-output freeze.

Do not migrate the remaining five layers for architectural neatness. The next engine migration remains data/scope driven:

- MBS when the requested pool data arrives;
- ILB or other layers only when Mario selects that work;
- `curves/`, `credit/`, and `dataio/` only when an active task benefits from the move.

Document this policy so “temporary shims” do not become unexamined permanence, but keep them during the current handoff period.

---

## 10. Validation gates

### Gate 1 — no-intentional-change hardening

After Workstream B and helper/provenance changes:

- complete pytest suite green locally and on 47;
- all five production CSVs byte-identical to their **same-environment** freeze;
- endpoint vs direct wrapper remains `==`;
- Excel fixture/live modes pass;
- structured error messages show the correct schedule field and no path/traceback;
- five corporate callable dispositions are complete and named.

### Gate 2 — intentional FRN risk change

After Workstream C:

- document exact affected columns and securities;
- base price/OAS checksums unchanged;
- only justified FRN risk/metadata fields change;
- no hybrid, fixed, tree, agency, guaranteed, ILB, or other output drifts;
- report all local/47 differences using same-environment baselines.

### Gate 3 — defaulted disposition decision

- all four defaulted securities have one explicit, evidence-backed terminal treatment;
- set reconciliation passes;
- any headline-count change is regenerated everywhere, not hand-edited selectively.

### Gate 4 — document truth pass

Before PDF/zip:

- weekly report, walkthrough, interface reference, README, WORKLOG, PROJECT_STATUS, CLAUDE, coverage, and missing-data registry agree on current counts and scope;
- no document says the Excel bridge supports seven request builders unless live tests prove it;
- no document calls a projected current coupon an observed fixing;
- no document calls provisional call terms confirmed;
- no document says synthetic tests validate the URS portfolio;
- every number is re-derived from the release-facts artifact or a fresh run.

### Gate 5 — packaging

- generate the PDFs with the existing script;
- rebuild the Drive staging folder with the established safe process;
- no handoff/internal-planning files in the client package;
- no stale report/walkthrough copies;
- no client workbook modification;
- zip opens and contains the intended source, tests, scripts, integration files, and current documents;
- origin and 47 synced; both trees clean.

---

## 11. Suggested commit sequence

Adapt names to the live repo, but keep intentional numerical changes separate.

```text
1. docs: record post-Round-2b review decisions and verified live baseline
2. test: add CI disposition reconciliation and stale-fact regressions
3. fix: introduce domain terms exceptions and narrow calibration catches
4. fix: canonicalise exercise-date conversion on ACT/364
5. refactor: replace floating private-helper imports with public aliases, no numeric change
6. feat: freeze supplied/base-proxy current FRN coupon during risk bumps
7. feat: add current-coupon and exercise-terms provenance metadata
8. fix: resolve defaulted-security terminal dispositions from evidence
9. docs: add short-gap callable design note and shim exit policy
10. docs: correct weekly report, walkthrough, interface docs, coverage and registry from fresh runs
11. chore: regenerate PDFs, release facts, staging folder and zip; sync origin + 47
```

Run the full suite after every code-bearing commit. Re-run the five drivers after each commit that can affect routing, pricing, risk, serialization, or output disposition.

---

## 12. Acceptance criteria

This instruction is complete only when all of the following are true:

- no new asset type or model family has been opened;
- the weekly report and walkthrough accurately distinguish seven-type endpoint support from actual Excel-builder support;
- no stale `223`, `300`, or `23/23` release claim remains unless a historical sentence labels it explicitly;
- exercise-term errors cannot be swallowed by a broad `ValueError` handler;
- every production exercise date uses the canonical ACT/364 conversion;
- disposition completeness is enforced both during production runs and by pytest without stale output dependencies;
- the FRN current-period coupon is frozen under risk bumps, supplied or transparently proxied;
- pre-change FRN base price/OAS are preserved and the intentional duration changes are fully tabulated;
- provisional call schedules are machine-labelled as provisional;
- puttable and sinking claims remain synthetic/model-level, not portfolio-level;
- all four defaulted securities have a consistent evidence-backed disposition;
- `TNTD04920858` remains named and refused in production pending a properly designed exercise-date grid;
- the short-gap solution is documented with off-coupon accrued/event-order requirements;
- shims remain in place under explicit exit criteria;
- all tests and Excel checks pass, outputs reconcile within their proper environment, package contents are current, and origin/47 are clean and synced.

---

## 13. Final self-review of this directive

This directive deliberately distinguishes three different activities that must not be mixed:

1. **Migration proof** — no numerical change, demonstrated by same-environment hashes and identity tests.
2. **Correctness hardening** — exception ownership, day-count ownership, set-level completeness, provenance, and public helper names.
3. **One intentional methodology refinement** — freezing the current FRN coupon during risk bumps, with base price/OAS preserved and risk deltas explicitly reported.

It does not treat a client report as a substitute for code evidence, and it does not treat technical-note uncertainty as a reason to open new product scope. It chooses refusal over a plausible wrong callable number, but it also defines the proper future model path rather than leaving the security as an unexplained permanent gap.

No additional source file is required to begin. Mario’s final worksheet-layout decision and the outstanding Bloomberg data remain external dependencies, but neither blocks this post-Round-2b hardening and release-candidate pass.

---

# 14. Gate-0 revision — 2026-08-31, recorded before implementation

Run per §3. Six adjustments; two change what a workstream must do, one is a defect in code
this project shipped last round, and one is a scope question for the user.

## 14.1 Verified live baseline

| check | live |
|---|---|
| HEAD | `fb6761e`; local, origin and 47 all in sync; tree clean |
| pytest, local | **302** |
| pytest, on 47 | **302** |
| five production drivers | frozen; all five byte-identical to the 08-31 freeze, same environment |
| Excel bridge, fixture mode | **48/48** |
| Excel bridge, live-Python mode | **50/50** |
| endpoint instrument types | 7, read from `contracts.INSTRUMENT_TYPES` |
| visible demo workbook | **vanilla only** — `DemoBuilder.bas` has no type or schedule cells |
| corporate output @3-31 | 565 rows = 555 priced + 10 flagged |
| five callable dispositions | 3 priced · `TNTD04920858` not-representable · `TNTD04923866` schedule-unavailable |

Driver hashes (local, this freeze) are recorded in the release-facts artifact required by §4.3.

**§3 stop conditions: none triggered.** The Excel scope *does* differ from the weekly report
— which is precisely what §4.1.1 was written to correct, so it is a finding to fix rather
than an unknown to stop for.

## 14.2 Adjustment 1 — the VBA builder emits FIVE of seven, and only FOUR are tested

§4.1.1 is right, and the true numbers are worth stating exactly, because "seven" is wrong in
two different directions. Simulated from `BuildRequest`'s actual behaviour and run through
the live endpoint:

| type | can the builder construct it? | why |
|---|---|---|
| `vanilla` (and no type named) | ✅ | |
| `callable` | ✅ tested in Excel | `FIP_CallSchedule` |
| `puttable` | ✅ tested in Excel | `FIP_PutSchedule` |
| `sinking` | ✅ tested in Excel | `FIP_SinkingSchedule` + basis cell |
| `floating` | ⚠️ **nominally** | goes through, but with `UNUSED_FIELD` warnings on `bond.coupon_pct` and `bond.quoted_margin_bp` |
| `stepped` | ❌ | refused, `bond.coupon_schedule` — no cells exist for a coupon table |
| `fixed_to_floating` | ❌ | refused, `bond.quoted_margin_bp` — no cells for the margin or the switch date |

The floating caveat matters beyond a count: the sheet has **no cell for the quoted margin or
the already-fixed current coupon**, so Excel can only ever send the margin-absent case — a
discount margin rather than a credit spread — and **the current-coupon treatment Workstream C
is about cannot be exercised from Excel at all.** Workstream C's transparency fields will be
visible in the JSON but unreachable from the sheet.

**Documents must say: four types tested from Excel, five constructible, seven supported by
the engine and the contract.** Never "the spreadsheet can ask for any of seven".

## 14.3 Adjustment 2 — §7.2's defaulted rule is a THIRD "two owners, one decision"

The facts for the four, derived from live objects rather than a document:

| asset | `primary_reason` | `coupon_class` | legs | par | BT | in output |
|---|---|---|---|---|---|---|
| `TNTD03037967` | defaulted | **defaulted** | 1 | 1,625,000 | 12.00 | ✅ `recovery` |
| `TNTD04769276` | defaulted | **floating** | 1 | 2,540,000 | 0.01 | ✅ `recovery` |
| `TNTD03067251` | defaulted | **F** | 3 | 8,780,000 | 0.01 | ❌ absent |
| `TNTD03044683` | defaulted | **na** | 1 | 1,450,000 | 11.25 | ❌ absent |

**The word `defaulted` names two different things.** It is a *coupon class* (the workbook cell
reads "N/A (Defaulted)") **and** an *exclusion reason* (the rating maps to D/SD). They are
independent: a bond can have a defaulted rating and a perfectly ordinary coupon formula.

There are then **two recovery paths keyed on different fields**:

```text
the special-coupon loop   filters on coupon_class in (zero, stepped, step-up, defaulted)
the floating loop         tests primary_reason == "defaulted" or BT <= 1.0
```

`TNTD03037967` is caught by the first, `TNTD04769276` by the second, and the two whose coupon
class is `F` or `na` are caught by **neither**. So this is not a tidiness question — it is the
same ownership duplication as the callable routing hole, for the third time, and `TNTD03067251`
is again a plain `Fixed` bond (8.78M par across three legs) that is invisible.

**Applying §7.2's rule therefore gives different outcomes per bond, not one blanket change:**

- `TNTD03067251` — held, matched, usable mark ⇒ **must emit a named `recovery` row**. Output
  565 → 566. Intentional, isolated, Gate 3.
- `TNTD03044683` — coupon class `na`, which is one of Mario's permanent exclusions, and it has
  no maturity at all. It stays **out**, but per the rule its terminal reason must state the
  **actual** reason (`na` / unclassified, permanently excluded) rather than `defaulted`.

## 14.4 Adjustment 3 — a defect in the disposition sidecars shipped last round

`outputs/corporate_disposition.csv` and `outputs/callable_disposition.csv` default to
**undated filenames**, unlike `implied_oas_<date>.csv`. Running the 3-31 driver and then the
6-10 driver leaves only the 6-10 file: the live `corporate_disposition.csv` reads
`population=732, in-output=560`, which is the **6-10** figure, and the 3-31 disposition has
been silently overwritten.

The evidence artifact built to prove nothing is silently lost was itself silently losing a
run. Fix belongs in §5.3: date the default filenames, and have the release-facts artifact
record both dates.

## 14.5 Adjustment 4 — §5.4 concerns TWO private names, not five

`core/pricing/hybrid.py:55` imports `YEAR_DAYS, _as_date, _df, price_frn, simple_forward`.
Three of those are already public names; only **`_as_date` and `_df`** are private.

Worth checking during the refactor: `_as_date` looks equivalent to the canonical
`core.utils.dates.as_date`. If they are, hybrid should use the canonical one and the seam
shrinks further — which makes this a §7.3 ownership item as well as a §5.4 naming one. Parity
must still be proven by hashes, not by inspection.

## 14.6 Adjustment 5 — removing `days_per_year` breaks one existing test

Production is clean: both call sites (`callable_risk.py:133`, `phase2_risk.py:159`) pass
`364.0` explicitly. But `tests/test_call_schedules.py:53` calls `to_lattice_schedule` **on the
default**, so §5.2's preferred "remove the argument" will fail that test until it is updated.
Naming it here so it is a planned edit rather than a surprise.

## 14.7 Adjustment 6 — a scope question for the user, not a unilateral decision

§4.1.1 says not to claim seven "unless the live VBA builder truly emits all seven request
shapes", which permits either documenting the truth or making it true. Completing the builder
is small — one more named table for the coupon schedule and three cells (`FIP_SwitchDate`,
`FIP_QuotedMarginBp`, `FIP_CurrentCouponPct`) — and it is layout-neutral in exactly the way
§B2 already established, so it is *not* the "final seven-product worksheet design" §0 forbids.

It is nevertheless in none of Workstreams A–E. **Default action: document truthfully (five
constructible, four tested), and do not extend the builder in this pass.** If the user wants
the asymmetry closed — Excel can send three exotic tree products but not a stepped bond — it
is a clearly-scoped addition and I will do it on request.

## 14.8 What is adopted unchanged

Every §1 decision, the §2 locks, the §5–§8 workstreams, the §9 shim policy, the §10 gates and
the §11 sequence are adopted as written. In particular: `TNTD04920858` stays refused and
named; the FRN current coupon is frozen under bumps with a base-curve proxy when unobserved;
ACT/364 becomes the single conversion; no counterparty request is opened; and Workstream C is
the only intentional numerical change, isolated in its own commit with a before/after table.
