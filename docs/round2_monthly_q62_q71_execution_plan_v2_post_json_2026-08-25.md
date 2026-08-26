# Final Execution Plan — Round 2 Code-Structure Rollout for Monthly Q62–Q71 (Post-JSON/Excel Baseline)

**Date:** 2026-08-25  
**Project:** RYSE Fixed-Income Pricing  
**Execution owner:** Claude Code on the private live repository / server 47  
**Prerequisite:** start from the clean four-commit vanilla JSON/Excel result now pushed to origin and server 47, with a clean working tree and **194 green tests**; record the exact live HEAD before editing.  
**Target for this week:** a reviewable code-structure rollout and Mario-facing progress report covering the four non-bullet, non-mortgage families identified by the Monthly input dictionary: **callable, puttable, sinking-fund, and floating-rate bonds**.


## Live baseline incorporated from the completed prior round

The preceding vanilla interface round is complete and is now part of the architecture, not a future dependency:

```text
origin + server 47        synced
working trees             clean
test suite                194 green (166 + 28)
```

The live repository now contains:

```text
src/pricer/endpoints/
├── main.py                # one payload in, one response envelope out
├── contracts.py           # standard-library normalization/validation/envelopes
└── pricing.py             # thin vanilla orchestration; no pricing formulas

src/pricer/core/market/curves.py
└── resolve_curve(...)     # reusable currency/date/frequency curve seam

scripts/price_json.py       # file JSON in / file JSON out, atomic response write

integrations/excel_vba/     # thin VBA bridge, VBA-JSON 2.3.1 + MIT license,
                            # configurable runner and real fixtures
```

The existing endpoint exposes two deliberately separate operations:

```text
calibrate_and_risk
    clean market price in
    implied OAS + price/risk outputs out
    supplied OAS remains invalid in this operation

price_at_oas
    explicit OAS in
    price/risk outputs out
    no calibration step
```

This does **not** reopen the project lock that production OAS is a calibration output. It creates an explicitly named scenario/analysis operation for legacy per-metric calls and later model experiments.

The completed interface also establishes the following rules, which this round must reuse rather than redesign:

1. **JSON dates are ISO strings.** Numeric Excel serials are rejected at the Python boundary. The VBA bridge performs the Excel-date → ISO conversion.
2. **All quoted prices and risks remain per 100.** `face_value` may be accepted and echoed for client convenience, but v1 calculations do not scale with it.
3. **Currency is an external routing input, not an FX instruction.**
4. **Curve failures are distinguished** as unsupported/missing data versus `CURVE_BUILD_FAILED`; client responses do not expose repository paths.
5. **Safe leniency is retained:** lowercase currency, numeric strings, omitted request metadata, unknown fields with warnings, non-100 face, and irrelevant vanilla volatility do not break an otherwise valid request.
6. **Exact endpoint parity is locked:** successful endpoint results equal direct Python function results with `==`, not a tolerance.

### Consequences for Round 2

- Do not create a second endpoint hierarchy, contract framework, CLI, JSON parser, or Excel bridge.
- New asset wrappers must remain transport-independent but should be easy for the existing endpoint to call.
- The two existing operations provide the natural volatility split:
  - `price_at_oas` for price at fixed OAS;
  - `calibrate_and_risk` for implied OAS at fixed market price.
- New JSON schedule dates, if the endpoint is extended, use ISO strings only.
- Exercise prices, clean prices, dirty prices, DV01, and scenario prices remain on a per-100 basis regardless of echoed `face_value`.
- Any endpoint extension must reuse the current warning policy, response envelopes, sanitized error mapping, curve resolver, and exact direct-function parity tests.

---

## 0. Executive decision

Proceed with the next round, but do **not** build four separate pricing engines.

The correct decomposition is:

```text
                                  ┌─ corporate callable wrapper
one shared embedded-option tree ──┼─ corporate puttable wrapper
                                  └─ corporate sinking-fund wrapper

one shared forward-rate engine  ─── corporate floating-rate wrapper
```

This follows Mario’s `core ≈ 80% / assets ≈ 20%` principle and keeps the approved repository structure intact:

- `core/` owns reusable numerical algorithms;
- `assets/` owns thin bond-type wrappers, legacy units, input descriptions, and output names;
- old `src/pricing/*` imports remain compatibility shims;
- production drivers and numerical outputs must remain unchanged unless this plan explicitly introduces a genuinely new capability.

The endpoint/Excel seam is already implemented. This round extends pricing structure first and may attach the new wrappers to that seam only after engine parity is secure.

The round has two different kinds of work:

1. **Migration without numerical change**
   - callable/putable BDT lattice;
   - FRN forward-projection engine.
2. **A small new generic capability**
   - sinking-fund exercise on the shared tree, validated first with synthetic schedules and **not** automatically applied to URS holdings.

MBS is explicitly excluded. The Mortgage Price item in the Monthly dictionary remains for the later MBS phase.

### 0.1 Strictness balance

Keep this round **flexible on implementation shape and firm only on economic red lines**.

Hard guards:

- no drift in already validated outputs;
- no duplicated pricing logic;
- no guessed schedules or silent route changes;
- no misuse of stale Monthly caches;
- no MBS/pass-through scope creep;
- clean/dirty, OAS, curve, and risk conventions remain locked.

Flexible choices:

- exact filenames and number of modules;
- whether a helper remains a class method or becomes a small function;
- how many test files are used;
- exact scenario grid around the 15% baseline;
- whether the optional JSON dispatcher extension is included;
- whether closely related checks are combined into one parameterised test.

The executor should prefer the smallest clear change that satisfies the hard guards. The lists below are a complete design reference, not a demand to create one file, class, test, or commit for every bullet.

---

## 1. Exact interpretation of the Monthly sheet

### 1.1 Cell-range correction

Mario’s ten-item block is **Q62:Q71**, not Q61:Q70. `Q61` is the header `Description`.

**VERIFIED against the workbook 2026-08-25** (openpyxl read of `Monthly`, rows 56-75): row 60 is the
block title `Bond OAS Formula`; row 61 is the header row `Input Number | Field Name | Options |
Description` (cols N|O|P|Q); rows 62-71 carry the ten entries with **the analysisType NUMBER in
column P (1..10)** and the label in column Q. Row 67 also shows, in cols N/O, that this is input
number **1 — `AnalysisType As Double`**. So the ten cells are the option list of one input, exactly
as §1.2 states, and the number-to-label mapping below is read from the sheet, not inferred.

The ten entries are:

| Cell | Monthly description | Interpretation |
|---|---|---|
| Q62 | Bullet Bond Price | already represented by the approved vanilla/bullet sample |
| Q63 | Callable Bond Price | product family for this round |
| Q64 | Puttable Bond Price | product family for this round |
| Q65 | SinkingF price | product family for this round |
| Q66 | OAS | common embedded-option calibration output |
| Q67 | Duration | common embedded-option risk output |
| Q68 | FRN Price | product family for this round |
| Q69 | OAS FRN | FRN calibration output |
| Q70 | Duration FRN | FRN risk output |
| Q71 | Mtge Price | later MBS phase; excluded now |

