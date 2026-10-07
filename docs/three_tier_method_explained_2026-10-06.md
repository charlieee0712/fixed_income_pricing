# The three-tier structured method, explained — 2026-10-06

**What this file is for.** `client_directive_three_tier_structured_method_2026-10-06.md` is
the decision record: facts, slide citations, measurements, decisions. **This one is the
reading guide** — enough to understand the whole thing without opening either deck, with the
concepts spelled out and the numbers traced to where they come from. Written because the
material arrived all at once and reads as far more new than it is.

---

## 1. The honest one-paragraph version

Mario sent two decks and a message. They say: the four securitised classes (mortgage pools,
CMOs, commercial mortgage-backed, asset-backed — 1,294 securities, **57% of the portfolio by
count**) will be brought into the risk system in **three phases**. Phase 1 treats each one as
a simple bond whose cash flows are fixed, calibrates a spread to the price the custodian
already reports, and shocks rates and spreads to get portfolio risk. Phase 2 makes the cash
flows behave the way the historical data says they behave — **which is the work we validated
on 2026-10-01, named in his deck as ours**. Phase 3 is buying Intex, and only if a client
needs it. He wants Phase 1 now, and then a portfolio-wide Monte Carlo.

---

## 2. ⭐ Almost nothing here is new — this is checkable, not reassurance

| what Mario calls it | what it already is |
|---|---|
| **Tier 1** — calibrate a spread to the custodian price, then compute risk | **`src/pricing/calibrate.py` + `risk.py`**, written June 2026. The same equation, pointed at a new asset class. |
| **Tier 2** — Bloomberg + empirical | **The factor route**, built and validated 2026-10-01. His slides name it. |
| **Tier 3** — Intex | Buying software. Not our work. |
| **the Monte Carlo at the end** | ⭐ genuinely new, and genuinely later. |

So the new ideas are **two**: the *factor*, and the Monte Carlo layer. The three-tier framing
is an ordering of things we mostly have.

---

## 3. The concepts, in plain language

### 3.1 Bullet versus amortising — and why it is the whole game

An ordinary corporate bond: you lend 100, collect interest, and on **one specific day** you
get the 100 back. All at once. That single lump is why it is called a **bullet**.

A mortgage pool: you own a slice of a thousand home loans. Every month the homeowners pay
interest **and a little principal**. So money comes back **continuously**. That is
**amortising**. By the time the date written in the legal documents arrives, there is
usually nothing left.

Money comes back early for two reasons:

1. **Scheduled amortisation** — every monthly mortgage payment contains some principal by
   design.
2. **Prepayment** — someone sells their house or refinances and repays the whole loan.
   ⭐ In 2009 rates were collapsing, so refinancing was heavy: we **measured** these pools
   losing about **20% of their balance per year**.

### 3.2 What a "factor" is

One number per security per month, between 0 and 1: **the fraction of the original balance
still outstanding.**

```
factor = 1.00   nothing repaid yet
factor = 0.40   60% has come back, 40% still owed
factor = 0.00   fully repaid; the security is finished
```

⭐⭐ A monthly series of factors is therefore a **complete record of when the money actually
came back**. And from two consecutive months:

```
principal paid this month = original size x ( last month's factor − this month's factor )
interest paid this month  = original size x   last month's factor x rate ÷ 12
```

⭐⭐⭐ **That is the entire cash flow, and it needs no knowledge of the deal's rules** — no
waterfall, no tranche priorities, no Intex — **because the factor already records what those
rules did.** This is why we called it the way out of buying deal data, and it is why Mario's
Tier 2 is our work.

⚠️ Two wrinkles that look like errors and are not:

* An **accrual tranche** (Z / VZ / ZC) does not pay its interest out; it adds it to its own
  balance. So its factor **grows**, and can exceed 1 — the largest in this book is **3.1368**.
  The formula then gives a *negative* principal, which exactly cancels the interest: net cash
  zero, which is precisely what such a tranche pays. Our engine asserts that identity to
  machine precision rather than special-casing it.
