# Phase-2 inventory — four new asset classes (Mario, 2026-07-20)

Read-only recon of the URS workbook for the next phase. Master = `Fixed Income` sheet, filtered on
`Asset sub category` (col U); pool terms = `Govt MTGE` tab. No code written — findings only;
approach to be decided per class after review.

Column discoveries (master): **BG = Income rate, BH = Income rate - annualized, CB = Payment
frequency, CA = Paydown factor, BX = Original face value**; `DO Coupon` / `DP Type of Coupon`
are empty for all four classes (as for corporates). The Govt MTGE tab has its OWN layout —
confirmed letters there: `DK Asset ID · AI CUSIP · BE Income rate · BS Market price ·
BV Maturity · BZ Paydown factor · CA Payment frequency · CU Shares/Par · DH YTM ·
DV-EC analytics block · DS = BS-100 (premium/discount)`.

## 1. Government Agencies — 42 rows / 39 unique ids

| field | fill |
|---|---|
| coupon (BG Income rate) | **42/42** — validated as the coupon: 10/10 exact match vs the %-figure embedded in the description |
| payment freq (CB) | 40/42 (Semi-Annually 37 · Annually 2 [the EUR/JPY internationals] · Monthly 1; the 2 blanks = the two zero-coupon strips) |
| maturity (BW) | 42/42 · ISIN 41/42 (1 NULL: TNTD04733316 FHLMC MTN) · par 42/42 |
| golden (BT / DI ytm) | 42/42 / 42/42 |
| ccy | USD 38 · EUR 2 (EIB, KfW) · JPY 1 (KfW) · AUD 1 (EIB) — curves exist for all four |

Mix: FNMA/FHLMC/FHLB debentures + quasi-sovereigns (Hydro-Québec, PEMEX gtd, KDB, KEXIM, Israel
US-gtd, KfW, EIB, Farmer Mac 144A). **Structure notes:** ① ~5-8 are CALLABLE agency debentures —
5 have master call dates (AB) and several more show "maturity/call" date pairs in the description
(some with already-passed call dates, i.e. surviving past first call) → decide vanilla+flag vs the
v2 lattice; ② 2 zero-coupon strips (Resolution Funding CPN STRIPS, BG≈0, BT≈70) → vanilla
degenerate. The rest = plain vanilla reuse as expected.

## 2. Guaranteed Fixed Income — 11 rows / 9 unique ids

**All 11 are FDIC-guaranteed TLGP crisis paper** (Morgan Stanley, JPMorgan, GE Capital ×3, Citi,
BofA, Bank of the West): USD, semiannual, coupons 1.65-2.25%, maturities 2011-2012, BT ≈ par
(100.2-100.7). Every field 11/11 (BG validated 2/2 vs description). **100% vanilla reuse.**
One方案 decision: rating treatment — the master carries the BANK ratings, but these trade as
government credit (FDIC) → suggest an own "guaranteed" bucket rather than the issuer rating.

## 3. Index Linked Government Bonds — 16 rows / 15 unique ids

**14 US TIPS + 1 JGBi (0.5% due 2015-06-10, JPY) + 1 Korea KTBi (2.75% due 2017-03-10, KRW).**
All fields 16/16 (freq all Semi-Annually; maturity/ISIN/par/BT/DI complete).

**Two conventions decoded from the file itself:**
- **BG = real coupon × current inflation index ratio** ⇒ the 2009-03-31 index ratio is
  recoverable per bond as BG ÷ description-coupon. Recovered ratios: 1998-99-vintage TIPS
  1.19-1.31, mid-2000s 1.01-1.12, JGBi 1.014 — a sensible CPI-accretion pattern.
- **BT = BU/CV × 100 exactly (all 14 USD rows) = the inflation-ADJUSTED price** (real price ×
  index ratio); real clean ≈ BT ÷ ratio (e.g. the 2.375% 2025 → 103.9 real at 2009-03-31 —
  plausible). So the recon identity BT×par=MV holds, and both quote bases are derivable.
  (Non-USD rows: BU is base-USD so BU/CV×100 = BT×FX — checked, consistent.)