Therefore, the ten cells are **ten analysis labels**, not ten separate security classes. After removing Bullet and Mortgage, the remaining work is exactly four product families:

```text
Callable
Puttable
Sinking Fund
Floating-Rate Note
```

### 1.2 Direct legacy mapping

The Monthly dictionary maps these labels to `BondOAS(analysisType)` approximately as follows:

```text
1  Bullet price
2  Callable price
3  Puttable price
4  Sinking-fund price
5  OAS
6  Duration
7  FRN price
8  FRN OAS
9  FRN duration
10 Mortgage price
```

This mapping is useful for:

- function naming;
- input-catalogue design;
- product/analysis routing;
- documenting the legacy intent.

It does **not** require copying the old VBA implementation line by line, and it does not make every saved Monthly value a valid numeric golden.

### 1.3 Monthly population findings that govern validation

The workbook inventory identifies approximately:

```text
callable-family routes     ≈ 449 rows
put-related routes          = 7 rows
sink-related routes         = 18 rows
FLOATING-labelled rows      = 426 rows
```

These are legacy-workbook inventory counts, not URS production-universe counts. The routing fields were partly populated from live Bloomberg descriptors and are incomplete or stale.

Important qualifications:

- the callable/put/sink rows are overwhelmingly in the **2010-03-01 cache**;
- that cache has already been proven to be `legacy-stale-session` and is not a valid numeric golden;
- the `FLOATING` label is broader than pure FRNs and can include fallback routes, variable structures, and hybrids;
- `NORMAL` was sometimes sent through the legacy sink flag, but a normal fixed bond is **not** thereby a sinking-fund bond;
- `CONV/PUT/CALL` is a convertible and must not be used as a puttable-bond test case without a conversion model;
- combined routes such as `CALL/PUT` and `CALL/SINK` are evidence that one shared option engine is preferable to duplicated product engines.

### 1.4 Reconciliation consequence

For this round:

- **current Python output parity and invariants are the primary acceptance evidence**;
- 2010 Monthly rows are diagnostic and three-way comparison material only;
- no executor may tune the new Python code to reproduce stale 2010 cached values;
- any relevant 2012 rows found in the live extraction may be used as numeric goldens, but the inventory currently indicates no meaningful sound 2012 cohort for these four families;
- the Monthly sheet remains authoritative for function shape, input terminology, and route inventory—not for forcing false numeric agreement.

---

## 2. Scope

### 2.1 In scope

1. Inventory the live repository after the current JSON/Excel round finishes.
2. Migrate the existing callable/putable lattice implementation into the approved `pricer/core` structure without changing existing numbers.
3. Add thin corporate wrappers for callable and puttable bonds.
4. Add a clearly bounded sinking-fund schedule capability to the shared tree.
5. **[MOVED TO ROUND 2b — see §21]** Migrate the existing FRN engine into the approved `pricer/core`
   structure without changing existing numbers.
6. **[MOVED TO ROUND 2b — see §21]** Add a thin corporate floating-rate wrapper.
7. Extend the input catalogue with separate common, tree-option, sinking, and floating inputs.
8. Add callable/putable/sinking volatility-scenario outputs that answer Mario’s question about the effects on both price and implied OAS.
9. Preserve the current hybrid engine through full regression tests because it depends on the FRN implementation, but do not migrate the hybrid wrapper in this round.
10. Add focused Monthly Q62–Q71 mapping and route diagnostics.
11. Produce a concise Mario-facing report for this week.
12. Preserve the completed vanilla JSON/Excel behavior and, if the endpoint extension remains small after migration, attach selected new product wrappers to the existing two-operation contract.
13. Update core project records after completion.

### 2.2 Out of scope

- MBS or `Q71 Mtge Price`;
- Government-MBS pool routing;
- pass-through scheduled-amortisation pricing;
- deterministic amortising-bond engine work triggered by the missing 13-security schedules;
- migration of the fixed-then-float hybrid wrapper;
- convertible bonds;
- perpetual-model redesign;
- T/U steepening and flattening;
- recovery/default models;
- EIR;
- CreditMetrics;
- FastAPI or cloud deployment;
- a new Excel workbook or a four-product Excel user interface;
- a second endpoint/contract/CLI hierarchy;
- changing the established ISO-date, per-100, currency-routing, warning, or sanitized-error policies;
- broad restructuring of `dataio`, curve loaders, drivers, or reconciliation code;
- automatic rerouting of any URS security merely because its workbook `Sinking` field says `Yes`.

---

## 3. Repository-alignment rule

The live repository after the current round is authoritative.

Before editing:

```bash
find src/pricer -maxdepth 5 -type f | sort
find src/pricing src/dataio src/curves scripts tests docs integrations \
  -maxdepth 4 -type f | sort
.venv/bin/python -m pytest -q
```

Record:

- current commit;
- current full-suite count and result;
- exact `src/pricer/` tree;
- the current endpoint files `main.py`, `contracts.py`, and `pricing.py`;
- both operations (`calibrate_and_risk`, `price_at_oas`) and their exact-parity tests;
- the existing `resolve_curve` entry point and current curve-error mapping;
- current imports used by `lattice.py`, `frn.py`, `hybrid.py`, corporate driver, callable driver, and phase-2 driver;
- current representative outputs for corporate callables, agency callables, FRNs, and hybrids;
- the actual names of the two completed JSON/Excel decision/interface documents and the current Excel integration README, so no duplicate documents are created.

Apply this rule throughout:

> Reuse an existing file when it already owns the responsibility. Add the minimum missing structure. Do not create a parallel hierarchy solely to match an illustrative diagram.

---

## 4. Preferred minimal repository delta

Adapt filenames if the live repository already has equivalent locations.

```text
src/pricer/
├── core/
│   ├── pricing/
│   │   ├── analytical.py             # existing; unchanged
│   │   ├── cashflows.py              # existing; unchanged except shared imports if needed
│   │   ├── discounting.py            # existing; unchanged
│   │   ├── tree.py                   # migrated generic short-rate lattice + option operations
│   │   └── floating.py               # migrated generic forward-projection FRN calculations
│   ├── risk/
│   │   └── sensitivities.py          # reuse; add only genuinely shared helpers if useful
│   ├── market/
│   │   ├── curves.py                 # existing curve seam
│   │   └── spreads.py                # existing OAS seam
│   └── utils/
│       └── dates.py                  # existing date seam
└── assets/
    └── corporate/
        ├── bonds_input.py            # extend existing catalogue in clear sections
        ├── vanilla.py                # existing; no change in responsibility
        ├── callable.py               # thin legacy-unit wrapper
        ├── puttable.py               # thin legacy-unit wrapper
        ├── sinking.py                # thin legacy-unit wrapper; schedule required
        └── floating.py               # thin legacy-unit wrapper

src/pricing/
├── lattice.py                        # compatibility shim after migration
├── frn.py                            # compatibility shim after migration
└── hybrid.py                         # remains implementation or existing module this round;
                                     # must continue to work bit-identically

tests/
├── test_pricer_tree_structure.py
├── test_pricer_floating_structure.py
└── test_monthly_q62_q71_mapping.py   # merge files if the project prefers fewer modules

# Already exists; modify only if the late endpoint-attachment gate is taken:
src/pricer/endpoints/{main,contracts,pricing}.py
scripts/price_json.py
```

