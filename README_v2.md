# Fixed-Income Pricing — v2 code package

Code-only snapshot at commit `24689a7`. A Python re-implementation of a legacy Excel/VBA
fixed-income pricing toolkit; **corporate bonds are the first reference implementation.**

**v2 = the v1 vanilla-pricing foundation + a per-bond OAS-calibration & risk layer + a
callable/putable short-rate lattice.** This README is written for code review — it gives a reading
order, the design decisions behind anything non-obvious, and the scope boundaries so intentional
choices aren't mistaken for bugs.

> This is **code only**. The client portfolio and market-data workbooks are git-ignored and shipped
> separately; tests that need them **SKIP** cleanly when they're absent (they don't fail).

---

## 1. Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # numpy, pandas, scipy, openpyxl, pytest
python -m pytest -q                              # from the repo root; conftest.py puts src/ on sys.path
```

- Any **Python 3.9+** with the requirements works. (The original Windows box had no usable local
  Python, so this was developed and run on a Linux server — nothing here depends on that.)
- **Run a driver** (needs the URS workbook): `PYTHONPATH=src python3 scripts/calibrate_risk.py`.
  Point it at the workbook with `FIP_URS_WB=/path/to/URS…xlsx` (or drop the file under `data/`).
- Workbook-dependent tests **auto-skip** if the data isn't found — so `pytest` is green out of the box
  on just the code. Set `FIP_URS_XLSX` to run them against the real workbook.

---

## 2. Layout (in dependency order — this is also the suggested reading order)

```
src/
  curves/    bootstrap.py      par-yield curve -> zero (spot) curve.  The validated numerical core.
             zero_curve.py     ZeroCurve: zero_rate(t) + discount_factor(t, spread); per-ccy routing.
  credit/    ratings.py        S&P / Moody agency ratings -> 7 rating buckets (the notch map).
             oas.py            per-rating index OAS from the archived credit-curves sheet (v1 method).
  dataio/    loaders.py        Excel loaders: the master "Fixed Income" sheet + "Corporate Bonds" tab.
             universe.py       the MECE funnel -> canonical priceable universe + per-bond exclusion log.
             call_schedules.py [v2] call/put exercise table (CSV) -> per-asset [(date, price)] schedule.
  pricing/   bond_price.py     vanilla clean/dirty price (ACT/364, 182-day schedule, accrual).
             calibrate.py      [v2] implied_oas: solve the OAS so model clean == custodian mark (BT).
             risk.py           [v2] effective duration / DV01 / convexity (parallel-shift bumps).
             lattice.py        [v2] callable/putable Black-Derman-Toy short-rate tree.
scripts/     calibrate_risk.py    [v2] driver: per-bond implied OAS + risk metrics + by-rating table.
             callable_risk.py     [v2] driver: callable-lattice implied OAS + effective duration.
             init_call_schedules.py [v2] seed the call-schedule CSV.
