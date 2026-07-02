# Work Log

Reverse-chronological. Each entry is **anchored to the commit** that delivered the
work. Hours are recorded per entry; `[TO FILL]` = not yet logged.

---

## 2026-07-02 — 3-31 calibration ADOPTED as baseline (Mario's USD curve) + date-matched index fix
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Mario's 2009-03-31 USD curve arrived** (`USD_Yield_Curve.txt`, dropped at the repo root). Format = the
**native `*_Yield_Curve.txt` schema** — `Date`(Excel serial)`,0.25,0.5,1,2,3,5,10,20,30`, values **decimal**,
**USD-only** (no EUR/GBP inside). ⇒ **no adapter needed**: `bootstrap.load_par_curve` reads it directly;
integration = drop the file in + swap `VAL`. It is a **superset of the old USD file** (14,794 rows ~1962→2026):
fills the 2008-11-10→2009-06-10 gap (**3-31 = serial 39903 present**), and its 2024-01-16 row is **byte-identical**
to the old file (only diffs at overlapping dates = higher precision + a corrected 6-10 20y: old 4.75% → 4.3555%).
Swapped in on 47 (`data/USD_Yield_Curve.txt`; old kept as `…_pre_mario.txt`); **26/26 tests still green**.

**Curve self-check (bootstrap @ 3-31, Semiannual).** Short end ~ZIRP (0.5y 0.42%, 1y 0.55%); belly/long
**~100–137bp below 6-10** (2y 0.80 vs 1.36; 10y 2.75 vs 4.09; 30y 3.88 vs 5.26) — the March-lows→June sell-off.
**Par bonds reprice to 100.0000** at 2/5/10/30y, DFs monotone → arb-free & self-consistent. 3-31 levels tie to
actual end-Mar-2009 UST (5y≈1.66, 10y≈2.67, 30y≈3.54).

**DECISION — 3-31 ADOPTED as the calibration baseline; 6-10 retained as control.** Reasons: matches the
**holdings date**; **more correct universe** (481 vs 476 — 5 bonds alive @3-31 that 6-10 wrongly dropped as
matured); **fixes near-maturity distortion**; risk metrics barely move; and it is Mario's instruction. Calibration
exact both dates (`|clean−BT|`≈2e-8; 479/481 priced @3-31).

**Near-maturity distortion CLEARED (the caveat-1 fix, confirmed).** Date-matching the curve to the holdings date
removes the 70-day annualisation artefact:
- `TNTD04216534` (AA, matures 2009-06-15): **1371bp → 464bp**.
- `TNTD04598394` (A, matures 2009-07-15): **−177bp → +199bp** (the negative OAS).
- `TNTD04215797` (BBB, matures 2009-08-15): 12bp (implausibly tight) → 375bp.
- Aggregate over the near-mat set: `|bp|>1000-or-neg` **3→1**, negatives **1→0**, median|bp| 602→485, max 3182→2486.
  4 bonds cross >1y and **rejoin the by-rating medians**. The lone survivor (2486bp) is a genuine discount bond
  (BT 84), not a date artefact.

**By-rating implied OAS (excl. near-mat) + BT-MARKING-DATE EVIDENCE.** The ~100bp-lower 3-31 curve lifts every IG
median by ~+100bp. Paired with the **date-matched** ICE index (fix below), the two-date table is the evidence that
**BT embeds a ~June (post-rally, tighter) credit level, not a March crisis-peak level** (bp):

| rating | implied 6-10 | index 6-10 | implied 3-31 | index 3-31 |
|--------|-------------:|-----------:|-------------:|-----------:|
| AAA    |  171 |  148 |  278 |  246 |
| AA     |  388 |  227 |  489 |  403 |
| A      |  297 |  302 |  406 |  549 |
| BBB    |  420 |  453 |  525 |  731 |
| BB     | 1375 |  741 | 1423 | 1112 |
| B      | 1310 |  945 | 1389 | 1537 |
| CCC    | 2587 | 1704 | 2451 | 3093 |

