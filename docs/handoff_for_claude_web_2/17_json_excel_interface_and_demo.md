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

**Tested on real Excel**: `integrations/excel_vba/tests/Run-BridgeTests.ps1`, 23 checks, in
two modes — a stand-in runner (no Python needed) and `-PythonExe` (Excel calls Python for
real). Both pass.

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

- **vanilla only through Excel.** Callable, puttable and sinking price in Python today;
  connecting them to this interface is Round 2b. The demo therefore shows the volatility
  story from a terminal (`scripts/demo_volatility.py`).
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
