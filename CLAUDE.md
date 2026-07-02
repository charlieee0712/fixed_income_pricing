# CLAUDE.md — persistent context for this project

Operating memory for future sessions. Read `PROJECT_STATUS.md` (full methodology +
architecture) and `WORKLOG.md` (history) alongside this. Keep this file terse and
high-signal; update it when a stated fact changes.

## What this project is
Port a legacy Excel/VBA fixed-income pricing toolkit to a structured, scalable
**Python** module. **Corporate bonds = first reference implementation**; must extend
to MBS/CMBS/ABS/CMO/callables and a CreditMetrics risk layer.
Repo: `github.com/charlieee0712/fixed_income_pricing` (keep **private** — references a client portfolio).

## Environment (important)
- **No usable local Python** on the Windows machine (only a Microsoft Store stub).
  Run code on **server 47** or a real local install. Don't assume `python` works locally.
- **Interface to 47 = ssh from the Windows box** (chosen). Needs **key-based ssh** (the Bash
  tool is non-interactive — a password prompt hangs). Loop: edit locally → push → `ssh 47
  'cd <repo> && git pull && pytest'`. Data lives on 47 (git-ignored). Repo on 47 = **`/home/PengSX/fixed_income_pricing`** (conda env `PengSX`);
  run scripts via **`PYTHONPATH=src python3 scripts/…`**, run tests via **`.venv/bin/python -m pytest`** (pytest
  is in the repo `.venv`, NOT conda's `python3` — bare `python3 -m pytest` fails "No module named pytest"). Quick
  iter: `scp` the file to 47 then run (working-tree edit), or push + `git pull`. Use `ssh -o BatchMode=yes 47`.
- To read the Excel files without Python, a PowerShell sheet-decoder approach works
  (unzip the xlsx/xlsm and parse `sharedStrings.xml` + `worksheets/sheetN.xml`).
- **No Bloomberg.** Inputs are exported `*_Yield_Curve.txt` + FRED OAS (the VBA's
  `GetBloomberg` is replaced).
- **Never commit client data** — `*.xlsx/*.xlsm/*.zip/*.csv/*.txt` are git-ignored.

## File roles
- `All_Yield_Curve.zip` — raw **par-yield** history per country/ccy (`Date(Excel serial), 0.25..30`).
  Country-name files alias currency-code files (JAPAN ≡ JPY). Bundles
  `Zero_Yield_Curve_VBA_Code.txt` = auditable bootstrap VBA (replaces old `Veloz`).
- `Bootstrapped-*.zip` — Stage-1 output, **demo @ 2024-01-16** (not the pricing basis).
- `Pricing File.xlsm` — reference VBA: `Bootstrapping.bas` (1706 lines: **`BondPrice`**,
  `ZeroCalc`, `Parcurve`), `Matrix.bas`, `Copulas.bas`. **Port `BondPrice`** — do **not**
  port the ~11k-line `Module1` in the other workbook *for v1* (v2 callables DO port `BondOAS` from it — see below).
  Contains a *separate* Uganda demo.
- `Project Pricing Fixed Income Instruments.xlsm` — legacy risk-system sample (huge `Module1`). **v2 callable
  source** (recon 2026-06-30; VBA → `47:extracted/project_vba.txt`): **`BondOAS`** l.4397-5861 = straight
  callable/putable/sink **binomial short-rate lattice** (`analysisType` 5=implied-OAS, 6=±10bp eff-dur = the
  redefined flow); `CBondPrice` l.3904-4394 = **convertible** (CRR equity tree, NOT the callable target); BS
  equity Greeks l.6928-7225; **no DV01/convexity/Macaulay in legacy**.
- `URS …xlsx` — **the portfolio to price**: a US engineering-company pension, USD ISINs,
  positions split by asset type; `Corporate Bonds` tab is current focus.

## Two clients — do NOT merge
- **URS** = US pension (USD) → the pricing target.
- **Uganda** (UGANGB govt bonds, UGX) = a separate example, only in `Pricing File.xlsm`.

## Conventions (validated)
- Bootstrap recursion (shared): `cpn=100·par/f`; `DF_i=(100−cpn·Σ_{k<i}DF_k)/(100+cpn)`.
  ⚠️ **Two bootstraps exist in legacy** — do NOT conflate (Liping's catch, VERIFIED 2026-06-29):
  (i) the *auditable* routine — **continuous** `z=−ln(DF)/t` — what our `bootstrap.py` ports;
  (ii) `BondPrice`'s **own embedded** bootstrap (`Bootstrapping.bas`) — **semiannual**
  `z=2·((1/DF)^(1/2t)−1)` — what legacy *pricing* actually used. Same `DF`, different expression of `z`.
- **The VBA discounting bug + our fix** (VERIFIED 2026-06-29): `BondPrice` stores a **semiannual**
  zero but discounts it with the **continuous** `exp(−t·z)` (l.449) → convention mismatch,
  systematically **under-prices**. Proof: a curve must reprice its own par bonds to 100 — under
  `exp(−t·z)` they come out **below par (10y → 99.67)**; under the consistent `(1+z/2)^(−2t)` →
  **100.000000**. Our pipeline discounts consistently (`exp(−t·z_cont)`=DF, par→100); **`vba_compat=True`
  reproduces the legacy output EXACTLY** (0.0000% on the sample bond). Effect ≈ **0.2% @8y** (node DF
  −0.43% @10y) — far below v1's 6.4% IG dispersion, so it does **not** change the v1 verdict.
- 41-tenor grid 0.08y…30y; linear interpolation (interior) / linear extrapolation (ends);
  output monthly to ~374 months × {Annual, Semiannual, Quarterly, Monthly}.
- Pricing: discount each cash flow at `z(t)+OAS(rating)`, **linear interpolation** of the
  monthly grid; dirty = Σ coupons·DF + face·DF(T); clean = dirty − accrued.
- **OAS — REDEFINED 2026-06-30 (Mario call): a per-bond CALIBRATION factor, NOT a pricing input.** New flow:
  back out each bond's **implied OAS** from the custodian price `BT` (solve OAS s.t. model clean = `BT`,
  `src/pricing/calibrate.py`), then compute **risk metrics** on the calibrated model (`src/pricing/risk.py`).
  Goal = risk metrics; implied OAS is the intermediate. **Supersedes index-rating-OAS as the endpoint**; moots
  v1's 6.4% IG dispersion (no rating average forced on names). ⇒ WRDS *distressed/sector OAS* pulls **CANCELLED**
  (FISD terms-rescue may still be needed — cash flows for risk metrics, not OAS). Calibration @ 2009-06-10/476:
  exact (`|clean−BT|`<2.2e-8), 475/476 OAS>0. Caveats: near-maturity OAS distorted by the 70-day date mismatch
  (3-31 date-match **REOPENS for calibration**), **17/476 EUR/GBP** (→ own-ccy curves), distressed OAS =
  recovery plug. **Caveats handled (2026-06-30):** near-maturity (<1y) flagged + excluded from medians (16);
  EUR/GBP routed to own-ccy curves via `ZeroCurve.from_currency` (15 EUR fixed → OAS −20..55bp, 2 GBP curve-blocked
  @ 6-10); distressed = `recovery-plug` flag. After fixes A/BBB land on the index (291/413 vs 302/453), AA wide
  (386 vs 227 = AA-financials). **3-31 ADOPTED as calibration baseline (2026-07-02)** — Mario's USD 3-31 curve
  (native schema, no adapter) swapped in; near-maturity distortion cleared (1371→464bp, −177→+199bp), universe
  481 (>476: 5 bonds alive @3-31 that 6-10 dropped), IG medians +~100bp (= the ~100bp-lower curve), risk metrics
  stable (eff-dur +0.13y). 6-10 kept as control. See WORKLOG 2026-07-02. [v1 index OAS below, kept for history.]
- **OAS (v1 index, kept for history)** = **ICE BofA US Corporate/HY** Index OAS, **one flat spread per rating** (AAA…CCC).
  **Historical source = `Pricing File.xlsm` / sheet `OAS Credit Curves`** (full daily 1997-01-02 …
  2025-11-07, 7 buckets; archived before ICE/FRED truncated the free series to a rolling 3y window
  in **April 2026**). Read via **`src/credit/oas.py`** (`oas_on(path, date)` → decimal dict, raises on
  missing date). **Do NOT use the FRED online API for OAS history** — it now only serves the last 3y.
  (UST par yields, by contrast, = FRED **`DGS*`** series — government data, **NOT** truncated — usable for
  any historical date; e.g. the 2009-03-31 curve absent from the txt was pulled from DGS and validated
  same-source against the 6-10 txt row.)
- **Bootstrap module** (`src/curves/bootstrap.py`, colleague's validated port): Excel epoch
  **1899-12-30** (`excel_serial_to_date`); output cols `Maturity, {Freq}_Rate`(percent)`, {Freq}_DF`;
  `load_par_curve` **raises** on a missing valuation date (no silent nearest-date — matters for 2009).
- **Data sourcing (corp)**: join master↔tab on **Asset ID** (`S`↔`Asset Code`, 100%; ISIN
  secondary). Terms (coupon rate/type/freq/maturity) ← `Corporate Bonds` tab (master coupon
  cols are EMPTY). Rating ← master `CM` S&P / `CL` Moody (default precedence; NR→fallback→exclude).
  Par held ← master `CV` Shares/Par value. EIR cost ← `Z`. **Golden master** = `BT` price /
  `BU` MV / `DI` YTM — keep in a SEPARATE reconciliation table, never in pricing inputs.

## Critical corrections (don't re-derive — already validated)
- **Valuation date**: holdings = **2009-03-31**; bundled curves = **2024-01-16** (RMSE 0).
  2009-03-31 is **absent** from curve files (gap 2008-11-10 → 2009-06-10). At 2024-01-16
  only **123/668** corporate bonds are still alive (545 matured); at 2009-03-31, **667**.
  → To price the real 2009 book, **bootstrap a ~2009 curve**; the 2024 CSVs are a demo.
  **Curve date: calibration baseline = 2009-03-31** (Mario's USD curve arrived 2026-07-02, fills the gap;
  matches the holdings date → near-maturity distortion cleared, universe 481). 6-10 kept as control (v1 +
  BT-date evidence). [was "6-10 chosen", pre-3-31-file.]
  ⚠️ Even @3-31 the model reproduces the VBA tool's output, not the custodian mark; **BT marking date/source
  still open** — evidence now points to BT ≈ ~June credit level (see WORKLOG 2026-07-02).
- **Universe = deterministic 2-layer pipeline**, **IMPLEMENTED** in `src/dataio/universe.py`.
  Start = master sub-cat == `Corporate Bonds`, dedupe by Asset ID → **732 unique** (from 811
  rows; no separate MTN sub-cat — MTN = a terms-gap label, not a category). Log every drop with
  ONE primary reason + Asset ID. Counts (all reproduce **exactly**): join **597 matched / 135
  master-only / 19 tab-only**; rating **712 covered / 4 defaulted / 16 no-rating**; Layer-A raw
  **54 non-vanilla / 73 callable**. Priority (LOCKED): `terms-unavailable/unmatched → defaulted →
  no-rating → structured/floating → callable → matured`. Layer A = date-independent, Layer B =
  matured-at-val-date. **Result @ 2009-06-10 (post-priority MECE): canonical 476 / terms-unavailable
  135 / structured-floating 51 / callable 51 / no-rating 9 / matured 6 / defaulted 4.** **@2009-03-31 (adopted
  baseline): canonical 481** (5 more alive — bonds that matured 3-31→6-10 and 6-10 dropped).
  135 master-only = `terms-unavailable` (MTN; terms in neither sheet — **data gap, not security type**).
  Notch-map (S&P/Moody → 7 buckets) implemented in **`src/credit/ratings.py`**. Red lines: keep IG/HY split
  (BBB−→BBB, BB+→BB); S&P CC/C & Moody Ca/C → CCC, **not** default (only D/SD).

## Validated so far
- **Bootstrap ported** (`src/curves/bootstrap.py`, colleague's validated module): A/S exact,
  Q exact ≤30y, Monthly <0.1 pp (short-end fill); golden-master `tests/test_bootstrap.py` uses
  **segmented** thresholds — A/S strict <1e-9 red line; Quarterly terminal-extrapolation node
  (>30y) and Monthly-DF short-end residual carved out (see WORKLOG 2026-06-27). Rating notch-map
  `src/credit/ratings.py` (`tests/test_ratings.py`). Bloomberg cut.
- **Universe pipeline** (`src/dataio/loaders.py` + `universe.py`, run on 47): reproduces the
  documented funnel **exactly** (join 597/135/19, rating 712/4/16, Layer-A raw 54/73, MECE=732)
  → **canonical = 476 @ 2009-06-10**; per-bond exclusion log; golden `tests/test_universe.py`.
- **Pricing + reconciliation** (`zero_curve.py` + `bond_price.py` + `oas.py`, on 47): 2009-06-10 USD curve
  sane vs actual June-2009 UST; priced canonical 476. **v1 method VALIDATED.** *Is the method correct?* →
  **yes, UNBIASED**: IG (AAA-BBB) signed median **−0.4% (≈0)**, curve+OAS centred on BT; plus OAS=0 near-
  maturity high-grade ties BT **<0.2%**. *Precision?* → **~6.4% median |diff%|, which is DISPERSION not bias**
  — name-level scatter around the index rating OAS (±300 bp normal in 2009); a **known v1 design boundary,
  not a bug** (distress removal leaves it 6.1% → broad, not outliers). NOT a "near-miss vs 5%": success,
  precision to improve in v1.5. Narrowing path to <5% = **finer OAS (sector/quality/name), v2** — the
  3-31 date-match is a **tested dead end** (makes IG *worse*, 6.4%→11.1%: the 3-31 crisis-peak OAS overstates
  these holdings' spreads — see WORKLOG). HY / distressed / callable = v2.
- **Calibration + risk layer** (`src/pricing/calibrate.py` + `risk.py`, on 47) — **the redefined direction**:
  per-bond **implied OAS** from `BT` (canonical 476: exact, 475/476>0) → **effective duration / DV01 / convexity**
  (numerical ±1bp = parallel-shift bump; == continuous Macaulay to 1e-7). `outputs/implied_oas.csv`. Driver `scripts/calibrate_risk.py`. **Caveats handled:** `from_currency` routes per-ccy curves (15 EUR
  fixed, 2 GBP curve-blocked), `near_maturity` flags+excludes <1y → A/BBB land on the index (291/413 vs
  302/453), AA wide (386) = AA-financials, HY = distress. See WORKLOG 2026-06-30.
  **3-31 adopted as baseline (2026-07-02):** re-calibrated @2009-03-31 (canonical 481, exact), near-maturity
  cleared, by-rating index now **date-matched** via `oas_on(VAL)`; driver env-parameterised
  (`FIP_VAL_DATE`/`FIP_OUT`/`FIP_OAS_WB`). See WORKLOG 2026-07-02.
- **v2 callable lattice** (`src/pricing/lattice.py` + `scripts/callable_risk.py`, on 47) — **clean standard BDT**
  short-rate tree (fwd-induction Arrow-Debreu calib to `ZeroCurve`, arb-free), **NOT a `BondOAS` replica** (legacy
  unrunnable w/o Bloomberg). Invariant-validated (`test_lattice`, 26). Only **4 genuine fixed callables** in the
  book (46 make-whole → vanilla); lattice moves numbers on ~1 (TNTD04441873 eff-dur 11.56→10.03). Custodian AQ
  ≈ straight dur (doesn't capture the call). **Call price/schedule + σ=0.18 are ASSUMPTIONS** (data gaps; par-call@100
  refuted for TNTD03203204 ⇒ BT≫par-call). Mario Qs: call-schedule source, vol level, BT date. See WORKLOG 2026-07-02.

## Open questions
- **OAS redefined → calibration (2026-06-30; see WORKLOG).** Implied OAS per bond from `BT`, then risk metrics;
  index/sector/distressed OAS no longer external inputs (**WRDS distressed/sector OAS pulls cancelled**). New opens
  for Mario: (a) calibration date — **3-31 ARRIVED & ADOPTED (2026-07-02)**: Mario's USD 3-31 curve (native schema)
  swapped in, `VAL`=2009-03-31, near-maturity distortion cleared (the v1 3-31 *rating-OAS* refutation below does
  **NOT** apply to calibration); (b) **EUR/GBP own-ccy curves DONE** (15 EUR fixed, **2 GBP still curve-blocked** —
  non-arb 3y node, needs a GBP replacement curve or `bootstrap` variant-isolation, NOT a date issue); (c) **FX
  RESOLVED** — custodian base-USD columns (`BU`='Market value - base', `Z`='Book cost - base') read directly, no
  self-convert (`to_usd` removed; `currency` kept for routing); (d) **confirm BT marking date/source — now the key
  open**: two-date evidence shows implied@6-10 ≈ 6-10 index but implied@3-31 sits 143–206bp *below* the 3-31 crisis
  index ⇒ BT embeds ~June credit; affects OAS-level *interpretation* only, not the calibration/risk deliverable.
- ~~3-31 curve = the v1 IG lever~~ **REFUTED (tested 2026-06-27, for the v1 rating-OAS method; REOPENS for calibration — see above):** date-matching to 3-31 (3-31 DGS curve +
  3-31 OAS) makes IG **worse** (6.43%→11.14%, signed −0.41%→−6.70%) — the 3-31 crisis-peak OAS (BBB 7.31% vs
  6-10's 4.53%) overstates these high-grade holdings' spreads; **BT aligns with ~6-10 (tighter) spreads, the
  70-day gap is NOT a precision lever** (real lever = finer OAS, v2).
- **Confirm BT's marking date/source** (colleague) — **now corroborated by the 2026-07-02 two-date calibration**:
  implied OAS @6-10 ≈ the 6-10 index but @3-31 sits 143–206bp *below* the 3-31 crisis-peak index ⇒ BT embeds a
  ~June (post-rally) credit level. Interpretation of the OAS level, not a calibration/risk-delivery blocker.
- ~~Historical OAS source~~ **RESOLVED** — `Pricing File.xlsm` / `OAS Credit Curves` via `src/credit/oas.py`
  (FRED online truncated to 3y in April 2026; the workbook holds the full 1997-2025 archive).
- ~~Canonical universe definition + exclusion list~~ **RESOLVED** — `dataio/universe.py` →
  canonical **476 @ 2009-06-10** + per-bond exclusion log (final valuation date pending colleague).
- **EIR (IFRS-9 amortised cost)** — **a requirement, not legacy code**: searched both workbooks (14k VBA
  lines + all sheets), **zero hits** → implement from the standard, **no legacy golden** to reconcile. Spec
  preset (confirm w/ CEO): `Book cost` (Z) = amortised carrying value (data-inferred) ⇒ amortised cost ≈ Z,
  EIR = IRR(Z, remaining CFs); deliver per-bond {eff. yield, amortised cost} + amortised-cost-vs-market table.
  **Implement only after the v1 Mario report + spec confirmation.**
- ~~Where per-bond rating/holdings are sourced~~ **RESOLVED** — see Data sourcing above
  (rating `CM`/`CL`, par `CV`; join on Asset ID). ~~build the MECE pipeline~~ **done**.

## Target architecture (`src/<layer>/`; root `conftest.py` puts `src/` on path)
- `src/curves/` — ✅ `bootstrap.py` (par→zero, reproduces golden) · ✅ `zero_curve.py` (`ZeroCurve`, linear-interp z/DF + OAS spread; `from_currency` per-ccy curves).
- `src/credit/` — ✅ `ratings.py` (notch-map) · ✅ `oas.py` (per-rating OAS from `OAS Credit Curves`).
- `src/dataio/` — ✅ `loaders.py` (master + Corporate Bonds tab) + `universe.py` (`build_universe`,
  MECE funnel → **canonical 476 @ 2009-06-10**); FRED OAS loader next. (Named `dataio`, **not** `io`:
  `conftest` puts `src/` at `sys.path[0]`, so an `io` package would shadow stdlib `io`.)
- `src/pricing/` — ✅ `bond_price.py` (`BondPrice` port: ACT/364, 182-day schedule, accrued, clean/dirty;
  **default = corrected DF**, `vba_compat` reproduces the legacy `exp(-t·z_semi)` bug; `oas`/`freq` params) ·
  ✅ `calibrate.py` (`implied_oas`: solve OAS s.t. clean=`BT`) · ✅ `risk.py` (`risk_metrics`: effective
  duration / DV01 / convexity by ±1bp = parallel-shift bump) · ✅ `lattice.py` (**v2** callable/putable BDT
  short-rate tree: fwd-induction Arrow-Debreu calib to `ZeroCurve`, arb-free; implied OAS + eff-dur; NOT a
  `BondOAS` replica — invariant-validated; driver `scripts/callable_risk.py`).
- `src/instruments/` (Bond model + cash flows) · `src/risk/` (CreditMetrics, later) · `src/config/`.
- `tests/` — golden-master (`test_bootstrap`, `test_ratings`, `test_universe`, `test_oas`) + `test_lattice`
  (v2 callable-lattice **invariants**: par-reprice/arb-free, callable≤straight≤putable, σ=0 degeneracy). 52 total.
