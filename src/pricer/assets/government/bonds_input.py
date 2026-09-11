"""Government-bond input catalogue.

Companion to ``assets/corporate/bonds_input.py``, in the same format the legacy workbook uses
on its "Monthly" sheet (Input Number | Field Name | Options | Description, plus whether the
engine actually uses it). Units at this asset layer follow the legacy convention — **coupons
and inflation in PERCENT (6.5 = 6.5%), prices per 100 face, spreads in basis points**; the core
engines underneath work in decimals and the wrappers convert.

⚠️ **This is its OWN numbering, not a continuation of the corporate catalogue's 1-17.** The
legacy sheet keeps one input dictionary per asset family, and a reader who cross-references
"input 9" against the wrong family reads the wrong field description — quietly. Government
input 9 is ``spread_vs_nominal_bp``; corporate input 9 is ``bp_adjust``. They are different
dictionaries and neither renumbers the other.

⚠️ **Every ``external`` cell below reads ``-``: none of these inputs is reachable from a
worksheet.** That is a decision, not an omission (2026-09-10). The Excel bridge has no cells
for a real coupon, an index ratio or an inflation assumption, and the project's 7/5/5 rule
exists to keep an instrument type off a sheet whose layout Mario has not chosen. When those
cells exist, the endpoint contract gains an eighth instrument type and these fields gain
external names; until then the government engines are reached from Python only.

What is genuinely different about a government book's inputs
------------------------------------------------------------
* **A linker's coupon is REAL, not nominal**, and is a separate input (1) from the nominal
  coupon (2) an agency or guaranteed bond pays. Passing one where the other belongs is a
  modelling error that no amount of unit checking would catch, which is why they never share
  a field name.
* **A linker is priced on the NOMINAL curve** (input 7) plus an explicit index path, because
  this project has no real-yield curves. The calibrated spread (9) is therefore *not* a credit
  spread — see ``linker.implied_spread_vs_nominal_bp``.
* **Volatility (13) is an input for exactly one route**: the five agency debentures with a
  live call. Everything else here is optionless, so volatility has nothing to act on — the
  same structural statement ``vanilla.py`` and ``floating.py`` make.
"""
from __future__ import annotations

