# The mortgage book without the deal models — 858 of 882 priced

**Ryse / URS fixed income · 2026-10-14 · valuation date 2009-03-31**

---

## 1. The short version

Two weeks ago this report ended on a question: *if the factor history comes back, we will know
within days whether these 756 securities can be valued without buying deal models.*

**It came back for the 344 of those that sit in the government mortgage book, and the answer
is yes.** The other 412 are the category still waiting for the same data (§6).

* Of the 882 government mortgage securities, **505 priced a fortnight ago and 858 price now**
  — 784 of them with a spread and a risk number, and 74 interest-only strips with a price but
  no risk number, for the reason in §4.1.
* Of the **377** we listed then as unpriceable — each one named — **353 now price.** The
  remaining **24** are still named, and their reasons are in §4.4.
* **341 of the 344 slices of structured deals are among them** — the holdings the last report
  said would need the deal models themselves.
* It works across **five different kinds of security** — whole pools, slices of a deal,
  principal-only strips, interest-only strips and forward contracts — with **one** method and
  no deal rules of any kind.

⚠️ **One thing we did differently from the call, and it should not be buried.** You said to
treat these as bullet bonds first — all the principal returning on the legal maturity date. We
amortised them instead. On the securities whose repayment history we hold, the legal maturity
is a median of **24 years** away while the principal actually came back in a median of **3.2**
— security by security, a median of **6.4 times** sooner. Taken as a bullet, the typical
mortgage holding would have carried roughly **twenty extra years** of duration.

⭐ **Your own custodian says the same thing without being asked:** its effective duration
across the whole securitised book — present on 1,290 of the 1,294 holdings — has a median of
**2.0 years**, against a median legal life of **24.8**. Two independent sources, sharing no
inputs, agree the money comes back early.

⭐ And your own Tier 1 slide permits the choice: it asks for cash flows that do not respond to
prepayment or to rates, and a *recorded* repayment history is exactly that — it is history, so
it responds to nothing. The amortising treatment costs nothing and is the more realistic
effective-life representation your Tier 2 slide already lists.

⭐ **And outside the mortgage book**, the coupon formulas you sent on Tuesday let **four
corporate bonds price that have been held at the custodian's mark since July**, and confirmed
eight margins we had found ourselves, to the basis point (§5.2).

**What is still missing** is one category — the 412 non-government CMOs, commercial
mortgage-backeds and asset-backeds, which have no repayment history at all. The same method
will work on them; it needs the same data (§6).

---

## 2. How it works

Picture the pool as a **bucket** that fills with money each month as a thousand borrowers make
their payments. What a holding actually is comes in two shapes:

* **a percentage of the bucket.** Whatever goes in, you get your share of it.
* **one of a row of glasses the bucket is poured into, in a fixed order.** The first glass
  fills before the second gets a drop. ⚠️ If you own the third glass, knowing how much went
  into the bucket tells you nothing at all until you also know the pouring order and the size
  of the glasses ahead of you.

⭐ **That pouring rulebook is what deal models are sold for** — and it is why two thirds of
this book looked unpriceable in July.

The way out, as last report set it out, is that somebody already records what ended up in each
glass. The **factor** is the share of a security's *own* original balance still outstanding —
so for a glass, it is that glass's level, after the pouring has happened. Two consecutive
factors give the month's cash flow:

* **principal paid** = original size × (last month's factor − this month's factor)
* **interest paid** = original size × last month's factor × rate ÷ 12

### It works, and here it is working

Take `31402CZR6`, a Fannie Mae pool at 4.5% maturing 2019, which you hold at 103.57. At the
valuation date its factor is **0.44041654** — 44% of the original loans are still outstanding.
The first six months:

```
month   factor        principal returned      interest paid
                      per 100 of original     per 100 of original
 1      0.42939682           1.101972              0.165156
 2      0.41997097           0.942585              0.161024
 3      0.41186327           0.810770              0.157489
 4      0.40355866           0.830461              0.154449
 5      0.39635314           0.720552              0.151334
 6      0.38777872           0.857442              0.148632
```

