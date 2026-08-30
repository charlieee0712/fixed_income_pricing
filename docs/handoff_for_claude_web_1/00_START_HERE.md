# START HERE — handoff 1

**Refreshed 2026-08-30 · repo `fixed_income_pricing` main at `23da147` · 287 tests green
(local ~21 s, server 47 ~34 s) · working tree clean, origin and 47 in sync.**

Client-confidential: this Project references a private US pension portfolio. Keep the
Project private; don't share its artifacts onward.

---

## The two bundles — the split is by PURPOSE, not by length

| | **handoff 1** (this one) | **handoff 2** |
|---|---|---|
| Files | 13 | up to 40 (32 today) |
| Purpose | everything needed to **decide** | everything needed to **specify** |
| Carries | state, numbers, locked decisions, the numerical laws, open asks, traps, feedback on your own plans | the same, plus per-domain deep dives: engine internals, the code map, module-level conventions, environment mechanics, the Monthly reconciliation |

**Handoff 1 is meant to be sufficient on its own for a decision.** If you are choosing scope,
sequencing a rollout, deciding a method, drafting comms or writing a report structure,
everything you need is here. Reach for handoff 2 when a plan has to name modules, functions or
per-engine behaviour — or when you want the full forensics behind something summarised here.

*(This bundle used to be deliberately terse and pointed at handoff 2 for anything substantive.
The user changed that on 2026-08-30: it should carry what the decision side needs.)*

## Your role

You are the **planning side**: strategy, methodology, prioritisation, scoping, comms drafting,
report structure. **Execution** — code, data, tests, server runs — happens in a Claude Code CLI
session on the private repo; you don't see the live code and don't need to. Hand back decisions
and designs the user can relay as directives, not code diffs.

What normally happens to a plan you write: the user uploads it to the repo, the CLI session
runs an **alignment gate** against the live tree, **adjusts the plan in place** where reality
differs, records the adjustments, and only then executes. **The most recent round had no plan
at all** — the ask arrived as annotations Mario wrote on a spreadsheet. Expect that again; this
client gives directives in the workbook.

Treat `02` as settled unless the user explicitly reopens an item. If today's date is more than
three weeks past the stamp above, ask for a refresh.

## Precedence when files disagree

```text
01 (current state, curated today)
  > 02 / 12 (locked decisions, numerical laws, traps — curated, stable)
  > 03 / 04 (verbatim repo docs; the WORKLOG is authoritative on history,
             but a fast-moving number may lag by hours)
  > everything else
```

## What is NEW — read in this order

1. **`01_current_state_and_open_items.md`** — the delta, and the fullest picture of where
   everything stands. Mario marked six rows of the coupon-type pivot as not-yet-covered; all
   six are now covered. **One of them turned out to be our own bug, not a data gap** — the
   sterling market-data file is stored in percent, not decimals, and we had a replacement-curve
   request open against two Bloomberg channels for something we already had. That correction,
   and the bond it had been hiding, is the most important thing in this refresh.
2. **`12_traps_and_plan_feedback.md`** — **NEW FILE.** Part A is the silent-failure list, in
   cost order; Part B is what your previous plans got wrong plus the **five habits**, including
   a new fifth: *a claimed data gap needs evidence from the source, not from our own error
   message.* Read this before writing a plan.
3. **`02_locked_decisions_and_conventions.md`** — decisions **and**, new in this refresh, a
   section **D** carrying the numerical laws a plan must not break (the calendar, the
   discounting law, the clean/dirty law, units, currency routing, the par-yield units registry,
   the migration law, the refuse-vs-forgive list).
4. **`08_workstream_weekly_report.md`** — the current Mario/Google-facing report (2026-08-30),
   replacing the 08-25 one in this slot. It answers his six cells one by one and carries **one
   question back to him** about the demonstration spreadsheet's layout — the only thing
   blocking us on the Excel side.
5. **`05_coverage_matrix.md`** — coupon class → engine → status, now pointing at the `pricer/`
   paths, with the GBP gap struck out.
6. **`06_missing_data_registry.md`** — one entry left this registry **without anyone sending us
   anything**, and the rule that follows is written into the file.
7. **`03_project_status_full.md`** · **`04_worklog_full.md`** — the canonical status document
   and the full dated history. The 2026-08-30 WORKLOG entry is the fullest account of this
   round; `03` is the deepest single source on method.
8. **`07_phase2_methods.md`** — agencies / guaranteed / inflation-linked (unchanged).
9. **`09_code_structure_template.txt`** — Mario's original template, the target architecture.
10. **`11_monthly_recon_report.md`** — the Gates-1–3 reconciliation (unchanged; still the basis
    for why the 2010 Monthly batch is not a numeric golden, which is why the tree and floating
    families have no golden at all).
11. **`10_glossary.md`** — custodian columns and project shorthand. Skim once; it decodes most
    of the vocabulary in the other files.

## Still only in handoff 2

Per-domain engine internals (the tree, the FRN projection, the hybrid composition), the code
map, module-level conventions, environment and execution mechanics, and the full verbatim set.
Per-bond ISIN evidence and the Gate-0 memo are in neither — ask the CLI session.

## How this bundle is maintained

Refreshed **only when the user explicitly asks** ("更新handoff") — not automatically at
milestones. Curated files (`00`, `01`, `02`, `10`, `12`) are updated in place, the NEW list
above is **replaced** rather than appended, `03`–`09` and `11` are re-copied verbatim, and the
bundle is re-zipped as `handoff1_<date>.zip`. Content is kept current rather than short; stale
content is displaced rather than accumulated.
