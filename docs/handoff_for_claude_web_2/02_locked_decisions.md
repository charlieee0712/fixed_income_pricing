# Locked decisions

Settled. A plan may reference these; a plan should **not** re-open one unless the user
explicitly says so. Each row gives the date it was fixed and the reason, because the reason
is usually what stops it from being re-litigated by accident.

---

## 1. Methodology

| Decision | Date | Why |
|---|---|---|
| **OAS is a per-bond calibration OUTPUT, not a pricing input.** Solve the spread that makes the model reprice the custodian mark, then compute risk on the calibrated model. | 2026-06-30 (Mario) | The goal is risk metrics. Forcing a rating-average spread onto individual names produced ~6.4% dispersion; per-bond calibration removes it by construction. Supersedes the whole v1 index-OAS flow. |
| **Valuation baseline = 2009-03-31**, with 2009-06-10 kept as a control. | 2026-07-02 | Mario supplied a native-schema USD curve for 3-31, which matches the holdings date and cleared the near-maturity distortion (implied OAS 1371 → 464 bp at the extreme). |
| **Custodian `BT` is a clean price; the model PV is dirty.** Every calibration solves `clean(OAS) == BT`. | 2026-08-04 (Liping review) | Both forms have the same root because accrued is date-only, but only one of them is *stated*, and the lattice had been comparing a dirty PV to a clean mark. |
| **Duration / convexity denominator = the DIRTY price.** | 2026-08-04 | Tested both ways against custodian AQ on 61 bonds: dirty was closer on 41 of 61 (median |Δ| 0.236 vs 0.331). |
| **BT's marking date is not a mismatch to explain away.** | 2026-07-03 (Mario) | By 2009-03-31 the crisis had passed its peak and spreads had retreated; BT's tighter credit is a genuine recovering-market mark. |
| **Single-curve discounting for floaters** (project forwards and discount on the same curve). | 2026-07-08 | It is the 2009 convention and it matches the legacy tree. OIS dual-curve is documented as a future enhancement, not a defect. |
| **Sinking fund = issuer optional redemption on fractions of the OUTSTANDING amount.** An original-face basis is refused. | 2026-08-25 | Only the outstanding basis keeps value-per-unit level-free, which is what a recombining tree can represent. Original face needs a strip decomposition. |

## 2. Conventions that are frozen because everything rests on them

| Decision | Date | Why |
|---|---|---|
| **ACT/364 day count, 182-day semiannual coupon grid.** | validated 2026-06-29 | It is the legacy engine's own convention. Changing it breaks reconciliation with every validated number in the repo. Real day-count labels are carried as *data* only. |
| **Corrected discounting is the default** (`exp(-t·(z+s))` with a continuous zero); `vba_compat=True` reproduces the legacy bug exactly, for reconciliation only. | 2026-06-29 | The legacy stored a semiannual zero and discounted it continuously, systematically under-pricing. Proof: a curve must reprice its own par bonds to 100 — the bug gives 99.67 at 10y. |
| **One accrued-interest formula, shared by every engine.** | 2026-08-04 | A second copy is how clean/dirty discipline silently rots. |
| **Prices, accrued and DV01 are quoted per 100 face**; a supplied `face_value` is echoed and not applied. | 2026-08-25 | Field names are the contract; applying face while the caller sends a per-100 mark is a silent mispricing. |
| **σ = 0.15** is the v1 short-rate volatility. | 2026-07-03 (Mario) | His call, replacing 0.18. |

## 3. Architecture

| Decision | Date | Why |
|---|---|---|
| **`core/` (~80%) + `assets/` (~20%) + `endpoints/`** — many simple functions, inputs documented per function. | 2026-08-15 (Mario directive), approved 2026-08-25 | His words: the old code was "difficult to follow, a bit nested", and a Google team is taking it over for cloud optimisation. |
| **Old module paths become thin shims** and keep working until deliberately retired. | 2026-08-15 | Migration must never require a flag day. |
| **Migrations move code verbatim; float-operation order is preserved.** | 2026-08-15 | Bit-identical output is the only cheap proof that a migration changed nothing. |
| **One shared tree for callable / puttable / sinking**, not one engine each. | 2026-08-25 | Fourteen workbook rows carry two rights at once (`CALL/SINK`, `CALL/PUT`); separate engines could not price them without copying each other. |
| **Flat `endpoints/`**, not the template's `endpoints/routes/`. | 2026-08-25 | A single non-HTTP entry point does not earn a folder, and the original complaint was nesting. `routes/` arrives with the HTTP service. |
| **One transport-independent entry point** `analyze_vanilla_payload(payload) -> response`; failures are values, never exceptions. | 2026-08-25 | Any transport wraps the same function, so a second pricing implementation cannot appear. |

