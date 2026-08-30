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
     "external": "bond.coupon_schedule",
     "options": "[(date | None, rate), ...]",
     "description": "Dated coupon time-table (the 'Coupon Vector' input type) for "
                    "stepped / step-up bonds; overrides `coupon` when given. ⚠️ Rates "
                    "here are DECIMAL (0.075), the one exception to this layer's percent "
                    "rule — the parser and the override CSV both emit decimals, and two "
                    "dialects of the same object would be worse than one documented "
                    "exception. `stepped.validate_schedule` refuses a percent-looking one.",
     "used": "vanilla / stepped (optional)"},
    {"n": 12, "field": "day_count", "type": "str",
     "external": "bond.day_count_label",
     "options": "30/360, ACT/ACT, ...",
     "description": "Carried as DATA only. The engine's internal convention is the "
                    "validated legacy ACT/364 + 182-day grid; the legacy tool's own "
                    "dictionary says of this field: '30/360, but is not used'. An external "
                    "response states this back explicitly rather than staying silent.",
     "used": "NOT used in pricing"},
    {"n": 13, "field": "quoted_margin_bp", "type": "float",
     "external": "bond.quoted_margin_bp",
     "options": "bp, e.g. 45",
     "description": "Contractual margin over the floating index (formerly listed as "
                    "`spread_over_libor`). Floating + hybrid engines. When the workbook "
                    "cell reads '... + Spread' with no number, the margin is UNKNOWN: a "
                    "plain floater may be priced with 0 here and the calibrated spread "
                    "absorbs it (the response says so), but a HYBRID must not — an "
                    "invented post-switch margin is a half-modelled bond reported as a "
                    "whole one, so those are flagged instead.",
     "used": "floating / fixed-to-floating (not vanilla)"},
    {"n": 14, "field": "volatility", "type": "float",
     "external": "model.yield_volatility_decimal",
     "options": "e.g. 0.15",
     "description": "Yield volatility of the short-rate lattice. It has an effect only "
                    "where someone holds an early-repayment right: used by callable / "
                    "puttable / sinking = YES; used by vanilla, stepped, floating and "
                    "fixed-to-floating = NO, structurally — an option-free promise has "
                    "nothing for volatility to act on. When a generic form supplies it on "
                    "one of those, it is accepted, echoed, reported unused, and the "
                    "volatility sensitivities come back null (never zero) — a zero would "
                    "read as a calculated vega.",
     "used": "callable / puttable / sinking only"},
    {"n": 15, "field": "switch_date", "type": "date",
     "external": "bond.switch_date",
     "options": "ISO date, e.g. 2017-05-15",
     "description": "Fixed-to-floating bonds only: the date the coupon stops being fixed "
                    "and starts floating. It drives nearly all of the bond's rate risk, "
                    "because the floating leg after it largely resets its own risk away.",
     "used": "fixed-to-floating only"},
    {"n": 16, "field": "float_freq", "type": "int",
     "external": "bond.float_frequency",
     "options": "1 / 2 / 4 / 12, or blank",
     "description": "Fixed-to-floating bonds only: resets per year AFTER the switch, when "
                    "it differs from the fixed leg's frequency. Blank = same as `cpn_freq`.",
     "used": "fixed-to-floating (optional)"},
    {"n": 17, "field": "current_coupon", "type": "float",
     "external": "bond.current_coupon_pct",
     "options": "PERCENT, or blank",
     "description": "Floating notes only: the coupon already FIXED at the last reset, in "
                    "percent — the one payment on a floater that is not projected. Blank "
                    "= project that period off the curve like the others.",
     "used": "floating (optional)"},
]

# The applicability statements the external layer echoes back for inputs a generic
# form will send but a given engine does not consume. Kept next to the catalogue
# so the wording is maintained in ONE place.
VANILLA_NOT_APPLICABLE = {
    "volatility": "Option-free vanilla DCF has no direct yield-volatility parameter; "
                  "volatility drives the callable/option engines only.",
    "day_count": "The validated engine prices on the legacy ACT/364 convention with a "
                 "182-day coupon grid; the day-count label is carried as data only.",
}

