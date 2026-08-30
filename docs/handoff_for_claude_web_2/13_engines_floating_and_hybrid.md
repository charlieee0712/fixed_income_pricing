# Floating-rate notes and fixed-then-float hybrids

**Migrated into `pricer/` on 2026-08-30 (Round 2b).** This file used to describe next week's
target; it now describes shipped code. The engines answer Mario's pivot column-F rows
**F12 · F14 · F15 · F16** (and, unmarked but sharing the hybrid engine, rows 6–11).

```text
pricing/frn.py     -> pricer/core/pricing/floating.py   + assets/corporate/floating.py
pricing/hybrid.py  -> pricer/core/pricing/hybrid.py     + assets/corporate/hybrid.py
```

Both moved **verbatim** (the body below the docstring is asserted byte-identical to the
pre-move file); the old paths are compatibility shims. Only hybrid's two import lines changed,
and both targets are exact aliases of the same objects — asserted in a test, not assumed.

---

## 1. The FRN engine (`core/pricing/floating.py`)

Each future coupon is the **simple forward off our own bootstrapped `ZeroCurve`**,
`F(t₀,t₁) = (DF(t₀)/DF(t₁) − 1)/(t₁−t₀)`, plus the note's quoted margin. Every cash flow is
discounted on the **same** curve plus a flat calibrated spread. Single-curve — the 2009
convention. OIS dual-curve discounting is a documented future enhancement, deliberately not
modelled, and the docstring says so rather than leaving a reader to assume it was overlooked.

Conventions mirror the fixed engine exactly (ACT/364, backward `round(364/freq)`-day grid,
the same accrued formula), so FRN and vanilla numbers are directly comparable.

**Input shape — the thing to know before reading the code.** A floater has **no `coupon`
input at all**. It is replaced by two:

| input | meaning |
|---|---|
| `quoted_margin_bp` | the contractual spread over the index |
| `current_coupon_pct` | the ONE coupon already fixed, at the last reset (optional) |

That difference *is* the instrument, and it is the first thing to point at in a walkthrough.

### ⚠️ Duration: two exact regimes, and the sign flips

The old docstring described only one of these, and two tests were written wrong against it
before the engine was checked. Both regimes are exact, measured on a flat 4% curve, a
30-year note:

| `current_coupon_pct` | effective duration | why |
|---|---|---|
| supplied (e.g. 4% or 6%) | **+0.104396** = +time to the **next** reset | the running coupon is genuinely fixed, so the bump cannot move it |
| omitted (projected) | **−0.395604** = −time **since** the last reset | the bump reprices that period's coupon too, so the note behaves like a claim struck at the last reset |
| — | *same-maturity fixed bond: 17.44* | the comparison that makes both look small |

Both are within one coupon period, and the "supplied" case is independent of the coupon's
level. A **third**, different regime exists for a deep-discount note: price ≈ par minus a
spread annuity, so a rate rise shrinks the gap to par and the price *rises*, giving a negative
duration of order spread × annuity duration — and this one **grows with maturity**, unlike the
two above. A 57-year note marked near 50 shows ≈ −10.6.

Universal check: `|duration| ≪` a same-maturity fixed bond. That is the reliability test to
run when a floater's number looks surprising.

### The spread's meaning depends on an input

Most of this book's `coupon_formula` cells read "EURIBOR + Spread" with no number. Those notes
are priced with `quoted_margin_bp = 0`, and the calibrated spread then **absorbs the unknown
contractual margin as well as credit** — a discount-margin-type number, not a clean credit
spread. The price still reprices the mark exactly and the risk numbers are unaffected (a
floater's rate sensitivity is structural, not spread-level), and a real margin can be
separated back out later.

**The endpoint states which of the two meanings applies**, in `results.spread_interpretation`,
rather than leaving a reader to assume. Four notes have documented margins in
`data/frn_spreads.csv` (Bear L+40, PNC L+14, MS L+45, IndepComm L+182 — the first three
corrected to quarterly).

## 2. The hybrid engine (`core/pricing/hybrid.py`)

Fixed coupon to a contractual switch date, floating after. **Every** such bond in the URS book
was still inside its fixed leg at valuation, with switches from 2009 to 2037.

- **fixed leg** (valuation → switch): the vanilla engine's conventions, grid anchored at the
  **switch**, accrued off that grid, no face;
- **floating leg** (switch → maturity): the FRN engine's conventions, grid anchored at
  **maturity** and truncated at the switch, first period starting **at** the switch;
- **one curve and one calibrated spread discount both legs**, because it is one borrower's one
  promise. Splitting the spread would invent a second credit.

**Degenerate limits delegate rather than approximate**, so they agree bit-for-bit by
construction: switch ≥ maturity → the vanilla engine; switch ≤ valuation → the FRN engine.
Both are asserted with `==`.

**The composition itself is validated by the margin-0 identity**: with margin and spread both
zero, the floating leg telescopes *exactly* to `face × DF(t_switch)` on **any** curve, so the
hybrid equals a plain bullet maturing at the switch. That is the test that proves the two legs
are glued correctly rather than merely each being right.

**Perpetuals** truncate at 90 years, where the face is worth essentially nothing.

**`reference_oas_to_switch_bp`** is a secondary column — the spread of a bullet repaid at par
on the switch date. It is a real market convention while a bond trades near par and **actively
misleading for a deep discount**, where the market is pricing *extension*: a bond marked at 36
solves a spread of many hundreds of basis points that describes nothing. The response labels
it, and `implied_oas_bp` is always the answer.

## 3. The coupling that would have broken the migration

`hybrid.py` imported **private** names from `frn.py`:

```python
from pricing.frn import YEAR_DAYS, _as_date, _df, price_frn, simple_forward
```

The shim therefore re-exports the privates as well as the public surface, and there is a test
named after the reason:
`test_floating_shim_still_carries_the_private_helpers_hybrid_needs`. This was flagged in the
previous handoff as the single most likely way the migration would break, and naming it in
advance is why it did not.

## 4. Volatility policy

**A plain floater and a fixed-then-floating bond both have no volatility input, structurally**
— nobody holds an option, so there is nothing for rate volatility to act on. The endpoint
returns `null` (never `0.0`, which would read as a calculated vega) with a **per-product
reason**, not one generic line. A callable floater would need the tree; none is held.

## 5. What Round 2b actually proved

No numeric golden exists for these families — every relevant Monthly row is in the stale
2010-03-01 batch. So the evidence is:

- production driver CSVs **byte-identical** to a pre-change baseline after every code-bearing
  commit (all five files, hashed);
- endpoint and wrapper results equal to direct engine calls with **`==`**, not a tolerance;
- shim identity asserted on the **object** (`a is b`), not on equality;
- the invariants above, each with at least one exact anchor: the par-at-last-reset identity
  holds to 1e-12 at every curve level, the margin-0 telescoping is exact on any curve, and the
  two degenerate limits are bit-exact.

## 6. Route census (source: `outputs/implied_oas_2009-03-31.csv`, 565 rows)

Rows 12/14/15/16 = 27 tab rows, all 27 held: **7 FRN + 8 hybrid + 6 vanilla-schedule
re-routes = 21 priced**; 5 `hybrid-margin-unavailable` + 1 defaulted floater. Rows 6–11
(`Fixed → Reset`) = 6 tab / 6 held / 3 priced, 3 awaiting margins.

The 8 margin-gap names are **deliberately not half-modelled** — a guessed post-switch margin
prices the floating leg as if the borrower paid pure index and reports a confident number for
a bond nobody has fully specified. A margin fill is **one cell** in
`data/hybrid_switch_terms.csv` and the bond prices with zero code change.
