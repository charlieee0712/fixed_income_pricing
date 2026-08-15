# Handoff for Claude Web — planning-side sync

_Refreshed **2026-08-15** · repo `fixed_income_pricing` @ `c7a7e7a` (main) · 145 tests green ·
maintained by the Claude Code CLI session (protocol in §6)._

> **How to read this (you = Claude on claude.ai, inside this Project).** You are the
> **planning side**: strategy, methodology design, prioritization, comms drafting, report
> structure. **Execution** — code, data, tests, server runs — happens in a Claude Code CLI
> session on the private repo; you don't see the code and don't need to. Hand back decisions
> and designs the user can relay as directives, not code diffs. Treat §3 (locked) as settled
> unless the user explicitly reopens an item. In a returning chat, read **Δ** first. If
> today's date is >3 weeks past the refresh stamp above, ask the user for a refreshed
> handoff before leaning on §2/§4 details.

## Δ — since previous handoff

- Initial version (2026-08-15). Baseline = state after the 2026-08-04 code-review fixes
  (clean/dirty convention audit + lattice calibration fix, response PDF sent to Liping).
  All four external data requests (§4a) still outstanding.

## 1 · Project & people

- **Goal:** port a legacy Excel/VBA fixed-income pricing toolkit to a structured Python
  module. Corporate bonds = the reference implementation; agencies/guaranteed/inflation-linked
  now also built; MBS/ABS/CMO next; a CreditMetrics risk layer later. Mario's framing: this
  is an **all-purpose tool** — an automated end-to-end process plus a complete
  missing-data table matter more than any single bond's number.
- **Book:** URS, a US engineering-company pension (USD-dominated), custodian holdings as of
  **2009-03-31**. Custodian marks (price/MV/YTM/duration) are the golden master for
  reconciliation only — never pricing inputs. (A Uganda govt-bond demo inside the legacy
  files is a separate example — never merge the two.)
- **People:** **Mario** — project lead, sets methodology directives, primary Bloomberg
  channel. **Liping** — colleague, second Bloomberg channel (campus terminal) and code
  reviewer (her v2 review drove the 2026-08-04 fix). **Boss/CEO** — approved keeping client
  data in the private repo; EIR (IFRS-9) spec confirmation pending. **The user** — sole
  implementer, runs both this Project and the CLI sessions.
- Deliverables to Mario go via a Google Drive folder (`corporate_bond`); comms via WhatsApp.

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
- callable/putable **BDT lattice** — Arrow-Debreu-calibrated to the zero curve, σ=0.15,
  call schedules read from a data CSV; straight-bond-on-lattice ≡ closed form to machine
  precision. Corporate genuine-callable bucket = 5 bonds: 3 lattice-priced, the AssuredGty
  one awaits its call schedule (asked of Liping);
- zero · **ILB** (index-ratio path; calibrated spread ≈ −breakeven, kept in its own column,
  never mixed with credit OAS) · **MBS static-CPR skeleton** built to the exact 8-mnemonic
  Bloomberg interface (data lands ⇒ zero code change) · recovery marks for defaulted.

**Convention law (post-review):** model PV = dirty, custodian price = clean, ONE shared
accrued-interest formula (ACT/364); every calibration is clean-vs-clean; duration
denominator = dirty (tested both ways against custodian durations).

**Results @ 2009-03-31 baseline** (2009-06-10 kept as control, ~110bp tighter across the
board = the Mar→Jun yield backup, consistent):

- Corporates: **564 rows = 553 priced + 11 flagged** — data-gap bonds are carried at the
  custodian price with a named flag, never force-priced; each later data fill = one CSV
  row, zero code change.
- Phase 2: **AGY 39** (median 121bp; wides = quasi-sovereign credit; the 5 agency lattice
  callables land within 0.75y of the custodian's option-adjusted duration — independent
  validation) · **GTD 9** (all FDIC-TLGP paper, own guaranteed bucket, median 86bp) ·
  **ILB 15** (extracted breakevens show the 2009 deflation-panic shape; JGBi's sign flips
  correctly; Korean KTBi custodian-marked pending terms).
