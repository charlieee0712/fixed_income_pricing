# START HERE — handoff bundle for the Claude-web planning side

**Refreshed 2026-08-17 · repo `fixed_income_pricing` main (docs-only commit after `241e76f`) ·
153 tests green (unchanged — Gate 0 touched no code).**
This multi-file bundle supersedes the old single-file `HANDOFF_FOR_CLAUDE_WEB.md` (remove that
file from Project knowledge if still present).

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

1. **`01_current_state_and_open_items.md`** — delta-first: what changed 2026-08-17 (your
   Monthly-reconciliation plan was executed at Gate 0 — **its Rev-A §2/§3 premises were
   refuted by the workbook/VBA evidence**; the plan is now Rev B in the repo), plus the full
   current state and waiting-on list.
2. **`11_monthly_gate0_memo.md`** — **NEW: the Gate-0 inventory memo** (all verdicts with
   cell/VBA-line citations). Read this before any further planning on the Monthly
   reconciliation: it replaces Rev A's assumptions (government curves, not Libor/swap;
   `vba_compat` dropped; month-grid parity mode; routing fields; vanilla golden ≈ 420 rows,
   not ~1,900; duration three-way added). The repo's plan file is already Rev B — your local
   memory of Rev A is stale.
3. **`08_workstream_code_structure_report.md`** — the workstream still AWAITING MARIO: the
   plain-language report + restructured sample (his template on the vanilla chain).
   `09_code_structure_template.txt` = his original template.
4. **`02_locked_decisions_and_conventions.md`** — the rules your plans must respect. Do not
   re-litigate items here.
5. **`06_missing_data_registry.md`** — every known data gap → landing file → interim
   treatment → request status. (Gate 0 opened NO new asks; the lost SteepFlat twist file
   becomes an ask only when the T/U gate opens.)
6. **`03_project_status_full.md`** — canonical full methodology/architecture doc, verbatim.
7. **`04_worklog_full.md`** — complete dated history, verbatim (the 2026-08-17 entry = Gate 0
   in depth; 2026-08-15 = directive + sample + Monthly decode).
8. **`05_coverage_matrix.md`** — coupon-class → engine → status over the 676-row pivot.
9. **`07_phase2_methods.md`** — agencies / guaranteed / inflation-linked methods & results.
10. **`10_glossary.md`** — custodian columns and project shorthand. Skim once; return as
    needed.

Not included on purpose (ask the CLI session if needed): per-bond ISIN evidence
(`docs/isin_lookup_2026-07-20.md`), server/ssh mechanics, code files.

## How this bundle is maintained

The CLI session refreshes it at every milestone / comms-state change (or on request,
"更新handoff"): curated files `00`/`01`/`02`/`10` are updated in place (the NEW list above
is REPLACED each time, never appended), `03`–`09` and `11` are re-copied verbatim from the
repo, and the bundle is re-zipped. The user then replaces the files in this Project's
knowledge. File-count discipline: ≤ 12 files; new content displaces old (now at 12).
