# START HERE — handoff 2 (the deep bundle)

**Stamped 2026-08-25 · repo `fixed_income_pricing` main at `68ebfef` · 223 tests green
(local Windows ~19 s, server 47 ~92 s) · working tree clean, origin and 47 in sync.**

Client-confidential: this Project references a private US pension portfolio (URS). Keep the
Project private and do not share its artifacts onward.

---

## What this bundle is, and how it differs from handoff 1

There are now **two** bundles, and they are not the same document at two sizes:

| | **handoff 1** | **handoff 2** (this one) |
|---|---|---|
| Files | ≤ 12, new content displaces old | up to 40 |
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

What actually happens to your plans: the user uploads them to the repo, and the CLI session
reads the plan, runs an **alignment gate** against the live tree, **adjusts the plan in
place** where reality differs, records the adjustments in a revision section, and only then
executes. Two plans went through that cycle on 2026-08-25 and both needed corrections —
`06_feedback_on_previous_plans.md` says exactly which, and why. Reading that file will make
your next plan measurably better.

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
   silent-failure section is the important half.
5. `06_feedback_on_previous_plans.md` — what your last two plans got wrong, what the
   verified facts are, and the four habits that would have prevented all of it.

**Then, by domain, as your plan requires:**

`10` architecture and code map · `11` fixed-rate and schedule engines · `12` the
embedded-option tree (callable / puttable / sinking — this week's work) · `13` floating and
hybrid (next week's migration target) · `14` curves and market data · `15` universe and
routing · `16` the data-file / override layer · `17` the JSON-Excel interface and the demo ·
`18` testing and validation · `19` the Monthly-sheet reconciliation · `20` environment and
execution mechanics · `21` comms and counterparties · `22` deliverables and audience.

**Verbatim repo documents (`30`–`40`)** are the primary sources:

```text
30  CLAUDE.md                the CLI session's own operating memory — the single most useful
                             file for predicting what the execution side will and will not do
31  PROJECT_STATUS.md        the canonical methodology / architecture document
32  WORKLOG.md               the complete dated history, entry by entry
33  COVERAGE.md              coupon class -> engine -> status, over the 676-row pivot
34  missing_data.md          every gap -> landing file -> interim treatment -> request status
35  weekly report            2026-08-25, the current Mario/Google-facing deliverable
36  Round 2 detail           the embedded-option round in depth
37  JSON/Excel interface v1  the field-by-field contract
38  Monthly Q62:Q71 mapping  the route census and the no-golden finding, with counts
39  phase-2 methods          agencies / guaranteed / inflation-linked
40  Mario's template         his original structure txt
```

## What changed since handoff 1 was last refreshed (2026-08-17)

Four things, all on 2026-08-25:

1. **Mario approved the code-structure sample**, with three follow-up points (currency,
   yield volatility, an Excel→JSON→Python process). All three are answered and built.
2. **The JSON/Excel interface shipped** — `pricer/endpoints/`, a file-based runner, and a
   thin VBA bridge, tested on real Excel (23/23) including a live round trip.
3. **Round 2a shipped** — the validated lattice migrated into `pricer/core/pricing/tree.py`
   and now serves callable, puttable and a new sinking-fund capability from one engine.
   FRN was deliberately deferred to next week (Round 2b).
4. **A demonstration workbook exists** — a real `.xlsm` that prices a bond live from cells,
   with a run sheet for the meeting.

Test count went 153 → 166 → 194 → **223** across those steps, and every pre-existing
production number is byte-identical throughout (checked by hashing whole output files, not
by spot-checking).

## Not in this bundle

Per-bond ISIN evidence (`docs/isin_lookup_2026-07-20.md`), the Gate-0 memo with cell/VBA
citations, server credentials, and the code itself. Ask the CLI session if a plan needs any
of it.

## How this bundle is maintained

Refreshed **only when the user explicitly asks** ("更新handoff") — not automatically at
milestones. Curated files are updated in place; `30`–`40` are re-copied verbatim; the
bundle is re-zipped as `handoff2_<date>.zip`. The user replaces the files in this Project's
knowledge.
