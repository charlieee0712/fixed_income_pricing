# The mortgage book, end to end — from an idle engine to 882 published rows

**What this file is.** The *narrative*: how the securitised book got from "an engine with no
data" in July to 882 priced rows in October, what was decided at each fork, and what we got
wrong on the way. It is the document to read first, or to re-read in three months when the
reasons have faded.

⚠️ **What it is NOT, and where that material lives.** It does not re-explain the concepts —
`docs/three_tier_method_explained_2026-10-06.md` already does that, and repeating them here
would halve the information per line in both files. Use that one for *what a thing is* and this
one for *why we did it*:

| for | go to |
|---|---|
| what a factor / WAL / I/O / TBA / bond-equivalent spread **is** | `three_tier_method_explained` §3, §8 (glossary) |
| why DV01 and CS01 split on a forward; why an I/O's duration is negative | same, §3.4, §3.5, §3.8 |
| why the duration is the deliverable and the spread is a plug | same, §3.9 |
| the `BOOK_CPR_PCT` gross-vs-net finding in full | same, §3.10–§3.11 |
| why a **formula is not a coupon** — reset lag, caps, and the test on the 201 | same, §3.13 |
| why Bloomberg's margin differs from ours on 67 securities (LIBOR → Term SOFR) | same, §3.14 |
| what a measured history buys, and why `CPN` is not `MTG_FACTOR` | same, §3.15 |
| why a factor's month label is not always its month — and why no class rule fixes it | same, §3.17 |
| why an observed coupon beats a formula **at the valuation date**, and loses after it | same, §3.18 |
| why the custodian's duration cannot be compared across the two books | same, §3.19 |
| why a floater's duration goes **negative** below par, and what we publish instead | same, §3.20 |
| the decision record behind Mario's three tiers | `client_directive_three_tier_structured_method_2026-10-06.md` |
| the factor validation in full | `bloomberg_return_2026-10-01.md` §7 |
| every open data gap | `missing_data.md`, G1–G7 |
| any count, hash or test number | the newest `release_facts_<date>.md` — it outranks prose, including this file |

---

## 1. The problem, in one page

An ordinary bond pays interest and then returns the whole principal **on one stated day**. You
know the dates; pricing is arithmetic.

A mortgage pool is a slice of a thousand home loans. Every month the borrowers pay interest
**and a little principal**, and on top of that some of them sell the house or refinance and
repay the lot early. So the money comes back **continuously, on a schedule nobody wrote down**,
and by the legal maturity there is usually nothing left. ⭐ **The whole difficulty of valuing
one is knowing when the cash arrives.**

And a *structured* deal is worse: the pool's cash is split between tranches by a "waterfall" —
a set of rules saying who gets paid first, who absorbs losses, who accrues instead of
receiving. Reproducing a tranche's cash flow in principle means reproducing those rules.

**The industry answer is to buy them.** Intex encodes the waterfall of essentially every deal.
Mario's position (2026-10-06): *"very expensive and difficult to get"* — so Tier 3, optional,
"only when the analytical requirement justifies the cost".

⇒ the question this whole arc answers: **can the book be valued without the deal models?**

---

## 2. The arc at a glance

| when | what happened | what changed |
|---|---|---|
| 2026-07-22 | `pricing/mbs.py` built — a static-CPR pool engine on an exact 8-field Bloomberg interface | an engine, no data |
| 2026-07-30 | the 8 fields × 882 CUSIPs requested (Liping) | — |
| 2026-09-25 | the pull arrives, 882/882 | 505 pools priceable |
| **2026-10-01** | ⭐⭐⭐ **the factor route validated** | the deal models stop being necessary |
| 2026-10-06 | Mario's three tiers; the bullet question settled from his own slide | the method is agreed |
| 2026-10-06/07 | **Tier 1 for all 882**; I/O risk refused; TBA forwards split DV01 from CS01 | the deliverable exists |
| 2026-10-07 | ⚠️ `BOOK_CPR_PCT` found to be the wrong *kind* of 25% | an open parameter decision |
| 2026-10-07/08 | the coupon **structure** arrives; 132 published durations disclosed | the floater blind spot named |
| **2026-10-14** | the coupon **formulas**; a finding retracted; four corporate hybrids unstuck | G3 mostly closed |
| **2026-10-16** | Mario's call: three questions, and our own evidence found to be borrowed | the two asks re-sorted — factor **blocks**, coupon **qualifies** |
| **2026-10-23/24** | the data comes back: 372 of 412, no `CPN` **by decision** | ⭐ the T+1 shift turns out to belong to the **security** |
| **2026-10-24** | the 412 priced — the book reaches ~88% — and the published duration found to be a **spread** duration | ⭐ `coupon_formula` enters production |

