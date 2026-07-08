# Fixed-Income Pricing Module — v2: Calibration, Risk Metrics & Callables

*Corporate-bond reference implementation · valuation basis 2009-03-31 · status: implemented & validated (60 tests green)*

---

## 1. Summary

v2 takes the module from *validating a pricing method* (the subject of v1) to the workflow you defined: **calibrate an implied OAS from each bond's custodian price, compute its risk metrics on that calibrated model, and extend the engine to callable bonds.** In v1 the credit spread was an *input* — a rating-based index OAS — and the question was whether the resulting prices were right. In v2 the spread is an *output*: the single number that makes our model reprice the custodian's mark exactly, from which the risk analytics are then derived. The deliverable is no longer a price; it is the spread and the interest-rate risk implied by the mark.

All three parts are implemented and validated. **527 canonical corporate bonds** are calibrated, with the implied OAS reproducing every custodian price to machine precision. **Effective duration, DV01 and convexity** are computed for the calibrated book and cross-checked against analytic values. A **callable/putable short-rate lattice engine** is built and validated by financial invariants. The valuation basis is your 2009-03-31 curve, and every key convention — calibration date, FX handling, volatility, call terms, and the custodian marking environment — is now confirmed rather than assumed-pending.

---

## 2. The calibration approach: implied OAS as a calibration factor

The implied OAS is a **calibration factor, not a pricing input**. For each bond we solve for the single flat spread that, added to the risk-free curve, makes our model's clean price equal the custodian's price. Because price falls monotonically as the spread rises, this spread is unique, and a standard root-finder recovers it reliably. This replaces v1's approach of *reading in* a rating-average index spread: rather than imposing one spread per rating on every name, each bond now carries the exact spread its own mark implies. The calibration is exact across the whole book — the largest price residual is ~2×10⁻⁸ — which is the primary validation: the model fits every custodian mark by construction.

The backed-out spreads are also economically sensible, which validates their *level*, not just the fit. Comparing the median implied OAS by rating against the ICE BofA index (compared at **2009-06-10**, our control date, where the index reflects the same recovering-market credit environment the custodian marks were struck in — see §3 — so the comparison is like-for-like; near-maturity names excluded; each bond on its own-currency curve):

| Rating | Implied OAS (median, bp) | ICE index (bp) |
|--------|-------------------------:|---------------:|
| AAA    |                      171 |            148 |
| AA     |                      386 |            227 |
| A      |                      291 |            302 |
| BBB    |                      413 |            453 |

Two results stand out:

- **(a) No systematic bias.** A and BBB — the investment-grade core of the book, over 369 names between them — land essentially on the index (A 291 vs 302, BBB 413 vs 453). Where the comparison is like-for-like, the calibration reproduces the market's own rating spreads, with no drift up or down. (Including the 46 reclassified make-whole names, all A/BBB, moves these medians by only a few basis points.)
- **(b) The method captures what the index averages away.** AA comes out materially wider than its index — **386 vs 227 bp** — and this gap *persists when near-maturity names are excluded*, so it is not an artefact of a few short bonds. It is the real 2009 market: AA-rated bank and financial debt traded well wider than the AA *index average* right through the crisis. The per-bond implied OAS sees this; an index-average spread (v1) smooths it away. This is the concrete sense in which per-bond calibration improves on the index approach — it recovers a truth the average discards.

(The high-yield buckets are dominated by distressed names, whose implied OAS is a recovery-driven plug rather than a clean credit spread; these are flagged as such.)

This implied-OAS-then-risk-metrics flow is, in fact, the design of the legacy risk system's *own* callable routine — which solves for an implied OAS in one mode and an effective duration in another — so v2 realigns the Python module with the original system's intent.

---

## 3. Data and correctness improvements

Several corrections and confirmations landed in v2, each improving correctness over v1:

- **2009-03-31 curve adopted as the baseline.** Your 2009-03-31 USD curve fills the gap that had forced v1 onto a snapshot ~70 days later, so v2 now calibrates *on the holdings date itself*. It integrates natively (same file format) and matches the old file to the digit at the one overlapping date. This makes the universe more complete — **481 canonical at 3-31 vs 476 at 6-10**, as five bonds that were alive on the holdings date but had matured by June are correctly retained — and it clears a short-end distortion: an AA bond maturing in June went from an inflated **1371 bp to 464 bp**, and the one **negative implied OAS** (an A bond maturing in July, −177 bp) turned to a sensible **+199 bp**. The by-rating relationships from §2 carry over at the 3-31 levels (e.g. AA stays wide, 489 vs 403).
- **EUR/GBP bonds routed to their own-currency curves.** v1 silently priced the whole book on the USD curve; v2 prices the EUR sleeve on the EUR curve, which **tightens their implied OAS by ~20–55 bp** (EUR rates sat above USD in 2009 — a real correction, not a re-labelling). Two GBP-related bonds remain parked pending a usable GBP curve.
- **FX confirmed — no self-conversion.** We verified the custodian file already carries base-USD market-value columns, and our loader reads those directly. There is no need to apply exchange rates ourselves; the currency field is retained only to route each bond to its pricing curve.
- **Custodian marking environment confirmed (open question closed).** At the 3-31 baseline the implied investment-grade spreads sit *below* the 3-31 crisis-peak index. You confirmed the reason: by end-March 2009 the crisis was already easing and spreads had retreated from the peak, so the tighter credit embedded in the custodian's marks reflects a **recovering market, not a stale or mismatched date**. Our implied-OAS observation is exactly consistent with that reading, which closes the marking-date question. (It affects only how the spread *level* is interpreted; the risk metrics reprice each mark exactly regardless of its date.)
- **Make-whole callables reclassified as vanilla.** 46 bonds previously excluded as "callable" are in fact make-whole callables — callable only near maturity at a price that makes the option worth ≈ zero — so they are correctly priced as ordinary bonds. Reclassifying them lifts the canonical set to **527** (from 481) and removes a spurious exclusion; only genuinely optional callables now go to the lattice (§5).

