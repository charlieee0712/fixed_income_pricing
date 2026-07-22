# Phase-2 build — methods & decisions: AGY / GTD / ILB engines + static-CPR MBS skeleton (2026-07-22)

Follow-up to `docs/phase2_inventory_2026-07-20.md` (the read-only recon). This session BUILT the
three data-self-sufficient classes and the MBS engine skeleton; user拍板 on all methods below.
Code: `src/dataio/phase2.py` · `src/pricing/ilb.py` · `src/pricing/mbs.py` ·
`scripts/phase2_risk.py`. Tests 103 → **129 green** on 47. Outputs:
`outputs/phase2_risk_2009-03-31.csv` (baseline) + `…_2009-06-10.csv` (control), mirrored locally.

Recon corrections to the inventory (verified on 47 this session):

- The pool tab is **`Govt MTGE`** (sheet name exact); the `Mtge` sheet is the corporate
  pass-through pivot ("Details for Count of … Amortizing (mortgage-backed)"), not the MBS tab.
- Master maturity is **BW** (BV = 'Market value - local'); desc short/long = **Q/T**; the
  Asset/Liability indicator is **Y** but is uniformly `'A'` — it does NOT identify the short
  rows; the negative par sign itself does. All 10 negative-par rows are Govt-MBS TBA-style
  hedge positions (round lots to −44.2M, generic "30 YEAR GOLD" pools); none in AGY/GTD/ILB.
- Foreign par-curve txt files (EUR/JPY/AUD/GBP + country aliases) carry BOTH 2009-03-31 and
  2009-06-10 rows — the "2009-03-31 absent" gap was a USD-file-only problem (fixed by Mario's
  file in July). **KRW has 2009-06-10 only** (no 3-31 row). `ZeroCurve.CURVE_FILE` now maps
  JPY/AUD/KRW.

## 1. Government Agencies — 42 rows → 39 unique, routes locked

| route | n | rule (data-driven) | engine |
|---|---|---|---|
| vanilla | 27 | default | implied OAS to BT + risk (per-ccy curves) |
| callable-lattice | 5 | master AB call date present | BDT lattice, **Bermudan par call @100 from AB**, σ=0.15 |
| call-passed-vanilla | 4 | desc "maturity/call" date pair, call = 2006 (PASSED), AB blank | vanilla + flag |
| zero | 2 | BG < 0.01 (the Resolution Funding CPN STRIPS, BG=1e-5) | degenerate vanilla (single face flow) |
| cmo-tranche | 1 | "SER 3122 CL ZB" + Monthly freq | **BT mark** — REMIC Z-tranche misfiled as agency debenture; CMO phase |

**Methodology note (callables).** Bermudan par call @100 from the first call date is the
*industry-standard* structure for agency debentures — unlike the corporate book, where naked
par-call was a placeholder and make-whole the reality, par call here is the correct default, not
an assumption of convenience. The Sempra lie detector stays on: the driver annotates any negative
callable OAS or callable≫straight OAS. **@3-31 it never fired** — all 5 come out `call-active`
with coherent numbers (callable OAS 161-223bp vs straight 214-307bp; positive call cost).
Schedule rows live in `data/call_schedules.csv` (the single call-terms source; 5 rows appended
from AB) — a real Bloomberg step schedule drops in as data only.

**Validation headline: the custodian's AQ 'Duration - effective' MATCHES the lattice.**

| bond | lattice callable dur | straight dur | custodian AQ |
|---|---|---|---|
| FHLB 5.53 2014/call 2010-02 | **0.99** | 4.82 | 0.87 |
| FHLMC 5.3 2020/2010 | **4.30** | 8.41 | 5.92 |
| FNMA MTN 5.625 2021/2011 | **5.33** | 9.12 | 5.38 |
| FHLMC 5.625 2035/2015 | **9.66** | 13.65 | 9.74 |
| FNMA 6.0 2036/2016 | **9.12** | 13.40 | 9.62 |

4 of 5 within 0.06-0.50y of AQ (and far from straight): the custodian's agency durations are
option-adjusted, and the σ=15% BDT reproduces them — the exact reverse of the corporate finding
(there AQ ≈ straight, missing the call). Free external validation of the lattice.

