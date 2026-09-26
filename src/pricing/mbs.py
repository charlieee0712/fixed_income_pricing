"""COMPATIBILITY SHIM — the pool engine now lives in the template layout:
``pricer/core/pricing/prepayment.py``. The implementation moved verbatim (2026-09-25), body
spliced below the docstring at sha256 ``45a0ef7d5d98d893``, so every number it produces is
unchanged; this module keeps the original import path working for the tests that already use it.

It was the last engine outside the template — every other module in this package has been a
shim since the Round-2b and government rounds. Migrating it now was the cheap moment precisely
because nothing depends on it: there is no driver and no hashed output for a Govt-MBS run yet,
so unlike every earlier migration there were no production CSVs to hold byte-identical. That
stops being true the moment the first pool driver is written.

Everything documented here before the move — the static-CPR level-pay model, the SMM
conversion, the month-grid discounting, and the note that one price cannot identify CPR and OAS
together — moved WITH the code into that module's docstring, where the CPR-versus-spread choice
is now recorded as settled rather than open (the delivered Bloomberg pull is as-of 2026, so the
price implies the CPR rather than the CPR implying the spread; see ``scripts/mbs_data_check.py``).

⚠️ Like ``pricing/ilb.py`` and unlike ``pricing/frn.py``, this shim has no private re-exports to
honour: nothing outside the module imports ``_solve_decreasing`` or any other private name
(verified 2026-09-25 across ``src/``, ``scripts/`` and ``tests/``). The contract is the public
surface below, and ``tests/test_pricer_securitized_structure.py`` asserts each name here IS the
same object as in the core module — importability alone would let a shim quietly re-implement
the engine and still pass every import-by-name check.

Existing imports keep working unchanged; new code should use ``pricer.*`` directly — the
per-metric wrappers with legacy naming live in ``pricer.assets.securitized.pool``.
"""
from __future__ import annotations

from pricer.core.pricing.prepayment import (          # noqa: F401
    BLOOMBERG_FIELDS,
    MONTHS_PER_YEAR,
    PoolFlow,
    PoolTerms,
    implied_cpr_pool,
    implied_spread_pool,
    pool_cash_flows,
    pool_risk_metrics,
    price_pool,
    select_cpr,
    smm_from_cpr,
)

__all__ = [
    "PoolTerms", "PoolFlow", "BLOOMBERG_FIELDS", "MONTHS_PER_YEAR",
    "select_cpr", "smm_from_cpr", "pool_cash_flows", "price_pool",
    "implied_spread_pool", "implied_cpr_pool", "pool_risk_metrics",
]
