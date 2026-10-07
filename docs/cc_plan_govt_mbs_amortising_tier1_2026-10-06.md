# Plan — Government MBS, amortising Tier 1 (2026-10-06)

**Goal.** Every Government-MBS security that can carry an amortising cash flow gets a
calibrated spread and risk metrics in one table: **861 of 882**. Nothing else in the book
moves.

⚠️ **Gate 0 is §1 and it has already run.** Four rounds in a row needed a revision section
written after the fact; the one that put Gate 0 first did not
(`cc_next_instruction_government_assets_restructure_2026-09-10.md`). Its results are
below, and the decisions in §2 are written *around* them rather than before them.

---

## 1. Gate 0 — RUN 2026-10-06, four checks, all passed

### G1 · the inputs still reproduce
```
docs/03_factor_history.xlsx   sha256 7e1c445be421f7d8…
376 columns x 211 months, 79,336 numeric      = the 10-01 record exactly
outputs/pool_risk_2009-03-31.csv  505 rows
```

### G2 · the 356 new securities carry every Tier-1 input

| | n |
|---|---:|
| new securities (in the factor file, **not** among the 505) | 356 |
| custodian price present | 356 |
| income rate present | 356 |
| usable factor path (`f₀ > 0`) | **354** |
| **all three** | **354** |

⚠️ **2 have no usable path** and will be named, not dropped.
Composition: **ordinary amortising 202 · P/O 78 · I/O 76**.

### G3 · ⭐⭐⭐ The I/O question is SETTLED — and positively

Named on 10-02 as the next thing to check and still open: an I/O's factor might be a
*notional* and its coupon a *strip rate*, neither exercised by the 10-01 validation (all 20
validation securities were ordinary pools). **Check the few before the many.**

| kind | n | price median | p10 | p90 | coupon median | custodian duration |
|---|---:|---:|---:|---:|---:|---:|
| **I/O** | 76 | **8.151** | 4.663 | 12.226 | 5.978% | **−6.685** |
| P/O | 78 | 90.176 | 81.966 | 95.525 | **0.000%** | +7.191 |
| ordinary | 222 | 103.850 | 94.575 | 107.012 | 6.000% | +2.349 |

⭐ **A price of ~8 per 100 is the signature of a claim on a notional**, against ~104 for an
ordinary tranche. And **8 of 8** test cases calibrated to a finite, positive spread under
an interest-only treatment. ⇒ `par` is a notional, the price is per 100 of notional, and
`interest(t) = 100 · f(t−1)/f₀ · coupon/12` with **no principal term** is the right
decomposition.

⚠️⚠️ **CORRECTED the same day — "the 76 are buildable" was read off 8 samples and the
population refuted it.** Run over all 74 that price:

* **74 of 74** come out with a POSITIVE effective duration, while **49 of 74** have a
  custodian duration that is NEGATIVE;
* the calibrated spreads run **−56,670 to +6,719 bp**, with 55 of 74 beyond ±2,000.

They are *computable*, not *usable*. ⭐ The rule that settles it: **publish a risk number
only when its sign is known to be right.** For the 221 amortising and 78 P/O the duration
sign is positive and the custodian agrees in aggregate; for an I/O it is structurally wrong,
because the only sensitivity Tier 1 can see (discounting) is the smaller of the two and the
larger (prepayment response) is what Tier 1 by construction cannot model.

**Decided:** the 76 ship with price and market value — which are exact, being calibrated to
the custodian's own mark — and with `implied_spread_bp` and the duration **blank**, route
`io-strip-prepayment-dominated`, and the custodian's duration in its own column as the
evidence. ⚠️ **Our column is never filled with their number**: that is the standing
"custodian duration is evidence, never a router" rule (2026-09-03), and a column that
sometimes holds our model and sometimes theirs is worse than a blank.

