# Code Walkthrough Guide — restructured sample (10 minutes)

*Prepared 2026-08-17 for the session with Mario and the Google team. Files referenced are
in the `code_structure_sample` folder; every claim below is backed by the automatic test
suite (166 green, ~10s).*

**Opening line:** "We restructured the corporate-bond pricing chain into Mario's template —
many simple functions, every input documented — and every number is bit-identical to the
validated engine. Here is the tour."

## The tour, in order

**1. `src/pricer/__init__.py` — the map (30 sec).**
Layout = `core/` (reusable engines, ~80%) + `assets/` (thin per-asset wrappers, ~20%).
The docstring table shows what is DONE vs PLANNED and which old module each piece came
from. Point out: the rest of the codebase migrates the same way once the shape is approved.

**2. `assets/corporate/vanilla.py` — one simple function per output (2 min).**
Open the module docstring: the table mapping each function to its legacy formula
(`implied_oas` ↔ `CorpBondOAS`, `duration` ↔ `CorpBondDuration`, `widening/tightening` ↔
`CorpBondwidening(±bp)`, plus new `dv01`/`convexity`). Open any one function: the
numbered Inputs block with units in capitals — this layer speaks the legacy sheet's units
(coupon in PERCENT, prices per 100, spreads in BASIS POINTS); the core engines underneath
work in decimals and the wrapper converts. **For the Google team:** all functions are pure
— no state, no globals — so every bond of a portfolio can be priced independently and in
parallel in the cloud.

**3. `assets/corporate/bonds_input.py` — the input catalogue (1 min).**
One table documenting every input, in the legacy Monthly sheet's own dictionary format
(No | Field | Options | Description | Used) — including which inputs are carried as data
but NOT used (e.g. `day_count`: the legacy tool's own dictionary says "30/360, but is not
used"). `validate_vanilla_inputs` fails fast with named-field messages (e.g. a coupon of
650 is rejected as "looks like bp — this layer takes PERCENT").

**4. `core/` — the engines, bottom-up (4 min).**
- `utils/dates.py`: the calendar. One year = 364 days, one semiannual period = 182 days —
  the legacy system's own convention, kept on purpose; changing it breaks reconciliation
  with every validated number. One shared schedule walk (`coupon_dates`).
- `pricing/cashflows.py`: the cash-flow table + THE one accrued-interest formula every
  engine shares (clean = dirty − accrued gives the same calibration root either way).
- `pricing/discounting.py`: `DF = exp(−t·(z+spread))` — the corrected convention that
  reprices the curve's own par bonds to exactly 100. The legacy discounting bug
  (semiannual zero in the continuous formula) is documented here and reproducible on
  demand via `vba_compat` — for reconciliation only, never the default.
- `pricing/analytical.py`: the price function is now just orchestration — dates → cash
  flows → discount each → sum → subtract accrued. ~25 lines of logic.
- `risk/sensitivities.py`: DV01 / effective duration / convexity as pure arithmetic on
  three prices, engine-agnostic: point `parallel_bump_metrics` at ANY pricing function.
- `market/spreads.py`: the OAS definition (a per-bond calibration factor solved from the
  market price — unique root because price is strictly decreasing in spread).

**5. Proof, then close (2 min).**
- `src/pricing/bond_price.py` (+ `calibrate.py`, `risk.py`): the old modules are thin
  shims re-exporting the new blocks — every existing script, test and number unchanged.
- `tests/test_pricer_structure.py`: bit-exactness is locked by tests, not promised —
  wrapper == engine to the last bit, unit round-trips, input validation.
- Validation beyond tests: we cross-checked the rebuilt engine against the Monthly
  sheet's own saved results (report §5) — the Dec-2012 batch matches essentially exactly
  (spreads within 1bp, durations to 4 decimals), and on older batches our durations track
  Bloomberg's closer than the sheet's saved values for 94% of bonds.

## Numbers to have ready

| Claim | Number |
|---|---|
| Automatic checks | **166 green**, ~10s (145 pre-existing unchanged + 8 structure + 13 Monthly-comparison locks) |
| Behavior change from restructure | **zero** — bit-identical (float-operation order preserved) |
| Monthly cross-check, Dec-2012 batch | spreads ≤1bp (the legacy solver's own precision), durations to 4 decimals, 100% within tolerance |
| Durations vs Bloomberg (older batch) | ours closer for **94%** of ~200 bonds |

## Likely questions — answers

- *"Why 364/182 days instead of real calendars?"* — It is the legacy engine's own
  convention; we keep it so every number reconciles. Real day-count labels are carried as
  data (`day_count` input) and can drive a future convention layer if wanted.
- *"Why is the file `bonds_input.py` when the template says `bons_input.py`?"* — The
  template's spelling looked like a typo; we asked Mario which to keep (report Q2). The
  docstring notes both.
- *"Why does `core/pricing/cashflows.py` import from the old `pricing` package?"* —
  `pricing.coupon_schedule` is a real not-yet-migrated module (moves into `core/` in the
  rollout), not one of the compatibility shims; the comment at the import says exactly that.
- *"Why divide duration by the dirty price?"* — The dirty price is the actual PV of the
  cash flows; accrued is yield-independent so the derivative is identical either way, only
  the divisor differs. Tested both ways against custodian durations (2026-08-04); dirty won.
- *"What about callable / floating / MBS?"* — Same pattern, planned modules are listed in
  `pricer/__init__.py`; they migrate in the approved rollout order, each with its tests.
- *"Can this run in the cloud / at scale?"* — Yes by construction: pure functions, no
  shared state, one bond per call; `endpoints/` (batch runners) is the planned entry layer.
