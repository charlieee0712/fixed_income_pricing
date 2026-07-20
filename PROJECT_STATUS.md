# Fixed-Income Pricing — Project Status

**Objective.** Re-implement a legacy Excel/VBA fixed-income pricing toolkit as a
structured, scalable **Python** module that can plug into a broader risk-management
process. **Corporate bonds are the first reference implementation**; the design must
generalise to MBS / CMBS / ABS / CMO / callables and to a credit-risk
(CreditMetrics) layer.

Repo: `github.com/charlieee0712/fixed_income_pricing`

> ⚠️ **Data handling — CHANGED 2026-07-08 (boss-approved).** Client portfolios and
> market-data workbooks (`*.xlsx / *.xlsm / *.zip / *.csv / *.txt`) are now **committed
> in-repo** — they contain a client's actual holdings and proprietary curves. Because the
> repo now holds real client data (not just code/docs), **keeping the GitHub repo PRIVATE
> is mandatory, not optional.** `.gitignore` now excludes only build/cache/editor artifacts.
> *(Prior policy: data git-ignored, "must never be committed" — superseded.)*

---

> ## ⚠️ Read this first — state as of 2026-07-20
>
> Sections 2–4 and 7 below describe the project as of the **v1 era** and are kept for the record;
> the method has since evolved materially. The current picture:
>
> - **Methodology (redefined 2026-06-30, Mario):** OAS is a per-bond **calibration output**, not a
>   pricing input — each bond's implied OAS is solved so the model clean price equals the custodian
>   mark (`BT`), and **risk metrics** (effective duration / DV01 / convexity, ±1bp parallel curve
>   bump) are computed on the calibrated model. The v1 index-rating-OAS flow in §2 is historical.
> - **Valuation baseline = 2009-03-31** (Mario's USD curve, adopted 2026-07-02; matches the
>   holdings date); 2009-06-10 kept as control. EUR/GBP bonds route to own-currency curves.
> - **Engines by coupon structure** (`Coupon_Formula2` routing, 2026-07-08): vanilla fixed ·
>   coupon-schedule (stepped / rating-step / documented paths) · FRN forward-projection ·
>   **fixed-then-float hybrid** (2026-07-20) · BDT callable lattice (v2) · recovery marks.
> - **Term-override data layer (2026-07-20):** flagged bonds resolved from public primary sources
>   by ISIN/CUSIP (22 of 35 fully, sources cited per bond in `docs/isin_lookup_2026-07-20.md`);
>   fills live in `data/coupon_schedules.csv`, `data/frn_spreads.csv`,
>   `data/make_whole_overrides.csv`, `data/hybrid_switch_terms.csv`.
> - **Universe:** canonical **523** @2009-06-10 / **528** @2009-03-31 (documented make-whole
>   override incl.), callable bucket 5, make-whole-as-vanilla 47. §3's canonical-476 figures are
>   the pre-reclassification history.
> - **Coverage:** output **564 bonds = 553 priced end-to-end + 11 flagged** @2009-03-31
>   (559 = 548 + 11 @6-10); **103 tests green**. Live map: `COVERAGE.md`; reports:
>   `v3_report_coverage` + `v3_report_addendum` (2026-07-20).
> - **Outstanding:** an 11-security Bloomberg margin list, the pass-through data (Mario sourcing),
>   a usable GBP par curve. Amortizing + N/A excluded permanently (Mario 2026-07-20).

---

## 1. Source material (file map)

