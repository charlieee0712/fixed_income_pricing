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
- **Client data is now TRACKED in-repo** (policy change 2026-07-08, boss-approved): the client
  portfolio, proprietary workbooks/curves, and derived reports are committed here. The repo **MUST
  stay private** (`github.com/charlieee0712/fixed_income_pricing`). `.gitignore` now excludes only
  build/cache/editor junk (`__pycache__/`, `.venv/`, `outputs/`, `.claude/`, …), not data. [was:
  "Never commit client data — *.xlsx/*.xlsm/*.zip/*.csv/*.txt are git-ignored".]

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
  RESOLVED (2026-07-03, Mario):** by 3-31 the crisis was near its end & spreads had retreated from peak, so BT's
  tighter credit is the real recovering-market mark (not a date mismatch); implied OAS below the 3-31 peak = that
  recovery. 3-31 baseline unchanged (see WORKLOG 2026-07-03).
- **Universe = deterministic 2-layer pipeline**, **IMPLEMENTED** in `src/dataio/universe.py`.
  Start = master sub-cat == `Corporate Bonds`, dedupe by Asset ID → **732 unique** (from 811
  rows; no separate MTN sub-cat — MTN = a terms-gap label, not a category). Log every drop with
  ONE primary reason + Asset ID. Counts (all reproduce **exactly**): join **597 matched / 135
  master-only / 19 tab-only**; rating **712 covered / 4 defaulted / 16 no-rating**; Layer-A raw
  **54 non-vanilla / 73 callable**. Priority (LOCKED): `terms-unavailable/unmatched → defaulted →
  no-rating → structured/floating → callable → matured`. Layer A = date-independent, Layer B =
  matured-at-val-date. **Result @ 2009-06-10 (post-priority MECE): canonical 522 / terms-unavailable
  135 / structured-floating 51 / callable 5 / no-rating 9 / matured 6 / defaulted 4.** **@2009-03-31 (adopted
  baseline): canonical 527** (5 more alive). **Make-whole callables (call date within `MAKE_WHOLE_MAX_GAP_DAYS`=7d
  of maturity, option value≈0) route to VANILLA — enter canonical, flagged `is_make_whole` (46 bonds) — NOT the
  `callable` exclusion (WORKLOG 2026-07-02); only 5 genuine-gap callables stay excluded → v2 lattice.** [was
  canonical 476/481, callable 51 pre-reclassification.]
  135 master-only = `terms-unavailable` (MTN; terms in neither sheet — **data gap, not security type**).
  Notch-map (S&P/Moody → 7 buckets) implemented in **`src/credit/ratings.py`**. Red lines: keep IG/HY split
  (BBB−→BBB, BB+→BB); S&P CC/C & Moody Ca/C → CCC, **not** default (only D/SD).

## Coupon-type routing (Mario 2026-07-08) — read `Coupon_Formula2`, route by structure
- **Directive:** the module defaulted every bond to `F`; now it reads **`Coupon_Formula2`** (Corporate
  Bonds tab, Excel col **M** — Mario said "N", header confirms **M**; N is empty, loader was right) and
  routes by coupon structure. Classifier = **`src/dataio/coupon_types.py`** (`classify_coupon_formula` +
  `ROUTE`), wired into `universe.py` (adds `coupon_class`+`route`; splits the old blanket
  structured/floating funnel bucket). Reconciles **EXACTLY** to Mario's 676-row pivot: **F 617 · floating
  27 · fixed-to-reset 6 · stepped 2 · step-up 1 · zero 1 · defaulted 1 · excluded 21** (in
  `extras["coupon_class_pivot"]`).
- **Route → engine:** F/zero → vanilla · stepped/step-up → vanilla-schedule (Step 3) · floating +
  fixed-to-reset → floating engine (Step 4, TBD) · defaulted → recovery mark (Step 3) ·
  **pass-through/amortizing/na → EXCLUDED per Mario** (16/1/4 = 21; prepayment/amortization models or
  unclassified). Pass-through sheet's Collateral-col loader **kept** for the later MBS phase.
- **Funnel @6-10:** canonical stays **522** but now 100% `coupon_class F`/`route vanilla` — the 1
  `Amortizing` bond coupon_type mislabelled "Fixed" left canonical (correctness fix), a formula-`Fixed`
  hybrid replaced it; **callable 5→6** (a formula-`Fixed` bond coupon_type had mislabelled non-fixed = real
  fixed callable → v2 lattice). `test_universe` +3, **63 green**.
