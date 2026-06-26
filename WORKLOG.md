# Work Log

Reverse-chronological. Each entry is **anchored to the commit** that delivered the
work. Hours are recorded per entry; `[TO FILL]` = not yet logged.

---

## 2026-06-26 — Onboarding: structural analysis + bootstrap validation
**Commit:** `[TO FILL — this commit]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- Mapped all four source workbooks: sheet inventory, column layouts, instrument
  fields, and the pricing/credit logic embedded in cell formulas and VBA.
- Documented the end-to-end pipeline & methodology (bootstrap → rating OAS →
  discount pricing → CreditMetrics overlay) in `PROJECT_STATUS.md`, including the
  exact bootstrap formulas and the FRED ICE BofA OAS source.
- Confirmed the bootstrap formula against the auditable VBA and **reproduced it in
  Python**: Annual / Semiannual / Quarterly **exact (0 error)**; **Monthly within
  0.08 bp** (short-end fill convention).
- Identified the **valuation-date mismatch**: holdings priced 2009-03-31, but the
  bundled bootstrapped CSVs match curve date 2024-01-16 (RMSE 0); 2009-03-31 is
  missing from the curve files (gap 2008-11-10 → 2009-06-10). Impact: 123 priceable
  bonds at 2024-01-16 vs 667 at 2009-03-31.
- Reconciled the corporate-bond universe into three counts (811 / 676 / 641).
- Confirmed **Bloomberg dependency is cut** (txt par curves + FRED OAS).
- Established the repo, `.gitignore` (excludes all client data), and project docs
  (`PROJECT_STATUS.md`, `WORKLOG.md`, `CLAUDE.md`).

**Open / next**
- Decide canonical valuation date + universe; bootstrap a ~2009 curve for the real book.
- Build `io` loaders + `instruments.Bond`; map rating + holdings from the master sheet.
- Port `BondPrice` (from `Pricing File.xlsm → Bootstrapping.bas`) into `pricing`.
- Locate & port the EIR (amortised-cost) method; then start the CreditMetrics layer.

---

<!-- Template for new entries:

## YYYY-MM-DD — <short title>
**Commit:** `<hash>`
**Hours:** `[TO FILL]`
**Author:** <name>

**Done**
- …

**Open / next**
- …
-->
