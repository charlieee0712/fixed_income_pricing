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

Two kinds of caller, one catalogue
----------------------------------
* **Python callers** (drivers, tests, other engines) pass a ready ``curve`` object.
* **External callers** (the Excel/VBA bridge, a future HTTP service) cannot carry a
  curve across JSON, so they send **currency + valuation date + coupon frequency**
  and the endpoint layer resolves the curve for them
  (``core.market.curves.resolve_curve`` -> the bond's OWN-currency par curve). The
  ``external`` column below is the JSON path an external caller uses; ``-`` marks an
  input that exists only inside Python.

Nothing else differs: both callers reach the same validated functions, and currency
selects a *pricing curve* — it is never an instruction to re-FX a portfolio value
(the custodian's base-USD columns stay authoritative for that).

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
# are carried as data only (the legacy sheet marks these si / no / "not used");
# "external" is the JSON field an Excel/HTTP caller sends, "-" = Python-only.
INPUT_CATALOGUE = [
    {"n": 1, "field": "coupon", "type": "float",
     "external": "bond.coupon_pct",
     "options": "e.g. 6.5",
     "description": "Annual coupon in PERCENT (6.5 = 6.5%); 0 = zero-coupon.",
     "used": "all functions"},
    {"n": 2, "field": "cpn_freq", "type": "int",
     "external": "bond.coupon_frequency",
     "options": "1 / 2 / 4 / 12",
     "description": "Coupon payments per year: 1 annual, 2 semiannual, 4 quarterly, 12 monthly. "
                    "Also selects the matching bootstrap variant of the discount curve.",
     "used": "all functions"},
    {"n": 3, "field": "maturity", "type": "date",
     "external": "bond.maturity_date",
     "options": "ISO date, e.g. 2017-01-15",
     "description": "Bond maturity date.",
     "used": "all functions"},
    {"n": 4, "field": "valuation_date", "type": "date",
     "external": "market.valuation_date",
     "options": "ISO date, e.g. 2009-03-31",
     "description": "Date of valuation (t = 0). The par-curve file must carry a row for "
                    "exactly this date — no nearest-date substitution.",
     "used": "all functions"},
    {"n": 5, "field": "currency", "type": "str",
     "external": "bond.currency",
     "options": "USD / EUR / GBP / JPY / AUD / KRW",
     "description": "Pricing currency: selects the bond's OWN-currency par curve "
                    "(a non-USD bond discounted on the USD curve is mispriced). Case and "
                    "blanks are forgiven; an unmapped currency is refused, never silently "
                    "replaced by USD. NOT an FX instruction — portfolio values stay base-USD.",
     "used": "external callers (Python callers pass `curve` directly)"},
    {"n": 6, "field": "curve", "type": "ZeroCurve",
     "external": "-",
     "options": "flat_zero_curve(...) | resolve_curve(ccy, date, freq)",
     "description": "The discount curve (continuous zeros). Python callers build it; "
                    "external callers get it resolved from `currency` + `valuation_date` "
                    "+ `cpn_freq` by the endpoint layer.",
     "used": "all functions"},
    {"n": 7, "field": "market_price", "type": "float",
     "external": "market.clean_price_per_100",
     "options": "per 100 face",
     "description": "Existing CLEAN price of the bond, from Custodian or Bloomberg. This is "
                    "the calibration INPUT: the operation that solves for OAS needs it.",
     "used": "implied_oas only"},
    {"n": 8, "field": "oas", "type": "float",
     "external": "analysis.oas_bp",
     "options": "basis points",
     "description": "Flat spread over the curve, in bp. It is the OUTPUT of implied_oas "
                    "(calibrated per bond from the clean market price — the locked project "
                    "definition) and the INPUT of calculated_price / duration / dv01 / "
                    "convexity / widening / tightening. External callers therefore supply it "
                    "only in the price-at-a-given-spread operation; the calibrating operation "
                    "refuses it, so a market price and a hand-typed spread can never disagree.",
     "used": "price & risk functions"},
    {"n": 9, "field": "bp_adjust", "type": "float",
     "external": "analysis.spread_shift_bp",
     "options": "e.g. 10",
     "description": "Spread move in bp for the widening / tightening scenarios (legacy ±10).",
     "used": "widening / tightening"},
    {"n": 10, "field": "face", "type": "float",
     "external": "bond.face_value",
     "options": "default 100",
     "description": "Face value; prices and accrued scale with it. The JSON interface always "
                    "QUOTES per 100 face (its field names say so), so a face other than 100 is "
                    "echoed back with a warning and not applied — scale a position by par / 100.",
     "used": "all functions"},
    {"n": 11, "field": "coupon_schedule", "type": "list",
     "external": "-",
     "options": "[(date | None, rate), ...]",
     "description": "Dated coupon time-table (the 'Coupon Vector' input type) for "
                    "stepped / step-up bonds; overrides `coupon` when given.",
     "used": "all functions (optional)"},
    {"n": 12, "field": "day_count", "type": "str",
     "external": "bond.day_count_label",
     "options": "30/360, ACT/ACT, ...",
     "description": "Carried as DATA only. The engine's internal convention is the "
                    "validated legacy ACT/364 + 182-day grid; the legacy tool's own "
                    "dictionary says of this field: '30/360, but is not used'. An external "
                    "response states this back explicitly rather than staying silent.",
     "used": "NOT used in pricing"},
    {"n": 13, "field": "spread_over_libor", "type": "float",
     "external": "-",
     "options": "bp",
     "description": "Quoted margin of a FLOATING coupon. Floating engine only "
                    "(pricing.frn — migrates to assets/corporate in a later step).",
     "used": "floating only (not vanilla)"},
    {"n": 14, "field": "volatility", "type": "float",
     "external": "model.yield_volatility_decimal",
     "options": "e.g. 0.15",
     "description": "Yield volatility of the short-rate lattice. Vanilla is an option-free "
                    "deterministic DCF and has no volatility parameter at all, so: used by "
                    "vanilla = NO; used by callable / option-aware engines = YES; if an "
                    "external form supplies it on a vanilla request it is accepted, echoed and "
                    "not used, and the response returns null (never zero) for the volatility "
                    "sensitivities — a zero would read as a calculated vega.",
     "used": "callable only (not vanilla)"},
]

# The applicability statements the external layer echoes back for inputs a generic
# form will send but the vanilla engine does not consume. Kept next to the catalogue
# so the wording is maintained in ONE place.
VANILLA_NOT_APPLICABLE = {
    "volatility": "Option-free vanilla DCF has no direct yield-volatility parameter; "
                  "volatility drives the callable/option engines only.",
    "day_count": "The validated engine prices on the legacy ACT/364 convention with a "
                 "182-day coupon grid; the day-count label is carried as data only.",
}

PRICING_CONVENTION = "ACT/364 with a 182-day coupon grid"


def describe_inputs() -> str:
    """Render :data:`INPUT_CATALOGUE` as the legacy-style table.

    Inputs: none.
    Returns: str — one row per input
    ("No | Field | External JSON field | Options | Used | Description").
    """
    lines = [f"{'No':>2} | {'Field':<17} | {'External JSON field':<30} | "
             f"{'Options':<45} | Used | Description"]
    for row in INPUT_CATALOGUE:
        lines.append(f"{row['n']:>2} | {row['field']:<17} | {row['external']:<30} | "
                     f"{row['options']:<45} | {row['used']} | {row['description']}")
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
