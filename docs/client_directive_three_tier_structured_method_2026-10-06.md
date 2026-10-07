# Mario's three-tier method for the structured book — 2026-10-06

**Provenance.** A phone call with Mario (Lichen), two decks dropped into `docs/` at 09:41,
and one follow-up message quoted verbatim in §2. ⚠️ As with
`client_directive_browser_azure_architecture_2026-09-26.md`, the call itself is **Lichen's
recollection** and is marked as such; the decks are primary and every claim sourced to a
slide below was read out of the file.

| file | slides | what it is |
|---|---:|---|
| `Chapter_VIII_Fixed_Income_Pricing_with_Structured_Securities_Method.pptx` | 15 | the shorter deck — **and the FRESHER status** |
| `Ryse_Fixed_Income_Pricing_Defensible_Structured_Risk_Methodology.pptx` | 27 | the full methodology, with the academic references |

⚠️ **They are not "the same deck, one longer".** Two differences matter:
- **Slide 7 status column.** Ch-VIII marks Non-Government CMOs / ABS / CMBS as **`WIP`**
  and leaves Futures/Options blank; Defensible marks all five **`Scoped, not started`**.
  ⇒ **Ch-VIII is the later edit. Quote its status, not the other's.**
- **Slide 11 attribution.** Ch-VIII reads "**Mario's** recommendation", Defensible reads
  "**Ryse** recommendation" — i.e. Ch-VIII is the internal copy, Defensible the
  client-facing one.