### Do not add in this round unless the live code genuinely needs them

```text
BaseEngine
BaseAsset
AssetFactory
generic instrument class hierarchy
volatility surface module
new curve package
new schedule database abstraction
new HTTP routes
empty future-asset folders
```

A scalar BDT volatility input does not justify creating `core/market/volatility.py`. Add that module only when the project actually has a volatility curve/surface or a reusable volatility-data interface.

---

## 5. Core design — one embedded-option tree

### 5.1 Preserve the validated tree first

The existing BDT implementation is already validated for:

- curve fit;
- straight-bond equivalence;
- callable/putable ordering;
- data-driven exercise schedules;
- clean-vs-clean OAS calibration;
- dirty-price duration denominator;
- corporate and agency callable production runs;
- volatility default `σ = 0.15`.

The first tree commit is a **migration**, not a redesign.

Move the implementation to the selected `pricer/core/pricing/tree.py` location while preserving:

- public behavior;
- operation order;
- grid construction;
- Arrow-Debreu / forward-induction sequence;
- schedule mapping;
- accrued-interest treatment;
- OAS convention;
- risk bump convention;
- all existing outputs.

Keep `src/pricing/lattice.py` as a thin shim that re-exports the same objects and functions.

### 5.2 Natural helper boundaries

Extract helpers only at real conceptual boundaries and only if parity remains exact. Possible responsibilities:

```text
build_short_rate_tree
calibrate_tree_step
map_schedule_to_tree
rollback_cashflows
apply_call_right
apply_put_right
apply_sinking_redemption
price_embedded_option_bond
solve_embedded_option_oas
embedded_option_risk_metrics
volatility_scenario_metrics
```

These names are illustrative. Do not rename stable current functions merely to match them.

Avoid splitting the innermost numerical loop into many tiny calls if doing so changes floating-point order, obscures performance, or weakens parity evidence.

### 5.3 Call and put rights

The shared tree must support:

- call schedule only;
- put schedule only;
- both call and put schedules;
- neither schedule, which must reduce exactly to a straight bond on the tree.

Economic behavior:

```text
call right: issuer caps the continuation value at the contractual call amount
put right:  holder floors the continuation value at the contractual put amount
```

For a same-node call and put, use one documented exercise function and preserve the economically valid interval. If `put_price > call_price` on the same date, return a clear data-validation error rather than silently choosing an order.

Exercise prices and accrued interest must remain consistent with the project’s locked clean/dirty law. Do not introduce a second accrued-interest formula.

### 5.4 Combined features

The low-level core should be capable of accepting more than one schedule because the legacy inventory contains `CALL/PUT` and `CALL/SINK` routes.

This round does **not** require separate asset wrappers for every combination. It requires that the shared core not make future combined products impossible.

Exclude `CONV/PUT/CALL` from tests and outputs unless a conversion engine is supplied; the put/call rights alone do not price a convertible correctly.

---

## 6. Sinking-fund design — do not conflate two different products

### 6.1 Critical distinction

There are at least two economically different structures:

1. **Issuer sinking-fund redemption / partial refunding**
   - a contractual amount or fraction can be retired on scheduled dates;
   - the issuer may satisfy the requirement through a redemption or market purchase;
   - this can behave like partial issuer optionality and belongs in the tree.
2. **Deterministic scheduled principal amortisation**
   - principal cash flows are fixed by a known factor/amortisation schedule;
   - this is a cash-flow engine problem, not the same optional sinking-fund exercise rule.

The URS `Sinking=Yes` field is not sufficient to distinguish these. In the corporate terms file, most such rows are the pass-through/amortising structures already waiting for schedules. They must **not** be sent to the optional sinking-fund tree.

### 6.2 Capability implemented in this round

Implement only the first mode in the embedded-option tree:

```text
issuer_optional_redemption
```

Use a canonical internal schedule such as:

```text
(date/time, redemption_fraction, redemption_price_per_100)
```

The source adapter or caller must document whether the fraction is based on original or outstanding principal. Do not guess the basis from a free-text workbook field.

The wrapper may accept a schedule directly. A production CSV loader is not required until real URS sinking-fund terms are available.

### 6.3 Production routing rule

No current URS security enters the new sinking route unless all of the following are explicit:

- it is a true sinking-fund security rather than a pass-through/amortizer;
- redemption dates are known;
- redemption fractions or amounts are known;
- redemption prices are known;
- the fraction basis is known;
- the schedule passes validation.

Otherwise retain the current route and current BT-mark/data-gap treatment.

### 6.4 Future deterministic amortisation

Record—but do not implement here—a separate future seam:

```text
core/pricing/amortizing.py
```

That future engine will be triggered by arrival of the 13 pass-through schedules and must not reuse the optional-sinking node rule.

---

## 7. FRN design — preserve the current project method

### 7.1 Current method remains authoritative

The existing project FRN engine is already methodologically settled:

- future coupon projection from simple forwards on the existing `ZeroCurve`;
- quoted margin added to the reference forward;
- the same curve plus flat implied OAS used for discounting;
- single-curve treatment retained as the 2009 convention;
- implied OAS calibrated to clean `BT`;
- effective duration bumps the **curve**, reprojects forwards, and rediscounts;
- near-par FRN duration is close to the next-reset horizon;
- deep-discount long FRNs may have a small or negative credit-spread-annuity duration.

Do not replace this with a literal copy of the legacy FRN tree merely to match the Monthly label.

### 7.2 Migration target

Move the reusable numerical implementation to `pricer/core/pricing/floating.py` or the closest live equivalent.

Keep the asset wrapper in `pricer/assets/corporate/floating.py` responsible for:

- legacy units;
- required/optional input list;
- simple per-output functions;
- user-readable diagnostics such as `next_reset_t`;
- quoted-margin terminology.

Keep `src/pricing/frn.py` as a shim.

### 7.3 Hybrid dependency guard

The fixed-then-float hybrid engine depends on FRN behavior. Although the hybrid wrapper is out of scope, the migration is incomplete unless all existing hybrid tests and representative outputs remain bit-identical.