Read: **@6-10 implied ≈ 6-10 index** (A 297 vs 302, BBB 420 vs 453); **@3-31 implied sits 143–206bp BELOW the 3-31
crisis-peak index** (A 406 vs 549, BBB 525 vs 731). Implied spreads move with the risk-free curve but do **not**
climb to the March index ⇒ the custodian marks were struck against ~June credit spreads. **⇒ question for
Mario/the colleague: what is the custodian's actual BT marking convention (date/source)?** NB: this affects the
**interpretation of the OAS absolute level only** — it does **not** affect the calibration+risk-metric deliverable
(which reprices BT exactly by construction, whatever BT's date).

**Risk metrics robust to the date.** Excl. near-mat (n=462 @3-31): eff-dur median 5.95y, DV01 0.051/100/bp,
convexity 41.6. Shift 6-10→3-31: eff-dur **+0.13y**, DV01 +0.0009, convexity +2.2 (earlier date = longer horizon +
lower yield). The deliverable is stable across the curve-date choice.

**GBP still blocked (2 bonds, `TNTG019421U`/`TNTG301334W`).** Mario's file is USD-only, and the *existing* GBP curve
@3-31 still hits its non-arb 3y node (Annual variant): `bootstrap()` builds all four freq variants and dies on the
bad Annual node even for a semiannual bond. **Root cause = GBP curve data (or the eager all-variant bootstrap), NOT
the valuation date.** Revisit when a GBP replacement curve arrives, or robustify `bootstrap` to build only the
needed variant. Non-blocking.

**Code (`scripts/calibrate_risk.py`).** (1) added `FIP_OUT` env override → per-date output files, no clobbering;
(2) **fixed a latent bug** — the by-rating index was a hardcoded 6-10 dict, wrong for any other date; now pulled
**date-matched** via `oas_on(OAS_WB, VAL)` (`FIP_OAS_WB` overridable). Verified: 6-10 reproduces the old hardcode
(148/227/302/453/741/945/1704), 3-31 gives the crisis-peak index (246/403/549/731/1112/1537/3093). 26/26 green.

**Open / next**
- **Ask Mario/colleague the BT marking date/source** (evidence above) — OAS-level interpretation, not a pipeline blocker.
- GBP ×2: needs a GBP replacement curve or `bootstrap` variant-isolation (parked, non-blocking).
- Position-level risk (portfolio DV01/duration via `mv_base_usd` × per-100 sensitivities); golden tests for
  `calibrate`/`risk`.
- EIR (IFRS-9) after the v1 Mario report + spec confirmation.

---

## 2026-06-30 — FX resolved (custodian base-USD columns) + 3-31 flat-file prep
**Commit:** `[TO FILL]`
**Author:** charlieee0712

- **FX self-conversion REMOVED — the custodian pre-converts.** Probed the master: it carries paired
  `… - base` / `… - local` columns, and our loader already reads the **base-USD** ones — `BU` = **'Market value
  - base'** (USD), `Z` = 'Book cost value - base' (USD). Verified on EUR bonds (e.g. `…22656W` BU 1,731,459 ==
  local 1,304,104 / fx 0.7532; sibling `BV` = 'Market value - local' = 1,304,104). ⇒ per Mario, **no self-FX**:
  dropped `loaders.to_usd`; the driver now takes position MV from `BU` directly (`mv_base_usd`). Kept `currency`
  (AJ) — still needed to route each bond to its own-ccy **pricing** curve (**MV basis ≠ pricing curve** — Mario's
  warning, don't conflate). `fx_rate` (BB) kept as a reference/audit link only. 26/26 golden tests green;
  implied-OAS / risk table **unchanged** (per-100, FX-independent).
- **3-31 flat file (Mario→Liping) — the caveat-1 fix, prepped, awaiting the file.** Mario gave Liping a flat file
  with **all 2009-03-31** yield curves (the authoritative holdings-date curve). Plan: feed it through the existing
  bootstrap and swap `VAL`→2009-03-31; the near-maturity OAS distortion should clear (each short bond gets its
  true residual horizon). **Integration seam =** `bootstrap.load_par_curve(txt, date)`'s contract — it returns
  `(tenors_years_ascending, par_pct)`; the 3-31 adapter only needs to emit that same tuple per (currency,
  2009-03-31), then `bootstrap()` does the rest unchanged. **Need from Liping's file** to write the adapter fast:
  layout (one file all ccys vs per-ccy), date/tenor encoding, and units (decimal vs %). The **2 GBP** curve-blocked
  bonds may also resolve if the 3-31 file carries GBP — revisit together.

**Open / next**
- Get Liping's 3-31 flat file → write the adapter → re-calibrate at 3-31 → expect near-maturity OAS to normalise.
- Position-level risk (use `mv_base_usd` × per-100 sensitivities): portfolio DV01 / duration. Golden tests for
  `calibrate` / `risk`.

---

## 2026-06-30 — OAS REDEFINED as a calibration factor (Mario call) + implied-OAS & risk-metric layer
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Redefinition (Mario, phone).** OAS is a **calibration factor, NOT a pricing input.** New flow:
(1) back out each bond's **implied OAS** from the custodian price `BT` (solve OAS s.t. model clean = `BT`);
(2) on that calibrated model compute **risk metrics** (duration / DV01 / convexity / Greeks). The deliverable
is the risk metrics; implied OAS is the intermediate product. This **moots v1's 6.4% IG dispersion** (no
rating-average OAS forced onto single names) and **changes the data plan**: the WRDS/Bloomberg pulls for
*distressed* and *sector* OAS are **CANCELLED** (each bond's OAS now comes from its own `BT`). FISD (MTN +
callable terms) may still be needed — risk metrics need each bond's full cash flows — but that's a
*pricing/terms* need, unrelated to OAS; still gated on WRDS account activation.

**Implemented (on 47, default corrected engine; 26/26 golden tests still green).**
- `src/pricing/calibrate.py` — `implied_oas(target_clean, …)`: Brent root-find of the flat OAS s.t.
  `price_bond(...).clean == BT`. Clean is strictly decreasing in OAS ⇒ unique root; auto-widening bracket.
- `src/pricing/risk.py` — `risk_metrics(...)`: effective **duration / DV01 / convexity** by ±1 bp central
  difference. Key identity: `price_bond` adds OAS flat to the continuous zero, so **bumping OAS ≡ a parallel
  curve shift** — no curve object is mutated. Duration/convexity use the dirty (full) PV; DV01 = price change
  per +1 bp (per 100; ×par/100 for a position).
- FX: `loaders.py` now carries `currency` (`AJ`) + `fx_rate` (`BB`) + a `to_usd()` helper. **BB is quoted
  LOCAL-per-USD** (JPY 98.77, GBP 0.70, EUR 0.75 @ 2009) ⇒ local→USD is **÷ BB** (NOT the spoken "× rate" —
  confirm w/ Mario; also confirm whether the stored MV/par are already base-USD).

**Results @ 2009-06-10, canonical 476** (`outputs/implied_oas.csv`).
- **Calibration exact**: `|clean(implied_oas) − BT|` max **2.2e-8**. **475/476 implied OAS > 0** (1 negative).
- **Risk metrics validated**: numerical effective duration == continuous Macaulay (`Σ tᵢ·PVᵢ / P`) to **1e-7**;
  sane (~10y → dur ≈ 6.6, DV01 ≈ 0.069, cvx ≈ 56; 30y AA → dur ≈ 12.3, DV01 ≈ 0.13, cvx ≈ 244).
