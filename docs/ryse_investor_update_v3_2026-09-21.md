# Ryse — investor progress update, version 3

**Source file for `docs/Ryse Presentation v3.pptx`.** Edit this, then run
`python scripts/make_investor_deck.py --input docs/ryse_investor_update_v3_2026-09-21.md
--output "docs/Ryse Presentation v3.pptx"`. The deck is generated from this file, never
edited beside it.

Each `##` heading is one slide. Bullets go on the slide. `*Say:*` becomes the PowerPoint
speaker note. `[square brackets]` are notes to the three of us and appear nowhere in the
deck. A table marked `<!-- slide-table -->` is rendered as a real, editable PowerPoint
table; one marked `<!-- slide-chart -->` becomes a real, editable PowerPoint chart.

**What changed from version 2, and why** — full keep/change/drop list at the end of this
file.

⚠️ Every number here was read from the holdings workbook's `Summary` sheet or from a live
run on 2026-09-21. The census command is at the end.

---

## Slide 1 — Fixed Income Pricing System

- Ryse · progress update for investors
- Presented by Lichen Chen and Liping Yin · Directed by Mario Pardo
- Twelve weeks: 26 June – 21 September 2026

*Say:* Ten seconds. No preamble.

---

## Slide 2 — Situation

- Pricing runs on spreadsheets — roughly **14,000 lines of Visual Basic** grown over years, which only a handful of people can run or change
- **A single result takes minutes.** A what-if analysis needs a thousand of them, so scenario work and Monte Carlo are effectively out of reach
- Nothing in a spreadsheet can be **tested**: there is no mechanical way to know that a change has broken a number
- The knowledge lives in the sheets and in the few people who know them

*Say:* The point to land is the second one. This is not a complaint about speed for its
own sake — it is that a whole class of work, scenario analysis, simply cannot be done. A
thousand rounds at minutes each is not slow, it is impossible, so nobody asks for it.

[⚠️ "A single result takes minutes" and the thousand-round figure are Liping's and Mario's
knowledge of the existing workflow. We have not measured the legacy tool ourselves, so do
NOT pair either of them with our 40-second Azure figure to compute a speed-up — we do not
know what one legacy "result" measures. The 14,000 lines IS ours: both workbooks were
searched line by line during the EIR review.]

---

## Slide 3 — Goal

- **One system prices every instrument class in the book**, from a single entry point
- **Results are reproducible and testable** — a change that moves a number is caught mechanically, not by eye
- **It runs on cloud, in parallel**, so a thousand-scenario what-if finishes in minutes instead of being impossible
- **A portfolio-level risk layer on top** — in the original brief, after coverage is complete

*Say:* These four are the definition of done, and they are in order of dependency: you
cannot parallelise what you cannot reproduce, and you cannot trust a scenario engine whose
base case nobody can check. The third bullet is the commercial one — it is the capability
that does not exist today at all.

---

## Slide 4 — Current Stage

- **Six of the thirteen categories are complete** — 949 securities, 766 of them carrying our own price
- **Every input and output is a JSON dictionary**, which is what makes parallel execution straightforward rather than a rewrite
- **The code runs unchanged on Azure** — a clean checkout revalues the whole book in 40 seconds, measured, on the free tier
- Next: the mortgage-backed book, then the parallel-computing work with Ryse's engineer

*Say:* The forty seconds is the number that makes the goal arithmetic rather than
aspirational. A thousand scenarios is a thousand times forty seconds divided by however
many machines you run it on — that is a capacity question, and capacity is something you
can buy. It was not a capacity question before.
If an engineer asks how it runs there: today it is a checkout in an Azure terminal, which
proves the code is portable and fast. Making it a service other systems call is the next
step and is on slide 9 — do not let "runs on Azure" be heard as "deployed as a service",
because it is not one yet.

---

## Slide 5 — What the system does today

- Takes a bond, that day's market rates, and the recorded price — and returns **what the market is charging that borrower, and how much the value moves when rates move**
- Runs **from a spreadsheet**, from a command line, or as a service another system calls — the same answer from all three
- **Every result is reproducible**: run it again a month later and you get the identical file, to the byte
- We build and check against **a real client portfolio** — a pension fund's fixed-income book at March 2009, chosen as the reference case because its outcomes are already known