- History, for context only: v1 (one index OAS per rating bucket) validated **unbiased**
  (~0% signed IG error) with ~6.4% name-level dispersion — superseded by per-bond
  calibration, which reprices the custodian exactly by construction; model quality is now
  judged on risk metrics and the invariance test suite (**145 green**).

## 3 · Locked decisions — do not re-litigate

1. **Valuation & calibration date = 2009-03-31** (holdings date; Mario's curve). The
   custodian's tighter-than-index marks are the genuine recovering-market level (Mario,
   07-03) — the "70-day gap / marking-date" question is CLOSED.
2. **OAS is a per-bond calibration OUTPUT, not a pricing input**; risk metrics are the
   goal. Index/sector OAS sourcing is dead (FRED's free OAS history was truncated to a
   3-year window in Apr-2026 anyway; the workbook archive is the only history source).
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

## 4 · Open items — the planning surface

### 4a · Blocked on external data (all requests sent, all awaiting reply)

| Ask | Channel | Sent | Unblocks |
|---|---|---|---|
| 11-security list: 3 exempt-US FRNs (full terms) + 8 hybrid post-call margins | Mario | 07-20 | each margin = one CSV cell → bond prices, no code |
| Govt-MBS pull: 8 fields × 882 CUSIPs (BDP template provided) | Mario | 07-22 | MBS driver + pool routing (engine skeleton ready) |
| Pass-through terms, 13 uniques (EETC/private amortizers) | Mario (his initiative) | 07-20 meeting | likely amortizing-vanilla; no prepayment model needed |
| Full gap request: all of the above + AssuredGty call schedule (5th callable) + opportunistic extras (KTBi, GBP curve, FHR-3122-ZB) | Liping | 07-30 | second channel; DEDUPE against Mario's returns on arrival |

Also pending: **EIR (IFRS-9)** spec confirmation from the CEO. Agreed approach: effective
yield = IRR of book cost vs remaining cash flows; no legacy code exists (searched — zero
hits), so no golden master. Implement only after confirmation.

### 4b · Deferred by design (trigger = Mario's MBS-data return; do NOT re-raise earlier)

KTBi indexation terms + the missing KRW curve date (single $1.2M position, safely
custodian-marked) · agency call-schedule confirmation (par-call lattice already matches
custodian durations — confirmation only) · one rating-feed quirk (A vs Aa2).

### 4c · Next milestones, in order

1. **Any Bloomberg return** → dedupe the two channels → diff vs provisional overrides
   (Bloomberg wins, deltas logged) → CSV landings → rerun both drivers (baseline + control)
   → refreshed outputs + registry. Zero code change by design.
2. **MBS data lands** → pool-routing design (incl. REMIC Z-tranches / paid-down rows) +
   driver reconciled against the custodian golden; prepayment sophistication (CPR vector →
   behavioral model) staged after.
3. **Pass-through data lands** → price as scheduled-amortization vanilla.
4. **EIR** after CEO confirmation.
5. **CreditMetrics risk layer** — architecture slot reserved, design not started; the next
   big methodology conversation (good topic for this Project).
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
- **TNTD…/TNTG…** — internal custodian asset IDs (the join key across sheets).

## 6 · Handoff protocol (for both sides)

- Lives at the repo root; the CLI session refreshes it **in the same commit as any
  milestone or comms-state change**, and on request ("更新handoff"). Each refresh: update
  facts in place, **replace** Δ (never append), bump the stamp line. Hard cap **250
  lines** — new content must displace old, no history accumulation.
- After each refresh the user swaps this file into the claude.ai Project knowledge
  (re-upload, or re-sync if added via the GitHub connector).
- Deliberately excluded (lives in the repo; ask the CLI session): server/ssh mechanics,
  file paths, function/test names, per-bond ISIN detail, full history (`WORKLOG.md`),
  full methodology prose (`PROJECT_STATUS.md`).
