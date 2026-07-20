# ISIN lookup — flagged / data-gap bonds (Mario meeting 2026-07-20)

**Meeting decisions (Mario, 2026-07-20):**
1. **Pass-through (16)** — Mario will pull the needed data from Bloomberg and send it; engine work
   (prepayment model) starts when it arrives. Until then they stay out of the output.
2. **Amortizing (1) + N/A (4)** — ignore permanently (confirmed; stays excluded per Mario).
3. **Flagged bonds in the completed classes** (⚠️ rows in COVERAGE.md + the FRN-spread gap):
   try to resolve terms from public sources by ISIN; whatever cannot be found goes back to
   Mario as a Bloomberg request list.

This file is the result of (3): a web lookup by ISIN/CUSIP of every flagged or spread-gap bond
(35 securities), run 2026-07-20. Every numeric term carries a source URL; nothing is filled from
"typical structure" guesses. Terms marked HIGH confidence are used to seed the data CSVs
(`data/coupon_schedules.csv`, `data/call_schedules.csv`, `data/frn_spreads.csv`); MEDIUM/LOW are
listed for Mario to spot-check on Bloomberg.

## Inventory (what we hold vs. what we needed)

Custodian identity decoded from the URS master (`Fixed Income` sheet cols T/W/X/AB/BW).
CUSIP = chars 3–11 of the US ISIN. Dates are from our data: mat = tab/master maturity,
call = master `AB` (custodian "next call").

### A. Fixed→Floating switch unknown (5) — route `frn-switch-unavailable`, BT-marked
| asset_id | ISIN | custodian name | mat | call (AB) |
|---|---|---|---|---|
| TNTD03009347 | US020002AV33 | ALLSTATE CORP JR SUB DEB FXD-FLTG SER B | 2037-05-15 | 2017-05-15 |
| TNTD04627285 | US76117JAB44 | RESONA BK FLT RT NT 144A | 2049-09-29 | 2016-04-15 |
| TNTD04735032 | US534187AS84 | LINCOLN NATL CORP CAP SECS VAR RT | 2066-05-17 | 2016-05-17 |
| TNTD04967448 | US53079EAN40 | LIBERTY MUT GROUP JR SUB NT SER A 144A 7.8% | 2087-03-07 | — |
| TNTD04986722 | US171232AP67 | CHUBB CORP 6.375% | 2067-03-29 | 2010-04-15 |

### B. Perpetual / reset terms unknown (8) — routes `frn-no-maturity`, `reset-*`
| asset_id | ISIN | custodian name | mat | call (AB) |
|---|---|---|---|---|
| TNTD03020850 | US05565AAB98 | BNP PARIBAS SUB NT TIER 1 144A 7.195% | 2049-06-29 (proxy) | 2037-06-25 |
| TNTD04509751 | US17133PAA66 | CHUO MITSUI TR & BKG SUB NT PERP 144A 5.506% | perp (BW=2015-04-15) | — |
| TNTG532803U | XS0229704886 | RESONA BANK LTD 4.125% | 2049-09-29 (proxy) | — |
| TNTG532805U | XS0229705008 | RESONA BANK LTD BD 144A | 2049-09-29 (proxy) | — |
| TNTG533596W | XS0231436238 | UNICRED ITAL CAP 4.028% NTS PERP | perp | 2015-10-27 |
| TNTG614042U | XS0244642889 | SHINSEI BANK 3.75%-FRN 02/16 '144A' | **2016-02-23 (master BW!)** | 2011-02-23 |
| TNTG614044U | XS0244642616 | SHINSEI BANK 3.75%-FRN 02/16 'REGS' | **2016-02-23 (master BW!)** | 2011-02-23 |
| TNTG701894W | XS0161100515 | TELECOM ITALIA (SA) 7.75% EMTN (VAR) | 2033-01-24 | — |

Note: the Shinsei pair's maturity was sitting in master `BW` all along (tab `C` empty) — the
`frn-no-maturity` flag for these two is resolvable from our own workbook. ⚠️ Do NOT make
`maturity_master` a blanket fallback: for perps the custodian stuffs the **call** date into `BW`
(e.g. Chuo Mitsui BW=2015-04-15 on a perpetual).

### C. Special structures (3)
| asset_id | ISIN | custodian name | what we need |
|---|---|---|---|
| TNTD04150829 | US03840PAC68 | AQUILA INC SR NT STEP UP, dtd 2003-06-27, due 2012-07-01 | the step coupon table |
| TNTD03037132 | US20030NAV38 | COMCAST CORP NEW 0% DUE 2037-08-15 | actual structure (BT 93.1 ≠ plain zero) |
| TNTD03203204 | US816851AL38 | SEMPRA ENERGY SR NT dtd 2008-11-20 8.9% due 2013-11-15 | real call terms (par-call conflicts w/ BT 108.69) |