**Call-passed evidence (the 4 re-routed bullets).** FNMA 4.625 2010 / FNMA 4.7 2010 / FNMA 4.75
2010 / FHLMC 4.75 2012 all show "mm-dd-2010/mm-dd-2006"-style pairs — one-time calls in 2006 that
were NOT exercised; the custodian agrees (AB blank), and their BTs (103.9-108.2) price to
maturity. Routed vanilla + flag (evidence beats a terms-unavailable mark). Their calibrated OAS
(60-93bp) sit exactly on the agency curve — confirming the read.

**Results @3-31** (calibration exact: |clean−BT| ≤ 6.6e-9 over 42 OAS-calibrated): class median
**121bp** (n=28 excl 5 near-maturity). GSE bullets 11-95bp; wides are all quasi-sovereign credit,
correctly so: KDB 607 / KEXIM 594 (Korea crisis pricing, BT 90-93) / PEMEX 2035 620 (BT 73.3) /
FHLB-Chicago SUB 392 (the troubled sub notes) / Hydro-Québec 178 / Israel US-gtd 88-152 /
Farmer Mac 144A 66-139. RefCorp STRIPS 107-113bp @ ~9.4y. Foreign: KfW-EUR 45, EIB-EUR 26,
EIB-AUD 129, KfW-JPY 62 (own-ccy curves). One name to watch: TNTD04366584 "FNMA 6.25 2011"
carries rating A/Aa2 in the master and calibrates 231bp — inconsistent with a GSE senior
debenture (the master rating row is odd); left as-data, worth one Mario question if it matters.

**Ratings treatment (AGY):** master carries `*AGY`/`*TSY` pseudo-ratings alongside AAA/Aaa — we
carry the raw S&P/Moody strings and report **class-level** medians (no forced notch-map);
quasi-sovereigns are visibly separated by their spreads.

## 2. Guaranteed (FDIC-TLGP) — 11 → 9, all vanilla, own bucket

All 9 are 2009-vintage FDIC-guaranteed TLGP notes (JPM ×2, GE Capital ×3, MS, Citi, BofA, Bank of
the West), USD semiannual, maturities 2011-2012. **Decision (documented rationale): reported as
`group = TLGP-guaranteed`, never inside bank rating buckets.** The credit substance is the FDIC
guarantee — the master itself rates them AAA/Aaa; folding them into A/BBB bank buckets would
distort the by-rating table, and folding them into a generic AAA bucket would blend government
credit into corporate statistics. Results @3-31: implied OAS 64-96bp, median **86bp** — a
liquidity/novelty premium over UST, no bank credit in it, consistent with where TLGP paper traded
in spring 2009.

## 3. Index-Linked — 16 → 15: the nominal-curve + inflation-assumption engine

**Model** (`pricing.ilb`): `ratio(t) = ratio_0 · (1+FIP_INFL)^t`; coupon flows
`real_cpn/f · 100 · ratio(t)`, redemption `100 · ratio(T)`; discount `exp(−t·(z_nominal + s))` on
the own-ccy curve; solve `s` so model clean = BT. `ratio_0` = BG ÷ description real coupon
(recovered per bond, 1.008-1.31 by vintage; the description formats are "2.00 DUE", "x%", and
"x.xx <date>" — parser in `dataio.phase2.parse_desc_coupon`, None-principle). BT is the
inflation-adjusted clean price (BT = BU/par·100 exact once duplicate account legs are SUMMED —
the dedupe rule sums par, MV and book cost).

**The sign convention — read before calling it a bug.** At the default `FIP_INFL=0` the
calibrated spread **must be negative ≈ −(breakeven)**: nominal ≈ real + expected inflation, so
zero-inflation cash flows matched to a market price push the whole inflation expectation into the
spread. This is arithmetic, not error — exactly: pricing with inflation π at spread s equals
pricing with 0 inflation at spread `s − ln(1+π)` (unit-tested to 1e-9). The spread therefore
lives in its **own column `implied_spread_vs_nominal_bp`** (companion `breakeven_bp = −spread`
when FIP_INFL=0) and never mixes with credit OAS or the by-rating medians.

**Results @3-31 = the engine's validation** (|clean−BT| ≤ 1.4e-8 over 14):

- US term structure of extracted breakevens: 2010 **−34bp** (near-maturity-flagged; the
  deflation-scare front end) → 2014-17 **+35…79bp** → 2025-29 **+85…108bp** → 2032 **+139bp**.
  Monotone, sub-150bp, negative at the short end — precisely the March-2009 deflation-panic
  breakeven curve (10y market BEI then ~120-150bp; TIPS-carry-unadjusted reads lower).
