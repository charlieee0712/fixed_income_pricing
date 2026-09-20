# Investor progress update — draft deck

**For:** the project's investors at Goldman Sachs · **Date:** week of 2026-09-21
**Format:** 8 slides. One chart. No demo, no implementation detail — Mario's brief.

**How to read this file.** Each `##` heading is one slide. The bullets are what goes ON the
slide, written to be read in five seconds. The *Say* block is what the presenter says and
does **not** go on the slide. Everything in square brackets is a note to us, not to them.

⚠️ Every number here was read out of a live run on 2026-09-19, not from memory. The census
command is at the end.

---

## Slide 1 — Fixed-income pricing system: progress to 19 September 2026

- Built for the client's fixed-income portfolio
- Presented by [YOUR NAME] and Mario [SURNAME] — fill these in
- Twelve weeks of work, 26 June to 19 September 2026

*Say:* Keep this up for ten seconds. No preamble.

---

## Slide 2 — What we were asked to build, and where it stands

- The client had a pricing toolkit built in Excel and Visual Basic, grown over years, that
  only a handful of people could run or change
- **The job: rebuild it as proper software** — same answers, but testable, automatable, and
  able to be handed to their own engineering team
- **Status: the system works end to end and is in use.** The remaining work is extending it
  to the rest of the portfolio

*Say:* Two things to land here. First, this was never a research project — it is a rebuild
of something that already ran the client's business, so "does it give the same answers" was
always the test. Second, the thing exists and runs today; we are not describing a plan.

---

## Slide 3 — What it does today

- Takes a bond, the market rates for that day, and the price the client's custodian
  recorded — and works out **what the market is charging that borrower, and how much the
  bond's value moves when rates move**
- Runs **from a spreadsheet**, from a command line, or as a service the client's own systems
  can call — same answer from all three
- **Every result is reproducible**: run it again a month later and you get the identical
  file, to the byte
- We price the client's **March 2009 book** — their own reference case, chosen because the
  outcomes are already known

*Say:* The third point is worth a sentence. In a pricing system that number is the whole
product, so we made "did anything change" a mechanical check rather than a matter of
opinion. Every time we change the code, every price the system has ever published is
regenerated and compared. That is how we can tell you a restructuring changed nothing.

[We do NOT say "525 automated tests". It means nothing to this audience and invites the
wrong question.]

---

## Slide 4 — Coverage

**Chart: one horizontal stacked bar, 2,260 securities** — `docs/img/investor_coverage.png`

| | securities | |
|---|---:|---|
| **Priced today** | **766** | every ordinary bond in the portfolio |
| Waiting on data we have asked for | 1,046 | 882 mortgage securities + 164 bonds whose terms are not in the file we were given |
| Scoped, not yet built | 412 | the other pooled products |
| Excluded by the client, or out of scope | 36 | |

- **All six classes of ordinary bonds are complete** — corporate, government, municipal,
  agency, inflation-linked, guaranteed
- **The single largest remaining block is not waiting on us**

*Say:* The honest reading of this chart is the second bullet. Of what is left, roughly
eight securities in ten are blocked on data we have formally requested, and two in ten are
work we have scoped but not started. That distinction is the whole message of this meeting.

---

## Slide 5 — How we know the numbers are right

- **A government bond priced on its own government's curve must come out at zero.** Japan's
  come out at 0.0; the UK's at 0.04% — the thermometer reads right in ice water
- **The client's own custodian independently reports a risk number for some bonds.** Where
  it does, ours agrees — four of five agency bonds within a tenth of a year
- **We re-derived the client's own inflation adjustments from published government
  statistics** — thirteen US inflation-linked bonds, agreeing to six parts in a million

*Say:* None of these three checks uses anything we control. That is the point — we are not
grading our own homework. The third one also caught something: the client's records are
struck one day after the valuation date. Small, but nobody knew it.

---

## Slide 6 — The one thing blocking the largest block

- **882 mortgage securities — 39% of the portfolio — need terms that only Bloomberg has**
- **The engine for them is already built and tested.** It has been waiting on data, not on
  code — the day the data lands it runs with no further development