- **Implied OAS vs rating** (median bp): AAA 176 / AA 390 / A 292 / BBB 414 / BB 1374 / CCC 2585 — broadly
  monotone, aligned with the v1 index OAS (148/227/302/453/741/1704) but **wider, with name dispersion**, and
  **distressed clearly larger** (as Mario expected).

**Three caveats found (pasted to the user — need a decision).**
1. **Near-maturity distortion.** Bonds maturing within ~6 mo of 6-10 get inflated / negative implied OAS
   (a 5-day AA → **1372 bp**; the lone negative is a 35-day A → −177 bp). A tiny BT-vs-model price gap ÷ a
   near-zero horizon annualises to a huge "spread"; the gap is mostly the **70-day 3-31(holdings)/6-10(curve)
   mismatch**. ⇒ for **calibration** the 3-31 date-match question **REOPENS** — different from the v1 *rating-OAS*
   result (where 3-31 hurt): a 3-31 curve+date gives each short bond its true residual horizon and cleans the
   short end. Ties to the still-open **"confirm BT's marking date/source."**
2. **17 / 476 canonical bonds are EUR/GBP**, not USD (the book is **not** all-USD: 459 USD + 16 EUR + 1 GBP,
   `TNTG…` ISINs). They're being priced on the **USD** curve (as v1 silently did) ⇒ their implied OAS is a
   USD-vs-EUR-curve artifact. The EUR/GBP par curves **are** in `data/` ⇒ price them on their own-ccy curves
   (v1.5). Surfaced by the FX work.
3. **Distressed implied OAS** (BT 11–35 → OAS up to **~11,800 bp**) is a **recovery-driven plug**, not an
   economic spread — fine as a calibration factor, not interpretable as credit.

**Recon — legacy callable/option engine (background agent, read-only).** All option/Greek code is in
`Project Pricing…/Module1` (`extracted/project_vba.txt`, 11,983 lines). **The straight callable/puttable engine
is `BondOAS`** (l.4397-5861) — a **binomial short-rate/credit lattice** (0.5/0.5), `analysisType` 2=callable /
3=putable / 4=sink / **5=solve implied OAS** / **6=±10 bp effective duration**. ⇒ **Mario's redefined flow
(implied OAS → duration) literally IS the legacy `BondOAS` design.** `CBondPrice` (l.3904-4394) is a
**convertible** pricer (CRR equity tree + Tsiveriotis-Fernandes), **not** the callable target — porting note.
Greeks (l.6928-7225) are closed-form **Black-Scholes equity** option Greeks (for convertibles). **No
DV01/convexity/Macaulay anywhere in legacy** (only ±10 bp effective duration) ⇒ our `risk.py` fills a real gap.
Both callable engines build their **own** rate lattice (not the bootstrapped curve) ⇒ a v2 port re-points them
at `ZeroCurve`.

**Caveats — HANDLED this session (per Mario).** (1) near-maturity `<1y` now flagged (`calibrate.near_maturity`)
and **excluded from the by-rating medians** (16 bonds; kept in the CSV); the 3-31 calibration-date question stays
open. (2) **EUR/GBP FIXED** — `ZeroCurve.from_currency` routes by `currency`; the **15 EUR** re-priced on the EUR
curve tighten implied OAS **~20–55 bp** (EUR rates > USD in 2009); the **2 GBP** can't bootstrap (GBP par
non-arb-free at the 3y node @ 2009-06-10 — `bootstrap()` builds all variants together so the whole curve fails)
→ skipped+flagged for follow-up (nearby GBP date / bootstrap robustness). (3) distressed → `recovery-plug` flag
(BT<50) + a distress-excluded median. **Refined by-rating implied OAS (excl. near-maturity, own-ccy curves; bp):**
AAA 171 / AA 386 / A 291 / BBB 413 / BB 1374 (855 excl-distress) / CCC 2585 (2279) — **A & BBB land on the index
(302/453)**; **AA wide (386 vs 227) = the AA-financials sector effect** (real, not an artifact); HY wide = distress.
New code: `zero_curve.from_currency`, `calibrate.near_maturity`, `scripts/calibrate_risk.py`. Also scrubbed a
client-ISIN leak from `docs/wrds_data_plan.md` and `.gitignore` now blocks all of `data/`.

**Open / next**
- **Decide (Mario):** (a) calibration date — keep 6-10 or use a 3-31 curve+date to fix the short end (needs the
  3-31 curve source / BT date confirmation); (b) FX direction (÷BB) + whether MV/par are already base-USD;
  (c) price the 17 EUR/GBP names on their own-ccy curves now (v1.5) or defer.
- Then: position-level risk (×par; portfolio DV01 / duration), spread / key-rate durations.
- v2 callables: port `BondOAS` (lattice), re-pointed at `ZeroCurve`; needs vol + call/put schedules (FISD).
- Amend `docs/wrds_data_plan.md` (Parts 2 & 3 — distressed/sector OAS — cancelled; Part 1 FISD still maybe).
- Commit the calibrate/risk layer + FX on a fresh branch (currently scp'd to 47, uncommitted).

---

## 2026-06-29 — WRDS data-pull plan recorded (env ready; blocked on account activation)
**Commit:** `[TO FILL]`
**Author:** charlieee0712

- **47 ↔ WRDS confirmed reachable** (`wrds-pgdata.wharton.upenn.edu:9737` OK; general outbound OK —
  pypi/FRED hosts also reachable, so the old "FRED unreachable" was the 3y data-truncation, not the network).
- **Env prepared on 47** (`PengSX` conda): installed `wrds` + `psycopg2-binary` (imports OK,
  `wrds.Connection` present). Side effect: pandas **2.1.1 → 2.2.3** — verified harmless (pricing byte-identical;
  **golden suite 26/26**). Offered to pin pandas back if the colleague's other work needs 2.1.1.
- **Blocked:** user's WRDS account is **inactive** → must be reactivated on the WRDS portal (annual
  re-validation / rep approval). Pull cannot run until then.
