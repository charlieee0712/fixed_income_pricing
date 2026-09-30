# Mortgage pools: 505 priced — and a possible way out of buying deal data

**2026-09-30 · valuation date 2009-03-31 · control date 2009-06-10**

**Who should read what.** Sections 1–5 are the finance answer and assume no mortgage
vocabulary — every term is defined in the clause where it first appears. **Section 6 is
the engineering section** and can be skipped by anyone who does not want it. Azure is
**not** in this report; it has its own note (`azure_service_2026-09-30.md`), because it
answers a different question and is for a different half of the room.

---

## 1. The short version

The mortgage data you sent came back complete, and we built the pricer around it. **505 of
the 882 mortgage securities are now priced**, with a spread, a duration and an average life
for each.

But the more important result is about the **other 377**, and it is not what we expected in
July.

> **A third of the whole portfolio — 756 securities — are slices of structured deals, and
> a slice cannot be priced from its own description. Until this week the only route we
> could see was buying the deal models. There may be a cheaper one, and the request to
> test it is already with Liping.**

That is the decision in this report. Everything else is how we got there.

---

## 2. What we can price now, and what the numbers say

A **mortgage pass-through pool** is the simple case: a few thousand household mortgages,
bundled, with every dollar of interest and principal passed straight through to the holder
in proportion. No priority, no tranches. If you know the pool's coupon, its remaining term
and how fast borrowers repay, you know the cash flows.

**490 of the 882 are pools like that, and 478 of them price.** A further **27** are
**TBAs** — a forward contract to receive a pool that has not been delivered yet, quoted by
coupon and settlement month rather than by a specific pool — which we price as forwards on
their cohort. **505 in total.**

### 2.1 The one number we cannot observe, and what we did about it

Everything about a mortgage turns on **prepayment**: the borrower's right to repay early,
usually by refinancing. It is measured as **CPR** — the annual percentage of the remaining
balance that repays ahead of schedule.

⚠️ **We do not have the 2009 prepayment speeds.** The Bloomberg pull was taken this year, so
its speeds describe today's housing market, not March 2009's. Rather than pick a number and
present one answer, **we price each pool across a grid and report the trade-off:**

| assumed prepayment speed | median spread | 10th pct | 90th pct |
|---|---:|---:|---:|
| 15% CPR | **264.9 bp** | 182.4 | 326.1 |
| 25% CPR | **250.3 bp** | 170.0 | 297.6 |
| 35% CPR | **219.8 bp** | 147.6 | 267.4 |

*Source: `outputs/pool_risk_2009-03-31.csv`, all 505 securities.*

**Read it as: the spread is around 220–265 bp, and the prepayment assumption moves it by
about 25 bp for every 10 points of CPR.** That band is the honest width of what we know
today, and Liping's pull is what collapses it to one column.

⚠️ **One number is deliberately left in and deliberately not used.** If we force the credit
spread to zero — defensible in principle, since these are government-guaranteed — the
prepayment speed that would explain the observed prices comes out at a **median 66% CPR**,
and for 48 securities no speed explains the price at all. **66% is not a real prepayment
rate.** It is the calculation telling us the market was demanding a real spread on
government paper in March 2009, which is exactly what one would expect that month. We keep
it in the output as evidence, not as an input.

### 2.2 The model reproduces something it was never told

**Moneyness** is how far a pool's own mortgage rate sits above the rate a borrower could
refinance into today — the higher it is, the more reason to prepay. These pools sit a
**median 1.53 percentage points in the money**.

Sorting the 505 by moneyness and taking the median spread in each band:

| moneyness (pool rate − market rate) | securities | median spread |
|---|---:|---:|
| below +0.5pp | 66 | **173.4 bp** |
| +0.5 to +1.5pp | 176 | **217.2 bp** |
| +1.5 to +2.5pp | 190 | **273.8 bp** |
| above +2.5pp | 73 | **295.8 bp** |

⭐ **The spread rises monotonically with moneyness, across 505 securities, and nothing in
the model was told to do that.** This is the well-documented shape of mortgage spreads
against refinancing incentive — the market charges more for the bonds whose borrowers are
most likely to leave. Getting it out of an engine that only knows cash flows and a discount
curve is the strongest single piece of evidence that the pricing is behaving.