| File | Role | Notes |
|---|---|---|
| `All_Yield_Curve.zip` | **Raw input** — par-yield curve history per country/currency | 27 `*_Yield_Curve.txt`. Columns: `Date(Excel serial), 0.25, 0.5, 1, 2, 3, 5, 10, 20, 30` (tenors in years, values = par yields as decimals). Country-name and currency-code files are aliases (e.g. `JAPAN` ≡ `JPY`). Also bundles `Zero_Yield_Curve_VBA_Code.txt` — the **auditable bootstrap VBA** (clean rewrite that replaces the old fast routine `Veloz`). |
| `Bootstrapped-*.zip` | **Stage-1 output (demo)** | 25 `XX_yield_curves.csv` (2-letter codes). Columns: `Maturity, Monthly_Rate, Monthly_DF, Quarterly_*, Semiannual_*, Annual_*`. ⚠️ These correspond to valuation date **2024-01-16**, not the URS holdings date — see §4. |
| `Pricing File.xlsm` | **Pricing template + reference VBA** | VBA modules: `Bootstrapping.bas` (1706 lines — `BondPrice`, `ZeroCalc`, `Parcurve`), `Matrix.bas`, `Copulas.bas`. Built around a **separate** Uganda govt-bond (UGANGB, UGX) demo + a CreditMetrics migration model. |
| `Project Pricing Fixed Income Instruments.xlsm` | **Legacy risk-system sample** | 26 sheets + an ~11k-line `Module1` VBA project. This is the broad "risk management process" target; **do not port `Module1` directly** — use the cleaner routines in `Pricing File.xlsm`. |
| `URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx` | **Client portfolio (the pricing target)** | A **US engineering-company pension** portfolio (custody managers: Western Asset / BlackRock / JPM / Capital Guardian), **all USD ISINs**. Positions split by asset type: `Corporate Bonds`, `CMBS`, `ABS`, `CMO`, `Callable Bonds`, `Pass-through`, `Govt MTGE`, … The `Corporate Bonds` tab is the current focus. |

> **Two distinct clients — do not merge.** `URS` (US pension, USD) is the portfolio we
> are pricing. *Uganda* (UGANGB govt bonds) is a separate example that lives only in
> `Pricing File.xlsm → Investments`.

---

## 2. Pipeline & methodology

```
[ raw par curves ]                         [ credit spread ]
 All_Yield_Curve.zip                        FRED ICE BofA US Corp OAS
   │  (per country/ccy)                       │  (one spread per rating, flat)
   ▼                                          │
① BOOTSTRAP risk-free zero curve             │
   par yield → zero rate → discount factor   │
   ▼                                          │
② RATING-ADJUSTED DISCOUNT CURVE  ───────────┘
   r(t) = z(t) + OAS(rating)
   ▼
③ BOND PRICING  (linear interpolation of the curve at each cash-flow date)
   Price = Σ couponCF · DF(tᵢ) + face · DF(T)
   ▼
④ RISK OVERLAY  (CreditMetrics — later)
   revalue 1-yr forward under each rating migration → value distribution → credit VaR
```

### ① Bootstrap (validated — see §4)
Per compounding frequency `f` (Annual=1, Semiannual=2, Quarterly=4, Monthly=12):

```
cpn_i = 100 · par_i / f
DF_i  = (100 − cpn_i · Σ_{k<i} DF_k) / (100 + cpn_i)      # standard par→zero bootstrap
z_i   = − ln(DF_i) / t_i                                  # continuous compounding
```

- Standard **41-tenor grid** 0.08y … 30y; missing tenors filled by **linear
  interpolation**, ends by **linear extrapolation**.
- Output: a **monthly grid out to 374 months (~31.2y)** × {Annual, Semiannual,
  Quarterly, Monthly}, each carrying a zero rate and a discount factor.

### ② OAS (credit spread)
- Source: **FRED — ICE BofA US Corporate Index Option-Adjusted Spread**, per rating
  bucket `AAA, AA, A, BBB, BB, B, CCC` (decimal; e.g. AAA ≈ 0.0026, CCC ≈ 0.073).
- The index OAS is a **single flat spread per rating** (not a term structure). It is
  added to the bootstrapped zero rate to obtain the rating-specific discount curve.

### ③ Pricing (fixed-rate bond)
```
cash-flow times τⱼ : next coupon … maturity T, step 1/f
DF(τ)              : linear interpolation on the monthly zero/DF grid
dirty price        = Σⱼ (c/f)·F·DF(τⱼ) + F·DF(T)
clean price        = dirty − accrued interest
```
Reference implementation to port: **`BondPrice` in `Pricing File.xlsm → Bootstrapping.bas`**.