---

## 3. Act 1 — an engine with no data (July)

`pricing/mbs.py` was a **static-CPR** pool pricer: give it a gross coupon, a remaining term and
an assumed prepayment speed, and it amortises level-pay, applies the speed to what the schedule
leaves, discounts, and returns price / spread / duration / WAL.

⭐ **One decision from July paid for itself twice.** The engine's input object was written
against the *exact* Bloomberg field names (`PoolTerms.from_bloomberg`), so that when the data
arrived nothing would need rewriting. It didn't: the pull landed and the 505 pools priced with
**zero code change**. The same discipline is why `data/coupon_structure.csv` and
`data/coupon_formula.csv` slotted in later without touching an engine.

⚠️ But the engine's central input — the prepayment speed — was a **guess with a grid around
it** (15 / 25 / 35% CPR), because nobody had measured 2009.

## 4. Act 2 — the factor, and why it replaced the deal models (25 Sep – 1 Oct)

A **factor** is one number per security per month: the fraction of the original balance still
outstanding. The move is that two consecutive factors give you the month's cash flow outright:

```
principal(t) = original face × ( factor(t−1) − factor(t) )
interest(t)  = original face ×   factor(t−1) × coupon ÷ 12
```

⭐⭐⭐ **And that needs no knowledge of the deal's rules at all — because the factor already
records what those rules did.** The waterfall ran; the factor is its output. That single
observation is what let a 1,294-security book be valued without Intex.

### ⭐ Worked on a real holding

`31402CZR6`, FNMA POOL #725352 4.5% due 2019, net coupon 4.500%, custodian price 103.5708,
factor at the valuation date **0.44041654**:

```
month   factor        principal / 100 of ORIGINAL face     interest / 100
 t=1    0.42939682              1.101972                      0.165156
 t=2    0.41997097              0.942585                      0.161024
 t=3    0.41186327              0.810770                      0.157489
 t=4    0.40355866              0.830461                      0.154449
 t=5    0.39635314              0.720552                      0.151334
 t=6    0.38777872              0.857442                      0.148632
```

Read the first row: `100 × (0.44041654 − 0.42939682) = 1.101972` of principal, and
`100 × 0.44041654 × 4.5% ÷ 12 = 0.165156` of interest. ⚠️ Note the interest uses **last
month's** factor — you earn on the balance that was outstanding, not the one that is left.

⭐⭐ **And the invariant that makes it trustworthy:** summing principal over the *whole*
observed path gives **44.041654**, against `factor(0) × 100 = 44.041654`. Every dollar of
original face is accounted for and none is invented. Across all 374 securities the worst
deviation is **1.42e-14**.

⭐ Pricing per 100 of **current** face needs only factor *ratios*, never the original face —
which is just as well, because that column is empty in the holdings file.

### How it was validated, and the part that was thrown away

⭐ **Twenty ordinary pass-through pools were put into the data request on purpose** — securities
the existing engine already priced, so the new route could be checked against a trusted number
before being pointed at anything exotic.

```
principal conservation     100.0000 per 100, worst 1.28e-13
new route vs old engine    n = 14 in-grid, median |difference| 8.2 bp, signed −2.6 bp
```

⚠️ **Six of the twenty were excluded and said so.** They had realised 57–74% CPR, outside the
15/25/35 grid, where the interpolation *clamps* — so their "engine" number was just the 35%
number wearing a different label. Comparing against it would have manufactured agreement.

### ⭐ The 2009 prepayment speed, measured for the first time