- **Plan written → `docs/wrds_data_plan.md`** (execute-ready). Three pulls keyed by **ISIN→CUSIP**:
  (1) **Mergent FISD** `fisd` — rescue the 135 MTN terms + callable call schedules → expand canonical >476;
  (2) **Enhanced TRACE** `trace` — real 2009 marks for the 20 distressed BB/B/CCC names (index OAS can't
  recover them); (3) **industry×rating spreads** — self-built (FISD SIC + TRACE) to narrow the AA-bank
  sector-vs-index gap.
- **Technical decisions baked into the plan** (upgrades over the raw spec): confirm all table/column names via
  `describe_table` before bulk pulls; prefer direct ISIN join (CUSIP-derived fallback); apply **Dick-Nielsen**
  cleaning to Enhanced TRACE; Part 3 is a **Z-spread computed by inverting our own `price_bond`** (≡ OAS for
  option-free; drops straight into our engine; median per rating should ≈ the ICE index OAS = built-in
  validation); **QA-gate the FISD join on the 476 known-terms bonds** before trusting it for the 135 MTNs;
  client CUSIP/ISIN lists + all pulls stay **git-ignored** (`data/wrds/`).
- Next on live connection: smoke query → promote skeletons to a tested `src/dataio/wrds_pull.py`.

---

## 2026-06-29 — Re-verified the BondPrice discounting "bug" from scratch (Liping's challenge)
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Context.** Liping questioned the 2026-06-27 call that `exp(−t·z_semi)` is a VBA bug, and flagged that
our convention description was self-contradictory. Re-investigated from the raw VBA — not defending the
prior conclusion.

**Findings (verified, not code-reading alone):**
- **Read the real `BondPrice`** (decompiled `Pricing File.xlsm`/`vbaProject.bin` → `Bootstrapping.bas`
  via olevba on 47). `BondPrice` (l.108) and `BondPrice2` (l.487) BOTH bootstrap a **semiannual** zero
  `z=2·((1/DF)^(1/2t)−1)` (l.346/364) then discount it with **continuous** `exp(−t·z)` (l.449); no
  compensating step. (Our earlier line-refs 766–818 actually pointed at `BondPrice2` — identical
  convention, so the conclusion held.)
- **Root cause of the doc contradiction Liping caught: TWO bootstraps in legacy.** (i) auditable routine
  = **continuous** (`z=−ln(DF)/t`), what our `bootstrap.py` ports; (ii) `BondPrice`'s embedded bootstrap
  = **semiannual**. CLAUDE.md described only (i) as "the" convention while calling `exp(−t·z)` a bug —
  logically backwards *if* z were continuous. Fixed the docs to distinguish them.
- **Par-bond self-check = decisive proof.** A bootstrapped curve must reprice its own par bonds to 100.
  Under the VBA's `exp(−t·z)`: 5y→99.90, **10y→99.67**, 25y→99.20 (all below par). Under the consistent
  `(1+z/2)^(−2t)`: **100.000000** at every tenor. ⇒ the VBA discount is provably inconsistent with the
  VBA's own curve → under-prices. (Node DF too low −0.11% @5y, −0.43% @10y, −1.31% @20y — reproduces the
  6-27 numbers exactly.)
- **Module check** (sample bond A 5.55% 2017, 2009-06-10 curve): VBA-literal **113.9073** vs consistent
  **114.1365** = −0.20% (pure convention). Our `price_bond` default **114.1361** (= consistent to
  −0.0004%; residual = our 41-tenor vs VBA 9-anchor curve build, NOT the convention); our **`vba_compat`
  113.9073 = VBA-literal to 0.0000% (exact)**.

**Verdict.**
- **(a)** The VBA bug is **real** (semiannual zero discounted continuously; fails its own par self-check).
- **(b)** Our fix is **correct, not a regression** (default reprices par to 100). **No rollback.** The v1
  report's "corrected the VBA discounting bug" **stands**.
- **(c)** `vba_compat` reproduces legacy **exactly** (0.0000%).
- **Direction:** the *price* direction we documented (VBA under-prices) was **correct**; the only thing
  "backwards" was the convention *description* (continuous vs semiannual bootstrap) — now fixed.

**Impact scope (so no future session over-reads this).** The convention fix is worth only ≈**0.2% @8y**
(node DF −0.43% @10y, grows with maturity), **far below v1's 6.4% IG dispersion**. Signed median ≈0
whether default or vba_compat ⇒ **this does NOT change the v1 validation conclusion.**

**Artifacts.** Line-faithful transcription kept at `47:/tmp/convention_test.py` (re-runs the par
self-check + sample bond). Docs updated: CLAUDE.md «Conventions», this entry, `bond_price.py` docstring.

---

## 2026-06-27 — EIR located: a requirement, not legacy code (implement per IFRS-9)
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- Searched ALL legacy code for EIR / amortised cost: `Pricing File.xlsm` (4 sheets + ~2k VBA lines) and
  `Project Pricing Fixed Income Instruments.xlsm` (`Module1`/`Module2` = **11,983 VBA lines** + sheets).
  **Zero hits** for amort / effective-interest / EIR / book-value / constant-yield. The CEO reference sheet
  `Bond Px 4 Bonds w Diff Ratings` is the **Uganda CreditMetrics demo** (rating → sovereign-country curve +
  1y-forward revaluation), NOT EIR.
