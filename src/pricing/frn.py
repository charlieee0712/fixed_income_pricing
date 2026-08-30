"""COMPATIBILITY SHIM — the FRN engine now lives in the template layout:
``pricer/core/pricing/floating.py``. The implementation moved verbatim (Round 2b,
2026-08-30), so every existing number is unchanged; this module keeps the original
import path working for the drivers and tests that already use it.

Everything documented here before the move — the simple-forward projection off our
bootstrapped ``ZeroCurve``, the single-curve 2009 discounting convention, the
"spread unknown -> 0, the OAS absorbs it" convention, and above all the ⚠️ rule that
effective duration bumps the CURVE (reprojecting the forwards) and NOT the OAS,
together with the near-par / deep-discount duration regimes — moved WITH the code
into that module's docstring.

⚠️ This shim deliberately re-exports the PRIVATE helpers ``_as_date``, ``_rate``,
``_df`` and ``simple_forward`` as well as the public surface: ``pricing/hybrid.py``
imported them by name to build its floating leg on exactly the FRN conventions, so
dropping them here would break the hybrid engine at import time.

Existing imports keep working unchanged; new code should use ``pricer.*`` directly —
the per-metric wrappers with legacy naming live in ``pricer.assets.corporate.floating``.
"""
from __future__ import annotations

from pricer.core.pricing.floating import (           # noqa: F401
    YEAR_DAYS,
    FrnResult,
    _SPREAD_BP,
    _SPREAD_PCT,
    _as_date,
    _df,
    _rate,
    frn_risk_metrics,
    implied_oas_frn,
    parse_frn_spread,
    price_frn,
    simple_forward,
)

__all__ = ["FrnResult", "price_frn", "implied_oas_frn", "frn_risk_metrics",
           "parse_frn_spread", "simple_forward", "YEAR_DAYS"]
