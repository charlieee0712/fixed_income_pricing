# START HERE — handoff bundle for the Claude-web planning side

**Refreshed 2026-08-15 · repo `fixed_income_pricing` @ `b91854f` (main) · 153 tests green.**
**First bundle in this multi-file structure — it SUPERSEDES the single-file
`HANDOFF_FOR_CLAUDE_WEB.md` (remove that file from Project knowledge if present).**

Client-confidential: this Project references a private pension portfolio. Keep the Project
private; don't share its artifacts onward.

## Your role (read once)

You (Claude on claude.ai, inside this Project) are the **planning side**: strategy,
methodology design, prioritization, comms drafting, report structure. **Execution** — code,
data, tests, server runs — happens in a Claude Code CLI session on the private repo; you
don't see the live code and don't need to. Hand back decisions and designs the user can
relay as directives, not code diffs. Treat `02_locked_decisions_and_conventions.md` as
settled unless the user explicitly reopens an item. If today's date is >3 weeks past the
stamp above, ask the user for a refreshed bundle before leaning on state details.

**Precedence when files disagree:** `01` (curated, newest) > `03`/`04` (verbatim repo docs,
may lag by days on freshly-moving items) > everything else. Numbers in `01` are current.

## What is NEW / read in this order

1. **`01_current_state_and_open_items.md`** — the delta-first summary: what changed
   2026-08-15 (Mario's code-structure directive, the sample we shipped, the Monthly-sheet
   golden discovery), the full current state (pipeline, engines, results @ 2009-03-31), who
   we are waiting on for what, and the milestone order.
2. **`08_workstream_code_structure_report.md`** — the ACTIVE workstream: the plain-language
   report sent to Mario with the restructured sample (his template applied to the vanilla
   chain; per-metric functions; input catalogue; the ~2,600-bond Monthly reconciliation
   proposal). `09_code_structure_template.txt` is Mario's original template it implements.
3. **`02_locked_decisions_and_conventions.md`** — the rules your plans must respect:
   calibration definition, dates, price-convention law, universe rules, data-gap discipline,
   the restructure ground rules. Do not re-litigate items here.
4. **`06_missing_data_registry.md`** — every known data gap → its landing file → interim
   treatment → request status (the living registry; Bloomberg wins over provisional values).
5. **`03_project_status_full.md`** — the canonical full methodology/architecture doc, verbatim.
6. **`04_worklog_full.md`** — the complete dated work history, verbatim (reverse-chronological;
   the 2026-08-15 entry covers today's directive + sample + Monthly decode in depth).
7. **`05_coverage_matrix.md`** — coupon-class → engine → status over the 676-row pivot.
8. **`07_phase2_methods.md`** — agencies / guaranteed / inflation-linked methods & results.
9. **`10_glossary.md`** — custodian columns and project shorthand (BT, 47, canonical, route,
   Monthly sheet, …). Skim once; return as needed.

Not included on purpose (ask the CLI session if needed): per-bond ISIN evidence
(`docs/isin_lookup_2026-07-20.md`), server/ssh mechanics, code files.

## How this bundle is maintained

The CLI session refreshes it at every milestone / comms-state change (or on request,
"更新handoff"): curated files `00`/`01`/`02`/`10` are updated in place (the NEW list above
is REPLACED each time, never appended), `03`–`09` are re-copied verbatim from the repo, and
the bundle is re-zipped. The user then replaces the files in this Project's knowledge.
File-count discipline: ≤ 12 files; new content displaces old.
