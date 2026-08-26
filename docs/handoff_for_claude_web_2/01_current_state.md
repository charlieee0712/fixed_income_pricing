# Current state — every workstream, with numbers

**As of 2026-08-25, repo at `68ebfef`, 223 tests green, working tree clean.**

---

## 1. The one-paragraph version

The legacy Excel/VBA fixed-income toolkit has been re-implemented in Python. Corporate bonds
are fully priced and risk-measured; agencies, guaranteed and inflation-linked bonds are
priced; mortgages await data. The code has been restructured into the layout Mario asked for
(`core/` engines, `assets/` thin per-type wrappers, `endpoints/` transport) and Mario has
approved that structure. A spreadsheet can now call the engine: one JSON request in, one
JSON answer out, tested on real Excel. Callable, puttable and sinking-fund bonds price on
one shared tree. Floating-rate notes and the endpoint dispatch for the new types are next
week.

## 2. Pricing coverage

**Corporate bonds** — output **564 = 553 priced end-to-end + 11 flagged** at the 2009-03-31
baseline (559 = 548 + 11 at the 2009-06-10 control). Routes actually produced by the
production driver at 3-31:

```text
vanilla                    480      make-whole-as-vanilla        47
hybrid (fixed-then-float)   10      vanilla-schedule              9
hybrid-margin-unavailable    8      floating (FRN)                7
recovery                     2      frn-curve-blocked             1
```

**Phase 2** — agencies 42→**39** priced (median 121 bp; 5 on the callable lattice, 4
call-passed, 2 zero-coupon STRIPS, 1 REMIC tranche BT-marked), guaranteed FDIC-TLGP 11→**9**
(own bucket, median 86 bp), inflation-linked 16→**15** (spread reported in its own column as
approximately minus the breakeven). Government MBS 888 — engine skeleton built against the
exact 8-mnemonic Bloomberg interface, waiting on the data pull.

**Callable on the tree** — 3 corporate (one EUR) + 5 agency. A fourth corporate
(`TNTD04923866`, AssuredGty) is waiting on its call schedule, which is on the outstanding
Bloomberg request.

## 3. Code structure

```text
src/pricer/
├── core/        the mathematics
│   ├── pricing/    cashflows · discounting · analytical (plain bonds) · tree (options)
│   ├── risk/       sensitivities — engine-agnostic bump-and-reprice
│   ├── market/     curves (incl. resolve_curve) · spreads (OAS calibration)
│   └── utils/      dates (the 364/182 calendar)
├── assets/corporate/   bonds_input · vanilla · embedded_option · callable · puttable · sinking
└── endpoints/          main · contracts · pricing · dependencies

src/pricing/     the ORIGINAL module paths — now thin shims. Nothing that used them broke.
src/curves/ src/credit/ src/dataio/ src/recon/     not yet migrated; still the real code
scripts/         drivers + price_json.py + md_to_pdf.py + demo_volatility.py
integrations/excel_vba/    bridge · vendored VBA-JSON · tests · demo workbook
```

Migration status: the vanilla chain and the option tree are inside `pricer/`. FRN, hybrid,
ILB, MBS, the lattice's data loaders, curves, credit and dataio are **not yet migrated** and
are reached through their original paths.

## 4. This week in detail

### 4a. Mario's three follow-up points — all answered

| His point | What was built |
|---|---|
| "Add currency to our input" | `currency` is input 5 of the catalogue and selects the bond's **own-currency** curve. No silent USD fallback: an unmapped currency, a missing date and an unbuildable curve are three separately named refusals. |
| "What happens if yield volatility changes — for OAS and price?" | Answered as **two separate experiments** (price at fixed spread; spread at fixed price). Vanilla returns *not applicable* with `null` — never a fabricated zero. Callable/puttable/sinking now return real numbers. |
| "Can the team run Python from Excel — one JSON in, one JSON out?" | Built and tested end to end on real Excel: 23/23 checks including a live Python round trip, plus a demonstration workbook. |

### 4b. Round 2a — one shared tree

The validated BDT lattice moved **verbatim** into `pricer/core/pricing/tree.py`;
`pricing/lattice.py` is now a shim re-exporting the same object. Three thin wrappers sit on
it. The only new modelling is the sinking fund: issuer optional redemption of a fraction of
the amount **outstanding**, one node rule applied where the call cap already fires.

Deliberately deferred to **Round 2b (next week)**: the FRN migration, the floating wrapper,
and the endpoint dispatch for the new instrument types — grouped so one contract change
covers callable, puttable and floating together.

### 4c. The volatility numbers

On the portfolio's one genuinely call-active holding (6.45% of 2034-06-15, marked 90.0426,
callable from 2014-08-16 at par):

| Volatility | Price at the fixed 410.77 bp spread | Spread at the fixed 90.0426 price |
|---|---|---|
| 10% | 90.4229 | 414.52 bp |
| **15% (baseline)** | **90.0426** | **410.77 bp** |
| 20% | 89.5161 | 404.84 bp |

≈ 10 cents of price, or ≈ 1 bp of spread, per volatility point. The other two callables are
priced far from their call (one marked at 60) and move by **under a tenth of a basis
point** — which is why a single portfolio-level vega would be misleading and the module
reports per bond.

## 5. Test suite

**223 checks.** Composition:

```text
pre-existing engine + data suite     194   (bootstrap, ratings, universe, oas, lattice,
                                            frn, hybrid, ilb, mbs, coupon schedules,
                                            phase-2 universe, price convention, ...)
vanilla JSON endpoint                 28   parity with `==`, the firm rules, leniency, CLI
embedded-option tree                  29   migration identity, one-tree invariants, sinking
```

Plus **23 Excel bridge checks** driven through real Excel (not counted in the 223 — they are
a PowerShell script, not pytest).

## 6. What is blocked, and on what

| Blocked | Waiting on |
|---|---|
| MBS pricing | the 8-mnemonic × 882-CUSIP Bloomberg pull (requested 2026-07-22) |
| Pass-through / amortising bonds (13 securities) | their amortisation schedules |
| 3 exempt US FRNs, 8 hybrid margins | the 11-security Bloomberg list (sent 2026-07-20) |
| 1 callable (`TNTD04923866`) | its call schedule (on Liping's 2026-07-30 request) |
| 2 GBP bonds | a usable GBP curve — the current file is not arbitrage-free at the 3y node |
| KTBi indexation | terms + a KRW curve row for 2009-03-31 |

None of these blocks Round 2b.

## 7. Immediate next steps

1. **Round 2b**: migrate FRN into `core/pricing/floating.py` behind a shim, add the floating
   wrapper, and extend the endpoint with `instrument_type` for callable / puttable /
   floating in one change. The hybrid engine must stay bit-identical throughout.
2. The user briefs Mario and the Google team from `docs/weekly_report_2026-08-25.md`, using
   the demo workbook and the 15-minute walkthrough.
3. When Mario returns the MBS data, the deferred asks (KTBi terms, agency call schedules,
   the rating quirk) go with that touchpoint — not before.