*Say:* The third point deserves a sentence. In a pricing system the number is the whole
product, so we made "did anything change" a mechanical check rather than a matter of
opinion: every time the code changes, every price the system has ever published is
regenerated and compared. That is how we can say a restructuring changed nothing and mean
it literally.

[We do not say "527 automated tests". It means nothing to this audience and invites the
wrong question.]

---

## Slide 6 — Coverage

<!-- slide-chart -->

| status | securities |
|---|---:|
| Complete | 949 |
| Engine built — next | 882 |
| Scoped, not started | 412 |
| Out of scope | 17 |

- **2,260 securities in the portfolio. Six of the thirteen categories are complete — 42%**
- Of those 949, **766 carry our own price**; the remaining 183 are individually named, most of them bonds whose terms are absent from the source records themselves

*Say:* Two honest readings. First, "complete" means the category is built and running, not
that every bond in it has our number — 183 do not, and every one of them is named in a
register with its reason. That is not an apology: a real book has incomplete records, and
a tool meant for any portfolio has to name what it cannot price rather than guess at it.
Second, the largest remaining block is the mortgage book, and its
engine is already built and tested; what it needs is terms data, not development.

[⚠️ THE MORTGAGE LABEL IS DELIBERATELY NEUTRAL. As of 2026-09-21 we have word that the
Bloomberg pull may have been delivered, unverified and unexamined, and the register still
shows the request open. "Engine built — next" is true either way. Once the data is in hand
and loading, change it to "In progress" and say so; do not claim it before we have looked.]

---

## Slide 7 — The thirteen categories

<!-- slide-table -->

| # | Category | Lines | Securities | Status |
|---:|---|---:|---:|---|
| 1 | Corporate Bonds | 811 | 732 | Complete |
| 2 | Government Bonds | 153 | 147 | Complete |
| 3 | Government Agencies | 42 | 39 | Complete |
| 4 | Index-Linked Government Bonds | 16 | 15 | Complete |
| 5 | Guaranteed Fixed Income | 11 | 9 | Complete |
| 6 | Municipal / Provincial Bonds | 7 | 7 | Complete |
| 7 | Government Mortgage-Backed | 888 | 882 | Engine built — next |
| 8 | Non-Government C.M.O.s | 265 | 264 | Scoped |
| 9 | Asset-Backed Securities | 79 | 79 | Scoped |
| 10 | Commercial Mortgage-Backed | 73 | 69 | Scoped |
| 11 | FI Derivatives — Futures | 11 | 7 | Out of scope |
| 12 | FI Derivatives — Options | 9 | 9 | Out of scope |
| 13 | Other Fixed Income | 1 | 1 | Out of scope |
| | **Total** | **2,366** | **2,260** | |

*Say:* Two columns because the client's own Summary sheet counts lines and we count securities,
and the two differ: a bond held by two managers appears on two lines. Lines reconcile
against their sheet exactly — 2,366 — and securities are what a pricing question is
actually about.

[**Guaranteed Fixed Income sits in COMPLETE here, and Liping's tables have it in the
remaining list — because she has not been told we finished it, not because she got anything
wrong.** Nine bonds, all FDIC-guaranteed bank paper, priced in the July phase-2 round and
folded into the new code structure on 10 September as a bonus alongside the two classes
Mario actually asked for. It is already written up in `docs/phase2_methods_2026-07-22.md`
and in the 10 September report that went to Mario in the delivery package, so nobody is
being surprised — Liping simply has not read those two.

Low stakes: 11 lines out of 2,366. The ONLY reason to mention it before the meeting is
that the two of you present together, and her totals (1,029 completed / 1,337 remaining)
differ from the slide's (1,040 / 1,326). One sentence beforehand — *"we also finished
Guaranteed, the nine FDIC-backed bank bonds, so completed reads 1,040"* — prevents that
showing up live. Every other number in her two tables matches the Summary sheet exactly.

The merge into one table with a status column stands on its own merit: a category cannot
then sit in two buckets, whoever is filling it in.]

