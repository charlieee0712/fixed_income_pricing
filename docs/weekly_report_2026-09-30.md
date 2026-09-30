# Mortgage pools: 505 priced — and a possible way out of buying deal data

**2026-09-30 · valuation date 2009-03-31 · control date 2009-06-10**

Plain language throughout; every mortgage term is defined where it first appears. There is
a short appendix at the end with the commands, which you can ignore. Azure is **not** in
this report — it has a separate one-page note, because it is a different question.

---

## 1. The short version

The mortgage data you sent came back complete, and we built the pricer around it. **505 of
the 882 mortgage securities are now priced**, each with a spread, a duration and an average
life.

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
in proportion. No priority, no slices. If you know the pool's rate, its remaining term and
how fast borrowers repay, you know the cash flows.

**490 of the 882 are pools like that, and 478 of them price.** A further **27** are
**TBAs** — a forward contract to receive a pool that has not been delivered yet, quoted by
coupon and settlement month rather than by a named pool — which we price as forwards.
**505 in total.**

### 2.1 The one number we cannot observe, and what we did about it

Everything about a mortgage turns on **prepayment**: the borrower's right to repay early,
usually by refinancing. It is measured as **CPR** — the percentage of the remaining balance
that repays ahead of schedule in a year.

⚠️ **We do not have the 2009 prepayment speeds.** The Bloomberg data was pulled this year,
so its speeds describe today's housing market rather than March 2009's. Rather than pick a
number and present one answer as if we knew it, **we priced every pool at three speeds and
report the trade-off:**

| if prepayment is… | median spread | slowest 10% | fastest 10% |
|---|---:|---:|---:|
| 15% a year | **265 bp** | 182 | 326 |
| 25% a year | **250 bp** | 170 | 298 |
| 35% a year | **220 bp** | 148 | 267 |

*From `outputs/pool_risk_2009-03-31.csv`, all 505.*

**Read it as: the spread is somewhere around 220–265 bp, and the prepayment assumption
moves it by roughly 25 bp for every 10 points of speed.** That band is the honest width of
what we know today. Liping's data collapses it to a single column.

⚠️ **One number is deliberately in the output and deliberately not used.** If we assume the
credit spread is zero — arguable, since these carry a government guarantee — then the
prepayment speed that would explain the observed prices comes out at a **median 66% a
year**, and for 48 securities no speed explains the price at all. **66% is not a real
prepayment rate.** It is the arithmetic telling us the market was demanding a genuine
spread even on guaranteed paper in March 2009, which is what one would expect that month.
We keep it as evidence, not as an input.

### 2.2 The model reproduces something nobody told it

**How far a pool's own mortgage rate sits above what a borrower could refinance into
today** is the single best predictor of whether they will refinance. These pools sit a
**median 1.53 percentage points above** the prevailing rate.

Sorting all 505 by that gap and taking the median spread in each band:

| pool rate above market rate by… | securities | median spread |
|---|---:|---:|
| less than 0.5pp | 66 | **173 bp** |
| 0.5 to 1.5pp | 176 | **217 bp** |
| 1.5 to 2.5pp | 190 | **274 bp** |
| more than 2.5pp | 73 | **296 bp** |

⭐ **The spread rises steadily with the refinancing incentive, across all 505, and nothing
in the model was told to make that happen.** This is the shape mortgage spreads are known
to have — the market charges more for the bonds whose borrowers are most likely to leave
early. Getting it out of a model that only knows cash flows and a discount curve is the
strongest single sign that the pricing is behaving sensibly.

### 2.3 A second check, where the answer flips the other way — correctly

Almost all these pools trade **above face value** (median price 104.63): they pay more than
today's mortgage rates, so they are worth more than the balance outstanding. **Nine trade
below.**

Now, this next point reads backwards at first, so it is worth a slow sentence. We are
solving for the spread that makes our valuation *equal the price you are actually marked
at*. For a pool trading above face value, faster prepayment is bad news — the above-market
interest stops sooner — so our valuation falls. But the price we have to match has not
moved. **So the spread has to come down to lift the valuation back up.** For a pool trading
below face value, everything reverses.

| | securities | spread moves per +10 points of prepayment |
|---|---:|---:|
| priced above face value | 496 | **−26 bp** |
| priced below face value | 9 | **+32 bp** |

⭐ **Both directions are right, and the split is 496 against 9** — those nine are the entire
counter-example in the book, and the model finds them.

### 2.4 Risk numbers, and one honest disagreement

Median **average life 3.25 years**. Median **spread duration 2.80 years** — how much the
price moves when the spread moves.

⚠️ Against the custodian's own duration figure, the median gap is **0.76 years, and 102 of
478 differ by more than 1.5 years.** That is less a reconciliation failure than two
different quantities. Ours holds the prepayment speed fixed; theirs appears to let
prepayment respond to rates. We publish both columns side by side rather than choose. **It
is one more reason the 2009 speeds matter.**

---

## 3. The 377 we do not price, each one named

Nothing is quietly dropped. Every one of the 882 appears either in the priced output or in
a companion file with a reason beside it.

| | count | why |
|---|---:|---|
| **priced** | **505** | pools and TBAs |
| slices of structured deals | 192 | see section 4 |
| interest-only strips | 76 | receives the interest and **no principal at all** |
| principal-only strips | 76 | receives the principal and **no interest at all** |
| description matches nothing we recognise | 18 | we cannot tell what it is |
| adjustable-rate pools | 13 | the rate resets, and the rate we hold is this year's |
| TBAs that do not state a settlement month | 2 | a gap in the description text |

**505 + 344 + 33 = 882.**

⚠️ **The 18 we cannot recognise are a real gap, not a rounding line.** We read the
custodian's description text; for these it matches nothing we know, so we decline rather
than guess. Guessing would produce a confident price for a security whose structure we had
not actually identified — the worst of the available outcomes.

