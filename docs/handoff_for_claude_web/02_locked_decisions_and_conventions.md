# Locked decisions & conventions — do not re-litigate

Settled by directive, test, or evidence. Reopen only if the user explicitly asks.

## A · Methodology locks

1. **Valuation & calibration date = 2009-03-31** (matches holdings; Mario's USD curve fills
   the old curve-file gap). The custodian's tighter-than-index marks are the genuine
   recovering-market level (Mario 2026-07-03) — the "70-day gap / BT marking date" question
   is CLOSED. 2009-06-10 is kept as a control run only.
2. **OAS is a per-bond calibration OUTPUT, not a pricing input** (Mario 2026-06-30): solve
   the flat spread that makes the model reprice the custodian clean price, then compute
   risk metrics on the calibrated model. Index/sector OAS sourcing is dead (and FRED's free
   OAS history was truncated to a rolling 3y in Apr-2026 — the workbook archive
   `OAS Credit Curves`, 1997–2025 daily, is the only history source).
3. **Price-convention law** (Liping review, enforced by 16 invariance tests): model PV =
   dirty; custodian `BT` = clean; ONE shared accrued-interest formula (ACT/364,
   schedule-aware) ⇒ solving clean(OAS)==BT and dirty(OAS)==BT+AI give the SAME root.
   **Duration/convexity denominator = DIRTY**, retained after testing both ways against
   custodian durations (n=61: dirty closer 41/61).
4. **Legacy discounting bug is understood and contained:** the legacy tool discounts a
   semiannual zero with the continuous formula ⇒ systematic under-pricing (~0.2% @ 8y). Our
   default is corrected (par reprices to 100.000000); `vba_compat=True` reproduces the
   legacy output bit-for-bit for reconciliation only. Two legacy bootstraps exist
   (continuous z for the audit routine vs semiannual z inside BondPrice) — never conflate.
5. **Cash-flow calendar = the legacy ACT/364 + 182-day backward grid** — a validated
   convention, not a bug; real day-count labels (30/360, ACT/ACT…) are carried as data
   only. The legacy input dictionary itself marks Daycount "not used".
6. **Make-whole callables price as vanilla** (47 bonds, flagged; call ≈ economically
   worthless); only the 5 genuine-gap callables use the lattice. **σ = 0.15** (Mario).
   Call schedules are DATA (`data/call_schedules.csv`) — never hard-coded par-call.
7. **Single-curve FRN/hybrid discounting = the 2009 convention**; OIS dual-curve is a
   documented future enhancement, not now. FRN effective duration bumps the CURVE
   (reprojects forwards), giving the signature short/negative durations — correct, tested.
8. **ILB spread ≈ −breakeven at zero assumed inflation** — kept in its OWN column
   (`implied_spread_vs_nominal_bp`), never mixed with credit OAS (unit-tested identity).
9. **Universe = deterministic 2-layer MECE funnel** with LOCKED drop priority
   (terms-unavailable → defaulted → no-rating → structured/floating → callable → matured);
   the golden counts reproduce exactly (join 597/135/19, canonical 522 @ 6-10 no-override).
   Coupon routing reads `Coupon_Formula2` and reconciles EXACTLY to Mario's 676-row pivot.
   Rating red lines: BBB−→BBB, BB+→BB (IG/HY split); CC/C/Ca → CCC, never default (only D/SD).
10. **Medians composition:** only PRICED routes feed by-rating medians; near-maturity
    (<1y), hybrids/junior-sub, distressed, zero-structured stay OUT.

## B · Data & process locks

11. **No Bloomberg on our side.** All external data arrives via Mario/Liping pulls into
    tracked CSV landing zones (`term_overrides`, `call_schedules`, `hybrid_switch_terms`,
    `coupon_schedules`, `frn_spreads`, `make_whole_overrides`). **Web/ISIN-researched
    values are PROVISIONAL: on any Bloomberg return — diff, Bloomberg wins, deltas logged**
    (`06_missing_data_registry.md` is the living registry). A data fill = one CSV row,
    zero code change — that architecture is the point (Mario 2026-07-30).
12. **Data-gap bonds are flagged + custodian-marked, never half-modelled / force-priced.**
    Amortizing (1) + n/a (4) are permanently out (Mario). Pass-through work starts only
    when its Bloomberg data arrives.
13. **Deferred-asks discipline:** the deferred trio (KTBi, agency call-schedule
    confirmation, rating quirk) waits for Mario's MBS-data return — do not draft re-asks.
    Dedupe Mario/Liping returns before loading.
14. **Repo stays PRIVATE; client data is tracked in-repo** (boss-approved 2026-07-08).
    Custodian golden columns (BT/BU/DI/AQ) live in reconciliation tables, never in pricing
    inputs.

## C · Code-structure workstream locks (Mario 2026-08-15)

15. **Sample-first** (user's call): nothing beyond the vanilla chain migrates until Mario
    approves the sample.
16. **Migration ground rules:** module-by-module; old import paths stay as shims until
    retired; the FULL test suite must be green at every step with float-operation order
    preserved (bit-identical numbers); every function documents its inputs as a numbered
    block; asset-layer units follow the legacy sheet (coupon in percent, prices per 100,
    spreads in bp) while core stays in decimals; new code imports `pricer.*`, never the
    shims.
17. **The Monthly sheet is the reference:** per-metric simple functions + input
    dictionaries (adopted), and its ~2,600-bond results table is the reconciliation golden
    (planned milestone — treat its numbers as the target, mindful that the legacy engine
    carries the known discounting bug, so reconciliation may need `vba_compat`).
