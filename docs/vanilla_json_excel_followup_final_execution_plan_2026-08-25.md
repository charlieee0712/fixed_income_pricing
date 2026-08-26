# Final Execution Plan — Vanilla Code-Structure Follow-up: Currency, Volatility, and the JSON/Excel Bridge

**Date:** 2026-08-25  
**Project:** RYSE Fixed-Income Pricing  
**Execution owner:** Claude Code on the private live repository / server 47  
**Status:** Mario approved the first vanilla code-structure sample. The sample-first gate is open.  
**Design stance:** attach the new work to the approved repository, make the smallest useful structural change, and keep the first JSON/Excel version deliberately simple. Be flexible about file placement and interface conveniences; remain strict only where pricing correctness, data lineage, or a locked project convention requires it.

---

## 0. Executive decision

Do **not** redesign or broadly reorganize the current repository. Treat the live repository as the source of truth and add a thin interface seam around the already approved vanilla chain.

The target flow is:

```text
Excel cells or an Excel Table
        ↓
small VBA bridge
        ↓
one request JSON
        ↓
small Python endpoint / CLI wrapper
        ↓
existing pricer.assets.corporate.vanilla functions
        ↓
existing core pricing, calibration, and risk functions
        ↓
one response JSON
        ↓
small VBA bridge
        ↓
Excel output cells
```

The internal Python design remains “many small functions.” The external integration design is “one request in, one complete result out.” These are complementary, not competing, choices.

### Required outcomes of this round

1. Add `currency` clearly to the vanilla external-input story and use it to select the existing own-currency curve.
2. Make the role of yield volatility explicit:
   - vanilla DCF does not directly use it;
   - if Excel sends it, the request should still run, but the response must state clearly that it was not used and that vanilla price/OAS volatility sensitivities are not applicable;
   - callable and other option-aware engines will use it in their later migration rounds.
3. Provide a working Python “one JSON in, one JSON out” path for a single vanilla bond.
4. Provide a thin Excel/VBA integration package that can later point either to a local Python runner, a packaged executable, or an HTTP service without changing the JSON field meanings.
5. Preserve all existing calculations, conventions, outputs, shims, and tests.

### What this round is not

This is not the floating, hybrid, callable, agency, ILB, MBS, EIR, or CreditMetrics migration. It is not a FastAPI/cloud deployment. It is not a rewrite of `dataio`, `curves`, or the current driver layer. It is not a reason to add abstract base classes, factories, empty future modules, or a second vanilla adapter.

---

## 1. Current baseline to preserve

The approved vanilla sample already has the intended core/assets decomposition:

```text
src/pricer/
├── core/
│   ├── pricing/
│   │   ├── cashflows.py
│   │   ├── discounting.py
│   │   └── analytical.py
│   ├── risk/
│   │   └── sensitivities.py
│   ├── market/
│   │   ├── spreads.py
│   │   └── curves.py
│   └── utils/
│       └── dates.py
└── assets/
    └── corporate/
        ├── bonds_input.py
        └── vanilla.py
```

The legacy-facing modules under `src/pricing/` remain compatibility shims. Existing scripts and tests continue to use their current imports until each later migration is deliberately completed.

The current handoff baseline is **166 green tests** after the vanilla Monthly reconciliation. Confirm the live count before editing; if later commits have legitimately added tests, preserve that newer live baseline rather than forcing the number back to 166.

The following project rules remain in force:

- model PV is dirty;
- custodian `BT` is clean;
- the shared accrued-interest convention is retained;
- implied OAS is solved from clean market price and is an output of calibration;
- duration, DV01, and convexity use the existing locked definitions;
- currency selects the own-currency pricing curve and is not an instruction to re-FX the base-USD portfolio values;
- the numerical core and floating-point operation order must not change;
- the full existing suite must remain green.

---

## 2. First action: live-repository alignment gate

Before changing code, inspect the live tree and record the actual baseline. The plan describes responsibilities; it does not authorize Claude Code to create a parallel hierarchy merely because a diagram contains a particular filename.

Suggested inventory commands:

```bash
find src/pricer -maxdepth 5 -type f | sort
find src/pricing src/dataio src/curves scripts tests docs \
  -maxdepth 3 -type f | sort
.venv/bin/python -m pytest -q
```

Record:

- current commit;
- current test count and result (expected handoff baseline: 166 green, subject to legitimate live-repo additions);
- current `src/pricer/` tree;
- current curve-loading entry point used by the vanilla drivers;
- whether an `endpoints/` folder already exists;
- current naming and test conventions.

### Repo-alignment rule

> **Live repo wins. Reuse existing names and files whenever they already carry the needed responsibility. Add the minimum missing seam; do not move approved modules just to match this plan literally.**

