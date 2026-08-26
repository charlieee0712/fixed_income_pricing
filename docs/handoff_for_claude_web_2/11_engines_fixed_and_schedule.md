# Engines — fixed-rate, coupon-schedule, inflation-linked, mortgage

The non-option, non-floating engines. The tree is in `12`, floating and hybrid in `13`.

---

## 1. The plain fixed-rate bond (`core/pricing/analytical.py`)

A port of the legacy `BondPrice`, recomposed as orchestration over single-purpose functions:

```text
coupon_dates      the 364/182 backward schedule walk
bond_cashflows    (date, amount) table; face lands on the maturity flow
discount_factor   exp(-t·(z + oas))
accrued_interest  THE shared formula
clean = dirty - accrued
```

The price function itself is about 25 lines. Everything interesting is in the four helpers,
which is the point of the restructure.

**Returned object** (`PriceResult`): `clean`, `dirty`, `accrued`, `accrued_days`,
`last_coupon_date`, the per-cash-flow detail rows, and the `vba_compat` flag that produced
them. The per-flow detail carries both the continuous zero and the legacy semiannual zero,
so a reconciliation can see exactly where the two conventions diverge.

**Validated**: on the 2009-06-10 universe the method is unbiased — investment-grade signed
median −0.4%, and zero-OAS near-maturity high-grade bonds tie the custodian mark within
0.2%. The ~6.4% dispersion of the old rating-OAS approach was a design boundary of *that*
approach, and per-bond calibration removed it.

## 2. Coupon schedules (`pricing/coupon_schedule.py`, not yet migrated)

Free text such as *"7.50% until 2006 then 8.25%"* becomes `[(effective_date | None, rate)]`,
and `coupon_at(schedule, date)` resolves the rate in force. Threaded through `price_bond`,
`implied_oas` and `risk_metrics`.

The rule that matters: the parser returns **None, never a guess**, when a cell has no
numeric coupons. A bond with an unparseable schedule is flagged, not approximated.

Routes that use it: `vanilla-schedule` (9 bonds at 3-31) — stepped, rating-step and
documented coupon paths, including several where the workbook's own free text was wrong and
a primary-source override supplied the real path.

## 3. Inflation-linked (`pricing/ilb.py`)

Nominal own-currency curve, with an index ratio path
`ratio(t) = ratio_0 · (1 + FIP_INFL)^t`, where `ratio_0` is recovered per bond from the
custodian's `BG` column divided by the coupon parsed out of the security description.

**The output is not a credit spread and must never be reported as one.** At the default
assumption of zero inflation, the calibrated spread is approximately **minus the
breakeven** — π-at-spread-s is identically 0-at-(s − ln(1+π)), which is unit-tested. It
lives in its own column, `implied_spread_vs_nominal_bp`, with a companion `breakeven_bp`.

At the 3-31 baseline the extracted breakevens are the deflation-panic curve of March 2009:
−34 bp at 2010 rising to +139 bp at 2032. The JGBi's +229 bp spread corresponds to a −2.3%
Japanese breakeven — the sign flips correctly.

Known v1 boundary: the TIPS deflation floor is ignored, which needs inflation volatility to
model. One bond (KTBi) is BT-marked because its index ratio cannot be derived.

## 4. Mortgages (`pricing/mbs.py`) — a skeleton awaiting data

Built against the **exact 8-mnemonic Bloomberg interface** (`PoolTerms.from_bloomberg`), so
when the pull lands it is a data arrival and not a code change. Static-CPR, level-pay:
CPR → SMM, price / implied spread / implied CPR / risk / WAL.

Invariants are green (annuity degeneration, principal conservation, par-at-WAC, duration
falling as CPR rises). No production numbers exist yet, and none should be claimed.

Resolved along the way: `BZ > 1` factors are **correct** — they are REMIC accrual (Z / VZ /
ZC) tranches, not corrupt data.

## 5. Recovery and BT-marks

Defaulted bonds (route `recovery`) and any bond whose terms cannot be established are
carried at the custodian mark with a **named flag** and produce no model OAS. The flag
vocabulary is deliberately specific — `zero-structured`, `schedule-unavailable`,
`hybrid-margin-unavailable`, `reset-terms-unavailable`, `ilb-indexation-unverified`,
`frn-curve-blocked`, `cmo-tranche` — because "flagged" alone tells a later reader nothing
about what would unblock it.

## 6. What feeds all of them

- the bond's own-currency `ZeroCurve` (see `14`);
- terms from the `Corporate Bonds` tab, with the override CSVs taking precedence (see `16`);
- the custodian `BT` as the calibration target;
- for risk, a ±1 bp parallel shift of the spread, which for these engines is identical to a
  parallel curve shift.
