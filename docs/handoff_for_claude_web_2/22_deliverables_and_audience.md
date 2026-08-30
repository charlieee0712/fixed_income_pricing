# Deliverables and audience

How outward-facing work is written and packaged. This shapes report structure, so it is
directly relevant to any plan that ends in a document.

---

## 1. The audience changed on 2026-08-25

The Google / cloud team **now attends the briefing in person**. They no longer just receive
the code afterwards. So every report must serve two audiences at once:

- **plain language throughout** — define each bond term in a clause where it first appears
  ("callable = the borrower may repay early"; "OAS = the extra yield the market demands from
  this borrower"). Assume no fixed-income background;
- **one clearly-labelled engineering section** — architecture, the single entry point, how
  to run it, determinism, parallelism — which the finance reader can skip;
- **say in the opening which section is for whom**, so neither audience wastes time deciding.

And do not talk down to Mario in the process. The test that works: could an engineer with no
bond knowledge follow the argument, and would a portfolio manager still find the numbers
they came for?

## 2. Report structure that has worked

The 2026-08-25 weekly report is the current model:

```text
1  where the module stands            one table of headline facts
2  your three follow-up points        answer the counterparty's OWN questions first, in
                                      their own words, before anything else
3  what is new this round
4  the headline number, with a table  the specific thing they asked for
5  for the engineering team           labelled, skippable
6  what we deliberately did not do    boundaries, stated as choices with reasons
7  next week
8  questions back to you
```

Section 2 matters more than it looks: leading with *their* questions rather than with our
work is what makes the rest get read.

## 3. Honesty conventions that have paid off

Every one of these has been used, and each strengthened the deliverable rather than
weakening it:

- **state what has no evidence.** "No holding in the portfolio is a puttable bond today, so
  there is no live comparison to make" — said plainly, alongside what *is* tested.
- **report the negative result.** All 474 tree-family workbook rows are in a stale batch, so
  there is no number to reconcile to. Saying so pre-empts the obvious question and prevents
  a bad instinct (tuning to stale values).
- **report defects the testing found.** The VBA `null` bug went into the report. It
  demonstrates that the testing is real.
- **name the per-bond variation.** Two of three callables barely move with volatility; a
  portfolio-level average would have hidden that. Saying it is what makes the one real
  number credible.
- **quote from a run, not from a summary.** A table built from a CSV's rounded spread once
  contradicted the report's own claim; recomputing exactly fixed it. Self-review the numbers
  against a fresh run before rendering.

## 4. Packaging

```text
code_structure_sample/            git-ignored staging folder at the repo root
├── 00_README.md                  what is here, what changed
├── 01_weekly_report_<date>.md/pdf
├── 02_code_walkthrough_<date>.md/pdf
├── 03_json_excel_interface_v1.md
├── 04_round_detail_<date>.md/pdf
├── 05_previous_report_<date>.md
└── src/ tests/ scripts/ integrations/
                                  + code_structure_sample_<date>.zip
```

The user drags the folder or zip to Google Drive; Drive access is Mario-only.

Mechanics: `robocopy /E` after removing the destination — **never `/MIR`**, and never in the
same command as a `Remove-Item`. PDFs come from `scripts/md_to_pdf.py`.

## 5. The walkthrough

A separate document from the report: a **speaking aid** for the live session, currently 15
minutes. Structure: an opening line, a five-step tour in file order, a table of numbers to
have ready, and pre-answered likely questions. The questions section is the most useful part
— it is where "why 364-day years?" and "can this scale in the cloud?" get answered before
they are asked.

## 6. The demo

A real `.xlsm` that prices a bond from cells in about two seconds, plus a five-minute run
sheet with what to click, what to say, what to do when something fails, and an explicit
"what this demo does not claim" section.

The design lesson from its first version: **a demo button must never make the presenter
leave the application**. The original "show me the JSON" button handed over a temp-file path
to go and find; now the request and the answer appear on the sheet automatically.

## 7. Sample-first

Before a repo-wide change, build the smallest convincing slice plus a one-page report, and
wait for approval. It worked: the August sample came back approved with three **additive**
comments rather than a redesign, which is the cheapest possible outcome.

---

## Update 2026-08-30

**Package of the round** — `code_structure_sample/` staged and zipped as
`code_structure_sample_2026-08-30.zip` (616 KB, 113 files), for the user to drag to Drive:

```text
00_README.md                          orientation, and the two things to know first
01_weekly_report_2026-08-30.md + pdf  the deliverable
02_code_walkthrough_2026-08-30.md+pdf the 15-minute guided tour, refreshed for seven asset files
03_json_excel_interface_v1.md         the contract; section 14 is the v1.1 instrument types
04_previous_report_2026-08-25.md      context
05_round2_detail_2026-08-25.md        the embedded-option round in depth
src/ tests/ scripts/ integrations/    the code (robocopy /E, __pycache__ excluded)
```

Checks run before zipping, worth repeating every time: **no handoff files in the package**
(they carry internal comms framing and are not for Mario), **no `docs/` folder copied
wholesale**, no `__pycache__`, and the only workbook present is the demonstration one we
built. Both bundles' zips are git-ignored, as is the staging folder.

**Report structure that worked** — the 08-30 report leads with the six cells answered one by
one, then spends a full section on the GBP correction *as a correction*, then the interface
change, then what was deliberately not done, then the engineering section, then one question
back. Putting the correction third — after the answer he asked for, before the engineering —
kept it from reading either as burying it or as leading with an apology.

**A number in a report must be traceable to a run.** This round that discipline caught a wrong
count in a commit message (flagged 11 → 9, actually 11 → 10) and one unverified claim in the
draft report — that the 23 Excel checks still passed. They were re-run rather than assumed,
and they do.

**PDF**: `python scripts/md_to_pdf.py --input X.md --output Y.pdf`. One command; the three
silently-failing Edge flags are already inside the script and must not be re-derived.