⭐ This is stated in the report as a Tier-1 **boundary**, not a shortfall — it belongs on the
list his own slide 12 already keeps of what Phase 1 does not capture.

⚠️⚠️ **But one limit must be named now rather than discovered in a report.** The I/O
spreads come out **301–4,847 bp**, and the custodian's own duration is **negative**
(median −6.685) while **a fixed cash-flow schedule can only produce a positive duration**.
That is not a bug to fix inside Tier 1: **an I/O's entire rate sensitivity comes from
prepayment response**, which Tier 1 by construction does not model. So for the 76 I/Os:
- the **level** is still right (calibrated to the custodian price),
- the **duration sign is systematically wrong**,
- ⇒ they ship **flagged**, with the custodian's own duration printed beside ours, the way
  the sovereign book reports a >1.5y divergence with both numbers (2026-09-03).
- ⭐ And the number is not a credit spread: it is absorbing prepayment expectation. The
  naming rule in §2.1 matters most here.

### G4 · ⭐⭐⭐ The floating-coupon unknown costs at most ~1.8 years — so this round does not wait

104 of the 376 are floater-suspects and their coupon history has **not** been pulled
(sheet 03 of the unsent 10-02 pack). On a **bullet** that is fatal: a floater carried as
fixed gets a duration of roughly its maturity instead of roughly zero. On an **amortising
realised path** the principal timing is already correct and only the interest leg is in
doubt, so its share of PV bounds the error:

```
interest leg as a share of PV   median 15.3%   p90 36.7%      (n = 214)
PV-weighted average life        median 2.73y   p90 4.83y
worst-case duration error  <=  36.7% x 4.83y  =  1.77 years
for comparison, a bullet at legal maturity costs  ~21 years
```

⇒ **Ship now with the custodian's coupon held constant; Liping's coupon pull improves it
later by at most ~1.8 years of duration.** The gate that would have blocked this round
turns out to cost a twelfth of what bulleting costs.

---

## 2. Decisions taken here

### 2.1 ⭐ The column is NOT called an OAS, and a test enforces it

Mario's own slide 13: *"in the initial Ryse model this is best called an **implied or
bond-equivalent spread**. A true OAS requires explicit modeling of option-dependent cash
flows such as prepayments."* Our cash flows are fixed, so `implied_oas` here would
contradict the client's own deck.

**`implied_spread_bp`**, matching the sovereign book. Enforced the way
`implied_spread_vs_nominal_bp` is: **a test injects the banned name and fails**
(mutation-verified, 2026-09-10) — a lock that is not decorative.

### 2.2 The observed-path generator sits BESIDE the assumed-CPR one

`core/pricing/prepayment.py` already holds the assumed-CPR generator (`pool_cash_flows`,
level-pay + SMM) that prices the 505. The new one consumes an **observed** factor path.
They are the same mathematics — a balance schedule becomes cash flows — one assumed, one
measured, and **Mario's slide 18 says the tiers differ *only* in the cash-flow generator**.
Putting them in one module makes the code say that. **Additive only**; the 505 CSV is
asserted byte-identical afterwards.

### 2.3 ⚠️ The T+1 shift gets ONE owner

*Bloomberg's `2009-04` column IS the 2009-03-31 position* (verified to 2.9e-08 on 370/373;
reading the label costs a factor of six on `3133T5MR1`). Today that shift lives in a
scratchpad script and in prose. It becomes a **loader** — `dataio/factor_history.py` — and
no caller applies it again. This project has found three "two owners, one decision" bugs;
this is the shape of a fourth.

⚠️ And the data moves out of `docs/` into `data/`: a production input must not live in the
documentation folder.

### 2.4 A NEW output file; nothing existing moves

`outputs/tier1_structured_<date>.csv`, one row per security. `pool_risk_*.csv` keeps its
three-point CPR grid and stays byte-identical — the 505 enter the new table at a **single
measured speed**, which is what a portfolio risk layer needs, without disturbing the
artifact that proves the grid.