Forward from 2009-03-31: **1 month 20.4% · 3 months 21.4% · 12 months 19.1% CPR.** The 15/25/35
grid turned out to be **correctly centred**, which nobody had known. It also reproduced the
OAS "smile" independently: pools with a 3.50% coupon, deeply out of the money in 2009, prepaid
**0.91%**; pools at 6.50%, deeply in, prepaid **40.3%**.

### ⚠️ The trap: Bloomberg's month label is one month ahead

Its `2009-04` column **is** the 2009-03-31 position (median relative difference 2.9e-08 on
370 of 373; the column labelled `2009-03` is off by 1.6e-02). ⭐ Same house convention as the
TIPS index ratios found on 2026-09-19 — the second time, so now it is a known pattern rather
than a surprise. On one security, reading the labelled row puts the balance out by a factor of
six. `dataio/factor_history.py` is the single owner of the shift, and the raw file keeps
Bloomberg's own labels so the record stays checkable.

## 5. Act 3 — the three tiers, and the bullet question (6 Oct)

Mario sent two decks and a message. **Three tiers, and the custodian's price is the anchor in
all three:** ① reduced-form now, ② Bloomberg + empirical next (⭐ his slides name *our* factor
work as its input), ③ Intex, optional.

⚠️ **But on the phone he had said to treat the securities as bullet bonds first** — i.e. pretend
all the principal returns on the legal maturity date. We measured what that costs:

```
legal life, median      24.32 years
realised WAL, median     2.99 years      ⇒  6.87× overstatement, about +21 years of duration
                                            on 57% of the book by count
```

⚠️ **Re-measured on the shipped artifact, 2026-10-15** (the block above is the 2026-10-06
plan's, taken before the engine existed): legal **24.24 y**, realised WAL **3.17 y**, median
per-security ratio **6.43×**, over the **299** observed-path securities that receive principal
at all — the 373 less the 74 I/O strips, which receive none and so have no average life. The
legal side reproduces exactly; the WAL lengthened because the engine's residual treatments
extend the tail. ⭐ And the "57% of the book" is **the securitised 1,294 of 2,260**, not a
share of the 882 — easy to misread two lines under a table about the 882.

⭐⭐ **And his own deck settled it our way.** Slide 12, which *defines* Tier 1, says
"Bond-Equivalent Cash Flows" and states its limits as flows that *"do not yet respond explicitly
to CPR, defaults, extension/contraction or waterfall rules"*. **A measured factor path is a
fixed schedule — it is history, it responds to nothing — so it satisfies that in full.**
"Bullet" appears nowhere in the Tier-1 definition; only on the Tier-2 slide.

⇒ we amortised, and told him plainly that this differs from what he said on the call **and
costs nothing**. ⭐ The diagnosis is *"bullet"*, not *"maturity"*: the 505 pools already use the
master's legal maturity and are fine, because they amortise.

## 6. Act 4 — Tier 1 for all 882 (6–7 Oct)

### What "the custodian price is the anchor" actually means

Every tier solves the same equation for one unknown:

```
BT  =  Σ_t  CF(t) · exp( −t · ( z(t) + s ) )          ← solve for s
```

`BT` is the custodian's price — **given**. `CF(t)` are the cash flows — **assumed** (a factor
path, or a CPR). `s` is the spread — **solved**, so the model reproduces the price exactly.

⭐ Two consequences worth holding on to, both developed in `three_tier_method_explained` §3.6
and §3.9: the **price is right by construction**, so market value and concentration are exact
today; and the **spread is a plug** that silently absorbs any cash-flow error. ⇒ the number
that actually carries a claim is the **duration**, which is why "duration survives / spread does
not" recurs below as the test that matters.

### The deliverable

```
outputs/tier1_structured_2009-03-31.csv     882 rows = 858 priced + 24 named

three cash-flow generators, and every row says which it used:
   observed factor path        373
   assumed CPR                 458
   TBA forward, generic pool    27
```

⭐ The arithmetic reconciles exactly: `505 already priced + 376 with a path − 20 deliberate
overlap = 861`, then `− 3 degenerate = 858`. **None of the three is a shortfall** — two have a
factor already at zero, one produces no net cash at all, and nothing short of reading the path
could have known.

