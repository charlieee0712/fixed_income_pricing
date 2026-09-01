# The JSON / Excel interface, and the demonstration

Mario's third follow-up point, built and tested. The full field-by-field contract is the
verbatim file `37`; this is the shape, the decisions and the current limits.

---

## 1. The shape

```text
Excel cells → VBA bridge → request.json → runner command → scripts/price_json.py
                                                                    ↓
                                                    pricer.endpoints.main
                                                    analyze_vanilla_payload(payload)
                                                                    ↓
                                                    assets.corporate.vanilla  →  core.*
                                                                    ↓
Excel cells ← VBA bridge ← response.json ← runner command ←─────────┘
```

Two design choices that look opposed and are not: **inside** Python, many small functions;
**at the boundary**, one call that returns everything. The endpoint is an arrangement layer
over the same functions a Python caller uses.

## 2. The contract, in brief

**Two operations**, deliberately separate:

```text
calibrate_and_risk   clean market price IN -> implied OAS + all risk OUT
                     REFUSES a supplied oas_bp (a mark and a typed spread can disagree)
price_at_oas         an OAS in bp IN -> model price + all risk OUT
```

**Firm** (economics): currency must resolve to a usable curve; dates must be ISO **strings**;
maturity after valuation; a positive, finite price; a known operation; no hand-typed OAS in
the calibrating operation.

**Forgiving** (presentation): lower-case currency, numbers as text, missing request id /
schema version / operation, unknown fields (ignored with a warning), a face value other than
100 (echoed, **not applied**), and volatility on an instrument that cannot use it (echoed,
reported unused, `null` sensitivities — never a fabricated zero).

**Error vocabulary**: `INVALID_JSON`, `VALIDATION_ERROR`, `UNSUPPORTED_OPERATION`,
`CURVE_NOT_FOUND`, `CURVE_BUILD_FAILED`, `CALIBRATION_FAILED`, `PRICING_FAILED`,
`INTERNAL_ERROR`. No message ever carries a path, a traceback or the payload.

**The parity guarantee**: every number the interface returns equals the direct function call
as the identical float — asserted with `==`, not a tolerance. That is what makes a second,
drifting implementation impossible.

## 3. Decisions worth not re-opening

| Decision | Reason |
|---|---|
| Dates are ISO strings; a numeric date is a hard error | `pandas.Timestamp(39903)` = 1970-01-01. The silent wrong-date pricing is the worst failure this interface could have |
| `face_value` echoed, never applied | field names say "per 100"; applying face against a per-100 mark calibrates the wrong quantity |
| `CURVE_BUILD_FAILED` separate from `CURVE_NOT_FOUND` | GBP has a file and the date but an unusable curve; "not found" would send someone hunting for a present file |
| flat `endpoints/`, not `routes/` | one non-HTTP entry point does not earn a folder |
| VBA-JSON vendored, not hand-written | there is no VBA runtime in this environment, so a home-made parser would reach a live demo never having executed once — and our own responses contain the cases it would get wrong (a residual serialised as `-5.885e-09`) |
| batch refused with a clear message | Mario's own phrasing was "for each bond"; the single-bond object is canonical |

## 4. The Excel bridge

`RysePricingBridge.bas` is an **adapter only**: it reads named cells, converts Excel dates to
ISO, serialises, runs one configured command **and waits for it**
(`WScript.Shell.Run(..., waitOnReturn:=True)`), parses the answer, writes cells back. No
pricing, no curve choice, no OAS, no volatility rule.

The workbook knows exactly **one** thing about the engine: a command that accepts `--input`
and `--output`. Pointing that at a packaged executable or an HTTP wrapper changes nothing
else — no field, no cell, no VBA.

**Tested on real Excel**: `integrations/excel_vba/tests/Run-BridgeTests.ps1`, in two modes — a
stand-in runner (no Python needed) and `-PythonExe` (Excel calls Python for real). Both pass.
**23 checks at v1.0, 48/50 once the tree products reached the bridge, 57/61 since `floating`
closed the last untested type on 2026-08-31.**