tests/       golden-master + structural-invariant tests (see §5).
```

Everything discounts on the curve produced by `curves/`, so read that first; `pricing/` sits on top of
it; `dataio/` selects *which* bonds get priced. `[v2]` marks the modules new since v1.

---

## 3. Suggested review path

1. **`curves/bootstrap.py`** — the par→zero bootstrap (the shared recursion `DF_i = (100 − cpn·ΣDF_k)
   / (100 + cpn)`). This is a validated port; `tests/test_bootstrap.py` locks it to the legacy output.
2. **`curves/zero_curve.py`** — the thin `ZeroCurve` wrapper everything discounts through. Note
   `discount_factor(t, spread) = exp(-(z(t)+spread)·t)` and `from_currency(...)` (own-ccy routing).
3. **`pricing/bond_price.py`** — **read the module docstring first.** It documents (a) the VBA
   cash-flow conventions copied verbatim and (b) the one deliberate *correction* to the discounting.
   This is the most important "why" in the package (see §4.1).
4. **`pricing/calibrate.py` + `pricing/risk.py`** — the v2 direction: back out a per-bond implied OAS
   from the custodian mark, then take risk metrics off the calibrated model.
5. **`dataio/loaders.py` → `dataio/universe.py`** — how the priceable universe is built. `universe.py`
   is a deterministic MECE funnel; `tests/test_universe.py` locks every count.
6. **`pricing/lattice.py` + `tests/test_lattice.py`** — the v2 callable/putable lattice. It's the most
   involved module; the test file is the fastest way to see the invariants it must satisfy.
7. **`scripts/calibrate_risk.py`** — how it all composes into the deliverable (implied OAS + risk +
   by-rating review table).

---

## 4. Key design decisions (please read before flagging)

### 4.1 Discounting is deliberately *corrected*; `vba_compat` reproduces the legacy bug exactly
`bond_price.py` copies the VBA **cash-flow** conventions verbatim — **ACT/364** day count and a
**182-day** coupon schedule stepping back from maturity. These drift from the custodian's true
calendar dates and are a **known, intentional** source of small price gaps vs the custodian mark —
not bugs (a port must match the legacy where it matters).

The **discounting**, however, is corrected on purpose. The legacy `BondPrice` stores a *semiannual*
zero but discounts it with the *continuous* formula `exp(−t·z_semi)` — a convention mismatch that
systematically under-prices (a bootstrapped curve then fails to reprice its own par bonds to 100:
10y → 99.67). The default here discounts consistently (`exp(−t·z_cont) = DF`), so **par reprices to
100.000000**. Pass **`vba_compat=True`** to reproduce the legacy `exp(−t·z_semi)` output **exactly**
(verified 0.0000% on the sample bond) for reconciliation. Effect of the fix ≈ 0.2% @ 8y — below the
noise of the v1 method, so it does not change any verdict; it's there so the module is *correct* and
extensible, with a switch to tie out against the legacy sheet.

### 4.2 Input / truth separation
The custodian's own marks — market **price** (`BT`), market **value** (`BU`), **yield** (`DI`) — are
loaded under `gold_*` names and kept **out of every pricing input**. They are an independent
reconciliation cross-check, never fed into the model. (In v2 `BT` *is* used — but as a **calibration
target**, see 4.3 — never as a pricing input to a forward valuation.)

### 4.3 OAS is a per-bond calibration factor (the v2 redefinition)
v1 looked up an **index rating OAS** (one flat spread per rating, `credit/oas.py`) and computed a
price. **v2 inverts this**: it takes the custodian price `BT` as given and solves for the single flat
OAS that makes the model reprice to it (`calibrate.py`, Brent on a monotone objective). The calibrated
model — which reproduces the mark by construction — is then the basis for the risk metrics
(`risk.py`). The implied OAS therefore **absorbs everything** between model and mark (genuine credit
spread + the ACT/364 & 182-day conventions + any holdings/curve date gap): it's a model-calibration
spread, not a clean market OAS, but it's exactly what makes the sensitivities self-consistent with the
custodian valuation.

### 4.4 The universe is a deterministic MECE funnel
`universe.py` turns the master holdings + the terms tab into a canonical priceable set plus a per-bond
exclusion log. Every dropped bond gets **exactly one** primary reason, assigned by a **locked
priority**; the parts **partition** the universe exactly (checked in `test_universe.py`). Make-whole
callables (call date ≈ maturity ⇒ ~zero option value) route to **vanilla**; genuine callables are
excluded from vanilla and priced on the lattice.

### 4.5 Own-currency curve routing
A non-USD bond discounts on **its own-currency** curve (`ZeroCurve.from_currency`), not the USD curve
— pricing a EUR bond on the USD curve is simply wrong, and the pipeline routes each bond to the right
curve (with a documented fallback when a curve variant fails to bootstrap arbitrage-free).

### 4.6 Testing = golden-master **+** structural invariants
Two kinds of test, both worth trusting:
- **Golden-master** — reproduce the legacy numbers to the digit wherever a legacy output exists
  (bootstrap, and `vba_compat` pricing).
- **Structural invariants** — properties that must hold regardless of inputs: a curve reprices its own
  par bonds to 100; the callable lattice is arbitrage-free and satisfies `callable ≤ straight ≤
  putable`; at `σ = 0` the option value degenerates to zero. Invariants catch classes of bugs that a
  single golden number can't.

---

## 5. What's tested

| test | subject |
|---|---|
| `test_bootstrap.py` | par→zero bootstrap vs the legacy golden CSV (segmented thresholds: Annual/Semiannual strict `<1e-9`; the >30y Quarterly extrapolation node and the Monthly short-end residual are carved out and documented) |
| `test_ratings.py` | the S&P/Moody notch map (IG/HY split; CC/C → CCC, only D/SD → default) |
| `test_oas.py` | the per-rating index-OAS loader (raises on a missing date — no silent nearest-date) |
| `test_universe.py` | the MECE funnel — join / rating / security-type counts and the canonical count, all locked |
| `test_call_schedules.py` | **[v2]** the call-schedule CSV loader (multi-row grouping, date→time clamp) |
| `test_lattice.py` | **[v2]** callable-lattice invariants: par-reprice / arbitrage-free, `callable ≤ straight ≤ putable`, `σ=0` degeneracy, multi-date schedule ordering |

---

## 6. What's new in v2 (vs the v1 package)

| area | v2 addition |
|---|---|
| calibration | `pricing/calibrate.py` — `implied_oas`: solve the flat OAS so model clean == `BT` |
| risk | `pricing/risk.py` — effective duration / DV01 / convexity by ±1bp parallel-shift bumps (equals continuous Macaulay to ~1e-7 for an option-free bond) |
| embedded options | `pricing/lattice.py` — a from-principles Black-Derman-Toy short-rate tree (forward-induction Arrow-Debreu calibration to the `ZeroCurve`, so it's arbitrage-free). It is **not** a bit-for-bit replica of the legacy `BondOAS` (unrunnable without Bloomberg) — it's validated by invariants. Vol `σ = 0.15`; the call/put schedule is data-driven (`call_schedules.py`), no hard-coded par-call |
| call terms | `dataio/call_schedules.py` — reads the call/put exercise table (CSV) into per-asset `[(date, price)]` |
| drivers | `scripts/` — `calibrate_risk.py` (the main deliverable), `callable_risk.py`, `init_call_schedules.py` |

---

## 7. Scope & boundaries

**In scope (validated):** investment-grade vanilla corporate bonds (bootstrap → discount, unbiased vs
`BT` — signed median ≈ 0), the calibration+risk direction, and a handful of genuine fixed callables on
the lattice. Single-name pricing precision (~6% median |diff|) is **dispersion around an index rating
OAS**, a design boundary of the v1 method — not a bug (v2's per-bond calibration side-steps it for the
risk deliverable).

**Not in this package:** MBS / CMBS / ABS / CMO (out of scope for the corporate reference); floating-
rate notes, reset hybrids, stepped and zero-coupon structures (future scope);
EIR / IFRS-9 amortised cost (a later requirement).