**Two cross-checks, and they are the validation:** two different generators over two different
populations give median spreads **261.3 bp** (observed path, 223 securities) against
**250.9 bp** (assumed CPR, 458) — 10 bp apart. And observed-amortising duration comes out at a
median **2.62 years** against **the custodian's own 2.45**.

### ⭐⭐ Two numbers we refused to publish

**The 76 interest-only strips.** An I/O's rate sensitivity is almost entirely *prepayment
response*: rates up → refinancing slows → the notional survives → more interest arrives → the
I/O is worth **more**. A fixed cash-flow schedule cannot express that, and the result is not
noise but a structurally wrong sign — **74 of 74 came out with a positive duration while 49 of
their custodian durations are negative**, with spreads from −56,670 to +6,719 bp.
⭐ **The rule this produced: publish a risk number only when its sign is known to be right.**
Price and market value ship (exact, being calibrated to the custodian's mark); spread and
duration ship **blank** — verified: of the 74, **0** carry a published duration.

**The 27 TBA forwards.** Everywhere else in this book a parallel rate bump and a spread bump are
the same arithmetic — across the 757 rows priced before the forwards the two columns differed by
**exactly 0.0**. A forward breaks that, because its spread sits in the **numerator only**:
`rate_duration == spread_duration − settle`, exactly, residual 9.99e-09 on the real 27.
⚠️ Consequence: **one row, one bump kind** — a rate duration beside a spread convexity cannot be
combined.

## 7. Act 5 — the 25% that was the wrong kind of 25% (7 Oct)

The 458 rows with no factor path take one book-wide speed, and it was **measured, not chosen**:
the 32 pools that have real paths realised a 12-month median of **25.83%**.

⚠️⚠️ **But what was measured is total factor decay, and the engine's input is a prepayment
rate.** A pool's balance falls two ways — **scheduled amortisation** (contractual, happens
whether or not anyone prepays) and **prepayment**. The engine amortises *first* and prepays the
survivor, so feeding it a decay number double-counts the schedule.

⭐ **Why that is a short-pool problem, in one formula.** The share of balance retired by schedule
each month is `g / ((1+g)^rem − 1)`, which → 0 as the remaining term grows and → `1/rem` as it
shrinks. At 288 months left that is 1.7%/yr; at 60 months, 15.7%/yr. So the same 25.83% decay
implies a true prepayment rate of **24.5%** on a long pool and about **10.8%** on a short one.

**The consequence, measured on all 458:** the population is long (median 287 months), so at the
median `25.0` survives. **No row's duration moves as much as the 1.5-year reporting threshold**
(worst 0.489y) — ⭐ the deliverable is safe. But the **46 rows under six years have their spread
understated by about 47 bp**.

⚠️ **Still an open decision** (keep 25.0 and name the tail / derive per pool / one net number) —
and `three_tier_method_explained` §3.11 shows that doing it properly is WAC-dependent, which
makes it a prepayment model, which makes it Tier 2.

## 8. Act 6 — the one bit the holdings file cannot carry (7–8 Oct)

The custodian reports each security's coupon **rate**. It never says whether that rate **moves**
— and that single bit decides whether a duration is near zero or a full remaining life.

Mario's `Type of Coupon` answered it for all 1,333 securities. ⚠️ **29.3% are not fixed**, worst
in the classes not yet started (ABS 54%, non-government CMOs 49%).

⭐⭐ **And it graded our own guesswork at 40.3%.** We had been inferring which coupons move from
description text. Scored against Bloomberg's answer over the 751 securities an earlier request
covered, our patterns caught **129 of the 320** that really move — about two thirds on the agency
pools and about **a quarter** on the private-label deals, because a deal name does not say:
`2007-OA4` is an option ARM with the token nowhere in it.

⭐ **The consequence was a disclosure, not a reprice.** 192 of the published 882 are non-fixed
and 132 carry a published duration; those 132 now say so in their flag. **No number moved**,
because the coupon *level* is the custodian's own — what a fixed-schedule bump assumes is not the
level but that the level *stays*. ⚠️ And two flag texts, not one: on a measured path only the
interest leg is in doubt (bounded at 1.77 years); on an assumed CPR both legs rest on the
assumption and **that bound does not transfer**.

