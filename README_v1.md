# Fixed-Income Pricing — v1 code package

Code-only snapshot at commit `dcf9be4`. The **first reference implementation** of a Python port of a
legacy Excel/VBA fixed-income pricing toolkit: **vanilla investment-grade corporate bond pricing.**

The pipeline is: **par-yield bootstrap → zero curve → discount each cash flow at `zero + rating OAS`**,
over a deterministically-built priceable universe. This package is the **library + tests** (no driver
scripts yet — those arrive in v2).

> **Code only.** The client portfolio and market-data workbooks are git-ignored and shipped
> separately; workbook-dependent tests **SKIP** cleanly when the data is absent.

---

## 1. Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # numpy, pandas, scipy, openpyxl, pytest
python -m pytest -q                              # from the repo root; conftest.py puts src/ on sys.path
```

Any **Python 3.9+** with the requirements works. Tests that need the URS workbook auto-skip if it
isn't found (set `FIP_URS_XLSX` to run them against the real file), so `pytest` is green out of the box
on just the code.

---

## 2. Layout (dependency order = reading order)

```
src/
  curves/    bootstrap.py    par-yield curve -> zero (spot) curve.  The validated numerical core.
             zero_curve.py   ZeroCurve: zero_rate(t) + discount_factor(t, spread); per-ccy routing.
  credit/    ratings.py      S&P / Moody agency ratings -> 7 rating buckets (the notch map).
             oas.py          per-rating index OAS from the archived credit-curves sheet.
  dataio/    loaders.py      Excel loaders: the master "Fixed Income" sheet + "Corporate Bonds" tab.
             universe.py     the MECE funnel -> canonical priceable universe + per-bond exclusion log.
  pricing/   bond_price.py   vanilla clean/dirty price (ACT/364, 182-day schedule, accrual).
tests/       test_bootstrap · test_ratings · test_oas · test_universe   (golden-master)
```

Everything discounts on the curve from `curves/`; `credit/` supplies the rating and its OAS;
`dataio/` selects which bonds get priced; `pricing/bond_price.py` values one bond.

---

## 3. Suggested review path

1. **`curves/bootstrap.py`** — the par→zero bootstrap (`DF_i = (100 − cpn·ΣDF_k)/(100 + cpn)`), locked
   to the legacy golden CSV by `test_bootstrap.py`.
2. **`curves/zero_curve.py`** — the `ZeroCurve` wrapper (`discount_factor(t, spread) = exp(-(z+spread)·t)`).
3. **`pricing/bond_price.py`** — **read the module docstring first** (the conventions + the discounting
   correction, see §4.1).
4. **`credit/ratings.py` + `credit/oas.py`** — the rating bucket and the per-rating index OAS that
   feeds the discount spread.
5. **`dataio/loaders.py` → `dataio/universe.py`** — how the priceable universe is assembled;
   `test_universe.py` locks every count.

---

## 4. Key design decisions (please read before flagging)

### 4.1 Discounting is deliberately *corrected*; `vba_compat` reproduces the legacy bug exactly
`bond_price.py` copies the VBA **cash-flow** conventions verbatim — **ACT/364** day count and a
**182-day** coupon schedule stepping back from maturity. These drift from the true calendar coupon
dates and are a **known, intentional** source of small gaps vs the custodian mark, not bugs. The
**discounting** is corrected on purpose: the legacy stores a *semiannual* zero but discounts it with
the *continuous* `exp(−t·z_semi)`, which under-prices (a bootstrapped curve then can't reprice its own
par bonds to 100). The default discounts consistently so **par → 100.000000**; **`vba_compat=True`**
reproduces the legacy output **exactly** for reconciliation.

### 4.2 Input / truth separation
The custodian's own marks — market price `BT`, market value `BU`, yield `DI` — are loaded under
`gold_*` names and kept **out of every pricing input**. They are an independent reconciliation
cross-check, never a model input.

### 4.3 OAS = one flat index spread per rating
v1 prices by discounting each cash flow at `zero(t) + OAS(rating)`, where `OAS(rating)` is a single
flat spread per rating bucket read from the archived credit-curves sheet (`credit/oas.py`). This is
the v1 method; **v2 later redefines OAS as a per-bond calibration factor** backed out of `BT`.

### 4.4 The universe is a deterministic MECE funnel
`universe.py` produces a canonical priceable set + a per-bond exclusion log; every dropped bond gets
**exactly one** primary reason by a locked priority, and the parts partition the universe exactly
(`test_universe.py`).

### 4.5 Testing = golden-master
Reproduce the legacy numbers to the digit: the bootstrap vs its golden CSV (segmented thresholds), the
notch map, the index-OAS loader, and the funnel counts.

---

## 5. Scope & the v1 verdict

**In scope:** investment-grade vanilla corporate bonds. The method is **validated and unbiased** vs
the custodian mark (signed median ≈ 0 across AAA–BBB — the curve + rating OAS is centred on `BT`).
Single-name precision is ~6% median |diff|, which is **dispersion around an index rating OAS**
(±300 bp name-level scatter is normal for 2009), a **design boundary of the flat-per-rating method —
not a bug**.

**Deferred to v2 / later:** high-yield & distressed single names, callable/putable bonds (an option
model), floating-rate and structured coupons, and risk metrics (duration / DV01 / convexity). v2 adds
the per-bond OAS calibration + risk layer and a callable/putable short-rate lattice.
