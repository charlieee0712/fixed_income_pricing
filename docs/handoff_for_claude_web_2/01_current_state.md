# Current state

**2026-08-31 · `44e65fe` · 390 tests green · clean tree, origin and 47 in sync.**

---

## 1. The one-paragraph version

A legacy Excel/VBA fixed-income pricing toolkit is being ported to a structured Python
module. Corporate bonds are the reference implementation and are essentially complete;
agencies, guaranteed paper and inflation-linked bonds are priced; mortgages are built to an
exact interface and waiting on data. Since 2026-08-15 the work has been driven by Mario's
directive to restructure the code for a Google cloud team — many simple functions, inputs
highlighted — and the restructuring now covers every corporate coupon family except the ones
explicitly excluded. Numbers do not change when code moves: that is proven by hashing whole
production output files before and after every step.

## 2. Pricing coverage

**Corporates @ 2009-03-31** (`outputs/implied_oas_2009-03-31.csv`, **566 rows**):

| route | n | note |
|---|---|---|
| `vanilla` | 481 | plain fixed |
| `make-whole-as-vanilla` | 47 | call at treasury+spread ⇒ economically non-callable |
| `vanilla-schedule` | 10 | known coupon paths (incl. the GBP 7.50% unblocked this round) |
| `hybrid` | 10 | fixed-then-floating |
| `hybrid-margin-unavailable` | 8 | structure documented, post-switch margin not public |
| `floating` | 7 | FRNs |
| `recovery` | 2 | defaulted, carried at the mark |
| | **555 priced + 10 flagged** | |

`frn-curve-blocked` is **empty** and the driver header reads `skipped=0` (was 1). Callable
bucket: 5, of which 3 price on the lattice and 1 awaits a call schedule.

**Phase 2** — agencies 39 (5 on the lattice), guaranteed TLGP 9, index-linked 15.
**Govt MBS 888** — engine skeleton on the exact 8-mnemonic Bloomberg interface, awaiting the
pull. **Excluded per Mario, permanently:** amortizing 1, N/A 4. **Excluded pending data:**
pass-through 16.

## 3. Code structure

Inside `src/pricer/` (the template layout Mario approved):

```text
core/pricing/    analytical  cashflows  discounting  tree  floating  hybrid  coupon_schedule
core/risk/       sensitivities
core/market/     spreads  curves
core/utils/      dates
assets/corporate/  bonds_input  vanilla  stepped  floating  hybrid
                   embedded_option + callable / puttable / sinking
endpoints/       main  contracts  pricing  dependencies
```

Not yet migrated, reached through their original paths (all still working): `pricing/ilb.py`,
`pricing/mbs.py`, `curves/`, `credit/`, `dataio/`. Every migrated module left a **shim** at
its old path, so no driver, script or test changed.

## 4. This round in detail (2026-08-30, Round 2b)

### How it arrived

**No plan from the planning side.** At the meeting Mario worked down the coupon-type pivot on
the holdings workbook and annotated a **new column F**: `finished` against the plain-fixed row
(617), `just corp bond(fixed)` against the zero row, `no` against six rows. That column *is*
the ask, and it is now committed — it is the only record of what was requested and when.

### The interpretation

"Finished" cannot mean "priced" — all of these have priced in the legacy layer since July. It
means **in the restructured `pricer/` package**, which is exactly what the plain-fixed row
describes (the approved sample was the vanilla chain). The execution side checked whether the
two readings diverge in what they imply, found they don't, and proceeded without asking.

### The six cells

| Cell | Coupon type | Pivot ROWS | Unique securities | Held | Priced |
|---|---|---|---|---|---|
| F12 | Fixed → Floating | 5 | 5 | 5 | 4 |
| F13 | 7.00% / 7.50% date-segmented | 2 | **1** | 1 | 1 |
| F14 | GBP LIBOR + Spread | 1 | 1 | 1 | 1 |
| F15 | Reference Rate + Spread | 12 | 12 | 12 | 11 |
| F16 | EURIBOR + Spread | 9 | 9 | 9 | 5 |
| F20 | Step-up schedule | 1 | 1 | 1 | 1 |
| | **total** | **30** | **29** | **29** | **23** |

