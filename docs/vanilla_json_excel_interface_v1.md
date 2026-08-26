# Vanilla JSON / Excel interface — v1 reference

**Date:** 2026-08-25 · **Status:** implemented, 194 automatic checks green ·
**Scope:** vanilla (option-free, fixed-coupon) corporate bonds

This is the technical reference for the interface between a spreadsheet — or any
other caller that cannot import Python — and the validated pricing engine. It is the
document a developer needs; the how-to for setting up a workbook is
`integrations/excel_vba/README.md`, and the decision record is
`docs/code_structure_followup_json_excel_2026-08-25.md`.

---

## 1. Shape of the thing

```
Excel cells (named ranges)
        |
        v
RysePricingBridge.bas          adapter only: reads cells, converts Excel dates to
        |                      ISO strings, serialises, runs a command, waits
        v
one request JSON  ---->  runner command  ---->  scripts/price_json.py
                                                        |
                                          pricer.endpoints.main
                                          analyze_vanilla_payload(payload)
                                                        |
                                          pricer.assets.corporate.vanilla
                                          (the approved per-metric functions)
                                                        |
                                          pricer.core.*  (cash flows, discounting,
                                                          sensitivities, spreads)
                                                        |
one response JSON <----  runner command  <--------------+
        |
        v
Excel cells
```

Two design choices that look opposed and are not:

* **inside Python** — many small single-purpose functions, each with its inputs
  documented (Mario's structural directive, delivered in the August sample);
* **at the boundary** — one request in, one complete result out.

The endpoint is a thin arrangement layer over the same functions a Python caller
uses. It holds no formula of its own: no cash-flow generation, no accrued interest,
no discount factor, no root solving, no duration arithmetic, no curve bootstrap and
no FX. That is what makes the guarantee in §7 possible.

## 2. Operations

| operation | you send | you get back |
|---|---|---|
| `calibrate_and_risk` *(default)* | the CLEAN market price | the implied OAS + every risk number computed at it |
| `price_at_oas` | an OAS in basis points | the model price + every risk number at that spread |

`calibrate_and_risk` is the locked project methodology and the legacy sheet's own
flow: the market price is the input, the spread is the *output*. It therefore
**refuses** a hand-typed `analysis.oas_bp` — a market price and a chosen spread
cannot both be right, and silently preferring one would be the kind of ambiguity that
makes a number impossible to audit later. Callers who genuinely want a price at a
spread of their choosing say so by name, with `price_at_oas`.

## 3. Request

```json
{
  "schema_version": "1.0",
  "request_id": "DEMO-20260825-0001",
  "operation": "calibrate_and_risk",
  "bond": {
    "instrument_id": "DEMO-BOND-001",
    "currency": "USD",
    "coupon_pct": 6.5,
    "coupon_frequency": 2,
    "maturity_date": "2017-01-15",
    "face_value": 100.0,
    "day_count_label": "30/360"
  },
  "market": { "valuation_date": "2009-03-31", "clean_price_per_100": 94.25 },
  "analysis": { "spread_shift_bp": 10.0 },
  "model": { "yield_volatility_decimal": 0.15 },
  "metadata": { "source": "excel_demo" }
}
```

| field | required | units / form | notes |
|---|---|---|---|
| `bond.currency` | yes | ISO code | selects the OWN-currency curve; `USD EUR GBP JPY AUD KRW` configured |
| `bond.coupon_pct` | yes | **percent** (6.5 = 6.5%) | 0 = zero-coupon; >40 is refused as a probable decimal/bp mix-up |
| `bond.coupon_frequency` | yes | 1 / 2 / 4 / 12 | also selects the curve's compounding variant |
| `bond.maturity_date` | yes | ISO **string** | must be after the valuation date |
| `market.valuation_date` | yes | ISO **string** | the curve file must hold a row for exactly this date |
| `market.clean_price_per_100` | calibrate only | per 100 face | the calibration target |
| `analysis.oas_bp` | price_at_oas only | basis points | refused in `calibrate_and_risk` |
| `analysis.spread_shift_bp` | no (default 10) | basis points | the widening / tightening scenario size |
| `bond.instrument_id` | no | text | echoed back |
| `bond.face_value` | no | number | **echoed, not applied** — see §5 |
| `bond.day_count_label` | no | text | carried as data; reported as unused |
| `model.yield_volatility_decimal` | no | decimal (0.15 = 15%) | **not used by vanilla** — see §6 |
| `schema_version`, `request_id`, `metadata` | no | — | defaulted / generated / ignored |

## 4. Response

```json
{
  "schema_version": "1.0", "request_id": "...", "status": "ok",
  "engine": "corporate_vanilla", "operation": "calibrate_and_risk",
  "inputs_used": { "...": "what the engine actually ran on, after normalisation" },
  "market_data": { "pricing_currency": "USD", "valuation_date": "2009-03-31",
                   "curve_id": "USD|2009-03-31|Semiannual" },
  "results": { "...": "see the table" },
  "applicability": { "yield_volatility": {...}, "day_count": {...} },
  "warnings": [], "errors": []
}
```

| result | units | meaning |
|---|---|---|
| `model_clean_price_per_100` | per 100 | model price excluding accrued (matches the input mark after calibration) |
| `model_dirty_price_per_100` | per 100 | full present value of the remaining cash flows |
| `accrued_interest_per_100` | per 100 | the one shared accrued formula (ACT/364, 182-day grid) |
| `implied_oas_bp` | bp | the spread every other number was computed at |
| `oas_source` | text | `calibrated_from_clean_price` or `supplied_by_caller` |
| `effective_duration_years` | years | ±1bp parallel shift, dirty-price base |
| `dv01_per_100` | price per 100 | price change per +1 bp; a position's DV01 is this × par / 100 |
| `convexity` | years² | same bump |
| `price_spread_tighter_per_100` / `price_spread_wider_per_100` | per 100 | price after ∓ / ± the spread shift |
| `calibration_residual_per_100` | per 100 | model price − input mark (≈1e-9); `null` in `price_at_oas` |

`inputs_used` is the audit block: it shows the normalised values (uppercased
currency, ISO dates, applied defaults) so a wrong cell mapping in a spreadsheet is
visible immediately, without anyone reading Python. `curve_id` records which curve
produced the numbers. A number that could not be produced finitely is `null` with a
warning — never a placeholder digit.

## 5. Units, defaults, and the face-value rule

Legacy units at the boundary, exactly as the Monthly sheet uses them: **coupon in
percent, prices per 100 face, spreads in basis points.** Decimals live inside the
core engines; the asset wrappers convert.

Defaults: `schema_version` → `"1.0"`, `request_id` → generated, `operation` →
`calibrate_and_risk`, `spread_shift_bp` → `10.0`, `metadata` → `{}`.

**`face_value` is accepted, echoed and not applied.** Every field name in this
contract says "per 100", so a caller who sends both `face_value: 1000` and
`clean_price_per_100: 94.25` would otherwise be calibrating a per-1000 model price to
a per-100 mark — a silent mispricing. Scale a position by par / 100 on your own side;
the response carries a `FACE_VALUE_NOT_APPLIED` warning whenever the field arrives
with anything other than 100.

## 6. Volatility (and day count): stated, not swallowed

Vanilla pricing is an option-free discounted-cash-flow calculation. It has **no
volatility parameter at all** — not a zero one, none. A generic input form may still
carry one, so the interface neither fails the request nor discards the field quietly:

```json
"yield_volatility": {
  "input_value_decimal": 0.15,
  "used": false,
  "price_effect_per_1pct_vol": null,
  "oas_effect_bp_per_1pct_vol": null,
  "reason": "Option-free vanilla DCF has no direct yield-volatility parameter; volatility drives the callable/option engines only."
}
```

The sensitivities are `null`, never `0.0`: a zero would be read as a *calculated*
vega, which is a different and false statement. When volatility is omitted the block
still appears, with `input_value_decimal: null` and the same explanation.

`day_count` gets the same treatment — value echoed, `used: false`, and the convention
actually used (`ACT/364 with a 182-day coupon grid`) stated back. Both fields answer,
in the response itself, the question they would otherwise raise in a meeting.

When the callable engine joins this interface it will consume the **same** field, and
report, per volatility scenario, both the price at a fixed baseline OAS and the OAS
re-implied at a fixed market price. Vanilla keeps returning nulls.

## 7. The parity guarantee

For any successful request, each result equals the value obtained by calling the
approved vanilla function directly with the same inputs — not "to within a tolerance"
but as the identical float. `tests/test_vanilla_json_endpoint.py` asserts exactly
that, with `==`, for the price, the implied OAS, the duration, the DV01, the
convexity and both scenario prices. There is no endpoint-specific rounding anywhere,
and the interface can therefore never become a second, drifting implementation.

## 8. Errors

Every failure is a value, not an exception: same envelope, `status: "error"`,
`results: null`, one entry in `errors` with a code, the field at fault and a sentence
a spreadsheet user can act on.

| code | when |
|---|---|
| `INVALID_JSON` | the request file could not be parsed |
| `VALIDATION_ERROR` | a missing/ill-formed input, a numeric date, maturity ≤ valuation, an OAS supplied to the calibrating operation |
| `UNSUPPORTED_OPERATION` | an unknown operation, or a batch `{"requests": [...]}` payload |
| `CURVE_NOT_FOUND` | the currency has no configured curve, or that curve has no row for the date |
| `CURVE_BUILD_FAILED` | the curve exists but cannot be bootstrapped (a par node that is not arbitrage-free) |
| `CALIBRATION_FAILED` | no spread reprices the bond to the given mark |
| `PRICING_FAILED` | the priced cash flows could not be produced |
| `INTERNAL_ERROR` | anything unforeseen — reported by type only |

Two rules hold for every message: **no file path, no traceback, no echo of the
payload.** (The underlying curve loader does name its data file in its own error; the
endpoint catches that and re-words it with currency and date only.) The three curve
failures are genuinely different situations and are reported as such:

```
CHF 2009-03-31   no curve file configured for that currency   -> CURVE_NOT_FOUND
KRW 2009-03-31   file exists, that date is not in it          -> CURVE_NOT_FOUND
GBP 2009-03-31   file and date exist, par curve not arb-free  -> CURVE_BUILD_FAILED
```

There is **no silent USD fallback**. A bond whose currency we cannot price is
refused, because a EUR bond quietly discounted on a USD curve is a wrong number that
looks like a right one.

### The one deliberately unforgiving rule

Date fields must be ISO **strings**. A date sent as a number is refused:

```json
{ "code": "VALIDATION_ERROR", "field": "market.valuation_date",
  "message": "'market.valuation_date' must be a date STRING (YYYY-MM-DD), not the number 39903. An Excel date serial would be read as 1970-01-01 and price the bond on the wrong date — convert it with Format(cell, \"yyyy-mm-dd\") before sending." }
```

Excel stores 2009-03-31 as the number 39903; the Python date parser reads a bare
39903 as *nanoseconds since the epoch*, i.e. 1970-01-01. The bond would be priced on
the wrong date, on the wrong curve, and nothing would look broken. Converting the
serial is the bridge's job, and this rule makes skipping it impossible.

### What is forgiven

Lower-case currency, blanks around text, numbers sent as text, a missing request id /
schema version / operation, unknown fields (ignored with an `UNUSED_FIELD` warning —
they never change a calculation), a face value other than 100, and volatility on a
vanilla request. Caller-specific information belongs under `metadata`.

## 9. Command-line use

```bash
PYTHONPATH=src python3 scripts/price_json.py \
    --input  integrations/excel_vba/examples/vanilla_request_v1.json \
    --output response.json
```

Options: `--input`, `--output`, and `--data-dir` (else `$FIP_DATA_DIR`, else `data/`).
The response is written atomically (temp file, then replace). Exit codes: `0` ok,
`1` the request was refused — *a readable error response was still written* — `2` the
files themselves could not be read or written. Only a one-line status goes to stdout:

```
ok request_id=DEMO-20260825-0001
error code=CURVE_NOT_FOUND request_id=DEMO-20260825-0002
```

## 10. Worked example

Request: the committed `examples/vanilla_request_v1.json` — a 6.5% USD bond maturing
2017-01-15, marked at 94.25 clean on 2009-03-31, with a volatility of 0.15 supplied
by the form and a 30/360 day-count label.

Response (`examples/vanilla_response_v1.json`, real output):

```
curve_id                       USD|2009-03-31|Semiannual
model_clean_price_per_100      94.24999999411493      (= the mark, by construction)
model_dirty_price_per_100      95.41071427982922
accrued_interest_per_100        1.1607142857142858
implied_oas_bp                523.2980448854493
effective_duration_years        6.090692137822485
dv01_per_100                    0.058111728732818335
convexity                      43.43704394133383
price_spread_tighter_per_100   94.83319457648531      (spread -10 bp)
price_spread_wider_per_100     93.6709497905553       (spread +10 bp)
calibration_residual_per_100   -5.88507020893303e-09
applicability.yield_volatility used = false, effects = null
applicability.day_count        "30/360" received, used = false, ACT/364 applied
```

Note the residual's scientific notation: ordinary output here, and one of the reasons
the VBA JSON parser is a vendored, widely-used library rather than something written
for this project and never executed.

## 11. Excel named ranges

`FIP_Currency`, `FIP_CouponPct`, `FIP_CouponFrequency`, `FIP_MaturityDate`,
`FIP_ValuationDate`, `FIP_CleanMarketPrice` (required); `FIP_InstrumentId`,
`FIP_SpreadShiftBp`, `FIP_YieldVolatility`, `FIP_RunnerCommand` (optional). Outputs:
`FIP_Status`, `FIP_ModelCleanPrice`, `FIP_ModelDirtyPrice`, `FIP_AccruedInterest`,
`FIP_ImpliedOASBp`, `FIP_EffectiveDuration`, `FIP_DV01`, `FIP_Convexity`,
`FIP_TighterPrice`, `FIP_WiderPrice`, `FIP_CurveId`, `FIP_VolatilityApplicability`,
`FIP_Warnings`, `FIP_Errors`. Full setup: `integrations/excel_vba/README.md`.

## 12. The seam that keeps this portable

The workbook knows one thing about the engine: a command that takes `--input` and
`--output`. That single setting can point at

```
a local Python environment      (today)
a packaged executable           (no Python install on the desk)
an HTTP client wrapper          (the cloud service)
```

without changing a field name, a cell, or a line of VBA. When the service exists it
must call **this same** `analyze_vanilla_payload` — the transport may multiply, the
pricing implementation may not.

Known limits of v1, stated rather than hidden: one bond per request (batch is
refused, not half-supported); vanilla only (the floating, hybrid, callable,
agency, index-linked and MBS engines exist in the repo but are not exposed here yet);
each request rebuilds its curve, which is irrelevant at one bond and is the first
thing to cache when batch arrives; and one link of the Excel path is still stood in
for — `integrations/excel_vba/tests/Run-BridgeTests.ps1` drives the real VBA in a
hidden Excel instance (23 checks: cells → JSON → a waited-for command → cells, plus
the error path), but the runner it calls is a `.cmd` returning the committed fixture,
because the Windows machine here has no Python. Excel invoking a *live* Python runner
is the one step not yet exercised.

## 13. Where the code is

```
src/pricer/endpoints/main.py          analyze_vanilla_payload — the entry point
src/pricer/endpoints/contracts.py     normalisation, validation, envelopes
src/pricer/endpoints/pricing.py       the seven-step orchestration
src/pricer/endpoints/dependencies.py  the only environment-aware file
src/pricer/core/market/curves.py      resolve_curve / curve_id / CurveUnavailable
src/pricer/assets/corporate/          the approved vanilla functions + input catalogue
scripts/price_json.py                 request file -> response file
integrations/excel_vba/               the bridge, the parser, the fixtures
tests/test_vanilla_json_endpoint.py   28 interface checks (parity, firm, lenient, CLI)
integrations/excel_vba/tests/         23 VBA checks, driven through a hidden Excel

```