- **FRN legacy = Step-1 recon (NOT ported):** `BondOAS` **analysisType 7/8/9**
  (`47:extracted/project_vba.txt` **l.5693–5829**) = 7 price / 8 implied-OAS (`Veloz` solve) / 9 eff-dur
  (±10bp) on a **curve-forward FRN recombining tree** — floating coupon `Forward = Discount·sloperow` off
  the discount curve; discount `(OAS+Forward)/Freq` on the **same** curve (single-curve, periodic-simple,
  ≤30 steps). **Bloomberg data = substitutable (the callable-schedule pattern):** `swapcurve` short-end
  (EURIBOR `EU000nM` / GBP-LIBOR `BP000nM` / USD-LIBOR `US000nM` or **H.15 `h15tnM` = FRED-able**),
  `multi_cpn_schedule` (steps), `flt_cpn_hist` (spread+resets) → our ZeroCurve forwards + parsed
  spread/schedule. Step 4 method **CONFIRMED 2026-07-08** — plan below.
- **Step 3 DONE (2026-07-08) — simple special types priced.** New `src/pricing/coupon_schedule.py`
  (`parse_coupon_schedule` free-text → `[(eff_date|None, rate_decimal)]` + `coupon_at`; returns
  **None, never a guess**, when a cell has no numeric coupons); `price_bond`/`implied_oas`/`risk_metrics`
  take an optional `coupon_schedule`. Driver routes the 4 **held** special bonds:
  **stepped** TNTD04283895 (A; switch 2006 < val ⇒ flat 7.50%) → clean **210bp**, eff-dur 1.63, joins the
  A median; **zero** TNTD03037132 (BBB, 2037) priced degenerate-vanilla but BT 93.1 ⇒ **OAS −486bp** =
  BT inconsistent with a pure-discount zero (structured payoff) → route `zero-structured`, **excluded
  from medians**; **step-up** TNTD04150829 → `schedule-unavailable` (steps not in workbook — needs a
  terms source like the call schedule) → BT mark; **defaulted** TNTD03037967 (BT 12) → route `recovery`,
  BT mark, **no OAS**. Only `PRICED_ROUTES` {vanilla, make-whole-as-vanilla, vanilla-schedule} feed the
  by-rating medians. `test_coupon_schedule` (+10) → **73 green**.
- **Step 4 plan LOCKED (2026-07-08, Mario) — floating engine; do pure-FRN 27 FIRST, then reset 6:**
  ① fwd projection = **implied forward off our bootstrapped `ZeroCurve`** (`F(t1,t2)=(DF(t1)/DF(t2)−1)/
  (t2−t1)`, simple — matches legacy periodic discounting; Step-1 recon confirmed the legacy tree does
  exactly this). ② discount = **same curve + implied OAS (single-curve)**, matching legacy; **record in
  code/docs that single-curve = 2009 convention, OIS dual-curve = future enhancement** (transparency,
  not now). ③ data subs: USD short-end → **try pure ZeroCurve forwards first** (may need no external
  fixing), else FRED H.15; EUR/GBP → 47 own-ccy curves; **spread parsed from `coupon_formula`**
  ("EURIBOR + 45bp"→45bp, standalone parser + tests); current-reset coupon ← master `Coupon` (D).
  ④ **Fixed→Reset (6, incl perpetual) DEFERRED** — recon each one's terms first (perpetual = no maturity
  ⇒ CF truncation / perp formula); don't batch. ⑤ **no legacy golden (bbg) → invariant tests** (callable
  pattern): spread=0 & flat curve ⇒ price≈par; implied-OAS round-trip; **FRN eff-dur ≪ same-maturity
  fixed (≈ time-to-next-reset)** = the signature FRN check. ⑥ output: 27 floaters → main table
  (route=floating) with implied OAS + duration/DV01/convexity.
- **Step 4 pure-floating DONE (2026-07-08) — `src/pricing/frn.py`.** Coupons = simple forward off our
  `ZeroCurve` + spread; single-curve discount + implied OAS (calibrated to BT). **Effective duration bumps
  the CURVE (reprojects forwards), NOT the OAS** → ~ time to next reset. Bug fixed en route: the stub
  (current) period's forward must start at the true last-reset (t_prev<0), else the par-floater telescoping
  breaks. `test_frn` (7 invariants: par-under-any-shift, OAS round-trip, near-par dur≈0, **dur ≪
  same-maturity fixed even @78y**). Of 27: **18 priced FRNs** — durations SHORT across maturities to 58y
  (the 2066/2067 floaters: eff-dur **~−10.7** vs a ~+20y fixed; near-par ones ≈0; deep-discount ones carry a
  credit-spread-annuity duration, hence negative). **80 green.**
