"""COMPATIBILITY SHIM — the coupon time-table parser now lives in the template layout:
``pricer/core/pricing/coupon_schedule.py``. The implementation moved verbatim
(Round 2b, 2026-08-30), so every existing number is unchanged; this module keeps the
original import path working for the drivers, overrides loader and tests that use it.

Everything documented here before the move — the "return None, never a guess" rule for a
cell with no numeric coupons, the ``[(effective_from | None, rate_decimal), ...]`` shape and
the DECIMAL rate convention — moved WITH the code into that module's docstring.

Existing imports keep working unchanged; new code should use ``pricer.*`` directly — the
per-metric wrappers with legacy naming live in ``pricer.assets.corporate.stepped``.
"""
from __future__ import annotations

from pricer.core.pricing.coupon_schedule import (   # noqa: F401
    _DATE,
    _MONTHS,
    _PCT,
    _parse_date,
    _parse_one,
    coupon_at,
    parse_coupon_schedule,
)

__all__ = ["parse_coupon_schedule", "coupon_at"]
