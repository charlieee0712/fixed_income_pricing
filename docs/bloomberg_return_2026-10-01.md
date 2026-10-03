# What came back from the Bloomberg terminal — 2026-10-01

Liping ran the request and returned all four workbooks to `docs/`. Her note: *"The previous
document functions doesn't work. I have changed the functions and here are the
information."* ⚠️ **She is not expected back at a terminal for some time, so this is
treated as the only pull we get.**

---

## 1. The verdict in four lines

| ask | result |
|---|---|
| **03 factor history** — the one that matters | ⭐ **COMPLETE. 79,336 of 79,336 values, zero gaps, dating verified.** |
| 02 prepayment speeds at 2009 | ⚠️ **failed on the date** — our field has no history; her substitutes are today's |
| 01a / 01b pilots | ⭐ did exactly their job — both diagnosed the failure before the big pull |
| coupon history | ⚠️ **never asked for** in 03. Our omission, not hers |
| `04` five terminal questions | ⚠️ not returned — ⭐ and it costs almost nothing: Q1 ("is the factor field history-enabled?") was answered by 03 working, and the rest were the fallback route the factor path makes unnecessary |

⭐⭐ **And the failure in row two turns out not to matter much**, because the factor path
*is* the realised prepayment — see §4, where the 2009 speed is measured for the first time.

---

## 2. ⭐ 03 — complete, and correctly dated

```
376 securities × 211 months = 79,336 cells
NUMERIC 79,336    #N/A 0    blank 0
every column carries a full, monotonically declining series
```

**The dating was checked rather than assumed**, against the custodian's own
`paydown_factor` for 373 of the 376:

| the row labelled | median relative difference | within 1e-6 |
|---|---:|---:|
| `2009-03` | 1.6e-02 | 78 / 373 |
| **`2009-04`** | **2.9e-08** | **370 / 373** |
| `2009-05` | 1.6e-02 | 72 / 373 |

⭐⭐ **Bloomberg's month label sits one month ahead of the custodian's.** Its `2009-04`
column IS the 2009-03-31 position. ⚠️ **Every reader of this file must apply that shift.**

⭐ This is the *same T+1 convention* found on the TIPS index ratios on 2026-09-19 — the
custodian strikes at T+1. Two independent discoveries of one house convention.

⚠️ **The check earned its keep on a single security.** `3133T5MR1`: custodian
**0.00196067**, Bloomberg's `2009-03` **0.01212421**, Bloomberg's `2009-04` **0.00196067**.
Reading the labelled row would have put that pool's balance out by a factor of six — and
nothing on the face of the file would have said so.

---

## 3. ⚠️ 02 — our field name has no history, and the substitutes are current

`MTG_GEN_CPR_3M` returned **505 × `#N/A Invalid Field`** under `BDH`, at both dates, for all
three tenors.

⭐ **It is not a typo.** The identical mnemonic under `BDP` returns numbers (01a column E,
five of five). **It is a current-value-only field with no history** — a property of the
field, not an error in our list. That is a different failure from July's
`MTG_HIST_COLLAT_CPR_LIFE`, which genuinely did not exist.

Liping substituted, and labelled them properly:

| field | filled |
|---|---|
| `MTG_PREPAY_TYP` (`PSA` / `CPR`) | 439 of 505 |
| `MTG_PREPAY_SPEED` | 282 |
| `MTG_PL_PSA_1M` / `_3M` / `_6M` | **505 / 505 each** |

⚠️ **They are today's values.** One line settles it: for a seasoned pool CPR ≈ 0.06 ×
PSA/100, and on `31283H4W2` the returned `MTG_PL_PSA_3M` = 156.1 → **9.37% CPR**, against
that same security's `BDP MTG_GEN_CPR_3M` *today* of **9.34**. The same date failure as
July, in a different unit.

⚠️ The TBA rows are worse than merely current — `01F050452` reads **2281 PSA** (≈137% CPR),
which is not a prepayment rate. Pool-level fields on a generic do not mean anything. Flag,
never use.

---

## 4. ⭐⭐⭐ The 2009 prepayment speed, measured at last

The failure in §3 matters far less than it looks, because **a factor path IS a record of
prepayment**. For the 20 ordinary pass-through pools deliberately included in the request as
a validation set — known rate, known term — the speed can now be *measured*:

```
survival  = f(t+n) / f(t)                      from the factor file
scheduled = level-pay amortisation, no prepayment
SMM       = 1 − survival / scheduled      CPR = 1 − (1−SMM)^12
```

