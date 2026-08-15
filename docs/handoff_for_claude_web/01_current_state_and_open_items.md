# Current state & open items — 2026-08-15

## Δ — what changed today (2026-08-15)

- **New Mario directive: restructure the code.** His words: "a bit difficult to follow, a
  bit nested"; a **Google team will take over the codebase for cloud-computing
  optimisation** ⇒ use many simple functions rather than one complicated; highlight the
  inputs (parameters) of each function. He supplied a target folder template
  (`09_code_structure_template.txt`: `core/` ≈80% reusable engines + `assets/` ≈20% thin
  per-asset wrappers + `endpoints/`) and pointed to the legacy workbook's **Monthly sheet**
  as the reference — adding that our results can be **checked against that sheet**.
- **Sample shipped the same day** (user's call: sample-first, migrate nothing else until
  Mario approves). The corporate vanilla chain (price → implied OAS → risk) now exists in
  the template layout — package `pricer/` with `core/pricing/{cashflows, discounting,
  analytical}`, `core/risk/sensitivities`, `core/market/{spreads, curves}`,
  `core/utils/dates`, and `assets/corporate/{bonds_input, vanilla}`. The asset layer is one
  simple function per output with legacy naming/units (`calculated_price`, `implied_oas`,
  `duration`, `widening`, `tightening` + new `dv01`/`convexity`), and `bonds_input.py`
  holds the input catalogue in the Monthly sheet's dictionary format. The old modules are
  thin shims, so every driver and all prior tests run unchanged — float-operation order was
  preserved, numbers are bit-identical. Tests **145 → 153 green** (~10s). Deliverable
  folder (plain-language PDF report + code + README, zipped) handed to the user for Google
  Drive upload to Mario.
- **The Monthly sheet was decoded end-to-end and turns out to be the missing legacy
  golden master** (details in §"Monthly sheet" below and in the 08-15 worklog entry).
- Handoff switched from a single file to this multi-file bundle.

## 1 · Project & people

- **Goal:** port a legacy Excel/VBA fixed-income pricing toolkit to a structured Python
  module. Corporate bonds = the reference implementation; agencies / FDIC-guaranteed /
  inflation-linked also built; MBS/ABS/CMO next; a CreditMetrics risk layer later. Mario's
  framing: an **all-purpose tool** — the automated end-to-end process and a complete
  missing-data table matter more than any single bond's number. Since 08-15, **structure /
  readability for the Google handover is a first-class requirement**.
- **Book:** URS, a US engineering-company pension (USD-dominated), custodian holdings as of
  **2009-03-31**. Custodian marks (price/MV/YTM/duration) = golden master for
  reconciliation only, never pricing inputs. (The Uganda demo in the legacy files is a
  separate example — never merge.)
- **People:** **Mario** — project lead, methodology directives, primary Bloomberg channel.
  **Liping** — colleague, second Bloomberg channel (campus terminal), code reviewer (her v2
  review drove the 2026-08-04 clean/dirty fix; the review-response PDF went to her 08-04).
  **Boss/CEO** — approved client data in the private repo; EIR (IFRS-9) spec confirmation
  pending. **The user** — sole implementer, runs both this Project and the CLI sessions.
- Deliverables to Mario travel via Google Drive folders (`corporate_bond`, and now the
  code-structure sample folder); comms via WhatsApp.

## 2 · Current state — built & validated

**Corporate pipeline:** workbook loaders → deterministic MECE universe funnel (732 unique
bonds → **canonical 528** vanilla-routed @ 2009-03-31, every exclusion logged with exactly
one reason) → per-currency zero curves (USD/EUR/GBP/JPY/AUD/KRW, par→zero bootstrap,
golden-exact vs legacy) → per-bond **implied OAS calibrated to the custodian clean price**
→ **risk metrics** (effective duration / DV01 / convexity) → output table.

**Engines** (each invariant- or golden-tested): vanilla fixed (exact legacy port; a
`vba_compat` mode reproduces the legacy discounting bug bit-for-bit; the default corrects
it, ≈0.2% @ 8y) · coupon-schedule (stepped/step-up) · FRN (curve-forward projection,
single-curve, eff-duration ≈ time-to-next-reset) · fixed-then-float hybrid (two legs glued
on one curve+OAS; margin-0 telescoping identity proves the composition) · callable/putable
BDT lattice (σ=0.15, data-driven call schedules; straight-bond-on-lattice ≡ closed form to
machine precision; corporate genuine-callable bucket = 5: 3 priced, AssuredGty awaits its
call schedule — asked of Liping) · zero · ILB (index-ratio path; calibrated spread ≈
−breakeven, own column, never credit OAS) · MBS static-CPR skeleton (built to the exact
8-mnemonic Bloomberg interface — data lands ⇒ zero code change) · recovery marks.

**Code structure (new):** the vanilla chain additionally exists in the template layout
(`pricer/` core+assets, old APIs shimmed) — sample only, rollout gated on Mario.