# One row per input, mirroring the legacy sheet's function dictionary.
# "used" tells the Google/cloud team which inputs drive the number and which are carried as
# data only; "external" is the JSON field an Excel/HTTP caller would send — "-" throughout,
# by the 2026-09-10 decision recorded in the module docstring.
INPUT_CATALOGUE = [
    {"n": 1, "field": "real_coupon", "type": "float",
     "external": "-",
     "options": "e.g. 3.875",
     "description": "REAL annual coupon in PERCENT for an inflation-linked bond. Every cash "
                    "flow is this coupon scaled by the index ratio; it is NOT the cash coupon "
                    "the bond pays today.",
     "used": "linker"},
    {"n": 2, "field": "coupon", "type": "float",
     "external": "-",
     "options": "e.g. 5.25; 0 = zero-coupon",
     "description": "NOMINAL annual coupon in PERCENT. Agency STRIPS carry a coupon below "
                    "dataio.phase2.ZERO_COUPON_MAX_PCT and route to zero.",
     "used": "agency, guaranteed"},
    {"n": 3, "field": "cpn_freq", "type": "int",
     "external": "-",
     "options": "1 / 2 / 4 / 12",
     "description": "Coupon payments per year. Also selects the matching bootstrap variant of "
                    "the discount curve.",
     "used": "all functions"},
    {"n": 4, "field": "maturity", "type": "date",
     "external": "-",
     "options": "ISO date, e.g. 2032-04-15",
     "description": "Bond maturity date.",
     "used": "all functions"},
    {"n": 5, "field": "valuation_date", "type": "date",
     "external": "-",
     "options": "ISO date, e.g. 2009-03-31",
     "description": "Date of valuation (t = 0). The par-curve file must carry a row for "
                    "exactly this date — no nearest-date substitution.",
     "used": "all functions"},
    {"n": 6, "field": "currency", "type": "str",
     "external": "-",
     "options": "USD / JPY / KRW / ...",
     "description": "Pricing currency: selects the bond's OWN-currency curve. A Japanese "
                    "linker discounted on the USD curve is mispriced.",
     "used": "all functions"},
    {"n": 7, "field": "curve", "type": "ZeroCurve",
     "external": "-",
     "options": "ZeroCurve.from_currency(data_dir, ccy, date)",
     "description": "The NOMINAL own-currency zero curve. ⚠️ For a linker this is deliberate, "
                    "not an approximation of a missing real-yield curve: the index path is "
                    "modelled explicitly by inputs 11 and 12 instead.",
     "used": "all functions"},
    {"n": 8, "field": "market_price", "type": "float",
     "external": "-",
     "options": "per 100 face, e.g. 152.7969",
     "description": "Existing CLEAN price the calibration targets (the custodian mark). For a "
                    "linker this is the inflation-ADJUSTED price, which is why the model clean "
                    "— which carries the ratio — calibrates to it directly.",
     "used": "implied_spread_vs_nominal_bp, implied_oas"},
    {"n": 9, "field": "spread_vs_nominal_bp", "type": "float",
     "external": "-",
     "options": "bp; NEGATIVE is the norm",
     "description": "Flat spread over the nominal curve for a linker, in BASIS POINTS. ⚠️ At a "
                    "zero inflation assumption this is approximately MINUS the market breakeven "
                    "inflation rate, never a credit spread. See linker.py.",
     "used": "linker"},
    {"n": 10, "field": "oas", "type": "float",
     "external": "-",
     "options": "bp",
     "description": "Flat option-adjusted spread over the nominal curve, in BASIS POINTS, for "
                    "the optionless and callable nominal bonds.",
     "used": "agency, guaranteed"},
    {"n": 11, "field": "index_ratio", "type": "float",
     "external": "-",
     "options": "e.g. 1.3054",
     "description": "The bond's accrued-inflation ratio AT the valuation date (t = 0); scales "
                    "every cash flow and the accrued. Recovered per bond by dataio.phase2 from "
                    "the custodian income rate divided by the description coupon. ⚠️ The "
                    "plausibility window for a RECOVERED ratio is the loader's "
                    "(dataio.phase2.RATIO_SANITY); this layer validates only that the ratio is "
                    "positive, so a synthetic or stress value prices normally.",
     "used": "linker"},
    {"n": 12, "field": "inflation_pct", "type": "float",
     "external": "-",
     "options": "PERCENT per year; production uses 0",
     "description": "Assumed annual inflation for the index path, ratio(t) = index_ratio * "
                    "(1 + inflation)**t. Production runs at 0 so that the calibrated spread is "
                    "read directly as a breakeven — see FIP_INFL in scripts/phase2_risk.py.",
     "used": "linker"},
    {"n": 13, "field": "volatility", "type": "float",
     "external": "-",
     "options": "decimal, e.g. 0.15",
     "description": "Short-rate volatility for the BDT lattice. Used ONLY by the five agency "
                    "debentures with a live call; every other security here is optionless, so "
                    "volatility has nothing to act on and the sensitivities are reported unused "
                    "rather than as zero.",
     "used": "agency (callable route only)"},
    {"n": 14, "field": "call_schedule", "type": "list",
     "external": "-",
     "options": "[(time_in_years, price_per_100), ...]",
     "description": "The exercise table, from data/call_schedules.csv via dataio.call_schedules. "
                    "⚠️ Never inferred and never defaulted to a par call in code: the par-call "
                    "convention is applied when the row is SEEDED, and every seeded row is "
                    "labelled provisional.",
     "used": "agency (callable route only)"},
    {"n": 15, "field": "face", "type": "float",
     "external": "-",
     "options": "default 100",
     "description": "Face value the price is quoted per. For a linker this is the ORIGINAL "
                    "unindexed face; indexation is carried by input 11.",
     "used": "all functions"},
    {"n": 16, "field": "bp_adjust", "type": "float",
     "external": "-",
     "options": "bp, e.g. 50",
     "description": "Parallel spread move for the widening / tightening scenario functions.",
     "used": "widening, tightening"},
]