- **JGBi flips sign: spread +229bp = breakeven −2.3%** — Japan's deflation expectation,
  extracted with the correct sign on the JPY curve.
- Free per-bond cross-check: `z_nominal(dur) + s ≈ custodian DI real YTM` — e.g. the 2016 TIPS
  1.95% − 0.51% ≈ 1.44% vs DI 1.4387; the 2025 TIPS ≈ 2.85% vs DI 2.8736; JGBi vs DI 3.19. The
  engine reproduces the custodian's real yields bond by bond.

**v1 boundaries (recorded in `pricing.ilb` docstring):** ① TIPS deflation floor ignored — for
the near-par-ratio vintages (1.008 / 1.019) the max(ratio_T, 1) floor had REAL value in 2009's
deflation scare; needs an inflation-vol model, v2 item. ② Static inflation path ⇒ eff duration
(= spread bump = parallel nominal shift) is the full PV-weighted, i.e. a REAL-rate duration;
nominal/inflation co-movement not modelled. ③ No indexation lags/seasonality. ④ **KTBi
(TNTG673976U) BT-marked `ilb-indexation-unverified`**: BG == coupon exactly (no ratio embedded)
and its description carries no coupon ⇒ ratio_0 not derivable; Korea indexation convention →
the Mario/Bloomberg list (KRW curve also lacks a 2009-03-31 row — second blocker at baseline).

## 4. Govt MBS — static-CPR skeleton built; BZ verdict; awaiting the 8-field pull

`pricing.mbs` is built against the EXACT Bloomberg request already drafted for Mario:
`PoolTerms.from_bloomberg({mnemonic: value})` consumes MTG_WACPN / MTG_WAM / MTG_STATED_WALA /
MTG_AOLS / MTG_GEN_CPR_3M/6M/12M / MTG_HIST_COLLAT_CPR_LIFE (percent in, decimal internal), plus
the tab's BE net coupon — data drops in with zero code change. Engine: level-pay amortisation
re-amortised on the surviving balance + CPR→SMM prepayment + interest at the net rate; pricing on
the month grid `exp(−t(z+spread))` per 100 current face; `implied_spread_pool` /
`implied_cpr_pool` (the one-unknown GNMA fallback) / `pool_risk_metrics` (spread-duration + WAL —
the CPR(rate) response is the v2 prepayment model). Invariants green: CPR=0 ⇒ level annuity
amortising to zero at WARM; Σ principal = opening balance at any CPR; price = par exactly when
discounting at the (monthly-compounded) WAC at ANY CPR; duration strictly ↓ in CPR.

**BZ paydown-factor >1 — investigated and RESOLVED (not an error, keep the field):** the 9 rows
with BZ>1 (to 1.868) are ALL REMIC **accrual (Z) tranches** — "CL-Z", "CL VZ", "CL ZC",
"SER nnnn CL …" — whose face ACCRETES (coupon rolls into principal during lockout), so
current/original > 1 is correct behaviour. Cross-checks: BZ ≡ master CA 'Paydown factor'
(849/849 equal at 1e-9 — same field, two locations); master BX original face is EMPTY for all
MBS rows, so no par/BX reconstruction is possible (the factor stands alone). Verdict: keep BZ as
a descriptive field; the static-CPR engine prices per-100 current face and never needs it. Side
finding for the CMO phase: the Govt-MBS bucket itself contains REMIC Z/VZ/PO classes (and the 2
factor=0 + 5 near-zero-factor paid-down rows) — a routing question for the方案 round when the
Bloomberg data lands.

## 5. Control run @6-10 (mixed-date, mirrors the corporate finding)

Against the 6-10 curve the same 3-31 BT marks calibrate ~110bp tighter across the board (AGY
median 121→10bp, GTD 86→14bp; ILB breakevens 160-270bp): the Mar→Jun 2009 yield backup is
absorbed into the spread. Date-matched 3-31 stays the baseline; 6-10 kept as control, exactly as
in the corporate book.

## 6. Open items for Mario (adds to the standing list)

1. **KTBi indexation terms** (KR1035027T36): base CPI / ratio convention (+ the KRW curve has no
   2009-03-31 row — 6-10 only).
2. Standing: the corporate 11-security list (2026-07-20) + the Govt-MBS 8-field × 882-CUSIP pull.
3. Optional: the master's A/Aa2 rating on TNTD04366584 ("FNMA 6.25 2011", calibrates 231bp) —
   looks like a data quirk, only matters if agency by-name spreads are ever reported.
