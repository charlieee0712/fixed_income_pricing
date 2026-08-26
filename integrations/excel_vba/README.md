# Excel bridge — RYSE fixed-income pricing (v1)

Price a vanilla corporate bond from an Excel sheet: the cells go out as one JSON
request, the engine answers with one JSON response, and the answers land back in
cells. The bridge is an adapter only — **no pricing logic lives in VBA**, and no
pricing logic lives in the JSON layer either. Every number comes from the same
validated Python functions the production runs use.

```
named cells  ->  RysePricingBridge.bas  ->  request.json  ->  runner command
                                                                    |
cells        <-  RysePricingBridge.bas  <-  response.json  <---------+
```

The full field-by-field contract is in **`docs/vanilla_json_excel_interface_v1.md`**.
This file is only the how-to.

---

## 1. Install (once per workbook)

1. Open the workbook, press **Alt+F11** (VBA editor).
2. **File → Import File…** and import BOTH modules from this folder:
   - `JsonConverter.bas` — VBA-JSON v2.3.1, MIT, vendored unmodified
     (provenance and licence: `LICENSE_JSON_PARSER.txt`)
   - `RysePricingBridge.bas` — the bridge
3. **Tools → References…** and tick **Microsoft Scripting Runtime**.
   VBA-JSON declares `Dictionary`, so without this reference the project will not
   compile. (It is present on every standard Windows Office install.)
4. Save the workbook as **.xlsm** (macro-enabled).

## 2. Name the cells

The bridge reads and writes **workbook-level named ranges** — no hard-coded A1
addresses, so the sheet can be laid out however the desk prefers. Create the names
via *Formulas → Define Name*.

**Inputs** (only the first six are required):

| Name | Example | Notes |
|---|---|---|
| `FIP_Currency` | `USD` | Selects the bond's OWN-currency curve. `USD EUR GBP JPY AUD KRW` are configured; anything else is refused, never silently replaced. |
| `FIP_CouponPct` | `6.5` | PERCENT, not decimal and not bp. |
| `FIP_CouponFrequency` | `2` | 1, 2, 4 or 12. Also selects the matching curve variant. |
| `FIP_MaturityDate` | `15/01/2017` | A real Excel date cell. The bridge converts it to `2017-01-15`. |
| `FIP_ValuationDate` | `31/03/2009` | Same. The curve file must have a row for exactly this date. |
| `FIP_CleanMarketPrice` | `94.25` | CLEAN price per 100 face — the calibration input. |
| `FIP_InstrumentId` | `DEMO-BOND-001` | Optional label, echoed back. |
| `FIP_SpreadShiftBp` | `10` | Optional, default 10 — the widening/tightening scenario size. |
| `FIP_YieldVolatility` | `0.15` | Optional. Vanilla does **not** use it (see §5). |
| `FIP_RunnerCommand` | `C:\RYSE\bin\ryse-fip.cmd` | Where the engine is (see §3). |

**Outputs** (create only the ones you want to see; missing names are skipped):

| Name | Meaning |
|---|---|
| `FIP_Status` | `ok` or `error` |
| `FIP_ModelCleanPrice` / `FIP_ModelDirtyPrice` / `FIP_AccruedInterest` | per 100 face |
| `FIP_ImpliedOASBp` | the calibrated spread, in basis points |
| `FIP_EffectiveDuration` / `FIP_DV01` / `FIP_Convexity` | years / price per +1bp / years² |
| `FIP_TighterPrice` / `FIP_WiderPrice` | price after the spread shift, both directions |
| `FIP_CurveId` | e.g. `USD\|2009-03-31\|Semiannual` — which curve produced the numbers |
| `FIP_VolatilityApplicability` | the plain-language answer to "did it use my volatility?" |
| `FIP_Warnings` / `FIP_Errors` | one line per entry |

## 3. Point it at an engine

`FIP_RunnerCommand` is any command that accepts `--input <file> --output <file>`.
Copy `runner_example.cmd`, edit its two paths, and name that file in the cell:

```
FIP_RunnerCommand = C:\RYSE\bin\ryse-fip.cmd
```