- Caveat: the KTBi shows BG = coupon exactly (ratio 1.0?) and its description carries no coupon —
  Korea linker indexation convention needs a terms check (small lookup/Bloomberg item).

**Pricing path (to decide):** we have no real-yield curves → the v1 path is *nominal curve +
inflation assumption to project indexed cash flows*, seeded with the per-bond index ratios above
as the accrued-inflation starting point. JPY/KRW nominal curves exist for the two foreign linkers.

## 4. Government Mortgage Backed Securities — 888 rows / 882 unique; Govt MTGE tab joins 1:1 (882↔882, no orphans)

All USD; issuer mix FNMA 451 · FEDERAL-spelled 248 · GNMA 107 · FHLMC 79 · misc 3; payment freq
Monthly 850/852; **zero "ARM" mentions** → fixed-rate monthly pass-through pools (a static
fixed-rate CPR engine suffices; no floaters).

**What is usable in the tab:**

| field | fill | range | note |
|---|---|---|---|
| BE Income rate (pass-through coupon) | 888/888 | med 5.50 · max 30.1 ⚠️ | max outliers to inspect |
| BS Market price (golden) | 888/888 | med 104 · min 0.0041 ⚠️ | 3 rows < 1 (near-paid-down artifacts) |
| BV Maturity | 870/888 | 2009-2047 | 18 missing |
| BZ Paydown factor | 849/888 | med 0.527 · **max 1.868 ⚠️ (>1)** · min 0 | 39 missing |
| CU Shares/Par | 888/888 | **10 negative rows ⚠️** (to −44.2M) | short/liability rows — `Asset/Liability` col exists; treat separately |
| DH YTM (golden ref) | 886/888 | −99.9…386 at the tails | garbage extremes |

**The static-CPR input block is DEAD in the workbook: 0/888.** `WAC / WARM / WALA / AOLS /
PREP 1M/6M/1Y/LIFE` (cols DV-EC) are all cached `#NAME?` — broken Bloomberg add-in formulas
`=blp($AI2 & " MTGE", <field>)`. The intended field mnemonics survive in FB2:FI2:

> **MTG_WACPN · MTG_WAM · MTG_STATED_WALA · MTG_AOLS · MTG_GEN_CPR_3M · MTG_GEN_CPR_6M ·
> MTG_GEN_CPR_12M · MTG_HIST_COLLAT_CPR_LIFE**, keyed `CUSIP + " MTGE"`.
> (NB the sheet header says "PREP 1M" but the field is CPR_**3M** — header mislabel.)

⇒ **The Bloomberg request for Mario is exact:** pull those 8 fields for the 882 unique CUSIPs
(CUSIP col AI is 888/888 filled) — the same mechanism as the pass-through pull he is already
doing. Interim fallbacks to discuss: price on BE (coupon) + BV (stated maturity, overstates WARM)
+ an assumed/sector CPR, or imply a constant CPR from BS with OAS≈0 (defensible for GNMA);
one-price-two-unknowns means CPR and OAS cannot both be implied — decision for the方案 round.

## Golden marks (all four classes)

BT (master) fill: **AGY 42/42 · GTD 11/11 · ILB 16/16 · MBS 888/888** (tab BS also 888/888;
DS = BS−100 confirms). DI YTM near-complete everywhere. Reconciliation baseline is fully covered.

## Cross-class notes

- Every class has duplicate asset-ids across accounts (42→39, 11→9, 16→15, 888→882) → same
  dedupe-and-sum-par treatment as the corporate universe.
- Master `DO/DP` coupon columns: empty in all four classes — **BG/BH is the coupon carrier**
  (for linkers: coupon × index ratio; for MBS: the pass-through rate).
- Multi-currency footprint of the phase: EUR/JPY/AUD/KRW beyond USD — all four have curve files;
  routing = the existing `ZeroCurve.from_currency` path.
