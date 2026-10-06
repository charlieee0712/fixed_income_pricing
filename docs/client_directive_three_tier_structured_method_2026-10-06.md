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
+21 years of duration on the median security.** Mario's own slide 19 says Tier 2 will
*"replace legal-maturity bullet behaviour with a more realistic effective-life
representation"*, which implies Tier 1 uses legal maturity. Taken literally that publishes
portfolio durations ~7× too long for **57% of the book by count**, on the one output the
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

## 4. Open questions for Mario

Short, and each one is a decision only he can make.

1. ⭐⭐ **What maturity does the bond-equivalent use — legal, or effective life?** With
   §3.2 as the evidence. This is the question; the rest are housekeeping.
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

**Decided here:** the pack is rebuilt against Mario's population before it is sent, and the
claim assertion in `make_mario_request.main()` is re-pointed at 1,294 so the arithmetic
cannot drift again. ⚠️ Not sent until the §4 questions come back — question 1 can change
what the sheets need to carry.
