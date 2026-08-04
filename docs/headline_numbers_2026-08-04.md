# Headline numbers — post clean/dirty-convention fix (2026-08-04)

**Citation rule: any figure quoted to Mario (or in any new report) comes from THIS page.** The
lattice-derived numbers quoted in earlier materials — `v2_progress_report.md` §5 (and its PDF),
`docs/phase2_methods_2026-07-22.md` §1, WORKLOG entries ≤ 2026-07-22 — are **superseded** by the
2026-08-04 convention fix (Liping code review; WORKLOG 2026-08-04, commits `f7e9e7d`/`c3ab2f5`).
What changed: the callable lattice now runs on the bond's real ACT/364 coupon dates (root PV =
true dirty) and calibrates model clean (= dirty − the single shared accrued formula) against the
custodian BT — clean vs clean, the same equation as every other engine. **Only lattice-routed
bonds moved; every vanilla / schedule / FRN / hybrid / ILB / zero number is bit-identical**
(spot-verified to full float precision against the pre-fix outputs).

Valuation basis 2009-03-31 (σ = 0.15, Bermudan par-call @100 from custodian AB via
`data/call_schedules.csv`), 2009-06-10 as control. Source outputs: `outputs/callable_risk.csv`,
`outputs/phase2_risk_2009-03-31.csv` / `_2009-06-10.csv` (regenerated 2026-08-04).

## (a) The call-active corporate A bond (TNTD04441873, 6.45% 06/2034, BT 90.04)

| | current | superseded (pre-fix) |
|---|---|---|
| eff-dur straight → callable | **11.43 → 10.37** (−1.06y from the call) | 11.56 → 10.54 |
| implied OAS callable / straight | **410.8 / 415.4 bp** (call cost 4.6 bp) | 412.3 / 416.7 |
| custodian AQ | 11.73 ≈ our **straight** dur | unchanged |

The story is unchanged: the custodian's corporate analytics do not capture the call; our lattice
does, and the option is worth ~1 year of duration on this name.

## (b) Agency callables — lattice effective duration vs custodian AQ (@3-31)

| bond | lattice callable dur | straight dur | custodian AQ | superseded dur |
|---|---|---|---|---|
| FHLB 5.53 2014 / call 2010-02 | **1.07** | 4.81 | 0.87 | 0.99 |
| FHLMC 5.30 2020 / 2010 | **3.72** | 8.35 | 5.92 | 4.30 |
| FNMA MTN 5.625 2021 / 2011 | **4.74** | 9.05 | 5.38 | 5.33 |
| FHLMC 5.625 2035 / 2015 | **9.43** | 13.50 | 9.74 | 9.66 |
| FNMA 6.00 2036 / 2016 | **8.88** | 13.16 | 9.62 | 9.12 |

Headline unchanged: the custodian's agency AQ is **option-adjusted** (all five sit far below the
straight durations) and the σ=15% BDT reproduces it — 4/5 within 0.75y (pre-fix: within 0.5y;
the old snapped grid's two approximations happened to offset toward AQ — exact conventions and
the machine-precision vanilla tie-out outrank that accidental fit; the FHLMC-2020 outlier's AQ
sits between callable and straight, i.e. the custodian only partially option-adjusts that one).

## (c) Final implied OAS — all lattice-routed bonds (bp, @3-31)

| bond | callable OAS | straight ref | note |
|---|---|---|---|
| corp TNTD04115619 (BBB 6.75% 2013, BT 60.65) | **1993.6** | 1993.6 | call-not-binding (distressed-wide) |
| corp TNTD04441873 (A 6.45% 2034) | **410.8** | 415.4 | call-active |
| corp TNTG701850W (EUR A 4.875% 2014) | **305.6** | 305.6 | call-not-binding |
| corp TNTD04923866 (AssuredGty 6.4% 2066) | — | — | unpriced; awaiting call schedule (Liping ask ④) |
| AGY FHLB 5.53 2014 | **190.0** | 306.1 | call-active |
| AGY FHLMC 5.30 2020 | **212.0** | 244.6 | call-active |
| AGY FNMA 5.625 2021 | **189.7** | 235.0 | call-active |
| AGY FHLMC 5.625 2035 | **178.9** | 213.5 | call-active |
| AGY FNMA 6.00 2036 | **191.4** | 231.9 | call-active |

Superseded OAS: corp 1959.0 / 412.3 / 293.2; AGY 160.5 / 223.0 / 197.0 / 181.2 / 194.1.
Shift vs pre-fix is **mixed-sign, ≤35 bp** (grid-timing correction, not a one-sided accrued
bias). @6-10 control: AGY 122.3 / 78.5 / 50.8 / 28.6 / 43.2 (pre-fix 133.2 / 79.3 / 51.3 /
30.5 / 43.4). Lie detector: clean on all five agencies at both dates.

## (d) Anything else that changed? — audit of other quotable figures

- **Nothing else.** Corporate by-rating medians, AGY vanilla median 121bp, quasi-sov wides
  (KDB 607 / KEXIM 594 / PEMEX 620 / FHLB-Chi 392), TLGP median 86bp, ILB breakevens (JGBi
  −2.3%), STRIPS 107-113bp, hybrid/FRN/reset numbers, universe counts (523/528, callable 5,
  make-whole 47), coverage (564 = 553 + 11 @3-31) — all bit-identical.
- **Test suite: 129 → 145 green** (new `test_price_convention`, 16: per-engine clean-form vs
  dirty-form calibration root invariance <1e-10; lattice ≡ `price_bond`; shared-accrued locks).
- **Duration denominator = DIRTY (full price), retained** after computing both ways for all 61
  AQ-carrying bonds @3-31: dirty closer on 41/61, median |dur−AQ| 0.236 vs 0.331 ⇒ the
  custodian's AQ is itself full-price-based; matches Bloomberg convention. Both variants are now
  standing columns in the driver outputs (`eff_dur` = dirty-base, `eff_dur_cleanden`).
- Note the v2 report's §5 "fourth callable refutes par-call (BT 108.69)" anecdote was already
  superseded on 2026-07-20 (Sempra = SEC-documented make-whole-only → re-routed off the lattice,
  implied 509bp as vanilla).
