# Fixed-Income Pricing — v1 Summary (Corporate Bonds)

**For:** Mario / project review &nbsp;•&nbsp; **As-of:** 2026-06-27 &nbsp;•&nbsp; **Repo:** `github.com/charlieee0712/fixed_income_pricing` (private)

**Goal.** Re-implement the legacy Excel/VBA pricing toolkit as a structured, scalable Python module.
v1 = the corporate-bond reference implementation (**bootstrap → rating OAS → discount**), reconciled
against the custodian's marks. Valuation basis: URS pension book, USD corporates, **2009-06-10**
(first curve after the 2008-11 → 2009-06 data gap; holdings dated 3-31).

## What v1 delivers (end-to-end, tested)
- **Curve** — par→zero bootstrap, reproduces the legacy golden CSV to the digit; wrapped in `ZeroCurve`.
  The 2009-06-10 USD curve checks out vs actual June-2009 Treasuries.
- **Universe** — deterministic MECE pipeline: 811 holding rows → **732 unique** → **476 canonical**
  priceable corporates, with a per-bond exclusion log (every documented count reproduced exactly).
- **Rating → OAS** — S&P/Moody notch-map → 7 ICE BofA buckets; per-rating OAS from the project's own
  archive (1997–2025 daily).
- **Pricing** — faithful port of the VBA `BondPrice` (ACT/364, 182-day schedule, accrued, clean/dirty),
  with the discounting **corrected** (the VBA put a *semiannual* rate into a *continuous* formula,
  under-pricing ~0.3% at 10y; default fixed, a `vba_compat` switch reproduces the legacy for reconciliation).
- **26 golden-master tests green**; all code merged to GitHub.

## v1 verdict — the method is VALIDATED
- **Unbiased.** Investment-grade (AAA–BBB) vs custodian price (BT): **signed median −0.4% (≈ 0)** — curve +
  rating OAS is *centred* on the market mark, no systematic error. (At OAS = 0, near-maturity high-grade ties
  BT to **< 0.2%**, isolating the engine from credit.)
- **Precision.** Single-bond **median |diff| ≈ 6.4%** — this is **dispersion, not bias**: individual names
  scatter around the *index-average* rating OAS (±300 bp is normal in the 2009 crisis). A known v1 **design
  boundary**, not an error.
- **Confirmed twice.** Removing distressed names barely moves it (→ 6.1%); and a date-matched re-pricing as-of
  3-31 **ruled out the 70-day holdings/curve gap** as the cause (it made the fit *worse* — the 3-31 crisis-peak
  OAS overstates these high-grade holdings' spreads).
- **Bottom line.** `bootstrap → rating OAS → discount` works for ordinary IG credit: **unbiased, ~6% name-level
  dispersion** limited by the index-average-OAS design. Not a "miss vs 5%" — **success, precision to improve in v1.5.**

## Out of v1 scope (= v2, by design — these need richer inputs)
- **High-yield / distressed single-names** (BB/B/CCC): a rating-*average* OAS can't reprice a near-default name
  marked on recovery (e.g. BT 12–29) — needs single-name market price / recovery assumptions.
- **Callable bonds** (73): need an option model.
- **Finer OAS** (sector / quality / name): the real lever to tighten IG precision below 5% — the 6.4% is the
  index-average-OAS boundary.

## Open items for the team
- **CEO — confirm the EIR (amortised-cost) spec.** EIR is a *requirement, not legacy code* (searched 14k VBA
  lines + all sheets, zero hits) → implement per **IFRS-9**, no legacy golden to reconcile. Data-inferred preset
  (to confirm): Book cost = amortised carrying value ⇒ amortised cost ≈ book cost, EIR = IRR(book cost, remaining
  cash flows); deliver per-bond {effective yield, amortised cost} + an amortised-cost-vs-market table.
- **Colleague — confirm the custodian BT marking date/source.** The 6-10 model fits a nominally-3-31 mark, so BT
  may not be strictly 3-31. A data-understanding item, **not** a precision lever (the 3-31 experiment settled that).

## Roadmap
v1 (done) corporate IG pricing → **v1.5** finer OAS (sector/quality) + EIR (amortised cost) → **v2** distressed
single-names, callables (option model), CreditMetrics risk overlay (rating migration / credit VaR).