---

## 4. The third of the book that needs deal data

Interest-only strips, principal-only strips, REMICs and CMOs are all the same idea: one
pool's cash flows are cut into pieces and handed to different investors under a set of
priority rules written for that one deal. Which piece gets paid, in what order, under what
conditions — all of it is specific to that deal, and none of it is in any data feed we can
subscribe to field by field.

**Counting that same structure across every securitised class:**

| class | securities | slices of a deal |
|---|---:|---:|
| Government MBS | 882 | 344 |
| Non-Government CMOs | 264 | 264 |
| Commercial Mortgage-Backed | 69 | 69 |
| Asset-Backed Securities | 79 | 79 |
| **total** | | **756 — a third of the 2,260-security portfolio** |

⚠️ **And they are not 756 similar problems.** In Government MBS alone, the 344 slices come
from **170 different deals — and 144 of those deals contribute exactly one slice to your
portfolio.** To work out what one slice receives, you need the rules for the *whole* deal,
including every other slice you do not own. So the requirement is roughly **170 complete
deal models**, not 344 security records. That is the shape of the purchase.

⚠️ **The obvious shortcuts do not work, and we checked two rather than assume.** The letter
in a slice's name looks like it should classify it, but the lettering is each deal's own
convention: of the 54 whose letter begins with `P`, **29 turn out to be principal-only
strips** rather than the scheduled-payment slices the letter suggests. And the custodian's
own duration on these ranges from **−102 to +57 years**, against a well-behaved 1 to 4 on
the ordinary pools. Those extremes are *correct* — an interest-only strip really does gain
value when rates rise, because the borrowers stop leaving — which is exactly why treating
these as ordinary pools would be a category error rather than a rough approximation.

### 4.1 ⭐ The possible way out

Since July the plan has been that this needs a deal-structure purchase. **We now think we
were asking for the wrong thing.**

> The only job those deal rules do is decide **how much principal each slice receives each
> month**. And there is a published monthly number that records exactly that decision after
> the fact: the **factor** — the share of a security's original balance still outstanding.

From one month's factor and the next:

- **principal paid** = original size × (last month's factor − this month's factor)
- **interest paid** = original size × last month's factor × rate ÷ 12

⭐ **That is the complete cash flow, and it needs no knowledge of the deal's rules at all.**
It also handles every structure without special treatment: a principal-only strip has no
interest term, an interest-only strip has no principal term, and a slice that rolls its
interest into its own balance instead of paying it works out to exactly zero cash that
month — which is precisely what such a slice does.

⭐⭐ **And because we are valuing as at 2009, most of that history has already happened.**
Of the 344 slices: **89 have paid off completely**, so their cash flow is a matter of
record with no assumption of any kind; **251 are still outstanding**, with a median 6.7
years left against the 17 years we can already observe. We already hold the starting
factor for **341 of the 344**.

**This is the cheaper request, not merely a different one.** A factor is a published
monthly fact with a date on it — ordinary historical data. A *forecast* of future cash
flows, by contrast, is computed from today's loan pool and cannot be run backwards to 2009.

⚠️ **The honest limit, and it must travel with every number this produces.** Using what
actually happened is hindsight: it gives the return the holder really earned, not the
spread the market was demanding in March 2009. For **risk** measures — duration,
sensitivity — a cash flow schedule is a cash flow schedule, and the numbers stand on the
same footing as the pools' figures above. For *"what was this worth to the market that
morning"*, the deal structure is still required.

⭐ **The test is built into the request.** It includes **20 ordinary pools we already
price**, so the method gets checked against numbers we already trust *before* it is pointed
at a single slice.

### 4.2 What this does to the purchase decision

**It does not answer the question; it adds a branch that costs almost nothing to test.**
The request is with Liping — 376 securities, one lookup each. If the factor history comes
back, we will know within days whether these 756 securities can be valued without buying
deal models. If it does not, the purchase question returns exactly as it stood, and we will
have spent a few hours finding out.

---

## 5. Three modelling choices we made, and why

**We solve for the prepayment speed rather than the spread.** One observed price can
identify one unknown, not two. For government-guaranteed paper the credit spread is
defensibly near zero, so spending that single equation on prepayment is the better use of
it — and when the 2009 speeds arrive, the two become a cross-check on each other instead of
alternatives.

**We refuse to report a prepayment speed when it carries no information.** For some pools
the price barely moves across the entire range of possible speeds — less than the precision
the price is even quoted to. The arithmetic still produces an answer, and that answer is
determined by rounding rather than by prepayment. We decline to print it.

**A TBA settles on a stated future month, and the description does not give the year.** A
contract that says "settles April" is a one-month forward at the March valuation date and
an *already-delivered* position at the June control date — not a fourteen-month forward.
Running both dates is what surfaced that, and it is why we run both.

---

## 6. How we know nothing else moved

This round added a mortgage pricer and touched nothing else. To demonstrate that rather
than assert it, all four existing valuation runs were repeated and compared: **not one
number changed in any of them** — the corporate book, the government and sovereign book,
the agency and inflation-linked book, or the callable book. **656 automated checks pass.**

---

## Appendix — running it

```
PYTHONPATH=src python scripts/pool_risk.py          # 2009-03-31
FIP_VAL_DATE=2009-06-10 PYTHONPATH=src python scripts/pool_risk.py
```

Produces `outputs/pool_risk_<date>.csv` and a companion `pool_disposition_<date>.csv` with
one row per security in the class, so the two files together always account for all 882.

The mortgage engine sits in the same structure as the rest of the library — the
mathematics in one layer, the per-product functions with their inputs listed one per line
in another — the arrangement agreed in August and used for the corporate and government
books.