The first line is `100 × (0.44041654 − 0.42939682) = 1.101972` of principal and
`100 × 0.44041654 × 4.5% ÷ 12 = 0.165156` of interest. ⚠️ The interest uses *last* month's
factor, because you earn on the balance that was outstanding, not the one left after the
payment.

⭐ **And the check that makes it trustworthy:** adding up the principal across the whole
recorded history gives **44.041654**, against a starting factor of 0.44041654 — the same number.
Every dollar of original face is accounted for and none is invented. Across all 374 securities
the worst discrepancy is **one part in a hundred trillion**.

### One method, five shapes of security

This is the part that matters for the purchase decision. **The same two lines above handle all
of these, with no special case for any of them:**

| the holding | why nothing special is needed |
|---|---|
| a whole pool | the factor is the pool's own balance |
| **a slice of a deal** — 191 of them | the factor is *that slice's* balance, so the pouring has already happened before we see the number |
| **principal only** — 76 | there is no interest line. Its rate is literally 0.000% |
| **interest only** — 74 | there is no principal line; interest is earned on a shrinking amount |
| a slice that takes its interest as more debt rather than in cash | the principal line comes out negative and cancels the interest exactly — which is what such a slice pays that month: nothing |

⭐ **We are not reproducing the pouring rules. We are reading the glass after the pouring has
finished.** That is the whole of it, and it is why no deal model is needed.

---

## 3. What came out, and how we checked it before trusting it

**858 of the 882 now carry a price, and 784 of those a spread and a risk number** — the 74
interest-only strips are the difference, and §4.1 says why. There are two ways to know
how much money comes back each month, and the report says on every row which one was used:

* **predict it** — assume a rate at which borrowers repay early, then work out the schedule.
  **458 securities.** ⚠️ This only works for *a percentage of the bucket*, and indeed all 458
  are exactly that. These are the pools already priced in September; their history was never
  requested, because they did not need it.
* **read the record** — the factor method above. **373 securities.** ⭐ **341 of these are
  glasses** — 341 of the 344 in the whole book — where prediction cannot work however good the
  assumptions, because the pouring rules decide the answer and we do not have them. Reading the
  glass sidesteps the rules completely. The other 32 are ordinary pools that happen to have a
  history, 20 of them deliberately (below).
* and **27 forward contracts**, priced as forwards (§4.2).

⭐ **Twenty securities were put deliberately in both groups** — ordinary pools we already priced
— so the new method could be checked against numbers we already trusted before it was pointed
at a single glass.

### The two checks, and they are what makes the number believable

**The two routes agree.** Over two different populations and two entirely different ways of
producing a cash flow, the spread comes out at a median **261.3 basis points** from the recorded
history (223 securities) against **250.9** from the modelled schedule (458). Ten basis points
apart.

**And the risk numbers agree with yours.** On the securities valued from their recorded history,
our effective duration has a median of **2.62 years** against the custodian's own **2.45** —
0.17 years apart, from two sources that share no inputs.

⚠️ For the twenty securities in both groups, the comparison is closer still, and six of them
were excluded from it and said so: they had prepaid at 57–74% a year, outside the range the
modelled schedule can represent, so the "model" figure for those six was just the edge of the
range wearing a different label.

---

## 4. Where Tier 1 stops — each one named, and what closes it

### 4.1 Interest-only strips: a price, and no risk number

An interest-only strip receives no principal at all — it earns interest on a balance it will
never be paid. So its rate sensitivity is almost entirely **prepayment response**: when rates
rise, refinancing slows, that balance survives longer, *more* interest arrives, and the
security is worth **more**. Fixed cash flows cannot express that. The result is not noise,
it is the wrong sign: all **74** come out with a positive duration while **49** of your
custodian's durations for the same securities are negative.

⭐ **So they ship with a price and market value — exact, because they are matched to the
custodian's own mark — and with the duration withheld.** Of the 74, exactly **0** carry a
published duration. Your custodian's figure sits in its own column beside them as evidence; we
do not put their number in our column, because a column that sometimes holds one and sometimes
the other is worse than a blank.

⭐ **A sentence for your "what Phase 1 does not capture" slide, if it helps:** *an
interest-only strip's rate sensitivity is almost entirely prepayment response, which fixed cash
flows cannot express, so Phase 1 publishes its price and withholds its duration.*

