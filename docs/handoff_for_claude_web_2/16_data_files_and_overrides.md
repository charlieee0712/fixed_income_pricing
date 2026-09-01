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
| `call_schedules.csv` | `asset_id, call_date, call_price` + **since 08-31** `exercise_terms_status, exercise_terms_source, exercise_price_source, exercise_terms_as_of, source`. One row per call date; multiple rows = a step schedule | `dataio.call_schedules` (`load_call_schedules` + `load_call_provenance`); the lattice's **only** source of exercise terms |
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

---

## Update 2026-08-30

**One entry left the missing-data registry without anyone sending us anything.** The GBP
curve request — open against **both** Bloomberg channels — was our own units bug, not a gap.
See `05` §1.9. The registry now carries the rule that follows:

> An entry whose only evidence is one of our own error messages is not yet a data gap.
> Reproduce the claim against the raw file, or against the market the file is supposed to
> describe, before writing it down and before asking anyone for it.

Two kinds of claim, worth separating whenever a plan cites a blocker:

| claim | status |
|---|---|
| "Bloomberg has not sent the pool factors" | a real gap — the absence is observable |
| "our engine reports the curve is not arbitrage-free" | a **symptom** — schedule a check against the raw source |

**Nothing new was asked of anyone this round.** The override tables are unchanged:
`coupon_schedules.csv` (9 documented paths, incl. the FT-GBP 7.50% floor that was seeded
against exactly this day), `frn_spreads.csv` (4 quoted margins), `make_whole_overrides.csv`,
`hybrid_switch_terms.csv` (18 rows), `call_schedules.csv`. A margin fill is still **one cell**
and prices the bond with zero code change — that architecture is what made the GBP fix a
data-layer non-event too: the coupon path was already seeded, so the bond priced the moment
the curve built.

**A new file-level fact belongs here as data, not code:** `curves.bootstrap.PAR_YIELD_UNITS`
declares that `GBP_Yield_Curve.txt` and `DKK_Yield_Curve.txt` store par yields in percent
while the other 24 exports store decimals. Treat it as part of the data layer: adding a new
currency file means checking it against the market on a verifiable date and adding a line.

---

## Update 2026-08-31 — exercise terms now carry their own provenance

`data/call_schedules.csv` gained four columns, and every one of its **nine rows** reads
`provisional / custodian_AB_seed / par_call_convention`. **Not one exercise term in this
project has been confirmed against Bloomberg.**

That was already true and already written down in `docs/missing_data.md`. What changed is that
it is now visible **at the number**: a call price of `100.0` in an output column looks
identical whether it came from a prospectus or from a convention someone applied to a
custodian date, and every one of ours is the second.

`dataio.call_schedules.load_call_provenance` reads them. Two rules that matter for any plan
touching this file:

- **A missing column defaults to `provisional`, never `confirmed`.** An absent statement of
  provenance is not evidence of good provenance.
- **An unrecognised status is REFUSED**, not coerced. `verified`, `final`, `TRUE` and a typo
  must not be read as confirmation.

Both drivers write `exercise_terms_status | _source | exercise_price_source | _as_of` on all
eight lattice-priced bonds, and the endpoint raises `PROVISIONAL_TERMS` when a tree request
does not declare confirmed terms. Labels never change a number — asserted with `==`.

`TNTD04115619` additionally carries a named `review_note` in `callable_risk.csv` (≈1994 bp on a
3.9y BBB marked 60.65). It is a **recorded observation, not a threshold**: nothing is filtered
on it, and the arithmetic is sound — the note says that a spread that wide is the market
pricing default risk rather than a term premium, and that the call is not binding at that
price, so the figure does not depend on the seeded schedule.

**The three corporate schedules joined the existing confirmation-only deferred queue. No new
request was opened**, by instruction. Every one of those bonds prices today.
