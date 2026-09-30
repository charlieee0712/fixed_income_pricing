# Bloomberg request pack, 2026-09-29 — the mortgage book's two data gaps

**For:** Liping (university terminal) · **Pack:** `docs/bloomberg_request_2026-09-29/`
**Regenerate:** `PYTHONPATH=src python scripts/make_bloomberg_request.py`
**Reader's note:** the pack's own `00_README.txt` is written for Liping, in Chinese. This
file is the repo's record — why the request has the shape it does, and what was measured
to give it that shape.

| file | rows | what it is |
|---|---:|---|
| `00_README.txt` | — | order of play, in Chinese |
| `01a_PILOT_cpr.csv` | 5 | **run first** — 4 ways of asking, stratified |
| `01b_PILOT_factor.csv` | 3 | **run first** — factor + coupon history |
| `02_cpr_main.csv` | 505 | 3 fields × 2 dates = 3,030 points |
| `03_factor_history.csv` | 376 | 344 tranches + **12 ARM pools** + 20 validation — a **list** |
| `04_cmo_terminal_questions.csv` | 3×5 | questions, no formulas |

---

## Ask 1 — prepayment speeds for the 505 we already price

We have these fields. They came back in July **as of the pull date** rather than as of
2009-03-31. `BDP` returns only a current value, so this is the same request re-dated
through `BDH`. 882 × 8 fields became **505 × 3 × 2 = 3,030 points**, a 57% cut.

**The acceptance test is quantitative.** ⚠️ Population named, because the first draft did
not: of the **505 in this request**, the **253 still alive today** run at a **median 8.3%
CPR** (p10 7.2 / p90 11.3). At 2009 the same collateral sat a **median 1.53pp in the
money** in the middle of a refi wave, so a 2009 speed should be several times today's —
plausibly 20–40%. **If the 2009 column reads ≈8%, the date did not apply.**

⭐ **The pilot is stratified, not sampled.** 486 of the 505 returned a value in July, so
the identifiers resolve and the field name is real — neither is what needs testing. The
open questions are whether `BDH` applies the date and how the array lays out. One row each
for: a live pool with a value, **a paid-off pool** (⚠️ Bloomberg *freezes* a dead pool's
CPR rather than blanking it — **215 of the 220 dead pools inside the 505** still return
one, so a frozen number is
indistinguishable from a live one), a live pool with no current value, and a TBA generic
from each side of the July outcome.

---

## ⭐ Ask 2 — factor history, which is the answer to the 344

### The reframe

