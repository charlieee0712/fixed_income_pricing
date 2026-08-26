"""Yield-curve operations (template: ``core/market/curves.py``).

MIGRATION POINTER: the validated curve stack still lives in ``curves/`` —
``curves.bootstrap`` (par -> zero bootstrap, golden-tested against the legacy sheets)
and ``curves.zero_curve.ZeroCurve`` (linear-interp continuous zeros + per-currency
routing). They are re-exported here so template-layout code imports from ONE place;
the modules themselves move here in a later migration step (their golden tests come
with them — do not fork the implementations).

This module also owns the ONE routing seam every caller needs: *which* curve does a
bond get? :func:`resolve_curve` answers it from the bond's own currency, the valuation
date and the coupon frequency, and raises a single, path-free :class:`CurveUnavailable`
when it cannot — so an external caller (the JSON endpoint, a future HTTP service) can
report the failure without pattern-matching on somebody else's error text.
"""
from __future__ import annotations

import math

import pandas as pd

from curves.zero_curve import CURVE_FILE, ZeroCurve  # noqa: F401  (re-export)

# Coupon frequency (payments per year) -> which bootstrap variant discounts it. The
# variant must match the bond's own frequency: the bootstrap solves a different zero
# grid per compounding convention. Same map the production drivers use.
CURVE_FREQ_VARIANT = {1: "Annual", 2: "Semiannual", 4: "Quarterly", 12: "Monthly"}

_DEFAULT_DATA_DIR = "data"


class CurveUnavailable(Exception):
    """No curve could be provided for a (currency, date, frequency) request.

    ``reason`` separates the two cases a caller has to explain differently:

        "not_found"     the currency has no configured par-curve file, or that file
                        has no row for the requested valuation date;
        "build_failed"  the file and the date are both there, but the bootstrap
                        refuses the curve (e.g. a non-arbitrage-free par node).

    The message is always path-free — data locations never travel to an external
    caller (the underlying loaders do put file paths in their own messages).
    """

    def __init__(self, message: str, reason: str = "not_found"):
        super().__init__(message)
        self.reason = reason


def flat_zero_curve(rate: float, max_tenor: float = 60.0,
                    freq: str = "Semiannual") -> ZeroCurve:
    """Build a flat zero curve — input Type 1 ("Yield" as a single number) of the
    corporate ``bonds_input`` catalogue; also the workhorse of invariance tests.

    Inputs
    ------
    1. rate      : float — the flat continuous zero rate, DECIMAL (0.04 = 4%).
    2. max_tenor : float — last grid node in years (default 60; interpolation is
       flat everywhere, extrapolation clamps).
    3. freq      : str — which bootstrap variant the grid mimics (default Semiannual).

    Returns: :class:`ZeroCurve` serving ``rate`` at every tenor.
    """
    grid = pd.DataFrame({
        "Maturity": [0.01, max_tenor],
        f"{freq}_Rate": [rate * 100.0, rate * 100.0],
        f"{freq}_DF": [math.exp(-rate * 0.01), math.exp(-rate * max_tenor)],
    })
    return ZeroCurve(grid, freq=freq)


def curve_variant(coupon_frequency: int) -> str:
    """Bootstrap variant that discounts a bond paying ``coupon_frequency`` times a year.

    Inputs
    ------
    1. coupon_frequency : int — payments per year (1, 2, 4, 12).

    Returns: str — "Annual" / "Semiannual" / "Quarterly" / "Monthly".
    Raises ``ValueError`` on any other frequency.
    """
    try:
        return CURVE_FREQ_VARIANT[int(coupon_frequency)]
    except (KeyError, TypeError, ValueError):
        raise ValueError(
            f"coupon frequency {coupon_frequency!r} has no curve variant "
            f"(supported: {sorted(CURVE_FREQ_VARIANT)})"
        ) from None


def supported_currencies() -> list:
    """Currencies with a configured par-curve file, sorted.

    Inputs: none.
    Returns: list[str] — e.g. ``['AUD', 'EUR', 'GBP', 'JPY', 'KRW', 'USD']``.
    """
    return sorted(CURVE_FILE)


def resolve_curve(currency, valuation_date, coupon_frequency: int = 2,
                  data_dir: str = _DEFAULT_DATA_DIR) -> ZeroCurve:
    """THE curve-routing seam: the discount curve for one bond, in its OWN currency.

    Inputs
    ------
    1. currency         : str — ISO code; case and surrounding blanks are forgiven.
    2. valuation_date   : date-like — the pricing "as of" date; the par-curve file
       must carry a row for exactly this date (no nearest-date substitution — a
       silently shifted curve is worse than a refusal).
    3. coupon_frequency : int — payments per year; picks the bootstrap variant.
    4. data_dir         : str — directory holding the ``*_Yield_Curve.txt`` exports
       (the endpoint layer supplies this from configuration).

    Returns: :class:`ZeroCurve` for that currency/date/variant.
    Raises :class:`CurveUnavailable` (never a loader-specific error, never a path).
    """
    code = str(currency).strip().upper()
    if code not in CURVE_FILE:
        raise CurveUnavailable(
            f"no yield curve is configured for currency {code!r} "
            f"(configured: {', '.join(supported_currencies())})",
            reason="not_found",
        )
    variant = curve_variant(coupon_frequency)
    date_label = _date_label(valuation_date)
    try:
        return ZeroCurve.from_currency(data_dir, code, valuation_date, freq=variant)
    except ValueError as exc:
        if "not found in" in str(exc):          # loader: the date has no row
            raise CurveUnavailable(
                f"the {code} par-curve file has no row for valuation date {date_label}",
                reason="not_found",
            ) from None
        raise CurveUnavailable(                 # bootstrap: the curve itself is unusable
            f"the {code} par curve for {date_label} could not be bootstrapped "
            f"({variant} variant): {_without_paths(str(exc))}",
            reason="build_failed",
        ) from None


def curve_id(currency, curve: ZeroCurve) -> str:
    """Short audit label for the curve a result was produced on.

    Inputs
    ------
    1. currency : str — the ISO code the curve was requested for.
    2. curve    : ZeroCurve — the resolved curve.

    Returns: str — ``"USD|2009-03-31|Semiannual"``; the date reads ``"flat"`` for a
    synthetic :func:`flat_zero_curve` (which carries no valuation date).
    """
    date_label = _date_label(getattr(curve, "valuation_date", None)) or "flat"
    return f"{str(currency).strip().upper()}|{date_label}|{curve.freq}"


def _date_label(value) -> str:
    """ISO ``YYYY-MM-DD`` label for any date-like value (empty string when None)."""
    if value is None:
        return ""
    try:
        return pd.Timestamp(value).date().isoformat()
    except (ValueError, TypeError):
        return str(value)


def _without_paths(message: str) -> str:
    """Drop any token that looks like a file path — messages leave the process."""
    return " ".join(w for w in message.split() if "/" not in w and "\\" not in w)
