# Fixed-Income Pricing Module — v3 Addendum (2026-07-20)

*Flagged-bond term resolution by ISIN, the fixed-then-float engine, and the updated data-request list.
Supplements — does not replace — `v3_report_coverage` (2026-07-18); where numbers differ, this
addendum is current.*

---

## 1. What happened since v3

Per our 2026-07-20 call: pass-throughs (16) wait for your Bloomberg data, amortizing + N/A (5) are
permanently excluded, and we took the ⚠️-flagged bonds to public sources by ISIN/CUSIP. That lookup
and one new engine both landed the same day:

- **All 35 flagged / data-gap bonds researched** in primary documents (SEC EDGAR full-text by CUSIP,
  prospectuses & offering circulars, issuer 20-F / annual reports): **22 fully resolved at high
  confidence, 10 partial, 3 with no public documentation** (exempt-market paper). Every recovered
  term carries a source link — per-bond evidence in `docs/isin_lookup_2026-07-20.md`.
- **A fixed-then-float engine** now prices the fixed-to-floating hybrids properly (Section 4).
- Test suite **80 → 103** (all green); output universe now **559 bonds = 548 priced end-to-end + 11
  flagged** at 2009-06-10 (**564 = 553 + 11** at the 2009-03-31 baseline).

## 2. The three v3 "alarms" — two resolved, one confirmed

v3 highlighted that the model alarms instead of emitting plausible-but-wrong numbers. The lookup
closed the loop, in each case in the direction the alarm pointed:

1. **Par-call refuted (TNTD03203204, Sempra 8.9% 2013)** — the offering documents (424B2, FWP,
   Officers' Certificate) show a **continuous make-whole call only (Treasury + 50 bp), no par call**;
   the custodian's "call date" is the bond's first coupon date. Re-routed off the callable lattice to
   straight pricing: **509 bp** implied OAS, consistent with its straight-OAS before (507 bp). The
   BT 108.69 conflict is fully explained.
2. **"Zero is actually structured" (TNTD03037132)** — sharper than that: **it is not a zero at all**.
   The custodian coupon field is a data error; the bond is the **Comcast 6.95% notes due 2037**
   (CUSIP-verified in Comcast's own filings). Re-priced on the real coupon: **+431 bp** (the −486 bp
   was the artifact of the wrong 0% input).
3. **Price-to-call absurdity (TNTG533596W)** — confirmed and now systematized. The bond is the
   UniCredito Italiano Capital Trust III €750m perpetual (full offering circular recovered): fixed
   4.028% to 2015-10-27, then 3M EURIBOR + 176 bp. On the new hybrid engine the main column is
   **979 bp**; price-to-call (1,878 bp) stays a reference column — the market priced extension,
   exactly as the alarm said.

## 3. Further corrections established by the lookup

| v3 stated | Resolved (all primary-source) |
|---|---|
| Step-up (Aquila) — schedule unavailable, BT-mark | Rating-linked steps had **reversed to the 11.875% base by 3/31/09** (Great Plains acquisition); priced vanilla, 864 bp |
| 18 FRNs priced at spread = 0 | Four "(VAR)"-tagged names are **plain fixed** (TI 7.25% '12, TI 7.75% '33, Anglian 5.375% '09, RBS 6% '13) and two are **rating-step** with documented coupon paths (BT '10: 8.625% → 9.125% from Jun-09; Sogerim '11: 7.50%) — all six re-priced on real coupons (sanity: TI '12 at 381 bp vs Sogerim at 398 bp, same guarantor). Four true FRNs now price with their **documented margins** (Bear L+40, PNC L+14, MS L+45, Independence L+182; Bear/PNC/MS corrected to quarterly) |
| AmEx & GE among the floaters | Both are **fixed-to-float hybrids** (6.80% to 2016 / 6.375% to 2017) — as is every such bond in the book: **all hybrids were still in their FIXED leg at 3/31/09** (switches 2009-10 … 2037) |
| Shinsei pair — "no maturity (perpetual?)" | **Dated 2016-02-23**, 3.75% to the 2011-02-23 call (issuer disclosures); only the post-call margin remains open |
| Universe: canonical 522, 6 callable, 46 make-whole | Canonical **523** (528 at 3-31), callable bucket **5**, make-whole **47** — the Sempra re-route via a documented make-whole override table |

## 4. New engine: fixed-then-float hybrids

Fixed coupons to the switch date on the vanilla engine's exact conventions, then curve-implied
forwards + the bond's documented margin on the FRN engine's exact conventions; one curve + one
implied OAS discounts both legs, calibrated to BT; duration bumps the curve (the floating leg
reprojects). Validated by construction and by test: the degenerate limits reproduce the two proven
engines bit-for-bit, and with margin = 0 the floating leg telescopes exactly to par at the switch on
any curve — the hybrid then equals the fixed-to-switch bullet, which is also the price-to-call
reference bond.

**Priced on it (10):** Allstate 789 bp · GE 967 · Lincoln 2,616 (BT 23) · AmEx 1,069 · Liberty 1,724
· Chubb 806 · SMBC 415 (switches Oct-09 → eff. duration 0.4) · BofA 1,058 · BNP 1,209 (perpetual) ·
UniCredito 979 (perpetual). Price-to-call is reported alongside as a reference; on deep discounts it
blows out vs the hybrid OAS (e.g. SMBC 1,869 vs 415) — extension priced, per the v3 alarm logic.
Durations sit far below same-maturity fixed bonds and are bounded by the switch time
(`next_switch_t` is output per bond). Hybrid OAS is **kept out of the by-rating medians**
(junior-subordinated / Tier-1 capital spreads).

**Deliberately not half-modelled (8):** bonds whose structure is documented but whose post-switch
margin is not public are carried at BT with route `hybrid-margin-unavailable`. Each one re-prices
automatically the moment its margin lands in `data/hybrid_switch_terms.csv` — a one-cell fill, no
code change. (This replaces the v3 coupon-continuation column for the reset hybrids.)

## 5. Updated coverage (2009-06-10 basis, as in v3)

| Class | n | Status now |
|---|---|---|
| F — plain fixed | 617 | ✅ 522 priced (475 vanilla + 47 make-whole) + 5 callable bucket (3 on the lattice) |
| Floating / Fixed→Floating | 27 | ✅ 7 FRN (4 with real margins) + 5 vanilla-schedule + 8 hybrid · ⚠️ 5 margin-gap + 1 GBP-curve + 1 defaulted |
| Fixed-to-reset | 6 | ✅ 2 hybrid (BNP, UniCredito) + 1 vanilla-schedule (TI '33) · ⚠️ 3 margin/terms-gap |
| Stepped / Step-up / Zero | 4 | ✅ all priced (incl. Aquila 11.875%; "zero" = the Comcast correction) |
| Defaulted | 1 | ✅ recovery mark |
| Pass-through / amortizing / N/A | 21 | ⏳ pass-through awaits your Bloomberg data · ❌ amortizing + N/A excluded (permanent) |
| **Output** | | **559 = 548 priced + 11 flagged** (3-31 baseline: 564 = 553 + 11) |

## 6. Outstanding data — the one-pull Bloomberg list

**A. Post-switch margin only** (structure and dates confirmed; one number each):
US76117JAB44 (Resona 5.85% perp — after 4/15/16) · US17133PAA66 (Chuo Mitsui 5.506% perp — after
4/15/15) · XS0238543416 (BTMU 3.50% '15 — after 12/16/10) · XS0212517550 (Resona 3.75% '15 — after
4/15/10) · XS0229704886 (Resona 4.125% perp — after 9/27/12, plus fixed-leg dates) · XS0229705008
(Resona perp sister tranche — full terms) · XS0244642889 / XS0244642616 (Shinsei 3.75% '16 — after
2/23/11).

**B. No public documentation at all** (need index + margin + frequency):
US61532RAA77 (Monumental Global Funding II 2005-C, '10) · US61532XAB29 (Monumental III, '14) ·
US634902LH11 (National City bank note, '10 — its 3/31/09 coupon of 1.2425% is a useful cross-check).

**C. Standing:** the pass-through data (16) · a usable GBP par curve (ours has a non-arbitrage-free
3y node; it blocks the France Télécom 7.5% '11 GBP whose coupon path is already confirmed).

---

*Code and evidence: commits `8a38bb0` … `1c092ea`; per-bond sources in
`docs/isin_lookup_2026-07-20.md`; new data tables `data/coupon_schedules.csv`,
`data/frn_spreads.csv`, `data/make_whole_overrides.csv`, `data/hybrid_switch_terms.csv`;
engine `src/pricing/hybrid.py`; 103 tests green.*