* A **principal-only (P/O) strip** receives no interest at all — and the custodian's own
  coupon for all 78 of them reads literally **0.000%**, which is a nice independent
  confirmation. An **interest-only (I/O) strip** is the mirror: no principal, interest on a
  shrinking notional.

### 3.3 Legal maturity, and the 7× problem

If you do not know when the money actually came back, the simplest thing is to pretend the
security is an ordinary bond: pay interest until the legal maturity, then return all the
principal on that day.

We measured what that costs, on the 373 securities whose real paths we hold:

| | median | p10 | p90 |
|---|---:|---:|---:|
| legal life (years) | **24.32** | 8.97 | 28.15 |
| realised WAL (years) | **2.99** | 1.13 | 4.97 |
| ratio | **6.87×** | 3.05× | 16.43× |

**WAL** ("weighted average life") is the average number of years you wait for each unit of
principal. ⭐ And **duration is essentially that same average, which is why it matters**:
duration answers *"if rates move 1%, how much does this lose?"* A 24-year duration says
"lose about 24%"; a 3-year one says "lose about 3%".

⚠️ **227 of the 373 had repaid completely by 2026-09** — a median 5.5 years after the
valuation date — against a median legal maturity of 24 years.

⭐⭐⭐ **And the diagnosis is "bullet", not "legal maturity" — this was checked, and the check
reversed the first reading.** Our pool engine (`core/pricing/prepayment.py`, pricing 505 pools
since July) uses *the same* legal maturity from the master. But it **amortises**: legal
maturity is the *term over which the balance runs down*, not the day a lump arrives. Its
2026-10-01 validation was clean on exactly that maturity. So the defect is the lump, and the
fix is to let the cash flows amortise — **which is still Tier 1** (fixed flows, one spread,
no response to rates) and uses an engine we already own.

### 3.4 Why DV01 and CS01 are two numbers

The discount rate in the pricing formula is `z + s` — the base (Treasury) rate **plus** the
spread. Two dials that add to one number.

* **DV01** — hold `s`, move `z`. Interest-rate risk.
* **CS01** — hold `z`, move `s`. Credit/liquidity-spread risk.

They are separated because in the real world they are driven by different things and often
move **in opposite directions**: in a panic, Treasuries rally (`z` down) while spreads blow
out (`s` up). One combined number would cancel them and show nothing. And you hedge them with
different instruments.

⚠️ **But in Tier 1 they come out identically equal, and that is not a bug.** The price depends
only on the sum `z + s`, so with fixed cash flows, bumping either dial by 1bp is the same
arithmetic. `tests/test_observed_paydown.py` asserts the equality *as a property*, so that the
day a generator makes cash flows respond to rates, that test is the one that notices.

⭐ We already have a live example of the separation in our own book: **an FRN's duration is
≈ the time to its next reset (near zero), because bumping the curve re-projects its future
coupons — while its spread duration is ≈ its full remaining life.** Same bond, two very
different numbers, and the difference exists *only because the cash flows move*.

### 3.5 Why an I/O strip has negative duration — and why Tier 1 cannot see it

An interest-only strip's rate sensitivity has **two** parts pulling opposite ways:

1. **Discounting** — rates up, present value down. Negative price effect ⇒ *positive* duration.
2. **Prepayment response** — rates up, refinancing slows, the notional survives longer, **more
   interest arrives** ⇒ *negative* duration.

For an I/O, part 2 dominates. ⚠️ **Tier 1 holds the cash flows fixed, so it can only see part
1.** Measured over the 74 I/O strips in this book that price: **74 of 74** come out with a
positive duration, while **49** of their custodian durations are negative. That is not noise —
it is structurally the wrong sign, and no amount of care inside Tier 1 fixes it.

### 3.6 The custodian price does more work than it looks

Because the spread is **solved** so that the model reproduces the custodian's price, the
price is right **by construction** — exactly, not approximately. So for the whole structured
book, Tier 1 gets **market value, exposure and concentration right today**. What it gets
wrong is ΔP under a shock. ⭐ That is a much narrower claim than "Tier 1's results are bad",
and it is the reason the order is defensible.

