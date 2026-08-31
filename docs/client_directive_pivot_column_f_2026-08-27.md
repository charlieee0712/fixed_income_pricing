# Client directive — Mario's column F on `Pivot of Corp Bonds` (2026-08-27)

Internal evidence record. This is the provenance of Round 2b's entire scope, written down
because the ask did not arrive as a message: **it arrived as annotations on a spreadsheet.**

---

## 1. What was annotated, and where

At the meeting of approximately 2026-08-27 Mario worked down the coupon-type pivot on the
holdings workbook and added a **new column F** to the sheet `Pivot of Corp Bonds`.

**Source: the tracked workbook itself**, not a screenshot —
`data/URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx`, sheet `Pivot of Corp Bonds`
(`xl/worksheets/sheet6.xml`). The column did not exist in the committed file before that
date; it arrived with the 2026-08-27 working-tree change and was committed **as Mario left
it** in `a5f7c81`, precisely so this record would exist. `git show a5f7c81~1:<workbook>`
recovers the pre-annotation version and shows column F absent.

> The planning-side Project copy of the workbook predates the meeting, so a Claude working
> from that copy cannot see column F and was supplied a screenshot instead. Both point at
> the same annotations; the tracked workbook is the stronger evidence and is what this
> record cites.

## 2. Exact transcription

Only cells that carry a value. **Blank cells are not interpreted as instructions.**

| Cell | Row label (`Coupon_Formula2`) | Pivot count | Visible text |
|---|---|---|---|
| `F5` | `F` (plain fixed) | 617 | `finished` |
| `F12` | `Fixed → Floating` | 5 | `no` |
| `F13` | `7.00% for  t<01-Mar-2006 7.50% for t≥01-Mar-2006` | 2 | `no` |
| `F14` | `GBP LIBOR + Spread` | 1 | `no` |
| `F15` | `Reference Rate + Spread` | 12 | `no` |
| `F16` | `EURIBOR + Spread` | 9 | `no` |
| `F20` | `Step-up schedule` | 1 | `no` |
| `F21` | `Zero coupon / structured payoff` | 1 | `just corp bond(fixed)` |

Left blank, and therefore **not** part of the ask: rows 6–11 (`Fixed → Reset` variants),
17 (`Amortizing`), 18 (`N/A`), 19 (`Pass-through cash flow`), 22 (`N/A (Defaulted)`).

## 3. How the annotations are read

**`finished` means "present in the restructured `pricer/` package", not "historically
priced".** This is the interpretation the whole round rests on, so the reasoning is recorded
rather than assumed:

- every coupon family marked `no` had been pricing in the legacy `src/pricing/` layer since
  July, so `finished` cannot mean "priced" — it would be true of all of them;
- `F5` is the plain-fixed row, and the plain-fixed vanilla chain is exactly what the
  2026-08-15 code-structure sample migrated and Mario approved on 2026-08-25.

The execution side checked whether the two readings diverge in what they imply before
proceeding. They do not: migrating the engines, producing the numbers and returning a
cell-by-cell status table satisfies both. No clarification was requested, and none was
needed.

**`just corp bond(fixed)` on `F21`** agrees with the existing treatment: the custodian's
0% coupon on that security was a data error for a 6.95% fixed bond, and it is already
routed as an ordinary fixed corporate. No structured-payoff engine was built or implied.

**Rows 6–11 are adjacent coverage, not six additional requests.** They share the
fixed-then-floating engine with `F12`, so they were covered as a by-product. They are
reported separately everywhere and are never folded into the six-cell counts.

## 4. What was NOT done to the workbook

The authoritative holdings file was **never written to** in order to record, insert or tidy
these annotations. What is committed is what Mario left. Our own status is reported in
`docs/column_f_delivery_matrix_2026-08-31.md`, which is the evidence Mario or the user can
use to update column F themselves — updating it is theirs to do.

## 5. Communication state

Confirmed:

- Mario discussed the 2026-08-25 report at the meeting;
- he agreed with the next-week plan (floating, then endpoint dispatch);
- the column-F annotations became the operational request.

**Not confirmed, and therefore not recorded as done:** that the 2026-08-30 package has been
sent or uploaded. It is prepared and staged; delivery is the user's action and this record
will not claim it until the user says so.