⚠️ **CORRECTED 2026-08-31 — the earlier version of this table was wrong about F13, and so
were the 08-30 report and both handoff bundles.** They read F13 as "2 rows, 1 held", which
implies one row is a security we do not hold. It is not. **F13's two rows are the SAME bond,
`TNTD04283895`, listed twice**, and it is held. The 30 → 29 step is a DUPLICATE LISTING, not
an unheld position. Across the whole tab, 676 rows are only **616 unique securities**: 60
asset IDs appear more than once, because the pivot counts rows.

The correct chain for Mario's six cells is therefore **30 pivot ROWS → 29 SECURITIES → 29
held → 23 priced + 6 named**.

⚠️ **Four denominators, not three.** 676 = tab ROWS · 616 = unique SECURITIES on the tab ·
566 = held/rated/matched positions in the output @3-31 · 555 = fully priced. Any plan quoting
a coverage number must say which of the four it means; regenerate with
`scripts/column_f_audit.py`, which prints all four.

The 6 unpriced = **5 awaiting post-switch margins** (already on the Bloomberg list; a fill is
one CSV cell, zero code change) + **1 defaulted** at its recovery mark. Rows 6–11
(`Fixed → Reset`, 6/6/3) share the hybrid engine and came free — adjacent, not part of the ask.

### What shipped

- `pricing/{frn,hybrid,coupon_schedule}.py` → `pricer/core/pricing/{floating,hybrid,coupon_schedule}.py`,
  moved **verbatim** (body asserted byte-identical), old paths now shims. The `floating` shim
  re-exports the **private** helpers because `hybrid` composes its floating leg out of them.
- A real layering violation closed: `core/pricing/cashflows.py` had been importing `coupon_at`
  from the legacy `pricing` package — core reaching upward into a not-yet-migrated layer.
- Three thin wrappers, `assets/corporate/{floating,hybrid,stepped}.py`.
- **One endpoint contract change covering all seven instrument types.** Splitting it would
  have meant two changes, which is what deferring dispatch to this round was meant to avoid.
  A typeless payload is still vanilla, so the Excel bridge and its 23 real-Excel checks pass
  unchanged (re-run and verified, not assumed).

### ⭐ The GBP finding

A two-month-old missing-data entry — "our GBP file has a non-arb 3y node", with a standing
request to **both** Bloomberg channels behind it — was our own bug. The par-yield exports are
not uniform: GBP and DKK store percentages, the other 24 files store decimals, and the loader
scaled everything by 100. The bootstrap then correctly refused a 73%–415% curve, and we read
its complaint as a fact about the data.

| | Before | Now |
|---|---|---|
| France Télécom GBP 7.50% 2011 | not priced | **205.31 bp**, duration 1.86 y |
| A UK EMTN fixed 5.50% 2033 | **absent from the output** | **197.30 bp**, duration 12.55 y |
| Rows @3-31 | 564 | **566** (priced 553→555, flagged 11) — 565 after the GBP units fix, then
  +1 on 08-31 when the defaulted-disposition rule recovered `TNTD03067251` |

The second bond generalises: it was **skipped, not flagged**, and it is a plain `Fixed` bond —
inside the class already reported complete. A completeness count was wrong in a direction no
report surfaced. Full accounts in `05` §1.9–1.10, `14` §1a and `06` §5. **The GBP request is
withdrawn — do not re-raise it.**

## 5. Test suite

**390** (was 223, then 287), ~35 s locally, ~29 s on 47.

```text
bootstrap  ratings  oas  universe  phase2_universe  term_overrides  call_schedules
coupon_schedule  frn  hybrid  ilb  mbs  lattice  price_convention  monthly_curves
pricer_structure  pricer_tree_structure  pricer_floating_structure (31, new)
vanilla_json_endpoint (28)  json_endpoint_dispatch (29, new)
```

Plus **57 checks driving real Excel** (`integrations/excel_vba/tests/Run-BridgeTests.ps1`) with
no Python installed, and **61** when a real interpreter is named — both outside pytest. Was 23
before the tree products reached the bridge, then 48/50, then 57/61 when `floating` closed the
last untested type on 08-31.

