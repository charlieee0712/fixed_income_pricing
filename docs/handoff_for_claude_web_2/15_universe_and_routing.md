# Universe and routing — how a holding becomes a priced bond

Three populations exist and are easy to confuse. Getting them straight is the single most
common source of wrong counts in a plan.

---

## 1. The three populations

| Population | Size | What it is |
|---|---|---|
| **Monthly workbook rows** | 2,642 | the legacy run-sheet's saved outputs, ~2,600 bonds across several valuation dates. **Not** the client portfolio. |
| **URS corporate universe** | 732 unique → **523 / 528 canonical** | the actual holdings after the exclusion funnel (6-10 / 3-31) |
| **Priced output** | **566** = 555 priced + 11 flagged | what the corporate driver emits at 3-31. 564 = 553 + 11 before the 08-30 GBP units fix; 565 = 555 + 10 after it; 566 = 555 + **11** after the 08-31 defaulted-disposition rule recovered `TNTD03067251` as a third `recovery` row |

A number quoted without its population is a number that will be wrong somewhere. "FLOATING
426" is the cautionary example: it is a URS production count that a plan attributed to the
Monthly sheet, where the actual label count is 29.

## 2. The corporate funnel (`dataio/universe.py`)

Deterministic and two-layered, and every drop is logged with **one primary reason** plus the
Asset ID.

```text
start        master sub-category == "Corporate Bonds", deduped by Asset ID  -> 732 unique
             (from 811 rows; there is no separate MTN sub-category — "MTN" is a terms-gap
              label, not a security type)

join         597 matched · 135 master-only · 19 tab-only
rating       712 covered · 4 defaulted · 16 no-rating
layer A      date-independent: 54 non-vanilla · 73 callable (raw, pre-reclassification)
layer B      matured at the valuation date

priority     terms-unavailable/unmatched > defaulted > no-rating > structured/floating
(LOCKED)     > callable > matured
```

Result at 2009-06-10, MECE after priority: **canonical 522** (523 with the production
make-whole override) / terms-unavailable 135 / structured-floating 51 / callable 5–6 /
no-rating 9 / matured 6 / defaulted 4. At 2009-03-31: **canonical 528** — five more bonds
are still alive.

Every one of those counts reproduces exactly in the test suite. If a plan quotes a different
number, the plan is wrong or the universe changed and the tests would have caught it.

## 3. Coupon-type routing (`dataio/coupon_types.py`)

Mario's 2026-07-08 directive: stop defaulting everything to fixed, read **`Coupon_Formula2`**
(Excel column **M** — he said N; the header confirms M and N is empty) and route by
structure. The classifier reconciles **exactly** to his own 676-row pivot:

```text
F 617 · floating 27 · fixed-to-reset 6 · stepped 2 · step-up 1 · zero 1 · defaulted 1
· excluded 21  (pass-through 16 + amortizing 1 + na 4)
```

Route map:

```text
F, zero                    -> vanilla
stepped, step-up           -> vanilla-schedule
floating, fixed-to-reset   -> the floating / hybrid engines
defaulted                  -> recovery mark
pass-through               -> waiting on data (Mario sourcing)
amortizing, na             -> ignored permanently (Mario, 2026-07-20)
```

An entry in `data/coupon_schedules.csv` **overrides** class routing and sends the bond to
`vanilla-schedule` — that is how the documented coupon paths beat the workbook's free text.

## 4. Reclassifications that changed the numbers

- **make-whole → vanilla** (2026-07-02). A call within 7 days of maturity has essentially no
  option value. 46 bonds moved off the callable exclusion into canonical, flagged
  `is_make_whole`; only genuine-gap callables remain for the lattice.