## 4. Data and scope

| Decision | Date | Why |
|---|---|---|
| **Client data is tracked in-repo; the repo must stay private.** | 2026-07-08 (boss-approved) | Reversal of the earlier "never commit data" rule. `data/` is the canonical location. |
| **Make-whole callables route to vanilla**, not to the lattice — option value ≈ 0. | 2026-07-02 | 46–47 bonds. Only genuine-gap callables reach the tree. |
| **Amortising (1) and N/A (4) coupon classes are ignored permanently.** | 2026-07-20 (Mario) | His explicit call. |
| **Pass-through / amortising bonds are NOT sinking-fund bonds.** No holding is rerouted on the strength of a `Sinking = Yes` flag. | 2026-08-25 | Deterministic amortisation and an issuer option are different products; the flag does not distinguish them. |
| **Web-sourced terms are PROVISIONAL.** On any Bloomberg return, diff, Bloomberg wins, log the delta. | 2026-07-30 (Mario) | His framing: interim data is fine, but every gap must be specified on a table so the whole thing can be re-run when real data lands. |
| **Convertibles are out of scope** until an equity model exists. | 2026-08-25 | One workbook row is `CONV/PUT/CALL`; put and call rights alone do not price a convertible. |

## 5. Validation

| Decision | Date | Why |
|---|---|---|
| **The 2010-03-01 Monthly batch is `legacy-stale-session`** and is not a numeric golden for any engine. | 2026-08-17 | Four independent proofs; see `19_monthly_sheet_reconciliation.md`. |
| **Only the 2012-12 batch caches are numeric goldens.** | 2026-08-17 | They reproduce at the legacy solver's own noise floor (govt 32/32, ΔOAS ≤ 0.9 bp). |
| **Tolerances**: OAS ≤ 1 bp target / 2 bp exception; duration ≤ 0.001 y; reprice ≤ 0.01. | 2026-08-17 | Re-baselined from the parity evidence rather than assumed. |
| **Validation for engines with no golden = production parity + `==` direct-call parity + invariants + a Bloomberg three-way.** | 2026-08-25 | All 474 tree-family workbook rows are stale; there is nothing to reconcile to. |

## 6. Process

| Decision | Date | Why |
|---|---|---|
| **Sample-first on big changes**: build the smallest convincing slice, get Mario's OK, then roll out. | 2026-08-15 | Keeps rework cheap. It worked — the sample was approved with three additive comments, not a redesign. |
| **The handoff bundles refresh ONLY on explicit request.** | 2026-08-17 | Previously refreshed at every milestone; the user stopped that. |
| **Deferred asks stay deferred** until the next natural touchpoint (when Mario returns the MBS data). | 2026-07-22 | Do not drip-feed small requests at a busy counterparty. |
| **Reports are written for Mario AND the Google team, who now attend the briefing.** | 2026-08-25 | Plain language throughout, plus a separate engineering section. |

---

## Round 2b (2026-08-30)

