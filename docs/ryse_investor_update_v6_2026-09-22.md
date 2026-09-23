# Ryse — investor progress update, version 6

**Source for `docs/Ryse Presentation v6.pptx`.** Edit this, then run
`python scripts/make_investor_deck.py --input docs/ryse_investor_update_v6_2026-09-22.md
--output "docs/Ryse Presentation v6.pptx"`.

**Presenting tomorrow:** Liping takes slides **2–5**, Lichen takes **6–9**.

⭐ **Version 6 answers Liping's two notes on version 5, and the second one found a mistake we
had been making for three versions.** She asked for futures and options in the coverage bar, and
she asked why the bar was blurry. It was blurry because it was a PowerPoint *chart object*, and
she works in Google Slides, which cannot open one: it keeps the bytes and shows a rendered
preview instead. That is also why she could not edit the numbers on that slide in either round,
and why version 4 carried her new numbers in the table but not in the bar — the table was the
only half she could reach. Version 3 had already "fixed" this once, by turning a PNG into a
chart object, which never touched the real problem. The bar is now ordinary rectangles and text
boxes, which Slides imports as editable native shapes.

⚠️ Every number was read from the holdings workbook's `Summary` sheet or from a live run.
Sources are tabulated at the end.

---

## Slide 1 — Upgrading the Fixed Income Pricing System

- Ryse · progress update for investors
- Presented by Lichen Chen and Liping Yin · Directed by Mario Pardo
- Twelve weeks: 26 June – 22 September 2026

*Say:* Ten seconds. No preamble.

---

## Slide 2 — Situation

- Pricing depends on years of accumulated VBA code (~14,000 lines) spread across workbooks that only the owner can operate or modify.
- Running a thousand what-if scenarios takes far too long, or crashes Excel, making scenario analysis and Monte Carlo simulations impractical.
- Spreadsheets cannot be tested: there is no systematic way to detect when a change produces a wrong result.

*Say:* The point to land is the second one. This is not a complaint about speed for its own
sake — it is that a whole class of work, scenario analysis, simply cannot be done. A
thousand rounds at minutes each is not slow, it is impossible, so nobody asks for it.

[Liping's wording, kept. The only edit is grammatical: "or crash Excel" → "or crashes Excel".
⚠️ The ~14,000 lines is ours and countable — both legacy workbooks were searched line by line
during the EIR review. "Takes far too long" and the thousand-round figure are Liping's and
Mario's knowledge of the current workflow; we have never timed the legacy tool, so do NOT
pair either with our 40-second figure to compute a speed-up.]

---

## Slide 3 — Goal

- A single system prices every instrument class in the book.
- Outputs are reproducible and testable: **a change to the code** that alters a result is detected automatically.
- Cloud-based parallel execution means a thousand-scenario what-if completes in minutes instead of being out of reach.
- Layered on top: portfolio-level risk, available once all instrument classes are coded.

*Say:* These four are the definition of done, and they are in order of dependency: you cannot
parallelise what you cannot reproduce, and you cannot trust a scenario engine whose base case
nobody can check. The third is the commercial one — it is the capability that does not exist
at all today.

[⚠️ ONE WORD CHANGED, AND IT MATTERS. Version 4 read "a **rate** change that alters a result
is detected automatically". That is backwards: when rates change the result is *supposed* to
change — that is the system working, not a fault. What the testing catches is a change to the
CODE that moves a number nobody meant to move. Worth mentioning to Liping before she presents
it, since she may be asked what the sentence means.]

---

## Slide 4 — Current Stage

- 6 of 13 categories done: 949 securities, with 766 priceable by the new engine.
- JSON dictionaries for every input and output — this makes parallel computing much easier.
- **The code already runs unchanged on Azure** — a clean checkout reprices the whole book in 40 seconds, measured.
- Next: focus on mortgage-backed securities and other instruments, then hand the code to Ryse's engineer for parallel-computing work.

*Say:* The forty seconds is what makes the goal arithmetic rather than aspirational. A
thousand scenarios is a thousand times forty seconds divided by however many machines you run
it on — a capacity question, and capacity is something you can buy. It was not a capacity
question before.
If an engineer asks how it runs there: today it is a checkout in an Azure terminal, which
proves the code is portable and fast. Hosting it so other systems can call it is the next step
and is on slide 9 — do not let "runs on Azure" be heard as "deployed as a service".