Do not migrate or redesign `hybrid.py` in the same commits. Only repair imports as necessary to point through the new implementation/shim without changing results.

### 7.4 FRN volatility policy

The current deterministic FRN engine does not use a standalone short-rate-volatility input. Return or document:

```text
yield_volatility_applicable = false
reason = current FRN method projects forwards from the curve and has no stochastic volatility parameter
```

Do not manufacture a zero vega. If a later callable-FRN or stochastic-rate FRN model is developed, it becomes a separate product extension.

---

## 8. Thin asset-layer function surfaces

Use the Monthly pattern: one simple function per requested output, with a shared input list.

### 8.1 Callable

Preferred surface, adapted to current naming:

```text
calculated_price
implied_oas
duration
dv01
convexity
widening
tightening
price_at_volatility
implied_oas_at_volatility
volatility_sensitivity
```

### 8.2 Puttable

Use the same output names and units as callable. The only product-specific input is the put schedule.

### 8.3 Sinking fund

Use the same price/OAS/risk/scenario outputs, requiring a validated sinking schedule. Include a diagnostic field such as:

```text
sinking_mode = issuer_optional_redemption
```

### 8.4 Floating-rate note

```text
calculated_price
implied_oas
duration
dv01
convexity
widening
tightening
next_reset_time
```

No standalone volatility output is required.

### 8.5 Units

Asset wrappers retain legacy-facing units:

```text
coupon and current coupon     percent
clean/dirty prices            per 100
OAS and scenario shifts       basis points
volatility                    decimal (0.15 = 15%)
volatility bump               decimal (0.01 = one vol percentage point)
face / face_value             external value may be echoed; all v1 calculations remain per 100
```

Core functions retain decimal/internal units.

---

## 9. Input catalogue

Extend the existing `bonds_input.py`; do not create several small catalogue files unless the live file has become genuinely unreadable.

Recommended sections:

```text
COMMON_BOND_INPUTS
EMBEDDED_OPTION_COMMON_INPUTS
CALLABLE_INPUTS
PUTTABLE_INPUTS
SINKING_INPUTS
FLOATING_INPUTS
```

### 9.1 Common bond inputs

```text
coupon
coupon_frequency
maturity
valuation_date
currency / resolved curve
market_clean_price
oas                  # internal/downstream result; externally accepted only by price_at_oas
face / face_value     # v1 endpoint echo only; core and quoted outputs remain on a 100 basis
day_count_label       # carried data; current ACT/364 convention remains locked
scenario_shift_bp
```

### 9.2 Embedded-option common inputs

```text
volatility_decimal
coupon dates / cash-flow schedule
exercise schedule(s)
```

Use `0.15` only as the existing production default where that decision already applies. The wrapper should allow an explicit alternative scenario value.

### 9.3 Callable

```text
call_schedule = [(date, price_per_100), ...]
```

### 9.4 Puttable

```text
put_schedule = [(date, price_per_100), ...]
```

### 9.5 Sinking

```text
sinking_schedule = [(date, fraction, price_per_100), ...]
fraction_basis
sinking_mode = issuer_optional_redemption
```

### 9.6 Floating

Use the current live-engine requirements, documented clearly. Depending on the current function surface, these may include:

```text
quoted_margin_bp
reset/coupon_frequency
reference-rate label
last reset or schedule anchor
current coupon when required
```

Do not add fields that the implementation does not use merely because the legacy input dictionary listed them.

---

## 10. Volatility outputs — answer Mario’s question explicitly

For every embedded-option family, report two different experiments. They answer different economic questions and must never be conflated. The completed endpoint already gives these experiments clean operation names; reuse them if the optional endpoint attachment is implemented.

### 10.1 Fixed OAS, change volatility

```text
Hold:
- curve
- cash flows
- exercise schedules
- calibrated baseline OAS

Change:
- volatility

Report:
- model price at each volatility
```

This answers: **how does the model price change when rate volatility changes?**

Endpoint mapping, when attached:

```text
operation = price_at_oas
hold supplied/baseline OAS fixed
change model volatility
```

### 10.2 Fixed market price, change volatility and recalibrate OAS

```text
Hold:
- clean market price
- curve
- cash flows
- exercise schedules

Change:
- volatility
- re-solve implied OAS at each volatility

Report:
- implied OAS at each volatility
```

This answers: **how does the OAS required to match the same market price change when volatility changes?**

Endpoint mapping, when attached:

```text
operation = calibrate_and_risk
hold clean market price fixed
change model volatility
re-solve implied OAS
```

### 10.3 Standard scenario table

For the Mario report, a simple scenario grid is preferred unless the live code already has a standard:

```text
10%
15% baseline
20%
```

An equivalent compact grid is acceptable if it communicates the same price/OAS relationship clearly.

Also calculate local sensitivities around the baseline using a one-vol-point bump if useful:

```text
price_vega_per_1_vol_point
implied_oas_change_bp_per_1_vol_point
```

State the unit in every output.

### 10.4 Directional tests

Use controlled synthetic fixtures, not universal economic assertions:

- in a deliberately call-active fixture, higher volatility should lower callable price at fixed OAS and normally tighten the recalibrated OAS at fixed price;
- in a deliberately put-active fixture, higher volatility should raise puttable price at fixed OAS and normally widen the recalibrated OAS at fixed price;
- do not impose a universal sign test on every real security or sinking schedule;
- scenario results for real bonds are outputs, not assumptions to be hard-coded.

---

## 11. JSON/Excel attachment boundary

The vanilla JSON/Excel bridge is complete. It is now a regression surface that this round must preserve.

### 11.1 Hard requirements

- do not add a parallel endpoint, contract layer, CLI, JSON parser, or VBA bridge;
- keep all new pricing functions independent of Excel and file transport;
- preserve both existing vanilla operations and their exact direct-function parity;
- reuse `resolve_curve`, the existing response envelopes, warning policy, and sanitized error mapping;
- preserve the v1 per-100 convention:
  - `face_value` may be accepted/echoed;
  - it must not scale model prices, exercise prices, OAS calibration, duration, DV01, or convexity;
- at any JSON boundary, bond dates and exercise-schedule dates are ISO strings; numeric Excel serials remain invalid;
- `calibrate_and_risk` continues to reject a supplied absolute OAS;
- `price_at_oas` remains the only v1 operation that accepts explicit OAS.

### 11.2 Recommended late attachment, but not an engine-completion blocker

After the tree and FRN migrations are stable, Claude Code may extend the **existing** endpoint files if the change stays thin and reviewable.

Preferred minimal extension:

```text
instrument_type:
    vanilla
    callable
    puttable
    sinking_fund
    floating

operation:
    calibrate_and_risk
    price_at_oas
```

The endpoint may normalize schedules and dispatch to the new asset wrappers, but it must not implement tree rollback, forward projection, OAS solving, sensitivities, or accrued interest.

Pragmatic scope rule:

- **Callable and FRN** are the highest-value endpoint additions because they have current production implementations and real regression cohorts.
- **Puttable and sinking-fund** may be attached using controlled fixtures if the contract remains simple.
- If puttable/sinking contract design starts to dominate the migration, document their future field map and defer their endpoint dispatch without failing the round.

Any successful new endpoint fixture must satisfy exact equality with direct wrapper calls before JSON serialization.

### 11.3 Excel boundary

Do not expand the Excel demonstration workbook in this round.

Only update `integrations/excel_vba/README.md` or the current interface document if needed to state:

- the same one-JSON-in/one-JSON-out seam will later accept the new `instrument_type` values;
- schedule dates will be emitted as ISO strings;
- exercise prices and model outputs are per 100;
- local runner / packaged executable / HTTP transport can reuse the same field meanings.

No new VBA pricing logic is permitted.

---

## 12. Execution gates

### Gate 0 — clean baseline and origin recon

Before code changes:

1. start from the clean four-commit result pushed to origin and server 47;
2. run the full suite and confirm the expected live baseline of **194 green** (or record and explain any legitimate later additions);
3. inventory the live tree and imports;
4. freeze representative outputs for:
   - all currently priced corporate callables;
   - all five agency callables;
   - a representative near-par FRN;
   - a representative deep-discount FRN with negative duration;
   - at least two existing hybrids;
5. read the current `lattice.py`, `frn.py`, and relevant `BondOAS` origin branches in full;
6. record the exact Q62:Q71 mapping and the legacy call/put/sink/FRN analysis-type behavior;
7. confirm the current Monthly route census and which dates/caches exist;
8. freeze the existing vanilla endpoint success/error fixtures for both operations;
9. record the exact current behavior of ISO dates, echoed `face_value`, unknown-field warnings, volatility non-use, and `CURVE_BUILD_FAILED` so Round 2 cannot regress them.

Deliverable:

```text
docs/monthly_q62_q71_non_mortgage_mapping_2026-08-25.md
```

This memo should distinguish source facts, current project choices, and legacy behavior that will not be copied.

### Gate 1 — tree migration only

1. move/re-export the current generic lattice into `pricer/core/pricing/tree.py` or the selected live equivalent;
2. turn `src/pricing/lattice.py` into a compatibility shim;
3. make no feature changes in this commit;
4. preserve existing object/function identity where practical;
5. rerun every existing callable, price-convention, phase-2, and full-suite test;
6. compare frozen production outputs bit-for-bit.

Stop and diagnose any numerical drift before continuing.

### Gate 2 — callable and puttable asset wrappers

1. add thin wrappers;
2. add numbered input docstrings and catalogue entries;
3. preserve all current callable behavior;
4. expose puttable calculations through the same core;
5. add combined call/put low-level support if not already present;
6. add price/OAS volatility scenarios;
7. keep all drivers unchanged unless a minimal import update is necessary.

### Gate 3 — sinking-fund extension

1. re-read and document the legacy sinking branch before coding;
2. add a canonical in-memory sinking schedule;
3. implement `issuer_optional_redemption` on the shared tree;
4. validate with synthetic schedules;
5. add a thin corporate wrapper;
6. do **not** route pass-through/amortising URS rows;
7. do **not** create guessed schedule data;
8. update the missing-data registry only if the live inventory reveals a real held security that is otherwise ready to price.

### Gate 4 — FRN migration  *(ROUND 2b — next week; see §21)*

1. move the current FRN numerical implementation into `pricer/core/pricing/floating.py` or the selected equivalent;
2. retain `src/pricing/frn.py` as a shim;
3. add the thin corporate floating wrapper;
4. preserve forward projection, quoted margin, OAS calibration, and curve-bump duration exactly;
5. rerun the entire FRN and hybrid test set;
6. compare frozen FRN and hybrid outputs bit-for-bit.

### Gate 5 — optional/recommended endpoint attachment

Take this gate only after Gates 1–4 are stable.

1. modify the existing `contracts.py`, `pricing.py`, and/or `main.py`; do not create parallel files;
2. preserve `calibrate_and_risk` and `price_at_oas` semantics;
3. reuse the existing curve resolver and error taxonomy;
4. normalize new schedule dates from ISO strings only;
5. preserve per-100 economics regardless of echoed `face_value`;
6. add exact direct-wrapper parity tests for every instrument type actually exposed;
7. preserve all prior vanilla endpoint fixtures bit-for-bit except for intentionally additive warning/metadata fields;
8. do not modify the Excel UI.

This gate is recommended for callable and FRN if it remains a thin dispatch change. It is not allowed to delay or destabilise the engine migration.

### Gate 6 — Monthly diagnostics

Produce a focused reconciliation artifact for the four families.

Do not claim a numeric golden where none exists. The output should classify every examined row as one of:

```text
current-code-session-golden
legacy-stale-session
route-ambiguous
combined-feature
convertible-excluded
missing-schedule
model-methodology-divergence
comparable-three-way
```

Required comparisons where data exist:

- new `pricer` result vs old Python path: exact parity;
- new result vs sound Monthly cache: numeric tolerance;
- new result vs stale Monthly cache: descriptive only;
- new/current result vs Bloomberg duration column: three-way diagnostic;
- OAS vs Bloomberg only with the existing pull-date/basis warning.

Do not open the SteepFlat/T/U ask in this round.

### Gate 7 — report and records

After all tests pass:

1. write the Mario-facing report;
2. update `WORKLOG.md`, `PROJECT_STATUS.md`, and `CLAUDE.md`;
3. update `COVERAGE.md` only if actual production routing or coverage changed;
4. update `docs/missing_data.md` only for a real newly identified data requirement;
5. do not refresh the web handoff bundle unless the user explicitly requests it.

---

## 13. Test plan

### 13.1 Migration locks

- full pre-round suite stays green after every code-bearing commit;
- legacy imports still work;
- new code imports `pricer.*`, not the old shims;
- frozen callable, agency, FRN, and hybrid outputs remain bit-identical;
- existing clean/dirty invariance tests remain unchanged and green.

### 13.2 Shared tree invariants

At minimum:

1. no exercise schedules ⇒ tree price equals the analytical straight-bond dirty price to the existing tolerance;
2. callable price ≤ straight price in a controlled fixture;
3. puttable price ≥ straight price in a controlled fixture;
4. callable-only ≤ call+put ≤ puttable-only when schedules are mutually valid;
5. later/higher call price does not make the issuer option more valuable in a controlled fixture;
6. higher put price does not reduce the holder’s put value;
7. out-of-the-money or post-maturity schedule degenerates to straight;
8. `σ=0` degeneracy remains valid;
9. OAS round-trip returns the seeded value;
10. clean-form and dirty-form calibration roots agree under the shared accrued formula;
11. duration/DV01/convexity use the locked dirty denominator;
12. schedule ordering is stable and duplicate dates are handled deterministically or rejected clearly.