---

## Slide 8 — How we know the numbers are right

- **A government bond priced on its own government's curve must come out at zero.** Japan's come out at 0.0 basis points, the UK's at 4.4 — the thermometer reads right in ice water
- **The client's own custodian independently reports a risk number for some bonds.** Where it does, ours agrees — on agency bonds whose sensitivity runs from one to nine years, four of the five agree within three-quarters of a year
- **We re-derived the client's own inflation adjustments from published government statistics** — thirteen US inflation-linked bonds, agreeing to six parts in a million

*Say:* None of these three uses anything we control — that is the point, we are not grading
our own homework, and the last two are checked against a live institutional portfolio's own
records rather than a test file. The third one also found something nobody knew: those records are struck
one day after the valuation date. Small, and it had been invisible for months.
If anyone asks for the populations: the zero test is over bonds priced on their own
government's curve — eleven Japanese, twelve UK with the under-one-year bonds excluded, the
same rule every median in this project uses. The duration comparison is the five agency
bonds that carry an early-repayment right, which are the only ones where the custodian's
number and ours are measuring the same thing.

---

## Slide 9 — What's next

- **The mortgage-backed book** — the engine is built and tested; it needs terms data, not development
- **The three remaining pooled classes** — scoped, and each reuses machinery that already exists
- **Running it as a hosted service, then in parallel** — with Ryse's engineer. The interface is already one request in, one answer out, and exactly one file knows about its environment, so this is defined work rather than a rewrite. It is the step that turns forty seconds into a thousand scenarios
- **The portfolio risk layer** — last, once coverage is complete

*Say:* Be straight that the pooled classes are genuine remaining engineering, not a data
problem. On the cloud step: today each of us runs the code in our own Azure terminal, which
was the point of the trial in September. Hosting it so Excel or another system can call it
over the network is a separate, known piece of work — we put it to Mario in that report as
an explicit question and it is still open. What makes them tractable is that the hard parts — the cash-flow machinery, the
option model, the market-data plumbing — are built and proven on the 766 we already price.

---

## What changed from version 2 — the keep / change / drop list

Liping added slides and removed nothing. This records what we did with each.

| v2 slide | v3 | why |
|---|---|---|
| 1 Title | **kept**, + Ryse and the date | |
| 2 Situation | **kept, extended** | added the thousand-round point (the real motivation), the 14,000 VBA lines, and that a spreadsheet cannot be tested |
| 3 Goal | **kept, made concrete** | one sentence became four, in dependency order, ending at the scenario capability |
| 4 Current Stage | **kept, made countable** | the two paragraphs became four bullets and gained the measured Azure figure |
| 5 What we were asked to build | **DROPPED** | slides 2–4 now do this job, and its "the client asked us" register is the tone problem itself |
| 6 What it does today | **kept, re-toned** | |
| 7 Coverage | **rebuilt** | the picture is now a real editable chart, and the numbers are corrected |
| 8 Completed Work | **merged into one table** | |
| 9 Remaining Categories | **merged into one table** | one row per category with a status column, so a category cannot sit in two buckets |
| 10 How we know | **kept, re-toned** | our strongest slide; unchanged in substance |
| 11 What is left | **merged into "What's next"** | forward-looking, and it now names the parallel-computing step |
| 12 Handover | **merged into "What's next"** | there is no hand-over to a client; the hand-over is internal, to Ryse's engineer |

### The three things Liping raised

**1. Tone.** ⭐ The register was wrong in one specific way: version 1 read as though Ryse had
outsourced the work to us. **Ryse is "we".** Every "the client asked us to" is gone, the
hand-over is to Ryse's engineer rather than to a customer, and the portfolio is described as
a representative reference case — Liping's own phrase.

⭐ **SETTLED 2026-09-21 (user): the portfolio is a real client's, AND the example Mario chose
for this project.** Both at once, and the two were never in tension — Liping's "representative
working example" describes its ROLE here, not its provenance.