### 2.3 A second check, where the answer flips sign correctly

Almost all these pools trade **above par** (median price 104.63) — they pay more than
current mortgage rates, so they are worth more than face value. **Nine trade below par.**

Calibrating to an observed price reverses the intuition, and it is worth stating slowly:
for a pool trading above par, faster prepayment destroys value (the extra coupon stops),
so the model price falls — and to still reach the same observed price, the spread must come
**down**. For a pool below par, faster prepayment *creates* value, and the spread must go
**up**.

| | securities | spread change per +10pp of CPR |
|---|---:|---:|
| above par | 496 | **−25.6 bp** |
| below par | 9 | **+32.2 bp** |

⭐ **Both signs are right, and the split is 496 against 9** — the nine are the whole
counter-example, and the model finds them.

### 2.4 Risk metrics, and one honest disagreement

Median **weighted average life 3.25 years**, median **spread duration 2.80 years** — how
much the price moves for a change in spread.

⚠️ Against the custodian's own duration the median gap is **0.756 years, and 102 of 478
differ by more than 1.5 years.** That is not a reconciliation failure so much as two
different quantities: ours is measured at a *fixed* prepayment assumption, the custodian's
appears to allow the prepayment rate to respond to rates. We report both columns rather
than pick. **It is another reason the 2009 speeds matter.**

---

## 3. The 377 we do not price, named individually

Nothing is silently dropped. Every one of the 882 appears in the output or in a companion
file with a reason.

| | count | why |
|---|---:|---|
| **priced** | **505** | pools and TBAs |
| REMIC / CMO tranches | 192 | a slice of a structured deal — see §4 |
| interest-only strips | 76 | receives interest and **no principal** |
| principal-only strips | 76 | receives principal and **no interest** |
| description matches no known pattern | 18 | we cannot tell what it is |
| adjustable-rate pools | 13 | the rate resets, and the rate we hold is this year's |
| TBAs with no settlement month stated | 2 | a gap in the description text |

**505 + 344 + 33 = 882.**

⚠️ **The 18 "no known pattern" are a real gap, not a rounding line.** Our classifier reads
the custodian's description text; for these it recognises nothing, so we decline rather
than guess. Guessing here would produce a confident price for a security whose structure we
had not identified, which is the worst available outcome.

---

## 4. The third of the book that needs deal data

An **IO strip**, a **PO strip**, a **REMIC** and a **CMO** are all the same idea: a pool's
cash flows are cut into pieces and handed to different investors under a set of priority
rules — the **waterfall** — written for that one deal. Which piece gets paid, in what
order, under what conditions, is specific to that deal and is in no field-level data feed.

**Counting the same structure across every securitised class:**

| class | securities | slices of a deal |
|---|---:|---:|
| Government MBS | 882 | 344 |
| Non-Government CMOs | 264 | 264 |
| Commercial Mortgage-Backed | 69 | 69 |
| Asset-Backed Securities | 79 | 79 |
| **total** | | **756 — 33% of the 2,260-security portfolio** |

⚠️ **And they are not 756 similar problems.** In Government MBS alone the 344 sit in **170
different deals, and 144 of those deals contribute exactly one slice to your portfolio.**
Running a waterfall for one slice requires the whole deal — every other tranche, including
the ones you do not own. The requirement is roughly **170 complete deal models**, not 344
security records.

⚠️ **The obvious shortcuts do not work.** We checked two. The class letter in the
description is a per-deal convention, not a standard: of the 54 whose letter starts with
`P`, **29 are principal-only strips rather than the PAC tranches the letter suggests**. And
the custodian's own duration ranges from **−102 to +57 years** on these (against a
well-behaved 0.9–4.0 on the pools) — those extremes are *correct*, an interest-only strip
really does gain value when rates rise, which is precisely why treating these as pools
would be a category error rather than an approximation.

### 4.1 ⭐ The possible way out

The plan since July has been that this needs a deal-structure purchase — Intex, or
Bloomberg's CMO analytics. **We think we were asking for the wrong thing.**

> A waterfall's only job is to decide how much principal each slice receives each month.
> **The factor file records that decision.**

A **factor** is the published monthly number saying how much of a security's original
balance is still outstanding. From two consecutive factors:

```
principal paid this month = original size × (last month's factor − this month's factor)
interest  paid this month = original size × last month's factor × coupon ÷ 12
```

⭐ **That is the complete cash flow, and it requires no knowledge of the deal's rules at
all.** It also works for every structure without special cases: a principal-only strip has
no interest term, an interest-only strip has no principal term, and an accrual tranche —
which adds its interest to its own balance instead of paying it — falls out automatically,
because the two terms become equal and opposite and the net cash flow is exactly zero,
which is what such a tranche does.

⭐⭐ **And because the valuation date is seventeen years ago, most of that history has
already happened.** Of the 344: **89 have paid off entirely**, so their cash flow is
complete with no assumption of any kind; **251 are still outstanding** with a median 6.7
years left against the 17 years already observed; 4 we cannot yet classify. We already hold
the starting factor for **341 of the 344**.

**This is the cheaper request, not just the different one.** A factor is a published
monthly fact with a date attached — ordinary historical data. A cash flow *projection*, by
contrast, is computed from today's collateral and cannot be run backwards to 2009.

⚠️ **The honest limit, and it must travel with every number this produces.** Using what
actually happened is hindsight. It gives the return the holder really earned, not the
spread the market demanded in March 2009. For **risk** measures — duration, sensitivity —
a cash flow schedule is a cash flow schedule and the numbers stand on the same footing as
the pools' fixed-CPR figures. For *"what was this worth to the market that morning"*, the
deal structure is still required.

⭐ **The test is built in.** The request includes **20 pools we already price**, so the
method is checked against numbers we trust *before* it is pointed at a single tranche.

### 4.2 What this means for the purchase decision

**It does not remove the question; it adds a branch that costs nothing to test.** The
request is with Liping — 376 securities, one Bloomberg call each. If the factor history
comes back, we will know within days whether these 756 securities can be valued without
buying deal models. If it does not, the purchase question returns exactly as it stood, and
we will have paid a few hours to find out.

---

## 5. How we know nothing else moved

This round added a mortgage pricer and touched nothing else. To show that rather than
assert it: **all four existing drivers were re-run and every previously published file is
byte-for-byte identical** — the corporate book, the government and sovereign book, the
agency/guaranteed/linker book, and the callable book. **656 automated checks pass.**

---

## 6. Engineering section

*Skippable. Architecture, where the code lives, and how to run it.*

### 6.1 What was built

The mortgage engine moved onto the same template as everything else —
`core/pricing/prepayment.py` for the mathematics, `assets/securitized/` for the
product-level functions with their inputs listed one per line, exactly as the corporate and
government layers are arranged. The old path remains as a thin forwarding module so nothing
that imported it had to change; the moved code is asserted byte-identical below its
docstring.

New: `assets/securitized/pool.py` (per-metric functions: price, implied CPR, implied
spread, duration, DV01, convexity, average life, widening, tightening),
`assets/securitized/tba.py` (forward settlement), and the driver `scripts/pool_risk.py`.

### 6.2 Three decisions worth recording

**The primary calibration is the prepayment rate, not the spread.** One observed price
identifies one unknown. For government-guaranteed paper the credit spread is defensibly
near zero, so solving for CPR is the better use of the single equation — and when the 2009
speeds arrive, the two become a cross-check on each other rather than alternatives.

**An implied CPR is refused when it carries no information.** If the price does not move
across the entire attainable prepayment range by more than the precision the price is
quoted to, the answer is determined by rounding rather than by prepayment. The root may be
perfectly well defined and still mean nothing; the function declines rather than return it.

**A TBA settles on a stated future date, and the year is not in the description.** A
contract that says "settles April" priced at the March valuation date is a one-month
forward; the same contract at the June control date is *already delivered*, not a
fourteen-month forward. Running both dates is what surfaced that, and it is why we run
both.

### 6.3 Running it

```
PYTHONPATH=src python scripts/pool_risk.py          # 2009-03-31
FIP_VAL_DATE=2009-06-10 PYTHONPATH=src python scripts/pool_risk.py
```

Outputs `outputs/pool_risk_<date>.csv` and a companion `pool_disposition_<date>.csv`
carrying one row per security in the class, so the two files together always account for
all 882.