### D. FRN quoted margins (19) — priced with spread→0 (folded into OAS); margin upgrades them
| asset_id | ISIN | custodian name | mat | call (AB) |
|---|---|---|---|---|
| TNTD03027773 | US073928X243 | BEAR STEARNS COS MTN VAR RT | 2010-07-19 | — |
| TNTD03035014 | US61532RAA77 | MONUMENTAL GLOBAL FDG II 2005-C FLTG 144A | 2010-06-16 | — |
| TNTD03057893 | US36962G3M40 | GEN ELEC CAP CORP MTN TR 00804 VAR RT | 2067-11-15 | 2009-11-15 |
| TNTD03080834 | US634902LH11 | NATL CITY BK CLEV MTN FLTG 1.2425% | 2010-01-21 | — |
| TNTD04087449 | US111021AD39 | BRIT TELECOM VARIABLE RATE NT | 2010-12-15 | — |
| TNTD04131505 | US693476AZ63 | PNC FDG CORP SR NT FLTG | 2012-01-31 | — |
| TNTD04259874 | US453414AB08 | INDEPENDENCE CMNTY BK VAR RT | 2014-04-01 | 2010-04-01 |
| TNTD04794469 | US025816AU39 | AMERICAN EXPRESS SUB DEB FLTG | 2066-09-01 | 2016-09-01 |
| TNTD04882955 | US61746BDC72 | MORGAN STANLEY MTN SER F FLTG | 2016-10-18 | — |
| TNTD04955876 | US61532XAB29 | MONUMENTAL GLOBAL FDG III FLTG 144A | 2014-01-15 | — |
| TNTG001023W | XS0099192790 | ANGLIAN WATER 5.375% (VAR) | 2009-07-02 | — |
| TNTG010475U | XS0197153371 | SUMITOMO MITSUI BKG VAR RT | 2014-10-27 | 2009-10-27 |
| TNTG023603W | XS0238543416 | BK TOKYO-MITSU UFJ 3.5%-FRN | 2015-12-16 | 2010-12-16 |
| TNTG405928W | XS0128842571 | ROYAL BANK OF SCOT 6% SUB (VAR) | 2013-05-10 | — |
| TNTG522013U | XS0191752434 | BK OF AMERICA 4.75%-FRN SUB | 2019-05-06 | 2014-05-06 |
| TNTG527525U | XS0212517550 | RESONA BANK 3.75%-FRN REGS | 2015-04-15 | 2010-04-15 |
| TNTG700307W | XS0126163764 | FRANCE TELECOM 7.5%-VAR GBP | 2011-03-14 | — |
| TNTG700496W | XS0128139531 | SOGERIM SA 7.25%-VAR GTD | 2011-04-20 | — |
| TNTG701369W | XS0146643191 | TELECOM ITALIA (SA) 7.25% EMTN (VAR) | 2012-04-24 | — |

(TNTG700307W is additionally GBP-curve-blocked — terms recorded for when a GBP curve lands.)

**Pre-lookup observation:** several EUR/GBP "(VAR)" names (BT 2010, Telecom Italia 2012/2033,
France Telecom 2011 GBP, possibly Sogerim/Anglian) look like **rating-linked coupon steps**, not
LIBOR floaters — if confirmed, their historical coupon path is deterministic (rating history is
public) and they re-route from the FRN engine to `vanilla-schedule` via `coupon_schedules.csv`.

## Findings

### C. Special structures — all three RESOLVED (HIGH confidence, SEC primary documents)

**TNTD03203204 | US816851AL38 — Sempra Energy 8.90% Notes due 2013-11-15** — FULL / HIGH
- **Make-whole call ONLY (Adjusted Treasury Rate + 50 bp), exercisable any time; NO par call, no
  fixed-price schedule, no sinking fund.** The custodian's "next call 2009-05-15" is the FIRST
  COUPON date ("commencing May 15, 2009"), not a call date.
- $250M, priced 2008-11-17 @ 99.608 (yield 9.00% = UST+670bp), settled 2008-11-20; s.a. May15/Nov15.
- Three primary sources agree: FWP `sec.gov/Archives/edgar/data/1032208/000119312508237853/dfwp.htm`,
  424B2 `.../000119312508238435/d424b2.htm` (Optional Redemption p. S-9, verbatim clause), Officers'
  Certificate EX-4.1 `.../000119312508240165/dex41.htm`.
- **Model action:** make-whole ⇒ option value ≈ 0 ⇒ re-route `callable`→make-whole→vanilla
  (canonical); DELETE the wrong par-call row from `data/call_schedules.csv`. Resolves the
  "par-call conflicts with BT 108.69" note — the bond trades as a straight bullet.

