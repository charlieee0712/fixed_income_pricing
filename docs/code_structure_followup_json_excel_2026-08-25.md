# Code-structure follow-up — currency, volatility, and the JSON/Excel bridge

**Date:** 2026-08-25 · **Type:** decision record / addendum ·
**Predecessor:** `docs/code_structure_sample_2026-08-15.md` (the approved sample report)

This is an **addendum**, not a replacement. The August 15 sample report stands as
written; this file records what Mario said about it, how we read his three follow-up
points, what we built in response, and where the code ended up.

---

## 1. Where this round came from

Mario reviewed the restructured vanilla sample (`src/pricer/` = `core/` engines +
`assets/` thin wrappers, every number bit-identical, 166 automatic checks) and
**approved the direction**, with three follow-up points. The sample-first freeze that
had been in place since 2026-08-15 is therefore lifted for this workstream.

> **Mario's three follow-up comments — verbatim, to be pasted in.**
>
> 1. *(currency)* …
> 2. *(yield volatility)* …
> 3. *(Excel ↔ JSON ↔ Python process)* …
>
> The summaries in §2 are our working interpretation, recorded before his exact
> wording was to hand; if the verbatim text differs in substance, §2 is what needs
> re-reading, not the code — every item below is a data/contract decision, not an
> engine change.

## 2. How we read the three points, and what follows from each

### 2.1 Currency

*Read as:* the external input story must name the pricing currency explicitly, and
that currency must select the bond's own curve.

*Adopted:* `currency` is now input 5 of the corporate input catalogue, marked as an
**external routing input**: a JSON/Excel caller cannot carry a curve object across
the wire, so it sends currency + valuation date + coupon frequency, and the endpoint
resolves the curve (`core.market.curves.resolve_curve`). `USD EUR GBP JPY AUD KRW`
are configured. Two rules go with it:

* **no silent USD fallback** — an unconfigured currency, a date the curve file does
  not contain, and a curve that cannot be bootstrapped are three different refusals
  with their own messages. A EUR bond quietly discounted on a USD curve is a wrong
  number that looks like a right one;
* **currency is not an FX instruction** — it chooses a discount curve. Portfolio
  values stay on the custodian's base-USD columns, exactly as before.

### 2.2 Yield volatility

*Read as:* is volatility an input to this thing or not — and if a generic form sends
it, what happens?

*Adopted:* vanilla is an option-free discounted-cash-flow calculation and has **no
volatility parameter at all**. So the interface neither fails the request nor
swallows the field: it accepts it, echoes it back, and states in the response that it
was not used, returning `null` — never `0.0` — for the volatility sensitivities,
because a zero would be read as a *calculated* vega. `day_count_label` is treated the
same way (carried as data; the response states that ACT/364 with a 182-day grid was
used). Both fields answer, in the response itself, the question they would otherwise
raise in a meeting.

Volatility becomes a real input when the callable/option engines join this interface.
The contract already reserves the same field name for them, and the plan fixes what
they must return per scenario: the price at a fixed baseline OAS *and* the OAS
re-implied at a fixed market price.

### 2.3 The Excel ↔ JSON ↔ Python process

*Read as:* prove the round trip — a spreadsheet sends inputs, Python prices, the
sheet shows the answers — and keep it portable enough for the cloud team to reuse.

*Adopted:* one request object in, one complete result out.

```
Excel cells -> VBA adapter -> request.json -> runner command -> Python endpoint
                                                                     |
Excel cells <- VBA adapter <- response.json <- runner command <-------+
```

The internal design stays "many small functions"; the boundary is deliberately the
opposite ("one call, everything back"). They are complementary: the endpoint arranges
the same functions a Python caller uses and holds no formula of its own.

The workbook knows exactly one thing about the engine — a command taking `--input`
and `--output`. Pointing that at a packaged executable or an HTTP wrapper later
changes no field, no cell and no VBA. **No server name, no SSH command and no
personal path is baked into the workbook.**

## 3. What was built

| Piece | Where |
|---|---|
| Public entry `analyze_vanilla_payload(payload) -> response` | `src/pricer/endpoints/main.py` |
| Request/response contract (normalisation, validation, envelopes) | `src/pricer/endpoints/contracts.py` |
| Vanilla orchestration — calls the approved functions, no formulas | `src/pricer/endpoints/pricing.py` |
| The one environment-aware file (where curve files live) | `src/pricer/endpoints/dependencies.py` |
| Reusable curve routing `resolve_curve` / `curve_id` / `CurveUnavailable` | `src/pricer/core/market/curves.py` |
| `currency` + external-field column + applicability wording | `src/pricer/assets/corporate/bonds_input.py` |
| File runner: request file -> response file | `scripts/price_json.py` |
| Excel bridge, vendored JSON parser, runner example, real fixtures | `integrations/excel_vba/` |
| Interface reference (the technical handoff) | `docs/vanilla_json_excel_interface_v1.md` |
| 28 interface tests (parity, firm rules, lenient rules, CLI) | `tests/test_vanilla_json_endpoint.py` |