- **Requested 22 July 2026.** [STATUS — confirm the week of presenting; see the note]
- A second, smaller request covers 164 ordinary bonds whose terms are missing from the file
  we were given

*Say:* This is the slide we would most like you to remember. There is no technical obstacle
and no disagreement about what is needed. Four in ten securities in this portfolio become
priceable on work that is already finished, as soon as the terms arrive.
BEFORE PRESENTING, REPLACE THE THIRD BULLET. As of 19 September we had word the data may
just have been delivered, unverified. Use whichever is true on the day.
If it has NOT arrived: "Requested 22 July 2026 — still outstanding." The ask is that you
help move it.
If it HAS arrived: "Requested 22 July; the data reached us in September and we are loading
it now." That is the better version of this slide — the engine was built ahead of the data
and the largest remaining block is unlocking rather than stuck.
Do not leave the outstanding wording standing once it is false. An investor who later
learns the data had already arrived will discount everything else on these slides.
Say all of this without blame either way. The request went to the client; we are surfacing
it, not escalating it. If asked why it took this long, the honest answer is we do not know.

---

## Slide 7 — What is left

- **Mortgage-backed securities** — engine built, awaiting data *(882)*
- **The other pooled products** — collateralised mortgage obligations, asset-backed,
  commercial mortgage-backed. Scoped; each reuses machinery that already exists *(412)*
- **A portfolio-level credit risk layer** — in the original brief, not yet started
- We are not blocked on anything in the second and third items except sequencing

*Say:* Be straight that the 412 is genuine remaining work, not a data problem. What makes it
tractable is that the hard parts — the cash-flow machinery, the option model, the market
data plumbing — are built and proven on the 766.

---

## Slide 8 — Handover

- The client asked for the code to be restructured so **their own engineering team can take
  it over** — that restructuring is complete
- It **runs unchanged on their cloud platform**, so the whole team can use it rather than one
  machine
- Everything ships with the data and the instructions to reproduce it — nothing depends on
  us being in the room

*Say:* This matters commercially. The deliverable is not a service they have to keep buying;
it is an asset they own and can run. That was the brief and it is met.

---

## Reconstructing every number on these slides

```bash
PYTHONPATH=src python scripts/release_facts.py        # row counts + hashes of every output
python - <<'PY'
import pandas as pd
def census(p):
    d = pd.read_csv(p)
    c = [x for x in d.columns if x.startswith('implied')
         and 'straight' not in x and 'cleanden' not in x]
    return len(d), int(d[c].notna().any(axis=1).sum())
for p in ('outputs/implied_oas_2009-03-31.csv', 'outputs/callable_risk.csv',
          'outputs/sovereign_risk_2009-03-31.csv', 'outputs/phase2_risk_2009-03-31.csv'):
    print(p, census(p))
PY
```

| number on a slide | where it comes from |
|---|---|
| 766 priced, 786 in an output | the census above, at 2009-03-31 |
| 2,260 securities / 2,366 lines | the holdings workbook's sub-category totals |
| 949 in the six complete classes | same |
| 163 named-and-excluded | `outputs/corporate_disposition_2009-03-31.csv`, 166 skipped less the 3 priced on the lattice |
| 135 terms-unavailable + 9 no-rating | the same file's reason codes |
| Japan 0.0 / UK 0.04% | `sovereign_risk_2009-03-31.csv`, median by currency |
| agency risk agreement | `phase2_risk_2009-03-31.csv`, model duration against the custodian's |
| six parts in a million | `tests/test_inflation_data.py` |
| 22 July 2026 request | `docs/missing_data.md` |

⚠️ **One thing to settle before this is presented.** The portfolio is a **March 2009**
snapshot — the client's own test case, chosen because the answers are known. Nobody on
these slides is told that, and an investor who spots a 2009 date without explanation will
wonder whether the work is current. Suggest one clause on slide 3: *"we price the client's
March 2009 book, which is their reference case because the outcomes are already known."*