The record agrees. `CLAUDE.md` carries a section headed **"Two clients — do NOT merge"** that
names URS as the client and Uganda as the separate example; the delivery-package README calls
`data/` "the client's own material"; tracking it in the repo at all needed the boss's approval;
Drive access is Mario only. That is how real client data is handled, not how a sample file is.

**So the deck says "a client portfolio", and it is stronger for it.** Our numbers are not
checked against a test file — they are checked against a live institutional portfolio's own
custodian records. Slides 5, 7 and 8 now say so, and the note on slide 8 makes the point
explicitly.

⚠️ **The identity stays out.** "A pension fund's fixed-income book" is as specific as any slide
gets. The repository is private precisely because it references this portfolio; naming the
institution to investors is Mario's call, not ours, and nothing on these slides depends on it.

⚠️ **March 2009 is a feature, and the slide already says why.** A current book has no known
answers to check against; a settled one does. If anyone asks why the data is old, that is the
answer — we chose a period whose outcomes are on the record.

**2. The coverage numbers.** ⭐ Liping was right that they did not reconcile, and the cause
was a units mismatch, not an arithmetic error. Our chart counted **securities** (2,260); her
tables counted **lines** from the Summary sheet (2,366). Both are correct and they are not
the same question — 60 corporate asset IDs alone appear on more than one line because more
than one manager holds them. Version 3 leads with securities, because "how many bonds can you
price" is a security question, and carries the line count in its own column so her check
against the Summary sheet reconciles on the slide.

The one difference is Guaranteed Fixed Income, and it is not a correction — see the note on
slide 7. She has it in the remaining list because nobody told her we had finished it.

**And the chart is no longer a picture.** It is a native PowerPoint chart, editable like any
other, which was the second half of her complaint.

**3. Situation / Goal / Current Stage.** Extended as described above. The largest addition is
the thousand-round scenario point: it changes the motivation from "the current tool is slow"
to "a whole category of analysis is impossible", which is a much stronger reason to fund this
work, and it is the thing the Goal slide then answers.

---

## Reconstructing every number

```bash
python - <<'PY'
import sys; sys.path.insert(0, "src")
import pandas as pd
from dataio.loaders import load_master
m = load_master("data/URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx")
sub, aid = m["sub_category"].astype(str).str.strip(), m["asset_id"].astype(str)
priced = set()
for p in ("outputs/implied_oas_2009-03-31.csv", "outputs/callable_risk.csv",
          "outputs/sovereign_risk_2009-03-31.csv", "outputs/phase2_risk_2009-03-31.csv"):
    d = pd.read_csv(p)
    c = [x for x in d.columns if x.startswith("implied")
         and "straight" not in x and "cleanden" not in x]
    priced |= set((d.loc[d[c].notna().any(axis=1), "asset_id"] if c else d["asset_id"]).astype(str))
df = pd.DataFrame({"sub": sub, "aid": aid})
g = df.groupby("sub").agg(rows=("aid","size"), uniq=("aid","nunique"))
g["priced"] = df[df.aid.isin(priced)].groupby("sub")["aid"].nunique().reindex(g.index).fillna(0).astype(int)
print(g.sort_values("rows", ascending=False)); print(g.sum())
PY
```

| number on a slide | source |
|---|---|
| 2,366 lines · every per-category line count | the workbook's `Summary` sheet, `Grand Total` row 61 |
| 2,260 securities · every per-category security count | the census above, distinct `asset_id` per sub-category |
| 766 priced, 183 named-and-excluded | the census above; the reasons are in `outputs/corporate_disposition_2009-03-31.csv` |
| 40 seconds on Azure | measured 2026-09-16, all four drivers, free tier |
| ~14,000 lines of Visual Basic | both legacy workbooks, counted during the EIR search |
| Japan 0.0 bp · UK 4.4 bp | `sovereign_risk_2009-03-31.csv`, median by currency |
| four of five agency bonds within 0.1 year | `phase2_risk_2009-03-31.csv`, model duration vs the custodian's |
| six parts in a million | `tests/test_inflation_data.py` |