| # | decision | why | date |
|---|---|---|---|
| L28 | **`finished` on Mario's pivot column F means "in the restructured `pricer/` package"**, not "priced" | every family he marked `no` had priced in the legacy layer since July; the plain-fixed row he marked `finished` is exactly the approved vanilla sample | 08-30 |
| L29 | **Par-yield file units are DECLARED per file, never sniffed** (`PAR_YIELD_UNITS`: GBP + DKK are percent, the other 24 decimal) | no threshold separates a 0.5% Danish yield from a 0.5 decimal — a heuristic would have got DKK right by luck | 08-30 |
| L30 | **A par row scaling above 100% raises before the bootstrap runs** (`ParYieldUnitError`) | so a units mistake can never again present itself downstream as "the par curve is not arbitrage-free", which is a claim about the market | 08-30 |
| L31 | **An entry whose only evidence is one of our own error messages is not a data gap** — reproduce against the raw source first | cost: two months, a standing request to both Bloomberg channels, and one bond missing from every report | 08-30 |
| L32 | **One entry point, seven instrument types** — `bond.instrument_type` dispatches; no second endpoint, envelope or error vocabulary | adding the mortgage engine later is one map entry and one function; splitting this change would have meant two contract revisions | 08-30 |
| L33 | **A fixed-then-floating bond without its post-switch margin is REFUSED, not defaulted to zero** | a placeholder margin prices the floating leg as if the borrower paid pure index and reports a half-modelled bond as a whole one. A plain floater MAY absorb it into the spread — and the response then says so | 08-30 |
| L34 | **Production parity is local-fresh vs local-fresh**, not cross-platform | driver CSVs differ across platforms by ~3.6e-8, all in convexity; the same-machine comparison is byte-exact and therefore stricter | 08-30 |
| ~~L35~~ | ~~**The Excel bridge stays vanilla-only until Mario answers the layout question**~~ **SUPERSEDED 08-31 by L36** | the reason was right, the scope was drawn too wide: sending a type is not the same as designing a worksheet | 08-30 |
| **L36** | **Excel scope is 7 / 5 / 5 and must always be stated as three numbers** — **7** types the engine and contract support · **5** the VBA builder can construct from cells · **5** verified by a real-Excel round trip (vanilla, callable, puttable, sinking, floating). NEVER "the spreadsheet can ask for any of seven" | the bridge CAN send a type without anyone having designed the sheet it sits on; conflating the two overstated delivery in the 08-30 report. `stepped` (no coupon-table cells) and `fixed_to_floating` (no switch-date cell) stay unconstructible ON PURPOSE, because adding either makes a sixth type reachable from a layout Mario has not chosen. Pinned by `test_the_excel_bridge_emits_only_the_documented_fields`, which greps the .bas and fails when the emitted field set changes | 08-31 |
| **L37** | **A refusal that describes the CONTRACT is not a `ValueError`.** `src/pricer/errors.py`: `PricingDomainError` → `ContractTermsError(.field)` → `ExerciseTermsError`, plus `CalibrationError`, all rooted at `Exception` | the solvers' own `except ValueError` was swallowing contract refusals and reporting them as "no spread reprices this bond". Three separate bugs of that shape were fixed at their raise sites before the type itself was recognised as the defect. Only `CalibrationError` may become `CALIBRATION_FAILED` | 08-31 |
| **L38** | **The FRN running coupon is FROZEN across risk bumps, supplied or not** — unobserved, a base-curve proxy from `FrnResult.cashflows[0][2]`, held in `frn_risk_metrics` and NOT in `price_frn` | it was fixed at the last reset, so today's curve cannot move it. Leaving it projected flipped the SIGN of duration, and which answer you got depended on whether a custodian field was numeric. Placing the freeze in the risk function keeps `price_frn` a plain scenario repricer, so the par-under-any-shift telescoping invariant survives. At zero shift the proxy reproduces the old value, so price and OAS cannot move | 08-31 |
| **L39** | **ACT/364 is project law, not a parameter.** One conversion, `core/utils/dates.exercise_schedule_times`; `days_per_year` DELETED (passing it is a `TypeError`) | two implementations with different defaults is the defect; aligning their constants is the weaker fix. Give the decision one owner and delete the other | 08-31 |
| **L40** | **A defaulted SECURITY is disposed once, by the RATING** — unless a permanent Mario coupon-class exclusion outranks it, in which case the disposition names THAT | `defaulted` names a coupon class and an exclusion reason independently; a handler keyed on each left an 8.78M holding matching neither. Naming the wrong owner also hides a decision Mario made | 08-31 |
| **L41** | **Provisional terms are labelled in the OUTPUT, never only in prose.** `exercise_terms_status`, `exercise_terms_source`, `exercise_price_source`, `exercise_terms_as_of` on every lattice-priced bond; `current_coupon_source` + `risk_status` on every floater; `PROVISIONAL_TERMS` / `PROVISIONAL_RISK` at the endpoint. A missing column defaults to `provisional`, never `confirmed`; an unrecognised status is REFUSED | a call price of 100.0 looks identical whether it came from a prospectus or from a convention applied to a custodian date, and every one of ours is the second. **0 of 9 exercise schedules are confirmed.** Labels never change a number — asserted with `==` | 08-31 |
| **L42** | **Quote numbers from `docs/release_facts_<date>.md`, not from memory or from an earlier document** | it is generated by `scripts/release_facts.py` from the files a driver just wrote: rows + sha256 for five CSVs and four sidecars, plus the real pytest line. Every count error this project has shipped came from a document quoting a document | 08-31 |