- ⚠️ **THE TWO DECKS NUMBER DIFFERENTLY AND BOTH HAVE A SLIDE 13, SAYING DIFFERENT THINGS.**
  Ch-VIII 13 is the **Tier-2** slide ("Next Round — Use Bloomberg…", where *"replace
  legal-maturity bullet behavior"* lives); Defensible 13 is **Step 1**, the calibration slide
  that carries the terminology lock. They share slides 9–12 almost verbatim and diverge after.
  ⇒ **never cite a bare slide number** — say which deck. Mapping for the ones we quote:
  Tier ladder = **11 both** · Tier-1 flow = **12 both** · terminology lock = **Defensible 13**
  · spread-as-state-variable = **Defensible 14** · Tier 2 / "replace…bullet" = **Ch-VIII 13 =
  Defensible 19** · "tiers differ only in the generator" = **Defensible 18** · econometrics =
  **Defensible 22–24** · Tier 3 optional = **Ch-VIII 14 = Defensible 25**.

---

## 0. The call itself, in Lichen's words — and each point checked against a slide

⚠️ **Recorded here because it was nearly lost.** It lived only in the conversation until
2026-10-07; a context compaction elided it to an ellipsis and nothing in the repo carried it.
It is a **recollection**, reproduced as given, and the check column is the only reason any of
it may be quoted.

> 我凭和他讨论的印象说 具体的细节你可以细看slides确认
> 1. 他说把这些type也先当成bullet bond 他说price不是重点 因为我们有custodian
>    先calibrate算出oas 再算一系列risk metrics才是我们这个项目的重点
>    他的意思是先把这几类用简单的方法做好 做到只剩futures options那几类小的
>    之后再回过头用方法2来优化
> 2. 也就是我说的方法2 他说是我们之前propose出的处理方法的变体 结合econometrics
>    method to estimate payment timeline and other inputs etc. so that we can imprive
>    accuracy than method 1
> 3. 用intex clients有这个具体需求的时候再想办法弄。

In English, and then checked:

| what was recalled | checked against the file | verdict |
|---|---|---|
| slides from 10 on are the plan for the classes not yet done | **slide 10 title is literally** `MBS ABS CMO CMBS CLO` | ✅ |
| **treat these types as bullet bonds first** | ⚠️ **the Tier-1 definition does not say this.** Slide 12 (both decks) reads `Custodian Market Price → Bloomberg Contractual Terms → **Bond-Equivalent Cash Flows** → Calibrate Implied Spread → Shock Rates + Spreads`, and its own limits list is *"cash flows do not yet respond explicitly to CPR, defaults, extension/contraction or waterfall rules"*. The word **bullet** occurs only on the **Tier-2** slide, in *"replace legal-maturity bullet behavior"*. See §3.2 and §4.1. | ⚠️ **partly** |
| price is not the point — calibrate the spread, then the risk metrics | Defensible 13: the custodian price is the anchor, `P₀ = Σ CFₜ × DF(zₜ + s*)`, and the output is a distribution of ΔP → VaR / ES / stress | ✅ |
| finish the simple classes until only futures + options remain | the follow-up message says exactly that, verbatim in §2 | ✅ |
| method 2 is a variant of **our own earlier proposal**, plus econometrics for the payment timeline | slide 11: *"Build on the historical Bloomberg extraction already developed by Lichen"* (Ch-VIII wording; Defensible drops the name). Defensible 22–24 estimate `CPR = f(refi incentive, seasoning, seasonality, burnout)` from history | ✅ |
| method 3 only when a client specifically needs it | Ch-VIII 14 / Defensible 25: **OPTIONAL**, *"only when the analytical requirement justifies the cost"* | ✅ |

⭐ **The one correction the decks make to the recollection is the load-bearing one**, and it
runs in our favour: *bond-equivalent* is not *bullet*. An observed monthly factor path is a
fixed schedule that responds to nothing — it satisfies slide 12's definition of Tier 1 in
full, including both of its stated limits.

---

## 1. The three tiers, as the slides define them

Slide 11 (both decks) and slide 21 (Defensible) carry the same ladder. Each tier keeps
**the observed custodian price as the valuation anchor** — that is the thread through all
three.

| | tier | what it does | status per Mario |
|---|---|---|---|
| **1** | **Reduced-Form Market Risk** | custodian price as anchor · **simplified bond-equivalent cash flows** · calibrate an implied spread · then shock rates and spreads | **"implement Level 1 now"** |
| **2** | **Bloomberg + Empirical Enhancement** | "build on the historical Bloomberg extraction **already developed by Lichen**" · principal paydowns, WAL · improve prepayment / contraction / extension **empirically** | next round; *"improves the reduced-form model rather than replacing it"* |
| **3** | **Full Structural Model** | collateral, CPR/CDR, severity, waterfalls, scenario-dependent tranche cash flows · true OAS | optional, use-case driven — **Intex** |

### 1.1 Tier 1, precisely (Defensible slides 13–15)

```
calibrate   P₀ = Σₜ CFₜ × DF(zₜ + s*)        choose s* so model price = custodian price
reprice     Pᵢ = Σₜ CFₜ × DF(zₜ,ᵢ + s* + Δsᵢ)
risk        ΔPᵢ = Pᵢ − P₀   →   VaR · Expected Shortfall · stress loss
DV01 ≈ [P(z−1bp, s*) − P(z+1bp, s*)] / 2        (hold the spread, move the curve)
CS01 ≈ [P(z, s*−1bp) − P(z, s*+1bp)] / 2        (hold the curve, move the spread)
```

⭐⭐⭐ **THE TERMINOLOGY LOCK — slide 13, verbatim:** *"in the initial Ryse model this is
best called an **implied or bond-equivalent spread**. A true OAS requires explicit
modeling of option-dependent cash flows such as prepayments."*
**Mario wrote that. So `implied_oas` on a structured tranche would contradict his own
deck.** We already have the precedent and the enforcement pattern:
`implied_spread_vs_nominal_bp` is banned from being renamed `implied_oas`, by a test that
injects the banned name and fails (mutation-verified, 2026-09-10). **The Tier-1 column gets
the same treatment, named before the first row is written.**

⭐ **Slide 14 — the spread is a STATE VARIABLE, not the answer:** *"the spread is not the
risk number. It is a state variable. Ryse simulates its movement, reprices the security in
every scenario, and the resulting price distribution is the risk."* ⇒ **the Tier-1 output
must be something a simulator can perturb**, not a scalar in a report. That shapes the
schema, so it is decided before the first row too.

### 1.2 Tier 2 is our factor work, named as such

Slide 19 (= Ch-VIII slide 13) lists under **"Existing Engineering Work"**: *historical
monthly principal repayments · observed realized cash-flow behavior · **existing validation
against pools priced by another method** · infrastructure for Bloomberg-based data
extraction*, under the heading *"The historical work already completed becomes the
empirical enhancement layer — **not discarded work**."*

⭐ That is a line-by-line description of what we built and validated on 2026-10-01/02
(factor route, principal conservation 1.28e-13, 8.2 bp against the existing engine on 14
in-grid pools). **Mario has placed it as Tier 2 and committed to it in writing.**

Defensible slides 22–24 give the econometrics: `SMM → CPR`, `MDR → CDR`,
`Severity = 1 − Recovery`, then `CPR = f(refinancing incentive, seasoning, seasonality,
burnout)` estimated from history and evaluated inside each scenario.
⚠️ **And slide 22 carries its own honest limit, which we must not lose:** *"ΔPrincipal
alone = scheduled principal + prepayment + default/write-off effects. CPR, CDR and severity
should only be estimated separately when the Bloomberg/collateral fields permit
identification."* ⇒ **our factor path alone cannot separate prepayment from default.** It
gives total paydown. Splitting it needs fields we have not asked for and may not exist for
2009 private-label paper.

### 1.3 The academic foundation (Defensible 16–17, 24, 26)

| tier | cited for | works |
|---|---|---|
| 1 | reduced-form credit, implied spread as a risk representation | Jarrow & Turnbull (1995) · Duffie & Singleton (1999) |
| 1→2 | MBS/ABS with uncertain principal, OAS via Monte Carlo | Dyer (2019) · Green (2014) |
| 2 | **historical prepayment estimation → valuation** | Schwartz & Torous (1989) · Richard & Roll (1989) · Kang & Zenios (1992) |

⭐ Slide 17 and 26 both disclaim honestly: *"these sources support the methodological
building blocks; they do not describe the exact Ryse Phase 1 implementation."* Worth
matching that register in anything we write on top of it.

---

## 2. Mario's follow-up message, verbatim

> as discussed Lichen, but please focus on Liping. With her BBG access, she can easily get
> the data for the Coupons structure, frequency, for all of those Gov MBS, Asset Backed S,
> Comercial Backed S, C.M.O.s and C.L.Os  oh I almost forgot, and Agency Securities. that
> will finish the gap. Only leaving us with the Futures and Options part. And Once that is
> done we continue with DEVELOPING Monte Carlo for the entire portfolio. ANd now we have
> the risk of the whole Fixed Income portfolio. Tell me if this is clear or not for you.

**The chain he is describing:**

```
coupon structure + frequency  (Liping, Bloomberg)
      ↓
Tier-1 bond-equivalent cash flows for the structured classes
      ↓
calibrate implied spread against the custodian price  →  DV01 · CS01
      ↓
coverage complete except futures + options
      ↓
Monte Carlo over (curve, spread) for the WHOLE portfolio
      ↓
portfolio VaR · Expected Shortfall · stress
```

**The chain is sound.** Everything below is about where our measurements change a step,
not about disputing it.

---

## 3. What we measured, before agreeing to anything

### 3.1 ⭐⭐⭐ 97% of the Tier-1 inputs are already on disk

Tier 1 needs coupon rate · payment frequency · a maturity · the custodian price. The
custodian master carries the first three:

| class | n | coupon | freq | maturity | par | **all four** |
|---|---:|---:|---:|---:|---:|---:|
| Government Mortgage Backed Securities | 882 | 882 | 851 | 868 | 877 | **846** |
| Non-Government Backed C.M.O.s | 264 | 264 | 262 | 264 | 264 | **262** |
| Commercial Mortgage-Backed | 69 | 69 | 69 | 69 | 69 | **69** |
| Asset Backed Securities | 79 | 79 | 79 | 79 | 78 | **78** |
| **total** | **1,294** | | | | | **1,255 = 97.0%** |

`pay_freq` is **Monthly** for 1,253 of them. So "get the coupons and frequency" is a
request for data we overwhelmingly hold.

⚠️ **This is NOT grounds for telling Mario the ask is unnecessary**, because a *rate* is
not a *structure*. `income_rate` is one number as of one date. It cannot say whether the
coupon is **fixed or moving** — and that single bit is load-bearing: a floater carried as a
fixed bullet gets a rate duration of roughly its maturity instead of roughly zero. ⭐ So
**the genuine Tier-1 gap is one classification bit per security**, which is exactly what the
2026-10-02 pack's `04_coupon_classify` (four dates) and `03_coupon_monthly` (the 156
measured suspects) were built to settle.