That test found a genuine defect on its first run: JSON `null` arrives in VBA as `Null`, not
`Nothing`, so `Set x = Field(response, "applicability")` raised "Object required" on **every
error response** — the sheet would have shown a technical error box instead of the reason
the bond could not be priced. Fixed with a `FieldObject` accessor; the error path is now a
regression check.

## 5. The demonstration workbook

`integrations/excel_vba/demo/` holds a real `.xlsm` with input cells, result cells and three
buttons, plus the builder script that regenerates it for any machine and a five-minute run
sheet.

```text
Price this bond               prices in ~1.9 s AND drops both JSON documents onto the sheet
Clear                         empties results and the JSON panel, for a clean re-run
Load saved answer (no Python) reads the committed example response — one click, no browser
```

The JSON panel was the fix for a real UX flaw: the first version had buttons that made the
presenter **leave Excel and navigate the file system**, which is dead air in front of an
audience. Now the request and the answer appear side by side on the sheet, with the same
`request_id` visible in both — a better way to make the point than opening a file.

Verified live: price → 1.9 s, all fourteen result cells correct; price 94.25 → 88 moves the
implied spread 523.30 → 635.19 bp; currency CHF → a clean `CURVE_NOT_FOUND` with the stale
numbers **cleared** rather than left on screen.

## 6. Current limits

- ~~**vanilla only through Excel.**~~ **NO LONGER TRUE — this limit was lifted on 2026-08-31.**
  The bridge now constructs five of the seven types (vanilla, callable, puttable, sinking,
  floating) and all five are verified by real-Excel round trips, including the volatility
  direction driven from the sheet. What remains is the *worksheet layout*, not the plumbing;
  the visible demo workbook is still vanilla-only, and `scripts/demo_volatility.py` still
  exists. See the 08-31 update at the end of this file.
- **one bond per call.** A portfolio is a loop over the same function, not a different
  design — but the sheet does not do it.
- **Windows-only bridge** (`WScript.Shell`, `ADODB.Stream`). A Mac or Office-Script version
  would replace that module, not the JSON.
- **no timeout** in `WScript.Shell.Run`; a runner that can hang should be wrapped.
- **no curve caching** — each request rebuilds its curve, which is irrelevant at one bond and
  is the first thing to add when batch arrives.

## 7. Determinism, and why it matters for the cloud

The same request produces **byte-for-byte identical** output on Windows (Python 3.13, NumPy
2.3) and on the Linux server (different Python, different NumPy) — checked on the full
response file, not a rounded summary. Results are therefore reproducible, cacheable,
replayable and comparable, which is exactly what a distributed runner needs.

Every pricing function is pure: no shared state, no globals, one bond per call. A portfolio
is an embarrassingly parallel workload and nothing in the design has to change for it.

---

## Update 2026-08-30 — v1.1: one entry point, seven instrument types

`schema_version` 1.0 → **1.1**, and the change is **additive**: one new optional field in
`bond`, plus per-type fields. A v1.0 request is a valid v1.1 request returning the same
numbers — asserted by the 28 existing endpoint tests and the 23 real-Excel checks, all of
which pass untouched.

**Why this was done once rather than twice.** The 08-25 report told Mario dispatch would land
"next week, so a single change covers callable, puttable and floating together rather than two
changes". Doing floating now and the tree types later would have contradicted the recorded
rationale for deferring it. All seven landed together.

### The dispatch field

```json
"bond": { "instrument_type": "fixed_to_floating", ... }
```

`vanilla` (default) · `stepped` · `floating` · `fixed_to_floating` · `callable` · `puttable` ·
`sinking`. Case and hyphens forgiven; an unknown value is `UNSUPPORTED_INSTRUMENT`, which
lists the valid ones. **Absent = vanilla**, which is what keeps every existing caller working.

