# Monthly-sheet golden reconciliation — design & gate plan

**Status:** **Rev B, 2026-08-17 — Gates 0–3 EXECUTED AND CLOSED** (Gate 0 evidence:
`docs/monthly_gate0_memo_2026-08-17.md`; Gates 1–3 results:
`docs/monthly_recon_report_2026-08-17.md`). Rev A (planning side, 2026-08-15) assumed the sheet
priced on its top-block Libor/swap curves and that the `BondPrice` discounting bug might carry
over — **both premises were refuted by Gate 0**; §2/§3 are rewritten accordingly. Gates 1–3 ran
same-day on the **user's explicit authorization** (recorded in §9). Headline verdicts: engine
parity proven exact on current-code-session caches (2012-12 batch: 100% within tolerance,
ΔOAS ≤0.9bp, Δdur ≤0.0003y); the 2010-03-01 batch = `legacy-stale-session` (older code rev ×
mixed-vintage data — see the report §4), on which the duration three-way vs Bloomberg goes
94% our way. Open scope = the tree-gated extensions (§ Gate 4).
**Respects locks:** `02` #4 (two legacy bootstraps, never conflate), #15 (sample-first),
#16 (migration ground rules), #17 (Monthly = reference & golden).

---

## 0. Purpose

The Monthly sheet (row 99+) is the missing legacy golden master: 2,642 priced rows with the
legacy system's own outputs (`bondcalc`), plus Bloomberg reference columns the legacy itself
reconciled against. Reconciling our engines against it is the single largest validation
available to this project — it converts "153 invariant/golden tests" into "reproduces the
production system at scale, and is measurably closer to Bloomberg where it differs."

The design is a gate sequence: each gate isolates one source of difference, and no gate opens
until the previous one closed with a named verdict. Gate 0 (inventory) is closed; its memo is
the evidence file for every fact below.

## 1. What the sheet is (inventory — post-Gate-0)

Workbook `Project Pricing Fixed Income Instruments.xlsm`, sheet `Monthly`, 2,896 rows × 81 cols:

| Block | Rows | Content |
|---|---|---|
| Top curve block | 1–43 | Per-ccy Libor+swap inputs (USD/DKK/EUR/GBP/JPY/SEK) + dead `=Zeroyield(range, ccy, "c:\blp\curves\")` cells. **A separate manual tool-chain — NOT in the golden table's data path** (memo F1). Cached rates look mixed-epoch; ignore unless that chain is ever reconciled. |
| Demo block | 47–60 | Per-metric simple functions (`CorpBondOAS`… + `bondoas`) — already adopted in the sample. |
| Input dictionaries | 61–98 | Numbered input tables per function (incl. "Daycount … not used", "Steepening from File in .txt"). |
| **Golden table** | 99 (header) + 2,642 rows | Multi-asset: Govt MBS 956 / **Corporate Bonds 856** / CMBS 351 / Govt Bonds 198 / Agencies 104 / ABS + tails (col AN). `cpn_typ` (D): FIXED 1,887 / FLOATING 426 / ZERO 110 (+ZERO COUPON 16, OID 2) / VARIABLE 74 / STEP 12 / DEFAULTED 21 / misc. Ccy (F): USD 2,476 / EUR 94 / GBP 21 / JPY 14 / tails. Valuation (O): 2010-03-01 × 2,187, 2012-06-01 × 122, 2012-12-12 × 274. |

**Golden-table column map (corrected by Gate 0):**

