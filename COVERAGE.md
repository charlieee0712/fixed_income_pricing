# Coupon_Formula2 coverage map

Final coverage of the `Corporate Bonds` tab's **`Coupon_Formula2`** column (Mario 2026-07-08 task).
The module no longer defaults every bond to `F`: it reads `Coupon_Formula2`, classifies each bond,
and routes it to a pricing engine **or explicitly flags it** — nothing is silently mispriced.

- **pivot n** = the 676-row `Coupon_Formula2` classification (reconciles to Mario's pivot exactly;
  locked in `tests/test_universe.py`).
- **priced/flagged** counts are over the held/rated/matched universe
  (`outputs/implied_oas_2009-03-31.csv`, **565 rows** @3-31 / 560 @6-10, both refreshed
  2026-08-30). ⚠️ **Denominators differ and are easy to confuse**: 676 = tab rows,
  565 = held/rated/matched positions at the 3-31 baseline, 555 = of those, fully priced.

## Class → engine → status

| `Coupon_Formula2` class | pivot n | engine / route | status @2009-06-10 |
|---|---|---|---|
| **F** — plain fixed | 617 | `bond_price` vanilla · make-whole→vanilla · genuine-callable→BDT lattice (v2) | ✅ 522 priced (475 vanilla + **47 make-whole** — Sempra re-routed off the lattice 2026-07-20, make-whole documented) + 5 in the callable bucket (3 on the lattice); rest excluded for rating/maturity/terms |
| **floating** — Ref-Rate / EURIBOR / GBP-LIBOR + Spread, Fixed→Floating | 27 | `core/pricing/floating` FRN · `core/pricing/hybrid` **fixed-then-float** · override → vanilla-schedule | ✅ **21 of 27 tab rows priced @3-31** (all 27 are held positions; 7 FRN + 8 hybrid + 6 vanilla-schedule re-routes, incl. the GBP bond) · ⚠️ 5 `hybrid-margin-unavailable` (post-switch margin on the Bloomberg list) + 1 defaulted floater at its recovery mark. **Migrated to `pricer/` 2026-08-30 (Round 2b, Mario's F12/F14/F15/F16)**; wrappers `assets/corporate/{floating,hybrid}` |
| **fixed-to-reset** | 6 | `hybrid.py` fixed-then-float · override → vanilla-schedule | ✅ **2 on the hybrid engine** (BNP L+129 sw-2037, UniCredit E+176 sw-2015 — perps truncated at 90y; replaces coupon-continuation) + 1 vanilla-schedule (TI-2033 plain fixed) · ⚠️ 3 `hybrid-margin-unavailable` (Chuo, Resona 4.125% + 144A tranche) |
| **stepped** — 7.00/7.50 date-segmented | 2 | `core/pricing/coupon_schedule` → vanilla | ✅ 1 priced (1 tab-only, not held). **Migrated 2026-08-30 (Mario's F13)**; wrapper `assets/corporate/stepped` |
| **step-up** | 1 | `core/pricing/coupon_schedule` → vanilla | ✅ **priced** — flat 11.875% (Aquila: rating-linked steps all reversed by 2009; SEC-sourced). **Migrated 2026-08-30 (Mario's F20)** |
| **zero** — zero coupon / structured payoff | 1 | vanilla | ✅ **re-routed vanilla 6.95%** — the custodian 0% was a DATA ERROR (Comcast 6.95% due 2037), not a structured zero; OAS now 431bp (was −486bp artifact) |
| **defaulted** — N/A (Defaulted) | 1 | recovery mark | ✅ BT-mark, no OAS |
| **pass-through** | 16 | — | ⏳ Mario is sourcing the needed data on Bloomberg (meeting 2026-07-20); prepayment engine work starts when it lands. Out of the output until then. [was: excluded] |
| **amortizing** | 1 | — | ❌ ignore permanently (Mario, confirmed 2026-07-20) |
| **na** — N/A | 4 | — | ❌ ignore permanently (Mario, confirmed 2026-07-20) |
| **total** | **676** | | |

## Priced vs flagged vs excluded (output universe, 560 rows @6-10 / 565 @3-31)

Updated **2026-08-30** (Round 2b): the GBP par-yield units fix added two GBP bonds — one that
was `frn-curve-blocked` and one that was silently SKIPPED (a plain `Fixed` bond, i.e. in the
class already reported complete). See `src/curves/bootstrap.py` / `PAR_YIELD_UNITS`.
Engine paths are now `pricer/core/pricing/{floating,hybrid,coupon_schedule}` (the
`pricing.*` names are shims). Term-override background: `docs/isin_lookup_2026-07-20.md`.

- **550 priced end-to-end @6-10 (555 @3-31)** (implied OAS + effective duration / DV01 /
  convexity): vanilla 475 (480 @3-31), make-whole 47 (incl. Sempra), vanilla-schedule 9
  (stepped 1 + the 8 override paths + the GBP 7.50% whose curve was blocked), floating 7,
  **hybrid 10** (fixed-then-float main column +
  price-to-call reference; perps truncated at 90y; `next_switch_t` output per bond; kept OUT of
  the by-rating medians — jr-sub/T1 capital spreads, same policy as the floating route).
- **10 flagged / BT-mark**: **hybrid-margin-unavailable 8** (structure documented in
  `hybrid_switch_terms.csv`, post-switch margin on the Mario/Bloomberg list — incl. the previously
  FRN-priced BTMU/Resona-EUR and continuation-priced Chuo/Resona, deliberately not half-modelled),
  recovery 2. **`frn-curve-blocked` is now EMPTY** (was 1, the FT GBP bond) and the driver
  reports `skipped=0` (was 1).
  reset-continuation is RETIRED (BNP/UniCredit → hybrid; Chuo/Resona → margin-unavailable).
- **21 excluded per Mario** (never enter the output): pass-through 16 (⏳ Mario sourcing Bloomberg
  data), amortizing 1, na 4 (permanent).
- Callable bucket **5**, and all five are now NAMED rather than counted (2026-08-31 — a count
  of "5, of which 3 priced and 1 awaiting a schedule" accounted for only four, and the fifth
  turned out to be priced by nothing at all):

  | asset | gap | disposition |
  |---|---:|---|
  | `TNTD04441873` | 7243 d | priced on the BDT lattice |
  | `TNTG701850W` | 1809 d | priced on the BDT lattice |
  | `TNTD04115619` | 1096 d | priced on the BDT lattice |
  | `TNTD04923866` | 20819 d | `schedule-unavailable` — genuinely no call terms; on Liping's list |
  | `TNTD04920858` | **90 d** | `call-schedule-not-representable-on-current-grid` |

  `TNTD04920858` (US828807BX41, 5.00% due 2012-03-01, callable at par from 2011-12-02; held,
  par 850k, MV 723,542, custodian 85.12, A−/A3) sat in a hole between two thresholds — the
  universe routed gap ≤ 7d to vanilla and excluded the rest as `callable`, while the lattice
  driver only accepted gap > 366d. It appeared in **no output and no document**, with no
  message anywhere, and had been recorded once in the WORKLOG as a "minor loose end". The
  driver now consumes the whole bucket and applies no threshold of its own; deciding *whether*
  a bond is callable happens in one place only. Its call date falls inside the final coupon
  period, where the coupon-date lattice has no exercise node, so it is REFUSED rather than
  silently priced as a straight bond — see `docs/column_f_delivery_matrix_2026-08-31.md` §0
  and `tests/test_callable_disposition.py`.

- **Disposition is now mechanical, not counted.** `dataio/dispositions.reconcile` proves every
  candidate has exactly one named outcome over SETS of identifiers, and both drivers run it:
  `outputs/corporate_disposition.csv` (population 732 = 565 in-output + 167 named) and
  `outputs/callable_disposition.csv` (5 = 3 priced + 2 named skips). A count check balances
  even with the wrong bond in the wrong set, which is how two omissions survived.

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
| ~~GBP curve~~ | ~~FT-GBP 7.50% + any GBP~~ | ✅ **CLOSED 2026-08-30 — never a data gap.** The GBP par file is stored in PERCENT, not decimals; our loader scaled it by 100 and the bootstrap then correctly refused a 73%-415% curve. Both GBP bonds now price (205.3 / 197.3 bp @3-31). Request to Mario/Liping WITHDRAWN. |
| pass-through data | 16 | ⏳ Mario sourcing on Bloomberg (meeting 2026-07-20) |