- **Data needed from Mario/Bloomberg** (flagged, gap-blocked, NOT force-priced; empty
  `data/coupon_schedules.csv` seeded `asset_id,effective_date,coupon_rate`): (a) FRN **spreads**
  ("...+ Spread" has no number → folded into OAS); (b) **Fixed→Floating switch dates** (5); (c) **perpetual**
  terms — 2 FRN + 3 reset have no maturity (CF truncation / perp formula); (d) **step-up** coupon table +
  **zero** structured-payoff terms (Step 3); (e) a usable **GBP curve** (non-arb 3y node blocks the 1 GBP
  floater + any GBP bond).
- **Reset-6 (fixed-to-reset) recon done — awaiting approach decision.** 6 deep-discount hybrids (BT 36–47,
  one 92.7): TNTD03020850 (perp, call'37), TNTD04509751 (perp), TNTG532803U (2049), TNTG532805U (2049,
  Variable), TNTG533596W (perp, call'15), TNTG701894W (2033, step/var). Half perpetual; reset date ≈ the
  call date where present. Share the FRN forward projection but need per-bond reset terms → decide next.

## Validated so far
- **Bootstrap ported** (`src/curves/bootstrap.py`, colleague's validated module): A/S exact,
  Q exact ≤30y, Monthly <0.1 pp (short-end fill); golden-master `tests/test_bootstrap.py` uses
  **segmented** thresholds — A/S strict <1e-9 red line; Quarterly terminal-extrapolation node
  (>30y) and Monthly-DF short-end residual carved out (see WORKLOG 2026-06-27). Rating notch-map
  `src/credit/ratings.py` (`tests/test_ratings.py`). Bloomberg cut.
- **Universe pipeline** (`src/dataio/loaders.py` + `universe.py`, run on 47): reproduces the
  documented funnel **exactly** (join 597/135/19, rating 712/4/16, Layer-A raw 54/73, MECE=732)
  → **canonical = 522 @ 2009-06-10** (incl. 46 make-whole-as-vanilla; callable=5); per-bond exclusion log; golden
  `tests/test_universe.py` (53 tests).
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
  unrunnable w/o Bloomberg). Invariant-validated (`test_lattice` 29 + `test_call_schedules` 4). Only **4 genuine
  fixed callables** (46 make-whole → vanilla); lattice moves ~1 (TNTD04441873 eff-dur 11.56→**10.54 @σ=0.15**);
  custodian AQ ≈ straight dur (misses the call). **Mario v1 (2026-07-03): σ=0.15** (was 0.18); **call schedule
  DATA-DRIVEN** — `data/call_schedules.csv` (`asset_id|call_date|call_price`, git-ignored) via
  `dataio.call_schedules`, seeded by `scripts/init_call_schedules.py`; the lattice reads a `[(time,price)]` step
  schedule (**no hard-coded par-call** — a real schedule = CSV-only change). v1 values = par-call@100, call_date ←
  AB; TNTD03203204 note "par-call conflicts w/ BT 108.69; awaiting actual schedule". **All 3 Mario Qs
  (schedule/vol/BT) RESOLVED — WORKLOG 2026-07-03.**

## Open questions
- **OAS redefined → calibration (2026-06-30; see WORKLOG).** Implied OAS per bond from `BT`, then risk metrics;
  index/sector/distressed OAS no longer external inputs (**WRDS distressed/sector OAS pulls cancelled**). New opens
  for Mario: (a) calibration date — **3-31 ARRIVED & ADOPTED (2026-07-02)**: Mario's USD 3-31 curve (native schema)
  swapped in, `VAL`=2009-03-31, near-maturity distortion cleared (the v1 3-31 *rating-OAS* refutation below does
  **NOT** apply to calibration); (b) **EUR/GBP own-ccy curves DONE** (15 EUR fixed, **2 GBP still curve-blocked** —
  non-arb 3y node, needs a GBP replacement curve or `bootstrap` variant-isolation, NOT a date issue); (c) **FX
  RESOLVED** — custodian base-USD columns (`BU`='Market value - base', `Z`='Book cost - base') read directly, no
  self-convert (`to_usd` removed; `currency` kept for routing); (d) **BT marking date/source — RESOLVED
  (2026-07-03, Mario):** by 3-31 the crisis was near its end & spreads had retreated from peak, so BT's tighter
  credit = the real recovering-market mark, NOT a date mismatch (implied@3-31 143–206bp *below* the 3-31 peak index
  IS that recovery). 3-31 baseline unchanged.
- ~~3-31 curve = the v1 IG lever~~ **REFUTED (tested 2026-06-27, for the v1 rating-OAS method; REOPENS for calibration — see above):** date-matching to 3-31 (3-31 DGS curve +
  3-31 OAS) makes IG **worse** (6.43%→11.14%, signed −0.41%→−6.70%) — the 3-31 crisis-peak OAS (BBB 7.31% vs
  6-10's 4.53%) overstates these high-grade holdings' spreads; **BT aligns with ~6-10 (tighter) spreads, the
  70-day gap is NOT a precision lever** (real lever = finer OAS, v2).
- ~~Confirm BT's marking date/source~~ **RESOLVED (2026-07-03, Mario):** by 2009-03-31 the crisis was near its end
  and spreads had already retreated from the peak ⇒ BT's tighter credit is the genuine recovering-market mark, not
  a date mismatch; the implied OAS sitting 143–206bp below the 3-31 crisis-peak index is that recovery, not an
  error. 3-31 stays the calibration baseline. See WORKLOG 2026-07-03.
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
  MECE funnel → **canonical 522 @ 2009-06-10** (46 make-whole→vanilla)) + ✅ `call_schedules.py` (call/put
  exercise table `data/call_schedules.csv` → per-asset `[(date,price)]`; the lattice's only call-terms source)
  + ✅ `coupon_types.py` (`Coupon_Formula2` → coupon-class + engine route, Mario 2026-07-08);
  FRED OAS loader next. (Named `dataio`, **not** `io`: `conftest` puts `src/` at `sys.path[0]`, so an `io` package
  would shadow stdlib `io`.)
- `src/pricing/` — ✅ `bond_price.py` (`BondPrice` port: ACT/364, 182-day schedule, accrued, clean/dirty;
  **default = corrected DF**, `vba_compat` reproduces the legacy `exp(-t·z_semi)` bug; `oas`/`freq` params) ·
  ✅ `calibrate.py` (`implied_oas`: solve OAS s.t. clean=`BT`) · ✅ `risk.py` (`risk_metrics`: effective
  duration / DV01 / convexity by ±1bp = parallel-shift bump) · ✅ `coupon_schedule.py` (**Step-3** coupon
  time-table for stepped/step-up/zero; threaded through `price_bond`/`implied_oas`/`risk_metrics`) ·
  ✅ `frn.py` (**Step-4** FRN: forward-projection off `ZeroCurve` + spread, single-curve discount, implied
  OAS; **curve-bump eff-dur ~ next reset**) ·
  ✅ `lattice.py` (**v2** callable/putable BDT
  short-rate tree: fwd-induction Arrow-Debreu calib to `ZeroCurve`, arb-free; implied OAS + eff-dur; NOT a
  `BondOAS` replica — invariant-validated; `call_array`/`put_array` read a `[(time,price)]` schedule from
  `dataio.call_schedules` — no hard-coded par-call; driver `scripts/callable_risk.py`, σ=0.15).
- `src/instruments/` (Bond model + cash flows) · `src/risk/` (CreditMetrics, later) · `src/config/`.
- `tests/` — golden-master (`test_bootstrap`, `test_ratings`, `test_universe`, `test_oas`) + `test_lattice`
  (v2 callable-lattice **invariants**: par-reprice/arb-free, callable≤straight≤putable, σ=0 degeneracy, multi-date
  schedule ordering) + `test_call_schedules` (loader: multi-row grouping, date→time clamp) + `test_universe`
  coupon-class locks (pivot reconciliation, canonical-all-F/vanilla, funnel-bucket split) + `test_coupon_schedule`
  (formula parser + schedule-aware pricing: past-step→flat, future-step, zero) + `test_frn` (FRN
  invariants: par-under-any-shift, OAS round-trip, near-par dur≈0, dur ≪ same-maturity fixed). **80 total.**