### 2.5 Routing is by structure, and it is explicit

| kind | principal term | interest term | n |
|---|---|---|---:|
| ordinary amortising | `100·(f(t−1)−f(t))/f₀` | `100·f(t−1)/f₀·c/12` | 202 |
| **P/O** | same | **none** — `income_rate` is literally 0.000% | 78 |
| **I/O** | **none** — the factor is a notional | same | 76 |

⚠️ Decided by the custodian's description text (`P/O`, `I/O` with the slash — `\bPO\b`
misses `P/O`, which already cost a mislabel on 10-02), **never** by a price or duration
sniff. The `PAR_YIELD_UNITS` lesson: an explicit registry, not a threshold.

---

## 3. Build order

1. `dataio/factor_history.py` — the loader + the single T+1 owner; `data/factor_history.csv`
2. `core/pricing/prepayment.py` — `observed_cash_flows` / price / implied spread / risk
3. `assets/structured/` — the per-metric wrappers the template requires
4. `scripts/tier1_structured.py` — the driver, 861 rows + a dated disposition sidecar
5. tests, including the banned-name lock and the two kind-routing locks
6. the 505 folded in at a single measured CPR

## 4. What this round does NOT do

- **CMO / CMBS / ABS (412).** No paydown profile of any kind exists for them. They are the
  whole reason Liping's trip is still needed, and they are out of scope here.
- **Futures and options (16).** Scope unresolved — see
  `client_directive_three_tier_structured_method_2026-10-06.md` §3.3.
- **The Monte Carlo layer.** Tier 1 feeds it; it is not built here.
- **Re-anchoring `pool_risk_*.csv`.** Deliberately untouched.


---

## Outcome — recorded 2026-10-07, after the run

⚠️ **This section is appended, and the body above is left as it was written.** A plan is a
record of what was planned; editing its numbers to match the result destroys the only evidence
of what was foreseen. Four previous rounds needed exactly such a section (§21 / §16 / §26 /
§14), and the one that put Gate 0 first did not.

**The plan said 861 of 882 and 21 named. Delivered: 858 and 24** — and the three that moved
reconcile exactly.

```
505   pool_risk priced today (478 spot pools + 27 TBA forwards)
376   securities with a measured factor path          (verified: 376 cusips in
 -20  in BOTH -- the validation pools put in the request deliberately    factor_history,
= 861 the plan's figure                                                 all 376 of the 882)

861
 -3   degenerate paths: 2 whose factor is already ZERO at the valuation date,
      1 whose measured path produces no net cash at all
= 858 delivered, as 373 observed-path + 458 assumed-CPR + 27 TBA forward
 24   named = 19 no path and no usable pool WAC + 3 degenerate + 2 forwards whose
      description states no settlement month
```

⭐ **None of the three is a shortfall: they are securities with no remaining cash flow to
price, and nothing short of reading the path could have told us.** The estimate was as good as
it could have been made.

**Two things the plan did not foresee at all:**

1. **The 29 TBA forwards.** The plan counted them among the amortisable. They are **forwards on
   a generic pool**, and pricing one as a spot pool silently drops the settlement adjustment
   that `assets/securitized/tba.py` exists to apply — caught on 2026-10-06 because the driver
   priced 2 securities `pool_risk.py` had deliberately skipped, and a cover that is a strict
   superset of an existing driver's is a question, not a win. They were named that day and
   **priced properly on 2026-10-07**, once `tba.py` acquired duration / DV01 / convexity.
2. ⭐⭐ **That a forward separates DV01 from CS01.** Every other security in this book is
   discounted at `z(t) + s`, so a rate bump and a spread bump are one number — across the 757
   rows priced before the forwards the two columns differed by **exactly 0.0, every row**. A
   forward's spread sits in the numerator only, so its rate duration is shorter than its
   spread duration by **exactly the settlement lag**. The schema already had both columns.
