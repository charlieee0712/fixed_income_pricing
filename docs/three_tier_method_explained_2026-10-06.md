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
   **prepaying** at about **20% a year** — and since that sits on top of the schedule, the
   balance itself fell by about **25% a year**.

⚠️⚠️ **Those two numbers are one measurement under two definitions, and keeping them apart
matters far more than it looks.** "How fast did the balance fall" and "how fast did people
prepay" differ by the scheduled leg — which is almost nothing on a fresh 30-year pool and
very large on one near the end of its life. **§3.10** is what happens when the distinction is
lost: an engine parameter was set from the first and is consumed as the second.

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

⚠️ **With one exception, and it is already in this book.** The equality holds on the **757**
Tier-1 rows priced before the forwards — maximum difference **exactly 0.0** — and **fails on
the 27 TBA forwards**, where the two differ by precisely the settlement lag. Not because
their cash flows respond to anything, but because a forward price carries the spread in only
one of its two places. See **§3.8**.

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

⭐⭐ **And the I/O carries this doc's sharpest process lesson: two questions wore one name.**

| the question | answered by | verdict |
|---|---|---|
| **Identity** — is `par` a notional? is the price per 100 of notional? is there a principal leg? | 8 pilot cases | ⭐ **settled, positively** |
| **Usability** — may a spread and a duration be published? | the full 74 | ⚠️ **refused** |

A price of **8.151** per 100, against **103.850** for an ordinary tranche, can only be a claim
on a *notional* — and all 8 pilot cases calibrated to a finite positive spread under an
interest-only treatment. So `interest(t) = 100 · f(t−1)/f₀ · coupon/12` with **no principal
term** is the right decomposition, and that conclusion still stands.

