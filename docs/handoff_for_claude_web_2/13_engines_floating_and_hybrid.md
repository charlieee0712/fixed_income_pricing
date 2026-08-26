# Floating-rate notes and fixed-then-float hybrids

**Round 2b's migration target.** Both engines are validated and in production; neither has
moved into `pricer/` yet. Read this before writing that plan.

---

## 1. The FRN engine (`pricing/frn.py`, 188 lines)

**Method, settled 2026-07-08 with Mario:**

```text
coupon projection   simple implied forward off our own bootstrapped ZeroCurve:
                    F(t1,t2) = (DF(t1)/DF(t2) − 1) / (t2 − t1),  plus the quoted margin
discounting         the SAME curve plus a flat implied OAS (single-curve)
calibration         implied OAS solved to the clean custodian mark
effective duration  bump the CURVE, which REPROJECTS the forwards, then rediscount
```

Single-curve is the **2009 convention** and it matches what the legacy tree did. OIS
dual-curve is recorded in the code and docs as a future enhancement, not as a defect — that
transparency was a deliberate decision, not an oversight.

**Public surface**: `simple_forward`, `parse_frn_spread`, `price_frn`, `implied_oas_frn`,
`frn_risk_metrics`, and the `FrnResult` dataclass.

**Two behaviours that look like bugs and are not:**

- **duration bumps the curve, not the spread.** For a floater the coupon *follows* rates, so
  bumping the discount spread alone gives a meaningless answer. Bumping the curve reprojects
  the forwards, and the resulting duration is approximately the time to the next reset.
- **a deep-discount long floater can have NEGATIVE effective duration.** The 2066/2067
  floaters show about −10.7 against roughly +20 for a same-maturity fixed bond. They carry a
  credit-spread annuity, and that is what the sign is telling you.

**One bug fixed en route, worth remembering**: the stub (current) period's forward must
start at the true last reset, i.e. `t_prev < 0`. Otherwise the par-floater telescoping
identity breaks.

**Production**: 18 of 27 pure floaters priced at the time of the FRN round; 7 on the
`floating` route at 3-31 today (the difference is hybrids and margin-gap names being split
out). One is blocked by the unusable GBP curve.

**Validation is by invariant, not by golden** (there is no Bloomberg reference): par under
any curve shift when spread and OAS are zero; OAS round-trip; near-par duration ≈ 0; and the
signature check — FRN duration much smaller than a same-maturity fixed bond's, which holds
even at 78 years.

## 2. The hybrid engine (`pricing/hybrid.py`, 162 lines)

Fixed-then-float bonds: a fixed coupon to a switch date, then a floating leg. Composed
rather than reimplemented:

```text
fixed leg     price_bond's EXACT conventions, grid anchored at the SWITCH, accrued off it,
              no face
floating leg  price_frn's EXACT conventions, grid anchored at MATURITY truncated at the
              switch, first period starts AT the switch, forward·tau + the documented
              margin, face at maturity
glue          ONE curve and ONE implied OAS discount both legs
risk          curve bump (the FRN convention)
```

**Why this composition is trustworthy:**

- **degenerate limits delegate**: switch ≥ maturity calls `price_bond`; switch ≤ valuation
  calls `price_frn`. Bit-exact, by construction;
- **the margin-zero identity**: with spread = 0 and OAS = 0 the floating leg telescopes
  *exactly* to `face · DF(t_switch)` on **any** curve, so the hybrid equals a fixed-to-switch
  bullet. That is the composition test, and it is the reason the glue can be trusted.

**Production**: 10 fully-termed hybrids priced; 8 BT-marked `hybrid-margin-unavailable`
because their post-call margin is unknown. A margin arriving is **one CSV cell** in
`data/hybrid_switch_terms.csv` and the bond prices — zero code change.

At the valuation date **every** fixed-to-float hybrid was still in its fixed leg (switches
run 2009-10 to 2037). Two perpetuals truncate at 90 years, where the face PV is negligible.

`price-to-call` is reported as a **reference column only**: for a deep-discount name it is
spurious (the market is pricing extension, not the call). SMBC is the clearest example —
415 bp as a hybrid versus 1869 bp priced to call.

## 3. The coupling that will break the migration if ignored

```python
# src/pricing/hybrid.py
from pricing.frn import YEAR_DAYS, _as_date, _df, price_frn, simple_forward
```

The hybrid imports **private** names from the FRN module. Any shim left at `pricing/frn.py`
must re-export `_as_date`, `_df` and `YEAR_DAYS` as well as the public functions, or the
hybrid engine fails at **import time**. This is the single most likely way Round 2b goes
wrong.

Other import sites to update or preserve: `scripts/calibrate_risk.py`, `tests/test_frn.py`,
`tests/test_hybrid.py`, `tests/test_price_convention.py`.

## 4. Volatility policy for floaters

The current FRN engine is deterministic and has **no** stochastic volatility parameter. It
should report exactly that — `yield_volatility_applicable = false` with the reason — and
must not manufacture a zero vega. A callable FRN or a stochastic-rate FRN would be a
separate product extension, not a tweak to this engine.

That policy is also why FRN was moved out of the volatility-focused week: its honest answer
to Mario's question is "not applicable".

## 5. What Round 2b has to prove

1. the FRN implementation moves **verbatim** into `core/pricing/floating.py`, with
   `pricing/frn.py` as a shim that re-exports the privates;
2. every existing FRN **and hybrid** test stays green;
3. frozen production outputs (`outputs/implied_oas.csv` in particular) stay
   **byte-identical** — freeze before, compare after, by hash;
4. a thin `assets/corporate/floating.py` wrapper appears, with the same per-output function
   names as the other wrappers plus `next_reset_time`;
5. the endpoint gains `instrument_type` dispatch. A floater's input set genuinely differs —
   quoted margin, reset anchor, current coupon — so that contract deserves deciding in the
   plan rather than at the gate.
