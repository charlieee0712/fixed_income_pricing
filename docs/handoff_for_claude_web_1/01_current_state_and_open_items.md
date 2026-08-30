# Current state and open items

**2026-08-30 · `a5f7c81` · 287 tests green · clean tree.** Deeper versions of everything
below are in handoff 2 (`01`, and the per-domain files `10`–`22`).

---

## 1. The delta since 2026-08-25

### How the work arrived — worth knowing, because it changes the shape of the ask

There was **no execution plan this round.** At the meeting, Mario worked down the coupon-type
pivot on the holdings workbook (`Pivot of Corp Bonds`) and annotated a **new column F**:
`finished` against the plain-fixed row (617), `just corp bond(fixed)` against the zero row,
and **`no` against six rows** — F12, F13, F14, F15, F16, F20. That column *is* the ask. It is
now committed, because it is the only record of what was requested and when.

He also agreed to the next-week plan you had seen (floating + endpoint dispatch), and the six
cells largely *are* that plan, widened.

### The interpretation that decided the work

"Finished" cannot mean "priced" — every one of those coupon families has priced in the legacy
layer since July. It means **"in the restructured `pricer/` package Mario's team takes over"**,
which is exactly what F5 describes: the approved sample was the vanilla chain. So the six
cells = the three coupon families not yet migrated, and the deliverable = migration + numbers
+ a cell-by-cell status table. Both readings are satisfied by doing that, so the ambiguity did
not have to be resolved before starting.

### The six cells

| Cell | Coupon type | Pivot rows | Held | Priced |
|---|---|---|---|---|
| F12 | Fixed → Floating | 5 | 5 | 4 |
| F13 | 7.00% / 7.50% date-segmented | 2 | 1 | 1 |
| F14 | GBP LIBOR + Spread | 1 | 1 | **1** |
| F15 | Reference Rate + Spread | 12 | 12 | 11 |
| F16 | EURIBOR + Spread | 9 | 9 | 5 |
| F20 | Step-up schedule | 1 | 1 | 1 |
| | **total** | **30** | **29** | **23** |

The six unpriced: **5 awaiting post-switch margins** already on the Bloomberg list (a fill is
one CSV cell, zero code change) + **1 defaulted** bond at its recovery mark. Rows 6–11
(`Fixed → Reset`, 6 tab / 6 held / 3 priced) share the hybrid engine and came free — adjacent,
not part of his ask.

⚠️ **Three denominators, easy to confuse:** 676 = tab rows · 565 = held/rated/matched
positions @3-31 · 555 = of those, fully priced. Row 13 is the live example: 2 tab rows, 1 held.

### What shipped

- **Three engines migrated verbatim** into `pricer/core/pricing/{floating,hybrid,coupon_schedule}.py`;
  old paths are shims. Closed a real layering violation on the way: `core/pricing/cashflows.py`
  had been importing from the legacy `pricing` package.
- **Three thin wrappers** `assets/corporate/{floating,hybrid,stepped}.py`.
- **One endpoint contract change covering all seven products** (`bond.instrument_type`:
  vanilla · stepped · floating · fixed_to_floating · callable · puttable · sinking). Doing
  floating now and the tree types later would have meant two contract changes — which is what
  deferring dispatch to this round was meant to avoid. A typeless payload is still vanilla, so
  the Excel bridge and its 23 real-Excel checks pass unchanged (re-run and verified).
- 223 → **287** tests.

## 2. ⭐ The GBP curve was never missing — and it cost us two months

We had told Mario the single sterling bond could not be priced because our UK curve "was not
arbitrage-free", and we had a Bloomberg request open for a replacement curve.

**The market-data files are not uniform.** 24 of 26 `*_Yield_Curve.txt` store par yields as
decimals; **GBP and DKK store percentages**. The loader multiplied every file by 100, turning
the 2009-03-31 gilt curve into a 73%–415% par curve — which the bootstrap then *correctly*
refused, reporting the only thing it could see. **We read its complaint as a fact about the
data.** The raw row reads `0.731 / 1.183 / 2.341 / 3.157 / 4.157`: that day's gilt market,
in percent.

| | Before | Now |
|---|---|---|
| France Télécom GBP 7.50% 2011 (F14) | not priced | **205.31 bp**, duration 1.86 y |
| A UK EMTN fixed 5.50% 2033 | **absent from the output** | **197.30 bp**, duration 12.55 y |
| Corporate rows @3-31 | 564 | **565** (priced 553→555, flagged 11→10) |

**The second bond is the part that generalises.** It was not flagged — it was silently
**skipped** — and it is a plain `Fixed` bond, i.e. inside the class already reported complete.
A completeness count was wrong in a direction no report surfaced. The driver header now reads
`skipped=0`.

Cross-check: the same bond is 279.93 bp on the USD curve and 197.30 on its own; the ~83 bp gap
*is* the gilt-vs-Treasury difference at 24 years — two independently computed numbers agreeing.

Fixed with an **explicit per-file registry** (`curves.bootstrap.PAR_YIELD_UNITS`), not a
sniffer — no threshold separates a 0.5% Danish yield from a 0.5 decimal, and DKK would have
been luck — plus a guard that raises before the bootstrap when a scaled row exceeds 100%.

**The GBP request is withdrawn.** Do not re-raise it. The registry rule it produced:
*an entry whose only evidence is one of our own error messages is not yet a data gap.*

## 3. Where everything stands

**Corporates @3-31** — 565 rows = 555 priced + 10 flagged. Routes: vanilla 481 ·
make-whole-as-vanilla 47 · vanilla-schedule 10 · hybrid 10 · hybrid-margin-unavailable 8 ·
floating 7 · recovery 2. **`frn-curve-blocked` is now empty.**

**Phase 2** — agencies 39 priced (5 on the lattice), guaranteed TLGP 9, index-linked 15.
Govt MBS 888: engine skeleton built to the exact Bloomberg interface, awaiting the pull.

**Code** — the vanilla chain, the option tree, floating, hybrid and the coupon-schedule
engine are inside `pricer/`. ILB, MBS, curves, credit and dataio are not yet migrated and are
reached through their original paths, which all still work.

## 4. Open items

**Awaiting Mario** — the 11-security Bloomberg list (sent 07-20); the Govt-MBS 8-field ×
882-CUSIP pull (sent 07-22); the 08-30 report and refreshed Drive folder (the user sends
next). **One question is outstanding inside that report: how he wants the extra bond types
laid out on the demonstration spreadsheet** — one sheet with a type dropdown, or one small
sheet per type. It is a couple of hours either way; it is his team's daily view, so it is
his call.

**Awaiting Liping** — the full gap request of 07-30 (MBS, pass-through terms for 13 uniques,
the 11-security list, the AssuredGty call schedule). **The GBP curve is no longer on it.**

**Deferred on purpose — do not re-ask** until Mario returns the MBS data: KTBi indexation
terms and a KRW curve row, agency call schedules (confirmation only), the `TNTD04366584`
rating quirk, the lost SteepFlat twist table.

**Not done, deliberately** — the Excel bridge still sends plain bonds only. The engine and
the message contract handle all seven types; the worksheet layout is the open question above.

**Next** — mortgages remain the largest block and are waiting on data, not on us. The
demonstration sheet for the new types follows Mario's answer.