def describe_inputs() -> str:
    """Render :data:`INPUT_CATALOGUE` as the legacy-style table.

    Inputs: none.
    Returns: str — one row per input
    ("No | Field | External JSON field | Options | Used | Description").
    """
    lines = [f"{'No':>2} | {'Field':<21} | {'External JSON field':<20} | "
             f"{'Options':<38} | Used | Description"]
    for row in INPUT_CATALOGUE:
        lines.append(f"{row['n']:>2} | {row['field']:<21} | {row['external']:<20} | "
                     f"{row['options']:<38} | {row['used']} | {row['description']}")
    return "\n".join(lines)


def validate_frequency(cpn_freq: int, field: str = "cpn_freq") -> None:
    """Fail fast on a coupon frequency the engines do not support.

    Inputs
    ------
    1. cpn_freq : int — payments per year.
    2. field    : str — the field name to quote in the message.

    Returns: None. Raises ``ValueError`` naming the field.
    """
    if cpn_freq not in (1, 2, 4, 12):
        raise ValueError(f"{field} must be 1, 2, 4 or 12 (payments/year); got {cpn_freq!r}")


def validate_linker_inputs(real_coupon: float, cpn_freq: int, index_ratio: float,
                           inflation_pct: float) -> None:
    """Fail fast on out-of-contract inflation-linked inputs.

    Inputs
    ------
    1. real_coupon   : float — REAL annual coupon in PERCENT.
    2. cpn_freq      : int — payments per year.
    3. index_ratio   : float — accrued-inflation ratio at the valuation date.
    4. inflation_pct : float — assumed annual inflation, PERCENT.

    Returns: None. Raises ``ValueError`` with a named-field message on violation.

    ⚠️ This checks the CONTRACT, not the data. The plausibility window for a ratio recovered
    from the custodian file belongs to ``dataio.phase2.RATIO_SANITY`` and stays there; a
    synthetic ratio outside it is a legitimate thing to price and is not refused here.
    """
    validate_frequency(cpn_freq)
    if real_coupon < 0.0:
        raise ValueError(f"real_coupon must be >= 0 (in percent, e.g. 3.875); got {real_coupon!r}")
    if real_coupon > 40.0:
        raise ValueError(f"real_coupon={real_coupon!r} looks like a decimal or bp value — "
                         f"this layer takes PERCENT (3.875 = 3.875%)")
    if index_ratio <= 0.0:
        raise ValueError(f"index_ratio must be > 0 (it multiplies every cash flow); "
                         f"got {index_ratio!r}")
    if inflation_pct <= -100.0:
        raise ValueError(f"inflation_pct must be > -100 (the index path would go non-positive); "
                         f"got {inflation_pct!r}")
    if abs(inflation_pct) > 100.0:
        raise ValueError(f"inflation_pct={inflation_pct!r} looks like a decimal or a multiple — "
                         f"this layer takes PERCENT (2.0 = 2% per year)")


def validate_agency_inputs(coupon: float, cpn_freq: int, volatility=None) -> None:
    """Fail fast on out-of-contract nominal government-bond inputs.

    Inputs
    ------
    1. coupon     : float — NOMINAL annual coupon in PERCENT.
    2. cpn_freq   : int — payments per year.
    3. volatility : float | None — short-rate volatility (decimal) for the callable route;
       ``None`` for every optionless bond.

    Returns: None. Raises ``ValueError`` with a named-field message on violation.
    """
    validate_frequency(cpn_freq)
    if coupon < 0.0:
        raise ValueError(f"coupon must be >= 0 (in percent, e.g. 5.25); got {coupon!r}")
    if coupon > 40.0:
        raise ValueError(f"coupon={coupon!r} looks like a decimal or bp value — "
                         f"this layer takes PERCENT (5.25 = 5.25%)")
    if volatility is not None:
        if volatility <= 0.0:
            raise ValueError(f"volatility must be > 0 when a call is priced; got {volatility!r}")
        if volatility > 2.0:
            raise ValueError(f"volatility={volatility!r} looks like a percentage — this field "
                             f"takes a decimal (0.15 = 15%)")