### 4.2 Forward contracts: two different sensitivities, not one

Twenty-seven holdings are agreements to buy an unspecified pool on a date weeks after the
valuation date. Everywhere else in this book a move in the base rate and a move in the spread
are the same arithmetic — across the **757** other securities that carry both numbers they
differ on **none**. On a forward they differ on **all 27**, by exactly the settlement period, and the
reason is plain: **a rate move changes both what the pool is worth and what it costs to finance
it until settlement; a spread move changes only what it is worth.**

⚠️ So on those 27 rows the two are not interchangeable and are reported separately. Their
duration also runs longer than your custodian's — median **2.85 years** against **1.82**, 5 of
the 27 more than 1.5 years apart. That gap is the prepayment option Tier 1 does not model, so
both numbers are published side by side rather than one withheld.

### 4.3 The 132 securities whose coupon moves

Your coupon file (§5.1) told us something the holdings file cannot: whether each security's
coupon is fixed. **192 of the 882 are not fixed-rate**, and **132 of those carry a published
duration**.

⭐ **The valuations are unaffected** — the coupon level we use is the custodian's own at the
valuation date. What a fixed-coupon duration assumes is not the level but that the level
*stays*. Those 132 now say so on the row. Where we can see the principal repaying month by
month, only the interest moves with the coupon — a median of a sixth of the value — and even
taking the worst tenth of the book on both the size of that interest and the length of its
life, the error is bounded at **1.8 years**, against the twenty that a bullet treatment would
have cost. The typical case is under half a year.
⚠️ For 61 of the 132 we have no recorded principal either, so that bound does not apply to them
and each of those rows says so.

### 4.4 The 24 that still do not price

| reason | n |
|---|---:|
| neither a recorded repayment history nor usable pool terms | 19 |
| the balance is already zero at the valuation date — nothing left to pay | 2 |
| the forward's description does not state a settlement month | 2 |
| the recorded history produces no net cash at all | 1 |

⚠️ None of these is a shortfall against the plan; three of them could only be discovered by
reading the history, and the other 21 are named data gaps rather than failures.

---

## 5. What the coupon files bought — and the one thing they cannot do

### 5.1 The bit the holdings file cannot carry

The custodian reports each security's coupon *rate*. It never says whether that rate **moves**,
and that single fact decides whether a duration is near zero or a full remaining life. Your
file answers it for all **1,333** securitised and agency holdings.

⭐ It also replaced guesswork rather than refining it: we had been inferring which coupons move
from the security descriptions, and scored against your answer that inference was only **40%**
right — a private-label deal name simply does not say.

### 5.2 Four corporate bonds that had been stuck since July

The formulas include the corporate book, and four holdings that have sat at the custodian's
mark since July — because no public source states what their coupon becomes after the call
date — now price:

| | price | implied spread |
|---|---:|---:|
| Chuo Mitsui perpetual 5.506% | 42.0 | **1,102.5 bp** |
| Resona perpetual 5.85% | 51.0 | **919.6 bp** |
| Resona euro perpetual 4.125% | 40.5 | **1,100.7 bp** |
| …and its sister tranche | 39.5 | **1,132.4 bp** |

About where distressed Japanese bank capital belonged in March 2009. ⭐ One of the four we had
recorded as "all terms unknown"; it came back identical to its sister tranche, which also
confirms the two are one issue in two wrappers. Eight further margins we had found ourselves
from prospectuses agree with your file **to the basis point**, with the same switch dates.

**Four others are still at your mark, and there your rule and our treatment differ.** You
said that where a coupon moves but no formula exists, it should be treated as fixed, since
there is no data. In the mortgage book that is exactly what we do, on all 192 holdings whose
coupon moves. These four we have held back instead — BTMU, a Resona euro issue and the two
Shinsei tranches, all four present in your file with the formula field simply empty. Each
switches to a floating coupon on a date we already know, between one and two years after the
valuation date, with about five years to run after that, so a fixed treatment would assert a
coupon the bond does not pay for roughly three quarters of its remaining life.

