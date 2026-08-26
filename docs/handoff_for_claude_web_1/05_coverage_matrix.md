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
| **F** — plain fixed | 617 | `bond_price` vanilla · make-whole→vanilla · genuine-callable→BDT lattice (v2) | ✅ 522 priced (475 vanilla + **47 make-whole** — Sempra re-routed off the lattice 2026-07-20, make-whole documented) + 5 in the callable bucket (3 on the lattice); rest excluded for rating/maturity/terms |
| **floating** — Ref-Rate / EURIBOR / GBP-LIBOR + Spread, Fixed→Floating | 27 | `frn.py` FRN · `hybrid.py` **fixed-then-float** · override → vanilla-schedule | ✅ 7 FRN-priced (4 documented margins, `frn_spreads.csv`) + 5 vanilla-schedule (rating-step/plain-fixed re-routes) + **8 on the fixed-then-float engine** (Allstate/Lincoln/Liberty/Chubb/AmEx/GE/SMBC/BofA — all still in their FIXED leg at VAL; main column + price-to-call reference) · ⚠️ 7 flagged (5 `hybrid-margin-unavailable` [Resona-US, BTMU, Resona-EUR, Shinsei×2 — structure documented, post-switch margin on the Mario list], 1 GBP curve [FT — coupon path seeded], 1 defaulted) |
| **fixed-to-reset** | 6 | `hybrid.py` fixed-then-float · override → vanilla-schedule | ✅ **2 on the hybrid engine** (BNP L+129 sw-2037, UniCredit E+176 sw-2015 — perps truncated at 90y; replaces coupon-continuation) + 1 vanilla-schedule (TI-2033 plain fixed) · ⚠️ 3 `hybrid-margin-unavailable` (Chuo, Resona 4.125% + 144A tranche) |
| **stepped** — 7.00/7.50 date-segmented | 2 | `coupon_schedule` → vanilla | ✅ 1 priced (1 tab-only, not held) |
| **step-up** | 1 | `coupon_schedule` → vanilla | ✅ **priced** — flat 11.875% (Aquila: rating-linked steps all reversed by 2009; SEC-sourced) |
| **zero** — zero coupon / structured payoff | 1 | vanilla | ✅ **re-routed vanilla 6.95%** — the custodian 0% was a DATA ERROR (Comcast 6.95% due 2037), not a structured zero; OAS now 431bp (was −486bp artifact) |
| **defaulted** — N/A (Defaulted) | 1 | recovery mark | ✅ BT-mark, no OAS |
| **pass-through** | 16 | — | ⏳ Mario is sourcing the needed data on Bloomberg (meeting 2026-07-20); prepayment engine work starts when it lands. Out of the output until then. [was: excluded] |
| **amortizing** | 1 | — | ❌ ignore permanently (Mario, confirmed 2026-07-20) |
| **na** — N/A | 4 | — | ❌ ignore permanently (Mario, confirmed 2026-07-20) |
| **total** | **676** | | |

## Priced vs flagged vs excluded (output universe, 559 rows @6-10 / 564 @3-31)

Updated 2026-07-20 after the ISIN-lookup term overrides + the fixed-then-float hybrid engine
(`docs/isin_lookup_2026-07-20.md`; engine = `src/pricing/hybrid.py`):

- **548 priced end-to-end @6-10 (553 @3-31)** (implied OAS + effective duration / DV01 /
  convexity): vanilla 475 (480 @3-31), make-whole 47 (incl. Sempra), vanilla-schedule 9
  (stepped 1 + the 8 override paths), floating 7, **hybrid 10** (fixed-then-float main column +
  price-to-call reference; perps truncated at 90y; `next_switch_t` output per bond; kept OUT of
  the by-rating medians — jr-sub/T1 capital spreads, same policy as the floating route).
- **11 flagged / BT-mark**: **hybrid-margin-unavailable 8** (structure documented in
  `hybrid_switch_terms.csv`, post-switch margin on the Mario/Bloomberg list — incl. the previously
  FRN-priced BTMU/Resona-EUR and continuation-priced Chuo/Resona, deliberately not half-modelled),
  recovery 2, frn-curve-blocked 1 (FT GBP — coupon path seeded, curve blocked).
  reset-continuation is RETIRED (BNP/UniCredit → hybrid; Chuo/Resona → margin-unavailable).
- **21 excluded per Mario** (never enter the output): pass-through 16 (⏳ Mario sourcing Bloomberg
  data), amortizing 1, na 4 (permanent).
- Callable bucket now **5** (Sempra re-routed): 3 priced on the v2 BDT lattice, 1 awaiting a
  `call_schedules.csv` row (TNTD04923866).

## Interpretation guards (not bugs)

- **FRN effective duration** ~ time to next reset near par; a small (negative) credit-spread-annuity
  duration when deep-discount; universally `|eff-dur| ≪` a same-maturity fixed bond. See `frn.py`.
- **reset-continuation** durations are LONG (6–10y) — correct, they are priced as a continued fixed
  coupon. **price-to-call** is a reference column only; for a deep-discount name (e.g. TNTG533596W,
  BT 36) it solves a spurious OAS because the market prices extension, not the call.
- Implied OAS for flagged / distressed names is a recovery/calibration plug, **not** a clean spread.

## Data gaps — after the 2026-07-20 ISIN lookup

Most of the old gap table is CLOSED from public primary sources — per-bond evidence, the filled
tables (`coupon_schedules.csv` / `frn_spreads.csv` / `make_whole_overrides.csv` /
`hybrid_switch_terms.csv`) and the remaining **11-security Bloomberg request list for Mario** all
live in **`docs/isin_lookup_2026-07-20.md`**. What still stands:

| gap | bonds | status |
|---|---|---|
| post-switch/post-call floating margins | 11 (3 exempt US FRNs — all terms; 8 hybrids — margin only) | → Mario/Bloomberg list; a margin fill = one `hybrid_switch_terms.csv` cell → the bond moves onto the hybrid engine with zero code change |
| ~~fixed-then-float engine~~ | ~~10 hybrids~~ | ✅ **DONE 2026-07-20** — `src/pricing/hybrid.py`, all 10 priced (route `hybrid`) |
| GBP curve | FT-GBP 7.50% (coupon path seeded) + any GBP | non-arb 3y node blocks it |
| pass-through data | 16 | ⏳ Mario sourcing on Bloomberg (meeting 2026-07-20) |
