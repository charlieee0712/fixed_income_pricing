"""Securitised-pool input catalogue.

Companion to ``assets/corporate/bonds_input.py`` and ``assets/government/bonds_input.py``, in
the format the legacy workbook uses on its "Monthly" sheet (Input Number | Field Name | Options
| Description, plus whether the engine actually uses it). Units at this asset layer follow the
legacy convention — **rates in PERCENT (6.5 = 6.5%), prices per 100 current face, spreads in
basis points**; the core engine underneath works in decimals and the wrappers convert.

⚠️ **This is its OWN numbering.** It continues neither the corporate 1-17 nor the government
1-16. The legacy sheet keeps one dictionary per asset family and a reader who cross-references
"input 3" against the wrong family reads the wrong field, quietly: here input 3 is ``cpr``, in
the government catalogue it is ``cpn_freq``, in the corporate one it is ``maturity``. Three
dictionaries, none of which renumbers another.

⚠️ **Every ``external`` cell reads ``-``: none of these inputs is reachable from a worksheet.**
That is the same decision taken for the government inputs on 2026-09-10, for the same reason.
The Excel bridge has no cells for a weighted-average coupon, a remaining term in months or a
prepayment rate, and the project's 7/5/5 rule exists to keep an instrument type off a sheet
whose layout Mario has not chosen. The engine, the contract and the ``.bas`` are untouched by
this package.

What is genuinely different about a pool's inputs
-------------------------------------------------
* **There is no maturity date and no valuation date.** A pool is described by a remaining term
  in MONTHS (2) measured from the valuation date, not by a calendar maturity, and the month
  grid is anchored at the valuation date implicitly. Nothing here takes a date at all — which
  also means intra-month accrued and the agency payment delay are not modelled yet.
* **Two coupons, and they are not the same number.** The gross ``wac`` (1) is what the
  borrowers pay; ``net_coupon`` (4) is what reaches the investor after servicing and guarantee
  fees. Defaulting one to the other makes the servicing strip zero, which is a choice, not an
  identity.
* ⭐ **``cpr`` (3) and ``spread`` (6) cannot both be solved for.** One price identifies one
  unknown. The delivered Bloomberg pull is as-of 2026 (``scripts/mbs_data_check.py``), so its
  trailing CPRs cannot serve as the 2009 input; the adopted route fixes the spread near zero
  for government-guaranteed paper and solves for the CPR. See :func:`pool.implied_cpr_pct`.
* **``wala`` (10) and ``aols`` (11) drive nothing.** They are carried because the Bloomberg
  request returned them and because a later prepayment model will want them — seasoning and
  loan size are classic S-curve covariates. Under a constant CPR they are descriptive only, and
  the catalogue says so rather than leaving a reader to infer it from their absence.
"""
from __future__ import annotations