### ④ Risk overlay (CreditMetrics) — later
One-year-forward zero curves by rating + a **rating transition matrix** + a Merton
**asset-value model** (the `NORMSDIST`/`NORMSINV` thresholds in `Pricing File.xlsm`)
→ forward value distribution → credit VaR. Lives in `Matrix.bas` / `Copulas.bas`.

> **Second valuation regime (not yet located/ported): Effective Interest Rate (EIR)**
> — amortised-cost accounting (IFRS 9). The CEO named *both* "bootstrapping and the
> Effective Interest Rate methods". EIR carries the bond at its purchase effective
> yield (constant-yield amortisation), independent of the market curve. Still to be
> found in the VBA.

> **No Bloomberg.** The original VBA pulled par yields via `GetBloomberg(...)`. That
> dependency is **cut**: inputs are now the exported `*_Yield_Curve.txt` files + FRED OAS.

---

## 3. Key findings & open questions

1. **Valuation-date mismatch (must resolve before pricing the real book).**
   - Holdings "Date of last pricing" ≈ **2009-03-31** (master sheet serial 39903).
   - The bundled `*_yield_curves.csv` exactly match curve date **2024-01-16**
     (brute-force over every date in the curve files, RMSE = 0.0000).
   - **2009-03-31 does not exist** in the curve files (data jumps 2008-11-10 → 2009-06-10).
   - Impact: at **2024-01-16**, of ~668 corporate bonds **545 have already matured**
     (no cash flows, unpriceable) → only **123 alive**; at **2009-03-31**, **667 alive**.
   - **Conclusion:** to price the 2009 holdings we must **bootstrap a ~2009 curve**;
     the 2024 CSVs are a **demo**, not the pricing basis.
   - **Decision:** curve files jump **2008-11-10 → 2009-06-10** (winter/spring absent).
     Candidates: 2008-11-10 (crisis trough, extreme curve) vs **2009-06-10 (CHOSEN** — nearest
     available, market calmer). `bootstrap.load_par_curve` **raises** on a missing date, so it's explicit.
   - **⚠️ Reconciliation caveat:** holdings are as-of **3-31**, nearest curve is **6-10** — a
     **70-day mismatch**; rates/spreads moved over Q2-2009, so our 6-10 prices will **not** tie
     to the custodian's 3-31 `BT/BU/DI`. Note the port's golden master is the **VBA tool's output**,
     not the custodian mark (see §3.2). **Ask the colleague which curve date/source the original
     tool used for the 3-31 book** (likely a 3-31 Bloomberg curve absent from our txt history) —
     this matters more than the date pick itself.

2. **Corporate-bond universe — RESOLVED as a deterministic pipeline (not a fixed number).** *(§3.2)*
   Start set = master `Asset sub category ∈ {Corporate, MTN}`, **deduped by Asset ID →
   732 unique instruments** (from 811 holding rows). Every drop is logged with **one
   primary reason + Asset ID/ISIN**, split into two layers so changing the valuation date
   only re-runs Layer B. Detail in **§3.2** below.

3. **EIR / amortised-cost method** is required (per CEO) but **not yet ported**.

4. **Structured-coupon tail.** Most corporates are vanilla fixed, but a tail
   (fix-to-reset, fix-to-float, perpetual hybrids) needs explicit handling — defer to v2.

### 3.2 Corporate-bond universe & data sourcing (detail)

**Join key = `Asset ID` (`S`, 100% filled) ↔ tab `Asset Code`; ISIN secondary.** Terms
and risk/holdings data live in different sheets and must be joined:

| Source | Fields taken |
|---|---|
| `Corporate Bonds` tab | coupon **rate**, **type / formula** (Layer-A classifier), payment freq, maturity |
| master `Fixed Income` | rating (`CM` S&P / `CL` Moody), **par held** (`CV` Shares/Par value), book cost (`Z`, for EIR), **validation** (`BT` price / `BU` MV / `DI` YTM) |

> Master coupon **rate/type are empty** (`DO`/`DP`) → terms MUST come from the tab.
> `BT`/`BU`/`DI` are the **custodian's own 3-31 marks** — keep them in a **separate
> reconciliation table**, never in the pricing inputs (input/truth separation). They are an
> *independent* cross-check, **not** the port's exact target: the port reproduces the **VBA
> tool's** output (a model), and a date mismatch (§3 ①) + model-vs-mark differences mean `BT`
> will not tie to the digit. The to-the-digit golden master for pricing = the VBA tool's output.