Alternatively set the `FIP_RUNNER_COMMAND` environment variable and leave the cell
empty. Nothing about the machine is baked into the workbook — **no server name, no
SSH command, no personal Python path**. When the engine later becomes a packaged
executable or an HTTP service, only this one setting changes; the field meanings and
the sheet stay identical.

## 4. Run it

Assign `PriceVanillaBond` to a button (or run it from Alt+F8).

The bridge writes the request to `%TEMP%\ryse_request_<timestamp>.json`, runs the
command **and waits for it to finish** (`WScript.Shell.Run(..., waitOnReturn:=True)`),
reads `%TEMP%\ryse_response_<timestamp>.json`, fills the cells, and deletes both temp
files on success. If a run fails, the files are left in place for inspection.

Two helper macros:

| Macro | What it does |
|---|---|
| `WriteRequestToFile` | Writes the request JSON only, and tells you where — see exactly what the sheet sends. |
| `PopulateFromResponseFile` | Maps a saved response into the cells. **Works with no Python installed** — use it with the committed fixtures below. |

## 5. What happens to volatility (and day count)

Vanilla pricing is an option-free discounted-cash-flow calculation: it has no
volatility parameter at all. A generic input form may still carry one, so rather than
failing the request or ignoring it quietly, the engine **accepts it, echoes it back,
and states that it was not used**; the volatility sensitivities come back as `null`,
never `0`, because a zero would read as a calculated vega. `FIP_VolatilityApplicability`
shows that sentence. Volatility becomes a real input when the callable/option engines
are migrated in a later round.

`bond.day_count_label` is treated the same way: carried as data, reported as unused,
with the convention actually used (ACT/364 with a 182-day coupon grid) stated back.

## 6. Test with the committed fixtures

`examples/` holds real engine input and output — the responses were generated by
running the CLI, not typed by hand:

| File | What it is |
|---|---|
| `vanilla_request_v1.json` | a complete request (USD, 6.5% of 2017-01-15, priced at 94.25 on 2009-03-31, volatility supplied) |
| `vanilla_response_v1.json` | its real response: OAS 523.298 bp, duration 6.0907 y, DV01 0.05811, convexity 43.437 |
| `vanilla_error_request_v1.json` / `vanilla_error_v1.json` | an unsupported currency (CHF) and the structured `CURVE_NOT_FOUND` answer |

Without Python: run `PopulateFromResponseFile`, choose `vanilla_response_v1.json`,
and confirm every output cell fills correctly (then try the error file — the numbers
must clear and `FIP_Errors` must show the message).

With Python: point `FIP_RunnerCommand` at your runner and check the same numbers come
back live. On the command line the same thing is:

```
PYTHONPATH=src python3 scripts/price_json.py \
    --input  integrations/excel_vba/examples/vanilla_request_v1.json \
    --output response.json
```

## 7. Known limitations of this first adapter

- **Windows only.** It uses `WScript.Shell` and `ADODB.Stream`, both Windows-Office
  facilities. A Mac or Office-Script version would replace this module, not the JSON.
- **One bond per run.** The single-bond object is the canonical unit; a batch payload
  is refused with a clear message rather than half-supported. Batch arrives with the
  service.
- **No timeout.** `WScript.Shell.Run` waits indefinitely. If a runner can hang, wrap
  it in a script that enforces its own timeout.
- **Not click-tested end to end here.** The Python side is covered by the automatic
  suite (28 interface tests, and the fixtures in `examples/` are its real output), and
  the VBA side is written against those fixtures — but this development environment
  has no Excel, so the first live click-through happens on a Windows machine with a
  runner installed. The VBA modules are marked as such until then.
- **Vanilla only.** Floating, hybrid, callable, agency, index-linked and MBS bonds have
  engines in the repo but are not exposed through this interface yet; they arrive in
  their own migration rounds, through the same request shape.

## 8. The authoritative workbook is never modified

This bridge is imported into a **demonstration** workbook. The client holdings file
(`URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx`) is a data source and is
never opened for writing, never given macros, and never used as the demo workbook.