⚠️ The series begins *at* the valuation date, so there is no trailing history. These are
therefore **forward** realised speeds — which is the more useful number anyway: the cash
flows being discounted are exactly the ones that followed.

| horizon from 2009-03-31 | median CPR | p10 | p90 |
|---|---:|---:|---:|
| next 1 month | **20.4%** | 14.4 | 30.4 |
| next 3 months | **21.4%** | 14.2 | 35.7 |
| next 12 months | **19.1%** | 13.4 | 37.6 |

⭐ **The grid we have been pricing on is 15 / 25 / 35% CPR. The truth is ~20%** — between
the first two columns, so the published band of **220–265 bp was correctly centred**, and
interpolating gives roughly **257 bp**.

⭐⭐ **And it independently confirms the OAS smile.** `312962EA7`, WAC 3.50% and out of the
money, prepaid at **0.91%**. `36241KNL8`, WAC 6.50% and deep in the money, prepaid at
**40.3%**. The refinancing incentive drives the realised speeds in exactly the order the
weekly report's spread bands predicted — from an entirely independent measurement.

---

## 5. ⚠️ What is still blocked, honestly

**Three buckets, and they must not be collapsed into one headline.**

| | count | status |
|---|---:|---|
| **principal-only (P/O) strips** | **79** | ⭐ **unblocked outright** — a PO pays no interest at all, so the factor path is its whole cash flow and coupon is irrelevant |
| **interest-only (I/O) strips** | **76** | ⚠️ **NOT unblocked** — the mirror case, and it needs *more*, not less: the strip rate, and whether its factor runs on a **notional** balance |
| everything else in the 376 | **222** | ⭐ **unblocked if the coupon is fixed** — factor path + the custodian's coupon; whatever floats is the range below |
| whatever genuinely floats | **16 – 62** | ⚠️ **blocked, and the range is honest** — see below |
| the 458 pools not in 03 | 458 | ⚠️ **stay on the 15/25/35 grid** — now anchored by the measured ~20%, but not individually dated |

⚠️⚠️ **CORRECTED 2026-10-02 — the 76 in the first version of this table was the
I/O count wearing the P/O label.** Measured over the 376 columns that came back, matching
the slash forms the custodian actually writes (`P/O`, `I/O`) rather than bare `PO`/`IO`:
**79 principal-only, 76 interest-only, 1 naming both, 222 neither.** ⭐ The two are
opposites — a PO has no interest leg and needs no coupon, an IO has no principal leg and
needs its strip rate *and* its factor's meaning — so the mislabel moved 76 securities from
"blocked" to "done" on the page. An earlier pattern found only 2 IO because `IO` does
not match `I/O`.

⚠️ **The blocked count is a RANGE because two methods disagree and I will not pick the
flattering one.** Searching the description text for floating-rate language finds **16**;
taking the class letter `S` (the usual inverse-floater convention) finds **57**; only **8**
are caught by both. ⭐ And the letter method is the one I *already demonstrated wrong* —
29 of the 54 `P`-prefixed tranches turned out to be principal-only strips rather than PACs.
Quoting a number from a method I had disproved was the same mistake twice; the honest
statement is **16 to 62, with at least 314 of the 376 certainly usable**.

⚠️ And "usable" is doing work in that sentence: 76 of the 314 are I/O strips, which are
unblocked for *coupon* only once 06 returns, and still owe the notional question.

⭐ **What would settle it is one more column.** A floater's coupon differs between two
dates and a fixed one's does not — and the 01b pilot proved the coupon field has history.
One observation at two dates classifies all 376 definitively.

⚠️ **The coupon gap is our omission, not hers.** The 01b pilot asked for factor *and*
coupon, and both worked — the coupon column returned a clean 12-month series. The main
sheet then asked for factor only. The README promised "factor + 票息历史" and the sheet it
described did not request it. **Recorded here rather than quietly worked around**, because
it is the difference between "the ARMs are in" and "the ARMs are not", and the first would
be untrue.

---

## 6. What the pilots bought

Both diagnosed their failure **before** the large pull, which is what they were for:

* `01a` showed `MTG_GEN_CPR_3M` dead under `BDH` while alive under `BDP` — so the
  substitution happened at the terminal, in one sitting, instead of after another round trip.
* `01b` showed `MTG_FACTOR` history working, which is why 03 was worth running at all.

