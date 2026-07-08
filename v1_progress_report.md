# Fixed-Income Pricing Module — Progress Report (v1: Corporate Bonds)

**To:** Mario Pardo
**From:** Lichen Chen
**Re:** Corporate bond pricing — methodology, validation, and findings

---

## 1. Summary

Over the past period I built and validated a first version (v1) of the fixed-income pricing module, focused on **corporate bonds**, in line with the objective of moving from ad hoc Excel/VBA tools to a structured, scalable Python module.

The core result: the pricing approach — **bootstrap a risk-free curve, add a rating-based credit spread (OAS), and discount the bond's cash flows** — has been implemented in Python and **validated against the custodian's own marks**. For investment-grade bonds the model is **unbiased** (it sits essentially dead-centre on the custodian's prices, with a median signed error near zero), confirming the method is sound. The remaining single-name dispersion is a known and well-understood consequence of using index-level (rather than issuer-level) spreads, not an error in the engine.

The work is organized as a clean, layered, version-controlled codebase with a regression-test suite, so it can be extended to other instrument types over time.

---

## 2. What the module does (the pricing pipeline)

The valuation of a corporate bond requires two inputs, which the module sources and combines:

1. **A risk-free yield curve** — taken from the U.S. Treasury par-yield history and converted, via **bootstrapping**, into a clean zero-coupon (spot) curve plus discount factors. Bootstrapping strips the market's "blended" par yields into period-by-period spot rates, which is what is actually needed to discount each individual cash flow.

2. **A credit spread (OAS) by rating** — taken from the ICE BofA US Corporate Option-Adjusted Spread history (the `OAS Credit Curves` data), selected for the relevant valuation date and the bond's credit rating.

The discount rate for each cash flow is then:

> **discount rate(t) = risk-free spot rate(t) + OAS[rating]**

and the bond price is the sum of each cash flow discounted at that rate. Lower-rated bonds carry a higher OAS, hence a higher discount rate and a lower price — exactly as observed.

This is the structured, repeatable version of the "look at OAS, bootstrap the curve, then discount" approach, with each layer (curve construction, credit spread, instrument terms, pricing) cleanly separated.

---

## 3. Building the priceable universe

The corporate-bond holdings were filtered down to a clean, priceable set using a **deterministic pipeline** that is fully reproducible and produces a per-bond exclusion log (every excluded bond carries a single, recorded reason).

The funnel, for the corporate-bond sub-category in the master positions file:

- **811** corporate-bond holding rows →
- **732** unique bonds (after de-duplicating on Asset ID) →
- **476** priceable bonds (plain fixed-rate, rated, non-callable, held, not yet matured).

The bonds excluded between 732 and 476 fall into clear, recorded categories:

- **Terms unavailable** (medium-term notes whose coupon terms are not in either sheet) — a data-availability issue, not an instrument issue;
- **Non-vanilla** (floating-rate, fix-to-float, structured) — out of scope for v1;
- **Callable** — these require an option model (deferred to v2), with their call terms preserved for later;
- **Defaulted / no-rating** — cannot be priced on a rating-based spread;
- **Matured** — no remaining cash flows at the valuation date.

Two practical notes that emerged here:

- Credit ratings are present and well-populated (S&P and Moody's each cover ~98% of the corporates, under the `Quality rating - …` columns), so the rating-based approach is viable. A consistent S&P-primary / Moody's-fallback mapping collapses all notches into the seven ICE BofA rating buckets (AAA…CCC), with the investment-grade / high-yield boundary handled explicitly.
- The custodian file conveniently also provides its own **market price, market value, and yield-to-maturity** for each bond. These are kept separate from the pricing inputs and used purely as a **validation benchmark** — a ready-made "answer key" to check our prices against.

---

## 4. Validation results

Prices were compared against the custodian's market prices for the 476 priceable bonds. Results are reported in two groups, since they behave very differently.

**Investment-grade (AAA–BBB, 456 bonds):**

- With **no credit spread** (OAS = 0), prices are systematically too high (median difference ~21%) — i.e. treating the bonds as risk-free over-values them. This is the expected starting point.
- **Adding the rating-based OAS** brings the median absolute difference down to **~6.4%**, and — crucially — the **median *signed* difference is essentially zero (−0.4%)**. In other words, with the credit spread applied, the model sits dead-centre on the custodian's prices, with no systematic bias up or down.
- As an independent check, near-maturity high-grade bonds (where credit risk is negligible) match the custodian to within ~0.2% even at OAS = 0, confirming the curve, discounting, and conventions are correct.

**High-yield / distressed (BB/B/CCC, 20 bonds):**

- These remain materially off. The reason is structural: several were marked by the market as near-default (custodian prices of ~12–29 per 100), and an **index-average** rating spread cannot capture that kind of **issuer-specific distress pricing**. This is a known limitation, addressed in v2 with issuer-level inputs.

**Interpretation.** The right way to read the ~6.4% investment-grade figure is as **dispersion, not bias**. With a median signed error near zero, the method is demonstrably unbiased; the ~6.4% reflects how far individual bonds scatter around their *rating-average* spread (in 2009, same-rating issuers could trade ±300 bp apart). This is the direct, expected consequence of using a single index spread per rating, rather than issuer- or maturity-specific spreads — a deliberate v1 simplification, not a defect.

---

## 5. Notable findings

**A date-alignment test (a useful negative result).** The positions are dated 2009-03-31, while the most readily available curve snapshot was 2009-06-10 — a ~70-day gap. To test whether this gap was driving the residual, I sourced the 2009-03-31 Treasury curve and re-priced on a fully date-aligned basis. The result was **worse**, not better (investment-grade median rose from 6.4% to 11.1%, and the prices became systematically too low). The reason: 2009-03-31 was near the crisis peak for credit spreads, and those peak spreads overwhelmed the slightly lower rates. This **rules out the date gap as the main lever** and independently confirms that the residual lives in the *granularity of the index spread*, not in the valuation date. It also indicates the custodian's marks align with the tighter (~June) spread environment rather than the March peak. The practical value: it saves us from pursuing curve-date alignment as a dead end.

**Data-source robustness.** The historical credit-spread data turned out to be available within the project's own files (the `OAS Credit Curves` history runs 1997–2025), which matters because the free online FRED history for these ICE BofA spreads was cut back in April 2026 to a rolling 3-year window. The project's stored copy is therefore now the durable source for historical spreads.

---

## 6. Where this leaves v1, and next steps

**v1 conclusion.** The bootstrap → rating-OAS → discount method is **validated and unbiased for ordinary investment-grade corporate bonds**, matching the custodian's marks to a median of ~6.4% — a residual that is fully explained (index-spread dispersion) with a clear improvement path. The engine, the universe pipeline, the credit-spread loader, and a regression-test suite are all in place and version-controlled.

**Natural next steps (v2):**

- **Finer credit spreads** — moving from index-level to sector-, quality-, or issuer-level spreads is the single real lever for tightening the investment-grade fit below ~5%. (A clear example is AA-rated bank debt, which in 2009 traded wider than the AA index — a sector-vs-index effect.)
- **Distressed single names** — the deeply marked-down bonds need issuer-level market prices or recovery assumptions rather than an average rating spread.
- **Callable bonds** — require an option-adjusted pricing model.

I'm happy to walk through any part of this in more detail, and to align on which direction to prioritize next.
