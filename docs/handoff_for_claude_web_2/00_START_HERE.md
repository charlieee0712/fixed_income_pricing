# START HERE — handoff 2 (the deep bundle)

**Stamped 2026-08-30 · repo `fixed_income_pricing` main at `a5f7c81` · 287 tests green
(local Windows ~21 s, server 47 ~34 s) · working tree clean, origin and 47 in sync.**

Client-confidential: this Project references a private US pension portfolio (URS). Keep the
Project private and do not share its artifacts onward.

---

## What this bundle is, and how it differs from handoff 1

There are **two** bundles, and they are not the same document at two sizes:

| | **handoff 1** | **handoff 2** (this one) |
|---|---|---|
| Files | ≤ 12, new content displaces old | up to 40 (32 today) |
| Length | kept short on purpose | no limit; depth is the point |
| Purpose | fast re-orientation after a gap | the reference you plan *from* |
| Content | current state + the canonical repo docs | the same, plus per-domain deep dives, the accumulated traps, and feedback on your own previous plans |

If you only have a minute, read handoff 1. If you are **writing an execution plan**, read
this one — specifically files `02`, `03`, `05` and `06`, which exist to stop a plan from
being wrong in ways that have already happened.

## Your role

You are the **planning side**: strategy, methodology, prioritisation, scoping, comms
drafting, report structure. **Execution** — code, data, tests, server runs — happens in a
Claude Code CLI session on the private repo. You do not see the live code and do not need
to; hand back decisions and designs the user can relay as directives, not diffs.

What normally happens to your plans: the user uploads them to the repo, the CLI session runs
an **alignment gate** against the live tree, **adjusts the plan in place** where reality
differs, records the adjustments in a revision section, and only then executes.

**This round had no plan from you** — see `06` §5. The ask arrived as annotations Mario wrote
on a spreadsheet at the meeting. That is worth knowing because it is likely to happen again:
this client communicates in the workbook.

## Precedence when files disagree

```text
01 (current state, curated today)
  > 02 / 03 / 05 (locked decisions, conventions, traps — curated, stable)
  > 30-40 (verbatim repo docs; the WORKLOG is authoritative on history,
           but a fast-moving number may lag by hours)
  > everything else
```

If today's date is more than about three weeks past the stamp above, ask the user for a
refreshed bundle before leaning on state details.

## Reading order

**Orientation (read all of these before planning anything):**

1. `01_current_state.md` — every workstream, where it stands, with numbers.
2. `02_locked_decisions.md` — decisions that are settled, with dates and reasons. Do not
   re-litigate an item here unless the user explicitly reopens it.
3. `03_conventions_and_laws.md` — the numerical and methodological rules a plan must not
   break. Several are load-bearing for *every* validated number in the repo.
4. `05_traps_and_gotchas.md` — things that have bitten, or would have. Read once; the
   silent-failure section is the important half, and **§1.9–1.11 are new and expensive**.
5. `06_feedback_on_previous_plans.md` — what your last plans got wrong, the four habits that
   would have prevented it, and **a fifth habit added this round**.

**Then, by domain, as your plan requires:**

`10` architecture and code map · `11` fixed-rate and schedule engines · `12` the
embedded-option tree · `13` floating and hybrid (**migrated this round — rewritten**) ·
`14` curves and market data (**new §1a: par-yield units**) · `15` universe and routing ·
`16` the data-file / override layer · `17` the JSON-Excel interface and the demo
(**now seven instrument types**) · `18` testing and validation · `19` the Monthly-sheet
reconciliation · `20` environment and execution mechanics · `21` comms and counterparties ·
`22` deliverables and audience.

**Verbatim repo documents (`30`–`40`)** are the primary sources:

```text
30  CLAUDE.md                the CLI session's own operating memory — the single most useful
                             file for predicting what the execution side will and will not do
31  PROJECT_STATUS.md        the canonical methodology / architecture document
32  WORKLOG.md               the complete dated history, entry by entry
33  COVERAGE.md              coupon class -> engine -> status, over the 676-row pivot
34  missing_data.md          every gap -> landing file -> interim treatment -> request status
35  weekly report            2026-08-30, the current Mario/Google-facing deliverable
36  Round 2 detail           the embedded-option round in depth
37  JSON/Excel interface     the field-by-field contract; §14 is v1.1, the instrument types
38  Monthly Q62:Q71 mapping  the route census and the no-golden finding, with counts
39  phase-2 methods          agencies / guaranteed / inflation-linked
40  Mario's template         his original structure txt
```

## What changed since this bundle was created (2026-08-25)

**Round 2b, 2026-08-30 — the ask came from Mario's spreadsheet, not from a plan.**

1. **Mario annotated column F** of the workbook's `Pivot of Corp Bonds` sheet, marking six
   coupon families **`no`** (F12–F16, F20) and the plain-fixed row **`finished`**. "Finished"
   means *in the restructured `pricer/` package* — not "priced". All six are now covered:
   30 pivot rows → 29 held → 23 priced, the other 6 awaiting margins or defaulted.
2. **Three engines migrated** (floating, hybrid, coupon-schedule) into `core/pricing/`, with
   three thin asset wrappers; a live layering violation closed on the way.
3. **One endpoint contract change covering all seven instrument types** — vanilla, stepped,
   floating, fixed_to_floating, callable, puttable, sinking.
4. **⭐ The GBP curve was never missing.** A two-month-old "data gap", with a standing request
   to both Bloomberg channels behind it, was a units bug in our own loader. Two bonds now
   price; **one of them had been absent from the output rather than flagged**. This is the
   most instructive thing in the refresh: `05` §1.9–1.10, `14` §1a, `06` §5.

Test count 223 → **287**. Every pre-existing production number byte-identical, with the two
GBP bonds as the single itemised exception.

## Not in this bundle

Per-bond ISIN evidence (`docs/isin_lookup_2026-07-20.md`), the Gate-0 memo with cell/VBA
citations, server credentials, and the code itself. Ask the CLI session if a plan needs any
of it.

## How this bundle is maintained

Refreshed **only when the user explicitly asks** ("更新handoff") — not automatically at
milestones. Curated files are updated in place; `30`–`40` are re-copied verbatim; the
bundle is re-zipped as `handoff2_<date>.zip`. The user replaces the files in this Project's
knowledge.
