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
