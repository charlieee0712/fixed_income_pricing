# Handoff for Claude Web — planning-side sync

_Refreshed **2026-08-15 (pm)** · repo `fixed_income_pricing` @ `241e76f`+ (main) · 153 tests green ·
maintained by the Claude Code CLI session (protocol in §6)._

> **How to read this (you = Claude on claude.ai, inside this Project).** You are the
> **planning side**: strategy, methodology design, prioritization, comms drafting, report
> structure. **Execution** — code, data, tests, server runs — happens in a Claude Code CLI
> session on the private repo; you don't see the code and don't need to. Hand back decisions
> and designs the user can relay as directives, not code diffs. Treat §3 (locked) as settled
> unless the user explicitly reopens an item. In a returning chat, read **Δ** first. If
> today's date is >3 weeks past the refresh stamp above, ask the user for a refreshed
> handoff before leaning on §2/§4 details.

## Δ — since previous handoff (same day, am)

- **New Mario directive (2026-08-15): restructure the code** — "a bit difficult to follow,
  a bit nested"; a **Google team will take over for cloud-computing optimisation** ⇒ many
  simple functions, inputs highlighted, per his folder template (core 80% / assets 20%).
- **Sample built & delivered same day** (awaiting Mario's approval before any further
  migration): the corporate vanilla chain re-expressed in the template layout
  (`pricer/` core+assets), old APIs kept as shims ⇒ numbers bit-identical; tests 145 → 153
  green. Deliverable folder (plain-language PDF report + code) ready for Google Drive.
- **The legacy "Monthly" sheet decoded** — it is the missing legacy GOLDEN: ~2,600 bonds
  with the old system's OAS/duration/scenario outputs @ 2010-03-01 (+ that day's 6-currency
  curves on-sheet), plus the per-function input dictionaries our new layout now mirrors.
  Reconciling our engines against it = proposed next validation milestone.

## 1 · Project & people

- **Goal:** port a legacy Excel/VBA fixed-income pricing toolkit to a structured Python
  module. Corporate bonds = the reference implementation; agencies/guaranteed/inflation-linked
  now also built; MBS/ABS/CMO next; a CreditMetrics risk layer later. Mario's framing: this
  is an **all-purpose tool** — an automated end-to-end process plus a complete
  missing-data table matter more than any single bond's number. **New (08-15): the codebase
  will be handed to a Google team for cloud optimisation ⇒ structure/readability is now a
  first-class requirement** (template + sample under review, see Δ).
- **Book:** URS, a US engineering-company pension (USD-dominated), custodian holdings as of
  **2009-03-31**. Custodian marks (price/MV/YTM/duration) are the golden master for
  reconciliation only — never pricing inputs. (A Uganda govt-bond demo inside the legacy
  files is a separate example — never merge the two.)
- **People:** **Mario** — project lead, sets methodology directives, primary Bloomberg
  channel. **Liping** — colleague, second Bloomberg channel (campus terminal) and code
  reviewer (her v2 review drove the 2026-08-04 fix). **Boss/CEO** — approved keeping client
  data in the private repo; EIR (IFRS-9) spec confirmation pending. **The user** — sole
  implementer, runs both this Project and the CLI sessions.
- Deliverables to Mario go via Google Drive folders; comms via WhatsApp.

## 2 · Current state — built & validated

**Corporate pipeline:** workbook loaders → deterministic MECE universe funnel (732 unique
bonds → **canonical 528** vanilla-routed @ 2009-03-31, every exclusion logged with exactly
one reason) → per-currency zero curves (USD/EUR/GBP/JPY/AUD/KRW, par→zero bootstrap,
golden-exact vs legacy) → per-bond **implied OAS calibrated to the custodian clean price**
→ **risk metrics** (effective duration / DV01 / convexity) → output table.

**Engines (each invariant- or golden-tested):**

- vanilla fixed — exact port; a `vba_compat` mode reproduces the legacy discounting bug
  bit-for-bit (default corrects it; effect ≈0.2% @ 8y, does not change any verdict);
- coupon-schedule (stepped/step-up) · FRN (curve-forward projection, single-curve,
  eff-duration ≈ time-to-next-reset) · fixed-then-float **hybrid** (fixed leg + FRN leg
  glued on one curve+OAS; margin-0 telescoping identity proves the composition);
