# Monthly Q62:Q71 — mapping, route census, and what can be validated against

**Date:** 2026-08-25 · **Type:** Gate-0/6 evidence memo (Round 2) ·
**Sources:** the workbook itself, and `outputs/monthly_golden_rows.csv` (2,642 rows frozen
2026-08-17)

This memo separates three things that are easy to blur: what the **sheet says**, what the
**project has decided**, and what the legacy behaviour was that we deliberately do **not**
copy. Every count below is read from the frozen extract, not carried over from an earlier
document.

---

## 1. The cell block, verified

`Q61` is the header, not an entry — the ten items are **Q62:Q71**. Read out of the
`Monthly` sheet on 2026-08-25:

```text
row 60   Bond OAS Formula                      (block title)
row 61   Input Number | Field Name | Options | Description      <- header, cols N|O|P|Q
rows 62-71   the ten entries
row 67   cols N/O also read: 1 | AnalysisType As Double,
```

So the ten cells are **the option list of input #1, `AnalysisType`** — the number lives in
**column P**, the label in column Q:

| P | Q (Q62:Q71) | Family | This round |
|---|---|---|---|
| 1 | Bullet Bond Price | vanilla | already delivered (August sample) |
| 2 | Callable Bond Price | callable | **built** |
| 3 | Puttable Bond Price | puttable | **built** |
| 4 | SinkingF price | sinking fund | **built** (new capability) |
| 5 | OAS | common output | **built** for all three |
| 6 | Duration | common output | **built** for all three |
| 7 | FRN Price | floating | Round 2b (next week) |
| 8 | OAS FRN | floating | Round 2b |
| 9 | Duration FRN | floating | Round 2b |
| 10 | Mtge Price | mortgage | later MBS phase, data-gated |

Ten **analysis labels**, not ten security classes. Removing bullet and mortgage leaves four
product families, and five of the ten labels (2, 3, 4, 5, 6) are covered by this round.

This mapping is used for function naming, input-catalogue design and routing vocabulary. It
does **not** oblige us to reproduce the legacy VBA line by line, and it does not make a
saved value on the sheet a valid number to reconcile against — see §3.

## 2. Route census (verified counts)

From `mty_typ`, the field the legacy `bondcalc` routes on, across all 2,642 rows:

```text
   999  0                     206  #NAME?              10  CALL/SINK
   546  (blank)                69  NORMAL               8  SINKABLE
   442  CALLABLE              348  AT MATURITY          5  PERP/CALL
                                                        4  CALL/PUT
                                                        2  PUTABLE
                                                        2  CALL/EXT
                                                        1  CONV/PUT/CALL
```

Grouping by right (a row can carry more than one):

| Family | Rows | Composition |
|---|---|---|
| callable | **464** | CALLABLE 442 + CALL/SINK 10 + PERP/CALL 5 + CALL/PUT 4 + CALL/EXT 2 + CONV/PUT/CALL 1 |
| puttable | **7** | PUTABLE 2 + CALL/PUT 4 + CONV/PUT/CALL 1 |
| sinking | **18** | SINKABLE 8 + CALL/SINK 10 |
| convertible | 1 | CONV/PUT/CALL — **excluded**: put and call rights alone do not price a convertible |

`CALL/SINK` (10) and `CALL/PUT` (4) are the empirical argument for one shared tree rather
than three product engines: those rows need two rights at once, which a per-product engine
cannot express without duplicating the other.

> **Correction to the plan's floating count.** The plan carries "FLOATING-labelled rows =
> 426". That number is not in this extract: `mty_typ` contains **no** FLOAT label at all,
> and `calc_typ_des` has **29** (FIX-TO-FLOAT BONDS 22, FLOAT RATE NOTE 6, plus one
> variant). 426 is the *URS production* floating count, a different population. Round 2b
> should derive its FRN cohort from this extract rather than reusing 426.

## 3. The decisive finding: there is no numeric golden for these families

The August-17 reconciliation established that the 2010-03-01 batch is a
`legacy-stale-session` — an older code revision run against mixed-vintage cached market
data — and therefore not a valid numeric target for any engine, while the 2012-12-12 batch
reproduces at the legacy solver's own noise floor and *is* a golden.

Applying that to this round's families:

```text
tree-family rows (callable / puttable / sinking)   474
   ... in the stale 2010-03-01 batch               474      100%
   ... in the sound 2012-12-12 cohort                0        0%
```

**Every single one is stale.** So the Monthly sheet offers this round no number to
reconcile to, and no amount of effort would change that. Stating it plainly is the point:
it would be easy, and wrong, to tune a new engine until it reproduced those cached values.

Consequence for validation, which is what §1.4 of the plan requires:

| Evidence used | What it proves |
|---|---|
| production-output parity (SHA256 on three driver CSVs) | the migration changed nothing that was already validated |
| direct-call parity with `==` | the new wrappers are the same computation, not a similar one |
| invariants on controlled fixtures | the new sinking capability behaves as the economics require |
| three-way vs Bloomberg duration | an external, session-independent check where a column exists |

The Monthly sheet remains authoritative for **function shape, input terminology and route
inventory** — which is exactly how it was used to design this round — and is not used for
numeric agreement.

## 4. Row classification

Using the plan's vocabulary, for the 474 tree-family rows:

```text
legacy-stale-session      474    all of them; diagnostic and descriptive only
current-code-session-golden  0    no tree-family row sits in the sound 2012-12 cohort
combined-feature            14    CALL/SINK 10 + CALL/PUT 4 — one shared tree required
convertible-excluded         1    CONV/PUT/CALL — needs a conversion model we do not have
route-ambiguous             69    NORMAL rows that were sometimes sent through the legacy
                                  sink flag; a normal fixed bond is NOT a sinking-fund bond
                                  and none is reclassified here
missing-schedule           all    no row carries exercise terms; the legacy fed schedules
                                  from Bloomberg at run time, and they were never saved
```

That last line is the practical boundary of the whole exercise: even for the stale rows we
do not hold the call/put/sink schedules the legacy used, so a row-by-row comparison is not
merely unreliable, it is not reconstructible. Our exercise terms come from
`data/call_schedules.csv`, which is a documented, swappable data table.

## 5. Legacy behaviour we deliberately do not copy

- the legacy lattice fitted the curve with a per-step "sloperow" adjustment rather than a
  standard calibration; ours is a forward-induction Arrow-Debreu fit that reprices the
  input curve's discount factors exactly;
- the legacy read short-end fixings, schedules and "SteepFlat" ASCII tables from Bloomberg
  at run time — none of which we have, and one of which (SteepFlat) is lost;
- `analysisType` 5/6 (OAS, Duration) are computed on our own calibrated tree with the
  project's clean-vs-clean convention and dirty-price duration denominator, not the
  legacy's.

These are recorded as decisions, with reasons, so that a later reader does not mistake a
difference for a defect.