- ⇒ **EIR is a requirement, not code.** Implement per **IFRS-9 amortised cost** (constant-yield amortisation).
  **No legacy golden output to reconcile against** (unlike BondPrice).
- **Spec preset (confirm with Mario/CEO at the v1 report):**
  - **Q1** master `Book cost` (Z) = **amortised carrying value** (data strongly suggests — another session:
    book cost per-100 median 99.82, hugs par, corr −0.13 with BT, near-maturity closer to 100; typical of
    amortised cost, not original purchase cost; tail exceptions exist). ⇒ amortised cost at valuation ≈ Z, and
    EIR is computable **without a purchase date** (which is absent from the master's 131 columns).
  - **Q2** deliverable = per-bond {effective yield, amortised cost} + an **amortised-cost vs market
    (bootstrap+OAS)** comparison table.
  - **Q3** scope = IFRS-9 amortised cost, carried at the book effective yield, **independent of the market curve**.

**Open / next**
- **Do NOT implement EIR yet.** Order: (1) report v1 to Mario + confirm the EIR spec; (2) then implement.

---

## 2026-06-27 — Batch pricing + OAS reconciliation; v1 success criterion + method boundaries
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- **Batch-priced the canonical 476** on the 2009-06-10 curve (corrected B). 462 semiannual + 14 annual
  (`price_bond` generalised to `freq`), 0 unpriceable. Reconciled vs custodian BT (price) / BU (MV).
- **OAS=0 result VALIDATES the engine.** Near-maturity high-grade bonds (credit ≈ 0) tie to BT to
  **<0.2%** (BBB +0.02% / A −0.17% / AA +0.19%) — proving curve + discounting + the ②③ conventions +
  the 70-day holdings/curve mismatch together contribute <0.2%. The systematic +22% median gap is
  entirely the missing credit spread (largest for low rating / long duration) — exactly what OAS fixes.
- **Rating OAS (EXACT, from the workbook) — v1 result.** Precise 2009-06-10 OAS read from
  `Pricing File.xlsm` / `OAS Credit Curves` via **`src/credit/oas.py`** (`oas_on`): AAA 1.48 / AA 2.27 /
  A 3.02 / BBB 4.53 / BB 7.41 / B 9.45 / CCC 17.04 %. IG (AAA-BBB, n=456) median |diff%| **21.3% → 6.43%**,
  **signed median −0.41% (UNBIASED — curve+OAS centred on BT)**; 39% within 5%, 66% within 10%. HY (n=20)
  137% → 23% (signed +23 — does not converge → v2). Golden `tests/test_oas.py`. Saved `outputs/recon_oas.csv`.
- **v1 verdict — VALIDATED (success), framed as bias vs dispersion (not "6.4% > 5%").**
  - *Is the method correct?* → **UNBIASED**: IG signed median **−0.41% (≈0)**, curve+OAS centred on BT;
    with OAS=0 near-maturity high-grade <0.2%. ⇒ bootstrap→rating-OAS→discount is correct.
  - *How precise?* → **|diff%| median 6.4% is DISPERSION, not bias** — individual-name scatter around the
    index rating OAS (±300 bp normal in 2009), the direct result of v1's design choice (boundary ①: one
    index OAS per rating, no name/term structure). Distress removal leaves it 6.1% ⇒ broad dispersion, not
    outliers ⇒ a **known design boundary, not a bug**.
  - ⇒ **Not a near-miss failure; "success, precision to improve in v1.5."** Precision is limited by the
    index-rating-OAS design, which is explained and has a clear narrowing path.
- **Narrowing path (priority) — REVISED after the 3-31 experiment (below); the residual is in OAS
  *granularity*, not the date:**
  ① **Finer OAS (sector / quality / name)** — the ONLY real path to <5% (v2).
  ② **AA financials** (a concrete sector-OAS case: banks trade wider than the AA index OAS).
  ③ **Index OAS has no term structure** → a duration-based credit-spread curve (v2).
- **[NEGATIVE RESULT — tested 2026-06-27 — 3-31 date-match is a DEAD END, do not retry].** Hypothesis was
  that the 70-day gap (3-31 holdings vs 6-10 curve) inflated the residual; **refuted.** Re-pricing AS-OF
  2009-03-31 (a **3-31 UST curve from FRED `DGS*`**, validated same-source against the 6-10 txt row, **+**
  3-31 OAS, fully date-matched to BT) makes IG **worse**: median |diff%| **6.43% → 11.14%**, signed
  **−0.41% → −6.70%**. Cause: 3-31 is the **crisis-peak OAS** (BBB **7.31%** vs 6-10's 4.53%; CCC 30.93% vs
  17.04%) — the peak spread overwhelms the lower 3-31 rates, so the 3-31 **total** discount rate is *higher*
  and prices fall below BT. ⇒ **BT aligns with ~6-10 (tighter) spreads, not the 3-31 peak; the 70-day date
  gap is NOT a precision lever.** This independently **confirms** the ~6.4% residual = index-OAS dispersion
  (not date) — a harder proof than "distress removal leaves it 6.1%". *(Earlier this entry called the 3-31
  curve the "biggest lever" — that is now refuted; kept here with data so no future session retries it.)*
- **One-liner for Mario/Liping:** "bootstrap→rating-OAS→discount validated for ordinary IG credit, unbiased
  vs BT (signed median ≈0); single-bond precision median ~6% is limited by the inherent dispersion of the
  index rating OAS (a known design boundary), with a clear narrowing path — the biggest being the 3-31 curve
  to remove the 70-day date mismatch. HY / distressed / callable are v2 as planned."
- **FRED historical OAS no longer free** (ICE truncated to a rolling 3y window in April 2026; both the API
  and fredgraph.csv only serve recent data — WebFetch 403, curl date-params ignored, Wayback unreachable).
  → **RESOLVED** by reading the workbook's `OAS Credit Curves` archive (full daily 1997-2025) instead.

