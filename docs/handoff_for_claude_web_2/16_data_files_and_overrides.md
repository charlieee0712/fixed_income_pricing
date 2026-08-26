# Data files and the override layer

The architecture principle that governs this whole area, and it is Mario's (2026-07-30):
what matters is that **the process runs end to end** and that **every unavailable field is
specified on a table**, so that when complete data arrives "we'll run all what you've
built". Every gap therefore has a landing file, and a data arrival is a CSV edit — never a
code change.

---

## 1. Source workbooks (`data/`, tracked in-repo)

| File | Role |
|---|---|
| `URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx` | **the portfolio to price.** US pension, USD ISINs, positions split by asset type; the `Corporate Bonds` tab is the terms source |
| `Project Pricing Fixed Income Instruments.xlsm` | the legacy risk system. Huge `Module1`; source of `BondOAS` (the option lattice) and the **Monthly** sheet |
| `Pricing File.xlsm` | the auditable reference VBA: `Bootstrapping.bas` (1,706 lines: `BondPrice`, `ZeroCalc`, `Parcurve`), `Matrix.bas`, `Copulas.bas`; also holds the archived OAS history, and a **separate Uganda demo** that must never be merged with URS |
| `*_Yield_Curve.txt` | par-yield history per currency |
| `h15_pillars_monthly_recon.csv` | H.15/CMT pillars for the three Monthly valuation dates |

Client data has been **tracked in-repo since 2026-07-08** (boss-approved), which is why the
repo must stay private. `data/` is the canonical location; `.gitattributes` marks
`data/** -text` so the files are byte-frozen.

## 2. The override CSVs — the Bloomberg landing zone

| File | Holds | Consumed by |
|---|---|---|
| `call_schedules.csv` | `asset_id, call_date, call_price` — one row per call date, multiple rows = a step schedule | `dataio.call_schedules`; the lattice's **only** source of exercise terms |
| `coupon_schedules.csv` | documented coupon paths; an entry routes ANY class to `vanilla-schedule` | `dataio.term_overrides` |
| `frn_spreads.csv` | quoted margins (+ a `freq` column, so quarterly resets use the quarterly curve variant) | `dataio.term_overrides` |
| `make_whole_overrides.csv` | documented make-whole-only bonds the 7-day heuristic misses | `dataio.term_overrides` |
| `hybrid_switch_terms.csv` | 18 rows: fixed rate, switch date, post-switch margin | `pricing.hybrid` |

All are optional: a missing file simply means no overrides. That is what makes them a
landing zone rather than a dependency.

## 3. Provenance and the provisional rule

The override values came from an ISIN/CUSIP research pass on 2026-07-20 (SEC EDGAR
full-text search on CUSIP, issuer offering circulars, 20-Fs, annual reports, and the
oblible / gruppotim / unicredit archives). Of 35 flagged bonds: **22 FULL (high confidence) /
10 PARTIAL / 3 NONE** (exempt US paper with no public filing). Per-bond evidence with
citations is in `docs/isin_lookup_2026-07-20.md`.

**These values are PROVISIONAL.** On any Bloomberg return: diff, **Bloomberg wins**, log the
deltas. That is Mario's rule and it is why the registry tracks request status per field.

Worked examples of what that pass found:

- **Comcast** — the workbook's "zero coupon" was a custodian **error**. Taking it at face
  value gave an implied OAS of −486 bp; the documented 6.95% coupon gives +431 bp.
- **TI-2012 and TI-2033** — tagged "(VAR)" / "Fixed→Reset" in the workbook, documented as
  **plain fixed**. Sanity check: TI-2012 at 381 bp sits next to Sogerim at 398 bp, same
  guarantor.
- **RBS 6.00%** — a call/float hypothesis was actively **refuted** by the documentation.
- **Shinsei** — the "FRN with no maturity" pair resolved to a dated 2016-02-23 bond at 3.75%
  to a 2011 call.

## 4. The missing-data registry

`docs/missing_data.md` is the living table: every gap → its landing CSV/loader → the interim
treatment → the request status. It exists because Mario asked for exactly that artifact.

Current headline gaps: MBS 8-mnemonic × 882 CUSIPs; pass-through schedules for 13 unique
securities; the 11-security list (3 exempt US FRNs, 8 hybrid margins); one callable's
schedule; a usable GBP curve; KTBi indexation terms.

## 5. Outputs

`outputs/` is git-ignored and regenerable:

```text
implied_oas.csv                the corporate book, per bond: route, OAS, risk, flags
callable_risk.csv              the lattice bonds, with straight-vs-callable comparisons
phase2_risk.csv                agencies / guaranteed / index-linked
monthly_golden_rows.csv        2,642 extracted Monthly rows (frozen 2026-08-17)
monthly_recon_rows.csv         576 reconciliation rows
govt_mtge_cusips.csv           the 882 CUSIPs sent with the MBS request
```

The three driver CSVs are also the **migration proof**: they are hashed before a change and
after it, and byte-identity is the acceptance criterion.

## 6. Two data facts that keep coming up

- the master's coupon columns are **empty**; terms come from the `Corporate Bonds` tab, and
  the join is on Asset ID (100%), ISIN secondary;
- the custodian's base-USD columns (`BU` market value, `Z` book cost) are used **directly**.
  There is no self-conversion anywhere; `currency` only ever routes a curve.
