# START HERE — handoff 2 (the deep bundle)

**Stamped 2026-09-26 · repo `fixed_income_pricing` main at `2d111d3` plus this refresh ·
594 tests green (local Windows ~60 s) · origin and 47 in sync · 39 files in this bundle.**

*Three rounds since the 09-16 stamp: the inflation data (09-19), the investor deck (09-22),
and the mortgage book (09-25/26). The mortgage round is the one that changes planning —
read `26` before scoping anything securitised.*

Client-confidential: this Project references a private US pension portfolio (URS). Keep
the Project private and do not share its artifacts onward.

---

## What this bundle is, and how it differs from handoff 1

There are **two** bundles, and they are not the same document at two sizes:

| | **handoff 1** | **handoff 2** (this one) |
|---|---|---|
| Files | 13, new content displaces old | up to 40 (**39 today**) |
| Length | no longer capped, but curated for deciding | no limit; depth is the point |
| Purpose | everything needed to **decide** | everything needed to **specify** — the reference you plan *from* |
| Content | state · numbers · locked decisions · the numerical laws · open asks · traps | the same, plus per-domain deep dives, the accumulated traps, and feedback on your own previous plans |

If you only have a minute, read handoff 1. If you are **writing an execution plan**, read
this one — specifically `02`, `03`, `05` and `06`, which exist to stop a plan from being
wrong in ways that have already happened, and `24` if the plan touches numbers on more
than one machine.

## Your role

You are the **planning side**: strategy, methodology, prioritisation, scoping, comms
drafting, report structure. **Execution** — code, data, tests, server runs — happens in a
Claude Code CLI session on the private repo. You do not see the live code and do not need
to; hand back decisions and designs the user can relay as directives, not diffs.

⚠️ **Read `06` §6 before assuming a plan is wanted.** Of the last four rounds, none came
from a web plan: two came from a user-written instruction document, one from the words
"ultrathink start", and one from a question. That is not an argument against planning —
it is evidence about *where* a plan earns its round trip. **A plan pays when there are
open decisions or new modelling. It is overhead when the procedure is established and
the decisions are already made.**

⚠️ **And this bundle was last refreshed 2026-08-31, two weeks and four rounds ago.** When
a plan is written from a snapshot, the CLI session runs an alignment gate against the
live tree and adjusts in place. Four plans in a row needed such an adjustment; the one
that put its gate **first** did not need one afterwards. See `06` §6.

## Precedence when files disagree

```text
01 (current state, curated today)
  > 02 / 03 / 05 / 24 (locked decisions, conventions, traps, determinism — curated)
  > 41 (release_facts — machine-generated from the files themselves; authoritative
       for any row count, hash or test number)
  > 30-40, 42-43 (verbatim repo docs; the WORKLOG is authoritative on history,
       but a fast-moving number may lag by hours)
  > everything else
```

⚠️ **For any count, hash or test number, `41_release_facts_verbatim.md` outranks prose
anywhere — including CLAUDE.md.** It is written by a script from the files it describes.
Three separate stale numbers were found in prose in one week (see `06` §7, Habit 8).

If today's date is more than about three weeks past the stamp above, ask the user for a
refreshed bundle before leaning on state details.

## Reading order

**Orientation (read all of these before planning anything):**

1. `01_current_state.md` — every workstream, where it stands, with numbers.
2. `02_locked_decisions.md` — settled decisions, with dates and reasons. Do not
   re-litigate an item here unless the user explicitly reopens it.
3. `03_conventions_and_laws.md` — the numerical and methodological rules a plan must not
   break. Several are load-bearing for *every* validated number in the repo.
4. `05_traps_and_gotchas.md` — **29 silent failures**, in cost order. Read once.
   ⚠️ §1.18–1.29 are new this refresh and several are about tools that were built to
   catch mistakes and contained the same mistake.
5. `06_feedback_on_previous_plans.md` — what your previous plans got wrong, and the
   **eight habits** that would have prevented nearly all of it. Habits 6–8 are new.

**Then, by domain, as your plan requires:**

`10` architecture and code map · `11` fixed-rate and schedule engines · `12` the
embedded-option tree · `13` floating and hybrid · `14` curves and market data ·
`15` universe and routing · `16` the data-file / override layer · `17` the JSON-Excel
interface and the demo · `18` testing and validation · `19` the Monthly-sheet
reconciliation · `20` environment and execution mechanics · `21` comms and counterparties ·
`22` deliverables and audience · **`23` the government and sovereign book (NEW)** ·
**`24` determinism and cross-platform (NEW)** · **`25` cloud and the Azure trial (NEW)**.

**Verbatim repo documents are the primary sources:**

