# Current state and open items

**2026-08-30 · `23da147` · 287 tests green · clean tree, origin and 47 in sync.**

This file is meant to be enough to plan from on its own. Where you need module-level
internals — engine mathematics, the code map, the Monthly reconciliation in depth — that is
handoff 2.

---

## 0. The project in six lines

A legacy Excel/VBA fixed-income pricing toolkit is being ported to a structured Python module
for a US pension portfolio (URS, valuation date **2009-03-31**, control **2009-06-10**).
Corporate bonds are the reference implementation; agencies, guaranteed paper and
inflation-linked bonds are priced; mortgages are built to an exact data interface and waiting
on data. Since 2026-08-15 the work is also shaped by **Mario's restructuring directive** — the
code passes to a Google cloud team, so it must be many simple functions with inputs
highlighted, per his template. **OAS is a per-bond calibration output, not a pricing input**:
we solve the spread that makes the model's clean price equal the custodian's mark, then
compute risk on the calibrated model. Two clients exist in the legacy workbooks — **URS**
(the target) and **Uganda** (a UGX demo). Never merge them.

## 1. The delta since 2026-08-25

### How the work arrived — this matters for how you plan

There was **no execution plan this round.** At the meeting Mario worked down the coupon-type
pivot on the holdings workbook (`Pivot of Corp Bonds`) and annotated a **new column F**:
`finished` against the plain-fixed row (617 rows), `just corp bond(fixed)` against the zero
row, and **`no` against six rows** — F12, F13, F14, F15, F16, F20. That column *is* the ask.
It is now committed with the workbook, because it is the only record of what was requested.

**This client gives directives by annotating spreadsheets.** Check the workbook's diff after a
meeting. He separately agreed the next-week plan you had seen (floating + endpoint dispatch),
and the six cells largely *are* that plan, widened.

### The interpretation that decided the work

"Finished" cannot mean "priced" — every one of those coupon families has priced in the legacy
layer since July. It means **"in the restructured `pricer/` package Mario's team takes over"**,
which is exactly what the plain-fixed row describes: the approved sample was the vanilla chain.
So the six cells = the three coupon families not yet migrated.

Worth imitating: the execution side did **not** stop to ask about the ambiguity, because it
first checked whether the two readings diverge in what they imply. They don't — migrate the
engines, produce the numbers, hand back a cell-by-cell table, and both are satisfied. Test
that before escalating an ambiguity; it often costs a day for nothing.

### The six cells

| Cell | Coupon type | Pivot rows | Held | Priced |
|---|---|---|---|---|
| F12 | Fixed → Floating | 5 | 5 | 4 |
| F13 | 7.00% / 7.50% date-segmented | 2 | 1 | 1 |
| F14 | GBP LIBOR + Spread | 1 | 1 | 1 |
| F15 | Reference Rate + Spread | 12 | 12 | 11 |
| F16 | EURIBOR + Spread | 9 | 9 | 5 |
| F20 | Step-up schedule | 1 | 1 | 1 |
| | **total** | **30** | **29** | **23** |

The 6 unpriced = **5 awaiting post-switch margins** (already on the Bloomberg list; a fill is
one CSV cell and zero code change) + **1 defaulted** bond at its recovery mark. Rows 6–11
(`Fixed → Reset`, 6 tab / 6 held / 3 priced) share the hybrid engine and came free — adjacent,
not part of his ask.

⚠️ **Three denominators, and they are easy to confuse.** 676 = rows on the Corporate Bonds
tab · 565 = held/rated/matched positions in the output @3-31 · 555 = of those, fully priced.
Row F13 is the standing illustration: 2 tab rows, only 1 of them a live holding.

### What shipped

- **Three engines migrated verbatim** into `pricer/core/pricing/{floating,hybrid,coupon_schedule}.py`;
  old paths are shims. A live layering violation closed on the way (`core/pricing/cashflows.py`
  had been importing from the legacy `pricing` package — core reaching upward).
- **Three thin wrappers** `assets/corporate/{floating,hybrid,stepped}.py`, so the asset layer
  is now seven products: vanilla · stepped · floating · hybrid · callable · puttable · sinking.
- **One endpoint contract change covering all seven** (`bond.instrument_type`). Doing floating
  now and the tree types later would have meant two contract changes — which is precisely what
  deferring dispatch to this round was meant to avoid. A typeless payload is still vanilla, so
  the Excel bridge and its 23 real-Excel checks pass unchanged (re-run, not assumed).