**v1 success criterion (LOCKED with the team's framing)**
- **NOT** "all 476 tie to BT" — impossible; distressed names can't be recovered by a rating-average OAS.
- **v1 succeeds if** investment-grade, non-distressed bonds price within a reasonable band of BT (~5%)
  via **bootstrap → rating OAS → discount**. That proves the method works for ordinary credit.
- **Distressed single-names and callables are v2** (need single-name market price / recovery, or an option
  model) — the same "needs richer inputs" bucket. This gives an objective yardstick for Mario/Liping.

**Method boundaries (residual that is NOT a bug)**
1. **Flat OAS, no term structure.** ICE BofA OAS is one index-level spread per rating, added flat across
   all tenors → short end over-priced, long end under-priced. v1-acceptable (CEO's "Bond Px 4 Bonds" uses
   flat OAS); part of the post-OAS residual is this, not an error.
2. **Index OAS ≠ single-name distress.** The CCC index OAS is the average of *still-trading* CCCs; it
   cannot reproduce a near-default name already marked on recovery (BT 12–29). Adding OAS lowers such names
   but they stay well above BT — a method boundary, → v2.

**Open / next**
- **Finer OAS (sector/quality/name)** is now the #1 v1.5/v2 lever to tighten IG (the 3-31 date-match was tested
  and refuted, above). **Confirm BT's marking date/source** with the colleague — a data-understanding item
  (6-10 fits a nominally-3-31 BT), no longer a precision lever.