Any structural deviation from the preferred delta below is acceptable when it reduces duplication and preserves the current repository’s conventions. Record the final chosen locations in the new integration document.

---

## 3. Preferred minimal repository delta

### 3.1 Code

If no endpoint layer exists, the preferred small addition is:

```text
src/pricer/
└── endpoints/
    ├── __init__.py
    ├── main.py                 # public Python entry: payload dict in, response dict out
    ├── pricing.py              # vanilla orchestration only
    └── dependencies.py         # curve/config lookup only, if a separate file is useful

scripts/
└── price_json.py               # request-file in, response-file out
```

**Live-repo check (2026-08-25): neither `endpoints/` nor `integrations/` exists, so this preferred
layout is ADOPTED as written** - flat, not the template's `endpoints/routes/pricing.py`. A single
non-HTTP entry point does not earn a folder, and Mario's original complaint was nesting; `routes/`
arrives with the HTTP service, if it ever does.

Two placement decisions follow from the live tree:

- the reusable `resolve_curve(currency, valuation_date, coupon_frequency)` seam belongs in
  `core/market/curves.py`, beside the existing `flat_zero_curve`, **not** in
  `endpoints/dependencies.py` - every later engine (callable, floating, MBS) needs the same routing,
  and the endpoint layer must stay disposable. `dependencies.py` keeps only the "where does the data
  live" concern (`FIP_DATA_DIR`), which is exactly the file a cloud deployment swaps.
- `scripts/calibrate_risk.py`, `callable_risk.py` and `phase2_risk.py` each carry their own local
  `FREQ_VARIANT` map today. They are on the §3.4 no-touch list and **keep** it this round; that
  duplication dies in the rollout step that migrates those drivers, not here.

If the live repo already has `endpoints/routes/pricing.py`, `contracts.py`, or equivalent files, use them. Do not create both `endpoints/pricing.py` and `endpoints/routes/pricing.py`. Do not add a file solely because it appeared in an earlier plan.

### 3.2 Excel integration

```text
integrations/
└── excel_vba/
    ├── README.md
    ├── RysePricingBridge.bas
    ├── JsonConverter.bas       # only if the repo has no approved JSON module
    ├── LICENSE_JSON_PARSER.txt # only when a third-party parser is vendored
    └── examples/
        ├── vanilla_request_v1.json
        ├── vanilla_response_v1.json
        └── vanilla_error_v1.json
```

A demonstration `.xlsm` may be created later, but it is not required to complete the Python endpoint. Do not modify the authoritative URS holdings workbook.

### 3.3 Tests

Prefer one focused test module first:

```text
tests/
└── test_vanilla_json_endpoint.py
```

Split it only if it becomes genuinely hard to read. Do not create five small test files merely to mirror five conceptual headings.

### 3.4 Files that should not be moved in this round

Do not relocate or redesign:

```text
src/dataio/
src/curves/
src/pricing/                 # existing shims and not-yet-migrated engines
src/recon/
scripts/calibrate_risk.py
scripts/callable_risk.py
scripts/phase2_risk.py
```

Do not add placeholder `BaseEngine`, `BaseAsset`, `AssetFactory`, `tree.py`, `volatility.py`, `routes/curves.py`, or future-asset folders unless current code in this round actually needs them.

---

## 4. Small changes to the approved vanilla surface

### 4.1 `bonds_input.py`

Update the existing catalogue rather than replacing it.

Required changes:

1. Add `currency` as an external routing input.
2. Explain that JSON/Excel callers provide currency, valuation date, and coupon frequency; Python resolves the existing curve object before calling the vanilla functions.
3. Keep `curve` documented as the direct-Python/internal input used by the existing functions.
4. Keep `day_count` as carried data and document that the current validated ACT/364 convention remains in force.
5. Keep volatility visible in the all-purpose catalogue, but mark it explicitly:

```text
used by vanilla: no
used by callable/option engines: yes
vanilla behavior if supplied externally: accepted, echoed, not used, explanatory warning returned
```

6. Keep OAS described carefully:
   - in the `calibrate_and_risk` operation, clean market price is the input;
   - implied OAS is the calibration result;
   - downstream price/risk functions may receive that already-calibrated OAS internally.

Do not split the catalogue into many files or classes unless the current file has already become difficult to read. A few clear sections or constants inside `bonds_input.py` are sufficient.

### 4.2 `assets/corporate/vanilla.py`

Preserve all existing public functions and calculations.

The endpoint should call the existing functions for:

```text
calculated_price
implied_oas
duration
dv01
convexity
widening
tightening
```

Do not add JSON parsing, file I/O, Excel knowledge, path handling, or subprocess logic to this module.

### 4.3 Curve resolution

Use the current validated curve-loading path. Add only a small wrapper if the live code lacks a single reusable call such as:

```python
resolve_curve(currency, valuation_date, coupon_frequency)
```

The wrapper should:

- normalize currency to uppercase;
- select the existing own-currency curve and frequency variant;
- fail clearly if the requested curve is unavailable;
- return a simple `curve_id` for audit, such as `USD|2009-03-31|Semiannual`;
- avoid all FX conversion and portfolio market-value logic;
- avoid duplicating bootstrap code.

A cryptographic curve hash is optional and should not block this round.

---

## 5. Flexible JSON contract v1

The contract should be simple enough for VBA to create and for a Google/cloud wrapper to reuse. It should be forgiving about harmless presentation details, while remaining firm about fields that determine the economics.

### 5.1 Canonical request

```json
{
  "schema_version": "1.0",
  "request_id": "DEMO-20260825-0001",
  "operation": "calibrate_and_risk",
  "bond": {
    "instrument_id": "DEMO-BOND-001",
    "currency": "usd",
    "coupon_pct": 6.5,
    "coupon_frequency": 2,
    "maturity_date": "2017-01-15",
    "face_value": 100.0,
    "day_count_label": "30/360"
  },
  "market": {
    "valuation_date": "2009-03-31",
    "clean_price_per_100": 94.25
  },
  "analysis": {
    "spread_shift_bp": 10.0
  },
  "model": {
    "yield_volatility_decimal": 0.15
  },
  "metadata": {
    "source": "excel_demo"
  }
}
```

### 5.2 Operations and required fields

v1 supports **two** named operations. They return the same result block and differ only in where
the spread comes from:

```text
calibrate_and_risk   clean market price IN -> implied OAS OUT   (the locked methodology, and the
                                              legacy sheet's own bondcalc flow: col B price -> OAS)
price_at_oas         OAS in bp IN          -> model price OUT   (the legacy per-metric functions'
                                              flow: CorpBondDuration / CorpBondwidening take a
                                              spread as an INPUT)
```

Adding `price_at_oas` now (rather than deferring it) costs ~15 lines and removes the only place
where the contract would reject a field an Excel user could reasonably send. The methodology lock
is unchanged: `calibrate_and_risk` still refuses a user-supplied OAS (§5.4).

The minimum economic request is:

```text
bond.currency
bond.coupon_pct
bond.coupon_frequency
bond.maturity_date
market.valuation_date
market.clean_price_per_100    (calibrate_and_risk only)
analysis.oas_bp               (price_at_oas only)
```

`instrument_id`, `face_value`, `day_count_label`, `spread_shift_bp`, volatility, request ID, and metadata are optional.

Defaults:

```text
schema_version        -> "1.0"
request_id            -> generate one when absent
operation             -> "calibrate_and_risk"
face_value            -> 100.0  (see 5.3 - prices are ALWAYS quoted per 100 face)
spread_shift_bp       -> 10.0
metadata              -> {}
```

### 5.3 Deliberately lenient behavior

The v1 adapter may normalize the following instead of failing:

- lowercase currency to uppercase;
- leading/trailing whitespace in strings;
- missing request ID by generating one;
- omitted schema version by assuming `1.0`;
- omitted operation by assuming `calibrate_and_risk`;
- harmless unknown fields by ignoring them and returning an `UNUSED_FIELD` warning;
- optional volatility on a vanilla request by echoing it and returning a clear non-applicability result;
- a `face_value` other than 100 by pricing per 100 anyway and returning a `FACE_VALUE_NOT_APPLIED`
  warning. Field names are the contract: every price, accrued figure and DV01 in this interface is
  **per 100 face**, and a position is scaled by par / 100 on the caller's side. Honouring `face_value`
  instead would make `clean_price_per_100` a lie whenever the caller also sent a per-100 market price
  - a silent mispricing - so the field is accepted, echoed, and not applied.

Unknown fields should never change a calculation. The integration guide should encourage optional client-specific information to be placed under `metadata`.

### 5.4 Fields that remain firm

Return a structured error for:

- missing currency;
- unsupported currency or unavailable curve/date;
- missing or invalid coupon/frequency/maturity/valuation date/clean price;
- maturity on or before valuation date;
- non-finite or non-positive clean price;
- **a date field sent as a NUMBER** (an Excel serial). `pd.Timestamp(39903)` silently parses as
  1970-01-01 (nanoseconds since the epoch), so a serial would price the bond on a wrong date with no
  error anywhere. Date fields must be ISO strings; converting Excel serials is the VBA bridge's job.
  This is the one place the contract is deliberately unforgiving, because the failure is silent and
  economic;
- unsupported operation - including a batch `{"requests": [...]}` payload, which must answer with a
  clear "batch is not supported in v1" message rather than a confusing validation error;
