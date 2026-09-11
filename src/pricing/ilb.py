"""COMPATIBILITY SHIM — the inflation-linked engine now lives in the template layout:
``pricer/core/pricing/inflation.py``. The implementation moved verbatim (2026-09-10), so every
existing number is unchanged; this module keeps the original import path working for the driver
and tests that already use it.

Everything documented here before the move — the nominal-curve-plus-index-path method, the
per-bond ``index_ratio`` recovery from the custodian file, above all the ⚠️ rule that the
calibrated spread at ``inflation = 0`` is EXPECTED to be **negative** (roughly minus the market
breakeven, never a credit OAS), and the three v1 simplifications — moved WITH the code into that
module's docstring.

⚠️ Unlike ``pricing/frn.py``, this shim's re-export of ``YEAR_DAYS`` and ``_as_date`` is a
courtesy, not a contract: no module imports an ILB private by name (verified 2026-09-10 across
``src/``, ``scripts/`` and ``tests/``). The contract is the three public functions and
``IlbResult``. The frn shim's private re-exports, by contrast, are load-bearing —
``core/pricing/hybrid.py`` builds its floating leg out of them.

Existing imports keep working unchanged; new code should use ``pricer.*`` directly — the
per-metric wrappers with legacy naming live in ``pricer.assets.government.linker``.
"""
from __future__ import annotations

from pricer.core.pricing.inflation import (          # noqa: F401
    YEAR_DAYS,
    IlbResult,
    _as_date,
    ilb_risk_metrics,
    implied_spread_ilb,
    price_ilb,
)

__all__ = ["IlbResult", "price_ilb", "implied_spread_ilb", "ilb_risk_metrics", "YEAR_DAYS"]