- callable/putable **BDT lattice** (calibrated to the zero curve, σ=0.15, data-driven call
  schedules; straight-bond-on-lattice ≡ closed form to machine precision); corporate
  genuine-callable bucket = 5 bonds: 3 lattice-priced, the AssuredGty one awaits its call
  schedule (asked of Liping);
- zero · **ILB** (index-ratio path; calibrated spread ≈ −breakeven, own column, never mixed
  with credit OAS) · **MBS static-CPR skeleton** (built to the exact 8-mnemonic Bloomberg
  interface — data lands ⇒ zero code change) · recovery marks for defaulted.

**Code structure (new 08-15):** the vanilla chain now also exists in the target template
layout — `pricer/core/` (cashflows, discounting, analytical DCF, sensitivities, spread
calibration, dates) + `pricer/assets/corporate/` (input catalogue + one simple function per
output, legacy naming/units) — with the old modules as thin shims. Sample only; rollout
gated on Mario.

**Convention law (post code review):** model PV = dirty, custodian price = clean, ONE
shared accrued-interest formula (ACT/364); every calibration clean-vs-clean; duration
denominator = dirty (tested both ways against custodian durations).

**Results @ 2009-03-31 baseline** (2009-06-10 kept as a ~110bp-tighter control):

- Corporates: **564 rows = 553 priced + 11 flagged** (data-gap bonds carried at custodian
  price with a named flag — never force-priced; each fill = one CSV row, no code change).
- Phase 2: **AGY 39** (median 121bp; 5 lattice callables land within 0.75y of custodian
  option-adjusted duration), **GTD 9** (all FDIC-TLGP, own bucket, 86bp), **ILB 15**
  (breakevens show the 2009 deflation-panic shape; JGBi sign flips correctly).
- History: v1 (one index OAS per rating) validated **unbiased** with ~6.4% name-level
  dispersion — superseded by per-bond calibration, which reprices the custodian exactly by
  construction; model quality is judged on risk metrics and invariance tests (**153 green**).

## 3 · Locked decisions — do not re-litigate

1. **Valuation & calibration date = 2009-03-31** (matches holdings; Mario's curve). The
   custodian's tighter-than-index marks are the genuine recovering-market level (Mario,
   07-03) — the "70-day gap / marking-date" question is CLOSED.
2. **OAS is a per-bond calibration OUTPUT, not an input**; risk metrics are the goal.
   Index/sector OAS sourcing is dead (FRED's free OAS history truncated to 3y in Apr-2026;
   the workbook archive is the only history source).
3. **No Bloomberg on our side.** External data arrives only via Mario/Liping pulls into
   tracked CSV landing zones. **Web/ISIN-researched terms are PROVISIONAL** — when
   Bloomberg data arrives: diff, Bloomberg wins, deltas logged (`docs/missing_data.md` is
   the living registry of every gap → landing file → interim treatment → request status).
4. Clean/dirty law + single accrued formula; duration on dirty price (§2).
5. **Make-whole callables price as vanilla** (47 bonds, flagged); only the 5 genuine-gap
   callables use the lattice. σ=0.15 (Mario). Call schedules are data, never hard-coded.
6. Single-curve FRN/hybrid discounting = the 2009 convention; OIS dual-curve = documented
   future enhancement, not now.
7. Data-gap bonds are flagged + custodian-marked, **never half-modelled**. Amortizing (1) +
   n/a (4) are permanently out (Mario). Pass-through work starts only when its data arrives.
8. Hybrid/junior-sub OAS, distressed and zero-structured bonds stay OUT of by-rating medians.
9. Repo stays **private**; client data is tracked in-repo (boss-approved 2026-07-08).
10. Deferred-asks discipline: §4b items wait for the next natural touchpoint (= Mario's MBS
    data return) — do not draft re-asks before then.
