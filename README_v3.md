# Fixed-Income Pricing — v3 code package

Code-only snapshot at commit `b7caa65`. A Python re-implementation of a legacy Excel/VBA
fixed-income pricing toolkit; **corporate bonds are the first reference implementation.**

**v3 = the v2 calibration/risk/lattice stack + full coupon-type coverage.** The module no longer
assumes every bond is a plain fixed ("F") bond: it reads the `Coupon_Formula2` column, classifies
each of the **676** corporate-bond rows, and routes every one to a pricing engine **or an explicit
flag — nothing is silently mispriced.** New in v3: a coupon-structure classifier/dispatcher, a
schedule-aware vanilla engine (stepped / step-up), a forward-projection **floating-rate (FRN)
engine**, coupon-continuation pricing for fixed-to-reset hybrids, and recovery marks for defaulted
names. `COVERAGE.md` (included in this package) is the class → engine → status map.

Result at the 2009-06-10 valuation: **558 bonds produce output — 545 priced end-to-end** (implied
OAS + effective duration / DV01 / convexity) **+ 13 carried at the custodian mark with an explicit
flag**; 21 are excluded per the client's instruction (pass-through / amortizing / N/A). This README
is written for code review — reading order, the design decisions behind anything non-obvious, and
the scope boundaries so intentional choices aren't mistaken for bugs.

> This is **code only**. The client portfolio and market-data workbooks are shipped separately;
> tests that need them **SKIP** cleanly when they're absent (they don't fail).

---

## 1. Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt        # numpy, pandas, scipy, openpyxl, pytest
python -m pytest -q                              # from the package root; conftest.py puts src/ on sys.path
```

- Any **Python 3.9+** with the requirements works. (Developed and run on a Linux server — nothing
  here depends on that.)
- **Run the main driver** (needs the URS workbook): `PYTHONPATH=src python3 scripts/calibrate_risk.py`.
  Point it at the data with `FIP_URS_WB=/path/to/URS…xlsx` (or drop the files under `data/`);
  `FIP_VAL_DATE` / `FIP_OUT` select the valuation date and output path.
- Workbook-dependent tests **auto-skip** if the data isn't found — `pytest` is green out of the box
  on just the code (the v3 FRN and coupon-schedule tests are pure-code and always run). Set
  `FIP_URS_XLSX` / `FIP_PRICING_XLSM` / `FIP_US_TXT` + `FIP_US_GOLDEN` to run everything against the
  real files.

---

## 2. Layout (dependency order = reading order; `[v3]` = new since v2)

```
src/
  curves/    bootstrap.py       par-yield curve -> zero (spot) curve.  The validated numerical core.
             zero_curve.py      ZeroCurve: zero_rate(t) + discount_factor(t, spread); per-ccy routing.
  credit/    ratings.py         S&P / Moody agency ratings -> 7 rating buckets (the notch map).
             oas.py             per-rating index OAS from the archived credit-curves sheet (v1 method).
  dataio/    loaders.py         Excel loaders: master "Fixed Income" sheet + "Corporate Bonds" tab.
             universe.py        the MECE funnel -> canonical universe + per-bond exclusion log.
             call_schedules.py  call/put exercise table (CSV) -> per-asset [(date, price)].
             coupon_types.py    [v3] Coupon_Formula2 -> ONE coupon class -> engine route (the dispatch).
  pricing/   bond_price.py      vanilla clean/dirty price; [v3] accepts an optional coupon schedule.
             calibrate.py       implied_oas: solve the OAS so model clean == custodian mark (BT).
             risk.py            effective duration / DV01 / convexity (parallel-shift bumps).
             coupon_schedule.py [v3] free-text stepped/step-up coupon tables -> [(date, rate)]; None, never a guess.
             frn.py             [v3] FRN engine: coupons = forwards off OUR curve; curve-bump duration.
             lattice.py         callable/putable Black-Derman-Toy short-rate tree (v2).
scripts/     calibrate_risk.py  [v3-expanded] THE routing driver: vanilla + Step-3 specials + FRNs
                                + reset hybrids -> one output table with per-route flags.
             callable_risk.py   callable-lattice implied OAS + effective duration (v2).
             init_call_schedules.py  seed the call-schedule CSV (v2).