### 3.2 ⭐⭐⭐ The real Tier-1 risk is the MATURITY, and it is a factor of seven

A bond-equivalent needs a stated maturity. `maturity_master` is the **legal final**.
Measured against the realised cash flows on the 373 securities whose factor history we hold:

| | median | p10 | p90 |
|---|---:|---:|---:|
| legal life (years) | **24.32** | 8.97 | 28.15 |
| realised WAL (years) | **2.99** | 1.13 | 4.97 |
| legal ÷ WAL | **6.87×** | 3.05× | 16.43× |

**227 of 373 had fully repaid by 2026-09**, a median 5.5 years after the valuation date,
against a median legal maturity of 24 years.

⚠️⚠️⚠️ **A bullet at legal maturity overstates the cash-flow timing by ~6.9× — roughly
+21 years of duration on the median security.**

⭐⭐⭐ **AND THE DIAGNOSIS IS "BULLET", NOT "MATURITY" — checked, not reasoned.**
`core.pricing.prepayment.pool_cash_flows(wac, wam_months, cpr)` **amortises** over the
remaining term with SMM prepayment, and it takes `wam_months` from *the master's own
maturity dates* (`pool_risk.py` docstring, line 83). So the 505 pools already run on
exactly the maturity called wrong above — and their 10-01 validation was clean. What makes
a tranche wrong is not the date; it is that **a bullet puts 100% of principal on the final
day and an amortising schedule spreads it.**