- **the make-whole override layer** (2026-07-20). Documented make-whole-only bonds whose
  call/maturity gap fails the 7-day heuristic are routed by
  `data/make_whole_overrides.csv`. Sempra 8.9% 2013 is the worked case: SEC 424B2 shows a
  T+50 bp make-whole and **no par call**, and the custodian's `AB` was simply the first
  coupon date. It had previously been the one bond whose lattice price "conflicted with BT" —
  the conflict was the par-call assumption, not the bond.
- **coupon-type corrections** (2026-07-08). One amortising bond mislabelled "Fixed" left
  canonical; one formula-Fixed hybrid replaced it; and one bond whose `coupon_type` was
  mislabelled turned out to be a real fixed callable, moving the callable bucket 5 → 6.

## 5. Phase-2 classes (`dataio/phase2.py`)

Loaded from a master superset and routed per class:

```text
Agencies 42 -> 39     vanilla 27 · callable-lattice 5 · call-passed-vanilla 4 · zero 2
                      · cmo-tranche 1 (a REMIC Z misfiled among agencies, BT-marked)
Guaranteed 11 -> 9    all FDIC-TLGP, reported in their OWN bucket, never bank credit buckets
Index-linked 16 -> 15 nominal curve + recovered index ratio; one BT-marked (KTBi)
Govt MBS 888          engine skeleton only, awaiting the data pull
```

Duplicate legs are summed (par, market value, cost), which makes the ILB identity
`BT = BU/par·100` come out exact.

## 6. What "flagged" means

A flagged bond is carried at the custodian mark with a **specific** reason, never a generic
one, because the reason is what tells a later reader what would unblock it:

```text
schedule-unavailable · zero-structured · reset-terms-unavailable
hybrid-margin-unavailable · frn-curve-blocked · ilb-indexation-unverified
cmo-tranche · recovery
```

11 bonds are flagged at 3-31. Each maps to a row in the missing-data registry.

---

## Update 2026-08-30 — counts, and a bond that was in none of them

**Corporate output @3-31 is now 566 rows** (was 564): **555 priced + 11 flagged**.
The GBP units fix took it to 565 = 555 + 10; the 08-31 defaulted rule added the eleventh
flagged row, `TNTD03067251`. @6-10 the same chain reads 559 → 560 → **561**.

| route | @3-31 |
|---|---|
| `vanilla` | 481 |
| `make-whole-as-vanilla` | 47 |
| `vanilla-schedule` | 10 |
| `hybrid` | 10 |
| `hybrid-margin-unavailable` | 8 |
| `floating` | 7 |
| `recovery` | 2 |
| `frn-curve-blocked` | **0 — the route is now empty** |

⚠️ **The lesson is not the counts, it is where the missing bond was.** `TNTG301334W` (a plain
fixed 5.50% GBP bond of 2033) was **not in any of these numbers** — not priced, not flagged,
not excluded. The driver caught a curve error and **skipped** it, and its header has been
printing `skipped=1` for months without anyone reading it. It now prints `skipped=0`.

Two things follow for any coverage reasoning:

1. **Ask whether priced + flagged + excluded reconciles to the universe you started from**,
   not just how many are flagged. A flagged bond is visible; a skipped one is not.
2. The bond was `Coupon_Formula2 = Fixed` — i.e. inside the 617-row class Mario had already
   been shown as *finished*. **A completeness statement can be wrong for a class you have
   already signed off.**

**FOUR** denominators, for any plan quoting a number: **676** tab ROWS · **616** unique
SECURITIES on the tab · **566** held / rated / matched positions @3-31 (**561** @6-10) ·
**555** fully priced.

⚠️ The 676 → 616 step was missing from the earlier version of this file: **60 asset IDs are
listed more than once**, because the pivot counts rows. Row F13 was cited here as "2 tab rows,
1 held position", which is wrong in a way worth remembering — its two rows are the SAME bond
(`TNTD04283895`) listed twice, and it IS held. Reading a duplicate listing as an unheld
security understates coverage and invents a gap. `scripts/column_f_audit.py` prints all four
populations; quote it rather than a memory.