tests/       golden-master + structural-invariant tests, 80 in total (see §5).
COVERAGE.md  [v3] class -> engine -> status over the 676-row pivot + the open data-gap list.
```

---

## 3. Suggested review path

1. **`dataio/coupon_types.py`** — the v3 entry point: `Coupon_Formula2` cell → exactly one coupon
   class → engine route. The class/count table in its docstring reconciles **exactly** to the
   client's 676-row pivot (locked in `tests/test_universe.py`).
2. **`COVERAGE.md`** — where every class lands (priced / flagged / excluded) and why.
3. **`pricing/frn.py`** — **read the module docstring first.** It carries the two most important
   "why"s in v3: effective duration must bump the **curve** (reprojecting the forwards), not the
   OAS; and the documented duration regimes — near-par ≈ time-to-next-reset, deep-discount slightly
   **negative** (a credit-spread-annuity effect), universally `≪` a same-maturity fixed bond.
4. **`pricing/coupon_schedule.py`** — the schedule parser. Note the contract: **returns `None`,
   never a guess**, when a cell carries no numeric coupons.
5. **`scripts/calibrate_risk.py`** — how it composes: four routing sections (vanilla universe →
   Step-3 specials → FRNs → reset hybrids) feed one table; only clean-spread routes enter the
   by-rating medians (`PRICED_ROUTES`).
6. **`tests/test_frn.py` + `tests/test_coupon_schedule.py`** — the invariants the new engines must
   satisfy; the fastest way to see what "correct" means here.

(The v2 core — `curves/bootstrap.py`, `pricing/bond_price.py`, `calibrate.py`/`risk.py`,
`lattice.py` — is unchanged in substance; see `README_v2.md` §3–4 if reviewing from scratch.)

---

## 4. Key design decisions (please read before flagging)

### 4.1 One dispatch, no silent defaults
Previously every bond was implicitly priced as plain-fixed. v3 classifies `Coupon_Formula2` into
exactly one class and routes it (`ROUTE` in `coupon_types.py`). Anything blank or unrecognised maps
to `unknown` → **excluded with a flag**, never silently priced as vanilla. (Convention trap,
documented in the module: the column is Excel **M** — the brief said "N", but N is empty and the
header confirms M.) Pass-through (16), amortizing (1) and N/A (4) are excluded **per the client's
explicit instruction** — they need prepayment/amortization models (a later phase), not this engine.

### 4.2 Parsers return `None`, never a guess
Both free-text parsers — the stepped/step-up schedule (`coupon_schedule.py`) and the FRN quoted
spread (`parse_frn_spread`) — return `None` when the cell has no usable number ("Step-up schedule",
"EURIBOR + Spread"). The driver then **flags the bond and carries it at the custodian mark** instead
of pricing on an invented term — the same pattern as the v2 call-schedule CSV: when the real terms
arrive, they drop in with **no code change**.

### 4.3 FRN: forwards off our own curve; duration bumps the curve, not the OAS
Each future coupon is projected as the **simple forward off our bootstrapped `ZeroCurve`**
(`F(t0,t1) = (DF(t0)/DF(t1) − 1)/(t1−t0)`) plus the quoted spread; every cash flow discounts on the
**same curve + a flat implied OAS** (single-curve — the 2009-era convention, matching the legacy
FRN branches; OIS/dual-curve discounting is a **documented future enhancement**, deliberately not
modelled). Quoted spreads are absent from this workbook, so priced FRNs use `spread = 0` and the
implied OAS **absorbs** the unknown spread (a discount-margin-type number); the calibrated price is
exact and the risk metrics are, to leading order, spread-independent — the spread can be separated
back out when the real figures arrive.

**Effective duration parallel-shifts the curve and reprojects the forwards.** Rising rates raise
the projected coupons and (largely) cancel the discounting, so an FRN's duration is ~ the time to
its next reset. Bumping only the discount rate (OAS-style) would wrongly make a floater look like a
fixed bond — this is the signature floating-rate check, locked in `test_frn.py`. A deep-discount
floater correctly shows a small **negative** duration (its below-par credit gap ≈ OAS × annuity PV
shrinks when rates rise) — documented in the `frn.py` docstring so it's never mistaken for a bug.

### 4.4 Reset hybrids: coupon-continuation is the metric; price-to-call is reference only
The fixed-to-reset perpetuals/hybrids with a known current coupon are priced as that coupon
**continued** (perpetuals truncated at 90y, where face PV ≈ 0 under crisis discounting — noted per
bond). **Price-to-call is emitted as a reference column only**: for a deep-discount name (BT ≈ 36)
the to-call solve implies an absurd spread because the market is pricing **extension**, not
redemption — so continuation is the reported number, by design.

### 4.5 The model alarms instead of emitting plausible-but-wrong numbers
Three live examples, all kept visible in the output: the "zero-coupon" bond prices to an OAS of
**−486 bp** → flagged `zero-structured` (BT is inconsistent with a pure discount bond; excluded from
medians); a callable's par-call assumption conflicts with BT 108.69 → flagged, real schedule
required; the reset to-call spread of 1,884 bp vs 627 bp continuation → to-call demoted to
reference. During development the FRN par invariant itself caught a stub-period forward mis-anchored
to the valuation date instead of the true last reset — fixed at the root, **no test threshold was
loosened**.

### 4.6 Median hygiene
Only routes whose implied OAS is a clean, model-repriced spread feed the by-rating review medians
(`PRICED_ROUTES = {vanilla, make-whole-as-vanilla, vanilla-schedule}`). Recovery marks,
BT-carried flags, near-maturity (<1y) names and the structured "zero" are reported but **kept out
of the medians** — an implied OAS that is a calibration plug must not contaminate the review table.

### 4.7 Unchanged v2 foundations (one paragraph)
Discounting is deliberately **corrected** vs the legacy VBA (which mixed a semiannual zero with
continuous discounting); `vba_compat=True` still reproduces the legacy output exactly for
reconciliation. The custodian marks (`BT`/`BU`/`DI`) stay under `gold_*` names — `BT` is used **only
as the calibration target**, never as a forward-pricing input. The universe remains a deterministic
MECE funnel with one primary exclusion reason per bond; v3 splits the old blanket
"structured/floating" bucket by actual coupon class. See `README_v2.md` §4 for the full rationale.

---

## 5. What's tested (80 tests)

| test | subject |
|---|---|
| `test_bootstrap.py` | par→zero bootstrap vs the legacy golden CSV (segmented thresholds) |
| `test_ratings.py` | the S&P/Moody notch map (IG/HY split; CC/C → CCC, only D/SD → default) |
| `test_oas.py` | the per-rating index-OAS loader (raises on a missing date) |
| `test_universe.py` | the MECE funnel counts **+ [v3] the coupon-class locks**: the 676-row `Coupon_Formula2` pivot reconciles exactly; canonical is 100% class-F/vanilla; the funnel-bucket split |
| `test_call_schedules.py` | the call-schedule CSV loader (multi-row grouping, date→time clamp) |
| `test_lattice.py` | callable-lattice invariants: arbitrage-free, `callable ≤ straight ≤ putable`, `σ=0` degeneracy |
| `test_coupon_schedule.py` | **[v3]** the schedule parser (numbers+dates → table; no numbers → `None`; mismatched counts → refuse) and schedule-aware pricing (past step ⇒ flat current coupon; future step; zero) — pure-code, never skipped |
| `test_frn.py` | **[v3]** FRN invariants: a pure floater **holds par under any parallel curve shift** (a mathematical identity, sampled −3%…+5%); implied-OAS round-trip; near-par duration ≈ time-to-next-reset; `|duration| ≪` a same-maturity fixed bond even at 78y — pure-code, never skipped |

Two kinds of test throughout, both worth trusting: **golden-master** (reproduce legacy numbers to
the digit where a legacy output exists) and **structural invariants** (properties that must hold
regardless of inputs — these catch classes of bugs a single golden number can't).

---

## 6. What's new in v3 (vs the v2 package)

| area | v3 addition |
|---|---|
| classification | `dataio/coupon_types.py` — `Coupon_Formula2` → one coupon class → engine route; reconciles exactly to the client's 676-row pivot; `unknown` never silently priced |
| stepped / step-up | `pricing/coupon_schedule.py` — free-text coupon table parser (`None`, never a guess) + schedule-aware cash flows threaded through `bond_price` / `calibrate` / `risk` |
| floating-rate | `pricing/frn.py` — forward-projection FRN engine off our `ZeroCurve`; implied OAS (Brent); **curve-bump** duration/DV01/convexity; `parse_frn_spread` |
| reset hybrids | coupon-continuation pricing (perp → 90y truncation) + price-to-call reference column, in the driver |
| defaulted / recovery | explicit recovery-mark route (BT carried, **no OAS** — solving a spread for a defaulted bond is meaningless) |
| driver | `scripts/calibrate_risk.py` — four routing sections → one output table; per-route flags; median hygiene (`PRICED_ROUTES`) |
| docs | `COVERAGE.md` — class → engine → status over all 676 rows + the open data-gap list |
| universe | funnel split by coupon class (was one blanket "structured/floating" bucket); 1 mislabelled amortizer out of canonical, 1 real fixed callable onto the lattice |

---

## 7. Scope, coverage & the open data gaps

**Covered end-to-end (545 priced):** vanilla fixed 475 + make-whole-as-vanilla 46 + floating 18 +
reset-continuation 4 + stepped 1 + the (flagged) structured zero. Genuine fixed callables (6) price
separately on the v2 BDT lattice. **13 carried at the custodian mark with explicit flags** — each
one is a *data* gap (switch dates, perpetual/reset terms, a step-up table, one blocked GBP curve),
listed bond-by-bond in `COVERAGE.md`; every engine is already routed, so each item resolves with a
data drop-in, **no code changes**.

**Not in this package:** pass-through / amortizing pricing (prepayment & amortization models — a
later MBS-phase, excluded per the client's instruction); OIS/dual-curve FRN discounting (documented
future enhancement); EIR / IFRS-9 amortised cost (a later requirement); portfolio-level risk
aggregation (natural next step).