- a user-supplied absolute `oas_bp` in `calibrate_and_risk` mode.

The last rule protects the locked methodology: `calibrate_and_risk` calibrates OAS from the clean
market price. A caller who genuinely wants a price at a spread of their own choosing uses the
separately named `price_at_oas` operation (§5.2), where `oas_bp` is required and
`clean_price_per_100` is ignored.

### 5.5 Volatility behavior for vanilla

Do not fail the entire request merely because a generic Excel form supplies volatility. Do not silently use or silently discard it either.

For vanilla:

```text
yield volatility supplied?       yes or no
used in vanilla pricing?          no
price sensitivity to volatility?  not applicable / null
OAS sensitivity to volatility?    not applicable / null
reason                            option-free deterministic DCF has no volatility parameter
```

Use `null`, not numeric zero, for the unavailable sensitivities. A zero could be mistaken for a calculated vega.
When volatility is omitted, return `input_value_decimal: null` with the same applicability explanation.

### 5.6 No dependency-heavy contract framework in v1

Use the Python standard library and small explicit normalization/validation functions unless the live repo already has an established typed-model dependency.

Do not add Pydantic, FastAPI, or a JSON Schema validator solely for this first interface. A committed JSON Schema can be added after the examples and tests stabilize, or earlier if Claude Code finds it trivial and dependency-free. It is not a completion gate for this round.

---

## 6. Response contract v1

### 6.1 Success response

```json
{
  "schema_version": "1.0",
  "request_id": "DEMO-20260825-0001",
  "status": "ok",
  "engine": "corporate_vanilla",
  "operation": "calibrate_and_risk",
  "inputs_used": {
    "instrument_id": "DEMO-BOND-001",
    "currency": "USD",
    "coupon_pct": 6.5,
    "coupon_frequency": 2,
    "maturity_date": "2017-01-15",
    "valuation_date": "2009-03-31",
    "clean_price_per_100": 94.25,
    "spread_shift_bp": 10.0,
    "face_value_per_quote": 100.0
  },
  "market_data": {
    "pricing_currency": "USD",
    "valuation_date": "2009-03-31",
    "curve_id": "USD|2009-03-31|Semiannual"
  },
  "results": {
    "model_clean_price_per_100": 94.25,
    "model_dirty_price_per_100": 95.10,
    "accrued_interest_per_100": 0.85,
    "implied_oas_bp": 412.34,
    "effective_duration_years": 6.12,
    "dv01_per_100": 0.0578,
    "convexity": 48.21,
    "price_spread_tighter_per_100": 94.83,
    "price_spread_wider_per_100": 93.68,
    "calibration_residual_per_100": 0.0
  },
  "applicability": {
    "yield_volatility": {
      "input_value_decimal": 0.15,
      "used": false,
      "price_effect_per_1pct_vol": null,
      "oas_effect_bp_per_1pct_vol": null,
      "reason": "Option-free vanilla DCF has no direct yield-volatility parameter."
    },
    "day_count": {
      "input_value_label": "30/360",
      "used": false,
      "convention_used": "ACT/364 with a 182-day coupon grid",
      "reason": "The validated legacy engine carries the day-count label as data only; its own input dictionary says '30/360, but is not used'."
    }
  },
  "warnings": [],
  "errors": []
}
```

The numbers in this example are illustrative. Committed examples must be generated from real direct-function outputs.

Three response conventions worth stating explicitly:

- `inputs_used` echoes exactly what the engine ran on, after normalisation (uppercased currency, ISO
  dates, defaulted shift). An Excel user can audit a run without reading any Python, and a
  wrong-cell mapping in the bridge shows up immediately.
- `day_count` gets the same applicability treatment as volatility. Both are fields a generic form
  will send and the vanilla engine does not use, and both would otherwise produce the same meeting
  question ("we sent 30/360 - did it use it?").
- A non-finite result is serialised as `null` with a warning, never as a number.

### 6.2 Error response

```json
{
  "schema_version": "1.0",
  "request_id": "DEMO-20260825-0001",
  "status": "error",
  "engine": "corporate_vanilla",
  "results": null,
  "warnings": [],
  "errors": [
    {
      "code": "CURVE_NOT_FOUND",
      "field": "bond.currency",
      "message": "No supported curve was found for the requested currency and valuation date."
    }
  ]
}
```

Keep the error vocabulary small initially:

```text
INVALID_JSON
VALIDATION_ERROR
UNSUPPORTED_OPERATION
CURVE_NOT_FOUND
CURVE_BUILD_FAILED
CALIBRATION_FAILED
PRICING_FAILED
INTERNAL_ERROR
```

More granular codes may be added later if a real consumer needs them.

Do not expose Python tracebacks, environment paths, secrets, or a full client payload in the response.