**Nothing else moved.** No engine, no shim, no driver, no `dataio`/`curves`/`recon`
module was touched, so every existing number is unchanged and the suite went from
**166 to 194 green**.

Two operations are exposed: `calibrate_and_risk` (clean market price in, implied OAS
out — the locked methodology, which still refuses a hand-typed OAS) and
`price_at_oas` (spread in, price out — the flow the legacy per-metric functions use).
The second was added rather than deferred: it costs ~15 lines and removes the only
place where the contract would have rejected a field a user could reasonably send.

## 4. Decisions worth remembering

1. **The parity guarantee.** Every result equals the direct function call as the
   identical float, asserted with `==` in the tests — no endpoint-specific rounding,
   so the interface can never drift into a second implementation.
2. **Dates must be ISO strings.** Excel stores 2009-03-31 as `39903`; the Python date
   parser reads a bare `39903` as nanoseconds since the epoch, i.e. 1970-01-01. A
   numeric date is therefore refused outright — it is the one silent, economic
   failure this interface could have had, and the bridge's job is to convert.
3. **`face_value` is echoed, not applied.** Every field name says "per 100"; applying
   a face of 1000 while the caller sends a per-100 mark would calibrate to the wrong
   quantity. Positions scale by par / 100 on the caller's side.
4. **Errors never carry a file path, a traceback, or the payload.** The curve loader
   does name its data file in its own message; the endpoint catches that and re-words
   it with currency and date only.
5. **The VBA JSON parser is vendored** (VBA-JSON v2.3.1, MIT, unmodified, provenance
   recorded). This environment has no VBA runtime, so a hand-written parser would
   have reached a live demo never having been executed once — and our own responses
   contain exactly what a home-made parser gets wrong (e.g. a residual serialised as
   `-5.885e-09`).
6. **Flat `endpoints/`, not the template's `endpoints/routes/`.** A single non-HTTP
   entry point does not earn a folder, and the original directive was that the code
   was too nested. `routes/` arrives with the HTTP service.

## 5. Honest limits of v1

* **Not yet click-tested end to end.** The Python side is covered by the suite, and
  the committed examples are its real output; the VBA is written against those
  fixtures. This machine has no Excel and server 47 has no Excel, so the first live
  click-through happens on a Windows desk with a runner installed. Said plainly in
  the README rather than implied to be done.
* **Vanilla only.** Floating, hybrid, callable, agency, index-linked and MBS engines
  exist and are validated in the repo, but are not exposed through this interface
  yet. They arrive in their own rounds, through the same request shape.
* **One bond per request.** A batch payload is refused with a clear message rather
  than half-supported. The single-bond object stays canonical; batch is a list
  wrapper when a real consumer needs it.
* **No curve caching.** Every request rebuilds its curve — irrelevant at one bond,
  and the first thing to add when batch arrives.
* **Steepening / flattening** (the legacy sheet's T/U columns) are not part of this
  interface: they need a non-parallel curve twist, and the legacy `SteepFlat` table
  that defined the twist is lost. That is a separate, already-tracked item.

## 6. What comes next

* **Callable through the same door.** The lattice engine migrates into `pricer/`,
  gains a `callable` operation, and volatility becomes a used input — reporting, per
  scenario, both the fixed-OAS price effect and the OAS re-implied at a fixed price.
* **The remaining engines** (floating, hybrid, agency, ILB, MBS) follow the same
  pattern in the approved rollout order.
* **Cloud / Google team.** A service exposes the *same* `analyze_vanilla_payload`
  over HTTP: `Excel or Office Script -> POST request JSON -> response JSON`. The
  transport may multiply; the pricing implementation may not.
* **Contract tooling** (JSON Schema, typed models, richer error codes, request
  hashes, signed macros) once the examples are stable and there is a second real
  consumer — deliberately not prerequisites for proving the process.

## 7. Open questions for Mario

1. **`bons_input.py` vs `bonds_input.py`** — still open from the August sample
   (question 2 there); the template's spelling looked like a typo and we kept
   `bonds_input.py`.
2. **Which workbook should carry the demo bridge?** We will not touch the
   authoritative URS holdings file; a small demonstration workbook is the intended
   home unless he prefers otherwise.
3. **Rollout order after vanilla** — the sample report proposed floating → callable →
   Monthly reconciliation → ILB/agency → MBS; his approval note did not change it, so
   that order still stands unless he says otherwise.
