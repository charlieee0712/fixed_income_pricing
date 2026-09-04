# Government and Municipal/Provincial bonds

**Date:** 2026-09-03 · **Valuation date:** 31 March 2009 (10 June 2009 kept as a control)

**Who should read what.** Sections 1 to 6 are written for everyone and assume no bond-market
vocabulary — every technical term is explained in the sentence where it first appears.
**Section 7 is the engineering section**: architecture, how to run it, and how we prove the
numbers. A finance reader can skip section 7 entirely and miss nothing. An engineer who reads
only section 7 will still want section 4, because two of the three findings there are data
problems, not modelling ones.

---

## 1. What you asked for

You marked two cells `no` in the **K column of the `Summary` sheet**: `K23` against
**Government Bonds** and `K55` against **Municipal/Provincial Bonds**. Those are the only two
annotations on that sheet, and each maps exactly onto one row of the holdings file.

- **Government Bonds** — debt issued by national governments (the United States, Germany,
  Japan, the United Kingdom, Mexico and eleven others). **153 lines → 147 distinct
  securities.**
- **Municipal/Provincial Bonds** — debt issued by a state, province or city rather than a
  national government. **7 lines → 7 securities.**

The line count is higher than the security count because the same bond can be held in more
than one account. We combine those holdings before pricing, so each security is valued once.

**154 securities in total.**

---

## 2. What we did

**147 of the 154 are priced at 31 March 2009**, and 150 at the June control date. Seven are
not priced; each one is named, with the reason, in section 5. Nothing is missing without an
explanation attached to it.

For each priced security we produce:

- an **implied spread** — the extra return the market is demanding over the relevant
  government interest-rate curve. A "curve" here just means the market's interest rate for
  each future date, built from that day's quoted government yields;
- **effective duration** — how much the price moves for a small change in interest rates,
  expressed in years. A duration of 5 means roughly a 5 % price fall if rates rise by one
  percentage point;
- **DV01 and convexity** — the same sensitivity in cash terms, and how that sensitivity itself
  changes as rates move.

Each price is reproduced to within **3 × 10⁻⁸** of the custodian's own recorded price, so the
spread we report is the one that exactly explains the price on the statement, not an
approximation to it.

**A point about what the spread means here, because it is not one thing.** For most of these
securities the issuer *is* the government whose curve we are discounting on — a UK gilt priced
on the UK curve, a Japanese government bond on the Japanese curve. In that case the spread is
not a credit signal at all; it *should* come out near zero, and it serves as a check that the
machinery is correct. For a Mexican bond issued in US dollars, or a Queensland state bond, the
spread is real and informative. Every row in the output says which of the three cases it is,
so the two can never be added together by mistake.

---

## 3. Where this leaves the book

It is worth being precise here, because the `Summary` sheet is a **flat list** of asset
sub-categories: `Corporate Bonds` sits alongside `Government Bonds` and
`Municipal/Provincial Bonds` rather than containing them. Mortgage-backed securities have
always been their own separate category and were never inside the corporate one.

| sub-category | lines | securities | status |
|---|---:|---:|---|
| Corporate Bonds | 811 | 732 | done — 566 in the output at 3-31 |
| Government Bonds | 153 | 147 | **done this week** |
| Government Agencies | 42 | 39 | done |
| Index Linked Government Bonds | 16 | 15 | done |
| Guaranteed Fixed Income | 11 | 9 | done |
| Municipal/Provincial Bonds | 7 | 7 | **done this week** |
| **the six cash-bond classes** | **1,040** | **949** | **complete** |
| Government Mortgage Backed Securities | 888 | 882 | engine built, waiting on data |
| Non-Government Backed C.M.O.s | 265 | 264 | not started |
| Asset Backed Securities | 79 | 79 | not started |
| Commercial Mortgage-Backed | 73 | 69 | not started |
| Derivatives and Other | 21 | 17 | out of scope |
| **Grand Total** | **2,366** | **2,260** | |

