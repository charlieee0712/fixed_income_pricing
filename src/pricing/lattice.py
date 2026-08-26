"""COMPATIBILITY SHIM — the callable/putable short-rate lattice now lives in the template
layout: ``pricer/core/pricing/tree.py``. The implementation moved verbatim (Round 2 Gate 1,
2026-08-25), so every existing number is unchanged; this module keeps the original import
path working for the drivers and tests that already use it.

Existing imports keep working unchanged; new code should use ``pricer.*`` directly — the
per-metric wrappers with legacy naming live in ``pricer.assets.corporate.callable`` /
``.puttable`` / ``.sinking``.
"""
from __future__ import annotations

from pricer.core.pricing.tree import ShortRateLattice, _root_decreasing  # noqa: F401

__all__ = ["ShortRateLattice"]