# One row per input, mirroring the legacy sheet's function dictionary.
# "used" tells the Google/cloud team which inputs drive the number and which are carried as
# data only; "external" is the JSON field an Excel/HTTP caller would send — "-" throughout,
# by the decision recorded in the module docstring.
INPUT_CATALOGUE = [
    {"n": 1, "field": "wac", "type": "float",
     "external": "-",
     "options": "e.g. 6.42",
     "description": "GROSS weighted-average coupon of the underlying loans, in PERCENT. What "
                    "the borrowers pay; drives the scheduled amortisation.",
     "used": "all functions"},
    {"n": 2, "field": "wam_months", "type": "int",
     "external": "-",
     "options": "months remaining, e.g. 289",
     "description": "Weighted-average remaining maturity in MONTHS, from the valuation date. "
                    "For the URS book this comes from the holdings file's own maturity dates, "
                    "not from Bloomberg — the delivered pull's WAM is as-of the pull.",
     "used": "all functions"},
    {"n": 3, "field": "cpr", "type": "float",
     "external": "-",
     "options": "0 to 99, in PERCENT per year",
     "description": "Constant prepayment rate, annualised, converted internally to the monthly "
                    "SMM. Held constant over the pool's life: the cash flows do NOT respond to "
                    "rates, so there is no prepayment option in the price.",
     "used": "all but implied_cpr_pct"},
    {"n": 4, "field": "net_coupon", "type": "float",
     "external": "-",
     "options": "e.g. 6.00; blank = equal to wac",
     "description": "PASS-THROUGH rate in PERCENT — what reaches the investor after servicing "
                    "and guarantee fees. Left blank the servicing strip is zero, which is an "
                    "assumption and not an identity.",
     "used": "all functions"},
    {"n": 5, "field": "curve", "type": "ZeroCurve",
     "external": "-",
     "options": "the pool's own currency",
     "description": "Nominal discount curve. Month-grid flows are discounted continuously at "
                    "z(t) plus the flat spread.",
     "used": "all functions"},
    {"n": 6, "field": "spread", "type": "float",
     "external": "-",
     "options": "BASIS POINTS; 0 = on-curve",
     "description": "Flat spread over the curve. For government-guaranteed paper ~0 is "
                    "defensible, which is what makes solving for the CPR instead possible.",
     "used": "all but implied_spread_bp"},
    {"n": 7, "field": "face", "type": "float",
     "external": "-",
     "options": "default 100",
     "description": "CURRENT face, not original. Pool quotes are per 100 of current balance, "
                    "so the pool factor is already applied upstream.",
     "used": "all functions"},
    {"n": 8, "field": "market_price", "type": "float",
     "external": "-",
     "options": "per 100 current face",
     "description": "The observed price a calibration solves against — the custodian's BT for "
                    "this book.",
     "used": "implied_cpr_pct, implied_spread_bp"},
    {"n": 9, "field": "bp_adjust", "type": "float",
     "external": "-",
     "options": "default 10",
     "description": "Scenario spread move in basis points for widening / tightening.",
     "used": "widening, tightening"},
    {"n": 10, "field": "wala", "type": "float",
     "external": "-",
     "options": "months",
     "description": "Weighted-average loan age. NOT USED by the constant-CPR model — carried "
                    "because a prepayment curve will need it (seasoning is an S-curve "
                    "covariate). Under a flat CPR it changes no number.",
     "used": "none (carried)"},
    {"n": 11, "field": "aols", "type": "float",
     "external": "-",
     "options": "dollars",
     "description": "Average ORIGINAL loan size. NOT USED by the constant-CPR model — carried "
                    "for the same reason as wala (loan size drives refinancing incentive).",
     "used": "none (carried)"},
]


def describe_inputs() -> str:
    """Render :data:`INPUT_CATALOGUE` as the legacy-style table.

    Inputs: none.
    Returns: str — one row per input
    ("No | Field | External JSON field | Options | Used | Description").
    """
    lines = [f"{'No':>2} | {'Field':<13} | {'External JSON field':<20} | "
             f"{'Options':<30} | Used | Description"]
    for row in INPUT_CATALOGUE:
        lines.append(f"{row['n']:>2} | {row['field']:<13} | {row['external']:<20} | "
                     f"{row['options']:<30} | {row['used']} | {row['description']}")
    return "\n".join(lines)


def validate_pool_inputs(wac: float, wam_months, cpr=None, net_coupon=None) -> None:
    """Fail fast on pool terms the engine cannot represent.

    Inputs
    ------
    1. wac         : float — gross coupon in PERCENT.
    2. wam_months  : int — remaining term in months.
    3. cpr         : float | None — prepayment rate in PERCENT, when the caller supplies one.
    4. net_coupon  : float | None — pass-through rate in PERCENT.

    Returns: None. Raises ``ValueError`` naming the offending field.

    ⚠️ Percent, not decimal. A WAC of 0.065 is a sixth of a basis point at this layer and will
    be refused rather than quietly priced as a near-zero-coupon pool — the units error this
    project has now made twice at data boundaries (``PAR_YIELD_UNITS``, ``TITLE_FACE``), caught
    both times only because something downstream looked wrong.
    """
    if wac is None or wac < 0:
        raise ValueError(f"wac must be a non-negative PERCENT; got {wac!r}")
    if wac > 0 and wac < 0.5:
        raise ValueError(
            f"wac={wac!r} looks like a decimal, not PERCENT — a pool coupon of {wac}% is "
            "below any mortgage rate ever written. Pass 6.42 for 6.42%.")
    if wam_months is None or int(wam_months) <= 0:
        raise ValueError(f"wam_months must be a positive number of months; got {wam_months!r}")
    if cpr is not None and not 0.0 <= cpr < 100.0:
        raise ValueError(f"cpr must be a PERCENT in [0, 100); got {cpr!r}")
    if net_coupon is not None and net_coupon < 0:
        raise ValueError(f"net_coupon must be a non-negative PERCENT; got {net_coupon!r}")
    if net_coupon is not None and net_coupon > wac:
        raise ValueError(
            f"net_coupon {net_coupon}% exceeds the gross wac {wac}% — the investor cannot "
            "receive more than the borrowers pay; the servicing strip would be negative.")