[⚠️ VERSION 4 SAID "The code **will be** run unchanged on Azure", and dropped the 40 seconds.
Both are a loss: we HAVE run it there, on 16 September, and the measurement is the strongest
number on this slide. The future tense understates what is done. What is *not* done is hosting
it as a service — a different thing, and slide 9 says so.]

---

## Slide 5 — What our new system does today

- Given a bond, today's rate, and the market price, it returns the spread the market is charging that borrower and the bond's sensitivity to rate moves.
- Runs three ways — spreadsheet, command line, or as a service other systems call — and returns the same answer from all three.
- Reproducible to the byte — run it again a month later, same results.
- Built and checked against a real portfolio — a pension fund's fixed-income book, March 2009 — chosen because the answers are already known.

*Say:* The third point deserves a sentence. In a pricing system the number is the whole
product, so we made "did anything change" a mechanical check rather than a matter of opinion:
every time the code changes, every price the system has ever published is regenerated and
compared. That is how we can say a restructuring changed nothing and mean it literally.

[Liping's wording, kept unchanged.]

---

## Slide 6 — Coverage

<!-- slide-chart -->

| status | securities |
|---|---:|
| Complete | 949 |
| Engine built — next | 882 |
| Not yet built | 429 |

- **2,260 securities in the portfolio. Six of the thirteen categories are complete — 42%**
- Of those 949, **766 carry our own price**; the remaining 183 are individually named, most of them bonds whose terms are absent from the source records themselves

*Say:* Two honest readings. First, "complete" means the category is built and running, not
that every bond in it has our number — 183 do not, and every one of them is named in a
register with its reason. That is not an apology: a real book has incomplete records, and a
tool meant for any portfolio has to name what it cannot price rather than guess at it. Second,
the largest remaining block is the mortgage book, and its engine is already built and tested;
what it needs is terms data, not development.

[⚠️ The mortgage label is deliberately neutral. "Engine built — next" is true whether or not
the Bloomberg pull has landed. Once the data is in hand and loading, change it to "In progress"
and say so — but not before we have looked at it.]

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
| 8 | Non-Government C.M.O.s | 265 | 264 | Scoped, not started |
| 9 | Asset-Backed Securities | 79 | 79 | Scoped, not started |
| 10 | Commercial Mortgage-Backed | 73 | 69 | Scoped, not started |
| 11 | FI Derivatives — Futures | 11 | 7 | Scoped, not started |
| 12 | FI Derivatives — Options | 9 | 9 | Scoped, not started |
| 13 | Other Fixed Income | 1 | 1 | Out of scope |
| | **Total** | **2,366** | **2,260** | |

*Say:* Two columns because the holdings file counts lines and we count securities, and they
differ — a bond held by two managers appears on two lines. Lines reconcile against that sheet
exactly, at 2,366. If anyone asks about the last three rows: the futures and options are
counted as work still to do, not as work written off — they are not bonds and they would need
machinery we have not designed, but they are sixteen securities and nobody should leave thinking
we have excluded them. The last row is a fund holding rather than a bond — no ISIN, no maturity
and no rating — so there is nothing in it for a bond model to price. The bar on the previous
slide groups all three rows into "not yet built", which is the same statement said more coarsely.

[The unit cost and the mark are in the file and they confirm the reading, but they are one real
position's cost and valuation and this is said out loud in front of the client's counterparty.
The structural facts carry the point on their own.]

[⭐ RESOLVED IN V6, AND THE V5 DIAGNOSIS WAS BACKWARDS. V5 read v4's chart-vs-table
disagreement as Liping having changed the table by mistake, and "fixed" it by pulling the table
back. She had not made a mistake: she changed the table because the table was the only one of
the two she COULD change — the chart was a PowerPoint chart object, which Google Slides cannot
edit. She asked for futures and options in the chart, so v6 moves both together: the bar is
949 / 882 / 429 and rows 11-12 read "Scoped, not started".
⚠️ ONE THING TO KNOW WHILE PRESENTING: no document scopes futures and options, and CLAUDE.md
still lists them out of scope. We are following Liping, who is on the calls. If Mario has not
actually committed to them, this is the slide where that surfaces — the wording is "not yet
built", which claims nothing beyond the fact.]

---

## Slide 8 — How do we know the numbers are right

**Three checks. Not one of them uses anything we control.**

- **A thermometer has to read zero in ice water.** We measure what a bond pays above its own government's cost of borrowing — so for a government's own bond, the answer has to be zero. Japan comes out at 0.00%, the UK at 0.04%.
- **An outside system computes some of the same numbers, and ours match.** The custodian holding these bonds publishes its own measure of how much each one moves when interest rates move. We compute ours from scratch — on four of the five where both exist, the two agree.
- **We rebuilt the client's own figures from public data.** An inflation-linked bond carries a factor for the inflation since it was issued. We recomputed all thirteen of them from published US inflation statistics — and they match to six parts in a million.

*Say:* The header is the whole slide: we are not grading our own homework. Each of these three
is checked against something outside the system — a mathematical identity, someone else's
calculation, and public government data.
Numbers if anyone asks. The zero test covers bonds priced on their own government's curve —
eleven Japanese and twelve UK, with the under-one-year bonds left out, the same rule every
average in this project uses. The rate-sensitivity comparison is the five agency bonds that
can be repaid early, the only ones where the custodian's figure and ours measure the same
thing; four agree within three-quarters of a year on figures running from one to nine years,
and the fifth differs by about two. The inflation check found something too: those records are
struck one day after the valuation date, which had been invisible for months.

[⚠️ THIS SLIDE IS WHY VERSION 5 EXISTS. Lichen said he could no longer follow his own bullets,
and he is presenting it. What made it unreadable was that each claim opened with the mechanism
and only then said what it proved — and two of the three needed a bond-maths term first
("spread", "sensitivity of one to nine years") before the sentence made sense.
Each bullet now opens with the CLAIM in ordinary words and puts the evidence second, and the
header carries the point of the whole slide. The tolerances came off the slide into the notes:
"agrees within three-quarters of a year" cannot be read by anyone who does not already know
what a year of sensitivity means, and it is not the claim — the claim is that somebody else
computed it and we match.
Version 4's "Sanity check / Independent check / Validation check" labels were a real
improvement on version 3 and the idea survives — the labels became the opening phrase of each
sentence instead of a heading above it, which saves three lines and reads aloud better.]

---

## Slide 9 — What's next

- **The mortgage-backed book** — the engine is built and tested; it needs terms data, not development
- **The three remaining pooled classes** — mortgage obligations, asset-backed and commercial mortgage-backed; each reuses machinery that already exists
- **Hosting it as a service, then running it in parallel** — with Ryse's engineer. It is a defined piece of work, not a rewrite: the system already answers one request at a time, which is exactly the shape a cloud service wants
- **The portfolio risk layer** — last, once coverage is complete

*Say:* Be straight that the pooled classes are genuine remaining engineering, not a data
problem. What makes them tractable is that the hard parts — the cash-flow machinery, the
option model, the market-data plumbing — are built and proven on the 766 we already price.
On the cloud step: today each of us runs the code in our own Azure terminal, which was the
point of the September trial. Hosting it so Excel or another system can call it over the
network is separate, known work — we put it to Mario in that report as an explicit question
and it is still open.
⚠️ If anyone joins the previous slide to this one and asks why futures and options are not on
it: because "scoped" on that table is a status, not a queue position. They are sixteen securities
out of 2,260, they are the only remaining rows that would need machinery we have not designed,
and they sit behind everything on this slide. Say that rather than improvising a date.

[Bullet 3 was two sentences of engineering in version 3/4, including "exactly one file knows
about its environment", which means nothing to this audience. Shortened to the claim that
matters: it is a defined piece of work rather than a rewrite. Bullet 2 spells out what
"pooled classes" are, since Lichen presents this.]

---

## Slide 10 — The team

<!-- slide-columns -->

| Lichen Chen | Liping Yin |
|---|---|
| <<DEGREE PROGRAMME>>, Columbia University · <<GRADUATING MONTH YEAR>> | <<LIPING: programme / affiliation>> |
| Built the instrument pricing engines, the calibration and risk layer, and the Excel-to-Python interface. | <<LIPING: what you did on this project>> |
| <<ONE LINE OF BACKGROUND BEFORE THIS — an internship, a role, a degree. Delete this row if you would rather not.>> | <<LIPING: one line of background, or delete this row>> |
| lc3904@columbia.edu | <<LIPING: contact>> |

*Say:* Almost nothing. Advance to this as you say "happy to take questions", give it one
line — "and that's us; do get in touch" — and leave it up. **Do not read your own bio
aloud**; they can read, and narrating it is the one way to make it awkward. The reason this
slide exists is that it stays on screen for the whole of Q&A, which is the most-looked-at
minute of the meeting.

[⭐ WHY A NEW SLIDE RATHER THAN A CORNER OF SLIDE 9. Slide 9 is the forward plan and it is
the note the presentation should close on; bolting biographies onto it would blunt that. A
separate final slide also buys the thing that actually matters here — it is the one that
sits on screen through every question.

BUILT FROM TEXT BOXES, NOT A TABLE, ON PURPOSE. Liping writes her own half, and she writes
it in Google Slides, where a text box arrives native and editable and a chart object does
not. Same reason the coverage bar stopped being a chart in this version. A blank cell is
skipped rather than drawn, so the two halves do not have to be the same length.

⚠ EVERY <<...>> IS AN UNFILLED PLACEHOLDER AND THE BUILD REFUSES TO PRODUCE THE DECK
WHILE ONE SURVIVES. That is deliberate: the alternative is a placeholder going up on a
screen in front of the investors. Square brackets were not used because the parser already
treats a bracketed line as a note to ourselves and drops it silently.

⚠ MARIO IS NOT ON THIS SLIDE. Slide 1 credits him as directing, and Liping asked for the
two presenters. If he expects a third half, that is a two-minute change — worth a message
tonight rather than a discovery tomorrow.

ON THE CONTRIBUTION LINE: it names three things and deliberately stops there. It does not
claim the curve bootstrap, which was a colleague's port, and it does not reach into
Liping's half — she describes her own work in her own words.]

---

## What changed — version 5 over Liping's version 4, then version 6 over that

Liping's version 4 is a plain-language pass over version 3 and **most of it is kept verbatim** —
slides 1, 2 and 5 are hers, and the improvements on 3 and 8 are hers in substance.

**Version 6** does two things, both from her review of version 5: it draws the coverage bar from
plain shapes instead of a chart object, so it is sharp and editable in Google Slides; and it
moves futures and options into the remaining-work count in the bar and the table together
(row 1 below, rewritten — version 5 had this backwards). Rows 2–4 are the version 5 changes,
unchanged.

| # | slide | change | why |
|---:|---|---|---|
| 1 | **6, 7** | Futures and Options are **Scoped, not started**, in the bar AND the table | ⭐ What v5 got backwards. Liping changed the table and not the chart because the chart was a chart OBJECT and Google Slides cannot edit one. v6 moves both: bar 949 / 882 / **429**, rows 11-12 Scoped |
| 2 | **8** | rewritten for plain language, keeping her three-check structure | ⭐ the explicit ask: the presenter could not follow his own bullets |
| 3 | **3** | "a **rate** change that alters a result" → "a change **to the code**" | a rate change is *supposed* to alter the result; what testing catches is a code change that moves a number nobody meant to move |
| 4 | **4** | "the code **will be** run on Azure" → "already runs", and the 40 seconds restored | we ran it on 16 September. The future tense understates what is done, and the measurement is the strongest number on the slide |

Plus two words: "or crash Excel" → "or crashes Excel" on slide 2, and "pooled classes" spelled
out on slide 9.

### Presenting

**Liping: 2–5. Lichen: 6–9.** Two things worth a word between you beforehand:

- **Slide 3's changed word** — she wrote it and may be asked about it.
- **Slide 7's last three rows — settled.** She asked for them in the bar and they are in it.
  The one thing to carry into the room: no project document scopes futures and options yet, and
  the repo's own coverage table still lists them out of scope. If an investor asks whether
  derivatives are committed work, the honest answer is that they are counted as remaining rather
  than written off, and no design exists for them. Worth one sentence to Mario afterwards, so
  the deck and the project record say the same thing.

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

| number | source |
|---|---|
| 2,366 lines · per-category line counts | the workbook's `Summary` sheet, `Grand Total` row 61 |
| 2,260 securities · per-category security counts | the census above |
| 766 priced · 183 named-and-excluded | the census above; reasons in `outputs/corporate_disposition_2009-03-31.csv` |
| 40 seconds on Azure | measured 2026-09-16, all four drivers, free tier |
| ~14,000 lines of VBA | both legacy workbooks, counted during the EIR search |
| Japan 0.00% · UK 0.04% | `sovereign_risk_2009-03-31.csv`, median of own-curve anchors, under-one-year excluded (11 and 12 bonds) |
| four of five within 0.75 years | `phase2_risk_2009-03-31.csv`, model duration vs the custodian's, the five callable agencies |
| six parts in a million | `tests/test_inflation_data.py` |
