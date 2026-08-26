# Monthly-sheet vanilla reconciliation — Gates 1–3 report (2026-08-17)

**Executes:** Gates 1–3 of `docs/monthly_reconciliation_plan_2026-08-15.md` (Rev B), started
same-day on the user's explicit authorization (recorded in plan §9; net-new validation
tooling beside production — no migration touched). Gate 0 evidence:
`docs/monthly_gate0_memo_2026-08-17.md`.
**Code:** `src/recon/{monthly_curve,parity}.py` + drivers
`scripts/monthly_extract_golden.py` / `monthly_recon_run.py`; locks
`tests/test_monthly_curves.py` (+13; suite **166 green**).
**Frozen artifacts (47 + local mirror):** `outputs/monthly_golden_rows.csv` (2,642 rows,
faithful extraction) · `outputs/monthly_recon_rows.csv` (576 vanilla-population rows, all
per-row metrics + reason codes).

---

## 1. Verdict in one paragraph

**The engine replication is proven exact, and the golden table splits by cache vintage.**
Wherever the sheet's cached outputs come from a current-code session — the 2012-12-12
batch, plus every sub-annual-maturity 2010 row — our replica reproduces them at the legacy
solver's own noise floor: **|ΔOAS| ≤ 0.9bp (median 0.5bp), reprices within 0.009 per 100,
durations equal to 4+ decimals, 100% of comparable rows inside every provisional
tolerance.** The 2010-03-01 batch (the bulk of the table) is cached output of an **older
code revision run on mixed-vintage market data** — demonstrably so (§4) — and is therefore
reclassified `legacy-stale-session`: not a valid numeric golden, for any engine, ours or
theirs. On exactly those rows the three-way against Bloomberg's own columns decides it:
**our durations are closer to Bloomberg's than the sheet's cached durations for 94% of
rows** (median gap 0.49y vs 4.30y — the stale cache carries a ×1/100 scaling bug our read
of the current VBA proves was later fixed).

## 2. Gate 1 — curve rebuild (CLOSED, exact)

- USD pillars for all three valuation dates = treasury.gov daily par-yield CMT (= H.15 =
  Bloomberg `H15T*` that `zeroyield4` pulled; FRED was GFW-blocked, treasury.gov fetched
  via 47). Tracked in `data/h15_pillars_monthly_recon.csv`.
- `src/recon/monthly_curve.py` replicates `zeroyield4` to the letter: 11 pillars → 41-tenor
  gap-fill (per-year-slope-per-row quirk on sub-annual rows included) → money-market
  deposits ≤1y → per-annual-pillar continuous-zero solve with linear-in-z fill, four
  frequency tables. Pass condition met: every gap-filled par instrument reprices to 100
  at 1e-8 on its own table (locked in tests).
- Lineage findings locked in tests: the tracked `USD_Yield_Curve.txt` rows agree with the
  H.15 pillars within ~4bp at shared tenors **except 20y, which the txt fabricates as
  exactly (10y+30y)/2** on all three dates (the real CMT 20y sat ~33bp above it in 2010).
- The production (auditable-variant) `bootstrap.py` differs from the zeroyield4 replica by
  ≤0.02bp on Semiannual zeros out to 30y on this data — the two legacy bootstrap variants
  are numerically near-identical here; the replica exists for exactness, not necessity.

## 3. Gate 2 — pilot (CLOSED; verdicts)

23 rows (18 corp/agy at-maturity-fixed across 7–337 months + 5 Treasuries).

- **Verdict 1 (parity):** split outcome — Treasuries (2012-12 batch): exact (ΔOAS ≤0.9bp,
  Δdur = 0.0000). Corp rows (2010 batch): systematic maturity-shaped misfit ⇒ triggered
  the §4 investigation, resolved as `legacy-stale-session`.
- **Verdict 2 (convention checksum):** the deliberate BondPrice-style mismatch mode is
  indistinguishable at 2010's near-zero short rates on the stale rows (checksum
  uninformative there); the operative dynamic proof of the consistent convention is the
  2012 exactness itself, which only the consistent mode produces.
- **Verdict 3 (tolerances re-baselined):** current-code-session rows achieve OAS ≤1bp /
  duration ≤0.001y / reprice ≤0.01 — adopted as targets (exceptions: >2bp / >0.05y /
  >0.10) for all current- and future-session reconciliations (tree gates included).

## 4. The 2010-03-01 batch = `legacy-stale-session` (evidence chain)

Four independent proofs, all in the frozen per-row CSV:

