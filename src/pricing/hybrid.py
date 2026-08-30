"""COMPATIBILITY SHIM — the fixed-then-float hybrid engine now lives in the template
layout: ``pricer/core/pricing/hybrid.py``. The implementation moved verbatim (Round 2b,
2026-08-30) — only its two import lines were repointed at the pricer-native modules, which
are exact aliases of the same objects — so every existing number is unchanged; this module
keeps the original import path working for the drivers and tests that already use it.

Everything documented here before the move — the fixed leg on ``price_bond`` conventions
anchored at the SWITCH, the floating leg on ``price_frn`` conventions anchored at MATURITY
and truncated at the switch, one curve + one implied OAS discounting both legs, the
degenerate limits that DELEGATE (so they agree bit-for-bit), the margin-0 telescoping
identity that validates the composition, and the curve-bump duration convention — moved
WITH the code into that module's docstring.

Existing imports keep working unchanged; new code should use ``pricer.*`` directly — the
per-metric wrappers with legacy naming live in ``pricer.assets.corporate.hybrid``.
"""
from __future__ import annotations

from pricer.core.pricing.hybrid import (             # noqa: F401
    HybridResult,
    hybrid_risk_metrics,
    implied_oas_hybrid,
    price_hybrid,
)

__all__ = ["HybridResult", "price_hybrid", "implied_oas_hybrid", "hybrid_risk_metrics"]