**Join result** (732 master uniques vs 616 tab uniques): **597 matched** ·
**135 master-only** → `terms-unavailable` (Medium-Term Notes etc.: *held*, but coupon terms
are in **neither** sheet — a **data-availability gap, not a security-type issue**; most MTNs
are plain fixed and can be added back if a terms source appears) ·
**19 tab-only** → `unmatched(not-held)`.

**Rating** — S&P `CM` primary → Moody `CL` fallback, **default precedence** (S&P D/SD wins
over any Moody grade). Of 732: **712 covered** · **4 defaulted** (→ Layer A) · **16 no-rating**
(`rating-exclusion`; do **not** force a bucket). Granular grades collapse to the **7 FRED
parent buckets** — implemented in `src/credit/ratings.py`:

| FRED bucket | S&P | Moody's |
|---|---|---|
| AAA | AAA | Aaa |
| AA | AA+, AA, AA− | Aa1, Aa2, Aa3 |
| A | A+, A, A− | A1, A2, A3 |
| BBB | BBB+, BBB, **BBB−** | Baa1, Baa2, **Baa3** |
| BB | **BB+**, BB, BB− | **Ba1**, Ba2, Ba3 |
| B | B+, B, B− | B1, B2, B3 |
| CCC *(lowest, catch-all)* | CCC+, CCC, CCC−, **CC, C** | Caa1, Caa2, Caa3, **Ca, C** |
| → defaulted (exclude) | D, SD | *(no D; via C / external flag)* |
| → no-rating (exclude) | NR | NR, WR |

> **Two red lines** (most spread-sensitive — must be exact): **(1)** S&P `CC/C` and Moody
> `Ca/C` → **CCC**, *not* defaulted (only `D/SD` are defaulted). **(2)** IG/HY boundary:
> `BBB−`/`Baa3` → **BBB** and `BB+`/`Ba1` → **BB** land in *different* buckets — never collapse.

**Layer A — security type (date-independent), within the 597 matched:**
- non-vanilla `Type ≠ FIXED` = **54** (floating 20 / hybrid 9 / structured 6 / pass-through 6
  / variable 2 / zero / step / preferred / fund) → reason `structured/floating`.
- **callable** (master `Call date` present) = **73** → reason `requires option model
  (deferred to v2)`; **keep `Call date` / call-price fields** for v2 (option-adjusted pricing,
  cf. `Module1.CBondPrice`). Some callables are also hybrid/perpetual — assign **one** primary
  reason (see priority below), do not double-count.

**Layer B — date-dependent:** matured at the chosen valuation date (`Maturity < val date`).

**Single primary reason per bond — LOCKED priority** (makes the funnel MECE):
`terms-unavailable / unmatched` → `defaulted` → `no-rating` → `structured/floating` → `callable` → `matured`.
Canonical = plain-fixed, rated, non-callable, held, not matured.

**IMPLEMENTED** in `src/dataio/universe.py` (`build_universe`); golden `tests/test_universe.py`.
All date-independent counts above reproduce **exactly**. Result **@ 2009-06-10** (post-priority MECE,
sums to 732): **canonical 476** / terms-unavailable 135 / structured-floating 51 / callable 51 /
no-rating 9 / matured 6 / defaulted 4 — well under the earlier loose **< 641** estimate. Layer-A
(date-independent) reasons dominate; only `matured` (=6) depends on the valuation date, so the
**final valuation date is still pending the colleague's confirmation** of the 3-31 curve source
(see §3 ①). The post-priority `no-rating`/`structured`/`callable` counts are below their raw
classifications (16/54/73) because higher-priority reasons absorb the overlaps.

---

## 4. Current progress

- ✅ **Structural analysis** of all four workbooks complete (sheets, columns,
  instrument fields, formula logic).