The public entry is now `analyze_payload`; `analyze_vanilla_payload` is retained as an alias.

### Per-type inputs

| type | required | optional |
|---|---|---|
| `vanilla` | `coupon_pct` | — |
| `stepped` | `coupon_schedule` | — |
| `floating` | — | `quoted_margin_bp`, `current_coupon_pct` |
| `fixed_to_floating` | `coupon_pct`, `switch_date`, **`quoted_margin_bp`** | `float_frequency` |
| `callable` / `puttable` | `coupon_pct` + its own schedule | the other schedule, volatility |
| `sinking` | `coupon_pct`, `sinking_schedule`, `sinking_fraction_basis` | call/put schedules, volatility |

A **floater has no `coupon_pct` at all**; sending one produces a warning and is ignored.
Schedules are arrays of objects, and **every date inside them obeys the same ISO-string rule
as every other date** — an Excel serial in `bond.call_schedule[0].date` is refused exactly
like one in `maturity_date`, and the error names the entry.

### Per-type results

`stepped` adds `coupon_pct_in_force_at_valuation`; `floating` adds `next_reset_years`,
`quoted_margin_source` and **`spread_interpretation`**; `fixed_to_floating` adds
`next_switch_years`, `reference_oas_to_switch_bp` and a `reference_note` labelling that column
spurious for a deep discount; tree types add `volatility_used_decimal`.

`spread_interpretation` exists because the same field means two things: a **credit spread over
the index** when a margin was supplied, and a **discount margin absorbing the unknown
contractual margin as well as credit** when it was not. Most of this book is the second case.
The response says which, rather than leaving a reader to assume.

### Volatility, per type

Not one sentence for everything any more. The three tree types return real numbers in both
directions (see `12`); the four option-free types return `null` — never `0.0`, which would
read as a calculated vega — with a reason that names why **that** product has none. A stepped
bond's reason is not a floater's.

### Two refusals that are new

Both replace a failure that happened anyway, somewhere unhelpful: a **hybrid with no
post-switch margin** (a placeholder zero would report a half-modelled bond as whole), and a
**sinking schedule with no fraction basis** (which used to surface as "no spread reprices this
bond — check the price, the coupon and the maturity").

### ⚠️ Three different numbers: 7 / 5 / 5 (corrected 2026-08-31)

**Do not write "the spreadsheet can ask for any of seven".** That reads a number off the
engine and attaches it to Excel, and it is the single most repeated error in this project's
own documents. Measured by driving `BuildRequest` and running the result through the live
endpoint:

| | count | which |
|---|---:|---|
| supported by the engine and the contract | **7** | vanilla · stepped · floating · fixed_to_floating · callable · puttable · sinking |
| constructible from cells by the VBA bridge | **5** | all but `stepped` (no coupon-table cells) and `fixed_to_floating` (no switch-date cell) |
| verified by a real-Excel round trip | **5** | vanilla · callable · puttable · sinking · floating |

`floating` was the last of the five to be driven from a real spreadsheet (08-31). Two optional
cells were added for it — `FIP_QuotedMarginBp` and `FIP_CurrentCouponPct`, read only when the
type is `floating`, neither defaulted. Blank margin ⇒ `UNUSED_FIELD` and the spread is a
discount margin; blank running coupon ⇒ `PROVISIONAL_RISK` and a base-curve proxy. The live
round trip returns **397.3304715128111 bp** for `TNTD03080834`, bit-identical to the
production CSV row.

**The two remaining types are unconstructible on purpose.** Adding a coupon-schedule table or
a switch-date cell would make a sixth type reachable from a worksheet whose layout Mario has
not decided — see `04` §1.

**Separately: the visible DEMO workbook (`DemoBuilder.bas`) is still vanilla-only.** It has no
type or schedule cells. The engineering test harness drives the named cells directly, which is
how five types are exercised without a designed sheet existing. Keep these two facts apart:
"the bridge can send this" and "a worksheet exists that a person would use to send it".