⭐ That reframes the whole question, and favourably: **an amortising bond-equivalent is
still Tier 1** — fixed cash flows, one calibrated spread, no scenario-dependent CPR — and
**we already own the engine**, because it is the one pricing the 505. What a tranche needs
on top is a paydown profile, and there are three populations:

| population | n | where its paydown profile comes from |
|---|---:|---|
| Government-MBS pass-through pools | 505 | ✅ already done — level-pay + the measured ~20% CPR |
| tranches whose factor history returned | 373 | ✅ the **realised** path, in hand since 10-01 |
| CMO / CMBS / ABS | ~375 | ⚠️ **nothing yet — this is what sheet 02 buys** |

⚠️ Precedent already in the code for not trusting `maturity_master` blindly: TBAs take
their terms from the DESCRIPTION because *"the master's maturity is wrong for these (a 2009
thirty-year forward is carried as maturing 2034)"* (`pool_risk.py`).

⭐⭐ **Two slides point different ways, and the one that DEFINES Tier 1 is the one we follow.**
**Ch-VIII 13 = Defensible 19** (the Tier-2 slide) says Tier 2 will *"replace legal-maturity
bullet behavior with a more realistic effective-life representation"* — which implies its
author expected Tier 1 to be a bullet at the legal final, and Lichen's recollection of the call
(§0) says Mario put it that way outright. But **slide 12, the slide that actually specifies
Tier 1, never says bullet**: it says *Bond-Equivalent Cash Flows*, and states its own two
limits as *"cash flows do not yet respond explicitly to CPR, defaults, extension/contraction or
waterfall rules"* and *"sensitivities are therefore bond-equivalent risk measures"*. A realised
factor path is a **fixed** schedule — it is history, it responds to nothing — so it meets that
specification exactly, both limits included. Taken as a bullet instead, the same table would
publish portfolio durations ~7× too long for **57% of the book by count**, on the one output the
project exists to produce. (Mario, 2026-10-06, as recalled: *price is not the point — we
have the custodian — calibrating the spread and then the risk metrics is the point.*)