### 13.3 Sinking invariants

Use controlled synthetic schedules:

1. zero redemption fraction ⇒ straight bond;
2. a full optional par redemption on one date behaves like a call at par on that date under the same exercise timing;
3. cumulative redeemed fraction cannot exceed the documented basis;
4. fractions must be in a valid range;
5. dates after maturity have no effect or return a clear validation warning;
6. increasing the optional redemption fraction does not increase investor value in a deliberately in-the-money issuer-redemption fixture;
7. principal/coupon treatment is internally conserved under the chosen schedule basis;
8. deterministic amortisation is not silently accepted as optional sinking mode.

### 13.4 Volatility tests

- 10% / 15% / 20% scenario calls produce finite results;
- baseline 15% reproduces existing production outputs;
- call-active and put-active controlled fixtures have the expected directional behavior described in §10.4;
- fixed-OAS price scenario and fixed-price recalibrated-OAS scenario are tested separately;
- `price_vega` and `oas_vega` units are explicit;
- FRN returns volatility non-applicability rather than a fabricated numeric sensitivity.

### 13.5 FRN invariants

Retain all existing locks and add wrapper parity:

- zero-spread/zero-OAS par-floater identity;
- implied-OAS round-trip;
- near-par duration close to next reset;
- FRN duration much smaller than same-maturity fixed in controlled cases;
- deep-discount negative-duration case retained;
- curve bump reprojects forwards;
- wrapper output equals direct old-Python output;
- hybrid limit/composition tests remain green.

### 13.6 Endpoint regression and optional extension

Always retain:

- both vanilla operations;
- exact endpoint-versus-direct equality;
- ISO-string date acceptance and numeric-date rejection;
- lowercase currency and numeric-string normalization;
- unknown-field warning behavior;
- `face_value` echo without economic scaling;
- sanitized `CURVE_BUILD_FAILED` responses;
- no raw repository path in client errors.

If new product dispatch is exposed:

- `price_at_oas` calls the relevant wrapper without calibration;
- `calibrate_and_risk` calibrates from clean market price and rejects supplied OAS;
- callable/puttable/sinking schedule dates accept ISO strings only;
- exercise prices stay per 100 even when `face_value != 100`;
- volatility fixed-OAS and fixed-price results equal direct wrapper calls exactly;
- FRN reports volatility non-applicability rather than a fabricated value.

### 13.7 Monthly mapping tests

- Q61 is the header;
- Q62:Q71 labels remain exactly mapped;
- Bullet and Mortgage are excluded from this round’s four-family set;
- `NORMAL` is not automatically treated as sinking;
- `CONV/PUT/CALL` remains excluded;
- stale 2010 rows receive `legacy-stale-session`, not a numeric pass/fail verdict.

---

## 14. Acceptance criteria

The following are the **hard completion criteria**. Related checks may be combined when existing tests already prove the same behavior; do not add ceremonial tests or files solely to satisfy a count.

The round is complete when:

1. the **194-green** live baseline plus all new tests is green;
2. the approved vanilla endpoint, Excel bridge, two operations, ISO-date policy, per-100 policy, warning behavior, and sanitized errors are not disrupted;
3. existing callable, agency-callable, FRN, and hybrid outputs are bit-identical;
4. `pricer/core/pricing/tree.py` or its live equivalent is the single implementation used by callable and puttable wrappers;
5. sinking-fund optional redemption is implemented once in that shared core and is invariant-tested;
6. no URS pass-through/amortising bond is misrouted into the sinking tree;
7. `pricer/core/pricing/floating.py` or its live equivalent is the single FRN implementation;
8. asset wrappers expose simple per-output functions in legacy units;
9. all functions carry numbered input documentation;
10. callable/putable/sinking outputs separately show:
    - price changes at fixed OAS when volatility changes;
    - implied-OAS changes at fixed market price when volatility changes;
11. FRN volatility non-applicability is explicit;
12. Monthly Q62:Q71 is documented correctly;
13. stale 2010 caches are not used as false goldens;
14. MBS, pass-through amortisation, hybrid migration, and convertibles remain outside the code changes;
15. old import paths remain functional shims;
16. the Mario-facing report is accurate about which families have production data versus synthetic/invariant validation;
17. no new Mario/Liping data request is sent automatically;
18. the repo remains private and no client data enters public examples or logs;
19. if the endpoint is extended, every exposed new product has exact direct-wrapper parity and no duplicate pricing implementation;
20. if the endpoint is not extended, the current JSON/Excel interface document contains a concise future field map and the engine round is still considered complete.

---

## 15. Mario-facing report content

Create:

```text
docs/code_structure_round2_embedded_options_frn_2026-08-XX.md
```

The report should be understandable without reading code and include:

### 15.1 What was migrated

```text
one shared interest-rate tree
  → callable
  → puttable
  → sinking-fund optional redemption

one shared forward-rate engine
  → floating-rate notes
```

### 15.2 Why this is simpler

- no duplicated tree code;
- one schedule-based engine can accept call, put, or sink terms;
- one simple function per requested output;
- inputs listed explicitly;
- old code continues to work through shims;
- later JSON/Excel calls can use the same wrappers.

### 15.3 What was proven

Report separately:

- **Callable:** production-output parity, corporate and agency examples, volatility scenarios;
- **Puttable:** shared-engine and invariant validation; state honestly if no current URS production cohort is available;
- **Sinking:** generic schedule capability and synthetic validation; explicitly state that pass-through/amortising URS bonds remain data-gated and were not reclassified;
- **FRN:** production-output parity, next-reset-duration behavior, deep-discount example, and hybrid dependency regression;
- **Monthly:** exact function/input mapping, but stale 2010 caches are not misrepresented as goldens.

### 15.4 Volatility answer

Include a compact table for at least one call-active bond:

```text
volatility
price at fixed baseline OAS
implied OAS at fixed market price
```

If a suitable puttable fixture is synthetic, label it clearly as a model validation example rather than a URS holding.

### 15.5 Boundaries

- MBS waits for data and its own phase;
- pass-through amortisation remains separate;
- callable FRNs/hybrids are not silently approximated;
- no numeric Monthly claim is made from stale caches.

---

## 16. Documents Claude Code should add or update

### New documents

```text
docs/monthly_q62_q71_non_mortgage_mapping_2026-08-25.md
docs/code_structure_round2_embedded_options_frn_2026-08-XX.md
```

### Update after completion

```text
WORKLOG.md
PROJECT_STATUS.md
CLAUDE.md
```

### Conditional updates

```text
COVERAGE.md                         # only if production routes/counts change
docs/missing_data.md                # only if a real new data gap is identified
the existing JSON/Excel interface doc
                                      # update only if endpoint dispatch is added,
                                      # or add a short future field map if it is deferred
integrations/excel_vba/README.md     # wording only; no new workbook/UI required
```