⭐ **We priced them your way in any case, because a refusal is only worth as much as the
number it refuses:** **137 bp** for BTMU at 93.77, **713** for the Resona euro issue at
70.53, **1,133** and **1,315** for the two Shinsei tranches at 52.00 and 46.76. Those are
sensible numbers — they sit beside the four above, which priced on real margins at 920 to
1,132. ⚠️ But each is an **upper bound**, and knowably so: after the switch these pay a
floating rate, and the euro market at the valuation date implied 2.7% to 5.1% across exactly
that window before any margin at all, against the 3.5–3.75% a fixed treatment holds. Add a
margin of the size your own file shows on comparable issues and the real coupon is nearer 5
to 7%, so fixing it understates the cash flows and widens the spread. **Say the word and
they go in with that caveat on the row; otherwise they wait for a margin, which is one cell
each.**

### 5.3 ⭐⭐ What the formulas cannot do — and what that says about Tier 2

We put the formulas into the valuation code as dated rules, exactly as you described: one bond,
several periods, each with its own start date, index and margin.

⚠️ **For the adjustable-rate pools they still do not produce the right coupon.** Worked out at
31 March 2009 the formula gives a rate **one to three points below** what the custodian reports
— all seventeen we can currently test, every one in the same direction. The reason is the
reset: these pools reset **once a year on their own anniversary**, so in March 2009 one is
carrying a rate set the previous June, when the one-year Treasury stood at **2.36%**, and
another one set in December, when it was **0.37%**. Across those twelve months the one-year
ranged over **2.3 points** — almost exactly the range of the gaps we see. The formula is
right. It cannot tell us which date to apply it on.

⭐ **The conclusion is about Tier 2, not about the formulas.** For the principal leg, the
empirical route turned out to be a *recorded history* rather than a model — that is §2. This
fortnight showed the **coupon leg is the same shape**: what closes it is the realised monthly
coupon, because that single series records what the formula, the index, the reset date and the
rate caps all did, none of which we can reconstruct separately. ⚠️ Until then, the custodian's
observed coupon — the actual rate after caps and resets — remains the better input, and that is
a deliberate choice rather than a gap.

---

## 6. What is still missing

**The 412.** The non-government CMOs, the commercial mortgage-backeds and the asset-backeds
have **no repayment history of any kind**. They are **18.2% of the portfolio by number of
holdings and 4.9% by par value** — the count makes them sound larger than they are, but they
are the last category with nothing behind them. **201 of the 412 (49%) also have a moving
coupon**, so they need both series.

⭐ One obstacle has already gone: 37 of the 412 had no usable identifier in the custodian file
and we expected to have to leave them out. Your mortgage file supplied identifiers for all 37,
so the request covers the full 412.

**Two requests have gone across separately**, kept apart because they are different decisions:
a small one to finish the government book (six index histories, and either the reset dates and
rate caps or the realised coupon for its 192 moving-coupon pools), and a larger one for the 412.

---

## Appendix — the engineering, briefly

**Running it.** `PYTHONPATH=src python scripts/tier1_structured.py` writes
`outputs/tier1_structured_2009-03-31.csv`, 882 rows, alongside a companion file accounting for
every security that did not price. The pool and corporate books have their own commands; all
outputs and their checksums are listed in `docs/release_facts_2026-10-15.md` — the file
numbered `07_release_facts` in the folder you received — which is generated from the
files rather than typed.

**Nothing else moved.** Every other output is unchanged from the 2026-10-08 record except the
corporate book, which gained the four bonds in §5.2 — verified row by row, with the row count,
the column list and every other value identical. The test suite stands at **753**.

**One internal note.** The prepayment speed assumed by the 458 predicted rows was measured as
a *total fall in balance* rather than a *prepayment rate* — the two differ by the contractual
repayment inside every monthly payment. It is right for this population's typical remaining
term and no security's duration moves by the 1.5-year threshold, but it understates the spread
of the 46 shortest pools by about 47 basis points. The proper fix is a speed derived per pool,
which is a prepayment model, which is Tier 2.

**Terminology.** The spread reported throughout is an **implied, bond-equivalent spread**, in
your own words from the methodology deck — not an option-adjusted spread, which would require
modelling the prepayment option explicitly. Nothing in the output is labelled otherwise.