⭐ **Corroborated independently by the custodian.** Its own effective duration is present
on **1,290 of 1,294** and runs **median 2.05 years** against a 24.8-year median legal life
— the same order as our measured 2.99-year WAL, nowhere near 24. Two independent sources
agree the true life is short.
⚠️ But AQ is **not clean enough to drive** the choice: 70 negative, 83 zero, 40 over 15
years, and medians of 0.01 (CMO) / 0.06 (ABS) that cannot be effective lives. The standing
rule holds — *custodian duration is evidence in flag text, never a router* (2026-09-03).

### 3.3 Three scope facts that do not match the message

| | finding |
|---|---|
| **C.L.O.s** | ⚠️ **There are none.** Zero matches for `CLO`, `CDO` or `CBO` in any description across all 2,260 securities. The thirteen master sub-categories contain no CLO bucket. Mario names them twice (slide 10 header and the message). |
| **Agency Securities** | ⚠️ **Complete on his own slide 7** (39 securities, done 2026-09-10). Its only real gap is **one** security — `TNTD04733316`, the REMIC Z misfiled as an agency debenture, BT-marked since 2026-07-22. Two of the 39 also lack `pay_freq`. |
| **Futures + Options** | ⚠️ **The scope moved and nobody agreed it.** `CLAUDE.md` has carried *FI Derivatives + Other = out of scope* since July. Defensible slide 7 says `Scoped, not started`; Ch-VIII leaves it blank; slide 7 row 13 still says `Out of scope`; and the message says they are the only thing left — i.e. in scope. **16 securities, and it is a new engine, not a data gap.** |

### 3.4 The slide-6 chart is ours, and the merge changed its meaning

Slide 6 of both decks carries a native stacked bar: `Complete (42%) 949 · Engine built —
next (39%) 882 · Not yet built (19%) 429`. Our own `Ryse Presentation v3/v4/v5` carry the
same chart type on the same slide number with `Complete 949 · Engine built — next 882 ·
**Scoped, not started 412** · **Out of scope 17**`.

⭐ So Mario built from our chart and **merged our last two buckets** (412 + 17 = 429).
⚠️ We had separated them on purpose: the 17 were the work we were *not* doing. Folding them
into "not yet built" is the same scope drift as §3.3, visible in the artwork.

### 3.5 766 reconciles exactly — and it is not the structured book

`766` is **securities priced by the engine inside the six COMPLETE categories**, not the
structured classes. Reproduced from our own outputs at 2009-03-31:

```
corporate vanilla / hybrid / schedule       555      implied_oas_2009-03-31.csv
corporate callable lattice                    3      callable_risk.csv
government + municipal                      147      sovereign_risk_2009-03-31.csv
agency 38 + guaranteed 9 + linker 14         61      phase2_risk_2009-03-31.csv
                                           ----
                                            766      deck slide 4 / 6: 766      MATCH
949 − 766 =                                 183      deck slide 6: 183          MATCH
```

⭐ The deck's numbers are our numbers, transcribed correctly. ⚠️ One label slip, ours or
his: slide 4 calls 949 *"Securities in scope"* — the scope is 2,260; 949 is the complete
categories. Slide 6 states it correctly. Not worth correcting this week.

**The structured book is 1,294** (882 + 264 + 69 + 79), of which `756` was *our* earlier
figure for the subset we said needed deal data (344 Gov-MBS tranches + the other three
classes entire). Three different numbers, easily confused — name the population every time.

---

## 3.6 ⭐⭐⭐ Why Tier 1 first, when its numbers are knowingly worse

The obvious objection is that Tier 1 ships a number we already know is wrong. Five reasons
it is still the right order, in descending order of how much they actually explain:

1. **⭐⭐ Risk aggregation needs COVERAGE, not precision.** A portfolio VaR computed over
   43% of the book is not a less-accurate VaR — it is not a VaR. It cannot be aggregated,
   compared period over period, or reported. **One uniform approximation across 100% beats
   a precise number across 43%.** This is the whole reason and the rest are supporting.
