# Glossary — custodian columns & project shorthand

## Custodian workbook columns (the URS holdings file)

- **BT** — clean market price (the calibration target). "**BT-mark**" = carry a bond at BT
  with a named flag, no model output.
- **BU** — market value (base USD) · **DI** — YTM · **AQ** — duration · **Z** — book cost
  (base) · **CV** — shares/par held · **CM/CL** — S&P / Moody ratings · **AB** — first
  call date column (seeded the par-call schedules).
- **Asset ID (TNTD…/TNTG…)** — internal custodian IDs; the join key across sheets (100%
  match master↔tab; ISIN secondary).

## Project shorthand

- **47** — the Linux compute server (ssh from the Windows box); all Python runs and tests
  happen there. GitHub↔47 is unreliable (GFW), so 47 is synced by direct git push from the
  local machine.
- **VAL** — valuation date: 2009-03-31 baseline, 2009-06-10 control.
- **canonical** — the vanilla corporate pricing universe after the MECE exclusion funnel
  (528 @ 3-31 production).
- **route** — per-bond engine assignment: vanilla / vanilla-schedule / floating / hybrid /
  lattice / recovery / flagged (BT-mark).
- **implied OAS** — the flat spread solving model clean price == BT; a calibration factor,
  not a market OAS.
- **make-whole** — call at treasury+spread ⇒ economically non-callable ⇒ routed vanilla
  (flagged), not to the lattice.
- **TLGP** — FDIC-guaranteed bank paper (Temporary Liquidity Guarantee Program); its own
  guaranteed bucket, never bank credit buckets.
- **overrides layer** — tracked CSVs (coupon paths, FRN margins, make-whole list, hybrid
  switch terms, call schedules) that outrank workbook free-text; the Bloomberg landing
  zone. Web-sourced values in it are PROVISIONAL.
- **missing-data registry** — `docs/missing_data.md` (bundle file `06`): every gap → its
  landing CSV → interim treatment → request status.
- **Coupon_Formula2** — the workbook free-text column the coupon-type router classifies
  (F / floating / fixed-to-reset / stepped / step-up / zero / pass-through / …).
- **BDT lattice** — the v2 callable/putable binomial short-rate tree (calibrated to the
  zero curve; σ=0.15; reads `[(date, price)]` call schedules from data).
- **Monthly sheet** — legacy run-sheet in `Project Pricing Fixed Income Instruments.xlsm`:
  per-metric function demos (`CorpBondOAS`…), per-function input dictionaries, and ~2,600
  bonds of legacy `bondcalc` outputs @ 2010-03-01 — our structure reference (adopted) and
  reconciliation golden (planned).
- **bondcalc / bondoas / Zeroyield / GetBloomberg** — legacy VBA UDFs: the consolidated
  per-metric calculator (analysisType 1–6), the callable-lattice analyzer (types 1–10),
  the curve bootstrapper, and the (dead) Bloomberg fetcher our data files replace.
- **pricer/** — the new template-shaped package (core engines 80% + thin asset wrappers
  20%, per Mario's 2026-08-15 template); the old `pricing.*` module paths are
  compatibility shims over it. Sample = vanilla chain; rollout awaits Mario.
- **EIR** — IFRS-9 effective-interest-rate deliverable (amortised cost); spec preset,
  awaiting CEO confirmation; no legacy code exists.
- **Two clients** — URS (the US pension book, the target) vs Uganda (a UGX demo inside the
  legacy pricing workbook). Never merged.

## Added 2026-08-25

- **`pricer/endpoints/`** — the external interface: one payload dict in, one response dict
  out (`analyze_vanilla_payload`). Failures are values, never exceptions. No arithmetic.
- **operation** — `calibrate_and_risk` (price in → OAS out; refuses a supplied OAS) or
  `price_at_oas` (spread in → price out).
- **the tree** — `core/pricing/tree.py`, the migrated BDT lattice. Serves callable, puttable
  and sinking-fund bonds; `pricing/lattice.py` is now a shim over it.
- **sinking fund (as modelled)** — *issuer optional redemption*: on scheduled dates the
  issuer may retire a fraction of the amount **outstanding** at a contractual price. Not
  amortisation, which is deterministic and has no option.
- **fraction_basis** — must be `"outstanding"`. `"original"` is refused with a pointer to the
  strip decomposition it would require.
- **the two volatility experiments** — price at a fixed spread vs spread at a fixed price.
  Different questions; never conflated.
- **Round 2a / 2b** — this week's embedded-option work; next week's floating + endpoint
  dispatch.
- **`legacy-stale-session`** — the 2010-03-01 Monthly batch: an older code revision run on
  mixed-vintage cached data. Diagnostic only, never a numeric target.
- **the bridge** — `RysePricingBridge.bas`, the Excel adapter. Reads named cells, writes one
  request, runs one configured command and waits, maps the answer back. No pricing in VBA.


## Added 2026-08-30

- **column F** — the status column Mario wrote on the workbook's `Pivot of Corp Bonds` sheet
  at the 2026-08-27 meeting. `finished` = the coupon family is in the restructured `pricer/`
  package (NOT "priced"); `no` = not yet. The six `no` rows were this round's ask.
- **`instrument_type`** — the JSON field that selects the engine: `vanilla`, `stepped`,
  `floating`, `fixed_to_floating`, `callable`, `puttable`, `sinking`. Absent = vanilla.
- **quoted margin** — a floating note's contractual spread over its index (renamed from
  `spread_over_libor`). Absent for most of this book, whose cells read "... + Spread" with no
  number; a plain floater may then be priced with it absorbed into the calibrated spread,
  a **hybrid may not**.
- **discount margin (as we use it)** — what `implied_oas_bp` becomes on a floater priced with
  no quoted margin: it absorbs the unknown contractual margin *and* credit. The response says
  which of the two meanings applies rather than leaving it to be assumed.
- **the two floating-duration regimes** — `+`time to next reset when the current coupon is
  supplied, `−`time since the last reset when it is projected. Both correct, both within one
  coupon period.
- **`PAR_YIELD_UNITS`** — the per-file registry declaring which `*_Yield_Curve.txt` store par
  yields in percent (GBP, DKK) rather than decimals (the other 24). Declared, never sniffed.
- **`ParYieldUnitError`** — raised *before* the bootstrap when a scaled par row exceeds 100%,
  so a units mistake cannot masquerade as "the curve is not arbitrage-free".
- **`skipped=N`** — the calibration driver's header count of bonds dropped without a flag.
  It was 1 for months (a GBP bond nobody could see was missing); it is now 0. Worth watching:
  a flagged bond is visible, a skipped one is not.
- **the convexity noise floor** — driver CSVs differ across platforms by ~1e-8, all in
  `convexity`, because it is a second difference divided by bump². Not a regression.