- EIR / amortised-cost method (CEO's 2nd method) — possible lead in `Pricing File.xlsm` / `Bond Px 4 Bonds w Diff Ratings`.
- v1.5/v2: sector OAS (AA financials), term-structure OAS, distressed single-names (market price/recovery), callables.
- Commit the pricing layer (ZeroCurve + bond_price + oas + recon) on a fresh branch after the universe PR merges.

---

## 2026-06-27 — Curve layer (ZeroCurve) + BondPrice port; corrected the VBA z_semi discounting bug
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- **ZeroCurve** (`src/curves/zero_curve.py`): thin wrapper over the validated `bootstrap()`; serves
  continuous zero rates + DFs (+ optional OAS spread) with linear interpolation. Bootstrapped the
  **2009-06-10** USD curve and sanity-checked vs actual June-2009 UST (3m 0.18% … 10y 3.98% … 30y
  4.76%): post-crisis ZLB short end, steep upward, zero>par, DFs sane. ✓
- **BondPrice ported** (`src/pricing/bond_price.py`, curva=1 spot). Cash-flow conventions copied
  verbatim from Bootstrapping.bas: **ACT/364** (t = days/364), **182-day backward** coupon schedule
  from maturity, semiannual coupon = rate/2·100 (+100 principal at maturity), accrued =
  coupon·(days since last coupon)/182, clean = dirty − accrued. Verified line-by-line on 5 sample
  bonds (2–10y); price behaviour correct (premium ∝ (coupon − yield)·duration).
- **z_semi discounting bug — found, verified, CORRECTED.** The VBA discounts each cash flow as
  `exp(−t·z_semi)` (z_semi = semiannual-compounded zero) instead of its own bootstrapped factor
  `exp(−t·z_cont)` = DisCF — it computes the correct DF and **discards it**. Mixing a semiannual rate
  into a continuous formula systematically **under-prices**: node-level DF too low by −0.01% @2y,
  −0.11% @5y, **−0.43% @10y**, −1.31% @20y; bond clean price too low −0.009% @2y → **−0.285% @10y**.
  Verified by (a) reading the full BondPrice (502–818) — no compensating step after the
  `exp(−t·z_semi)` discount — and (b) numerically on the real 2009-06-10 curve. **Decision** (per the
  CEO's "dedicated, correct, extensible module" goal): discount with the bootstrapped DF by default;
  keep `vba_compat=True` to reproduce the legacy `exp(−t·z_semi)` exactly, used only to explain the
  reconciliation gap. Recorded in the `bond_price.py` docstring.
- Conventions ②③ (182-day schedule, ACT/364) are VBA *choices* — kept as-is, flagged in code as
  known sources of gap vs the custodian's BT/BU/DI (calendar coupon dates + ACT/ACT or 30/360), not bugs.

**Open / next**
- After sign-off: batch-price the canonical **476** (OAS=0), then add rating OAS, then reconcile vs
  gold `BT/BU/DI` (expect a gap: 70-day holdings/curve mismatch + ②③ conventions + model-vs-mark).
- (cheap, optional) Ask the colleague for the VBA tool's clean price on ONE of these 5 bonds to pin
  the z_semi bias empirically against the real sheet (our finding is code-reading + replication).
- Pricing layer (ZeroCurve + bond_price + this entry) is uncommitted; commit on a fresh branch after
  the `feat/universe-pipeline` PR merges.

---

## 2026-06-27 — Server 47 live: env + data + bootstrap reconciled + universe pipeline
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- **Server 47 stood up.** Key-based `ssh 47` verified; cloned the repo; built `.venv` with
  `--system-site-packages` so it reuses the conda env's *already-compiled* numpy 1.26.1 /
  pandas 2.1.1 / scipy 1.11.3 / openpyxl 3.1.2, and only pip-installed pytest. Why: CentOS 7
  (glibc 2.17, gcc 4.8.5) can't build modern wheels from source, and the Tsinghua mirror ships
  pandas 2.3.3 as **sdist-only** so a naive `pip install -r` tried to compile pandas and failed.
  All five satisfy `requirements.txt`.
- **Data on 47**: scp'd the 3 inputs into `data/` (git-ignored by extension) and unzipped —
  `data/USD_Yield_Curve.txt` (+26 others), `data/Bootstrapped/US_yield_curves.csv`,
  `URS …V Mainak.xlsx`. The two `.xlsm` stay local until the BondPrice port.
- **Bootstrap golden master reconciled** (US, 2024-01-16). Adopted **segmented** tolerances in
  `tests/test_bootstrap.py` (not one blanket threshold — so the exact columns can't hide a
  future regression):
  - **Annual / Semiannual rates — RED LINE, kept strict `< 1e-9`** (observed 2.7e-15 / 4.4e-15,
    bit-exact). The OAS pricing foundation; deliberately not relaxed.
  - Quarterly rate: exact (`< 1e-9`) for every node ≤ 30y; the single 30y+ **extrapolated** tail
    node tolerated `< 1e-4` (observed 2.12e-05 @ 31.08y).
  - Monthly rate `< 0.1` pp; Monthly DF `< 1e-3` (observed 6.72e-04 @ 0.92y); A/S/Q DF `< 1e-4`.
  - **Residual source**: the USD par txt's shortest tenor is **3m**, so the Monthly grid's 1m/2m
    nodes are flat-extrapolated and differ infinitesimally from the VBA's short-end handling; that
    rides the recursive bootstrap `DF_i = f(Σ_{k<i} DF_k)` into the Monthly belly. Compounded by a
    **numpy/pandas version delta** vs the colleague's original validation env (this box: 1.26.1 /
    2.1.1). **Economic impact ≈ 0 — does not affect pricing or OAS.** `test_ratings` stays fully green.
- **Universe pipeline built & validated** (`src/dataio/loaders.py` + `universe.py`). openpyxl loaders
  for the master `Fixed Income` + `Corporate Bonds` tab — column letters confirmed against the V-Mainak
  book (Asset ID=`S`, ISIN=`X`, sub-cat=`U`, S&P=`CM`, Moody=`CL`, par=`CV`, call=`AB`, maturity=`BW`,
  gold `BT`/`BU`/`DI`); the V-Mainak appended cols (`DL` dup Asset ID, `DO`/`DP` ~empty coupon) confirm
  terms still come from the tab. `build_universe` runs Asset-ID join → notch-map → Layer A/B with the
  single-primary-reason LOCKED priority. **Every documented count reproduces exactly** (join 597/135/19,
  rating 712/4/16, Layer-A raw 54/73, MECE total 732) → **canonical 476 @ 2009-06-10** + per-bond
  exclusion log. Golden `tests/test_universe.py`; **22 tests green on 47**. Named `dataio` (not `io`):
  `conftest` puts `src/` at `sys.path[0]`, so an `io` package would shadow the stdlib `io`.

**Open / next**
- **Ask the colleague** (both **non-blocking**): (a) which **numpy/pandas versions** + **golden CSV
  source** he used for the bootstrap validation (his "Quarterly exact / Monthly_DF < 1e-4" is tighter
  than this env reproduces); (b) which **curve date/source** priced the 3-31 book — drives the final
  valuation date + whether prices can tie to the custodian `BT/BU/DI`.
- **Data-quality (defer to pricing):** the `Corporate Bonds` tab has 3 rows with `Freq = "—"`; if any
  are Fixed and reach canonical they'd lack a payment frequency — screen at the pricing stage.
- **Next (curve layer first):** wrap bootstrap output in a `ZeroCurve` class and bootstrap the
  **2009-06-10** USD curve; sanity-check the post-crisis low-rate shape before pricing. Then copy the
  two `.xlsm`, port `BondPrice`, price the canonical 476, reconcile vs `BT`/`BU`/`DI`.

---

## 2026-06-26 — Decisions: valuation date 2009-06-10 + 47 interface (ssh)
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- **Valuation date chosen = 2009-06-10** (first curve after the 2008-11-10 → 2009-06-10 gap;
  the alternative, 2008-11-10, is the crisis trough with an extreme curve).
- Recorded the **reconciliation caveat**: holdings are 3-31, nearest curve is 6-10 (70-day
  mismatch) → computed prices won't tie to the custodian's 3-31 `BT/BU/DI`. The port's
  to-the-digit golden master is the **VBA tool's output**, not the custodian mark; `BT/BU/DI`
  is an independent cross-check only.
- **Interface to server 47 = ssh from the Windows box** (option 2); requires key-based ssh.

**Open / next (server 47)**
- **Ask the colleague**: which curve **date/source** did the original tool use to price the 3-31
  holdings? (Likely a 3-31 Bloomberg curve absent from our txt history.) Does he have the VBA
  tool's **pricing output** for these bonds (= the real pricing golden master)?
- Set up key-based `ssh 47`; clone + venv + `pip install`; copy data; `pytest`.
- Then `src/io` loaders + `universe.build_universe()`; bootstrap the 2009-06-10 USD curve.

---

## 2026-06-26 — Integrate colleague's bootstrap module + adopt src/ layout
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- Reviewed the colleague's validated `bootstrap.py` (faithful par→zero VBA port). Confirmed
  conventions: Excel epoch 1899-12-30, continuous compounding, output cols
  `Maturity, {Freq}_Rate/DF` (rates in percent), `load_par_curve` raises on a missing date.
  Validation (US, 2024-01-16): Annual/Semiannual/Quarterly exact, Monthly < 0.1 pp (short-end).
- Adopted a `src/<layer>/` layout: placed the module at `src/curves/bootstrap.py` and moved the
  rating notch-map to `src/credit/ratings.py`. Root `conftest.py` now puts `src/` on `sys.path`.
- Turned the module's `_self_test` into `tests/test_bootstrap.py` (golden-master; skips when the
  git-ignored data files are absent — point via `FIP_US_TXT` / `FIP_US_GOLDEN`). Fixed the
  `tests/test_ratings.py` import.