| Col | Content | Note |
|---|---|---|
| **B** | `MarketPrice` — **the calibration input** (`price_i`) | X = `Mkt Base Price` is a base-ccy copy (=B for USD) |
| C/D/E/F/G | coupon (FRN: current reset) / cpn_typ / freq / ccy / maturity | G is mixed str+datetime; no margin column anywhere (legacy pulled FRN margins live) |
| **I** | **Bloomberg effective duration** (n=2,278) | the high-coverage third-party leg |
| N | Volatility (0.1 default) | |
| O | valuation date (datetime) | |
| P–U | OAS / Duration / Widening / Tightening / Steepening / Flattening = `bondcalc(1/2/4(+10)/4(−10)/5/6)` | R/S/T/U are **prices**; Q/R/S/T/U/V/W evaluated **at OASadj = P** |
| V/W | `bondcalc(3)` at vol N+1% / N | for non-option rows V=W= reprice at P ⇒ **\|V−B\| = legacy's own solve residual** |
| Y/Z | Vega (bp/$) | option rows only |
| AB/AC | cached `MTY_typ` / `calc_typ_des` (getbloomberg, " Corp" suffix hard-coded) | partial: dead for MBS CUSIPs (0) and stale rows (#NAME?) |
| AD / AE / AG | Bloomberg OAS (n=311) / `=P` / **relative** diff `|AE−AD|/|AD|` | AG is not absolute |

**Input-parity principle (unchanged):** our engine consumes the **sheet row's own terms** —
B/C/D/E/F/G/N/O/AN (+AB/AC for routing) — never the URS overrides layer. This is a different
universe from the URS book; any term substitution would make term diffs masquerade as engine
diffs.

## 2. The two real hazards (replaces Rev A's curve-regime hazard)

**Curve truth first (memo F1):** every golden row prices off `zeroyield4(ccy, valuation)` —
**government par curves** (USD = H.15/CMT 11 pillars, gap-filled to the 41-tenor 0.08…30y grid,
continuous-z 374-month bootstrap ×4 frequencies; the same architecture as our whole pipeline).
The BondOAS tree consumes the same build's par vector (`IYC`); Libor appears only as the tree's
month-1..5 deposit stubs. USD pillars = FRED `DGS*` for **all three valuation dates**; the
tracked `*_Yield_Curve.txt` files carry all three dates as a 9-tenor cross-check. So curves are
a rebuild task, not a data-recovery task.

**Hazard A — the month-grid convention.** The legacy vanilla chain prices on month counts, not
dates: `maximo = Δyears·12 + Δmonths`, coupons every `12/freq` months from the valuation month,
face at the **last coupon index** (maturity truncated down to the step), first coupon always a
full period out, **no accrued interest**, maturities capped at 30y, curve table chosen by the
bond's own freq. A bp-level reconciliation is impossible on our ACT/364 engine directly ⇒ build
a **legacy-parity mode** (thin, separate from production paths) that replicates exactly this.
Our production conventions are not bent; the parity mode exists only to isolate engine fidelity.

**Hazard B — routing.** Which engine priced a row depended on live Bloomberg fields
(`mty_typ`/`calc_typ_des`) fetched inside `BondCalc`: AT MATURITY → vanilla chain; CALLABLE/
NORMAL/PUTTABLE/SINKABLE/PERP → lattice; FLOAT RATE NOTE → FRN tree; **empty/unknown → FRN-tree
fallback**; MBS/ABS/CMBS → mortgage engine by asset class; Government Bonds → vanilla
unconditionally. AB/AC cache these fields with gaps ⇒ the recon routes by AN + cached AB/AC and
classifies dead-AB corporates **empirically** (parity-match ⇒ vanilla; else `route-unknown`).

## 3. The convention question — RESOLVED (Gate 0, static)

`bondcalc`'s chain is self-consistent: continuous zeros (`z=−ln(DF)/t`) discounted
`Exp(−(z+OAS/10⁴)·t)`. The `BondPrice` semiannual/continuous mismatch is absent.
**`vba_compat` is dropped from this workstream; H2 collapses to ≈0** (pre-registered outcome).
The Gate-2 pilot retains a 3-bond two-mode checksum purely as the static/dynamic agreement test.

## 4. Gate architecture

### Gate 0 — Inventory ✅ CLOSED (2026-08-17)

All eight questions answered with citations → `docs/monthly_gate0_memo_2026-08-17.md`.
Highlights: 0.1 inputs cached/readable (formulas dead); 0.2 range=input, path=output, chain
off-golden-path; 0.3 consistent + re-bootstraps in-memory per row; 0.4 SteepFlat file lost
(43% of FIXED rows are zero-twist T=U, reconcilable; 57% need the file); 0.5 no clean/dirty
concept — raw B matched to an accrued-free PV; 0.6 FRN current-coupon in C, margins were live
pulls; VARIABLE ≈ fix-to-float priced as callable-fixed; 0.7 no 2012 curve blocks and none
needed (FRED); 0.8 month-grid (Hazard A).

### Gate 1 — Curve rebuild ✅ CLOSED 2026-08-17 (exact; report §2)

Rebuild `zeroyield4`'s USD curve at 2010-03-01 (then the 2012 dates): FRED DGS pillars →
the exact gap-fill arithmetic → the `zeroyield` bootstrap (374-month, 4 frequencies,
continuous z). Hypothesis: `bootstrap.py` (the auditable-family port) already matches modulo
the legacy solver's noise floor; if not, a thin exact replica joins the parity mode.

- **Validation (formula cells are dead ⇒ self-check):** the rebuilt curve reprices each
  gap-filled par instrument to 100 under `Exp(−z·t)` at 1e-6; cross-check zero nodes vs the
  9-tenor txt rows at shared tenors.
- Non-USD (166 rows) deferred: Bloomberg country-curve pillar sets ≠ our txt grid; USD first.

**Artifact:** per-date curve tables + a permanent golden test (`tests/test_monthly_curves.py`).

### Gate 2 — Pilot ✅ CLOSED 2026-08-17 (verdicts in report §3; tolerances re-baselined: OAS ≤1bp target / >2bp exception, dur ≤0.001y / >0.05y, reprice ≤0.01 / >0.10)

Sample ~20 from the 248-row corp/agy AT-MATURITY-FIXED set (spanning maturity, coupon,
premium/discount; excluding the 8 solver-capped P≥999 rows) + ~5 Government-Bond rows
including Treasuries (legacy P ≈ 0 ± small = curve anchors). **No ZERO rows** (legacy P=0 —
nothing to reconcile; Rev A's pilot zeros are replaced by the govvie anchors).

- **Verdict 1 (parity):** legacy-parity mode on the Gate-1 curve reproduces P within ~1–2bp
  and Q/R/S mechanically (Q at OASadj=P, ±10bp; R/S = P±10bp reprices; expected residual =
  the Veloz noise floor ~0.1–1bp + curve slop).
- **Verdict 2 (checksum):** the 3-bond two-mode test confirms §3.
- **Verdict 3 (tolerances):** the pilot residual distribution re-baselines §7.

**Artifact:** pilot memo (residual table + re-baselined tolerances).

### Gate 3 — Bulk vanilla ✅ CLOSED 2026-08-17 (report §5; NOTE the population verdict: only current-code-session caches [2012-12 batch] are valid numeric goldens — the 2010-03-01 batch is `legacy-stale-session` and reconciles three-way vs Bloomberg columns instead)

**Scope corrected: ~420 rows** (248 corp/agy at-maturity-fixed + ~174 govt-bond fixed), plus
the 217 dead-AB FIXED corporates run *speculatively* through the parity mode for empirical
routing. All @2010-03-01 first; the 2012 vanilla stragglers follow with their FRED curves.
Columns P/Q/R/S (+V/W as the solver-residual diagnostic).

- R/S are internally derived: if P matches, R/S must — treat R/S mismatches with P matched as
  a scenario-definition finding, not an engine finding.
- **Exception discipline** (one named reason per out-of-tolerance row):
  `sheet-term-vs-our-read` / `grid-mismatch` / `route-unknown` / `legacy-solver-cap` (P at the
  1000 search bound) / `legacy-dead` (P=0 classes) / `engine-gap` / `sheet-stale-cache`
  (#VALUE!/#NAME?/formula-as-text rows ~60) / `bloomberg-basis` / `unresolved`.
- Report cuts: maturity bucket × coupon level × premium/discount; median + p95 |diff| per
  column; pass rate per tier; |V−B| distribution as the legacy-solve-quality overlay.

**Artifact:** reconciliation report + frozen per-row CSV + exception ledger.

### Gate 4 — Extensions (each conditional, each its own mini-gate)

| Extension | Precondition | Note |
|---|---|---|
| CALLABLE/NORMAL/SINK/PERP fixed (~450) | tree rollout + call-schedule source (schedules were live Bloomberg pulls, not cached) | lattice recon; NORMAL = optionless tree rows |
| FLOATING (426) | tree rollout (BondOAS(8) tree) | margins were live pulls (folded into OAS where absent); **legacy FRN duration = OAS-bump = spread duration** (Q med 3.6, not time-to-reset) — parity mode must bump the same way; heavy tails (62 neg / 95 capped) pre-registered as `legacy-solver-cap` |
| VARIABLE (74) | tree rollout | legacy priced fix-to-float as callable-FIXED (memo row 168); divergence vs our `hybrid.py` is a *methodology finding to report*, not to imitate, beyond the fidelity check |
| T/U steepening/flattening | zero-twist part: none (T=U rows, 43%); rest: **SteepFlat file from Mario** (deferred ask, opens with this gate) | zero-twist T/U ≡ reprice — reconcilable immediately with Gate 3 machinery |
| V/W/Y/Z vol columns | tree rollout | only rows with V≠W carry signal |
| 2012 blocks (396) | none beyond Gate-1 FRED pulls for those dates | **no longer conditional** (Rev A's blocker dissolved); note 3 rows have formulas-as-text (never evaluated) |
| ZERO (110+16+2) / DEFAULTED (21) | — | **excluded: legacy produced no signal** (P=0 / degenerate strip path) |
| MBS/CMBS/ABS (~1,300) | MBS phase; `mtge_cflows` inputs were disk files (lost) + Bloomberg | out of this workstream |

## 5. The three-way design — ours ↔ legacy ↔ Bloomberg

| Comparison | Question | Register |
|---|---|---|
| ours(parity mode) vs legacy P/Q/R/S | **implementation fidelity** — did we rebuild the machine? | confirmatory; this is "the reconciliation" |
| ours(production conventions) vs ours(parity) | the documented convention gap (dates/AI/grid), sign & size reported per maturity bucket | descriptive (replaces the dead H2) |
| ours vs **AD** (OAS, n=311), using AG(relative) as legacy's own distance | is our engine at least as Bloomberg-consistent as legacy? | exploratory |
| ours vs **col I** (Bloomberg eff. duration, n=2,278 — vanilla subset) | same question on the high-coverage column | exploratory |

**Hypotheses:** **H1 (fidelity)** — vanilla P within pilot-calibrated tolerance; failures
investigated, never tuned away. **H2 — collapsed** (Gate 0; recorded, no longer tested).
**H3 (headline, exploratory)** — on option-free USD rows our OAS sits at least as close to AD
as legacy's (both sides are now known Treasury-based, which *weakens* the common-basis caveat
but AD's own curve setting stays unknown ⇒ the robust read remains dispersion, not level).
**H4 (new, exploratory)** — our duration is at least as close to col I as legacy's Q is.

## 6. Expected-differences ledger (updated)

1. ~~Curve regime~~ **resolved** — same (government) regime; residual = Gate-1 rebuild leakage
   only.
2. ~~Discounting convention~~ **resolved** — consistent; `vba_compat` dropped.
3. Curve-build granularity + the legacy solver's noise floor (Veloz 1e-4 relative ⇒ ~0.1–1bp
   OAS slop; |V−B| measures it per row) — absorbed into pilot-calibrated tolerance.
4. Cash-flow grid — **replicated exactly** by the parity mode (month grid, truncation, 30y cap,
   freq-matched table); any residual grid diff = a parity-mode bug, not a finding.
5. Clean/dirty — non-issue: no accrued concept in the target; B matched raw.
6. Routing — cached-field gaps ⇒ `route-unknown` class, empirically resolved.
7. T/U twist — file-gated for the 57% non-zero-twist rows.
8. Bloomberg basis (AD, col I) — exploratory register only.
9. Sheet staleness — bounded and enumerated (~60 stale cells/col + 3 text rows + row 100).
10. **Session vintage (found at Gates 2–3, the dominant effect):** the 2010-03-01 batch was
    cached by an older code revision (duration ÷100 scaling, dead T/U cells) on
    mixed-vintage market data (run-time Libor deposits survive in the top block; no single
    curve fits the pillar rows) ⇒ reason `legacy-stale-session`; only 2012-12-batch caches
    are valid numeric goldens.

## 7. Tolerances (provisional — Gate 2 re-baselines)

| Quantity | Target | Exception threshold |
|---|---|---|
| Zero rate per node (Gate 1 self-check) | par-reprice 1e-6; txt cross-check ≤ 2bp | — |
| OAS (P), parity mode | ≤ 2bp | > 10bp |
| Duration (Q) | ≤ 0.05y | > 0.25y |
| Widening/Tightening (R/S) | derived-consistency with P | — |
| Reprice (V/W vs B) | reported as legacy residual, not our error | — |

## 8. Artifacts & where they land

1. This plan (Rev B) — updated in place.
2. ✅ Gate-0 memo: `docs/monthly_gate0_memo_2026-08-17.md`.
3. Gate-1 curve goldens → `tests/test_monthly_curves.py` pattern.
4. Gate-2 pilot memo (parity verdict + re-baselined tolerances).
5. Gate-3 reconciliation report + frozen per-row CSV + exception ledger.
6. **Mario-facing one-pager** (plain language): what was compared, the three-way result, the
   headline sentence (H3/H4 if they hold), exception counts with reasons.

All new code follows lock #16: `pricer/` layout, numbered-input docstrings, asset-layer legacy
units, full suite green at every step. The parity mode lives beside (never inside) the
production pricing paths.

## 9. Sequencing vs lock #15 (sample-first)

- **Done before Mario's reply:** Gate 0 (pure inventory) — completed 2026-08-17. **Gates 1–3
  followed the same day on the user's explicit authorization** (their call as sequencing
  owner, 2026-08-17): net-new validation code in `src/recon/`, no migration touched, so the
  sample-first freeze's purpose — don't build on an unapproved layout — was not violated;
  the deviation from the default wait-for-Mario order is recorded here.
- **On approval:** the `01` §5 milestone order stands, with one Gate-0 correction: the vanilla
  gates (1–3) **no longer depend on the tree rollout** (Rev A had tied the reconciliation to
  option-row machinery; the vanilla golden needs none of it). They also validate exactly the
  chain the 08-15 sample migrated — so if Mario wants evidence fast, Gates 1–3 can run
  immediately after (or alongside) the floating/hybrid rollout, with the tree-dependent Gate-4
  rows following the tree milestone. Decision stays with the rollout conversation.
- **If Mario's approval changes the template layout:** Gate-1+ code lands in the post-approval
  layout; everything decided here is layout-independent.

## 10. Open questions

- **SteepFlat Table Monthly.txt** (and, later, the era's call schedules / FRN margins / mtge
  cash-flow files): lost disk inputs; each becomes a concrete ask via `docs/missing_data.md`
  **only when its gate opens** (lock #13 discipline).
- Dead-AB FIXED corporates (217): empirical routing at Gate 3 — expected to split
  at-maturity-like vs FRN-fallback rows.
- Non-USD pillar sets (Bloomberg country curves) vs our 9-tenor txt: approximation quality —
  assessed only if/when non-USD rows are promoted.

---

*Rev A prepared on the planning side from the 2026-08-15 handoff bundle. Rev B incorporates the
Gate-0 inventory of 2026-08-17 (`docs/monthly_gate0_memo_2026-08-17.md`); §2/§3 premises of
Rev A are superseded as recorded there. Nothing here re-litigates a locked item.*
