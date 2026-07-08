"""Coupon-structure classifier + engine routing for corporate bonds.

Mario (2026-07-08 call): the pricing module defaulted EVERY bond to ``F`` (plain fixed),
but the ``Corporate Bonds`` tab's ``Coupon_Formula2`` column carries the real coupon
structure. This module reads ``Coupon_Formula2`` and assigns each bond exactly ONE coupon
class, then routes that class to a pricing engine.

⚠️ Column check (convention trap): ``Coupon_Formula2`` is Excel column **M** (the header
confirms it; ``loaders.TAB_COLS`` maps ``M`` -> ``coupon_formula2``). Mario's brief said
"N列", but column N is empty in this workbook — **M is authoritative**.

Classes and routing (counts reconcile to Mario's 676-row ``Coupon_Formula2`` pivot):

    class            n   Coupon_Formula2 values                    engine (status)
    F              617   "Fixed"                                   vanilla            (done)
    floating        27   "Reference Rate + Spread" (12),           floating           (Step 4)
                         "EURIBOR + Spread" (9),
                         "Fixed -> Floating" (5),
                         "GBP LIBOR + Spread" (1)
    fixed-to-reset   6   "Fixed -> Reset (perpetual/144A/...)"     floating/reset     (Step 4)
    stepped          2   "7.00% for t<... 7.50% for t>=..."        vanilla-schedule   (Step 3)
    step-up          1   "Step-up schedule"                        vanilla-schedule   (Step 3)
    zero             1   "Zero coupon / structured payoff"         vanilla (single CF)(Step 3)
    defaulted        1   "N/A (Defaulted)"                         recovery-rate mark (Step 3)
    pass-through    16   "Pass-through cash flow"                  EXCLUDED (Mario)
    amortizing       1   "Amortizing (mortgage-backed)"            EXCLUDED (Mario)
    na               4   "N/A"                                     EXCLUDED (Mario)

Mario explicitly excludes pass-through / amortizing / na (~21: prepayment/amortization
models or unclassified). Everything else is in scope. ``unknown`` catches any blank or
unrecognised cell so nothing is ever silently priced as vanilla.
"""
from __future__ import annotations

import re

# ---- coupon classes ----
F = "F"
FLOATING = "floating"
FIXED_TO_RESET = "fixed-to-reset"
STEPPED = "stepped"
STEP_UP = "step-up"
ZERO = "zero"
DEFAULTED = "defaulted"
PASS_THROUGH = "pass-through"
AMORTIZING = "amortizing"
NA = "na"
UNKNOWN = "unknown"          # blank / unrecognised -> flagged, never silently priced

IN_SCOPE = frozenset({F, FLOATING, FIXED_TO_RESET, STEPPED, STEP_UP, ZERO, DEFAULTED})
EXCLUDED_CLASSES = frozenset({PASS_THROUGH, AMORTIZING, NA, UNKNOWN})

# ---- engines ----
VANILLA = "vanilla"                    # bond_price.py, fixed cash flows (incl. zero = single CF)
VANILLA_SCHEDULE = "vanilla-schedule"  # vanilla discounting over a known coupon time-table (Step 3)
FLOATING_ENGINE = "floating"           # forward-projection FRN engine (Step 4, not yet built)
RECOVERY = "recovery"                  # defaulted: price = recovery assumption / BT mark
EXCLUDED = "excluded"

ROUTE = {
    F: VANILLA,
    ZERO: VANILLA,
    STEPPED: VANILLA_SCHEDULE,
    STEP_UP: VANILLA_SCHEDULE,
    FLOATING: FLOATING_ENGINE,
    FIXED_TO_RESET: FLOATING_ENGINE,
    DEFAULTED: RECOVERY,
    PASS_THROUGH: EXCLUDED,
    AMORTIZING: EXCLUDED,
    NA: EXCLUDED,
    UNKNOWN: EXCLUDED,
}

# Controlled exclusion vocabulary for the Mario-excluded classes (used by the universe funnel).
EXCLUDED_REASON = {
    PASS_THROUGH: "excluded-per-Mario: requires prepayment model",
    AMORTIZING: "excluded-per-Mario: requires amortization model",
    NA: "excluded-per-Mario: unclassified (N/A)",
    UNKNOWN: "excluded: coupon_formula2 blank/unrecognised",
}


def _norm(s) -> str:
    """Normalise a raw cell: unify the unicode arrow/>=, drop nbsp, collapse whitespace."""
    if s is None:
        return ""
    s = str(s).replace("→", " -> ").replace("≥", ">=").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def classify_coupon_formula(formula2) -> str:
    """Map a raw ``Coupon_Formula2`` cell to exactly one coupon class.

    Order matters: the most specific structural signals (defaulted, pass-through, reset)
    are tested before the generic fixed/floating keywords, so e.g. ``Fixed -> Reset`` lands
    in ``fixed-to-reset`` and ``Fixed -> Floating`` in ``floating`` rather than ``F``.
    """
    t = _norm(formula2)
    low = t.lower()

    if "default" in low:                              # "N/A (Defaulted)"
        return DEFAULTED
    if low == "":
        return UNKNOWN
    if low == "n/a":
        return NA
    if "pass-through" in low or "pass through" in low:
        return PASS_THROUGH
    if "amortiz" in low or "amortis" in low:
        return AMORTIZING
    if "zero" in low:                                 # "Zero coupon / structured payoff"
        return ZERO
    if "step-up" in low or "step up" in low:
        return STEP_UP
    if "reset" in low:                                # "Fixed -> Reset (...)"
        return FIXED_TO_RESET
    if "-> floating" in low or "to floating" in low:  # "Fixed -> Floating"
        return FLOATING
    if "+ spread" in low or any(k in low for k in ("euribor", "libor", "sofr", "reference rate")):
        return FLOATING
    if "%" in low and ("t<" in low or "t>=" in low or "for t" in low):
        return STEPPED                                # "7.00% for t<... 7.50% for t>=..."
    if low == "fixed":
        return F
    return UNKNOWN


def route_for(coupon_class) -> str:
    """Engine for a coupon class (defaults to EXCLUDED for anything unmapped)."""
    return ROUTE.get(coupon_class, EXCLUDED)
