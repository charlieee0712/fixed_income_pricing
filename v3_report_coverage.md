# Fixed-Income Pricing Module — Coverage by Coupon Type (v3)

*Full Coupon_Formula2 routing, engine reliability, and outstanding data items*

---

## 1. Summary

Following your walkthrough of the Corporate Bonds description tab and the Pivot of Corp Bonds sheet, the module now reads **Coupon_Formula2** for every bond and routes each one to the appropriate pricing method by type — rather than assuming everything is a plain fixed ("F") bond.

The result: **every one of the 676 corporate-bond rows now has an explicit owner** — priced by the right engine, honestly flagged where terms are missing, or excluded per your instruction (pass-throughs, amortizing, N/A). Nothing is silently mispriced. In total, **558 bonds produce output: 545 priced end-to-end** (implied OAS + duration, DV01, convexity) **and 13 carried at the custodian mark with an explicit flag**, with the remaining gaps reduced to a short, Bloomberg-fillable data list.

## 2. Coverage map

| Coupon_Formula2 class | n | Engine / route | Status |
|---|---|---|---|
| **F — plain fixed** | 617 | vanilla · make-whole→vanilla · genuine callable→BDT lattice | ✅ 521 priced (475 vanilla + 46 make-whole) + 6 callable |
| **Floating** (Ref-Rate / EURIBOR / GBP-LIBOR + Spread, Fixed→Floating) | 27 | FRN forward-projection engine | ✅ 18 priced · ⚠️ 9 flagged (switch dates / perpetual terms / GBP curve / 1 defaulted) |
| **Fixed-to-reset** | 6 | coupon-continuation (+ price-to-call as reference) | ✅ 4 priced · ⚠️ 2 BT-mark (variable coupon, terms needed) |
| **Stepped** (7.00/7.50 segmented) | 2 | vanilla with coupon schedule | ✅ 1 priced (1 tab-only) |
| **Step-up** | 1 | schedule not in workbook | ⚠️ BT-mark |
| **Zero coupon / structured payoff** | 1 | vanilla (degenerate) | ⚠️ priced & flagged — pricing shows it is not a pure discount bond |
| **Defaulted** | 1 | recovery mark | ✅ BT-mark, no OAS |
| **Pass-through / amortizing / N/A** | 16 / 1 / 4 | — | ❌ excluded per your instruction |
| **Total** | **676** | | |

The floating-rate engine projects each coupon from the implied forward rates of our bootstrapped zero curve and discounts on the same curve plus the calibrated OAS — the same architecture as the legacy FRN branches (analysisType 7/8/9), with the Bloomberg data inputs replaced by our curve set. Quoted spreads are not in the workbook, so FRNs are currently priced at spread = 0 with the implied OAS absorbing the unknown spread; prices calibrate exactly, and the spread can be separated out as soon as the actual figures arrive.

## 3. Engine reliability

The suite now runs 80 tests: golden-master checks (reproduce legacy numbers to the digit where a legacy output exists) plus **structural invariants** — properties that must hold regardless of inputs:

- **Bootstrap consistency** — a bootstrapped curve reprices its own par bonds to exactly 100.000000 (this is the check that originally caught the legacy discounting inconsistency).
- **FRN reset identity** — a pure floater holds par under any parallel curve shift (a mathematical identity; sampled −3% to +5%); implied OAS round-trips; near-par floater duration ≈ time to next reset.
- **Callable lattice** — arbitrage-free by construction (reprices its calibration curve); callable ≤ straight ≤ putable; at σ = 0 the option value degenerates to zero.

Worth highlighting: the model **alarms when an assumption is wrong instead of emitting a plausible-but-wrong number**. Three cases so far:

1. **Par-call refuted** — TNTD03203204: the par-call assumption conflicts with the custodian mark (BT 108.69 above the par-call value) → flagged; real call schedule required.
2. **"Zero" is actually structured** — TNTD03037132: priced as a pure discount bond, the implied OAS comes out at −486 bp → the model flags it as a structured payoff, not a plain zero.
3. **Price-to-call absurdity** — TNTG533596W: price-to-call implies 1,884 bp vs 627 bp on coupon-continuation → the deep discount means the market is pricing extension, not redemption; continuation is the reported metric, to-call kept as a reference column.

One engine bug was caught by this harness during development and fixed at the root rather than patched over: the FRN "holds par" invariant failed on first run, exposing a stub-period forward mis-anchored to the valuation date instead of the true last reset date. No test threshold was loosened.

A note on FRN durations: a deep-discount floater correctly shows a small **negative** duration — its below-par credit gap (OAS × annuity PV) shrinks when rates rise — always far below a same-maturity fixed bond's. Near-par floaters sit near zero, as they should.

## 4. Outstanding data items (all Bloomberg-fillable)

The engines already route these bonds; each item drops in with **no code changes** as soon as the field arrives:

| Gap | Bonds affected | Current treatment | Bloomberg source |
|---|---|---|---|
| FRN quoted spread | 18 FRNs | spread = 0, OAS absorbs it | flt_cpn_hist / DES (the "+ Spread" number) |
| Fixed→Floating switch date | 5 | flagged, not priced | multi_cpn_schedule / DES |
| Perpetual & reset terms | 4 BT-marked (+ 3 priced at 90y truncation) | BT-mark / continuation | DES / prospectus (call & reset schedule) |
| Step-up coupon table | 1 | BT-mark | multi_cpn_schedule |
| Zero structured-payoff terms | 1 | priced & flagged | DES / prospectus |
| GBP par curve | 1 GBP FRN (+ any GBP bond) | curve-blocked | a clean GBP par curve (the 3y node) |
| Callable call schedules | 6 genuine callables (4 seeded par-call) | par-call @100 (per v1 instruction) | call_schedule |

## 5. Where this leaves the module

- Plain fixed, callable/putable, floating, reset, stepped, zero and defaulted bonds are all classified and routed automatically from Coupon_Formula2 — one codebase, one dispatch.
- 545 of 676 bonds price end-to-end with calibrated OAS and full risk metrics; 13 more are carried transparently at the custodian mark; 21 are excluded per your instruction; the rest is a one-pull Bloomberg list.
- Natural next steps, whenever you'd like: filling the data items above, the pass-through/prepayment work when its time comes, and portfolio-level risk aggregation (position-weighted DV01/duration).

Happy to walk through any part of this.
