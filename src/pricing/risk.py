"""COMPATIBILITY SHIM — the risk formulas now live in the template layout:
``pricer/core/risk/sensitivities.py`` (engine-agnostic DV01 / effective duration /
convexity + the bump-and-reprice driver; the DIRTY-price-base convention is
documented there). This module keeps the original corporate-vanilla signature on top.

Existing imports keep working unchanged; new code should use ``pricer.*`` directly
(per-metric wrappers with legacy naming: ``pricer.assets.corporate.vanilla``).
"""
from __future__ import annotations

from pricer.core.pricing.analytical import price_fixed_rate_bond
from pricer.core.risk.sensitivities import ONE_BP, parallel_bump_metrics  # noqa: F401

__all__ = ["risk_metrics", "ONE_BP"]


def risk_metrics(valuation_date, maturity, coupon_rate, curve, oas, *,
                 face: float = 100.0, freq: int = 2, vba_compat: bool = False,
                 coupon_schedule=None, bump: float = ONE_BP) -> dict:
    """Return ``{dirty, clean, dv01, eff_duration, convexity}`` for the calibrated
    bond (``oas`` = the implied OAS, so dirty/clean reproduce the mark). Bumping the
    OAS is identical to a parallel curve shift — effective sensitivities.
    """
    def priced(shift: float):
        return price_fixed_rate_bond(valuation_date, maturity, coupon_rate, curve,
                                     oas=oas + shift, face=face,
                                     vba_compat=vba_compat, freq=freq,
                                     coupon_schedule=coupon_schedule)

    return parallel_bump_metrics(priced, bump=bump)