## 6. What is blocked, and on what

| blocked | on | channel |
|---|---|---|
| Govt MBS 888 | 8 pool fields × 882 CUSIPs | Mario 07-22 · Liping 07-30 |
| pass-through 13 uniques | amortisation schedules | Mario 07-20 · Liping 07-30 |
| 8 hybrids | post-switch margins only | Mario 07-20 · Liping 07-30 |
| 1 corporate callable | a call schedule (AssuredGty) | Liping 07-30 |
| 1 index-linked (KTBi) | indexation terms + a KRW 3-31 curve row | **deferred** — do not re-ask |
| the demo sheet's extra bond types | **Mario's answer on layout** | asked in the 08-30 report |

~~GBP curve~~ — **closed by us**, not by data. Withdrawn from the registry.

## 7. Immediate next steps

1. The user sends the 08-30 report and the refreshed Drive package to Mario.
2. Mario answers the layout question → the demonstration sheet gains the new bond types.
3. Mortgages when the pool data lands — the largest remaining block, and not blocked on us.

---

## 8. Update 2026-08-31 — the hardening round, and what it changed

Executed against `docs/cc_post_round2b_review_hardening_and_release_instruction_2026-08-31.md`,
whose §14 records a Gate-0 revision made **before** implementation. Eleven commits, `44e65fe`
at the head; 287 → **390** tests.

### The one intentional numerical change

**The FRN running coupon is now frozen while risk is measured** (L38). Six of the seven
floaters moved, all positive, each equal to one coupon period × 100/P to within 3%. **No price
and no spread moved**, `callable_risk` and both `phase2` files are byte-identical, and the only
columns that differ anywhere are `eff_dur`, `dv01`, `convexity`. Per-bond table:
`docs/frn_current_coupon_freeze_2026-08-31.md`.

The acceptance was mechanical rather than eyeballed: the moved set is *exactly* the floating
rows that had been negative (6 of 7 — the seventh had its coupon recorded and was already
frozen), and it contains no non-floating row.

### One more invisible security — 565 → 566

`TNTD03067251`, 8.78M nominal across three lots, matched neither of two recovery paths (`05`
§1.13). This is the **third** instance of one decision with two owners, after the GBP units bug
and the callable routing hole. It is now a named `recovery` row.

### Structural work, all numerically inert (five CSVs byte-identical after each)

- the domain exception family (L37) — and a live `NameError` it exposed in `phase2_risk.py`
- one ACT/364 exercise conversion, `days_per_year` deleted (L39)
- `hybrid` no longer imports `floating`'s private helpers; `discounting` gains `curve_rate` and
  `curve_discount_factor`, and floating's privates are `is`-asserted aliases so the shim's
  documented re-export contract still holds
- disposition sidecars are **dated** (`05` §1.16)
- `scripts/release_facts.py` (L42)

### Excel: 7 / 5 / 4 → **7 / 5 / 5**

`floating` became the fifth type verified by a real-Excel round trip. Two optional cells,
`FIP_QuotedMarginBp` and `FIP_CurrentCouponPct`, read only for that type; 37 added lines in the
`.bas`, nothing deleted, no engine/contract/schema change. Excel checks **48 → 57** fixture and
**50 → 61** live. The live round trip returns **397.3304715128111 bp** for `TNTD03080834` —
bit-identical to the production CSV row, produced from a spreadsheet.

### Two design memos, and a repo tidy

`short_gap_callable_design_note_2026-08-31.md` (why `TNTD04920858` stays refused, and the three
things an off-coupon exercise node must settle first) and `shim_exit_policy_2026-08-31.md` (four
exit criteria, **all** required; criterion 1 is currently UNMET because all three drivers still
import `pricing.*`; retire nothing now).

The four tracked `fixed_income_code_v*.zip` snapshots were removed from the branch — history
untouched, recoverable with `git show <old-commit>:<name>`, and `/fixed_income_code_v*.zip`
added to `.gitignore` anchored at the root so `data/*.zip` cannot match.

### Still true, and still the next thing

No new Mario or Liping request was opened, by instruction; the three corporate call schedules
joined the existing confirmation-only queue. The layout question in `04` §1 remains his.