11. **Restructure = sample-first** (user's call): nothing beyond the vanilla chain migrates
    until Mario approves; every migration step keeps the full test suite green with
    bit-identical numbers (shims preserve old APIs until retired).

## 4 · Open items — the planning surface

### 4a · Awaiting counterparties (all requests sent)

| Ask | Channel | Sent | Unblocks |
|---|---|---|---|
| **Code-structure sample approval** (Drive folder: plain-language report + `pricer/` code) | Mario | 08-15 | full migration rollout + the ~2,600-bond Monthly golden reconciliation |
| 11-security list: 3 exempt-US FRNs (full terms) + 8 hybrid post-call margins | Mario | 07-20 | 8 hybrids price via one CSV cell each |
| Govt-MBS pull: 8 fields × 882 CUSIPs (BDP template provided) | Mario | 07-22 | MBS driver + pool routing (skeleton waits) |
| Pass-through terms, 13 uniques (EETC/private amortizers) | Mario | 07-20 meeting | likely amortizing-vanilla, no prepay model |
| Full gap request incl. all of the above + AssuredGty call schedule (5th callable) + extras (KTBi, GBP curve, FHR-3122-ZB) | Liping | 07-30 | second channel; dedupe against Mario on arrival |

Also pending: **EIR (IFRS-9)** spec confirmation from the CEO (agreed approach: effective
yield = IRR of book cost vs remaining CFs; no legacy code exists — implement after
confirmation).

### 4b · Deferred by design (trigger = Mario's MBS-data return)

KTBi indexation terms + KRW curve row (single $1.2M position, safely custodian-marked) ·
agency call-schedule confirmation (lattice already matches custodian durations) · one
rating-feed quirk (A vs Aa2).

### 4c · Next milestones, in order

1. **Mario approves the structure sample** → roll the template layout out:
   floating/hybrid → callable lattice (`core/pricing/tree.py`) → **Monthly-sheet golden
   reconciliation** (~2,600 bonds @ 2010-03-01: rebuild the sheet's 6-ccy swap curves, run
   our engines, compare OAS/duration/scenario columns to the legacy outputs; needs a
   swap-grid bootstrap variant + curve-twist/vol bumps) → ILB/agency wrappers → MBS.
2. **Any Bloomberg return** → dedupe channels → diff vs provisional overrides (Bloomberg
   wins, deltas logged) → CSV landings → rerun both drivers → refreshed outputs + registry.
3. **Pass-through data lands** → price as scheduled-amortization vanilla.
4. **EIR** after CEO confirmation.
5. **CreditMetrics risk layer** — architecture slot reserved, design not started (a good
   conversation for this Project).
6. Boundary backlog (v2, unscheduled): TIPS deflation floor (needs inflation vol), OIS
   dual-curve, GBP curve replacement (a bad 3y node blocks 2 GBP bonds).

## 5 · Glossary (custodian & project shorthand)

- **BT / BU / DI / AQ / Z / CV** — custodian columns: clean price · market value · YTM ·
  duration · book cost · par held. "**BT-mark**" = carry a bond at BT with a named flag,
  no model output.
- **47** — the Linux compute server; all Python runs and tests happen there.
- **canonical** — the vanilla corporate pricing universe after the exclusion funnel.
- **route** — per-bond engine assignment (vanilla / schedule / floating / hybrid / lattice /
  recovery / flagged).
- **implied OAS** — the spread solving model clean price == BT.
- **make-whole** — treasury+spread call ⇒ economically non-callable ⇒ priced vanilla.
- **TLGP** — FDIC-guaranteed bank paper; its own bucket, never bank credit buckets.
- **overrides layer** — tracked CSVs (coupon paths, FRN margins, make-whole list, hybrid
  switch terms, call schedules) that outrank workbook free-text; the Bloomberg landing zone.
- **Monthly sheet** — legacy run-sheet in the old risk workbook: per-metric function demos,
  per-function input dictionaries, and ~2,600 bonds of legacy outputs @ 2010-03-01 — our
  structure reference (adopted) and reconciliation golden (planned).
- **pricer/** — the new template-shaped package (core engines + thin asset wrappers); old
  module paths are compatibility shims over it.
- **TNTD…/TNTG…** — internal custodian asset IDs (the join key across sheets).

## 6 · Handoff protocol (for both sides)

- Lives at the repo root; the CLI session refreshes it **in the same commit as any
  milestone or comms-state change**, and on request ("更新handoff"). Each refresh: update
  facts in place, **replace** Δ (never append), bump the stamp line. Hard cap **250
  lines** — new content must displace old, no history accumulation.
- The user then replaces this file in the Project knowledge (re-upload or GitHub re-sync).
- Deliberately excluded (lives in the repo, ask the CLI session): server/ssh mechanics,
  file paths, function/test names, full history, per-bond ISIN detail.