⚠️ **The pilot was then read as having answered the second question too, and the population
refuted it the same day.** 8 samples can establish what a security *is*; only the population
can establish whether a number about it is *publishable*. ⇒ the rule this book now carries:
**publish a risk number only when its sign is known to be right.** Price and market value
ship (exact, being calibrated to the custodian's own mark); spread and duration ship **blank**,
with the custodian's own duration in its own column as evidence.

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

### 3.8 The TBA forward, and the one place DV01 and CS01 really do differ

**TBA = "to be announced."** A contract to buy an unspecified pool of a given issuer, term and
coupon on a stated settlement date — **which pools actually deliver is announced 48 hours
beforehand**, which is what *generic* means. It is how the mortgage market mostly trades. This
book holds 27 that price: **20 settling 2009-04-15** (15 days out) and **7 on 2009-05-15** (45).

Two consequences follow, and neither is a new assumption.

**① A generic pool is priced as a typical new issue** — WAC = coupon + 0.50 (servicing and
guarantee fee), the full original term, the book CPR. ⭐ And the unknown was **measured to be
worth 0.1 bp**: moving the WAC from coupon+0.50 to coupon+1.00 moves the calibrated spread by
one tenth of a basis point. The thing we do not know turns out not to matter.

**② The price is a forward, which is arithmetic off the spot curve, not a second model:**

```
F · DF(0,u)  =  PV₀( the cash flows that begin at u )      ⇒   F = PV₀(flows) / DF(0,u)
```

You pay at `u`, so you do not fund the position until then, and the price is grossed up by the
financing cost over the lag. Only the valuation-date curve is used — **no forward curve is
built** — and at `settle == valuation` the wrapper delegates to the spot path bit-for-bit, so
this is a forward *on* the pool engine rather than a second engine beside it.

⭐⭐ **And this is where §3.4's equality breaks, because the spread sits in the numerator only:**

```
F(d) = [ Σ cᵢ · e^{−(tᵢ+u)(zᵢ + d + s)} ]  ⁄  e^{−u(z(u) + d)}
                  ↑ rate d AND spread s             ↑ rate d only
```

Differentiating `log F` in `d` picks up `+u` from the financing leg; differentiating in `s`
does not, because that leg carries the rate and not the spread. So, **exactly**:

```
rate_duration  ==  spread_duration  −  settle          measured residual on the real 27: 9.99e-09
```

In words: **a rate move changes both what the pool is worth and what it costs to finance it to
settlement; a spread move changes only what it is worth** — and the gap between the two
sensitivities is the financing period itself.

⚠️ **One row, one bump kind.** `eff_duration` / `dv01` / `convexity` come from the rate bump and
`cs01` from the spread bump; a rate duration beside a spread convexity cannot be combined into
an approximate move, even though everywhere else in this book they are interchangeable.

### 3.9 ⭐ Why the duration is the number that has to be right

Everything in this tier comes out of one equation with three objects in it:

```
BT  =  Σ_t  CF(t) · exp( −t · ( z(t) + s ) )               ← solved for s
```

* `BT` — the custodian's price. **Given.** We did not produce it.
* `CF(t)` — the cash flows. **Assumed** — a measured factor path, or a CPR.
* `s` — the spread. **Solved**, so that the equation balances.

⭐⭐ **So the spread is a plug.** If `CF(t)` is wrong, `s` absorbs the error and `BT` is still
reproduced *exactly* (§3.6). ⇒ **the price cannot detect a cash-flow error, and the spread is
where such an error goes to hide.** Neither of them is a test of anything.

The duration is the only one of the three that is a **prediction** — it states what happens
under a state of the world that has not occurred. That is why it is the deliverable, and it is
not our framing: the 2026-06-30 redefinition with Mario made the spread *"a per-bond
calibration factor, not a pricing input"*, with **"goal = risk metrics; implied OAS is the
intermediate."**

It is also the only one carrying a **materiality threshold** anywhere in this project: a
model-versus-custodian duration divergence beyond **1.5 years** gets reported with both numbers
(corporate callables, the sovereign book, 5 of the 27 forwards, 102 of 478 spot pools). There is
no comparable basis-point tolerance for the spread. ⭐ The book already decided which number is
load-bearing, by giving one a tolerance and the other none.

⚠️ **Do not over-learn this into "the spread is noise."** Three places its *level* still carries
meaning: **relative value** (anyone ranking pools by spread mis-ranks every row whose cash-flow
assumption is off), the **cross-generator validation** (§5's 261.3 bp against 250.9 bp is a
claim about spread *levels*, so it is precisely the claim a cash-flow error contaminates), and
any sanity band keyed on a spread. ⭐ For the Monte Carlo (§3.7) the right distinction is
sharper still: the spread's **level** is a plug, but its **sensitivity** is the risk — `CS01` is
a PV-weighted average time and barely moves when `s₀` shifts by tens of basis points. So a level
error of that size does not propagate into the simulated price distribution the way it
propagates into a league table.

### 3.10 ⚠️ `BOOK_CPR_PCT = 25.0` — a measurement that changed meaning on the way in

The **458** pass-through rows with no factor path all take one book-wide prepayment speed. It
was **measured, not chosen**: the **32** securities that are pass-throughs *and* hold a real
path realised a whole-life median **25.05%** and a forward-12-month median **25.83%**. Both
reproduce exactly on re-measurement, and 25 is already the centre of the pricing grid.

⚠️⚠️ **But what was measured is total factor decay, `1 − f₁₂/f₀`, and the engine's `cpr`
argument is a prepayment rate.** They differ by the **scheduled** leg — the principal every
monthly payment returns by contract whether or not anybody prepays (§3.1).
`core/pricing/prepayment.py` amortises *first* and prepays only the survivor:

```
pay    = B·g / (1 − (1+g)^(−rem))            g = WAC/12,  rem = months remaining
sched  = pay − B·g  =  B · g / ((1+g)^rem − 1)
prepay = (B − sched) · SMM                   ← the cpr acts on what the schedule left behind

⇒  total decay  =  scheduled  +  prepayment on the survivor
```

So feeding a *decay* number in where a *prepayment* number is expected double-counts the
schedule. Netting each pool's own scheduled leg off its own observed decay gives **19.15%** —
which is exactly the figure the 2026-10-01 record carries for the same horizon on the same
pools. ⭐ **Two definitions under one word, not two populations.**

**⭐ Why this is specifically a short-pool problem, in one formula.** The scheduled fraction
retired per month is `g / ((1+g)^rem − 1)`, which tends to **0** as `rem` grows and to
**`1/rem`** as `rem` shrinks — so it is negligible on a fresh pool and dominant on an old one:

| months remaining | scheduled leg, annualised (WAC 6.44%) | `cpr` reproducing a 25.83% decay |
|---:|---:|---:|
| 288 (24 years) | **1.7 %** | **24.5 %** ⭐ so 25.0 is right here |
| 120 (10 years) | 6.9 % | 18.7 % |
| 60 (5 years) | 15.7 % | **~10.8 %** ⚠️ |

The population that takes the assumption is **long** — median WAM **287 months** — so for the
typical row gross ≈ net and `25.0` survives. For the **46 rows under six years** it is roughly
**14 points too fast**: the engine is told to prepay a balance that is already leaving on
schedule.

**⭐ And why that lands on the spread rather than the duration.** These are **premium** pools
(BT > 100): you paid above par for an above-market coupon, so prepayment hands par back early
and *destroys* the premium. At any fixed spread, therefore,

```
P > 100   ⇒   ∂P/∂cpr < 0   ⇒   ∂s*/∂cpr < 0        (BT is pinned, so s* must tighten)
```

Measured in both directions: 19% → 25% costs **−14.25 bp** of median spread across the 458, and
correcting the 46 shortest rows to their own equivalent speed gives **+46.73 bp** back. Meanwhile
a five-year pool's duration is bounded by its five years whatever the speed — so the error is
**large in percentage points and small in years**:

| WAM band | n | equivalent `cpr` | Δ spread | Δ duration | max \|Δ dur\| |
|---|---:|---:|---:|---:|---:|
| < 72 m (under 6 years) | 46 | 10.79 % | **+46.73 bp** | +0.444 y | 0.489 |
| 72–120 m | 63 | 18.65 % | +19.12 bp | +0.381 y | 0.427 |
| 120–240 m | 69 | 22.31 % | +6.94 bp | +0.202 y | 0.383 |
| ≥ 240 m (the bulk) | **280** | 24.68 % | +0.20 bp | +0.032 y | 0.138 |

**0 of 458 rows move as much as the 1.5-year threshold** — median 0.055 y, worst 0.489 y. ⇒ read
through §3.9: **the deliverable survives everywhere; the diagnostic column does not, on 46 rows.**

⚠️ **And their slowness is partly real, not purely an artefact of the units.** Those short pools
carry WACs of **3.5–5.3%** against roughly 5% mortgage rates in March 2009 — out of the money,
genuinely not refinancing. Their low equivalent speed is therefore part schedule and part
economics, which is what makes §3.11's second option harder than it first looks.

⭐ **The cross-check already contained the signal.** §5's validation reads observed-path median
**261.3 bp** against assumed-CPR **250.9 bp** and reads the 10 bp as agreement. But a too-fast
assumed speed on a premium pool tightens the spread by exactly that sign and roughly that size.
⚠️ They are two different populations, so this is **consistent with** an assumption a few points
fast — not a decomposition of the 10 bp.

### 3.11 The three ways out of §3.10 — and why it is a direction, not a cleanup

⚠️ **Nothing has been changed.** `BOOK_CPR_PCT` is still 25.0 and all 882 published rows are
untouched. The options, with what each one actually buys:

| option | what changes | what it fixes | ⚠️ what it leaves |
|---|---|---|---|
| **1 · keep 25.0, name the tail** | no number at all; the record stops calling a decay a CPR, and the 109 rows under 120 months (15.4% of these rows' par) are named | the honesty, at zero cost — no re-run, no new hashes. And it *is* Mario's own standing rule from 2026-07-30: every gap sits on a table | the 47 bp on 46 rows |
| **2 · derive the speed per pool** | each of the 458 takes the `cpr` reproducing a 25.83% decay at its **own** WAC and WAM — long rows move under a point, short rows 10–14 | the tail's spread, without disturbing the 280 long rows | ⚠️ it still assumes a single *decay* rate for everyone. Done honestly it must be **WAC-dependent**, because that is *why* the short pools are slow — and a WAC-dependent speed **is a prepayment model, i.e. Tier 2** |
| **3 · one book-wide net number** | one constant | the median, by half a point — worth **1.3 bp and 0.06 y**. Inert | ⚠️ the tail, exactly as wrong: the error is per-pool and no constant can carry it. And the tempting value, **19.15%**, is actively *worse* — it is a 20-pool median dragged down by its own short members, and applied book-wide it moves the **280 long rows** by +14.25 bp and **+0.675 y of duration**. It breaks the majority, in the one column that is currently intact |

⭐⭐ **So the real question is not which number to use.** Options 1 and 3 are Tier-1
housekeeping. **Option 2, done properly, is the first step of Tier 2** — because "prepayment
response estimated from history" is precisely what his slide 19 lists under *Existing
Engineering Work*, and a WAC-dependent speed is that and nothing less. The decision is whether
to open that axis now or ship Tier 1 with the gap named.

⚠️ One thing is a correction rather than a choice, and is separable from all three: four places
in the record (`docs/bloomberg_return_2026-10-01.md` §B, `CLAUDE.md`, `WORKLOG.md`,
`scripts/tier1_structured.py:124`) describe the 25.05 / 25.83 as a *realised CPR*. They are a
realised **decay**. Same class of fix as 376 → 373: the word, not the method.

### 3.12 The floating-coupon unknown, and why 1.77 years is the whole of it

`income_rate` reports a *rate*, never a *structure*, so for **104 of the 376** nothing in the
custodian file says whether the coupon floats — and that single bit normally decides whether a
security's duration is ~0 or its whole remaining life. Liping's coupon history would settle it,
and she is not expected at a terminal for some time.

⭐ **On an amortising observed path the question shrinks, because the principal timing is already
fixed by the path.** A measured factor series is a record of what happened; it does not depend
on whether the coupon floated. So only the **interest leg** is in doubt, and its share of PV
bounds the whole error:

```
error  ≤  w_int × L_int            w_int = the interest leg as a share of PV
                                   L_int = its PV-weighted average life

                 median     p90                              (n = 214)
   w_int         15.3 %     36.7 %
   L_int         2.73 y     4.83 y

   bound   =  36.7 % × 4.83 y  =  1.77 years     ⚠️ both at p90, on purpose
   median  =  15.3 % × 2.73 y  ≈  0.42 years
```

Conservative twice over: it takes the p90 of *both* factors simultaneously, and it assumes the
true floating-leg duration is exactly 0 — which is itself the generous end, since a floater's
coupon rises with rates and its PV therefore barely moves (the same mechanism that makes an
FRN's duration ≈ its time to next reset, §3.4).

⇒ against the **~21 years** that bulleting at legal maturity costs (§3.3), the unknown is worth
about a twelfth of the defect being repaired. ⭐ **That is why this round did not wait for
Liping** — and why her pull, when it lands, improves the answer by at most ~1.8 years rather
than unblocking it.

---

## 4. ⭐ Numbers that are easy to confuse

This is the section to come back to. **Five counts** first, four of which nearly match and mean
different things — then **four prepayment rates wearing one word**.

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

⭐ **And four prepayment numbers wearing one word** — the subject of §3.10:

| number | what it actually is | population |
|---:|---|---|
| **25.05 % / 25.83 %** | **total factor decay**, whole-life / forward-12-month — schedule **and** prepayment together | the 32 pass-throughs holding a real path |
| **19.1 %** | the same horizon **net of the schedule** — a true prepayment rate | the 20 validation pools |
| **24.45 %** | the `cpr` that *reproduces* a 25.83% decay at the median remaining term | the 458 that take the assumption |
| **25.0** | `BOOK_CPR_PCT` — the parameter in the code | applied to those 458 |

⚠️ The first two differ by a **definition**, not by population, which is why both are correct
and why one of them is in the wrong place. The third is the first one *translated* for the
population it is applied to; the fourth is what is published.

---

## 5. What we measured before agreeing to any of it

| | finding |
|---|---|
| **Tier-1 inputs** | ⭐ **1,255 of 1,294 (97%) already carry coupon, frequency, maturity and par** in the custodian master; frequency is Monthly for 1,253. ⚠️ But a *rate* is not a *structure* — `income_rate` cannot say whether the coupon moves, and that one bit decides whether a floater gets a duration of ~0 or of its maturity. |
| **the floating unknown, priced** | ⭐⭐ On an amortising realised path the principal timing is already right, so only the interest leg is in doubt — bounded at **36.7% × 4.83y = 1.77 years** (p90 on both factors), against ~21 for bulleting; median case ≈ 0.42y. **This is why this round did not wait for Liping.** Derivation in **§3.12**. |
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
| **CPR / SMM** | annual / monthly **prepayment** rate. `SMM = 1 − (1−CPR)^(1/12)` |
| **total factor decay** | `1 − f₁₂/f₀` — how far the balance fell, schedule **and** prepayment together. ⚠️ **Not a CPR**, and the difference is the whole of §3.10 |
| **WAC · WAM** | weighted average coupon · weighted average maturity of the loans inside a pool |
| **PSA** | a prepayment convention; for a seasoned pool `CPR ≈ 0.06 × PSA/100` |
| **bullet** | all principal repaid on one day |
| **amortising** | principal repaid gradually |
| **scheduled amortisation** | the principal each monthly payment returns by contract, prepayment aside. Its monthly share of the balance is `g/((1+g)^rem − 1)` ⇒ ≈ 0 on a long pool, ≈ `1/rem` on a short one |
| **premium pool** | one priced above par, because its coupon beats the market rate. Prepayment returns par early and destroys the premium ⇒ **faster prepayment makes it worth less**, which is why a too-fast assumption comes out as a too-tight spread |
| **I/O · P/O** | interest-only · principal-only strip |
| **accrual (Z) tranche** | adds its interest to its own balance; factor can rise above 1 |
| **DV01 · CS01** | price change per 1bp of base rate · per 1bp of spread |
| **rate duration · spread duration** | from bumping the curve · from bumping the spread. Identical everywhere in this book **except** the 27 TBA forwards, where they differ by exactly the settlement lag (§3.8) |
| **TBA** | *to be announced* — a forward on an unspecified ("generic") pool of a given issuer, term and coupon; the pools that actually deliver are named 48 hours before settlement |
| **implied / bond-equivalent spread** | the flat spread that reprices the model to the observed price. ⚠️ **Not an OAS** — his own slide 13 draws the line, because an OAS requires modelling option-dependent cash flows |
| **VaR · Expected Shortfall** | the loss exceeded x% of the time · the average loss beyond it |
| **Intex** | the commercial deal-model engine Phase 3 would buy |
| **T+1** | the custodian strikes its figures one day after the valuation date, so Bloomberg's `2009-04` column is the 2009-03-31 position |