2. **⭐⭐ Tier 1 and Tier 2 differ ONLY in the cash-flow generator.** Defensible slide 18
   puts them side by side: `P = Σ CFₜ·DF(z+s*)` against
   `P = E[Σ CFₜ(path)·DF(path+OAS)]`. Calibration, DV01/CS01, the Monte Carlo, aggregation
   and reporting are **identical**. So Tier 1 is not throwaway work — it is the chassis,
   and Tier 2 swaps one component. Mario says this in writing twice ("improves the
   reduced-form model rather than replacing it"; "not discarded work").
3. **⭐ It unblocks other people.** Slides 4 and 9: *"then hand to Ryse's engineer for
   parallel-computing work."* An engineer cannot build or test a parallel layer that 57% of
   the book cannot feed, and the Monte Carlo cannot be tested until every security emits a
   (cash-flow, spread) pair. The quality of the pair does not matter for that.
4. **⭐ The LEVEL is exact by construction; only the SENSITIVITIES are wrong.**
   `P₀ = custodian price`, exactly. So market value, exposure and concentration are right
   today. What Tier 1 gets wrong is ΔP under a shock — a narrower claim than "the results
   are bad".
5. **⚠️ The commercial reason, named because it is real.** Both files are Ryse client
   material and one is titled *"**Defensible** Structured Risk Methodology"*, with academic
   citations and an explicit "what this does not capture" slide. **"Defensible" names the
   audience: somebody who will challenge the method.** "Risk on the whole portfolio, by a
   published-literature method, with the limitations stated" is a sentence he needs;
   "risk on 43% of it" is not.

⚠️ **And the risk in the order, which is ours to watch:** a phase 2 that is always next
quarter. Tier 1 reaching "coverage complete" is exactly the moment the pressure to fund
Tier 2 disappears. Mario guarded against it in writing, which is the best available
protection, but **the guard is a slide, not a commitment of anybody's time.**

### ⭐⭐⭐ The false dilemma, and how it dissolves

"Either wait for Liping or publish numbers that are 7× wrong" is not the choice, because
**the ability to amortise is already very unevenly distributed:**

| | n | can amortise TODAY, zero new data |
|---|---:|---|
| Gov-MBS pass-through pools, priced | 505 | ✅ level-pay + the measured ~20% CPR |
| securities with a realised factor path in hand | 376 | ✅ the path itself |
| **union** | **861** | ✅ **67% of the structured book** |
| Government MBS not covered by either | **21** | ⚠️ of 882 — i.e. **98% of Gov MBS is solvable now** |
| **Non-Government CMO / CMBS / ABS** | **412** | ⚠️ **0 of 412 — the entire gap is these three classes** |

⇒ **Government MBS can have a proper, amortising Tier 1 this week with nothing from
anybody.** The honest difficulty is confined to CMO / CMBS / ABS, where there is no paydown
profile of any kind and a bullet at a 25-year legal final is the only alternative.

### ⚠️ CORRECTION to §5, made the same day

An earlier version of §5 said sheet 02 **cannot** be deferred because the factor history is
load-bearing for Tier 1's amortisation. **That was wrong in its emphasis.** It is
load-bearing for the 412 CMO/CMBS/ABS — and for nothing else, because the 861 above already
have a paydown profile. So:

- **Sheet 02 CAN wait**, and waiting is where Mario put it. Liping's availability therefore
  stops blocking the next two weeks of work.
- What it buys is **412 securities in three classes**, and until it lands those three have
  no defensible Tier 1 either — so it is not optional, only *later*.
- ⭐ The sequencing question to put to Mario is therefore narrow and concrete: for those
  412, does he want a **labelled class-level assumption now** (median realised WAL from the
  373 measured paths, applied by class, carried as an assumption in the output the way the
  15/25/35 CPR grid is), or **nothing until the factor history lands**? Everything else
  proceeds either way.

## 4. Open questions for Mario

Short, and each one is a decision only he can make.

1. ⭐⭐ **An AMORTISING bond-equivalent, not a bullet — put as a recommendation, not an
   open question.** He wrote "Mario's recommendation" on his own slide 11; he will want one
   back. The proposal: keep Tier 1 exactly as specified — custodian price as anchor, fixed
   cash flows, one calibrated spread — but let the cash flows amortise instead of
   repaying in a lump at the legal final. Evidence: §3.2 (6.9×, and the custodian's own
   duration agreeing the life is short). Cost: none — the engine already prices the 505
   pools this way. The three populations and where each gets its paydown profile are in the
   table in §3.2; **only the ~375 CMO/CMBS/ABS need anything new, and it is sheet 02.**

   ⚠️ **Say plainly that this differs from what he said on the call**, which was to treat
   these as bullet bonds first (§0). It is not a disagreement about the method and must not
   be presented as one: slide 12's definition of Tier 1 is satisfied in full, and what the
   amortising path adds is the *"more realistic effective-life representation"* his **own
   Tier-2 slide** lists as a benefit. It arrives inside Tier 1 at zero cost because the
   input that slide names as *"Existing Engineering Work"* — *historical monthly principal
   repayments, observed realized cash-flow behavior, existing validation against pools
   priced by another method* — is already extracted and already validated (§1.2, 20 pools,
   median |diff| 8.2 bp). ⭐ **One Tier-2 benefit landed early; nothing was traded away for
   it.**
2. **C.L.O.s:** none in the book by any pattern. A specific holding in mind, or the family
   named generically? If he is planning from a list with a CLO bucket, the lists disagree.
3. **Agency:** complete on his slide 7 — did he mean the one misfiled REMIC Z, or did
   "Agency" come along with the MBS family?
4. **Futures + options:** in scope now? 16 securities, and a new engine rather than data.

⚠️ **And one thing he does not know: Liping said on 2026-10-01 she is not expected back at
a terminal for some time.** His instruction is "focus on Liping". State it plainly and let
him decide rather than building a request that assumes she is available.

---

## 5. What this does to the 2026-10-02 request pack

**Unsent as of today.** Its four sheets map onto the tiers unevenly:

| sheet | points | tier it serves |
|---|---:|---|
| `01_CHECK_FIRST` | ~72 | both — an entitlement probe |
| `02_factor_history` (375 × 211) | 79,125 | **see below — it is NOT purely Tier 2** |
| `03_coupon_monthly` (156 × 211) | 32,916 | **Tier 1** — the movers' coupon behaviour |
| `04_coupon_classify` (595 × 4) | 2,380 | **Tier 1** — the fixed-vs-moving bit |

⭐⭐ **The factor history serves BOTH tiers, and that is the finding that decides the
pack.** It is Tier 2's raw material, yes — but §3.2 shows it is also the only thing on
offer that gives Tier 1 a defensible maturity. Without it the bond-equivalent falls back on
legal maturity and is wrong by ~6.9×; with it we can set an effective life per security
from what actually happened. **So "defer sheet 02 because Mario said Tier 1 first" would be
exactly the wrong cut.**

⚠️ **Also incomplete against the message:** the pack covers 751 securities. Mario asks for
all of Gov MBS + ABS + CMBS + CMO (+ CLO, which does not exist, + Agency, which is done)
= **1,294**. The 10-02 pack's coupon coverage was built from the 376 already returned plus
the 375 requestable in the other three classes; it does not reach the 505 pools (whose
coupons we hold) nor the 37 without an identifier.

⭐⭐ **But "rebuild it for all 1,294" would be the GBP mistake with a different field.**
The coupon-moves bit is already settled or already asked for most of the book:

| population | n | the coupon bit |
|---|---:|---|
| Government-MBS pass-through pools | 505 | ✅ **fixed by construction** — a pass-through pays its pool's net coupon; nothing to ask |
| tranches whose factor history returned | 376 | ✅ **already in the pack**, sheets 03 + 04 |
| CMO / CMBS / ABS | 375 | ⚠️ **the genuine gap** — both the coupon bit and the factor history |
| no ISIN or CUSIP in the custodian file | 37 | ⚠️ unreachable by any request line |

⇒ **the pack's 751 is close to right; 1,294 would re-ask for data we hold.** What it needs
is not more securities but the §4.1 answer, because an amortising Tier 1 makes sheet 02
load-bearing for the 375 rather than deferrable.

**Decided here:** the pack is **not sent** until the §4 questions come back, and the claim
assertion in `make_mario_request.main()` is re-pointed at whatever population the answer
settles on — so the arithmetic cannot drift again. ⚠️ And it is not sent to Liping at all
until her availability is resolved.
