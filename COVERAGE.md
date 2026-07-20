# Coupon_Formula2 coverage map

Final coverage of the `Corporate Bonds` tab's **`Coupon_Formula2`** column (Mario 2026-07-08 task).
The module no longer defaults every bond to `F`: it reads `Coupon_Formula2`, classifies each bond,
and routes it to a pricing engine **or explicitly flags it** — nothing is silently mispriced.

- **pivot n** = the 676-row `Coupon_Formula2` classification (reconciles to Mario's pivot exactly;
  locked in `tests/test_universe.py`).
- **priced/flagged** counts are over the held/rated/matched universe at 2009-06-10
  (`outputs/implied_oas.csv`, 558 rows). Denominators differ: not every tab row is a held position.

## Class → engine → status

| `Coupon_Formula2` class | pivot n | engine / route | status @2009-06-10 |
|---|---|---|---|
| **F** — plain fixed | 617 | `bond_price` vanilla · make-whole→vanilla · genuine-callable→BDT lattice (v2) | ✅ 521 priced (475 vanilla + 46 make-whole) + 6 callable on the lattice; rest excluded for rating/maturity/terms |
| **floating** — Ref-Rate / EURIBOR / GBP-LIBOR + Spread, Fixed→Floating | 27 | `frn.py` forward-projection FRN | ✅ 18 priced · ⚠️ 9 flagged (5 switch-date, 2 perp, 1 GBP curve, 1 defaulted) |
| **fixed-to-reset** | 6 | coupon-continuation (vanilla) + price-to-call reference | ✅ 4 priced · ⚠️ 2 Variable → BT-mark |
| **stepped** — 7.00/7.50 date-segmented | 2 | `coupon_schedule` → vanilla | ✅ 1 priced (1 tab-only, not held) |
| **step-up** | 1 | `coupon_schedule` → vanilla | ⚠️ schedule-unavailable → BT-mark |
| **zero** — zero coupon / structured payoff | 1 | vanilla (degenerate, single CF) | ⚠️ priced but flagged: BT 93 ≠ a pure 28y zero (structured) |
| **defaulted** — N/A (Defaulted) | 1 | recovery mark | ✅ BT-mark, no OAS |
| **pass-through** | 16 | — | ⏳ Mario is sourcing the needed data on Bloomberg (meeting 2026-07-20); prepayment engine work starts when it lands. Out of the output until then. [was: excluded] |
| **amortizing** | 1 | — | ❌ ignore permanently (Mario, confirmed 2026-07-20) |
| **na** — N/A | 4 | — | ❌ ignore permanently (Mario, confirmed 2026-07-20) |
| **total** | **676** | | |

## Priced vs flagged vs excluded (output universe, 558 rows)

- **545 priced end-to-end** (implied OAS + effective duration / DV01 / convexity): vanilla 475,
  make-whole 46, floating 18, reset-continuation 4, stepped 1, zero-structured 1.
- **13 flagged / BT-mark** (awaiting terms): frn-switch-unavailable 5, recovery 2,
  reset-terms-unavailable 2, frn-no-maturity 2, schedule-unavailable 1, frn-curve-blocked 1.
- **21 excluded per Mario** (never enter the output): pass-through 16, amortizing 1, na 4.
- Genuine fixed callables (6) are priced separately on the v2 BDT lattice (`scripts/callable_risk.py`).

## Interpretation guards (not bugs)

- **FRN effective duration** ~ time to next reset near par; a small (negative) credit-spread-annuity
  duration when deep-discount; universally `|eff-dur| ≪` a same-maturity fixed bond. See `frn.py`.
- **reset-continuation** durations are LONG (6–10y) — correct, they are priced as a continued fixed
  coupon. **price-to-call** is a reference column only; for a deep-discount name (e.g. TNTG533596W,
  BT 36) it solves a spurious OAS because the market prices extension, not the call.
- Implied OAS for flagged / distressed names is a recovery/calibration plug, **not** a clean spread.

## Data gaps — awaiting Mario / Bloomberg (empty `data/coupon_schedules.csv` seeded)

| gap | bonds | needed |
|---|---|---|
| FRN spread | 18 FRNs | quoted spread ("... + Spread" carries no number → folded into OAS today) |
| Fixed→Floating switch date | 5 | the fixed→floating switch date |
| perpetual terms | 2 FRN + 3 reset | true perp handling (today: 90y truncation / BT-mark) |
| reset terms | 2 reset (Variable) | reset date + reset formula |
| step-up schedule | 1 | the step coupon table |
| zero structure | 1 | the structured-payoff terms |
| GBP curve | 1 GBP + any GBP | a usable GBP par curve (non-arb 3y node blocks it) |