## 9. Act 7 — the formulas, a retraction, and four bonds unstuck (14 Oct)

Mario sent the coupon formulas, as **dated rules**: one bond, several periods.

```
GREENPOINT MTG FDG TR 2006-AR3
   2006-04-28  →  1.000 * US0001M + 0.210%
   2019-07-25  →  1.000 * US0001M + 0.420%
   2023-07-25  →  1.000 * (TSFR1M + 0.114%) + 0.420%      ← LIBOR retires, Term SOFR arrives
```

⚠️⚠️ **This retracted a finding of ours.** A week earlier we had called the formula block
"not keyed to its rows", with a below-chance null test as evidence. The field returns a
**transposed six-row record** per security while the identifier block runs at one row — so
pairing by row number fails, which is exactly what the null detected. ⭐ **The detection was
right and the conclusion was not.** Proof needing no index and no convention: **437 of 437**
fixed records match the custodian's own coupon *exactly*.

⭐⭐ **The win was in the corporate book.** Four hybrids that had sat at the custodian's mark
since 2026-07-20 — no public source states what their coupon becomes after the call — now price
at **920 to 1,130 bp**. One had been recorded at LOW confidence with *all* terms unresolved and
came back identical to its sister tranche, confirming they are one issue in two wrappers. Eight
further margins we had sourced from the open web were confirmed **to the basis point**.

⭐⭐ **And the finding that shaped what happens next: the formulas cannot price an ARM.**
Evaluated at the valuation date they give a coupon **1 to 3 points below** the custodian's, all
seventeen testable pools in the same direction. It is not caps — it is the **reset**. These pools
reset annually **on their own anniversary**, so in March 2009 one carries a rate set the previous
June near 2.4% and another set in December nearer 0.5%; the one-year Treasury moved **2.34 points**
across that window, which is almost exactly the spread of gaps observed. ⚠️ The discriminating
test was *where* each implied reset date lands, not the size of the residual — solving one date
per pool always fits. **17 of 17 are explained by some past index level and 0 require a level the
index never reached.**

⇒ ⭐ **so Tier 1 keeps using the custodian's observed coupon**, which is the actual rate after
caps and resets — the better input, not a workaround.

---

## 10. Act 8 — the call, and evidence we had been borrowing (16 Oct)

Mario rang. He committed to sending **the six index histories** and **`MTG_FACTOR` for the
412** — both outstanding asks — and put three questions, each of which turned out to need a
measurement rather than an answer from memory.

**① "Didn't the index file I already sent have those six?"** No. It carries **11 series and
only 5 reach back to 2009**; Term SOFR starts 2019, the SOFR averages 2018, ECOFC 2022. ⭐ But
the question had a cause worth naming back to him: `TSFR6M` is in the file and `US0006M` is
not, `H15T1Y` and not `H15T5Y`, `US0001M`/`US0003M` and not `US0012M` — three near-miss pairs
that make the sheet look as though it already answers the request.

**② "How does your method simplify the traditional Tier 2 approach?"** It does not; at this
date it removes the need for one. **349 of 373 (94%) need no projected month at all**, median
127 recorded observations. ⚠️ With its limit said in the same breath: backwards only, so this
is Tier 2's input rather than its substitute. Mechanism in `three_tier_method_explained` §3.15.

**③ "Bloomberg has formulas for the 201 — why do you also need `CPN`?"** This is the one that
cost a round of self-correction, twice.

* The first draft said the formulas give "plausible numbers we cannot verify", and leaned on
  the agency ARM pools as *"the one population where both a formula and an observed coupon
  exist"*. ⚠️ **That was false** — the custodian reports `income_rate` for **all 412**, so the
  92 that compute are testable **directly**, on the population he asked about.
* ⭐ **And the direct test runs partly against us: 86% land within 5 bp.** The formulas are
  sound, and the reply now says so.
