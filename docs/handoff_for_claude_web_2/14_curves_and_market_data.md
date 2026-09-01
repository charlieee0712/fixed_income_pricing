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

## 1a. ⭐ Par-yield file UNITS — declared, never detected (added 2026-08-30)

**The exports are not uniform.** Twenty-four of the twenty-six `*_Yield_Curve.txt` files store
par yields as **decimals** (`0.0304` = 3.04%). **`GBP_Yield_Curve.txt` and
`DKK_Yield_Curve.txt` store PERCENT** (`3.04` = 3.04%).

```python
# curves/bootstrap.py
PAR_YIELD_UNITS = {"GBP_Yield_Curve.txt": "percent", "DKK_Yield_Curve.txt": "percent"}
DEFAULT_PAR_YIELD_UNITS = "decimal"
```

`load_par_curve(path, date, units=None)` looks the file up by name; `units=` overrides per
call. Verified across all 26 files at three dates each, against the actual market — GBP's
2009-03-31 row is `0.731 / 1.183 / 2.341 / 3.157 / 4.157`, which is that day's gilt curve;
DKK's 2020-06-15 row runs `−0.463 … +0.295`, the negative-rate curve of that summer.

**Why a registry and not a heuristic.** A "values above 1 must be percent" rule gets GBP right
and **DKK wrong** — DKK's median value is 0.543, because Danish rates spent most of the sample
near zero. No threshold separates a 0.5% yield from a 0.5 decimal. Declaring is the only
honest option, and adding a new currency file means checking it against the market once and
adding a line.

**The guard.** `ParYieldUnitError` is raised **before** the bootstrap when any scaled par
value exceeds 100%. It exists because of what happened without it: read as decimals, the GBP
file became a 73%–415% par curve, and the bootstrap reported the only thing it could see —
*"par curve is not arbitrage-free at this node"*. That is a true statement about the curve we
built and a false one about the file, and it stood for two months as a data gap in the
registry with an open Bloomberg request behind it. Full account: `05_traps_and_gotchas.md`
§1.9; the rule it produced is in `03_conventions_and_laws.md`.

**What it unblocked:** both GBP corporates now price — France Télécom 7.50% 2011 at
**205.31 bp** / 1.86 y, and a UK EMTN fixed 5.50% 2033 at **197.30 bp** / 12.55 y, the latter
having been absent from the output rather than flagged. Cross-check: the second bond prices at
279.93 bp on the **USD** curve against 197.30 on its own, and the ~83 bp gap is precisely the
gilt-vs-Treasury difference at 24 years — two independently computed numbers agreeing.

## 2. Currency routing

```python
ZeroCurve.from_currency(data_dir, "EUR", "2009-03-31", freq="Semiannual")
```

`CURVE_FILE` maps **USD, EUR, GBP, JPY, AUD, KRW**. A currency with no entry raises rather
than falling back. The wrapper the endpoint uses is
`core.market.curves.resolve_curve(currency, valuation_date, coupon_frequency)`, which also
picks the frequency variant and turns every failure into a single, path-free
`CurveUnavailable` with a `reason` of `not_found` or `build_failed`.

Two live failure modes, verified on the server:

```text
CHF 2009-03-31   no par-curve file configured for the currency   -> not_found
KRW 2009-03-31   file exists, that date is not in it             -> not_found
```

⚠️ **GBP used to be the third**, listed here as the `build_failed` example and described as
"a data problem, not a date problem". That was wrong — see §1a. It was a units bug in our
loader, GBP now builds in all four variants, and both GBP bonds price.

`build_failed` therefore has **no live example today**. Its mapping is still tested, by
monkeypatching the loader to raise — which is the right way round: the subject of that test
is the error mapping, not the state of any file. A test whose fixture is "this real thing
happens to be broken" fails the day the thing is fixed, and looks like a regression.

## 3. The frequency variant matters

The bootstrap emits four variants and a bond must be discounted on the one matching its own
coupon frequency, because each variant solves a different zero grid. The map is
`{1: Annual, 2: Semiannual, 4: Quarterly, 12: Monthly}`.

Note a historical quirk: `scripts/calibrate_risk.py`'s vanilla path uses a **two-entry** map
(annual and semiannual only) and skips bonds with other frequencies — that is a driver-level
universe restriction, not an engine limit. `phase2_risk.py` uses the full four-way map.

## 4. ~~TRAP — two day counts for the exercise-time axis~~ ✅ CLOSED 2026-08-31

`dataio.call_schedules.to_lattice_schedule` used to default to **365.25** days per year while
every coupon grid is **ACT/364**. Both production drivers passed `days_per_year=364.0`
explicitly, so production was always consistent, but a new caller taking the default would
silently have put exercise dates on a different axis than coupons.

There is now **one** implementation, `core/utils/dates.exercise_schedule_times`, which both
`core.pricing.tree.schedule_times` and `dataio.call_schedules.to_lattice_schedule` delegate
to, and the `days_per_year` argument has been **deleted** — passing it raises `TypeError`.
The day count is project law, not a parameter.

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