**Convention law (post Liping review):** model PV = dirty, custodian price = clean, ONE
shared accrued formula (ACT/364); every calibration clean-vs-clean; duration denominator =
dirty (tested both ways vs custodian durations).

**Results @ 2009-03-31 baseline** (2009-06-10 kept as a ~110bp-tighter control):

- Corporates: **564 rows = 553 priced + 11 flagged** (data-gap bonds carried at custodian
  price with a named flag, never force-priced; each later fill = one CSV row, no code).
- Phase 2: **AGY 39** (median 121bp; the 5 agency lattice callables land within 0.75y of
  the custodian's option-adjusted duration — independent validation) · **GTD 9** (all
  FDIC-TLGP, own guaranteed bucket, 86bp) · **ILB 15** (breakevens = the 2009
  deflation-panic shape; JGBi's sign flips correctly; KTBi custodian-marked pending terms).
- History: v1 (one index OAS per rating) validated **unbiased** (~0% signed IG error) with
  ~6.4% name-level dispersion — superseded by per-bond calibration, which reprices the
  custodian exactly by construction; quality is now judged on risk metrics and the
  invariance suite (**153 green**).

## 3 · The Monthly sheet (decoded 2026-08-15) — structure reference + future golden

In `Project Pricing Fixed Income Instruments.xlsm`: ① rows 3–43 = per-currency curve
inputs (US Libor 1–12M + USSA swap par 2–30y; USD/DKK/EUR/GBP/JPY/SEK) bootstrapped by the
`Zeroyield` UDF; ② rows 47–60 = demo block — per-metric simple functions sharing one input
list (`CorpBondOAS` / `CorpBondDuration` / `CorpBondwidening(±bp)` / `CorpBondSteepening`,
and `bondoas(analysisType 1–10)` for callable/put/sink/FRN/mortgage); ③ rows 61–98 =
per-function **input dictionaries** (Input Number | Field Name | Options | Description +
used-flags; Daycount: "30/360, but is not used" — compatible with our ACT/364 internal
convention); ④ row 99+ = **~2,600 bonds with the legacy system's outputs** via
`bondcalc(analysisType 1–6)`: OAS, Duration, Widening/Tightening (±10bp),
Steepening/Flattening, vol-bump prices and Vega — mostly at valuation **2010-03-01**
(~2,190 rows; also 2012-06-01 and 2012-12-12 blocks), plus a Bloomberg-OAS column with a
diff column. Mix ≈ 1,890 fixed / 430 floating / 130 zero / 74 variable + tails.
⇒ ①–③ are adopted in the sample; ④ = the proposed **large-scale reconciliation golden**
(rebuild the sheet's curves, run our engines over the rows, compare column-by-column) —
needs a swap-grid bootstrap variant + curve-twist and vol bumps.

## 4 · Awaiting counterparties (all requests sent)

| Ask | Channel | Sent | Unblocks |
|---|---|---|---|
| **Code-structure sample approval** (Drive folder: report + `pricer/` code) | Mario | 08-15 | full migration rollout + Monthly reconciliation |
| 11-security list: 3 exempt-US FRNs (full terms) + 8 hybrid post-call margins | Mario | 07-20 | 8 hybrids price via one CSV cell each |
| Govt-MBS pull: 8 fields × 882 CUSIPs (BDP template provided) | Mario | 07-22 | MBS driver + pool routing (skeleton waits) |
| Pass-through terms, 13 uniques (EETC/private amortizers) | Mario | 07-20 meeting | likely amortizing-vanilla, no prepay model |
| Full gap request incl. the above + AssuredGty call schedule + extras (KTBi, GBP curve, FHR-3122-ZB) | Liping | 07-30 | second channel; dedupe vs Mario on arrival |

Also pending: **EIR (IFRS-9)** spec confirmation from the CEO (approach preset: effective
yield = IRR of book cost vs remaining CFs; no legacy code exists — implement only after
confirmation).

**Deferred by design** (trigger = Mario's MBS-data return; do NOT re-raise earlier): KTBi
indexation terms + KRW curve row ($1.2M, safely custodian-marked) · agency call-schedule
confirmation (lattice already matches custodian durations) · one rating-feed quirk (A vs Aa2).

## 5 · Next milestones, in order

1. **Mario approves the sample** → rollout: floating/hybrid → callable lattice
   (`core/pricing/tree.py`) → **Monthly golden reconciliation** → ILB/agency wrappers → MBS.
2. **Any Bloomberg return** → dedupe the two channels → diff vs provisional overrides
   (Bloomberg wins, deltas logged) → CSV landings → rerun both drivers → refreshed outputs.
3. **Pass-through data lands** → price as scheduled-amortization vanilla.
4. **EIR** after CEO confirmation.
5. **CreditMetrics risk layer** — architecture slot reserved, design not started (a good
   topic for this Project).
6. Boundary backlog (v2, unscheduled): TIPS deflation floor (needs inflation vol), OIS
   dual-curve, GBP curve replacement (a bad 3y node blocks 2 GBP bonds).
