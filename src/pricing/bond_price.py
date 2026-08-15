"""COMPATIBILITY SHIM — the ``BondPrice`` port now lives in the template layout
(Mario's code-structure directive, 2026-08-15):

    price_bond (= price_fixed_rate_bond)  -> pricer/core/pricing/analytical.py
    bond cash flows + accrued_interest    -> pricer/core/pricing/cashflows.py
    discount factors + vba-compat rates   -> pricer/core/pricing/discounting.py
    coupon_dates + ACT/364 calendar       -> pricer/core/utils/dates.py

Everything documented here before the move — the VBA conventions (ACT/364, 182-day
backward schedule, accrued formula), the CORRECTED discounting vs the legacy
``exp(-t * z_semi)`` bug (VERIFIED 2026-06-29), and the ONE-accrued-formula law
(Liping review 2026-08-04) — moved WITH the code into those module docstrings.

This module re-exports the original public surface so every existing import keeps
working unchanged. New code should import from ``pricer.*`` directly.
"""
from __future__ import annotations

from pricer.core.pricing.analytical import (          # noqa: F401
    CashFlow,
    PriceResult,
    price_fixed_rate_bond as price_bond,
)
from pricer.core.pricing.cashflows import (           # noqa: F401
    accrued_interest,
    lattice_inputs,
)
from pricer.core.pricing.discounting import (         # noqa: F401
    _VBA_MAX_TENOR,
    semiannual_from_continuous as _cont_to_semi,
    vba_semiannual_rate as _vba_semi_rate,
)
from pricer.core.utils.dates import (                 # noqa: F401
    HALF_DAYS,
    YEAR_DAYS,
    as_date as _as_date,
    coupon_dates,
)

__all__ = ["CashFlow", "PriceResult", "price_bond", "accrued_interest",
           "lattice_inputs", "coupon_dates", "YEAR_DAYS", "HALF_DAYS"]