⚠️ The matching limitation: using what *actually happened* is **hindsight**. It gives the
return the holder really earned, not the spread the market was demanding in March 2009. For
ordinary amortising paper the effect is modest. For an I/O — a pure bet on prepayment — it is
severe, which is the other half of why I/O spreads come out between −56,670 and +6,719 bp.

### 3.7 "The spread is a state variable"

Mario's slide 14, verbatim: *"the spread is not the risk number. It is a state variable. Ryse
simulates its movement, reprices the security in every scenario, and the resulting price
distribution is the risk."*

⭐ Meaning: the Monte Carlo does not treat the calibrated spread as the answer. It takes `s₀`
as a *starting point*, simulates the curve and the spread moving together, reprices everything
in every scenario, and the **distribution of prices** is the risk. From that distribution come:

* **VaR** — the loss you exceed only x% of the time (e.g. the 5th-percentile loss).
* **Expected Shortfall** — the *average* loss in that bad tail, which is the more honest
  number because it does not stop at the threshold.
* **Stress loss** — the loss under one specific chosen scenario rather than a distribution.

⇒ **consequence for us:** the Tier-1 output must be something a simulator can *perturb and
re-price*, not a scalar in a report. That decides the output schema, so it gets decided before
the first row is written.

---

## 4. ⭐ Five numbers that are easy to confuse

This is the section to come back to, because four of them nearly match and mean different
things.

| number | what it is | source |
|---:|---|---|
| **2,260** | every security in the portfolio | master, deduped |
| **949** | securities in the **six completed** classes | 732+147+39+15+9+7 |
| **766** | of those 949, the ones the engine **prices** | reproduced exactly: 555 corporate + 3 callable + 147 govt/muni + 61 agency/guaranteed/linker. 949 − 766 = **183** unpriced, matching his slide |
| **1,294** | the whole **structured** book | 882 MBS + 264 CMO + 69 CMBS + 79 ABS |
| **756** | **our own earlier figure** for the subset we said needed deal data | 344 MBS tranches + 264 + 69 + 79 — a *subset*, not a class total |

⚠️ **`766` is not the structured book**, which is the natural first reading. It is "priced
inside the finished classes". Always name the population.

⭐ And the number this week's work is built on — **858 of 882**, and where it comes from.
**505** securities the pool driver already prices (478 spot pools + 27 TBA forwards). **376**
have a measured factor path. **20** are in both, because validation pools were put into the
request on purpose so the new method could be checked against the old. 505 + 376 − 20 = **861**,
which is what the plan said. The run delivered **858**: three securities have a factor path
with nothing left in it — two whose factor is already zero on the valuation date, one whose
path produces no net cash at all — and **no estimate could have known that before reading the
path**. The other **24 − 3 = 21** named rows are 19 with neither a path nor a usable pool
coupon, and 2 forwards whose description does not state a settlement month.
⭐⭐ The 20 that make the addition fail to balance are the 20 that proved the method works.

---

## 5. What we measured before agreeing to any of it

| | finding |
|---|---|
| **Tier-1 inputs** | ⭐ **1,255 of 1,294 (97%) already carry coupon, frequency, maturity and par** in the custodian master; frequency is Monthly for 1,253. ⚠️ But a *rate* is not a *structure* — `income_rate` cannot say whether the coupon moves, and that one bit decides whether a floater gets a duration of ~0 or of its maturity. |
| **the floating unknown, priced** | ⭐⭐ On an amortising realised path the principal timing is already right, so only the interest leg is in doubt — **15.3% of PV (p90 36.7%) over a 2.73y life ⇒ at most ~1.8 years of duration error**, against ~21 for bulleting. **This is why this round did not wait for Liping.** |
| **the amortising 221** | ⭐ duration median **2.61y** against the custodian's own **2.39y** — 0.22 years apart, two independent sources agreeing. 216 of 221 inside a sane spread band. |
| **the I/O 74** | ⚠️ not usable as risk numbers — see §3.5. |
| **C.L.O.s** | ⚠️ **zero** in the portfolio: no `CLO`, `CDO` or `CBO` anywhere in 2,260 descriptions, and no such sub-category. He names them twice. |
| **Agency Securities** | ⚠️ **Complete on his own slide 7.** Its only real gap is one security (`TNTD04733316`, a REMIC Z misfiled as an agency debenture). |
| **Futures + options** | ⚠️ scope moved without agreement: *out of scope* in our records since July, "the only thing left" in his message. 16 securities, and a **new engine**, not a data gap. |
| **slide 6's chart** | ⭐ it is **ours** (the same chart on the same slide of `Ryse Presentation v3/v4/v5`), with our last two buckets merged: `Scoped 412` + `Out of scope 17` → `Not yet built 429`. The distinction we drew on purpose was lost in the artwork — the same drift as the row above, visible in a picture. |

