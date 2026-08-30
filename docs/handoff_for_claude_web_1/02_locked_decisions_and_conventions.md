# Locked decisions & conventions — do not re-litigate

Settled by directive, test, or evidence. Reopen only if the user explicitly asks.

## A · Methodology locks

1. **Valuation & calibration date = 2009-03-31** (matches holdings; Mario's USD curve fills
   the old curve-file gap). The custodian's tighter-than-index marks are the genuine
   recovering-market level (Mario 2026-07-03) — the "70-day gap / BT marking date" question
   is CLOSED. 2009-06-10 is kept as a control run only.
2. **OAS is a per-bond calibration OUTPUT, not a pricing input** (Mario 2026-06-30): solve
   the flat spread that makes the model reprice the custodian clean price, then compute
   risk metrics on the calibrated model. Index/sector OAS sourcing is dead (and FRED's free
   OAS history was truncated to a rolling 3y in Apr-2026 — the workbook archive
   `OAS Credit Curves`, 1997–2025 daily, is the only history source).
3. **Price-convention law** (Liping review, enforced by 16 invariance tests): model PV =
   dirty; custodian `BT` = clean; ONE shared accrued-interest formula (ACT/364,
   schedule-aware) ⇒ solving clean(OAS)==BT and dirty(OAS)==BT+AI give the SAME root.
   **Duration/convexity denominator = DIRTY**, retained after testing both ways against
   custodian durations (n=61: dirty closer 41/61).
4. **Legacy discounting bug is understood and contained:** the legacy tool discounts a
   semiannual zero with the continuous formula ⇒ systematic under-pricing (~0.2% @ 8y). Our
   default is corrected (par reprices to 100.000000); `vba_compat=True` reproduces the
   legacy output bit-for-bit for reconciliation only. Two legacy bootstraps exist
   (continuous z for the audit routine vs semiannual z inside BondPrice) — never conflate.
5. **Cash-flow calendar = the legacy ACT/364 + 182-day backward grid** — a validated
   convention, not a bug; real day-count labels (30/360, ACT/ACT…) are carried as data
   only. The legacy input dictionary itself marks Daycount "not used".
6. **Make-whole callables price as vanilla** (47 bonds, flagged; call ≈ economically
   worthless); only the 5 genuine-gap callables use the lattice. **σ = 0.15** (Mario).
   Call schedules are DATA (`data/call_schedules.csv`) — never hard-coded par-call.
7. **Single-curve FRN/hybrid discounting = the 2009 convention**; OIS dual-curve is a
   documented future enhancement, not now. FRN effective duration bumps the CURVE
   (reprojects forwards), giving the signature short/negative durations — correct, tested.
8. **ILB spread ≈ −breakeven at zero assumed inflation** — kept in its OWN column
   (`implied_spread_vs_nominal_bp`), never mixed with credit OAS (unit-tested identity).
9. **Universe = deterministic 2-layer MECE funnel** with LOCKED drop priority
   (terms-unavailable → defaulted → no-rating → structured/floating → callable → matured);
   the golden counts reproduce exactly (join 597/135/19, canonical 522 @ 6-10 no-override).
   Coupon routing reads `Coupon_Formula2` and reconciles EXACTLY to Mario's 676-row pivot.
   Rating red lines: BBB−→BBB, BB+→BB (IG/HY split); CC/C/Ca → CCC, never default (only D/SD).
10. **Medians composition:** only PRICED routes feed by-rating medians; near-maturity
    (<1y), hybrids/junior-sub, distressed, zero-structured stay OUT.

## B · Data & process locks

11. **No Bloomberg on our side.** All external data arrives via Mario/Liping pulls into
    tracked CSV landing zones (`term_overrides`, `call_schedules`, `hybrid_switch_terms`,
    `coupon_schedules`, `frn_spreads`, `make_whole_overrides`). **Web/ISIN-researched
    values are PROVISIONAL: on any Bloomberg return — diff, Bloomberg wins, deltas logged**
    (`06_missing_data_registry.md` is the living registry). A data fill = one CSV row,
    zero code change — that architecture is the point (Mario 2026-07-30).
12. **Data-gap bonds are flagged + custodian-marked, never half-modelled / force-priced.**
    Amortizing (1) + n/a (4) are permanently out (Mario). Pass-through work starts only
    when its Bloomberg data arrives.
