"""Corporate-bond input catalogue.

(Template position: ``assets/corporate/bons_input.py`` — that spelling is the
template's own; we named the file ``bonds_input.py`` and have asked Mario which
to keep — report question 2. Not a typo on either side.)

This module documents EVERY input the corporate-bond functions take, in the same
format the legacy workbook uses on its "Monthly" sheet (Input Number | Field Name |
Options | Description, plus whether the engine actually uses it). Units at this
asset layer follow the legacy convention — **coupon in percent (6.5 = 6.5%), prices
per 100 face, spreads in basis points**; the core engines underneath work in
decimals, and the wrappers in ``vanilla.py`` do the conversion.

The template's three input types map onto these fields as:
  Type 1 — Yield, Maturity, Coupon, Freq          -> flat yield via
           ``core.market.curves.flat_zero_curve`` + a single ``coupon``.
  Type 2 — Yield, Maturity, Coupon Vector         -> ``coupon_schedule`` (a dated
           coupon time-table; stepped / step-up bonds).
  Type 3 — Yield Vector, Maturity, Coupon, Freq   -> a bootstrapped ``ZeroCurve``
           (the production path: ``ZeroCurve.from_currency(data_dir, ccy, date)``).
"""
from __future__ import annotations

# One row per input, mirroring the legacy sheet's function dictionary.
# "used" tells the Google/cloud team exactly which inputs drive the number and which
# are carried as data only (the legacy sheet marks these si / no / "not used").
INPUT_CATALOGUE = [
    {"n": 1, "field": "coupon", "type": "float",
     "options": "e.g. 6.5",
     "description": "Annual coupon in PERCENT (6.5 = 6.5%); 0 = zero-coupon.",
     "used": "all functions"},
    {"n": 2, "field": "cpn_freq", "type": "int",
     "options": "1 / 2 / 4 / 12",
     "description": "Coupon payments per year: 1 annual, 2 semiannual, 4 quarterly, 12 monthly.",
     "used": "all functions"},
    {"n": 3, "field": "maturity", "type": "date",
     "options": "-",
     "description": "Bond maturity date.",
     "used": "all functions"},
    {"n": 4, "field": "valuation_date", "type": "date",
     "options": "-",
     "description": "Date of valuation (t = 0).",
     "used": "all functions"},
    {"n": 5, "field": "curve", "type": "ZeroCurve",
     "options": "flat_zero_curve(...) | ZeroCurve.from_currency(...)",
     "description": "The discount curve (continuous zeros). Build from the bond's OWN "
                    "currency: USD/EUR/GBP/JPY/AUD/KRW par files are mapped.",
     "used": "all functions"},
    {"n": 6, "field": "market_price", "type": "float",
     "options": "per 100 face",
     "description": "Existing CLEAN price of the bond, from Custodian or Bloomberg.",
     "used": "implied_oas only"},
    {"n": 7, "field": "oas", "type": "float",
     "options": "basis points",
     "description": "Flat spread over the curve, in bp. OUTPUT of implied_oas; INPUT "
                    "to calculated_price / duration / widening / tightening.",
     "used": "price & risk functions"},
    {"n": 8, "field": "bp_adjust", "type": "float",
     "options": "e.g. 10",
     "description": "Spread move in bp for the widening / tightening scenarios.",
     "used": "widening / tightening"},
    {"n": 9, "field": "face", "type": "float",
     "options": "default 100",
     "description": "Face value; prices and accrued scale with it.",
     "used": "all functions"},
    {"n": 10, "field": "coupon_schedule", "type": "list",
     "options": "[(date | None, rate), ...]",
     "description": "Dated coupon time-table (the 'Coupon Vector' input type) for "
                    "stepped / step-up bonds; overrides `coupon` when given.",
     "used": "all functions (optional)"},
    {"n": 11, "field": "day_count", "type": "str",
     "options": "30/360, ACT/ACT, ...",
     "description": "Carried as DATA only. The engine's internal convention is the "
                    "validated legacy ACT/364 + 182-day grid; the legacy tool's own "
                    "dictionary says of this field: '30/360, but is not used'.",
     "used": "NOT used in pricing"},
    {"n": 12, "field": "spread_over_libor", "type": "float",
     "options": "bp",
     "description": "Quoted margin of a FLOATING coupon. Floating engine only "
                    "(pricing.frn — migrates to assets/corporate in a later step).",
     "used": "floating only (not vanilla)"},
    {"n": 13, "field": "volatility", "type": "float",
     "options": "e.g. 0.15",
     "description": "Short-rate vol of the callable lattice. Callable engine only "
                    "(pricing.lattice -> core/pricing/tree.py in a later step).",
     "used": "callable only (not vanilla)"},
]


def describe_inputs() -> str:
    """Render :data:`INPUT_CATALOGUE` as the legacy-style four-column table.

    Inputs: none.
    Returns: str — one row per input ("No | Field | Options | Description | Used").
    """
    lines = [f"{'No':>2} | {'Field':<17} | {'Options':<45} | Used | Description"]
    for row in INPUT_CATALOGUE:
        lines.append(f"{row['n']:>2} | {row['field']:<17} | {row['options']:<45} | "
                     f"{row['used']} | {row['description']}")
    return "\n".join(lines)


def validate_vanilla_inputs(coupon: float, cpn_freq: int) -> None:
    """Fail fast on out-of-contract inputs (the checks are deliberately explicit).

    Inputs
    ------
    1. coupon   : float — annual coupon in PERCENT.
    2. cpn_freq : int — payments per year.

    Returns: None. Raises ``ValueError`` with a named-field message on violation.
    """
    if cpn_freq not in (1, 2, 4, 12):
        raise ValueError(f"cpn_freq must be 1, 2, 4 or 12 (payments/year); got {cpn_freq!r}")
    if coupon < 0.0:
        raise ValueError(f"coupon must be >= 0 (in percent, e.g. 6.5); got {coupon!r}")
    if coupon > 40.0:
        raise ValueError(f"coupon={coupon!r} looks like a decimal or bp value — "
                         f"this layer takes PERCENT (6.5 = 6.5%)")