This is a concrete requirement, not a precaution: the live `curves.bootstrap.load_par_curve` raises
`"Valuation date ... not found in data/KRW_Yield_Curve.txt"`, i.e. its message embeds a data path.
The endpoint must catch curve errors and re-word them with currency and date only.

The three curve failure modes are distinct and all three are live in this repo (verified 2026-08-25
on server 47):

```text
CHF 2009-03-31   no par-curve file mapped for the currency        -> CURVE_NOT_FOUND
KRW 2009-03-31   file exists, that valuation date is not in it    -> CURVE_NOT_FOUND
GBP 2009-03-31   file and date exist, bootstrap refuses: negative -> CURVE_BUILD_FAILED
                 discount factor at t=3.0, curve not arb-free
```

`CURVE_BUILD_FAILED` is the one code added to the plan's starting vocabulary. It earns its place
because the GBP case is real (two GBP corporates are curve-blocked in production) and reporting it
as "curve not found" would send an Excel user hunting for a missing file that is present.

---

## 7. Python endpoint responsibilities

Expose one transport-independent function, with the exact file location adapted to the live repo:

```python
analyze_vanilla_payload(payload: Mapping[str, object]) -> dict[str, object]
```

Its steps are:

1. copy and normalize the input payload;
2. apply the small v1 validation rules;
3. resolve the existing curve from currency, valuation date, and frequency;
4. convert external legacy units to the existing internal units exactly once;
5. call the existing implied-OAS function once;
6. reuse that calibrated OAS for price, duration, DV01, convexity, widening, and tightening;
7. package the response, applicability information, warnings, and errors.

The endpoint must not implement:

- coupon schedules;
- cash-flow generation;
- accrued interest;
- discount factors;
- root solving;
- duration/DV01/convexity formulas;
- curve bootstrap;
- FX conversion.

Those remain in the existing validated modules.

### Direct parity requirement

For every successful JSON fixture, the endpoint result before serialization must equal the result obtained by calling the approved vanilla functions directly with the same normalized inputs. Do not add endpoint-specific rounding.

---

## 8. File-based CLI

Add a small script following the repository’s current execution style:

```bash
PYTHONPATH=src python3 scripts/price_json.py \
  --input request.json \
  --output response.json
```

The script should:

1. read one JSON object;
2. call the transport-independent endpoint;
3. write one response JSON object;
4. return exit code `0` for `status="ok"` and nonzero for `status="error"`;
5. print only a short status line to stdout.

Recommended, but not blocking, implementation details:

- UTF-8 files;
- standard JSON only;
- `allow_nan=False` when writing;
- temporary-file then replace for the response;
- a clearer exit split such as validation vs pricing errors if useful;
- a short timeout in the eventual Excel runner.

Do not make detailed exit-code taxonomy, duplicate-key detection, request hashing, or schema generation a prerequisite for the first working interface.

---

## 9. Excel/VBA bridge

### 9.1 Boundary

VBA is an adapter only. It may:

- read cells or an Excel Table;
- convert Excel dates to ISO dates;
- build the request object;
- serialize it to JSON;
- invoke a configured runner;
- wait for completion;
- parse the response JSON;
- write values and messages back to Excel.

VBA must not implement pricing, curve selection rules, OAS calibration, duration, or volatility logic.

### 9.2 Suggested workbook interface

Use workbook-level named ranges or a small input/output Table. Named ranges are preferred for the first demonstration because they are readable and avoid hard-coded A1 addresses.

Suggested inputs:

```text
FIP_InstrumentId
FIP_Currency
FIP_CouponPct
FIP_CouponFrequency
FIP_MaturityDate
FIP_ValuationDate
FIP_CleanMarketPrice
FIP_SpreadShiftBp
FIP_YieldVolatility
```

Suggested outputs:

```text
FIP_Status
FIP_ModelCleanPrice
FIP_ModelDirtyPrice
FIP_AccruedInterest
FIP_ImpliedOASBp
FIP_EffectiveDuration
FIP_DV01
FIP_Convexity
FIP_TighterPrice
FIP_WiderPrice
FIP_VolatilityApplicability
FIP_Warnings
FIP_Errors
```

### 9.3 VBA procedures

Keep the module small and readable. Suggested procedures:

```text
BuildVanillaRequest
WriteRequestJson
RunPricingCommand
ReadResponseJson
PopulateVanillaOutputs
PriceVanillaBond
```

`PriceVanillaBond` calls the smaller procedures in order.

### 9.4 Runner configuration

Do not hard-code:

- server 47;
- SSH commands;
- the user’s personal Python path;
- a specific virtual-environment location;
- client data paths.

Read one configured command from a workbook setting, environment variable, or small local configuration file, for example:

```text
FIP_RUNNER_COMMAND=C:\RYSE\bin\ryse-fip.cmd
```

The command may later point to:

```text
local Python environment
packaged executable
HTTP client wrapper
```

The workbook should not need field changes when the transport changes.

### 9.5 Process waiting

Do not use ordinary asynchronous VBA `Shell` followed immediately by a response-file read. Use a wait-capable invocation such as `WScript.Shell.Run(..., waitOnReturn=True)` or an equivalent approved Windows process wrapper.

### 9.6 JSON parser

Reuse an existing approved VBA JSON parser if one already exists in the organization or repo. Otherwise vendor one small parser with its license and version recorded. Avoid handwritten JSON string concatenation and ad hoc parsing.

**Decision (2026-08-25): vendor `VBA-JSON` (Tim Hall, MIT) as `JsonConverter.bas`**, recording its
version, source URL and licence in `LICENSE_JSON_PARSER.txt`. The deciding fact is that this
development environment has **no VBA runtime at all** - server 47 has no Excel, and the Windows box
runs the workbook by hand - so a hand-written parser would reach a live demo having never executed
once, and it is exactly the string-escape / locale / scientific-notation cases (a calibration
residual of `1.42e-14` is ordinary output here) that a parser gets wrong. If the file cannot be
obtained, the fallback is a minimal in-house parser that the README labels UNTESTED in as many words.

### 9.7 Current-environment limitation

The current development workflow runs Python on server 47 and the local Windows machine may not have a usable Python environment. Therefore:

- the Python JSON endpoint must be fully tested on 47;
- the VBA module must be tested for request creation and response mapping using committed fixtures;
- a true click-to-Python Excel smoke test is performed when a suitable Windows runner or packaged executable is available;
- absence of that local runtime does not block completion of the interface design and Python endpoint.

A developer-only SSH experiment may be used privately if convenient, but SSH-to-47 must not become the product interface or be hard-coded into the workbook.

---

## 10. Documents and examples Claude Code should add

Keep the documentation set small. Add only the following new documents unless equivalent files already exist.

### 10.1 Decision and architecture addendum

```text
docs/code_structure_followup_json_excel_2026-08-25.md
```

Contents:

- Mario’s approval of the vanilla sample;
- his three follow-up comments;
- the adopted interpretation of volatility, currency, and one-JSON-in/one-JSON-out;
- the final live-repo file placement;
- what was implemented in this round;
- what remains for callable and cloud phases.

Do not rewrite the already approved 2026-08-15 sample report as though it had never existed. Treat this as an addendum and decision record.

### 10.2 JSON/Excel interface reference

```text
docs/vanilla_json_excel_interface_v1.md
```

This is the main technical handoff document. It should contain:

- the architecture diagram;
- request and response field tables;
- units and defaults;
- currency behavior;
- volatility applicability behavior;
- Excel named-range mapping;
- CLI usage;
- error behavior;
- one worked example;
- the future local-runner / packaged-executable / HTTP seam.

### 10.3 Excel integration guide

```text
integrations/excel_vba/README.md
```

Contents:

- how to import the VBA modules;
- required named ranges;
- how to configure the runner command;
- how request/response temporary files are handled;
- how to test with the committed fixtures;
- known Windows-only limitations of the first adapter;
- a clear statement that the authoritative URS workbook is not modified.

### 10.4 Committed examples

```text
integrations/excel_vba/examples/vanilla_request_v1.json
integrations/excel_vba/examples/vanilla_response_v1.json
integrations/excel_vba/examples/vanilla_error_v1.json
```

Generate the success example from an actual passing endpoint call. Do not hand-type result numbers that could drift from the code.

### 10.5 Existing documents to update

Update after the code and tests are complete:

```text
WORKLOG.md
PROJECT_STATUS.md
CLAUDE.md
```

Record:

- Mario approval;
- the endpoint and Excel-bridge status;
- the selected final paths;
- the new test count;
- any limitation of the current Windows runtime;
- next migration order.

Do **not** refresh `docs/handoff_for_claude_web/` unless the user separately asks for an updated handoff bundle.

### 10.6 Optional later document

A generated JSON Schema is optional after the contract settles:

```text
schemas/vanilla_request_v1.schema.json
schemas/vanilla_response_v1.schema.json
```

Do not block the first working Excel/Python bridge on these files.

---

## 11. Test plan

### Gate 0 — baseline

- record the live tree and commit;
- run the full current suite;
- confirm the current baseline is green;
- freeze one or two representative direct vanilla outputs for endpoint parity.

### Gate 1 — catalogue and currency

- add currency to the external-input catalogue;
- document volatility applicability;
- use the existing curve loader;
- confirm every existing test and output remains unchanged.

### Gate 2 — endpoint parity

Add focused tests covering:

1. valid USD request;
2. valid non-USD request using the own-currency curve;
3. lowercase currency normalized to uppercase;
4. missing currency returns a structured error;
5. unavailable currency/date returns a structured curve error;
6. volatility supplied to vanilla returns `used=false`, null effects, and an explanation;
7. omitted volatility runs normally;
8. user-supplied absolute OAS in calibration mode is rejected;
9. endpoint numerical results equal direct function results before JSON serialization;
10. one malformed JSON file returns an error response rather than a traceback;
11. `price_at_oas` returns the same result block from a supplied spread, and its price equals
    `calculated_price` called directly;
12. calibrate then price_at_oas round-trip: the calibrated OAS reprices to the input price;
13. a date field sent as an Excel serial NUMBER is rejected (the 1970-01-01 trap);
14. a `face_value` other than 100 still prices, per 100, with the documented warning;
15. the three curve failure modes map to their codes (CHF -> CURVE_NOT_FOUND, KRW 2009-03-31 ->
    CURVE_NOT_FOUND, GBP 2009-03-31 -> CURVE_BUILD_FAILED) and no message contains a file path;
16. a batch `{"requests": [...]}` payload returns the explicit "not supported in v1" error.

### Gate 3 — CLI

- request fixture in → response fixture out;
- successful run returns exit code 0;
- invalid request returns nonzero and still writes a readable error JSON;
- no client payload is printed to stdout;
- full suite remains green.

### Gate 4 — Excel bridge

At minimum, verify with fixtures that VBA:

- reads the named inputs;
- writes semantically correct JSON;
- normalizes Excel dates;
- waits for the configured command;
- reads the success response;
- maps all outputs correctly;
- displays an error response cleanly;
- shows the vanilla volatility explanation.

A real Excel → local Python click test is desirable when a Windows runner is available, but it is not allowed to force a redesign of the Python environment or hard-code server 47.

---

## 12. Acceptance criteria

The round is complete when:

- the approved `core/` and `assets/` structure remains intact;
- existing old import paths still work;
- all existing numerical outputs remain bit-identical;
- the entire old suite plus the new endpoint tests is green;
- currency is visible in the external input catalogue and demonstrably routes USD and non-USD requests to their own curves;
- one request JSON returns one response JSON containing all vanilla outputs;
- volatility can be supplied by a generic Excel form without breaking the vanilla run, but the response explicitly says it was not used and reports no synthetic zero vega;
- clean market price remains the calibration input and implied OAS remains the result;
- the JSON endpoint contains no pricing formulas;
- VBA contains no pricing formulas;
- the runner command is configurable and does not hard-code server 47 or a personal path;
- the authoritative URS workbook is untouched;
- the decision addendum, interface reference, Excel README, and real examples are committed;
- the future callable and HTTP seams are documented without being implemented prematurely.

---

## 13. Suggested commit sequence

Adapt commit boundaries to the live repo, but keep concerns separate enough to review.

```text
1. docs: adjust this plan with the execution decisions (this revision)
2. refactor: add currency/applicability notes to the existing vanilla input catalogue
3. feat: add the curve-resolution seam and the minimal vanilla JSON endpoint
4. feat: add the request-file/response-file CLI and focused parity tests
5. docs: add the v1 JSON/Excel interface reference and real example files
6. feat: add the thin Excel/VBA bridge package and fixture-based smoke checks
7. docs: record Mario's approval and his three follow-up comments (addendum)
8. docs: update WORKLOG, PROJECT_STATUS, and CLAUDE with the final paths and test count
```

Run the full test suite after every code-bearing commit. Do not combine this work with another engine migration.

---

## 14. Follow-on design, not part of this round

### 14.1 Callable volatility

When the callable tree is migrated into `pricer/`, reuse the same optional field:

```text
model.yield_volatility_decimal
```

For each volatility scenario, return both:

```text
price_at_fixed_baseline_oas
implied_oas_at_fixed_market_price
```

Then add calculated volatility sensitivities. Vanilla continues to return null/not-applicable values.

### 14.2 Batch requests

Keep the single-bond object canonical. A later batch request may simply wrap a list:

```json
{
  "schema_version": "1.0",
  "requests": [
    { "...single vanilla request...": "..." }
  ]
}
```

Do not design batch concurrency in this round.

### 14.3 Cloud / Google team

A future service can expose the same endpoint over HTTP:

```text
Excel/VBA or Office Script → HTTP POST request JSON
                           ← HTTP response JSON
```

The pricing route must continue to call the same Python endpoint and approved asset/core functions. Cloud transport should not create a second pricing implementation.

### 14.4 Stronger contract tooling

After the v1 examples are stable and there is a real second consumer, consider:

- JSON Schema;
- Pydantic or another typed-model framework;
- detailed error codes;
- request/curve hashes;
- packaged console entry points;
- signed Excel macros;
- authentication and HTTP deployment.

These are legitimate later improvements, not prerequisites for proving Mario’s proposed Excel/JSON/Python process.

---

## 15. Final self-review

This plan has been checked against the current project state and revised to remove unnecessary rigidity.

### Repository fit

- It preserves the approved `src/pricer/core` and `src/pricer/assets` structure.
- It treats the live repo as authoritative.
- It does not require parallel `contracts/`, `adapters/`, or unused future-engine hierarchies.
- It does not move mature `dataio`, curve, driver, or reconciliation code.

### Methodology fit

- Clean market price remains the calibration input.
- Implied OAS remains the output.
- Currency chooses the own-currency pricing curve only.
- Base-USD market-value logic remains separate.
- Existing clean/dirty, accrued, risk, and numerical conventions are unchanged.

### Volatility fit

- Mario’s question is answered directly rather than hidden in a footnote.
- Vanilla accepts a generic volatility field without failing the request.
- The response makes non-use explicit and returns null—not fake zero—sensitivities.
- The future callable contract preserves both fixed-OAS price effects and fixed-price recalibrated-OAS effects.

### JSON/Excel fit

- One request returns every relevant vanilla output.
- VBA remains a thin adapter.
- The same payload can later travel through a packaged executable or HTTP.
- The first version uses standard-library Python and does not impose a new dependency stack on server 47.
- Excel end-to-end execution is not falsely declared complete before a Windows runner exists.

### Strictness balance

The plan is deliberately lenient about:

- request IDs;
- schema-version defaults;
- lowercase currency;
- optional fields;
- generic metadata;
- unknown harmless fields;
- volatility supplied to a vanilla form;
- exact internal placement of the small endpoint files.

It remains strict about:

- required economic inputs;
- valid curve routing;
- OAS being calibrated rather than supplied in this operation;
- no pricing logic in VBA or the endpoint;
- no silent USD fallback;
- no silent use or silent disregard of volatility;
- no numerical drift;
- no modification of the authoritative portfolio workbook.

No unresolved architecture question should block execution. The only environment-dependent item is the final Excel-to-local-Python click test; the Python endpoint and fixture-tested VBA bridge can be completed independently and attached to the approved repository now.

---

## 16. Execution revision (2026-08-25, Claude Code)

Adjustments made to this plan before starting work, after the live-repository alignment gate (§2)
and one Fable-advisor consult. Baseline recorded: server 47 at commit `6b74e25`, **166 green in
20.4s**, clean tree; `src/pricer/` exactly as in §1; no `endpoints/` and no `integrations/`; the
vanilla drivers resolve curves through `ZeroCurve.from_currency(data_dir, ccy, date, freq=variant)`.

| # | Adjustment | Why |
|---|---|---|
| 1 | `price_at_oas` added as a second v1 operation (§5.2) | The legacy per-metric functions take a spread as an INPUT; rejecting `oas_bp` with no named alternative was the plan's one piece of unnecessary strictness. The methodology lock is unchanged. |
| 2 | `face_value` accepted, echoed, NOT applied; prices always per 100 (§5.3) | Field names are the contract. Honouring face while the caller sends a per-100 market price is a silent mispricing. |
| 3 | Date fields must be ISO STRINGS; a numeric date is a hard error (§5.4) | Verified: `pd.Timestamp(39903)` -> 1970-01-01. A silently wrong valuation date is the worst failure this interface could have. |
| 4 | `CURVE_BUILD_FAILED` added to the error vocabulary (§6.2) | Verified on 47: GBP 2009-03-31 fails as a non-arbitrage-free bootstrap, not as a missing curve. Three live failure modes, two codes. |
| 5 | Curve-error sanitisation made an explicit requirement (§6.2) | `load_par_curve`'s own message embeds `data/KRW_Yield_Curve.txt`. |
| 6 | `inputs_used` echo block + `day_count` applicability added to the response (§6.1) | Audit without reading Python; day count gets the same honest treatment as volatility, and both pre-empt the same meeting question. |
| 7 | Endpoint layout fixed as flat `endpoints/{main,pricing,dependencies}.py`; `resolve_curve` placed in `core/market/curves.py`; drivers untouched (§3.1) | Follows the plan's own preferred delta and keeps the reusable seam out of the disposable layer. |
| 8 | VBA JSON parser: vendor VBA-JSON (MIT) rather than hand-write (§9.6) | No VBA runtime exists here, so an in-house parser would ship untested into a live demo. |
| 9 | Commit order changed: code first, the Mario-approval addendum at step 7 (§13) | Mario's three comments are only available verbatim from the user, and no code work depends on their wording. |

Everything else in this plan is executed as written.
