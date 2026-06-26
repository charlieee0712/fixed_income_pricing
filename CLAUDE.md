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
  port the ~11k-line `Module1` in the other workbook. Contains a *separate* Uganda demo.
- `Project Pricing Fixed Income Instruments.xlsm` — legacy risk-system sample (huge `Module1`).
- `URS …xlsx` — **the portfolio to price**: a US engineering-company pension, USD ISINs,
  positions split by asset type; `Corporate Bonds` tab is current focus.

## Two clients — do NOT merge
- **URS** = US pension (USD) → the pricing target.
- **Uganda** (UGANGB govt bonds, UGX) = a separate example, only in `Pricing File.xlsm`.

## Conventions (validated)
- Bootstrap per frequency `f`: `cpn=100·par/f`; `DF_i=(100−cpn·Σ_{k<i}DF_k)/(100+cpn)`;
  `z_i=−ln(DF_i)/t_i` (**continuous compounding**).
- 41-tenor grid 0.08y…30y; linear interpolation (interior) / linear extrapolation (ends);
  output monthly to ~374 months × {Annual, Semiannual, Quarterly, Monthly}.
- Pricing: discount each cash flow at `z(t)+OAS(rating)`, **linear interpolation** of the
  monthly grid; dirty = Σ coupons·DF + face·DF(T); clean = dirty − accrued.
- **OAS** = FRED **ICE BofA US Corporate** Index OAS, **one flat spread per rating** (AAA…CCC).

## Critical corrections (don't re-derive — already validated)
- **Valuation date**: holdings = **2009-03-31**; bundled curves = **2024-01-16** (RMSE 0).
  2009-03-31 is **absent** from curve files (gap 2008-11-10 → 2009-06-10). At 2024-01-16
  only **123/668** corporate bonds are still alive (545 matured); at 2009-03-31, **667**.
  → To price the real 2009 book, **bootstrap a ~2009 curve**; the 2024 CSVs are a demo.
- **Universe (3 lenses)**: **811** = master `sub-category=Corporate Bonds` (684 Corp + 125 MTN,
  by holding rows); **676** = cleaned `Corporate Bonds` tab; **641** = priceable vanilla
  fixed/semiannual subset (excl. floating/hybrid/structured/defaulted). Pick one + keep an
  exclusion list.

## Validated so far
- Bootstrap reproduced in Python: A/S/Q exact, Monthly 0.08 bp. Bloomberg cut.

## Open questions
- Canonical valuation date + how to bridge the 2009 curve gap.
- Canonical universe definition + exclusion list.
- **EIR (effective-interest / amortised-cost)** method — required by CEO, not yet located/ported.
- Where per-bond **rating** and **holdings/face** are sourced for the URS corporates (master sheet, by ISIN).

## Target architecture
`io/` (loaders) · `instruments/` (Bond model + cash flows) · `pricing/` (bootstrap,
ZeroCurve, discounting, accrued, YTM/OAS solvers — port `BondPrice` here) · `risk/`
(CreditMetrics, later) · `config/` (val date, universe, conventions) · `tests/`
(golden-master vs VBA/CSV).