* ⭐⭐ What survives is sharper than the overstatement it replaced, because **the misses cluster
  by index, identically** — two COF-11 bonds both out by exactly −1.130, three 12MTA bonds all
  by −0.193 — which identifies the **reset lag**, not the formula, and recovers the very print
  each coupon was struck on. Worked through in `three_tier_method_explained` §3.13.
* ⭐⭐⭐ **The reframing that actually answers him:** the formula's competitor was never the
  coupon history; it is the custodian's valuation-date coupon, which we already hold and use.
  `CPN` answers a different question — how the coupon *moved* afterwards.

**⚠⚠ And we retracted a sentence of our own.** The 10-14 message said a balance with no coupon
leaves us unable to build a cash flow. All 412 carry a custodian coupon and a maturity, so
`MTG_FACTOR` **alone** prices every one of them on the coupon held flat — his own rule, already
our treatment of 192 holdings. ⇒ **`MTG_FACTOR` blocks; `CPN` qualifies.** Our own request rule
says only what blocks belongs in a request, and we had broken it in our favour; he smelled it
before we checked it.

⭐ A third thing fell out of the same session: **67 securities in his formula table are LIBOR
deals restated onto Term SOFR**, which is why Liberty Mutual's `TSFR3M +383.761` looked like a
disagreement with our `3M LIBOR + 357.6` and is not — the gap is the ISDA fallback spread, to
the basis point. `three_tier_method_explained` §3.14, and a test now stops a SOFR-era margin
ever reaching a 2009 price.

---

## 11. Act 9 — the data comes back, and a rule changes owner (23–24 Oct)

Mario returned three files on 2026-10-23: the index histories, `MTG_FACTOR` for the 412, and the
376-security factor history re-pulled from issuance.

| | asked | came back |
|---|---|---|
| the 412's factor history | 412 | **372** |
| the six index series | 6 | **4** — `US0006M`, `US0012M`, `H15T5Y`, `EUR003M` |
| the 201's coupon history | 201 | **none — by decision, not omission** |

**The 37 that did not come back are a keying accident, not a refusal.** Our request shipped a
ready-made ticker in its `security` column — `<CUSIP> Mtge`, verified 412 of 412. The pull was
built from the `isin` column instead, and 37 of the 412 have no ISIN; they became `NULL Mtge`
and errored. ⚠️ I first read this as a defect in *our* file and was wrong — an off-by-one in my
own checking script printed the `cusip` column, and I nearly reported it as our fault.
Re-asking is one sentence.

**No coupon history came, and that is his answer rather than a gap.** He asked at the 16 Oct
call why we wanted `CPN` when the formulas exist; the delivery contains `MTG_FACTOR` and not a
single coupon column. Measured against his rule, **320 of the 412 (78%) are already treated
exactly as he specifies**; the remaining 93 are where we keep the custodian's observed coupon
instead of the formula's computed one — explainer §3.18 has the numbers.

**⭐ The finding worth the round: the T+1 month shift belongs to the security, not to Bloomberg.**
The re-pull reproduces our record to `0.00e+00` on all 376, so both pulls label months
identically — which made the 412's opposite answer a real contradiction rather than a vendor
quirk. Resolved by asking each series which of its own months equals the custodian's factor:
Government MBS 238 of 241 shift, private-label CMOs 168 of 191 do not, and **23 CMOs and 13 ABS
go the other way from their own class**. So the loader aligns per security and asserts no
convention anywhere. ⚠️ It also retires an explanation we had written down — *"the custodian
strikes at T+1"* — which cannot be right, because a custodian strike date would apply to
everything it holds. Explainer §3.17.

**Free with the delivery:** both factor files now start at issuance — a median **54 extra
months** per security, 375 of 376 beginning before our record did. It changes no 2009 number and
roughly doubles the data a Tier-2 prepayment model would be fitted on.

**⚠️ Still blocked, and it blocks nothing:** `RFUCCT1Y` and `RFUCCT6M` did not come — his note
says they are not on Bloomberg and to substitute. I tried to identify them by inverting the
formulas against the custodian's coupons and **threw the result away**: 15 candidate series
× 16 lags is 240 combinations, so something always fits, and the top match was three-month
EURIBOR for a US ARM pool. The 43 securities involved are **1.9% of the book**, all Government
MBS ARM pools, and all already priced on the custodian's observed coupon.

