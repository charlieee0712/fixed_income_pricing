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
| **principal-only strips** | **76** | ⭐ **unblocked outright** — a PO pays no interest at all, so the factor path is its whole cash flow and coupon is irrelevant |
| fixed-coupon tranches + the 20 validation pools | ~238 | ⭐ **unblocked** — factor path + the coupon already in the custodian file |
| whatever genuinely floats | **16 – 62** | ⚠️ **blocked, and the range is honest** — see below |
| the 458 pools not in 03 | 458 | ⚠️ **stay on the 15/25/35 grid** — now anchored by the measured ~20%, but not individually dated |

⚠️ **The blocked count is a RANGE because two methods disagree and I will not pick the
flattering one.** Searching the description text for floating-rate language finds **16**;
taking the class letter `S` (the usual inverse-floater convention) finds **57**; only **8**
are caught by both. ⭐ And the letter method is the one I *already demonstrated wrong* —
29 of the 54 `P`-prefixed tranches turned out to be principal-only strips rather than PACs.
Quoting a number from a method I had disproved was the same mistake twice; the honest
statement is **16 to 62, with at least 314 of the 376 certainly usable**.

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