1. **Sub-annual rows pin the deposit strip.** Rows touching only deposit nodes (≤15
   months) reprice EXACTLY (ΔOAS 0.00bp, ΔPV 0.0000) on the Libor deposit strip cached in
   the sheet's top block — which is *not* 2010-03-01 Libor (12M cached 1.88% vs ~0.85%
   actual). The run-time deposits survive in the cache; the top-block swap rows were
   refreshed later (mixed-epoch cells).
2. **No single curve explains the pillar-touching rows.** Backing the pillar curve out of
   the V column (reprice-at-P, solver-noise-free; fit/holdout split) leaves irreducible
   residuals (median 0.24–0.27 per 100, 100× the solver floor) around an implausible
   near-flat ~2.4% par shape matching no real Treasury or swap date — the rows were cached
   across multiple sessions with drifting inputs.
3. **The Q column carries an extinct scaling.** Cached corp durations = effective duration
   ÷ 100 (ratio test on 197 rows: median 1.03 vs the ÷100 hypothesis, p10–p90
   0.92–1.18) — the current VBA multiplies by 100 (`CorpBondDuration` l.2736); the cache
   predates that fix. Treasuries cached in 2012 sessions carry correctly-scaled durations.
4. **Dead scenario cells.** Many 2010-batch T/U (steep/flat) cells are 0 = the older code
   returned nothing; 2012-batch rows carry real twists (the SteepFlat file existed in that
   session — it remains the T/U gate's data prerequisite).

## 5. Gate 3 — bulk (CLOSED for the vanilla scope)

576 vanilla-population rows (248 core at-maturity + 161 govt + 167 dead-AB speculative):

| Population | n compared | Result |
|---|---|---|
| govt @ 2012-12-12 (Treasuries + agencies) | 32 | **100% within tolerance**: ΔOAS ≤0.9bp (med 0.51), ΔPV ≤0.0085, Δdur ≤0.0003y; R/S derived-consistent |
| spec (dead-AB corp) @ 2012-12-12 | 67 | **33% ≤2bp = empirically recovered at-maturity routes**; the rest = other engines at run time (FRN fallback / lattice) → their gates |
| core + govt + spec @ 2010-03-01 | 301 | `legacy-stale-session` (§4) — excluded as numeric golden; three-way below is the comparison that survives |
| non-USD (all sets) | 121 | `non-usd-deferred` (per plan: USD first) |
| legacy-dead (P=0) / stale cells / caps | 34 / 9 / 8 | excluded per the pre-registered reasons |

**Three-way (session-independent), on the stale 2010 rows:**

- **H4 (durations vs Bloomberg col I, n=194 core):** ours closer for **94%**; median
  |ours−I| = 0.49y vs |cached−I| = 4.30y. Same picture on spec rows (89%, 0.28y vs 3.18y).
  Treasuries: 69% ours-closer at parity of medians (~0.97y both — 20y+ Bloomberg
  durations differ by convention).
- **H3 (OAS vs Bloomberg col AD, n=97):** NOT decidable, as pre-registered: AD's pull
  date is unknown (plausibly cached in the same stale sessions) and its curve basis
  differs; the cached P sits nominally closer (med 43.6bp vs our 57.9bp). No conclusion
  drawn either way.

**New exception reason codes** (added to the plan's ledger): `legacy-stale-session`,
`legacy-dead`, `legacy-solver-cap`, `route-unknown`, `near-maturity-undefined`,
`beyond-curve`, `anomaly-unexpected-live`.

## 6. What this means for the project

1. **The restructured vanilla chain is validated against the legacy system's own output at
   the only scale the cache permits** — exact where the cache is sound, and demonstrably
   better than the cache (per Bloomberg's own columns) where it is not. This is the
   evidence sentence for Mario's sample review, and it is in the updated sample report.
2. The remaining Monthly populations (callable/NORMAL ~450, FLOATING 426, mtge ~1,300)
   reconcile after their engines roll out — with the warning, now proven, that **only
   2012-12-batch caches are trustworthy goldens**; 2010-batch comparisons must run
   three-way against Bloomberg columns instead.
3. Deferred asks unchanged (lock #13): SteepFlat file when the T/U gate opens; nothing
   new for Mario/Liping from Gates 1–3.
4. v1-report cross-check: the URS-book pipeline is untouched — everything here lives in
   `src/recon/` + scripts + tests.

## 7. Reproduction

```
PYTHONPATH=src python3 scripts/monthly_extract_golden.py         # workbook -> CSV
PYTHONPATH=src FIP_RECON_MODE=pilot python3 scripts/monthly_recon_run.py
PYTHONPATH=src FIP_RECON_MODE=bulk  python3 scripts/monthly_recon_run.py
.venv/bin/python -m pytest -q                                    # 166 green
```