- Updated `PROJECT_STATUS.md` (§5 architecture, §4 progress, §3.2 path) and `CLAUDE.md`.

**Open / next (server 47)**
- `pip install -r requirements.txt && pytest` — `test_ratings` green; `test_bootstrap` green once
  the US par-curve txt + golden CSV are present.
- Build `src/io` loaders + `universe.build_universe()`; pick the 2009 valuation date; wrap
  bootstrap output in a `ZeroCurve`; port `BondPrice`; reconcile vs `BT`/`BU`/`DI`.

---

## 2026-06-26 — Lock rating notch-map + implement fip/ratings.py
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- Finalised the rating notch-map (S&P / Moody's granular → 7 FRED parent buckets) and
  implemented it in `fip/ratings.py`, with `tests/test_ratings.py` locking the two red lines:
  IG/HY split (BBB−→BBB, BB+→BB); S&P CC/C & Moody Ca/C → CCC (not default); D/SD → defaulted;
  NR/WR → no-rating; S&P-primary with Moody fallback and default precedence.
- Locked the single-primary-reason priority and MTN handling (`terms-unavailable`: a
  data-availability gap, not a security-type issue — addable later if a terms source appears).
- Added `requirements.txt`, root `conftest.py`; `outputs/` git-ignored (pipeline emits client CSVs).
- Untested pending a Python env (server 47 tomorrow).

**Open / next (on server 47)**
- Implement `loaders` (openpyxl read of master + Corporate Bonds tab) and
  `universe.build_universe()` applying join → notch-map → Layer A → Layer B; emit the
  per-bond exclusion log + canonical universe CSV; run pytest; produce the MECE funnel.
- Then lock the valuation date, bootstrap the ~2009 curve, port `BondPrice`, reconcile vs `BT`/`BU`/`DI`.
- Align module layout with the colleague's bootstrap Python (still to receive).

---

## 2026-06-26 — Master-sheet profiling: ratings, universe funnel, data sourcing
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- Dumped all 131 master `Fixed Income` column names. **Resolved the rating gap**: the rating
  columns exist as "Quality rating - Fitch/Moody/S&P" (`CK`/`CL`/`CM`) — earlier scan missed
  them. Fill-rate: S&P 794/811, Moody 796/811 (~98% of corporates); Fitch empty.
- Profiled key columns: par held = `CV` Shares/Par value (99.9%); custodian `BT`/`BU`/`DI`
  present → use as golden master (kept separate from inputs).
- Built date-independent universe funnel (732 unique corporates by Asset ID):
  - Rating (default precedence): 712 covered / **4 defaulted** / **16 no-rating** (true "neither").
  - Join on Asset ID: **597 matched** / 135 master-only / 19 tab-only.
  - Coupon type (within matched): 543 FIXED / 54 non-vanilla; **73 callable**.
- Locked design: rating S&P→Moody fallback w/ default precedence; join on Asset ID (ISIN
  secondary); par=`CV`; EIR cost=`Z`; golden master separate; callable → v2 (own reason,
  keep call fields); single primary reason per bond by priority.
- Updated `PROJECT_STATUS.md` (§3.2) and `CLAUDE.md` with the deterministic two-layer
  universe pipeline, exclusion taxonomy, and data-sourcing map.

**Open / next**
- Implement the MECE universe pipeline (single primary reason by agreed priority) →
  per-bond exclusion log; build in Python on server 47.
- Lock valuation date (drives Layer B); bootstrap the ~2009 curve.
- Port `BondPrice`; reconcile computed price vs `BT`/`BU`/`DI`.

---

## 2026-06-26 — Onboarding: structural analysis + bootstrap validation
**Commit:** `9b7fe7f` (docs scaffold) · `[TO FILL]` (this anchor update)
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- Mapped all four source workbooks: sheet inventory, column layouts, instrument
  fields, and the pricing/credit logic embedded in cell formulas and VBA.
- Documented the end-to-end pipeline & methodology (bootstrap → rating OAS →
  discount pricing → CreditMetrics overlay) in `PROJECT_STATUS.md`, including the
  exact bootstrap formulas and the FRED ICE BofA OAS source.
- Confirmed the bootstrap formula against the auditable VBA and **reproduced it in
  Python**: Annual / Semiannual / Quarterly **exact (0 error)**; **Monthly within
  0.08 bp** (short-end fill convention).
- Identified the **valuation-date mismatch**: holdings priced 2009-03-31, but the
  bundled bootstrapped CSVs match curve date 2024-01-16 (RMSE 0); 2009-03-31 is
  missing from the curve files (gap 2008-11-10 → 2009-06-10). Impact: 123 priceable
  bonds at 2024-01-16 vs 667 at 2009-03-31.
- Reconciled the corporate-bond universe into three counts (811 / 676 / 641).
- Confirmed **Bloomberg dependency is cut** (txt par curves + FRED OAS).
- Established the repo, `.gitignore` (excludes all client data), and project docs
  (`PROJECT_STATUS.md`, `WORKLOG.md`, `CLAUDE.md`).

**Open / next**
- Decide canonical valuation date + universe; bootstrap a ~2009 curve for the real book.
- Build `io` loaders + `instruments.Bond`; map rating + holdings from the master sheet.
- Port `BondPrice` (from `Pricing File.xlsm → Bootstrapping.bas`) into `pricing`.
- Locate & port the EIR (amortised-cost) method; then start the CreditMetrics layer.

---

<!-- Template for new entries:

## YYYY-MM-DD — <short title>
**Commit:** `<hash>`
**Hours:** `[TO FILL]`
**Author:** <name>

**Done**
- …

**Open / next**
- …
-->
