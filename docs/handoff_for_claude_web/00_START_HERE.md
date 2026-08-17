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

1. **`01_current_state_and_open_items.md`** — delta-first: what changed 2026-08-17. Your
   Monthly-reconciliation plan was **executed through Gate 3 the same day** (Gate 0 refuted
   Rev A's §2/§3 premises → plan is Rev B in the repo; the user then explicitly authorized
   Gates 1–3). Headlines: engine parity proven exact on current-code-session caches; the
   2010-03-01 batch = `legacy-stale-session` (not a valid golden); durations three-way vs
   Bloomberg goes 94% our way. Your memory of Rev A is stale.
2. **`11_monthly_recon_report.md`** — **NEW: the Gates-1–3 report** (results, evidence
   chain for the stale-session verdict, re-baselined tolerances, what remains tree-gated).
   The Gate-0 inventory memo (cell/VBA citations) lives in the repo:
   `docs/monthly_gate0_memo_2026-08-17.md` — ask the CLI session if needed.
3. **`08_workstream_code_structure_report.md`** — the workstream AWAITING MARIO (Drive
   upload + WhatsApp ping 08-17): the plain-language report + restructured sample — its §5
   now carries the Monthly-reconciliation evidence. `09_code_structure_template.txt` = his
   original template.
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