---

## 12. Act 10 — the last category priced, and a duration that answered the wrong question (24 Oct)

Two pieces of work, one small and one that changed what we say about every floating-rate row.

**The 412 are priced.** `scripts/tier1_securitized.py` produces 412 rows — **371 on measured
factor paths, 41 named** for having none. A sibling driver rather than an extension of the
882-row table, which is already delivered; but the pricing core is imported from it, so the two
cannot disagree about how a measured path is priced. Validated the way the 882 were: principal
conserves to **1.42e-14** over 364 paths, the same floor. ⭐ The whole book is now **about 88%
priced** — 1,999 of 2,260 securities.

Two of its numbers looked wrong and both resolve. A **1,098 bp** median spread is simply what
non-agency paper cost in March 2009 — CMBS 771, ABS 1,052, CMO 1,334, against 226 for the
agency book, off marks with a median of 78. And a 2.61-year duration against a custodian 0.28
is the second piece of work.

**⭐⭐ The duration we publish is a SPREAD duration.** For a fixed coupon that is also the rate
duration; for the 312 rows whose coupon moves it is not, and the flag said only "this assumes
the coupon stays put" with no number. Measured, the two are a median **3.19 years** apart on
the government book and **6.89** on the securitised one, where the rate duration turns negative
on 79 of 83 — because below par a floater's coupon gain, which scales with face, beats its
discounting loss, which scales with price.

⚠⚠ **The first measurement was wrong and that is the part worth remembering.** It assumed
every coupon rises one-for-one with its index; **46 of 64** government floaters are inverse,
several leveraged to −3.0, and the naive assumption put the median at **−0.005 years instead
of +4.72**. The multiplier was in `coupon_formula.csv` all along — which is how that table
finally entered the production path rather than an audit script.

What shipped is a fact and a disclosure, not a model output: a `coupon_multiplier` column
(blank where unknown, never defaulted to 1.0) and a flag carrying the measured gap. The rate
duration itself is **not** published — no caps or floors are held, 97 of 180 securitised
floaters have no multiplier, and it is no closer to the custodian than what we already publish.
Explainer §3.19–§3.20.

---

## 13. ⭐⭐⭐ The one idea that keeps paying

**Measure what happened; do not model what should have happened.**

| | the thing you would have to model | the measurement that replaces it | status |
|---|---|---|---|
| **principal** | the deal's waterfall (Intex) | the **factor history** | ✅ done — 882 rows priced |
| **interest** | formula + index + reset anniversary + caps | the **realised monthly coupon** | ⏳ requested 2026-10-14 |

Both times the modelling route needed state we do not hold — the waterfall rules, or each pool's
own reset date and cap structure — and the measurement route needed **none of it**, because the
recorded number already contains the answer. ⭐ The second row is the first row's argument,
applied to the other leg of the cash flow, and it is why the ask is a coupon *history* rather
than the formula inputs.

## 14. ⭐ The discipline that keeps showing up

**Do not publish a number whose sign or whose units you cannot vouch for.** It has now fired
five times, each time on different material:

* I/O durations left **blank** — the sign is structurally wrong (Act 4).
* TBA metrics split into **two bump kinds** rather than one ambiguous column (Act 4).
* `BOOK_CPR_PCT` **named** as a decay rather than quietly re-fitted (Act 5).
* the 132 floating-coupon durations **marked** rather than re-routed on margins we lack (Act 6).
* leveraged coupon formulas **refused** rather than evaluated — `2370 × LIBOR − 15405%` returns
  about −14,220% at the 2009 index (Act 7).

⚠️ **And the corollary, learned the hard way twice:** run the null. A measurement that cannot
say it measured *nothing* is not evidence. It caught a spurious "13 of 34 within 2 bp" (the real
rate was below chance) — and the very same technique, applied honestly a week later, is what
retracted our own conclusion.

## 15. Where it stands, and what is missing

