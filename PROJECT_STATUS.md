# Fixed-Income Pricing — Project Status

**Objective.** Re-implement a legacy Excel/VBA fixed-income pricing toolkit as a
structured, scalable **Python** module that can plug into a broader risk-management
process. **Corporate bonds are the first reference implementation**; the design must
generalise to MBS / CMBS / ABS / CMO / callables and to a credit-risk
(CreditMetrics) layer.

Repo: `github.com/charlieee0712/fixed_income_pricing`

> ⚠️ **Data handling.** Raw client portfolios and market-data workbooks
> (`*.xlsx / *.xlsm / *.zip / *.csv / *.txt`) are **git-ignored** and must never be
> committed — they contain a client's actual holdings and proprietary curves. This
> repo holds code and documentation only. Because the docs reference a client
> portfolio, **keep the GitHub repo private.**

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
   - **Open:** which valuation date is the deliverable target, and how to handle the
     2009 data gap (nearest available 2009-06-10? interpolate across the gap?).

2. **Corporate-bond universe — three reconciled counts; pick one canonical definition.**
   | Count | Definition |
   |---|---|
   | **811** | Master sheet `Asset sub category = "Corporate Bonds"` — broadest; **684 Corporate Bond + 125 MTN**, counted by holding rows. |
   | **676** | Cleaned `Corporate Bonds` tab (~668 unique bonds used in the maturity analysis). |
   | **641** | Priceable plain-vanilla subset — fixed-rate, semi-annual; **excludes** floating / fix-to-float / hybrid / structured / defaulted. |
   - **Open:** adopt one canonical universe + maintain an explicit **exclusion list**.

3. **EIR / amortised-cost method** is required (per CEO) but **not yet ported**.

4. **Structured-coupon tail.** Most corporates are vanilla fixed, but a tail
   (fix-to-reset, fix-to-float, perpetual hybrids) needs explicit handling — defer to v2.

---

## 4. Current progress

- ✅ **Structural analysis** of all four workbooks complete (sheets, columns,
  instrument fields, formula logic).
- ✅ **Bootstrap reproduced & validated in Python** vs the VBA/CSV output:
  Annual / Semiannual / Quarterly **exact (0 error)**; **Monthly within 0.08 bp**
  (difference traced to a short-end fill convention).
- ✅ **Bloomberg dependency removed** (txt par curves + FRED OAS).
- ✅ Repo + documentation established (this file, `WORKLOG.md`, `CLAUDE.md`).
- ⏭️ Next: corporate-bond pricing layer (port `BondPrice`), resolve valuation date &
  universe, then accrued/clean-dirty and an OAS/YTM solver.

---

## 5. Target architecture

Layered, config-driven, vectorised (numpy/pandas). Each instrument type is a plug-in
on a shared pricing core; corporate bonds are the first.

```
fixed_income_pricing/
├── io/            # loaders: par-curve txt/zip, FRED OAS, Excel positions/instruments
│                  #   (handles country-name ⇄ 2-letter-code aliasing)
├── instruments/   # Bond data model (coupon, freq, maturity, daycount, seniority,
│                  #   rating, face, …) + cash-flow schedule generation
├── pricing/       # curve bootstrap + ZeroCurve (interp/extrap); discounting;
│                  #   accrued interest; clean/dirty; YTM & OAS solvers  ← port BondPrice here
├── risk/          # CreditMetrics migration, transition matrix, Merton thresholds, VaR (later)
├── config/        # valuation date, universe definition, day-count conventions
└── tests/         # golden-master tests vs VBA / CSV outputs (bootstrap already a passing case)
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