# Why volatility does nothing, per instrument type. The reason differs by product, and
# saying WHICH reason is the difference between an answer and a shrug. Types absent from
# this map DO consume volatility (callable / puttable / sinking — they carry an option).
VOLATILITY_NOT_APPLICABLE = {
    "vanilla": VANILLA_NOT_APPLICABLE["volatility"],
    "stepped": "A stepped or step-up coupon varies over time but every payment is known "
               "today: the cash flows are deterministic and no one holds an option, so "
               "there is nothing for rate volatility to act on.",
    "floating": "A plain floating-rate note carries no early-repayment right. Its coupons "
                "are projected from the curve, and rate volatility enters neither the "
                "projection nor the discounting of a spread-calibrated note.",
    "fixed_to_floating": "A fixed-then-floating bond is two option-free legs discounted on "
                         "one curve; the switch is a contractual date, not a choice anyone "
                         "makes, so volatility has nothing to act on. (Where such a bond "
                         "also carries an issuer call at the switch, that call belongs on "
                         "the tree engine and is priced there, not here.)",
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


# A quoted margin wider than this (bp) is taken as a units mistake rather than a real
# note: the widest documented margin in this book is 357.6 bp, and 5000 bp = 50%.
_MAX_MARGIN_BP = 5000.0


def validate_frequency(cpn_freq: int, field: str = "cpn_freq") -> None:
    """Fail fast on a coupon/reset frequency the engines do not support.

    Inputs
    ------
    1. cpn_freq : int — payments (or resets) per year.
    2. field    : str — the field name to quote in the message.

    Returns: None. Raises ``ValueError`` naming the field.
    """
    if cpn_freq not in (1, 2, 4, 12):
        raise ValueError(f"{field} must be 1, 2, 4 or 12 (payments/year); got {cpn_freq!r}")


def validate_margin_bp(quoted_margin_bp: float) -> None:
    """Fail fast on an out-of-contract quoted margin.

    Inputs
    ------
    1. quoted_margin_bp : float — contractual margin over the index, in BASIS POINTS.

    Returns: None. Raises ``ValueError`` on a negative margin or one so wide it is almost
    certainly a decimal (0.0045) or percent (0.45) value sent where bp (45) was expected.
    """
    if quoted_margin_bp is None:
        raise ValueError("quoted_margin_bp is None — an unknown margin must be flagged as "
                         "a data gap, not passed to the engine")
    if quoted_margin_bp < 0.0:
        raise ValueError(f"quoted_margin_bp must be >= 0 (basis points); "
                         f"got {quoted_margin_bp!r}")
    if quoted_margin_bp > _MAX_MARGIN_BP:
        raise ValueError(f"quoted_margin_bp={quoted_margin_bp!r} exceeds "
                         f"{_MAX_MARGIN_BP:g} bp — this input takes BASIS POINTS (45 = 45 bp)")


def validate_floating_inputs(cpn_freq: int, quoted_margin_bp: float,
                             current_coupon_pct=None) -> None:
    """Fail fast on out-of-contract floating-note inputs.

    Inputs
    ------
    1. cpn_freq           : int — resets per year (1, 2, 4, 12).
    2. quoted_margin_bp   : float — contractual margin in BASIS POINTS (0 = unknown,
       absorbed into the calibrated spread).
    3. current_coupon_pct : float | None — the already-fixed current coupon, in PERCENT.

    Returns: None. Raises ``ValueError`` with a named-field message on violation. Note
    there is deliberately no ``coupon`` check: a floater has no coupon input at all.
    """
    validate_frequency(cpn_freq)
    validate_margin_bp(quoted_margin_bp)
    if current_coupon_pct is not None:
        if current_coupon_pct < 0.0:
            raise ValueError(f"current_coupon_pct must be >= 0 (in percent); "
                             f"got {current_coupon_pct!r}")
        if current_coupon_pct > 40.0:
            raise ValueError(f"current_coupon_pct={current_coupon_pct!r} looks like a "
                             f"decimal or bp value — this layer takes PERCENT")


def validate_hybrid_inputs(fixed_coupon_pct: float, cpn_freq: int,
                           quoted_margin_bp: float) -> None:
    """Fail fast on out-of-contract fixed-then-floating inputs.

    Inputs
    ------
    1. fixed_coupon_pct : float — the fixed-leg coupon in PERCENT.
    2. cpn_freq         : int — fixed-leg payments per year.
    3. quoted_margin_bp : float — post-switch margin in BASIS POINTS.

    Returns: None. Raises ``ValueError`` with a named-field message on violation.

    The margin is validated as strictly as the coupon here, and that is the point: an
    unknown post-switch margin must reach the flagging layer as a data gap, never this
    engine with a placeholder zero (which would silently price the floating leg as if
    the borrower paid pure index).
    """
    validate_vanilla_inputs(fixed_coupon_pct, cpn_freq)
    validate_margin_bp(quoted_margin_bp)