---

## 4. Risk metrics

On each calibrated bond we compute three interest-rate risk measures — **effective duration** (the price sensitivity to a parallel rate move), **DV01** (the price change per 1 bp, the unit that aggregates to portfolio risk), and **convexity** (the curvature of that sensitivity). They are computed numerically, by a **±1 bp central-difference bump**. A subtle point makes this clean: our pricer adds the OAS as a flat spread on the continuous curve, so bumping the spread is mathematically identical to a parallel curve shift — no curve object is rebuilt. As a correctness check, the numerical effective duration matches the closed-form (Macaulay) duration to **seven decimal places**.

The metrics are computed across the full canonical book (bar the two GBP names above) and are **stable to the calibration date** — moving from the 6-10 control to the 3-31 baseline shifts the median duration by only ~0.13 year. The values are sane: median effective duration is about **6 years**, and individual bonds behave as expected (a ~10-year bond returns a duration near 6.6, DV01 near 0.069, convexity near 56; a 30-year AA returns ~12.3, ~0.13, ~244).

This is capability the legacy toolkit **did not have**. Across ~14,000 lines of legacy VBA, the only sensitivity computed was a single effective duration (via a ±10 bp bump) — there was no DV01, no convexity, and no analytic duration anywhere. The v2 risk layer is a genuine addition, not a re-implementation.

---

## 5. Callable and putable bonds: an option-adjusted lattice

A callable bond lets the issuer redeem early, and that optionality cannot be captured by simple discounting. v2 adds a proper engine for it.

**The engine.** We value callables (and putables) on a **clean, standard Black-Derman-Toy short-rate lattice** — a binomial tree of future interest-rate paths, calibrated by forward induction to our validated zero curve so that it is **arbitrage-free by construction** (it reprices the curve's own zeros and par bonds exactly). At each node the issuer may exercise the call when it is in their interest; rolling the value back through the tree yields an option-adjusted price, spread, and duration.

**Why invariant-validated, not golden-master.** The legacy callable engine depends on Bloomberg inputs we do not have and cannot be run to produce reference outputs. So rather than port it line-for-line, we built the correct standard engine and validated it against **financial invariants**: it reprices par bonds to 100; a callable is worth no more than an otherwise-identical straight bond, which is worth no more than a putable one; with zero volatility the option disappears and the price collapses to plain discounting; and the implied-OAS round-trip recovers its input. This is the same philosophy used for the v1 pricer — build and prove the correct engine rather than replicate a tool we cannot execute.

**Applied to the book.** Four bonds are genuine fixed-rate callables (the other 46 make-whole names are priced as vanilla, §3). They are valued with a **par call at 100** and **15% volatility** — both your confirmed v1 assumptions, and labelled as assumptions — and the engine reads its call terms from a **standalone schedule table**, so that when real call schedules (Bloomberg/FISD) arrive they drop in with *zero code change*; the table is built and waiting to be filled.

Two honest points about impact and assumptions:

- **The option changes the numbers on exactly one name.** For an A-rated bond marked at 90.04, the call shortens effective duration from **11.56 years (straight) to 10.54 years (option-adjusted, at 15% vol)** — about a year less interest-rate risk. On the other three the option is not currently binding (two are distressed, so the call is worthless; the fourth is discussed next). The lattice is a necessary capability, but on *this* book its numerical impact is confined to a single bond — stated plainly, not oversold.
- **A useful cross-check, and an honest self-refutation.** For that one call-active bond, the custodian's *own* reported effective duration (11.73 y) matches our **straight** duration (11.56), not the option-adjusted 10.54 — i.e. the custodian's analytics do not appear to capture the call, while our lattice does. Separately, the par-call assumption is *refuted* by a fourth bond whose market price (108.69) sits well above a par call, forcing a negative implied OAS — the model flags its own bad assumption. That is exactly the diagnostic behaviour we want, and it confirms that real call schedules are **needed data**, not a modelling choice, for these names.

---

## 6. Status and next steps

v2 is implemented, validated, and version-controlled, with the regression suite green — **60 tests**, adding the callable-lattice invariants and the schedule-table loader to the v1 golden-master set. Natural next steps:

- **Position-level risk** — aggregate the per-bond DV01 and duration by holding size into portfolio-level interest-rate risk (the natural consumer of these metrics).
- **Real call schedules and a GBP curve** — fill the schedule table for the four genuine callables (a data change, not code) and source a GBP curve for the two parked names.
- **EIR / amortised cost (IFRS-9)** — implement once the spec is confirmed; this is a requirement with no legacy equivalent to reconcile against, so it is built to the standard.
- **Beyond corporates** — the lattice engine is reusable for the structured products (MBS/CMBS/CMO) and the CreditMetrics risk overlay on the longer roadmap.
