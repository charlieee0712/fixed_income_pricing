# Curves and market data

Where discount curves come from, how they are built, and the two traps in this area.

---

## 1. The chain

```text
*_Yield_Curve.txt          raw PAR-yield history per currency, one row per date,
   (data/)                 columns Date (Excel serial) + tenors 0.25 .. 30
        |
   bootstrap()             the validated par -> zero bootstrap
        |
   monthly grid            41 tenors 0.08y..30y, linear interpolation inside,
                           linear extrapolation at the ends, output monthly to ~374
                           months × {Annual, Semiannual, Quarterly, Monthly}
        |
   ZeroCurve               continuous zeros + discount factors, linear interpolation,
                           flat extrapolation outside the grid; optional flat spread
```

The bootstrap recursion, shared by both legacy routines:

```text
cpn   = 100 · par / f
DF_i  = (100 − cpn · Σ_{k<i} DF_k) / (100 + cpn)
```

Our `bootstrap.py` expresses the zero **continuously**: `z = −ln(DF)/t`. `BondPrice`'s own
embedded bootstrap expressed it **semiannually**: `z = 2·((1/DF)^(1/2t) − 1)`. Same discount
factors, different expression — Liping caught the conflation risk, and it was verified on
2026-06-29.

**Reproduction quality** against the bundled golden CSVs: Annual / Semiannual exact,
Quarterly exact to 30 y (the >30 y node is terminal extrapolation), Monthly within 0.1 pp at
the short end. The golden test uses **segmented** thresholds rather than one loose one, so
the strict cases stay strict.

## 2. Currency routing

```python
ZeroCurve.from_currency(data_dir, "EUR", "2009-03-31", freq="Semiannual")
```

`CURVE_FILE` maps **USD, EUR, GBP, JPY, AUD, KRW**. A currency with no entry raises rather
than falling back. The wrapper the endpoint uses is
`core.market.curves.resolve_curve(currency, valuation_date, coupon_frequency)`, which also
picks the frequency variant and turns every failure into a single, path-free
`CurveUnavailable` with a `reason` of `not_found` or `build_failed`.

Three live failure modes, verified on the server:

```text
CHF 2009-03-31   no par-curve file configured for the currency   -> not_found
KRW 2009-03-31   file exists, that date is not in it             -> not_found
GBP 2009-03-31   file and date exist, bootstrap refuses:         -> build_failed
                 non-positive discount factor at t = 3.000,
                 the par curve is not arbitrage-free there
```

The GBP case blocks 2 GBP bonds and is on the opportunistic ask list. It is a **data**
problem, not a date problem.

## 3. The frequency variant matters

The bootstrap emits four variants and a bond must be discounted on the one matching its own
coupon frequency, because each variant solves a different zero grid. The map is
`{1: Annual, 2: Semiannual, 4: Quarterly, 12: Monthly}`.

Note a historical quirk: `scripts/calibrate_risk.py`'s vanilla path uses a **two-entry** map
(annual and semiannual only) and skips bonds with other frequencies — that is a driver-level
universe restriction, not an engine limit. `phase2_risk.py` uses the full four-way map.

## 4. TRAP — two day counts for the exercise-time axis

`dataio.call_schedules.to_lattice_schedule` defaults to **365.25** days per year while every
coupon grid is **ACT/364**. Both production drivers pass `days_per_year=364.0` explicitly,
so production has always been consistent. A new caller taking the default would silently put
exercise dates on a different axis than coupons.

New code uses `core.pricing.tree.schedule_times`, which is ACT/364 by construction, and a
test pins the two conversions against each other. The stale default is still there.

## 5. Valuation dates and where the data came from

- **2009-03-31** — the holdings date and the adopted baseline. The USD curve for it arrived
  from Mario on 2026-07-02 in the native schema. Before that, 3-31 was absent from the txt
  history (a gap from 2008-11-10 to 2009-06-10), which is why the project ran on 6-10 first.
- **2009-06-10** — retained as a control, and the source of the v1 evidence.
- The country txt files carry **both** 2009 dates; the "3-31 absent" gap was USD-only. KRW
  has 6-10 only.
- For the Monthly reconciliation, USD pillars for 2010-03-01, 2012-06-01 and 2012-12-12 came
  from **treasury.gov's** year-CSV endpoint (FRED is GFW-blocked from both machines) and
  live in `data/h15_pillars_monthly_recon.csv`.

## 6. Credit spreads (historical, v1 only)

The ICE BofA index OAS history (7 rating buckets, daily 1997-01-02 to 2025-11-07) survives
**only** inside `Pricing File.xlsm` / sheet `OAS Credit Curves`, read by `credit/oas.py`.
FRED truncated the free series to a rolling three years in April 2026, so the online API
cannot serve project history. Treasury `DGS*` series are government data and are **not**
truncated — that is how the 2009-03-31 curve was cross-validated.

This matters for history and for the v1 narrative. It is **not** an input to the current
method, where OAS is a per-bond calibration output.

## 7. A negative result worth not repeating

Date-matching the v1 rating-OAS method to 3-31 (3-31 curve **and** 3-31 index OAS) made
investment grade **worse**: median |diff| 6.43% → 11.14%, signed −0.41% → −6.70%. The
3-31 crisis-peak index OAS overstates these particular holdings' spreads. The 70-day gap was
never the precision lever; finer per-name spreads were, which is what per-bond calibration
now does. Do not propose the date-match as an improvement — it was tested and refuted.