The 344 REMIC/CMO tranches and IO/PO strips have been blocked on deal structure, with the
plan being to wait for a purchase (Intex, or Bloomberg's CMO analytics). **We were asking
for the wrong thing.**

> A waterfall's only job is to decide how much principal each tranche receives each month.
> **The factor file records that decision.**

```
principal(t) = orig_face × (factor(t−1) − factor(t))
interest(t)  = orig_face × factor(t−1) × coupon(t) / 12
```

That is the complete cash flow vector, and it requires **no knowledge of the structure at
all**.

⭐ **It is structure-agnostic, and that is not a claim — it falls out of the arithmetic.**
A PO has no interest term. An IO has no principal term. And a **Z accrual needs no special
case**: during accrual the interest term and the negative principal term are equal and
opposite, so the net cash flow is **exactly zero**, which is precisely what a Z does.
Verified before this was written.

### Why most of the vector is already known

We are valuing at **2009-03-31, seventeen years ago**. Measured on the 344:

* **89 have paid off entirely** ($114.3M) — realised cash flow **complete**, zero tail
  assumption of any kind.
* **251 still alive** ($356.0M), median **6.7 years** remaining today against the 17 years
  since the valuation date. The observed window dominates; the short tail takes the same
  CPR grid the pools already use.
* ⚠️ **4 are of unknown status** — the July pull returned no WAM for them, so they are
  neither. The first draft said "255 alive", folding the unknowns in, which made the
  paragraph sound more settled than the data is.
* **`factor` and `par` are on hand for 341 of 344**, so `orig_face = par / factor` is
  derivable — ⚠️ the master's `orig_face` column is empty, which is why it is computed
  rather than read.
* ⚠️ Factors range to **1.868** on this set, which is correct: a factor above 1 is a Z
  accrual whose balance has grown. Already documented in `CLAUDE.md`.

### Why this ask is easier than the one it replaces

A **factor is a published monthly fact with a date** — the category `BDH` exists to serve.
A cash flow *projection* is a computed analytic off today's collateral state, and dating it
to 2009 is a different and much harder thing. That distinction is the whole reason this
route is worth trying first.

### ⭐ The validation seed

`03_factor_history.csv` carries **20 pass-through pools our engine already prices**
alongside the 344. If the factor method reproduces our own number on those, the method is
proven **before** it is pointed at a single tranche. Gate 0, at the front, which is the one
ordering this project has measured as working.

⚠️ **`03` is a security LIST, not a formula sheet.** A factor request returns a *time
series* per security; 364 of those cannot sit one-per-row, and the layout is a decision to
make at the terminal once the pilot shows what one series looks like. The precedent is
`govt_mtge_cusips.csv`. ⚠️ `MTG_FACTOR` in `01b` is a **candidate spelling**, labelled as
one, with a `FLDS` question beside it — guessing a mnemonic is what cost the July pull.

### ⚠️ The honest limit, which must travel with every number this produces

A realised path is **hindsight**. It yields the discount rate the holder actually earned,
not the spread the market demanded in March 2009.

| | the 490 pools | the 344 tranches, proposed |
|---|---|---|
| cash flow path | **assumed** (CPR grid 15/25/35) | **realised** (factor history) |
| the spread | conditional on the assumption | conditional on hindsight |
| duration / DV01 / convexity | well defined given the path | well defined given the path |

**Neither is an OAS**, and we already say so about the pools. For *risk* metrics — which is
this project's stated goal, with implied spread as the intermediate — a cash flow vector is
a cash flow vector and the numbers stand on the same footing. For *"what was this worth to
the market that morning"* it is not the answer, and that still needs the deal structure.

⭐ **One bonus worth taking.** The same factor history on the 490 pools yields their
**realised CPR**, which turns the 15/25/35 grid from three arbitrary scenarios into three
scenarios plus the answer.

---

## Ask 2b — the fallback questions (`04`)

3 securities × 5 questions, no formulas. Q1 asks whether a factor field exists and is
history-enabled — the question ask 2 depends on. Q2–Q3 probe whether a cash flow projection
can be dated to 2009 at all; **we expect no**, and a measured no is still worth having,
because the purchase question has sat with Mario since 2026-09-26 on our reasoning alone.

⭐ **Why this exists at all:** our own handoff says the structure is *"a purchase decision
(Intex, **or Bloomberg CMO analytics**)"* — and the first draft of this request then told a
colleague about to sit at a Bloomberg terminal that the tranches were a conversation for
Mario. We named two sources and asked neither. Caught by the user, same day.

---

## What was measured while building this

* **344 tranches sit in 170 distinct deals; 144 of those deals contribute exactly one
  tranche.** We hold a single slice of a deal that may have twenty, so a *waterfall*
  requirement is ~170 complete deal models, not 344 records. (The factor route sidesteps
  this entirely — which is the point.)
* **39% of the class by count, 28.5% by value**: $473.4M of $1,660.8M.
* ⚠️ **The tranche class letter is a per-deal convention, not a standard.** Of the 54 whose
  class token starts with `P`, **29 are PRINCIPAL ONLY strips, not PACs**. Do not route on
  it — `04`'s Q5 exists because of this.
* **The cheap route is closed.** IO and PO are exactly **76 each**, which looks like matched
  pairs, and a held IO+PO pair reconstitutes its collateral. We hold both halves in **one**
  deal (FHLMC 2827) and even there the two are not complementary (`CL XO` vs `CL PS`).
* ⚠️ **Custodian duration does not rescue them.** On the 344 it runs **−102.5 to +57.1,
  61 negative**, against 0.85–3.95 on the 490 pools. Those extremes are *correct* — a −100y
  IO strip is real economics — which is exactly why approximating these as pools would be a
  category error rather than an approximation.

---

## ⚠️ A claim of ours that was wrong, and the follow-up it opens

An earlier draft told Liping: *"WAC is not re-pulled — an 0.50pp error moves the calibrated
spread by 0.24 bp median, 0.87 bp worst."* **That measurement was taken on the fixed-rate
pools that price**, where WAC drifts slowly. It is false for ARMs, where the WAC does not
drift, it **resets**.

Routing gives 519 candidates; the driver prices 505. ⭐ **No silent loss — all 14 are named
in `pool_disposition_2009-03-31.csv`**, which is the `reconcile()` discipline doing its job.
But the reasons matter:

* **12 ARM pools refused** because the pulled net income rate *exceeds* the pulled gross WAC
  — impossible, and the signature of a WAC that has reset since 2009. Gaps up to **3.9pp**
  (2026 pull 2.875%, 2009 income rate 6.756%).
* **2 TBAs** whose description never states a settle month — a description gap, not a data
  one.

⭐ **The 12 need no pull.** The master already holds the 2009 **net** coupon, and
`gross WAC = net + servicing` with the **0.50pp** constant we already ship as
`tba.TBA_SERVICING_SPREAD_PCT`. A 25bp error in that assumption costs ~**0.12 bp** of
spread on the measured sensitivity. ⚠️ The ARM nature remains — a level-pay fixed engine on
an adjustable pool freezes the coupon at its 2009 value, which is the same shape as the
2026-08-31 FRN current-coupon freeze and needs the same explicit label.

⭐⭐ **SUPERSEDED BY THE PRE-SEND AUDIT (2026-09-30): the 12 are now IN the factor
request.** The derived-WAC plan above is not wrong, it is beside the point — it recovers a
coupon **level**, and an ARM's whole difficulty is that the coupon **moves**. Factor
history plus coupon history is an ARM's realised path exactly as it is a tranche's: the
same route, the same request, twelve more rows on a list of 364.

⭐ Worth naming as a pattern: the reason they were left out was a **cost** argument ("24
data points, we can do it ourselves for 0.12bp") that quietly answered a **different
question** than the one being asked. The audit caught it only because it asked "is every
unpriced security accounted for in some ask?" rather than re-reading the prose.

**This is the same failure as `PAR_YIELD_UNITS` and the endpoint tolerance:** one rule sized
on the population you measured, silently covering a second population you did not.