Do not create another vanilla JSON/Excel decision record, interface reference, CLI guide, or Excel bridge README. Reuse the documents delivered by the completed prior round.

### Do not update automatically

```text
docs/handoff_for_claude_web/
```

Refresh that bundle only on the user’s explicit instruction.

---

## 17. Suggested commit sequence

Adapt to the live tree, but keep migration and feature work reviewable.

```text
1. docs: record Q62-Q71 mapping, route inventory, and Round-2 scope
2. refactor: move the validated lattice into pricer core with old-path shim
3. feat: add callable and puttable thin wrappers plus input catalogue sections
4. feat: add embedded-option volatility price/OAS scenarios
5. feat: add optional sinking-fund schedule support and synthetic invariants
6. refactor: move FRN implementation into pricer core with old-path shim
7. feat: add floating-rate thin wrapper and wrapper parity tests
8. feat (optional): attach callable/FRN and, if still simple, puttable/sinking to the existing endpoint
9. test: add Monthly route diagnostics and stale-session guards
10. docs: add Mario-facing Round-2 report
11. docs: update WORKLOG, PROJECT_STATUS, and CLAUDE
```

Run the full suite after every code-bearing commit.

Do not combine tree migration, sinking new logic, and FRN migration into one large commit.

---

## 18. Stop conditions and adjustment rules

Stop the affected gate and diagnose before proceeding if:

- moving an implementation changes a frozen output;
- a new helper changes floating-point order;
- clean/dirty calibration invariance breaks;
- the 194-green JSON/Excel baseline no longer reproduces or either existing operation regresses;
- a sinking schedule’s fraction basis cannot be established;
- a Monthly row requires convertible, mortgage, or hybrid functionality outside scope;
- a legacy value belongs to the stale 2010 cache but appears to pressure the implementation toward a numerical change.

Allowed adjustment:

- keep a larger existing function intact inside the new module if splitting it would create numerical risk;
- combine test files if the repository prefers fewer files;
- reuse an existing `routes/`, `models/`, or input-catalogue file rather than adding the preferred filename;
- defer some or all new endpoint dispatch without affecting engine-round completion;
- keep `face_value` as echo-only and add a clearer warning/diagnostic rather than introducing position scaling in this round.

Not allowed:

- copying the same tree logic into three asset wrappers;
- defaulting missing schedules to par assumptions silently;
- treating every `Sinking=Yes` row as a sinkable option bond;
- using the stale 2010 cache as a tuning target;
- pulling MBS or pass-through work into this round.

---

## 21. Execution revision (2026-08-25, Claude Code)

Adjustments made before starting, after the repository-alignment gate (§3), a workbook read, and
one Fable-advisor consult. **This section is authoritative where it conflicts with the body.**

### 21.0 True baseline

The prior round shipped **seven** commits, not four (the last three closed the Excel side): live HEAD
`c8d0a83`, clean tree, origin and 47 in sync, **194 green**. New since the plan was written: the
suite also runs **locally on Windows in 18.8s** — the "no usable local Python" note in CLAUDE.md was
wrong; `C:\Users\cnc\anaconda3\anaconda2025\python.exe` (3.13.5, numpy/pandas/scipy/pytest) runs
everything, and the endpoint's JSON output is byte-identical to 47's. Gate 0 can therefore freeze
outputs locally and cross-check on 47.

### 21.1 Decision — split into Round 2a (this week) and Round 2b (next week)

The user offered FRN as the movable piece if the week is too full. **It is: FRN moves to 2b.**

```text
Round 2a (this week)   Gates 0-3, 5 (partial), 6, 7
                       one shared tree -> callable + puttable + sinking-fund
                       the volatility answer Mario actually asked for

Round 2b (next week)   Gate 4 + the floating wrapper + FRN endpoint dispatch
                       + the hybrid regression that guards it
```

Reasons, in order of weight:

1. **This week's headline is entirely a tree story.** Mario asked what happens to price and OAS when
   volatility changes. That question has a quantitative answer for callable/puttable/sinking and the
   answer "not applicable, and here is why" for the deterministic FRN engine. Deferring FRN costs the
   report nothing it needs.
2. **The tree cluster has internal synergy; FRN does not share it.** One migration (225 lines) serves
   three wrappers. FRN is a separate 188-line engine, a separate wrapper, a separate input set and a
   separate endpoint contract — its marginal cost is additive, not shared.
3. **The only genuinely new modelling in this round is the sinking-fund exercise rule.** New capability
   is where errors hide, and it should get the week's thinking budget rather than its remainder.

Gate 0's output freeze stays **full-width — FRN and hybrids included** — even though they are not
touched this week. It costs nothing now and gives Round 2b a freeze taken from a known-good state.

**Round 2b carry-over facts, recorded now while they are in hand:**

- `src/pricing/hybrid.py` imports FRN **private** names: `from pricing.frn import YEAR_DAYS, _as_date,
  _df, price_frn, simple_forward`. The `frn.py` shim must re-export the privates too, or the hybrid
  engine breaks on import — this is the single most likely way that migration goes wrong.
- Other FRN import sites: `scripts/calibrate_risk.py`, `tests/test_frn.py`,
  `tests/test_price_convention.py`, `tests/test_hybrid.py`.

### 21.2 Decision — sinking fund is issuer optional redemption on fractions of OUTSTANDING

The plan (§6.2) leaves the fraction basis to "the caller"; the implementation cannot. **v1 implements
the outstanding basis, in the tree, and refuses the original basis with a pointer to its future
route.** The reason is not preference, it is correctness on a recombining lattice:

> With per-date fractions of *outstanding*, every remaining cash flow — coupons, later redemption
> amounts, final principal — scales linearly with the outstanding amount. The value *per unit
> outstanding* is therefore independent of how much was retired earlier, so the node value is
> path-independent and the tree stays recombining. With fractions of *original* face the retired
> amount is a fixed quantity against a varying base, the per-unit value stops being level-free, and a
> recombining tree can no longer represent it — that structure needs a strip decomposition (one
> callable sub-bond per sink date), which is a different implementation and is deferred.

The node rule, applied at exactly the point the existing call cap fires (on the discounted
continuation, **ex-coupon**, steps `i >= 1` — verified by reading `price_bond`):

```text
cont = (1 - f_i) * cont + f_i * min(cont, P_i)
```

Properties, all of which become tests:

- `f = 1` reduces to `min(cont, P)`, i.e. **literally the existing call path** — the anchor invariant;
- value is non-increasing in `f`, strictly decreasing only when the redemption is in the money;
- `f = 0` is a no-op, so an inactive step is encoded as `f = 0` and the formula never multiplies a
  fraction into a price on its own (`0 * inf` would be `NaN` — the inactive call price is `+inf`);
- cumulative retirement is `1 - prod(1 - f_i) <= 1` **by construction**, so §13.3 #3 needs no
  separate range check.

