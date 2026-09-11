"""Government and government-related bonds — the thin wrapper layer.

Companion to ``assets/corporate/``. Three classes of Mario's book live here:

  agency       Government Agencies            42 master rows -> 39 securities
  guaranteed   Guaranteed Fixed Income        11 master rows ->  9 securities
  linker       Index Linked Government Bonds  16 master rows -> 15 securities

They share one loader (``dataio.phase2``), one driver (``scripts/phase2_risk.py``) and one
63-row output file, which is why they were migrated together: restructuring two of the three
would have left the third an un-migrated island inside migrated code.

⚠️ **Nothing in this package routes a security to an engine.** Routing has a single owner —
``dataio.phase2._route_agency`` and its named constants — and duplicating those rules here
would recreate the "two files owning half a decision" defect closed five times in this project.
These modules are the per-metric surface: one simple function per output, legacy units
(prices per 100, spreads in basis points, coupons in percent), no arithmetic of their own.
"""
