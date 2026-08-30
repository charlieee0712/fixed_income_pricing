# START HERE — handoff 1 (the short bundle)

**Refreshed 2026-08-30 · repo `fixed_income_pricing` main at `a5f7c81` · 287 tests green
(local ~21 s, server 47 ~34 s) · working tree clean, origin and 47 in sync.**

Client-confidential: this Project references a private US pension portfolio. Keep the
Project private; don't share its artifacts onward.

---

## There are two bundles

| | **handoff 1** (this one) | **handoff 2** |
|---|---|---|
| Files | ≤ 12 | up to 40 (32 today) |
| Purpose | fast re-orientation | the reference you plan *from* |
| Content | current state + the canonical repo docs | per-domain deep dives, the accumulated traps, and feedback on your previous plans |

Use this bundle to get current. **If you are writing an execution plan, read handoff 2** —
in particular its `02` (locked decisions), `03` (conventions), `05` (traps) and `06`
(feedback on your previous plans).

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

1. **`01_current_state_and_open_items.md`** — the delta. Mario marked six rows of the
   holdings workbook's coupon-type pivot as not-yet-covered; all six are now covered. One
   of them turned out to be **our own bug, not a data gap** — the sterling market-data file
   is stored in percent, not decimals, and we had been asking the client for a replacement
   curve we never needed. That correction, and what it cost, is the most important thing
   in this refresh.
2. **`08_workstream_weekly_report.md`** — **NEW: the current Mario/Google-facing report**
   (2026-08-30), replacing the 08-25 one in this slot. It answers his six cells one by one
   and carries one question back to him about the demonstration spreadsheet's layout.
3. **`02_locked_decisions_and_conventions.md`** — the rules your plans must respect. New
   entries this round: what "finished" means on Mario's pivot, the per-file par-yield units
   registry, the two exact floating-duration regimes, and the parity protocol correction.
4. **`05_coverage_matrix.md`** — coupon class → engine → status, now pointing at the
   `pricer/` paths, with the GBP gap struck out.
5. **`06_missing_data_registry.md`** — one entry left the registry **without anyone sending
   us anything**, and the rule that follows is written into the file: an entry whose only
   evidence is one of our own error messages is not yet a data gap.
6. **`03_project_status_full.md`** · **`04_worklog_full.md`** — the canonical status document
   and the full dated history, verbatim. The 2026-08-30 WORKLOG entry is the fullest account
   of this round.
7. **`07_phase2_methods.md`** — agencies / guaranteed / inflation-linked methods (unchanged).
8. **`09_code_structure_template.txt`** — Mario's original template.
9. **`11_monthly_recon_report.md`** — the Gates-1–3 reconciliation (unchanged; still the
   basis for why the 2010 Monthly batch is not a numeric golden).
10. **`10_glossary.md`** — custodian columns and project shorthand. Skim once.

## Not included on purpose

Per-bond ISIN evidence, the Gate-0 memo with cell/VBA citations, server mechanics, and the
code. All of it is in the repo; ask the CLI session. The deeper synthesis lives in handoff 2.

## How this bundle is maintained

Refreshed **only when the user explicitly asks** ("更新handoff") — not automatically at
milestones. Curated files (`00`, `01`, `02`, `10`) are updated in place, the NEW list above
is **replaced** rather than appended, `03`–`09` and `11` are re-copied verbatim, and the
bundle is re-zipped as `handoff1_<date>.zip`. File-count discipline: ≤ 12 files; new content
displaces old.