**TNTD04150829 | US03840PAC68 — Aquila Inc 11.875% Senior Notes due 2012-07-01** (step-up solved) — FULL / HIGH
- Base 11.875% ($500M, issued 2002-07-03; this CUSIP = the 2003-06-27 exchange notes — matches the
  custodian "dated 06-27-2003"). Coupon is **rating-linked**, not date-scheduled: +100/125/150bp per
  agency notch below IG (Moody's Ba1/Ba2/Ba3−; higher of S&P/Fitch BB+/BB/BB−), day-weighted
  mid-period. History: 11.875 → 13.125 (Moody's Ba2, 2002-09) → 14.875 max (2003–2008) →
  **stepped back down to 11.875% on post-Great-Plains-acquisition IG (2008)**.
- **At 2009-03-31 the coupon = 11.875%** — GXP Q1-2009 10-Q (balance date exactly 3/31/09) lists
  "11.875% Series | 2012 | 500.0"; "14.875" absent from FY2008 10-K & 2009 10-Qs (grep-verified).
- Semiannual Jan1/Jul1, 30/360; make-whole T+50 only.
- Sources: S-4 `sec.gov/Archives/edgar/data/66960/000091205702037266/a2090171zs-4.htm` (step table,
  make-whole), 424B3 `.../000104746903018833/a2111197z424b3.htm` (exchange, 14.875 period), MO-PSC
  conversion report `.../1143068/000114306808000048/report_conversion.htm` (step-down clause),
  Q1-09 10-Q `.../1143068/000114306809000041/f10q09-q1.htm` (2009 coupon).
- **Model action:** all remaining CFs @ base 11.875% ⇒ `schedule-unavailable` → **vanilla** with
  coupon 0.11875 via `data/coupon_schedules.csv`. BT 105.0 ⇒ ~10% YTM: sane for BBB 2009.

**TNTD03037132 | US20030NAV38 — Comcast Corp 6.950% Notes due 2037-08-15** (NOT a zero!) — FULL / HIGH
- **The custodian's 0% coupon is a data error.** CUSIP 20030NAV3 = "6.950% Notes due 2037":
  plain fixed s.a. Feb15/Aug15, $2.0B, issued 2007-08-23 @ 99.790, make-whole T+30, guaranteed by
  the Comcast cable subsidiaries. No conversion, no put, no step. Confirmed by Comcast's own 2017
  exchange-offer 8-K exhibit (CUSIP↔title verbatim) + 2007 fund holdings + the 424B2.
- Sources: 424B2 `sec.gov/Archives/edgar/data/1166691/000089322007002912/w38473e424b2.htm`,
  8-K exhibit `.../000095010317009645/dp81290_ex9901.htm`, holdings `.../773757/000077375707000253/table.txt`.
- **Model action:** re-route `zero-structured` → **vanilla** with coupon 0.0695 via
  `data/coupon_schedules.csv`. BT 93.12 ≈ 7.5% yield — normal crisis IG; the −486bp OAS was an
  artifact of the wrong 0% input. (Correct the v3 report's "structured payoff" interpretation.)

### A. Fixed→Floating switch bonds — ALL 5 still FIXED at 2009-03-31 (switches 2016/2017/2037)

**TNTD03009347 | US020002AV33 — Allstate Series B 6.125% Fixed-to-Floating Jr Sub due 2067** — FULL / HIGH
- Fixed **6.125%** s.a. (May15/Nov15, 30/360) until **2017-05-15**; then **3M LIBOR + 193.5bp** qtly
  (ACT/360). Par call from 2017-05-15 (make-whole before). Scheduled maturity 2037-05-15 (= custodian
  "maturity"), **final maturity 2067-05-15**. $500M, issued 2007-05-10. Deferral up to 10y.
- Src: 424B5 `sec.gov/Archives/edgar/data/899051/000104746907003784/a2177656z424b5.htm`; CUSIP↔title
  via 2013 tender 8-K `.../000110465913051035/a13-15514_1ex99.htm`.

**TNTD04627285 | US76117JAB44 — Resona Bank 5.85% perpetual sub (144A)** — PARTIAL / MEDIUM
- Fixed **5.85%** until par call **2016-04-15**; perpetual (2049-09-29 = proxy). Post-2016 reset
  formula + margin **NOT public** (144A OM) → **Bloomberg列表**. In 2009: fixed 5.85% (PIMCO N-Q
  2/28/2009 shows it live at 5.85%).
- Src: fund N-CSR/N-Q filings (Dunham 2008, Bernstein 2005 "Callable 04/15/2016 @ 100", PIMCO 2009).

**TNTD04735032 | US534187AS84 — Lincoln National 7% Capital Securities due 2066-05-17** — FULL / HIGH
- Fixed **7%** s.a. (May17/Nov17, 30/360) until **2016-05-17**; then **3M LIBOR + 235.75bp** qtly
  (ACT/360). Par call from 2016-05-17. $800M, issued 2006-05-17. Deferral 5y.
- Src: form of security `sec.gov/Archives/edgar/data/59558/000119312506114841/dex42.htm` (CUSIP
  printed); 424B4 `.../000119312506111911/d424b4.htm`.

**TNTD04967448 | US53079EAN40 — Liberty Mutual 7.80% Series A Jr Sub due 2087-03-07 (144A)** — FULL(core) / HIGH
- Fixed **7.80%** until **2037-03-15**; then **3M LIBOR + 357.6bp**; par call from 2037-03-15. $700M
  (~2007-03 issue). Freq/day-count not public (144A) — s.a. Mar/Sep 15 likely but unverified.
- Src: issuer's 2019 Series D OM (ISE listing particulars, verbatim rate structure); Liberty Q2-2022
  financial statements footnote; tender PRs (CUSIP↔ISIN identity).

**TNTD04986722 | US171232AP67 — Chubb 6.375% DISCS due 2067-03-29** — FULL / HIGH
- Fixed **6.375%** s.a. (Apr15/Oct15, 30/360) until **2017-04-15**; then **3M LIBOR + 225bp** qtly
  (ACT/360). Par call from 2017-04-15 (make-whole T+25 before). Scheduled maturity 2037-04-15,
  final 2067-03-29. $1B, settled 2007-03-29. (Custodian call fields 2009/2010-04-15 = coupon-date
  artifacts.)
- Src: FWP `sec.gov/Archives/edgar/data/20171/000095012307004523/y32307fwfwp.htm` + form of note
  `.../000095012307004745/y32658exv4w3.htm` (both print the CUSIP).

**Modeling note (all 5):** at VAL=2009-03-31 every switch bond is in its fixed leg ⇒ near-term CFs
are known fixed coupons; the floating tail starts 2016+ with now-known margins (except Resona US).
Deep-discount BTs (23–57) = market pricing extension/deferral, consistent with our
continuation-style treatment; a proper fixed-until-switch + forward+margin engine mode is now
data-feasible for 4/5.

### D. FRN / floating results — US batch 2 (agent G)

**TNTD04131505 | US693476AZ63 — PNC Funding Corp FRN due 2012-01-31** — FULL / HIGH
- Plain FRN: **3M LIBOR + 14bp**, qtly Jan/Apr/Jul/Oct 31, ACT/360, $750M, issued 2007-02-01,
  PNC parent guarantee (NOT TLGP — pre-dates the program). Non-callable (none stated).
- Src: FWP `sec.gov/Archives/edgar/data/713676/000095015207000498/l24307afwp.htm` (CUSIP printed).

**TNTD04259874 | US453414AB08 — Independence Community Bank 3.75% Fixed/Floating Sub due 2014** — FULL / HIGH
- 10NC5: fixed **3.75%** first five years (issued 2004-03-22, $250M), then **3M LIBOR + 182bp**;
  callable at par from **2009-04-01** (custodian's 2010-04-01 is stale/wrong). Obligor by 2009 =
  Sovereign Bank (Santander). At VAL=2009-03-31: last day of the fixed leg ⇒ effectively floating
  L+182 (callable par) for the whole remaining life. Freq not stated (bank note, no prospectus).
- Src: ICBC FY2004 10-K Note 13 verbatim `sec.gov/Archives/edgar/data/945734/000095012305002998/y06559e10vk.htm`.

**TNTD04794469 | US025816AU39 — American Express 6.80% Subordinated Debentures (hybrid)** — FULL / HIGH
- **Misclassified as plain floating — actually fixed-to-float:** fixed **6.80%** s.a. Mar/Sep 1
  (30/360) until **2016-09-01**, then **3M LIBOR + 222.75bp** qtly ACT/360; par call from
  2016-09-01; stated maturity 2036-09-01 auto-extendible to 2066-09-01; $750M, settled 2006-08-01;
  deferral up to 10y. At 2009: FIXED 6.80% ⇒ move from `floating` to the switch-bond treatment.
- Src: FWP `sec.gov/Archives/edgar/data/4962/000095011706003189/a42447.htm` + form of debenture
  `.../000095011706003298/ex4-2.htm`.

**TNTD04882955 | US61746BDC72 — Morgan Stanley Series F FRN due 2016-10-18** — FULL / HIGH
- Plain FRN: **3M LIBOR + 45bp**, qtly on the 18th (Jan/Apr/Jul/Oct), ACT/360, non-callable
  ("may not redeem"), $1.75B total (1.25B + two re-openings), issued 2006-10-18.
- Src: FWP `sec.gov/Archives/edgar/data/895421/000090514806006155/efc6-2501_formfwp.htm` + 424B2s.

**TNTD04955876 | US61532XAB29 — Monumental Global Funding III FRN 144A due 2014-01-15** — identity HIGH / terms LOW
- Floating, 144A, funding-agreement program (AEGON/Monumental Life); **no public source states the
  index/margin** (zero EDGAR hits for the CUSIP). A 2011 fund schedule shows 0.478% in effect
  (⇒ ~L+20bp back-out, unverified). → **Bloomberg列表** (margin + freq).
- Src: OpenFIGI identity; SEI N-Q `sec.gov/Archives/edgar/data/701939/000119312511175450/dnq.htm`.

### D. FRN / floating results — US batch 1 (agent F)

**TNTD03027773 | US073928X243 — Bear Stearns Series B FRN due 2010-07-19** — FULL / HIGH
- Plain FRN: **3M LIBOR + 40bp**, qtly on the 19th (Jan/Apr/Jul/Oct) — custodian freq "2" is wrong,
  it is QUARTERLY. $460M, issued 2007-07-19, non-callable. (Day count not in the pricing supp.)
- Src: 424B2 `sec.gov/Archives/edgar/data/777001/000114420407036819/v081140_424b2.htm` (CUSIP-exact).

**TNTD03035014 | US61532RAA77 — Monumental Global Funding II 2005-C FRN 144A due 2010-06-16** — NONE / LOW
- Exempt 144A funding-agreement paper: **zero EDGAR hits, no public terms**. Sibling series document
  the program but not 2005-C. → **Bloomberg列表** (index + margin + freq).

**TNTD03057893 | US36962G3M40 — GE Capital 6.375% Fixed-to-Floating Sub Debentures due 2067** — FULL / HIGH
- **Misclassified as plain floating — actually fixed-to-float:** fixed **6.375%** s.a. May/Nov 15
  (30/360) until **2017-11-15**, then **3M LIBOR + 228.9bp** qtly ACT/360. Make-whole (whole-only)
  before 2017-11-15, par call after; deferral 10y. $2.5B, settled 2007-11-15. Custodian call
  "2009-11-15" = coupon-date artifact. At 2009: FIXED 6.375% ⇒ switch-bond treatment.
- Src: FWP `sec.gov/Archives/edgar/data/40554/000093041307008461/c51087_fwp.htm` + form of
  debenture `.../000093041307008751/c51257_ex4b.htm`.

**TNTD03080834 | US634902LH11 — National City Bank (Cleveland) FRN bank note due 2010-01-21** — NONE / LOW
- 3(a)(2)-exempt bank note: **no public formula** (zero EDGAR hits). Custodian current coupon
  1.2425% @2009-03-31 is the one hard datum (⇒ ~L+11-16bp back-out, unverified).
  → **Bloomberg列表** (index + margin + freq).

**TNTD04087449 | US111021AD39 — British Telecom 8.125% (min) rating-step notes due 2010-12-15** — FULL / HIGH
- **Rating-step fixed confirmed (NOT a LIBOR FRN):** base 8.125%, +25bp per rating category per
  agency below Moody's A3 / S&P A−, reversible, floor 8.125%; $3.0bn of the Dec-2000 $10bn global.
- **Evidenced coupon path:** 8.625% through FY2008/09 → accruing **8.625% at 2009-03-31** (March-09
  downgrades bite from the next coupon period) → **9.125% from the June-2009 period** (BT 20-F
  FY2010 shows "9.125% (2009: 8.625%)"). S.a., Dec-15 cycle (Jun/Dec 15 inferred).
- ⇒ deterministic schedule at VAL: Jun-09 coupon @8.625%, then 9.125% to 2010-12-15 maturity →
  re-route `floating` → **vanilla-schedule** via `coupon_schedules.csv`.
- Src: BT 20-F FY2009 `sec.gov/Archives/edgar/data/820534/000115697309000314/u06940exv15w2.htm`,
  FY2010 `.../000095012310053015/u08919exv15w2.htm`; CUSIP identity via AbitibiBowater 11-K
  `.../1393066/000139306609000043/form11k.htm`.

### D. FRN / floating results — EUR/GBP telecom + Resona (agent I)

**TNTG527525U | XS0212517550 — Resona Bank EUR 1bn 3.75% subordinated due 2015-04-15** — PARTIAL / MEDIUM
- EUR1bn sub (FY2005 AR), alive at 2009-03-31 (FY2009 AR), redeemed during FY2010/11 — consistent
  with the 2010-04-15 call. **In 2009: fixed 3.75%** (pre-call fixed leg). Post-call floating
  formula NOT public → **Bloomberg列表**. (Currently FRN-priced; really a mid-life fixed-to-float.)
- Src: Resona Holdings ARs `resona-gr.co.jp/holdings/english/investors/financial/annual/pdf/ar05|09|11.pdf`.

**TNTG700496W | XS0128139531 — Sogerim/Telecom Italia Finance €2bn notes due 2011-04-20** — FULL / HIGH
- **Rating-step fixed (not a floater):** base 7.00% at issue (custodian's 7.25% was the 2004-08
  level), +25bp per notch per agency below Moody's Baa1 / S&P BBB+, symmetric step-down; history
  7.00% → 7.25% (from Apr-2004 coupon) → **7.50% from the Apr-2008 coupon** (TI 20-F filed
  2009-04-10: "the new rate is now equal to 7.50%"). Annual April coupon; guaranteed by Telecom
  Italia SpA. **In 2009: 7.50%** ⇒ deterministic path → vanilla-schedule (flat 0.075 remaining).
- Src: TI 20-F FY2008 `sec.gov/Archives/edgar/data/948642/000119312509077016/d20f.htm` (mechanism
  F-61 + history), FY2003 20-F `.../000119312504101697/d20f.htm` (Sogerim origin, 3-tranche €6bn).

**TNTG701369W | XS0146643191 — Olivetti Finance/TI 7.25% Guaranteed Notes due 2012-04-24** — FULL / HIGH
- **PLAIN FIXED 7.25% annual (ACT/ACT ISMA), NO step, NO float** — pricing supplement reads
  "Interest Basis: 7.25 per cent. Fixed Rate… Change of Interest Basis: Not Applicable", and the
  TI 20-F step-bond list excludes it. The custodian "(VAR)" tag is simply wrong (blanket-applied
  to TI paper). €1bn (2×500m tranches 2002). ⇒ re-route to **vanilla-schedule flat 7.25%**.
- Src: prospectus `oblible.com/Prospectus/www.oblible.com__XS0146643191.pdf` (ISIN printed);
  TI 20-F FY2008 (row carries no step-note letter).

**TNTG700307W | XS0126163764 — France Télécom GBP 600m 7.50% notes due 2011(-03-14)** — FULL / HIGH
- **Rating-step fixed** (March-2001 jumbo): +25bp per notch per agency below Moody's A3 / S&P A−,
  reversible, **floored at the issue coupon 7.50%**. At 2009-03-31 FT was A3/A− (at the trigger,
  not below; unchanged through 2008, "no step-up clause was activated") ⇒ **coupon = 7.50% floor**.
  Deterministic flat 7.50% remaining — but the bond stays **GBP-curve-blocked** until a usable GBP
  par curve lands (schedule seeded, ready).
- Src: FT 20-F FY2008 `sec.gov/Archives/edgar/data/1038143/000130817909000052/francetelecom20f.htm`
  (verbatim clause + ratings 12/31/2008), FY2002 20-F `.../000095016803000869/d20f.htm`; EU decision
  `eur-lex...32006D0621` (2002 rating chronology).

### D. FRN / floating results — EUR batch 1 (agent H)

**TNTG001023W | XS0099192790 — Anglian Water Services Financing €350m 5.375% due 2009-07-02** — PARTIAL / HIGH-for-2009
- **Plain fixed 5.375%** — issuer statutory accounts drawn at exactly 2009-03-31 list it "5.375%
  Fixed" with no step footnote (step footnotes exist on sibling lines). "(VAR)" contradicted.
  → vanilla-schedule flat 5.375% (annual; matures 3 months after VAL).
- Src: AWSF Directors' Report & Accounts FY2009/FY2004/FY2003 (Companies House PDFs); OpenFIGI
  "AWLN 5.375 07/02/09".

**TNTG010475U | XS0197153371 — SMBC €1.25bn Fixed-to-Floating Sub due 2014-10-27** — FULL / HIGH
- Issuer's own Offering Circular fetched: fixed **4.375%** annual (Oct-27 cycle) until
  **2009-10-27**; then **6M EURIBOR + 225bp** s.a. (Apr/Oct 27, ACT/360); callable par 2009-10-27
  and every floating IPD (FSA consent); maturity 2014-10-27. Issued 2004-07-27, LT2.
  At VAL: fixed 4.375%, switch 7 months out ⇒ needs the fixed-then-float engine (margin KNOWN).
- Src: OC `smbc.co.jp/aboutus/english/stock-bond/pdf/eur1250M.pdf` (saved to scratchpad);
  cbonds title + OpenFIGI "SUMIBK V4.375 10/27/14".

**TNTG023603W | XS0238543416 — BTMU €1bn 3.50% sub due 2015-12-16** — PARTIAL / MEDIUM
- Fixed **3.50%** (issued 2005-12-16), EUR995m out at 2009-03-31; classified "adjustable/floating"
  by MUFG 20-F; redeemed during FY2010/11 (consistent with the 2010-12-16 call). **Post-call
  index/margin NOT public** → **Bloomberg列表**. At VAL: fixed 3.50%.
- Src: BTMU ASR FY2009/FY2010 (`bk.mufg.jp/...asr2009|2010.pdf`); MUFG 20-F FY2006/FY2009.

**TNTG405928W | XS0128842571 — RBS €1.5bn 6% Subordinated Eurobonds due 2013-05-10** — HIGH (structure)
- **Plain fixed 6% bullet — the "call 2008 / floating since" hypothesis REFUTED**: FY2007+FY2008
  20-F tables annotate every callable line "(callable …)" but not this one; Oct-2009 6-K names the
  series with no Fixed/Floating qualifier; LT2 non-deferrable. "(VAR)" wrong again.
  → vanilla-schedule flat 6% (annual).
- Src: RBS 6-K 2009-10-30 (series+ISIN, both tranches), 20-F FY2007/FY2008.

**TNTG522013U | XS0191752434 — Bank of America 4.75% Fixed/Floating Callable Sub due 2019-05-06** — FULL / HIGH
- The executed global note itself is on EDGAR (ISIN/WKN printed): fixed **4.75%** annual
  (ACT/365-6) until single par call **2014-05-06**; then **3M EURIBOR + 146bp** qtly
  (Feb/May/Aug/Nov 6, ACT/360) to maturity 2019-05-06. €1bn, issued 2004-05-06.
  At VAL: fixed 4.75% ⇒ fixed-then-float engine (margin KNOWN).
- Src: EX-4 global note `sec.gov/Archives/edgar/data/70858/000089552704000047/bofafixednote11.htm`.

### B. Tier-1 / perpetual results (agent B)

**TNTD03020850 | US05565AAB98 — BNP Paribas $1.1bn Undated Deeply Subordinated T1 144A** — FULL / HIGH
- Perpetual; fixed **7.195%** s.a. (Jun/Dec 25) until **2037-06-25**; then **3M USD LIBOR + 129bp**
  qtly; par call 2037-06-25 + every IPD after (regulatory approval). Issued 2007-06-25.
  In 2009: fixed 7.195% ⇒ current reset-continuation treatment is a good fixed-leg approximation
  until 2037; margin now known for the future engine.
- Src: oblible bond page (OC transcription) + BNP IR's own OC PDF for this ISIN.

**TNTD04509751 | US17133PAA66 — Chuo Mitsui Trust & Banking $850M 5.506% perpetual jr sub 144A** — PARTIAL / MEDIUM
- Perpetual (issuer's audited Note 14), fixed **5.506% until 2015-04-15** "then variable"
  (holder schedules). **Post-2015 reset formula NOT public** (144A OC) → **Bloomberg列表**.
  In 2009: fixed 5.506%.
- Src: Mitsui Trust Holdings AR2006 Note 14; John Hancock N-Q (~Jan-2009); Monsanto 11-K (CUSIP map).

**TNTG533596W | XS0231436238 — UniCredito Italiano Capital Trust III €750M perp trust preferred** — FULL / HIGH
- Full final OC (246pp) read on UniCredit's own site: fixed **4.028%** ANNUAL (Oct-27) until
  **2015-10-27**; then **3M EURIBOR + 176bp** qtly (Jan/Apr/Jul/Oct 27); par call any IPD from
  2015-10-27 (Special-Event make-whole Bund+50bp before); non-cumulative T1. Redeemed in full
  2015-10-27 (issuer notice). In 2009: fixed 4.028% — BT 36 = extension/coupon-skip pricing,
  contractual regime unchanged.
- Src: `unicreditgroup.eu/.../XS0231436238.pdf` (final OC, ISIN printed) + 2015 redemption notice.

**TNTG701894W | XS0161100515 — Olivetti Finance/TI Finance 7.75% Guaranteed Notes due 2033-01-24** — FULL / HIGH
- **PLAIN FIXED 7.75% annual (ACT/ACT ISMA), NO call/put, NO rating step** — both pricing
  supplements (2003 original + 2005 re-opening, issuer archive) read "Not Applicable" on every
  option field, and the TI 20-F's step-bond enumeration excludes this series. €1.05bn total.
  The workbook's "Fixed → Reset (step/var)" class is wrong ⇒ re-route `reset-terms-unavailable`
  → **vanilla-schedule flat 7.75%** (BT 92.72 now yields a real implied OAS).
- Src: gruppotim.it PS PDFs (ISIN printed); TI 20-F FY2003 step enumeration; oblible EMTN base OC.

### C. Japanese-bank EUR hybrids (agent C)

**TNTG532803U | XS0229704886 — Resona Bank perpetual sub 4.125% (2005-09-15 issue)** — PARTIAL / MEDIUM
- Perpetual; first call **2012-09-27** @100 then each coupon date (NOT 2015 — custodian's 2049-09-29
  is a proxy); issued 2005-09-15, ~€800m across the Sept-2005 tranches; all Resona EUR bonds exit
  the balance sheet during FY2012 (= called at first call). Post-call formula NOT public →
  **Bloomberg列表**. In 2009: pre-call 4.125% (custodian).
- Src: finanzen.net ISIN factsheet (WKN A0GFET) + Resona AR2006/AR2010/AR2013 aggregates.

**TNTG532805U | XS0229705008 — Resona Bank perpetual sub, sister tranche** — PARTIAL / LOW
- Same 2005-09-15 offering, first call 2012-09-27; whether it is the 144A twin of the 4.125%
  tranche or a floating tranche is UNRESOLVED → **Bloomberg列表 (all terms)**. Stays BT-mark.

**TNTG614042U / TNTG614044U | XS0244642889 / XS0244642616 — Shinsei Bank €1bn step-up callable LT2 (144A/RegS)** — structure HIGH, margin missing
- **The `frn-no-maturity` mystery resolved: dated 2016-02-23**, one series: fixed **3.75%** annual
  until first call **2011-02-23**, then "floating rate per quarter annum (Step-up)"; callable any
  IPD ≥2011-02-23 (FSA approval); issued 2006-02-23 @99.486, SGX-listed. Crisis history: buybacks
  → €543m by 2010-08, Sept-2010 exchange into 2020 notes, call FOREGONE at first call (Jan-2011
  decision), €200m out at 3/2011, called Dec-2013. **Post-call index+margin NOT public**
  (3.029% observed 3/2011 ⇒ ~3mE+195bp back-out, unverified) → **Bloomberg列表** (margin only).
  In 2009: fixed 3.75%.
- Src: Shinsei exchange-offer PR 2010-08-31 (full terms table) + cancellation PR + AR2006/10/11.

## Result summary

Of the **35 securities looked up: 22 FULL (HIGH confidence, primary documents), 10 PARTIAL, 3 NONE**
(all three exempt-market US paper with zero public documentation).

**Actioned in the model now (14 bonds):**
- `data/make_whole_overrides.csv` — Sempra re-routed callable → make-whole→vanilla (canonical);
  wrong par-call row removed from `data/call_schedules.csv`.
- `data/coupon_schedules.csv` — 9 deterministic coupon paths: Aquila 11.875 · Comcast 6.95 (zero
  was a custodian error) · BT 8.625/9.125 step path · Sogerim 7.50 · TI-2012 7.25 (plain fixed) ·
  TI-2033 7.75 (plain fixed) · Anglian 5.375 (plain fixed) · RBS 6.00 (plain fixed) · FT-GBP 7.50
  floor (seeded; GBP curve still blocks). All re-route to `vanilla-schedule` and now carry real
  implied OAS + risk metrics instead of BT-marks / wrong-engine prices.
- `data/frn_spreads.csv` — 4 quoted margins priced explicitly (Bear L+40 q · PNC L+14 q ·
  MS L+45 q · IndepComm L+182): OAS no longer absorbs the margin; Bear/PNC/MS also corrected to
  QUARTERLY.

**Parked for the fixed-then-float engine (`data/hybrid_switch_terms.csv`, 18 rows):** at
2009-03-31 **every** fixed-to-float hybrid in the book was still in its FIXED leg (switches
2009-10…2037): Allstate, Lincoln, Liberty, Chubb, AmEx, GE (the last two were misclassified as
plain floaters), SMBC, BofA, BNP, UniCredit + the margin-gap names below. Deep-discount BTs on
these = extension/deferral pricing; engine mode next.

## Bloomberg request list for Mario (not found / low confidence)

| # | asset_id | ISIN | security | what's missing |
|---|---|---|---|---|
| 1 | TNTD03035014 | US61532RAA77 | Monumental Global Funding II 2005-C FRN 144A, due 2010-06-16 | index + margin + freq (zero public docs) |
| 2 | TNTD04955876 | US61532XAB29 | Monumental Global Funding III FRN 144A, due 2014-01-15 | index + margin + freq (zero public docs) |
| 3 | TNTD03080834 | US634902LH11 | National City Bank (Cleveland) FRN bank note, due 2010-01-21 | index + margin + freq (3(a)(2)-exempt; current coupon 1.2425% known) |
| 4 | TNTD04627285 | US76117JAB44 | Resona Bank 5.85% perpetual 144A | post-2016-04-15 reset formula (index + margin) |
| 5 | TNTD04509751 | US17133PAA66 | Chuo Mitsui 5.506% perpetual 144A | post-2015-04-15 reset formula |
| 6 | TNTG023603W | XS0238543416 | BTMU €1bn 3.50% sub, due 2015-12-16 | post-2010-12-16 floating margin |
| 7 | TNTG527525U | XS0212517550 | Resona Bank €1bn 3.75% sub, due 2015-04-15 | post-2010-04-15 floating margin |
| 8 | TNTG532803U | XS0229704886 | Resona perpetual sub 4.125% (call 2012-09-27) | post-call formula; confirm fixed-leg dates |
| 9 | TNTG532805U | XS0229705008 | Resona perpetual sub, sister tranche | ALL terms (tranche type unresolved) |
| 10 | TNTG614042U | XS0244642889 | Shinsei €1bn LT2 10NC5 (144A) | post-2011-02-23 floating margin (structure fully known) |
| 11 | TNTG614044U | XS0244642616 | Shinsei €1bn LT2 10NC5 (RegS) | same margin |

(Minor: Liberty Mutual US53079EAN40 payment freq/day-count; Bear US073928X243 day count — both
144A/prospectus-supplement details, immaterial next to the confirmed economics. Standing non-ISIN
gaps unchanged: GBP par curve; pass-through data — Mario already sourcing on Bloomberg.)
