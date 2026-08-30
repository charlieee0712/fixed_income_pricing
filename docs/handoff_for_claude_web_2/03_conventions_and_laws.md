# Conventions and laws — the rules a plan must not break

These are the numerical and methodological invariants. Each is enforced by tests, and each
has a reason that is not "we prefer it that way". If a plan requires breaking one, say so
explicitly and explain what replaces it — do not let it happen as a side effect.

---

## 1. The calendar: ACT/364 with a 182-day grid

One year is **364 days**. One semiannual coupon period is **182 days**. The coupon schedule
is built **backwards from maturity** in `round(364/freq)`-day steps until just before the
valuation date.

This is not an approximation someone should improve. It is the legacy engine's own
convention, verified against the VBA on 2026-06-29, and every validated number in the repo
sits on it. Real day-count labels (`30/360`, `ACT/ACT`) are carried as **data** and reported
as unused — the legacy tool's own input dictionary says of that field: *"30/360, but is not
used"*.

`core/utils/dates.py` holds `YEAR_DAYS = 364.0` and `HALF_DAYS = 182` and the one schedule
walk every date-based engine shares.

## 2. The discounting law

```text
DF(t) = exp(-t · (z_continuous(t) + spread))
```

with `z` linearly interpolated on the dense monthly grid. The test that this is *correct*
rather than merely chosen: a curve must reprice its own par bonds to exactly 100. It does.

The legacy stored a **semiannual** zero and discounted it with the **continuous** formula,
which under-prices systematically (10y par bond → 99.67 instead of 100; ~0.2% at 8y).
`vba_compat=True` reproduces that bug exactly, bit for bit, and exists only for
reconciliation. It is never the default.

Two bootstraps exist in the legacy code and must not be conflated: the auditable routine
uses a continuous `z = -ln(DF)/t`; `BondPrice`'s embedded one uses a semiannual
`z = 2·((1/DF)^(1/2t) − 1)`. Same discount factors, different expression.

## 3. The clean / dirty law

```text
model PV        = DIRTY
custodian BT    = CLEAN
calibration     solves clean(OAS) == BT   ⟺   dirty(OAS) == BT + accrued
```

Both forms give the **same root**, because accrued depends only on dates — not on the OAS,
the curve, or any embedded option. That equivalence is unit-tested per engine
(`test_price_convention`, 16 checks), which is what makes it safe to state either way.

Two consequences that are easy to get wrong:

- **there is exactly ONE accrued-interest formula** (`core/pricing/cashflows.accrued_interest`),
  shared by the analytical engine, the FRN engine, the hybrid, the ILB and the lattice. A
  second copy is how this discipline rots;
- **duration, DV01 and convexity divide by the DIRTY price.** Tested both ways against
  custodian AQ on 61 bonds; dirty won 41–20.

## 4. Units

| Layer | Units |
|---|---|
| `assets/` wrappers (the legacy-facing surface) | coupon in **PERCENT**, prices per **100 face**, spreads in **BASIS POINTS**, volatility in **DECIMAL** (0.15 = 15%) |
| `core/` engines | decimals throughout |
| JSON interface | the asset layer's units, and every field name says so |

The wrappers convert; the core never sees percent. A volatility "point" means one
percentage point of volatility (0.01 in decimal), and every sensitivity output names its
unit.

## 5. Currency routes a curve. It is not an FX instruction

A bond is discounted on its **own-currency** curve
(`core.market.curves.resolve_curve` → `ZeroCurve.from_currency`). Portfolio values stay on
the custodian's base-USD columns; nothing self-converts.

**There is no silent USD fallback.** Three failures are distinguished by name because they
mean different things to whoever must fix them:

```text
currency not configured           -> CURVE_NOT_FOUND      (e.g. CHF)
configured, but no row for date   -> CURVE_NOT_FOUND      (e.g. KRW at 2009-03-31)
row exists, bootstrap refuses it  -> CURVE_BUILD_FAILED   (GBP at 2009-03-31: the par
                                                           curve is not arbitrage-free
                                                           at the 3-year node)
```

## 6. OAS is calibrated, never supplied — with one named exception

The operation `calibrate_and_risk` takes the clean market price and **refuses** a supplied
`oas_bp`: a mark and a hand-typed spread can disagree, and there is no principled way to
pick. The separately named operation `price_at_oas` exists for the legitimate
"price this at a spread I choose" case (which is what the legacy per-metric functions did).

The solve is robust rather than clever: price is strictly decreasing in the spread, so the
root is unique; the bracket auto-widens; Brent finds it.

## 7. Migration law

A migration **moves** code; it does not rewrite it.

```text
copy the implementation verbatim      float-operation order is preserved
old path becomes a shim               re-exporting the same objects (asserted by identity)
prove it by hashing whole outputs     not by spot-checking a few numbers
run the full suite after every commit
```