So: **all six categories of ordinary cash bonds are now complete — 1,040 of the 2,366 lines.**
What remains is the securitised block, which is a different kind of instrument (pools of
mortgages and loans rather than a single borrower's promise) and is waiting on the Bloomberg
data pull. The engine for it is already written and tested against its interface; it needs the
pool figures, not more code.

One note on the corporate numbers, since three different totals circulate and they are easy to
confuse: the `Corporate Bonds` **tab** carries **676 rows covering 616 distinct securities**
(sixty are listed more than once), the master sheet's corporate sub-category has **811 rows and
732 securities**, and our priced output has **566**. All three are correct; they count
different things.

---

## 4. Three things worth your attention

### 4.1 The euro curve in our data is an average of euro governments, not a swap curve

This one changes what a number *means*, so it matters more than it might sound.

We hold 30 euro-denominated government bonds — German, French, Dutch, Belgian, Irish and
Spanish. There are two defensible ways to price them: on each country's own curve, or on the
single euro curve. We tested both on a German government bond (4.25 %, maturing July 2014):

| priced on | implied spread |
|---|---:|
| the German curve | **+1.34 basis points** |
| the euro curve in our data | **−44.88 basis points** |

A basis point is one hundredth of one percent. Those two numbers look contradictory, and a
reader who saw both without explanation would reasonably conclude something was broken.
Neither is wrong. They answer different questions, and we had to establish which.

We checked what the euro file actually contains. It sits **between the German and Italian
curves at every maturity**, and a weighted average of the six euro-country curves we hold
reproduces it to within **7 basis points on average and 18 at worst**. It is therefore an
**average of euro-area governments** — not, as one might assume, a bank-lending or swap curve.

That makes the −44.88 meaningful: Germany is *expensive relative to the euro-area average*,
which is exactly what one would expect in March 2009, when money was moving into German debt
for safety. It is **not** a spread over bank rates and must not be described as one.

**We price everything on its own currency's curve** — the same rule the original spreadsheet
system used, and the same rule the corporate book already follows. The deciding argument was
practical rather than theoretical: **Ireland has no curve file in our data**, so a
country-by-country rule would have left two Irish bonds on a different basis from the other
twenty-eight, which is precisely the kind of quiet inconsistency that produces a wrong number
nobody notices. The country curves remain available and we use them as a cross-check.

The result reads correctly without being told anything about credit quality:

| | spread vs the euro-area average |
|---|---:|
| Germany (the four richest) | −70, −65, −55, −52 bp |
| Spain | +39 bp |
| Belgium | +40 bp |
| **Ireland** | **+156 and +164 bp** |

That is the March 2009 ordering of euro government credit, produced by the pricing machinery
alone.

### 4.2 One price in the file is quoted per 1,000, not per 100

Bond prices are normally quoted per 100 of face value: a price of 97 means 97 % of what the
bond repays. Six of the 154 holdings do not follow that convention in the custodian file —
their **quantity** column counts *certificates* rather than a currency amount.

We found this by checking the custodian's own internal arithmetic: for 148 securities,
price = market value ÷ quantity × 100 holds exactly. For six it fails, by a factor of exactly
one hundred. Five are Mexican and one is Brazilian.

The Mexican prices (99.455 to 117.793) are already on the normal per-100 basis and need no
change. The Brazilian bond is different: its recorded price is **916.73**, because Brazilian
government bonds are issued in units of 1,000 reais. On the normal basis that is **91.673**.

**Had we used 916.73 the reported spread would have been nonsense** — a number no government
has ever borrowed at. This is worth flagging because **the custodian file itself makes this
mistake**: its own yield figure for that bond is **−23.1 %**, against 6.45 % to 8.41 % for the
five Mexican bonds. So the yield column in the statement is not reliable for that security.

We did not guess our way out of this. The denomination comes from a small, explicit table in
the code, and it is confirmed by the file itself — every Mexican description carries the text
`MXN100` and the Brazilian carries `BRL1000`. An automatic check re-reads those descriptions
and fails if the table and the file ever disagree.

### 4.3 A US Treasury "spread" in this table measures liquidity, not credit

US Treasury bonds carry no credit risk relative to the US government curve, so their spread
should be zero. Ours has a median of about 40 basis points, which needs explaining rather than
excusing.

Three of our holdings mature on **the same day**, 15 February 2019:

| | coupon | spread |
|---|---:|---:|
| the 10-year note issued in February 2009 | 2.750 % | **+3.9 bp** |
| STRIPS (a bond split so each payment trades separately) | 0 % | +38.7 and +41.0 bp |
| an older bond issued decades earlier | 8.875 % | **+42.8 bp** |

Same borrower, same repayment date, same day, 39 basis points apart. No credit explanation is
possible. The government curve we use is built from **newly issued** bonds, and in March 2009
newly issued Treasuries were unusually expensive because investors wanted the most easily
traded security available. Older bonds and STRIPS were correspondingly cheap.

So on US Treasuries this column is a **liquidity measure**: recently issued bonds sit at a
median of 2.7 bp, everything older at 40 to 55. That is a real and historically extreme
feature of that month, not an error — but it means these particular numbers should not be
described as credit spreads.

---

## 5. The seven we did not price

| security | currency | what it is | why not |
|---|---|---|---|
| three Korean government bonds | KRW | ordinary fixed-coupon | our Korean curve file has no row for 31 March; **they price at the June date** |
| Denmark 5 % 2013 | DKK | ordinary fixed-coupon | our Danish curve file has no row for either date |
| Malaysia 3.718 % 2012 | MYR | ordinary fixed-coupon | we hold no Malaysian curve file at all |
| Japan floating-rate bond 2021 | JPY | coupon resets periodically | see below |
| Russian Federation 7.5 % 2030 | USD | see below | see below |

The first five are straightforward: a missing curve. We deliberately do **not** substitute a
neighbouring date or another country's curve, because a plausible-looking wrong number is
worse than a stated gap.

The last two are more interesting, and both are cases where the obvious answer was wrong.

**The Japanese floating-rate bond** looked at first like a bond missing one parameter — the
margin over its reference rate — which would have been a one-cell data request. It is not.
This is a 15-year Japanese government floater whose coupon resets to the **10-year government
bond yield**, and our floating-rate engine is built for bonds that reset to a short-term rate.
The reference itself is what we cannot represent, so supplying the margin would not have made
the answer right. The custodian's own duration figure for it (−0.475) is consistent with that
reading. We are recording it as an engine limitation rather than asking you for data that
would not help.

**The Russian bond** describes itself as `STEP UP` in the holdings file, meaning its coupon
changes on a schedule we do not hold. Separately, the custodian's own duration of **4.08** is
far below the roughly 10 that a straightforward 21-year 7.5 % bond would have, which says the
principal is repaid in instalments rather than all at maturity. We can model neither feature,
and pricing it as an ordinary bond would have produced a confident 21-year risk number that is
simply wrong.

**No new data request is attached to any of this.** All five gaps are written into our
missing-data register and can travel with the mortgage data when it comes back.

---

## 6. How we know the numbers are right

The strongest evidence is that the bonds which *should* price at zero do.

| currency | securities | median spread |
|---|---:|---:|
| Japan | 11 | **0.0 bp** |
| Sweden | 2 | 3.1 bp |
| United Kingdom | 12 | **4.4 bp** |
| Singapore | 2 | 8.0 bp |
| Mexico (local currency) | 5 | 10.3 bp |
| Canada | 1 | 11.4 bp |
| Norway | 2 | 22.6 bp |

A government bond priced on its own government's curve is the same credit as the curve, so a
median of zero is the pipeline confirming itself. This check catches a great deal at once: a
bond routed to the wrong country's curve, a curve file read in the wrong units, or a price on
the wrong scale would all break it, and none of them would show up in a count.

The numbers that are *supposed* to be informative also land where a market participant would
expect for March 2009:

| | spread |
|---|---:|
| Queensland and New South Wales state bonds, over the Australian government curve | 64 – 106 bp |
| Ontario (Canadian province) borrowing in yen, over the Japanese curve | 93 bp |
| Mexico borrowing in US dollars | 341 – 409 bp |
| Brazil borrowing in US dollars | 366 bp |
| Illinois State pension bond | 296 bp |
| a military-housing revenue bond | 546 bp |

We also compare our duration against the custodian's own for all 154. They agree closely — for
the seven municipal bonds, six are within 0.24 years. The single exception is the Ontario yen
bond, where the custodian reports 2.33 years for a bond maturing in 0.82 years, which is not
arithmetically possible; our 0.82 is right, and the row says so rather than quietly disagreeing.

**One callable US Treasury needs its two numbers read together.** "Callable" means the borrower
may repay early. This is a 12.5 % bond from a high-interest-rate era, repayable at face value
from August 2009, and at 2009 interest rates it was certain to be repaid early. Its spread is
**122 bp** allowing for that right and **950 bp** ignoring it, with a duration of 0.39 years
against 4.05. Almost the whole difference is the value of the early-repayment right, not
credit. The output says this in words on the row, so the 950 cannot be quoted on its own.

---

## 7. Engineering section

*A finance reader can stop here.*

**Shape.** No new engine was written. The two classes route through existing components:
the analytical bond pricer, the binomial short-rate tree for the one callable, and the
existing calibration and risk functions. What is new is a loader extension
(`src/dataio/phase2.py`), eight currency-to-curve-file registrations
(`src/curves/zero_curve.py`, 6 → 14), and one driver, `scripts/sovereign_risk.py`.

**Why a separate driver.** The existing `phase2_risk.py` produces one of five output files
that we compare by cryptographic hash after every commit, as the guarantee that a change to
shared code moved no existing number. Adding 154 rows to it would have spent that guarantee.
Instead the shared loader takes an explicit class list defaulting to the original four, so
`phase2_risk.py` and its file are untouched. **All five production files and all four
disposition files regenerate byte-identical to the previous release.**

**Determinism and coverage.** Every one of the 154 securities is either priced or recorded
with a named reason, and that cover is proved over **sets of identifiers**, not counts — a
count check passes even when the wrong security is in the wrong bucket. The result is written
to a dated file per valuation date, so a second run at a different date cannot overwrite the
first.

**Handling of the price convention.** The denomination table is deliberately an explicit
registry rather than a rule inferred from the price, because no threshold separates a 916.73
quoted per 1,000 from one quoted per 100. The conversion is written as `price / (F/100)` so
that when `F` is 100 the divisor is exactly 1.0 and the five Mexican prices pass through
**bit-identically** — asserted with `==` rather than a tolerance. The first version multiplied
and divided by 100 and was not bit-exact; the test caught it.

**Verification.**

```text
python -m pytest -q                                     424 checks, ~45 s
FIP_VAL_DATE=2009-03-31 PYTHONPATH=src python scripts/sovereign_risk.py
PYTHONPATH=src python scripts/release_facts.py          hashes for every output
```

Identical results on Windows and on the Linux deployment host: 424 checks pass on both, and
every text column of the output now matches exactly between them. Numeric agreement is to
5 × 10⁻¹¹ on spreads and 3 × 10⁻¹³ on durations; convexity differs at 2 × 10⁻⁷, which is a
second difference divided by the square of a small bump and is expected floating-point noise
rather than a disagreement.

**One defect the cross-platform comparison caught,** worth recording because it was not a
number. A message on rows where the curve was unavailable was embedding the file path, which
differs between the two operating systems — so the same failure produced two different strings,
and a filesystem path was appearing in a delivered file. The rule now has one owner
(`curve_failure_reason`), used by both drivers; it keeps the file name and drops the directory.

**Test additions.** 390 → 424. The new checks pin the route for each unusual security, the
denomination registry against the descriptions in the file, the units of all eight new curve
files re-read from the raw exports, and the anchor property itself — that a sovereign on its
own curve prices to near zero — which is the end-to-end check that fails if any part of the
routing is wrong.

---

## 8. Open questions for you

1. **The daily-use spreadsheet layout** remains the outstanding design question from the
   previous round, unchanged. The bridge can send every bond type the engine supports; what
   does not exist is the worksheet a person would use day to day, because that layout is yours
   to decide.
2. **Nothing is being requested this week.** The five data gaps in section 5 are recorded and
   can be picked up alongside the mortgage-pool data whenever that returns.
3. **A question of presentation**, not of data: for the government bonds where the spread is a
   validation anchor rather than a credit measure, would you rather see the number reported, or
   suppressed with a note? We currently report it, labelled, on the grounds that a suppressed
   column cannot be checked.

---

**Supporting material in this folder:** `05_sovereign_detail_2026-09-03` carries the full
audit — every population, all seven unpriced securities, the curve-identification evidence and
the reconstruction commands. `07_release_facts_2026-09-03` carries the row count and
cryptographic hash of every output file quoted above, generated from the files themselves.