13. **Deferred-asks discipline:** the deferred trio (KTBi, agency call-schedule
    confirmation, rating quirk) waits for Mario's MBS-data return — do not draft re-asks.
    Dedupe Mario/Liping returns before loading.
14. **Repo stays PRIVATE; client data is tracked in-repo** (boss-approved 2026-07-08).
    Custodian golden columns (BT/BU/DI/AQ) live in reconciliation tables, never in pricing
    inputs.

## C · Code-structure workstream locks (Mario 2026-08-15)

15. **Sample-first** (user's call): nothing beyond the vanilla chain migrates until Mario
    approves the sample.
16. **Migration ground rules:** module-by-module; old import paths stay as shims until
    retired; the FULL test suite must be green at every step with float-operation order
    preserved (bit-identical numbers); every function documents its inputs as a numbered
    block; asset-layer units follow the legacy sheet (coupon in percent, prices per 100,
    spreads in bp) while core stays in decimals; new code imports `pricer.*`, never the
    shims.
17. **The Monthly sheet is the reference:** per-metric simple functions + input
    dictionaries (adopted), and its ~2,600-bond results table is the reconciliation golden
    (planned milestone — treat its numbers as the target, mindful that the legacy engine
    carries the known discounting bug, so reconciliation may need `vba_compat`).

---

## Added 2026-08-25 (the JSON/Excel and embedded-option rounds)

**Interface**

- **Two named operations.** `calibrate_and_risk` takes the clean market price and **refuses**
  a supplied OAS; `price_at_oas` is the separately named operation for pricing at a spread the
  caller chooses. A mark and a typed spread can disagree and there is no principled tiebreak.
- **Dates crossing the JSON boundary are ISO STRINGS.** A numeric date is a hard error:
  `pandas.Timestamp(39903)` is 1970-01-01, so an Excel serial would price the bond on the
  wrong day with nothing looking broken. Converting it is the VBA bridge's job.
- **Everything is quoted per 100 face.** A supplied `face_value` is echoed and **not
  applied** — applying it against a per-100 mark calibrates the wrong quantity.
- **Currency routes a curve and nothing else.** No silent USD fallback; `CURVE_NOT_FOUND`
  (no file, or no row for that date) and `CURVE_BUILD_FAILED` (the curve exists but is not
  arbitrage-free — GBP at 3-31) are different codes because they mean different things.
- **Exact parity is the contract**: every interface number equals the direct function call
  with `==`, not a tolerance. That is what prevents a second, drifting implementation.
- **Leniency is for presentation only.** Lower-case currency, numbers as text, unsorted
  schedules, unknown fields, an unused volatility — all absorbed with a warning. Economics
  are never inferred.

**Embedded options**

- **One shared tree** serves callable, puttable and sinking-fund bonds. Fourteen workbook
  rows carry two rights at once, so separate engines would have to copy each other.
- **Sinking fund = issuer optional redemption on fractions of the OUTSTANDING amount.** Only
  that basis keeps value-per-unit level-free and the node path-independent on a recombining
  tree; an original-face schedule needs a strip decomposition and is **refused**, not
  approximated.
- **A pass-through or amortising bond is not a sinking-fund bond.** No holding is rerouted on
  the strength of a `Sinking = Yes` flag.
- **Contradictory terms are refused**, not resolved silently: a put priced above a call on the
  same date, a sinking date colliding with a call or put date, two redemptions inside one
  coupon period.

**Validation**

- With **no golden available** (all 474 tree-family Monthly rows are stale), the accepted
  evidence is production parity by hash + `==` direct-call parity + invariants with at least
  one exact anchor + the Bloomberg three-way.

**Process**

- **Reports serve two audiences**: Mario and the Google team, who now attend the briefing in
  person. Plain language throughout, plus one labelled engineering section.

## Added 2026-08-30 (Round 2b — Mario's pivot column F)

**What Mario's annotations mean**

- **`finished` on the pivot's column F means "in the restructured `pricer/` package"**, not
  "priced". Every coupon family he marked `no` had already been pricing in the legacy layer
  since July. Read any future column-F marking that way.
- **Column F is the ask.** It is committed with the workbook, because it is the only record of
  what was requested and when. Do not treat a spreadsheet annotation as ephemeral.

**Curves and market data**

- **Par-yield file units are declared per file, never sniffed.**
  `curves.bootstrap.PAR_YIELD_UNITS` marks `GBP_Yield_Curve.txt` and `DKK_Yield_Curve.txt` as
  PERCENT; the other 24 files are decimals. A threshold rule cannot separate a 0.5% Danish
  yield from a 0.5 decimal, so declaring beats detecting.
- **A par-yield row that scales above 100% raises `ParYieldUnitError` before the bootstrap
  runs.** This exists so a units mistake can never again present itself downstream as
  "the par curve is not arbitrage-free", which is a statement about the market.
- **An entry whose only evidence is one of our own error messages is not yet a data gap.**
  Reproduce the claim against the raw file, or against the market the file describes, before
  writing it into the missing-data registry and before asking anyone for it. This rule cost
  two months and one silently-dropped bond to learn.

**Interface**

- **One entry point, seven instrument types** — `bond.instrument_type` dispatches; there is
  no second endpoint, envelope or error vocabulary. Adding the mortgage engine later is one
  map entry and one function. `analyze_payload` is the public name; `analyze_vanilla_payload`
  is retained as an alias and a typeless payload is still vanilla, which is what keeps the
  Excel bridge working untouched.
- **A fixed-then-floating bond without its post-switch margin is REFUSED, not defaulted to
  zero.** A placeholder margin prices the floating leg as if the borrower paid pure index and
  reports a half-modelled bond as a whole one. A plain floater *may* be priced with the margin
  absorbed into the calibrated spread — and the response then says so explicitly, so the
  number is never read as a clean credit spread.
- **`schema_version` is 1.1 and the change is additive.** A v1.0 request is a valid v1.1
  request returning the same numbers.

**Numerical conventions**

- **A floating note's effective duration has two exact regimes and the sign flips between
  them.** With the already-fixed `current_coupon` supplied it is **+**the time to the next
  reset; with that period projected off the curve it is **−**the time *since* the last reset,
  because the bump reprices that coupon too. Both are within one coupon period and far below
  a same-maturity fixed bond. Neither is a bug; only the interpretation differs.

**Validation**

- **Production parity is compared local-fresh vs local-fresh.** Windows and server 47 agree
  for the test suite and the single-bond endpoint JSON, but full 565-bond driver CSVs differ
  by up to **3.6e-8 relative, entirely in `convexity`** (a second difference ÷ bump² amplifies
  a last-bit rounding by 10⁸). Text columns are identical and prices/spreads/durations agree
  to ~1e-12. A cross-platform byte comparison therefore shows a difference that is not a
  regression.

---

# D · The numerical laws a plan must not break

Everything above is a *decision*. This section is the *arithmetic* every validated number in
the repo sits on. Breaking one of these silently invalidates the lot, so a plan that touches
pricing should be checked against it. (handoff 2's `03` carries the same laws with the
derivations.)

## D1 · The calendar: ACT/364 with a 182-day grid

One year is **364 days**; one semiannual period is **182**. The schedule is built **backwards
from maturity** in `round(364/freq)`-day steps until just before valuation.

This is not an approximation to improve. It is the legacy engine's own convention, verified
against the VBA on 2026-06-29, and every validated number rests on it. Real day-count labels
(`30/360`, `ACT/ACT`) are carried as **data** and reported unused — the legacy tool's own input
dictionary says of that field: *"30/360, but is not used"*.

## D2 · The discounting law

```text
DF(t) = exp(-t · (z_continuous(t) + spread))          z linearly interpolated, monthly grid
```

The test that this is *correct* and not merely chosen: a curve must reprice its own par bonds
to exactly 100. It does. The legacy stored a **semiannual** zero and discounted it with the
**continuous** formula, which under-prices systematically (10y par bond → 99.67; ≈0.2% at 8y).
`vba_compat=True` reproduces that bug bit for bit and exists only for reconciliation — never
the default. ⚠️ Two bootstraps exist in the legacy code and must not be conflated: the
auditable routine uses continuous `z = −ln(DF)/t`; `BondPrice`'s embedded one uses semiannual
`z = 2·((1/DF)^(1/2t) − 1)`. Same discount factors, different expression.

## D3 · The clean / dirty law

```text
model PV     = DIRTY
custodian BT = CLEAN
calibration solves   clean(OAS) == BT   ⟺   dirty(OAS) == BT + accrued
```

Both forms give the **same root**, because accrued depends only on dates — not on the OAS, the
curve, or any embedded option. Unit-tested per engine (16 checks). Two consequences:

- **there is exactly ONE accrued formula** (`core/pricing/cashflows.accrued_interest`), shared
  by the analytical engine, FRN, hybrid, ILB and the lattice. A second copy is how this rots;
- **duration, DV01 and convexity divide by the DIRTY price.** Tested both ways against the
  custodian's duration on 61 bonds; dirty won 41–20.

## D4 · Units

| layer | units |
|---|---|
| `assets/` wrappers (the legacy-facing surface) | coupon **PERCENT**, prices per **100**, spreads **BASIS POINTS**, volatility **DECIMAL** |
| `core/` engines | decimals throughout |
| the JSON interface | the asset layer's units, and every field name says so |

Wrappers convert; the core never sees percent. A volatility "point" is one percentage point
(0.01 decimal). **The one documented exception**: a coupon *schedule* is decimal even at the
asset layer, because the parser and the override CSV both emit decimals and two dialects of one
object would be worse; at the JSON boundary the field is `rate_pct` and `contracts.py`
converts. `stepped.validate_schedule` refuses a percent-looking schedule rather than pricing a
750% coupon.

## D5 · Currency routes a curve — it is not an FX instruction

A bond discounts on its **own-currency** curve. Portfolio values stay on the custodian's
base-USD columns; nothing self-converts. **No silent USD fallback.** Failures are named
separately because they mean different things to whoever must fix them:

```text
currency not configured           -> CURVE_NOT_FOUND     (e.g. CHF)
configured, but no row for date   -> CURVE_NOT_FOUND     (e.g. KRW at 2009-03-31)
row exists, bootstrap refuses it  -> CURVE_BUILD_FAILED
```

⚠️ **`CURVE_BUILD_FAILED` has no live example any more.** GBP used to be it; that was our units
bug, not the market's (see `12` A1). The mapping is still tested, by monkeypatching the loader
— which is the right way round.

## D6 · Par-yield file units are declared, never detected

`PAR_YIELD_UNITS` marks `GBP_Yield_Curve.txt` and `DKK_Yield_Curve.txt` as **percent**; the
other 24 exports are decimals. A threshold heuristic cannot separate a 0.5% Danish yield from a
0.5 decimal. Any scaled row above 100% raises `ParYieldUnitError` **before** the bootstrap, so
a units mistake can never again surface as a claim about arbitrage.

## D7 · OAS is calibrated, never supplied — with one named exception

`calibrate_and_risk` takes the clean market price and **refuses** a supplied `oas_bp`: a mark
and a hand-typed spread can disagree and there is no principled tiebreak. `price_at_oas` is the
separately named operation for "price this at a spread I choose" (what the legacy per-metric
functions did). The solve is robust rather than clever: price is strictly decreasing in the
spread, so the root is unique; the bracket auto-widens; Brent finds it.

## D8 · Migration law

A migration **moves** code; it does not rewrite it.

```text
copy the implementation verbatim       float-operation order preserved
old path becomes a shim                re-exporting the SAME objects (identity-asserted)
prove it by hashing whole outputs      not by spot-checking numbers
run the full suite after every commit
```

If a frozen output changes, **stop and diagnose before continuing**. "It is only the last
digit" is exactly the signal that something moved.

## D9 · Refuse rather than guess — the current list

Every refusal marks a place where a silent assumption would produce a plausible **wrong**
number: a date sent as a number (an Excel serial); a currency with no usable curve; a put
priced above a call on the same date; a sinking date colliding with a call or put; two sinking
redemptions inside one coupon period; an exercise schedule entirely after maturity (it would
quietly price a straight bond); a `fraction_basis` the engine does not implement; a coupon
above 40 percent; a **hybrid with no post-switch margin**; a **sinking schedule with no
fraction basis**.

**Forgiven, deliberately:** lower-case currency, numbers as text, unsorted schedules, duplicate
schedule entries (deduped with a warning), missing optional fields, unknown extra fields, a
face value other than 100 (echoed, not applied), and volatility on an instrument with no use
for it (echoed, reported unused, `null` sensitivities — never a fabricated zero).

**The dividing line, worth restating in any plan touching the contract: leniency is for
presentation; economics are never inferred.**

## D10 · Reporting laws

- a value that could not be computed finitely is serialised as `null` with a warning, never a
  placeholder digit;
- error messages never carry a file path, a traceback or the client payload;
- every result names the curve that produced it (`curve_id` = `USD|2009-03-31|Semiannual`);
- the response echoes what it actually ran on (`inputs_used`), **in the caller's own units and
  shape**, so a wrong cell mapping is visible without reading Python.