`fraction_basis` must be supplied and must be `"outstanding"`; `"original"` returns a clear error
naming the strip decomposition. Accepting a label the engine does not implement would be the
`face_value` trap again: leniency is for presentation, never for a basis that silently changes the
number.

### 21.3 Correction — the call/put conflict rule does NOT exist yet

§5.3 requires a validation error when `put_price > call_price` on the same date. The live core does
not do that. It applies the cap then the floor:

```python
cont = np.minimum(cont, call_price[i])     # issuer
cont = np.maximum(cont, put_price[i])      # holder  <- silently wins any conflict
```

So today a contradictory pair is resolved in the holder's favour with no signal. Add the check in the
**wrapper/validation layer** (put <= call at intersecting dates, else refuse with both values named);
do **not** reorder or branch the core's float path — that path is the thing this round must keep
bit-identical. Same-date **call + sink** is likewise refused in v1 with a message, because the
application order of two rights on one node changes the number and no order is currently tested; the
core keeps both arrays possible so the combined `CALL/SINK` route stays reachable later.

### 21.4 Reuse, don't fork, the date -> tree-time conversion

Wrappers take `[(date, price)]`; the lattice consumes `[(time_years, price)]`.
`dataio.call_schedules.to_lattice_schedule` already owns that conversion on the ACT/364 convention
and is golden-tested. Reuse it (or its exact convention) rather than writing a second formula — a
forked date arithmetic is precisely the class of bug this migration exists to prevent.

### 21.5 Schedule leniency, calibrated

Forgive presentation, refuse economic contradiction:

```text
forgiven   unsorted schedules (sorted on the way in), numeric strings, any date form the Python
           layer can parse (the ISO-string-only rule stays a JSON-boundary rule, not a Python-API
           rule), duplicate dates carrying the SAME price (deduped with a warning)
refused    put price > call price on the same date; a fraction outside (0, 1]; fraction_basis
           other than "outstanding"; duplicate dates carrying DIFFERENT prices; a schedule whose
           dates all fall after maturity (nothing to exercise)
```

### 21.6 Endpoint (Gate 5) — pre-commitment, final call still at the gate

`put_schedule` has byte-for-byte the same shape as `call_schedule`, so puttable dispatch is one key
on the same normaliser once callable exists. Sinking adds a third tuple element plus `fraction_basis`
— exactly the contract growth §11.2 warns can dominate the round.

```text
attach this week (if still thin)   instrument_type = callable, puttable
defer with a documented field map  instrument_type = sinking_fund
already live                       instrument_type = vanilla (unchanged)
```

### 21.7 Gate 6 reuses the frozen Monthly extracts

`outputs/monthly_golden_rows.csv` (2,642 rows) and `outputs/monthly_recon_rows.csv` (576) from the
August-17 round are still present locally. Gate 6 is a classification pass over existing data, not a
re-extraction.

---

## 19. External design cross-checks

These references support the architecture but do not override project-specific locks:

1. **Black, Derman and Toy (1990), “A One-Factor Model of Interest Rates and Its Application to Treasury Bond Options.”** Supports the use of a one-factor short-rate lattice for bond-option valuation.
2. **QuantLib callable-bond source.** Uses a shared put/call schedule, a short-rate tree engine, OAS/clean-price calculations, and explicit accrued treatment at exercise dates—consistent with keeping schedules outside the core and preserving clean/dirty discipline.
3. **FINRA callable and sinking-fund explanations.** Distinguish issuer call rights, make-whole provisions, and sinking-fund redemptions; sinking requirements can be met through periodic retirement mechanisms, reinforcing the need not to conflate optional sinking exercise with deterministic amortisation.

The project’s own validated conventions, data sources, and locked decisions remain controlling.

---

## 20. Final self-review

This plan was re-checked against the workbook, current handoff, locked decisions, existing engines, missing-data registry, and Mario’s recent feedback.

### Corrections made during the post-execution self-review

1. Rebased the plan on the completed four-commit, 194-green repository rather than treating JSON/Excel as unfinished.
2. Reused the actual endpoint files and removed any implication that a second contract/CLI/bridge should be created.
3. Incorporated the two live operations:
   - `price_at_oas` for fixed-OAS price experiments;
   - `calibrate_and_risk` for fixed-market-price implied-OAS experiments.
4. Preserved the methodology lock by limiting externally supplied OAS to the explicitly named `price_at_oas` operation.
5. Extended the strict ISO-date rule to all future exercise schedules and kept Excel serial conversion exclusively in VBA.
6. Added a per-100 guard so the existing echo-only `face_value` cannot accidentally scale tree cash flows, exercise prices, or risk.
7. Reused the live `resolve_curve` seam and the distinction between missing/unsupported curves and `CURVE_BUILD_FAILED`.
8. Preserved the current safe-leniency policy and exact endpoint-versus-direct equality tests.
9. Made endpoint dispatch a late, thin, reviewable attachment rather than a prerequisite for migrating the engines.
10. Prevented duplicate JSON/Excel documentation and a second Excel UI from entering scope.

### Corrections made during self-review

1. Corrected the remembered range from `Q61:Q70` to **`Q62:Q71`**, with `Q61` identified as the header.
2. Reframed the ten entries as analysis labels and derived the correct four product families.
3. Rejected a four-engine design in favor of one shared tree plus one shared FRN core.
4. Kept the validated current FRN method instead of copying the legacy FRN tree merely for apparent parity.
5. Separated optional sinking-fund redemption from deterministic pass-through/amortising cash flows.
6. Prevented `Sinking=Yes`, `NORMAL`, and `CONV/PUT/CALL` from being blindly routed.
7. Recognized that the relevant Monthly caches are predominantly the invalid 2010 session and removed exact legacy-cache parity as a completion requirement.
8. Used current Python production parity and invariants as the primary validation basis.
9. Added both volatility questions Mario actually asked: price at fixed OAS and implied OAS at fixed market price.
10. Kept MBS, hybrid migration, pass-through schedules, and Excel UI expansion out of scope so the round remains credible for this week.
11. Preserved the current repo as the baseline and made file placement adaptable to the live tree.
12. Ensured the current JSON/Excel work can attach later without requiring a second pricing implementation.

### Final judgment

This is the appropriate next round after the current vanilla JSON/Excel work:

- it follows the Monthly sheet in the way Mario intended;
- it expands the approved code structure materially without broad repo churn;
- it reuses already validated engines rather than reopening methodology;
- it adds only one genuinely new capability—optional sinking-fund exercise—with tight boundaries;
- it produces a useful, honest Mario update within the week;
- it does not depend on MBS data or new counterparty responses.

No unresolved design issue should block Claude Code from beginning Gate 0 from the current clean 194-green HEAD. The only optional branch is how many of the new wrappers are attached to the already working endpoint after the engine migrations are proven stable.