---

## 6. Why Tier 1 first, when its numbers are knowingly worse

The full argument is in the decision record §3.6. In short, and in order of how much each
reason actually explains:

1. ⭐⭐ **Risk aggregation needs coverage, not precision.** A portfolio VaR over 43% of a book
   is not a less-accurate VaR — it is not a VaR. It cannot be aggregated or compared.
2. ⭐⭐ **Tier 1 and Tier 2 differ only in the cash-flow generator** (his slide 18 puts the two
   equations side by side). So Tier 1 is the chassis, not throwaway work.
3. ⭐ **It unblocks other people** — the parallel-computing handoff cannot be built or tested
   while 57% of the book emits nothing.
4. ⭐ **The level is exact by construction** (§3.6).
5. ⚠️ **And a commercial reason worth naming:** one deck is titled *"**Defensible** Structured
   Risk Methodology"*, with academic citations and an explicit "what this does not capture"
   slide. "Defensible" names the audience — someone who will challenge the method.

⚠️ **The risk in the order, and it is ours to watch:** a Phase 2 that is always next quarter.
Tier 1 reaching "coverage complete" is exactly when the pressure to fund Phase 2 disappears.
He guarded against it in writing, but **a slide is not a commitment of anybody's time.**

---

## 7. The academic backing he cites

| for | works |
|---|---|
| reduced-form credit; a market-implied spread as a representation of credit risk | Jarrow & Turnbull (1995) · Duffie & Singleton (1999) |
| MBS/ABS with uncertain principal; OAS via Monte Carlo | Dyer (2019) · Green (2014) |
| ⭐ **historical prepayment estimation feeding valuation** — i.e. Phase 2 | Schwartz & Torous (1989) · Richard & Roll (1989) · Kang & Zenios (1992) |

⭐ Both reference slides disclaim honestly: *"these sources support the methodological
building blocks; they do not describe the exact Ryse Phase 1 implementation."* Worth matching
that register in anything we build on top.

⚠️ And his slide 22 carries a limitation we must not lose: `ΔPrincipal = scheduled principal +
prepayment + default/write-off`. **Our factor path gives total paydown only.** Splitting
prepayment from default — needed for CDR and severity in Phase 2 — requires fields that
separately identify defaults and recoveries, which may not exist for 2009 private-label paper.

---

## 8. Glossary

| term | meaning here |
|---|---|
| **factor** | fraction of original balance still outstanding; one number per month |
| **WAL** | weighted average life — the average years until each unit of principal returns |
| **CPR / SMM** | annual / monthly prepayment rate. `SMM = 1 − (1−CPR)^(1/12)` |
| **PSA** | a prepayment convention; for a seasoned pool `CPR ≈ 0.06 × PSA/100` |
| **bullet** | all principal repaid on one day |
| **amortising** | principal repaid gradually |
| **I/O · P/O** | interest-only · principal-only strip |
| **accrual (Z) tranche** | adds its interest to its own balance; factor can rise above 1 |
| **DV01 · CS01** | price change per 1bp of base rate · per 1bp of spread |
| **implied / bond-equivalent spread** | the flat spread that reprices the model to the observed price. ⚠️ **Not an OAS** — his own slide 13 draws the line, because an OAS requires modelling option-dependent cash flows |
| **VaR · Expected Shortfall** | the loss exceeded x% of the time · the average loss beyond it |
| **Intex** | the commercial deal-model engine Phase 3 would buy |
| **T+1** | the custodian strikes its figures one day after the valuation date, so Bloomberg's `2009-04` column is the 2009-03-31 position |