- 223 → **287** tests.

## 2. ⭐ The GBP curve was never missing — and it cost two months

We had told Mario the single sterling bond could not be priced because our UK curve "was not
arbitrage-free", and we had a replacement-curve request open against **both** Bloomberg
channels.

**The market-data files are not uniform.** 24 of 26 `*_Yield_Curve.txt` store par yields as
decimals; **GBP and DKK store percentages**. The loader multiplied every file by 100, turning
the 2009-03-31 gilt curve into a 73%–415% par curve — which the bootstrap then *correctly*
refused, reporting the only thing it could see. **We read its complaint as a fact about the
data.** The raw row reads `0.731 / 1.183 / 2.341 / 3.157 / 4.157`: that day's gilt market, in
percent.

| | Before | Now |
|---|---|---|
| France Télécom GBP 7.50% 2011 (F14) | not priced | **205.31 bp**, duration 1.86 y |
| A UK EMTN fixed 5.50% 2033 | **absent from the output** | **197.30 bp**, duration 12.55 y |
| Corporate rows @3-31 | 564 | **565** (priced 553→555, flagged 11→10) |

**The second bond is the part that generalises.** It was not flagged — it was silently
**skipped** — and it is a plain `Fixed` bond, i.e. inside the class already reported complete.
A completeness count was wrong in a direction no report surfaced. The driver header has been
printing `skipped=1` for months with nobody reading it; it now reads `skipped=0`.

Cross-check that the new numbers are right: the same bond prices at 279.93 bp on the **USD**
curve against 197.30 on its own, and the ~83 bp gap *is* the gilt-vs-Treasury difference at 24
years — two independently computed numbers agreeing.

Fixed with an **explicit per-file registry** (`curves.bootstrap.PAR_YIELD_UNITS`), not a
sniffer — no threshold separates a 0.5% Danish yield from a 0.5 decimal, and DKK would have
been right by luck — plus a guard raising **before** the bootstrap when a scaled row exceeds
100%. **The GBP request is withdrawn. Do not re-raise it.** Full forensics and the rule it
produced: `12_traps_and_plan_feedback.md`.

## 3. Pricing coverage — where every bond stands

**Corporates @ 2009-03-31** (`outputs/implied_oas_2009-03-31.csv`, **565 rows**):

| route | n | what it means |
|---|---|---|
| `vanilla` | 481 | plain fixed bullet |
| `make-whole-as-vanilla` | 47 | call at treasury+spread ⇒ economically non-callable |
| `vanilla-schedule` | 10 | a known coupon path (stepped / step-up / documented overrides) |
| `hybrid` | 10 | fixed-then-floating, main column + a price-to-switch reference |
| `hybrid-margin-unavailable` | 8 | structure documented, post-switch margin not public ⇒ carried at the mark |
| `floating` | 7 | FRNs |
| `recovery` | 2 | defaulted, carried at the mark, no spread |
| | **555 priced + 10 flagged** | |

`frn-curve-blocked` is **empty**. Callable bucket: 5, of which 3 price on the lattice and 1
awaits a call schedule. At 6-10 the same shape gives 560 rows = 550 + 10.

**Phase 2** — agencies **39** (27 vanilla / 5 callable-lattice / 4 call-passed / 2 zero /
1 CMO-tranche BT-marked), guaranteed TLGP **9** (own bucket, never bank credit buckets),
index-linked **15** (spread vs the nominal curve in its **own column** — it is ≈ minus a
breakeven, never to be mixed with credit OAS).

**Govt MBS 888** — `pricing/mbs.py` is a static-CPR skeleton built to the exact 8-mnemonic
Bloomberg interface. Data lands ⇒ zero code change.

**Excluded per Mario, permanently:** amortizing 1, N/A 4. **Excluded pending data:**
pass-through 16 tab rows (13 unique securities).

## 4. Code structure — what is migrated and what is not