```
2,260 securities in the portfolio
  1,040 rows / 949 securities   six non-securitised classes          COMPLETE
    882 Government MBS           every one has a Tier-1 row          DONE
    412 CMO / CMBS / ABS         no repayment history of any kind    ⚠️ THE GAP
```

⚠️ **The 412 are the largest remaining hole — 18.2% of the book by count, 4.8% by par value**
(quote both, or say which: a count alone overstates by about 4×). They have no factor history,
and about **half** of them have moving coupons. ⚠️ **That request has never reached Mario** —
the 2026-10-02 pack carrying it was never sent, nor was the 2026-10-08 message. It is named in
one line of `mario_message_2026-10-14.md` and goes separately.

**Also open:** `BOOK_CPR_PCT` (Act 5, a decision not a cleanup) · six index histories and the
ARM reset/cap fields (`missing_data.md` G7a/G7d) · four Eurobond margins whose formula field
comes back empty, so re-pulling it will not help · and `COVERAGE.md` / `PROJECT_STATUS.md`,
which still do not describe the mortgage book.

## 16. Every headline number, and where it comes from

| number | meaning | source |
|---|---|---|
| 882 = 858 + 24 | Tier-1 rows, priced and named | `outputs/tier1_structured_2009-03-31.csv` |
| 373 / 458 / 27 | the three cash-flow generators | same, `paydown_source` |
| 505 = 478 + 27 | pools the pool driver prices | `outputs/pool_risk_2009-03-31.csv` |
| 1.42e-14 | worst principal-conservation deviation, 374 securities | `bloomberg_return_2026-10-01.md` §7 |
| 8.2 bp, n=14 | new route vs the existing engine, 20 validation pools | same |
| 19.1% / 20.4% | measured 2009 CPR, 12-month and 1-month forward | same |
| 24.32y vs 2.99y | legal life against realised WAL ⇒ 6.87× | `cc_plan_govt_mbs_amortising_tier1_2026-10-06.md` |
| 261.3 vs 250.9 bp | the two generators' median spreads | `tier1_structured_*.csv` by route |
| 2.62y vs 2.45y | observed-amortising duration vs the custodian's | same, 223 rows |
| 74 / 0 | I/O strips priced / with a published duration | same, `route == io-strip-…` |
| 9.99e-09 | `rate_dur − (spread_dur − settle)` on the 27 forwards | `src/pricer/assets/securitized/tba.py` |
| 25.83% / 19.15% | the same pools' 12-month decay, gross and net | `three_tier_method_explained` §3.10 |
| 0 of 458, max 0.489y | rows whose duration moves past the 1.5y threshold | same |
| 192 / 132 | non-fixed rows / those with a published duration | `tier1_structured_*.csv`, `coupon_structure` |
| 40.3%, 129 of 320 | our description-pattern recall vs Bloomberg | `missing_data.md` G7 |
| 437 of 437 | fixed records matching the custodian exactly | same, G7b retraction |
| 920–1,130 bp | the four newly priced corporate hybrids | `outputs/implied_oas_2009-03-31.csv` |
| 2.34 points | 1-year Treasury **peak-to-trough range** over the 12 months to 2009-03-31 — ⚠️ the *change* across those months is only 0.98 | `data/index.xlsx`, `H15T1Y` |
| 349 of 373, median 127 | securities needing no projected month · months of recorded history | `tier1_structured_*.csv`, `months_observed/projected` |
| 94 / 92 / 14 / 1 | the 201 by formula outcome at 2009-03-31 | `coupon_formula.csv` + `index.xlsx`, run 2026-10-16 |
| 86%, median −0.021 pt | formula vs the custodian's own coupon, n=92 | same, against master `income_rate` |
| −1.130 × 2, −0.193 × 3 | identical per-index errors that identify the reset lag | same; `three_tier_method_explained` §3.13 |
| 67, 26.161 bp | LIBOR-to-SOFR restatements · the 3M ISDA adjustment | `coupon_formula.csv`; §3.14 |

⚠️ Re-read these from the artifacts at writing time, never from here — and for any count, hash
or test number the newest `release_facts_<date>.md` outranks this file.