⚠️ One thing neither the pilots nor **four separate pre-send audits** caught: that the
main sheet asked for only half of what the pilot tested.

⭐ That is worth being precise about, because it was not a lack of rigour. The audits
checked, repeatedly and successfully, whether the files were **correct** — column letters
against real positions, every formula against its own row's ticker, the month calendar
contiguous, the formula row carrying the first month, formulas stored as formulas rather
than text, the whole thing opened in real Excel. One of those checks
(`verify_transposed`) is the only reason this pull is usable at all: 03 shipped for one
commit with its formulas a row above their month labels, which would have attributed all
79,336 values to the wrong month — invisibly, and *especially* invisibly once Bloomberg's
own T+1 offset was layered on top.

**What no audit asked was whether the files were COMPLETE against what we had said we
needed.** A missing question, not a weak one.

⭐ **The rule that closes it: diff the pilot's field set against the main sheet's before
sending, and fail if the main sheet asks for less.** A pilot can only verify the fields it
carries; nothing was watching the ones the main sheet forgot to inherit.

---

## 7. ⭐⭐⭐ The method is validated — the factor route prices a bond

This is the test the 20 pass-through pools were put in the request for: they are ordinary
pools **our engine already prices**, so the factor route could be checked against a number
we already trust before being pointed at a single tranche.

⭐ **Pricing per 100 of CURRENT face needs only factor RATIOS, never the original face** —
which deletes the `orig_face = par / factor` derivation, and with it the first of the five
ways this could have gone wrong.

Conventions mirrored exactly from `core.pricing.prepayment` — same monthly grid, same
`exp(-t(z+s))` discounting, same calibration target. A difference arising from pricing
conventions rather than from the method would have proved nothing.

### The three checks

| | result |
|---|---|
| **A. principal conservation** — an identity, not a tolerance | **100.0000 per 100, worst deviation 1.28e-13** |
| **B. realised whole-life CPR** | median **23.94%** |
| **C. factor path vs the existing engine at the same pool's own realised speed** | n=14, median **8.2 bp**, signed median **−2.6 bp** |

⭐ **8.2 bp between two genuinely different calculations** — one assuming a constant speed,
one using the month-by-month path that actually happened — with **no systematic bias left**.
That residual is not error; it is the information the path carries and a flat assumption
cannot.

⚠️ Six of the twenty realised 57–74% CPR, far outside the 15–35% grid. `np.interp` clamps,
so their "engine" figure is just the 35% number and comparing against it would measure the
interpolation rather than the method. **Excluded and said so**, rather than left in to
flatter the median.

### ⭐ And the validation did its job — it found something

The first run showed **median |diff| 21.2 bp with a signed median of −11.4 bp**. A
consistent sign is not noise, so it had a cause, and the cause was predictable from the
one check that was already failing: **principal conservation came to 98.4–100.0 rather
than 100**.

⚠️ The series ends at 2026-09, and a pool still alive then has balance we had simply
dropped. Too little PV ⇒ too narrow a calibrated spread ⇒ **every still-alive pool reading
negative**, which is exactly the pattern the table showed. (The one still-alive pool
reading positive, `312962EA7`, is the only one priced **below** par — the sign reverses
with the price, as it does throughout this book.)

Repaying the residual at the last observation:

```
                      tail dropped     tail repaid
principal identity     98.4 – 100.0    100.0000  (1.28e-13)
median |diff|             21.2 bp         9.9 bp
signed median            −11.4 bp        +0.8 bp
```

⭐ **A hypothesis with a predicted sign, tested, and the bias disappeared.** That is what
twenty pools in a request buy: the gap was found on twenty securities in an evening rather
than on three hundred in a report.

⚠️ The residual tail is now a **named modelling item** for the real driver — repaying it at
the last observation bounds the effect but is not a model. The right treatment is to
continue amortising at the terminal speed, and the difference between the two is small
(the residual is 0–1.6% of balance) but it should be a choice rather than an accident.

### What this settles, and what it does not

⭐ **Settles:** the decomposition is arithmetically exact; the factor data prices a real
bond; the result agrees with an independent engine with no systematic offset. **The route
is sound and the ~314 unblocked securities can be built.**

⚠️ **Does not settle:** the IO strips (76) — their factor may be a *notional* and their
coupon a *strip rate*, neither of which this test exercised, since all 20 validation
securities are ordinary pools. ⭐ That is the next thing to check, and it should be checked
the same way: on the few, before the many.