```text
30  CLAUDE.md                the CLI session's own operating memory — the single most useful
                             file for predicting what the execution side will and will not do
31  PROJECT_STATUS.md        the canonical methodology / architecture document
32  WORKLOG.md               the complete dated history, entry by entry
33  COVERAGE.md              coupon class -> engine -> status, over the 676-row pivot
34  missing_data.md          every gap -> landing file -> interim treatment -> request status
35  weekly report            2026-09-10, the current Mario/Google-facing deliverable
36  Round 2 detail           the embedded-option round in depth
37  JSON/Excel interface     the field-by-field contract; §14 is the instrument types,
                             §14.6.1 the product that deliberately has none, §15 the labels
38  Monthly Q62:Q71 mapping  the route census and the no-golden finding, with counts
39  phase-2 methods          agencies / guaranteed / inflation-linked
40  Mario's template         his original structure txt
41  release_facts            ⭐ NEW — rows, sha256 and text fingerprint of every output
                             file, plus the real pytest line. Machine-written. Quote this
42  sovereign scope          NEW — the audit behind the government/municipal round
43  government instruction   NEW — the 09-10 directive doc, whose §1 is its Gate 0
```

## What changed since the 2026-09-16 stamp — three rounds, and one that resets the map

**2026-09-19 — inflation data, sourced by us.** The measurement redirected the work: a
per-country *constant* inflation assumption is a no-op (at 2% every spread moved by exactly
ln(1.02) and nothing else moved), so the data landed on the index ratio instead. All 13 US
ratios validate to 5.9e-06; the Korean linker is priced. `525` tests.

**2026-09-22 — the investor deck, v1 to v6.** Nine slides for the Goldman Sachs investors.
⭐ The finding worth carrying: the reviewer works in **Google Slides**, which cannot open an
embedded PowerPoint chart — it shows a rendered preview instead. That is why a chart came
back "blurry" twice, and why a v3 "fix" (PNG → chart object) never touched the problem. The
bundle's own guidance: anything a colleague has to edit must be a native shape or a table.

**⭐ 2026-09-25/26 — the mortgage book, and it changes what "remaining" means.** The Bloomberg
pull arrived complete (882/882) but as-of the pull date, not 2009; the master already held
the field we most needed. The last engine outside the template moved in. 505 of 882 are
priced. **594 tests.**

⚠️ **The part that should reshape a plan:** only 56% of the mortgage class is a simple
pass-through pool. Counting the same structure across CMOs, ABS and CMBS, about **756
securities — a third of the whole book — need deal-level waterfall data that no field-level
pull contains.** That is a purchase decision (Intex, or Bloomberg CMO analytics), not a
scheduling one. **Read `26` before scoping anything securitised.**

**Also decided:** Mario demoed a browser front end calling Azure pricing APIs, which answers
the hosted-service question we put to him on 09-16. Not started; waits for coverage. See `25`.

---

## What changed in the refresh before that (2026-08-31 → 09-16)

Four rounds, two weeks, **390 → 495 tests**, and three rounds since taking it to **594** (the section above). `01` carries each in full; the short version:

1. **2026-09-03 — Government Bonds + Municipal/Provincial priced** (154 securities, 147
   at the baseline). Locked the own-currency curve convention; found that
   `EUR_Yield_Curve.txt` is a sovereign *composite*, not a swap curve; found one price
   quoted per 1,000 — and that the custodian made the same error, poisoning the obvious
   cross-check. See `23`.
2. **2026-09-10 — the government book moved onto the `pricer/` template.** Agencies,
   index-linked and guaranteed, together, because they share one loader, one driver and
   one hashed CSV. **63 securities before, 63 after, every output byte-identical** — the
   invariance *is* the deliverable. The inflation-linked engine was the only real
   migration; agencies never had an engine of their own. See `23`.
3. **2026-09-13 — the Excel/JSON interface was documenting numbers that rot.** Six
   currencies named where fourteen are priced; a header claiming "194 checks, Scope:
   vanilla". Both fixed by removing the hand-maintained copy rather than editing it.
   ⭐ **"7 / 5 / 5" became "8 / 7 / 5 / 5"** — until the ILB migration, every product the
   engine priced had a contract type. See `17` and `23` §11.
4. **2026-09-15 — the code ran on Azure**, on pandas 3.0, 483 green in 40 s. And the
   parity tooling built to police it contained two of its own traps. See `24` and `25`.

⚠️ **Three claims in the previous version of this bundle, or in CLAUDE.md, were wrong
rather than merely stale, and are corrected here:**

1. **The endpoint's JSON is NOT byte-identical across platforms.** CLAUDE.md said it
   was; that was written when the endpoint priced vanilla only. `24` §3.
2. **The handoff bundles do NOT still carry the F13 "2 rows, 1 held" error.** CLAUDE.md
   says they must be fixed at the next refresh; they were already fixed on 2026-08-31.
3. **`supported_currencies()` is 14, not 6** — and the number appeared wrong in two
   shipped places at once. `05` §1.22.

## Not in this bundle

Per-bond ISIN evidence (`docs/isin_lookup_2026-07-20.md`), the Gate-0 memo with cell/VBA
citations, server credentials, Azure credentials, and the code itself. Ask the CLI
session if a plan needs any of it.

## How this bundle is maintained

Refreshed **only when the user explicitly asks** ("更新handoff") — never automatically at
milestones. Curated files (`00`–`25`) are updated in place; `30`–`43` are re-copied
verbatim by `scripts`-adjacent tooling; no zip is produced any more — the user uploads
the folder.

⚠️ **The curated half goes stale silently and the verbatim half does not**, because
nothing links a curated file to the thing it describes. That asymmetry is why this
refresh found three wrong claims rather than three outdated ones.