- ✅ **Bootstrap ported & reconciled** — `src/curves/bootstrap.py` (the colleague's
  validated module) reproduces the golden `XX_yield_curves.csv`: Annual / Semiannual /
  Quarterly **exact (0 error)**; **Monthly < 0.1 pp** (short-end fill). Golden-master test:
  `tests/test_bootstrap.py`.
- ✅ **Bloomberg dependency removed** (txt par curves + FRED OAS).
- ✅ **Master-sheet profiling + universe funnel** (corporate bonds): rating columns
  located (S&P/Moody ~98%; Fitch empty), Asset-ID join (597 matched / 135 master-only /
  19 tab-only), coupon-type & callable classified, golden-master columns identified. See §3.2.
- ✅ **Universe pipeline IMPLEMENTED** (`src/dataio/loaders.py` + `universe.py`, on server 47):
  openpyxl loaders + `build_universe` reproduce the funnel **exactly** → **canonical 476 @
  2009-06-10** + per-bond exclusion log; golden `tests/test_universe.py`. **22 tests green.**
  (Package is `dataio`, not `io`, to avoid shadowing the stdlib `io` that pandas/openpyxl import.)
- ✅ Repo + documentation established (this file, `WORKLOG.md`, `CLAUDE.md`).
- ⏭️ Next: wrap bootstrap output in a `ZeroCurve`; bootstrap the **2009-06-10** USD curve (sanity-
  check the post-crisis low-rate shape); port `BondPrice`; price the canonical 476; reconcile vs
  `BT`/`BU`/`DI`. (Universe pipeline ✅ done.)

---

## 5. Target architecture

Layered, config-driven, vectorised (numpy/pandas). `src/<layer>/` packages; the root
`conftest.py` puts `src/` on `sys.path`. ✅ = exists, others planned.

```
fixed_income_pricing/
├── src/
│   ├── curves/        # ✅ bootstrap.py (par→zero, reproduces golden CSV); ZeroCurve next
│   ├── credit/        # ✅ ratings.py (S&P/Moody → 7 OAS buckets); OAS-curve loader next
│   ├── dataio/        # ✅ loaders.py (master + Corporate Bonds tab) + universe.py (MECE funnel → canonical 476); FRED OAS next  [named dataio, not io — stdlib clash]
│   ├── instruments/   # Bond model (coupon, freq, maturity, daycount, rating, face) + cash flows
│   ├── pricing/       # discounting, accrued, clean/dirty, YTM/OAS solvers  ← port BondPrice
│   ├── risk/          # CreditMetrics migration, transition matrix, Merton thresholds (later)
│   └── config/        # valuation date, universe definition, day-count conventions
├── tests/             # golden-master: test_bootstrap, test_ratings, test_universe
├── conftest.py        # puts src/ on sys.path
└── requirements.txt
```

**Design principles**
- Conventions (day-count, accrual, cash-flow dates, calendars) are the real risk —
  the VBA (`BondPrice`) is the source of truth; pin them with golden-master tests.
- Curve, OAS, and instrument data are inputs; valuation date and universe are config,
  not hard-coded.

---

## 6. Environment & dependencies

- **Execution:** preferred target **server 47**; or a local Python install. The local
  Windows machine has **only a Microsoft Store Python stub (non-functional)** — no
  usable interpreter yet.
- **Suggested stack:** Python 3.11+, `numpy`, `pandas`, `scipy` (solvers),
  `openpyxl` (Excel I/O), `oletools` (decompile remaining VBA), `pytest`.
- **No Bloomberg** runtime dependency.

---

## 7. Next steps (proposed)

1. Decide canonical **valuation date** + **universe**; build the curve for that date
   (bootstrap ~2009 for the real book).
2. Implement `io` loaders + `instruments.Bond` from the `Corporate Bonds` tab; map
   each bond's **rating** (from the master sheet) and **holdings** → pricing inputs.
3. Port **`BondPrice`** → `pricing`: cash-flow generation, discounting with
   `z(t)+OAS(rating)`, accrued, clean/dirty. Golden-master vs VBA.
4. Add OAS/YTM solvers; reconcile a sample of bonds end-to-end.
5. Locate & port **EIR** (amortised cost); then begin the **CreditMetrics** risk layer.
