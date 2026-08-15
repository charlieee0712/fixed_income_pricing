"""COMPATIBILITY SHIM — implied-OAS calibration now lives in the template layout:
the generic monotone-spread solver is ``pricer/core/market/spreads.py`` (Mario's
2026-06-30 redefinition — OAS is a per-bond CALIBRATION factor, not a pricing input —
is documented there), and this module keeps the original corporate-vanilla signature
on top of it. ``near_maturity`` moved to the same module (the flag travels with the
spread statistics it protects).

Existing imports keep working unchanged; new code should use ``pricer.*`` directly
(the per-metric wrapper ``pricer.assets.corporate.vanilla.implied_oas`` returns bp).
"""
from __future__ import annotations

from pricer.core.market.spreads import near_maturity, solve_spread_to_price  # noqa: F401
from pricer.core.pricing.analytical import price_fixed_rate_bond

__all__ = ["implied_oas", "near_maturity"]


def implied_oas(target_clean, valuation_date, maturity, coupon_rate, curve, *,
                face: float = 100.0, freq: int = 2, vba_compat: bool = False,
                coupon_schedule=None,
                lo: float = -0.20, hi: float = 2.0, xtol: float = 1e-10,
                max_expand: int = 40) -> float:
    """Solve for the flat continuous OAS (decimal) s.t. model CLEAN price ==
    ``target_clean`` (per ``face``; the custodian ``BT`` per-100 with ``face=100``).

    Delegates to :func:`pricer.core.market.spreads.solve_spread_to_price` with the
    analytical engine as the price function; bracket/tolerance semantics unchanged.
    Returns the OAS in decimal (e.g. 0.0453 = 453 bp).
    """
    def clean_at(oas: float) -> float:
        return price_fixed_rate_bond(valuation_date, maturity, coupon_rate, curve,
                                     oas=oas, face=face, vba_compat=vba_compat,
                                     freq=freq, coupon_schedule=coupon_schedule).clean

    return solve_spread_to_price(clean_at, target_clean, lo=lo, hi=hi, xtol=xtol,
                                 max_expand=max_expand)
