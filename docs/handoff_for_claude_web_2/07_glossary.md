# Glossary

## Custodian workbook columns (the URS holdings file)

| Column | Meaning |
|---|---|
| **BT** | clean market price — the calibration target. "**BT-mark**" = carry the bond at BT with a named flag and no model output |
| **BU** | market value, base USD |
| **DI** | yield to maturity |
| **AQ** | duration (the custodian's own; option-adjusted for agencies, straight for corporates) |
| **Z** | book cost, base USD (the EIR work would treat this as amortised carrying value) |
| **CV** | shares / par held |
| **CM / CL** | S&P / Moody's ratings (Fitch column is empty) |
| **AB** | first call date — seeded the par-call schedules |
| **AD / AG** | Bloomberg OAS and the relative difference against it, on the Monthly sheet |
| **Asset ID** (`TNTD…` / `TNTG…`) | internal custodian IDs; the join key across sheets — 100% match master↔tab, ISIN secondary |

## Project shorthand

**47** — the Linux compute server, reached by ssh from the Windows box. Historically the
only place Python ran; since 2026-08-25 the local machine also runs everything, and 47 is
the deployment target and parity reference. GitHub↔47 is GFW-unreliable, so 47 is synced by
pushing to it directly from local.

**VAL** — the valuation date. 2009-03-31 is the baseline; 2009-06-10 is the control.

**canonical** — the vanilla corporate universe after the MECE exclusion funnel (523 at
6-10 / 528 at 3-31 with the production overrides).

**route** — a bond's engine assignment: `vanilla`, `vanilla-schedule`, `floating`,
`hybrid`, `callable-lattice`, `recovery`, or a flagged BT-mark.

**implied OAS** — the flat spread that makes the model's clean price equal BT. A
calibration factor, not a quoted market OAS.

**make-whole** — a call at treasury + spread, i.e. economically non-callable. Routed to
vanilla with a flag, never to the lattice. 46–47 bonds.

**TLGP** — FDIC-guaranteed bank paper (Temporary Liquidity Guarantee Program). Reported in
its own guaranteed bucket, never in bank credit buckets.

**overrides layer** — tracked CSVs (coupon paths, FRN margins, make-whole list, hybrid
switch terms, call schedules) that outrank workbook free text. This is the Bloomberg landing
zone: a data arrival is a CSV edit, not a code change. Web-sourced values in it are
**provisional**.

**missing-data registry** — `docs/missing_data.md`: every gap → its landing CSV → interim
treatment → request status.

**`Coupon_Formula2`** — the workbook free-text column (Excel column **M**) that the
coupon-type router classifies into F / floating / fixed-to-reset / stepped / step-up / zero /
pass-through / amortising / na.

**BDT lattice / the tree** — the binomial short-rate lattice for bonds with embedded
options. Lognormal short rate, constant σ, p = 0.5, calibrated by forward induction with
Arrow-Debreu prices so it reprices the input curve's discount factors exactly. Now
`core/pricing/tree.py`.

**Monthly sheet** — the legacy run-sheet inside `Project Pricing Fixed Income
Instruments.xlsm`: per-metric function demos, per-function input dictionaries, and ~2,600
rows of saved `bondcalc` output. Authoritative for **function shape and input terminology**;
mostly **not** authoritative for numbers (see `19`).

**`bondcalc` / `BondOAS` / `zeroyield4` / `GetBloomberg`** — the legacy VBA functions: the
per-metric calculator (analysisType 1–6), the option-lattice analyser (types 1–10), the
curve bootstrapper, and the now-dead Bloomberg fetcher our data files replace.

**`pricer/`** — the template-shaped package: `core/` engines (~80%), `assets/` thin
per-bond-type wrappers (~20%), `endpoints/` transport. The old `pricing.*` module paths are
compatibility shims over it.

**shim** — a module at an old import path that re-exports the migrated objects, so nothing
that used the old path breaks. Asserted by identity in tests.

**`analysisType`** — the legacy `BondOAS` input #1: 1 bullet price · 2 callable price ·
3 puttable price · 4 sinking-fund price · 5 OAS · 6 duration · 7 FRN price · 8 FRN OAS ·
9 FRN duration · 10 mortgage price. These are the ten labels in cells **Q62:Q71** (the
numbers live in column P).

**`legacy-stale-session`** — the verdict on the 2010-03-01 Monthly batch: an older code
revision run against mixed-vintage cached market data. Diagnostic only; never a numeric
target.

**Round 2a / 2b** — this week's embedded-option work (callable, puttable, sinking) and next
week's floating-rate work plus the endpoint dispatch.

**EIR** — the IFRS-9 effective-interest-rate / amortised-cost deliverable. A requirement,
not legacy code: a search of 14k VBA lines and every sheet found zero hits, so there is no
golden to reconcile to.

**Two clients, never merged** — **URS** (the US pension book in USD; the actual target) and
**Uganda** (a UGX demo living inside the legacy pricing workbook).