Inside `src/pricer/` (Mario's template layout, sample approved 2026-08-25):

```text
core/pricing/    analytical  cashflows  discounting  tree  floating  hybrid  coupon_schedule
core/risk/       sensitivities
core/market/     spreads  curves
core/utils/      dates
assets/corporate/  bonds_input  vanilla  stepped  floating  hybrid
                   embedded_option + callable / puttable / sinking
endpoints/       main  contracts  pricing  dependencies
```

**Not yet migrated**, reached through their original paths (all still working): `pricing/ilb.py`,
`pricing/mbs.py`, `curves/`, `credit/`, `dataio/`. Every migrated module left a **shim** at its
old path, so no driver, script or test changed at any point.

**The migration law**, which any plan touching this must respect: move code **verbatim**
(the body below the docstring is asserted byte-identical), leave a shim, keep the full suite
green at every step, and prove production outputs unchanged by hashing whole files. New code
imports `pricer.*`, never the shims.

## 5. Open items — who owes what

### Awaiting Mario

| what | sent | unblocks |
|---|---|---|
| 11-security Bloomberg list (3 exempt US FRNs all-terms · 8 hybrid margins) | 2026-07-20 | 8 flagged hybrids ⇒ each is **one CSV cell** |
| Govt-MBS 8 fields × 882 CUSIPs | 2026-07-22 | the whole 888-row MBS class |
| the 08-30 report + refreshed Drive package | the user sends next | — |

### ⭐ The one live question back to Mario

**How should the extra bond types appear on the demonstration spreadsheet?** One sheet with a
bond-type dropdown that shows/hides each type's fields, or one small sheet per type. This is
**the only thing blocking us on the Excel side**: the engine and the message contract already
handle all seven types, so it is purely layout — a couple of hours either way — and it is his
team's daily view, so it was deliberately posed as his call.

*Closed by the 08-27 meeting:* which workbook carries the demo (the small demonstration
workbook stands; the authoritative holdings file is never touched), and whether the rollout
order still holds (yes — and he refined it himself by marking the six cells).

### Awaiting Liping (second Bloomberg channel, campus access)

Full gap request sent 2026-07-30: MBS 8×882 with a BDP template, pass-through terms for 13
uniques, the 11-security list, and the AssuredGty `US04622DAA90` call schedule (the unpriced
5th corporate callable). **The GBP curve is no longer on it.** If she returns one anyway, it
is a **cross-check**, not a fix. Dedupe Mario/Liping returns before loading.

### Deferred on purpose — do NOT re-ask before Mario returns the MBS data

- KTBi indexation terms + a KRW 2009-03-31 curve row (one $1.2M position, BT-marked, nothing
  downstream depends on it);
- agency call schedules — **confirmation only**, the par-call lattice already matches the
  custodian's duration on 4 of 5;
- the `TNTD04366584` A/Aa2 rating quirk;
- the lost `SteepFlat Table Monthly.txt` (only needed when the twist columns are opened).

### Not done, deliberately

The Excel bridge still sends **plain bonds only**. Engine and contract do all seven types;
the worksheet layout is the question above.

## 6. Test suite and what counts as evidence

**287** tests, ~21 s locally, ~34 s on server 47. Plus **23 checks driving real Excel**
(`Run-BridgeTests.ps1`), outside pytest and run deliberately.

There is **no numeric golden** for the tree or floating families — all 474 relevant rows in the
legacy Monthly workbook sit in the 2010-03-01 batch, which was diagnosed in August as an
unusable stale run. So the accepted evidence, in descending strength, is:

1. **production parity by hash** — all five driver CSVs byte-identical to a pre-change
   baseline, after **every** code-bearing commit, not just at the end;
2. **`==` parity** — every wrapper and endpoint result equals the direct engine call exactly.
   Not a tolerance: a tolerance permits a second, drifting implementation;
3. **shim identity on the object** (`a is b`, not `a == b`);
4. **invariants with at least one exact anchor** — e.g. retiring *all* of a sinking bond
   equals calling it, bit for bit.

⚠️ **Parity is compared local-fresh vs local-fresh.** Windows and 47 agree for the test suite
and the single-bond endpoint JSON but **not** byte-for-byte for the 565-bond driver CSVs: up to
**3.6e-8 relative, entirely in `convexity`** (a second difference ÷ bump² amplifies a last-bit
rounding by 10⁸). A cross-platform hash diff shows a difference that is **not** a regression.

## 7. Immediate next steps

1. The user sends the 08-30 report and the Drive package to Mario.
2. Mario answers the layout question → the demonstration sheet gains the new bond types.
3. **Mortgages** when the pool data lands — the largest remaining block, and not blocked on us.
4. Remaining migrations (`ilb`, `mbs`, `curves`, `dataio`) follow the same verbatim-move law
   whenever they are scheduled; none is urgent.