If a frozen output changes, stop and diagnose before continuing. "It is only the last
digit" is exactly the signal that something moved.

## 8. Refuse rather than guess

Every refusal in the codebase marks a place where a silent assumption would produce a
plausible **wrong** number. The current list:

- a date sent as a **number** (an Excel serial). `pandas.Timestamp(39903)` is 1970-01-01, so
  a serial would price the bond on the wrong day, on the wrong curve, with nothing looking
  broken;
- a currency with no usable curve (see §5);
- a put priced above a call on the same date — contradictory terms, no right answer to pick;
- a sinking date coinciding with a call or put date — two rights on one node need an order,
  and no order is tested;
- two sinking redemptions inside one coupon period — the tree resolves exercise on coupon
  dates and would otherwise coarsen the schedule silently;
- an exercise schedule every entry of which falls after maturity — it would quietly price a
  straight bond while the caller believes an option was applied;
- a `fraction_basis` the engine does not implement;
- a coupon above 40 (percent), which is almost always a decimal or bp value in the wrong
  place.

What is **forgiven**, deliberately: lower-case currency, numbers as text, unsorted
schedules, exact duplicate schedule entries (deduped with a warning), missing optional
fields, unknown extra fields (ignored with a warning), a face value other than 100 (echoed,
not applied), and volatility on an instrument that has no use for it (echoed, reported as
not used, with `null` sensitivities — never a fabricated zero).

The dividing line is worth stating in any plan that touches the contract: **leniency is for
presentation; economics are never inferred.**

## 9. Reporting laws

- a number that could not be computed finitely is serialised as `null` with a warning, never
  as a placeholder digit;
- error messages never carry a file path, a traceback, or the client payload. (The curve
  loader's own exception *does* name its data file — the endpoint catches and re-words it);
- every result says which curve produced it (`curve_id` = `USD|2009-03-31|Semiannual`);
- the interface echoes back what it actually ran on (`inputs_used`), so a wrong cell mapping
  is visible without reading Python.

---

## Added 2026-08-30

### Par-yield file units

`data/*_Yield_Curve.txt` are **not uniform**. `GBP_Yield_Curve.txt` and
`DKK_Yield_Curve.txt` store par yields in **PERCENT**; the other 24 store **decimals**.
Declared in `curves.bootstrap.PAR_YIELD_UNITS`, overridable per call with `units=`, and
guarded: any scaled row above 100% raises `ParYieldUnitError` **before** the bootstrap.
Detection was considered and rejected — DKK's median value is 0.543, so a threshold rule
would have been right about GBP by luck. See `14` §1a and `05` §1.9.

### Floating-rate duration has two exact regimes, and the sign flips

Measured on a flat 4% curve, a 30-year note:

| `current_coupon` | effective duration |
|---|---|
| supplied | **+0.104396** = +time to the **next** reset (independent of the coupon's level) |
| projected | **−0.395604** = −time **since** the last reset (the bump reprices that coupon too) |
| *same-maturity fixed bond* | *17.44* |

Both are within one coupon period. A **third** regime applies to a deep-discount note —
price ≈ par − spread annuity, so a rate rise shrinks the gap and the price rises, giving a
negative duration of order spread × annuity duration that **grows with maturity** (a 57-year
note near 50 shows ≈ −10.6). Universal law: `|duration| ≪` a same-maturity fixed bond.

### A schedule crossing the JSON boundary carries units at the boundary, not inside

`coupon_schedule` arrives as `rate_pct` (**percent**, like `coupon_pct`) and is converted to
the engines' decimals in `contracts.py`. That is the only place the two conventions meet.
Inside the asset layer a coupon *schedule* is decimal — the documented single exception to
that layer's percent rule, because the parser and the override CSV both emit decimals, and
two dialects of one object would be worse than one exception. `stepped.validate_schedule`
refuses a percent-looking schedule rather than pricing a 750% coupon.

### The audit echo mirrors the request, not the engine

`inputs_used` echoes per-product inputs in the caller's own shape and units — schedules as
objects with `rate_pct`, not as the engine's decimal tuples. The block exists so a wrong cell
mapping in the spreadsheet is visible without reading Python; an echo in different units would
defeat it. (It is also rounded to 10 dp, because `0.07 * 100` is `7.000000000000001` and an
audit line that does not match the cell it came from is worse than useless.)

### Parity protocol

Windows and server 47 agree for the test suite and the single-bond endpoint JSON, but **full
565-bond driver CSVs differ by up to 3.6e-8 relative, entirely in `convexity`** (a second
difference ÷ bump² amplifies a last-bit rounding by 10⁸). Text columns identical; prices,
spreads and durations agree to ~1e-12. Two local runs are byte-identical to each other, so
**parity is asserted local-fresh vs local-fresh** — byte-exact, and stricter than the
cross-platform comparison it replaces.
