# Current state and open items

**2026-08-25 · `68ebfef` · 223 tests green · clean tree.** Deeper versions of everything
below are in handoff 2 (`01`, and the per-domain files `10`–`22`).

---

## 1. The delta since 2026-08-17

Two rounds shipped, both on 2026-08-25.

### Round 1 — Mario approved the sample, and his three follow-ups are built

| His point | Answer |
|---|---|
| "Add currency to our input" | `currency` is an explicit input and selects the bond's **own-currency** curve. No silent USD fallback: an unmapped currency, a missing date and an unbuildable curve are three separately named refusals. |
| "What happens if yield volatility changes — for OAS and price?" | Answered as **two separate experiments** (price at a fixed spread; spread at a fixed price). A plain bond returns *not applicable* with `null` — never a fabricated zero. |
| "Can the team run Python from Excel — one JSON in, one JSON out?" | Built and tested end to end on real Excel: 23/23 checks including a live Python round trip, plus a demonstration workbook that prices a bond in about two seconds. |

Delivered: `pricer/endpoints/` (one transport-independent entry point), `scripts/price_json.py`,
`integrations/excel_vba/` (a thin bridge, vendored VBA-JSON, real fixtures, tests, and the
demo). 166 → 194 tests.

### Round 2a — three more bond types on one shared engine

The validated lattice moved **verbatim** into `pricer/core/pricing/tree.py` (the old path is
a shim) and now serves **callable, puttable and sinking-fund** bonds from one engine. The
only new modelling is the sinking fund: issuer optional redemption of a fraction of the
amount **outstanding**, one node rule applied where the call cap already fires. 194 → 223
tests; the three production driver CSVs are byte-identical throughout.

**FRN was deliberately moved to Round 2b (next week)**, together with the endpoint dispatch
for the new types — one contract change then covers callable, puttable and floating.

### The volatility numbers

On the one genuinely call-active holding (6.45% of 2034, marked 90.0426, callable 2014 at par):

| Volatility | Price at the fixed 410.77 bp spread | Spread at the fixed price |
|---|---|---|
| 10% | 90.4229 | 414.52 bp |
| **15% (baseline)** | **90.0426** | **410.77 bp** |
| 20% | 89.5161 | 404.84 bp |

≈ 10 cents of price or ≈ 1 bp of spread per volatility point. The other two callables are
priced far from their call and move by **under a tenth of a basis point** — which is why a
single portfolio-level vega would mislead.

### One finding that constrains future validation

All **474** callable / puttable / sinking rows in the Monthly workbook sit in the
**2010-03-01 stale batch**; not one is in the sound 2012-12 cohort. There is therefore **no
numeric golden** for any of this round's families, and none was manufactured. Validation is
production parity + `==` direct-call parity + invariants + the Bloomberg three-way.

## 2. Where everything stands

**Corporates** — 564 at 3-31 = 553 priced + 11 flagged. Routes: vanilla 480 ·
make-whole-as-vanilla 47 · hybrid 10 · vanilla-schedule 9 · hybrid-margin-unavailable 8 ·
floating 7 · recovery 2 · frn-curve-blocked 1.

**Phase 2** — agencies 39 priced (5 on the lattice), guaranteed TLGP 9, index-linked 15.
Govt MBS 888: engine skeleton built to the exact Bloomberg interface, awaiting the pull.

**Code** — the vanilla chain and the option tree are inside `pricer/`; FRN, hybrid, ILB,
MBS, curves, credit and dataio are not yet migrated and are reached through their original
paths, which all still work via shims.

## 3. Open items

**Awaiting Mario** — the 11-security Bloomberg list (sent 07-20); the Govt-MBS 8-field ×
882-CUSIP pull (sent 07-22); the weekly report and refreshed Drive folder (the user sends
next). Two questions inside the report: which workbook should carry the Excel demo, and
whether the rollout order still holds.

**Awaiting Liping** — the full gap request of 07-30 (MBS, pass-through terms for 13 uniques,
the 11-security list, and the AssuredGty call schedule).

**Deferred on purpose — do not re-ask** until Mario returns the MBS data: KTBi indexation
terms and a KRW curve row, agency call schedules (confirmation only), the `TNTD04366584`
rating quirk, the lost SteepFlat twist table, and a usable GBP curve.

**Next** — Round 2b: migrate FRN into `core/pricing/floating.py` behind a shim, add the
floating wrapper, and extend the endpoint with `instrument_type`. One hazard to plan for:
`hybrid.py` imports **private** names from `frn.py` (`_as_date`, `_df`, `YEAR_DAYS`,
`simple_forward`), so the shim must re-export them or the hybrid engine breaks on import.
