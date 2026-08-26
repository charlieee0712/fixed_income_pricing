# START HERE — handoff 1 (the short bundle)

**Refreshed 2026-08-25 · repo `fixed_income_pricing` main at `68ebfef` · 223 tests green ·
working tree clean, origin and 47 in sync.**

Client-confidential: this Project references a private US pension portfolio. Keep the
Project private; don't share its artifacts onward.

---

## There are now two bundles

| | **handoff 1** (this one) | **handoff 2** |
|---|---|---|
| Files | ≤ 12 | up to 40 |
| Purpose | fast re-orientation | the reference you plan *from* |
| Content | current state + the canonical repo docs | per-domain deep dives, the accumulated traps, and feedback on your previous plans |

Use this bundle to get current. **If you are writing an execution plan, read handoff 2** —
in particular its `02` (locked decisions), `03` (conventions), `05` (traps) and `06`
(feedback on your last two plans, with the four habits that would have prevented every
correction they needed).

## Your role

You are the **planning side**: strategy, methodology, prioritisation, comms drafting, report
structure. **Execution** — code, data, tests, server runs — happens in a Claude Code CLI
session on the private repo; you don't see the live code and don't need to. Hand back
decisions and designs the user can relay as directives, not code diffs.

Treat `02_locked_decisions_and_conventions.md` as settled unless the user explicitly reopens
an item. If today's date is more than three weeks past the stamp above, ask for a refresh.

**Precedence when files disagree:** `01` (curated, newest) > `03`/`04` (verbatim repo docs,
may lag by hours on fast-moving numbers) > everything else.

## What is NEW — read in this order

1. **`01_current_state_and_open_items.md`** — the delta. Two rounds shipped on 2026-08-25:
   Mario **approved** the code-structure sample and gave three follow-ups, all now answered
   and built (currency, the volatility question, and an Excel→JSON→Python round trip that is
   tested on real Excel); then callable, puttable and sinking-fund bonds landed on one shared
   tree. 194 → 223 tests, every pre-existing number byte-identical.
2. **`08_workstream_weekly_report.md`** — **NEW: the current Mario/Google-facing report.**
   This is the document being presented; it replaces the August-15 sample report in this
   slot. Note the audience change: the Google team now attends the briefing in person.
3. **`02_locked_decisions_and_conventions.md`** — the rules your plans must respect. Several
   new entries this round (the sinking-fund basis, the per-100 rule, the ISO-date rule).
4. **`06_missing_data_registry.md`** — every gap → landing file → interim treatment →
   request status. Nothing new was asked of anyone this round.
5. **`11_monthly_recon_report.md`** — the Gates-1–3 reconciliation. Still the basis for
   *why* the 2010 Monthly batch is not a golden; this round confirmed that **all 474**
   callable/puttable/sinking rows sit in that stale batch.
6. **`03_project_status_full.md`** · **`04_worklog_full.md`** — the canonical status document
   and the full dated history, verbatim.
7. **`05_coverage_matrix.md`** · **`07_phase2_methods.md`** — coverage by coupon class, and
   the agencies / guaranteed / inflation-linked methods.
8. **`09_code_structure_template.txt`** — Mario's original template.
9. **`10_glossary.md`** — custodian columns and project shorthand. Skim once.

## Not included on purpose

Per-bond ISIN evidence, the Gate-0 memo with cell/VBA citations, server mechanics, and the
code. All of it is in the repo; ask the CLI session. The deeper synthesis now lives in
handoff 2.

## How this bundle is maintained

Refreshed **only when the user explicitly asks** ("更新handoff") — not automatically at
milestones. Curated files (`00`, `01`, `02`, `10`) are updated in place, the NEW list above
is **replaced** rather than appended, `03`–`09` and `11` are re-copied verbatim, and the
bundle is re-zipped as `handoff1_<date>.zip`. File-count discipline: ≤ 12 files; new content
displaces old.
