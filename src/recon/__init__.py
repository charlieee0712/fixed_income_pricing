"""Monthly-sheet golden reconciliation tooling (legacy-parity mode).

Replicates the legacy workbook's own curve build (`zeroyield4`) and vanilla
pricing chain (`BondCalc` -> `CorpBond*`) so the ~2,600-row Monthly golden
table can be reconciled bond-by-bond.  Plan: docs/monthly_reconciliation_plan_
2026-08-15.md (Rev B); evidence: docs/monthly_gate0_memo_2026-08-17.md.

This package lives BESIDE production pricing (src/pricing, src/pricer) and is
never imported by it: the month-grid / no-accrued conventions replicated here
are reconciliation instruments, not production methodology.
"""
