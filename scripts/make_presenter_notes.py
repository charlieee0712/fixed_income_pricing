"""Build the presenter's Word document for slides 6-10 of the investor deck.

Two things in one file:

  * the WALKTHROUGH -- what each slide means, what every number on it is, and the finance
    concept underneath it, written for someone who has to understand it rather than
    recognise it. This exists because the presenter said twice that he could no longer
    follow his own bullets.
  * the SCRIPT -- the actual words, because that is what gets said in the room.

Every figure was read from a live run on 2026-09-22, not from memory, and the last page
lists the sources. Regenerate with:

    python scripts/make_presenter_notes.py --output "docs/Presenter Notes v6.docx"

Needs ``python-docx``. Like ``make_investor_deck.py`` and ``md_to_pdf.py`` this is document
tooling, so it is deliberately NOT in requirements.txt.
"""
from __future__ import annotations

import argparse
import pathlib

from docx import Document
from docx.shared import Inches, Pt, RGBColor

INK = RGBColor(0x1F, 0x4E, 0x79)      # headings
SAY = RGBColor(0x0B, 0x3D, 0x62)      # the words actually spoken
WARN = RGBColor(0xA6, 0x3A, 0x00)     # things that would cost you if said wrong
QUIET = RGBColor(0x5A, 0x5A, 0x5A)


def _p(doc, text="", size=10.5, colour=None, bold=False, italic=False,
       indent=0.0, before=2, after=4):
    """One paragraph. ``**bold**`` inside the text becomes bold runs."""
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Inches(indent)
    para.paragraph_format.space_before = Pt(before)
    para.paragraph_format.space_after = Pt(after)
    for i, chunk in enumerate(str(text).split("**")):
        if chunk:
            run = para.add_run(chunk)
            run.font.size = Pt(size)
            run.font.bold = bold or (i % 2 == 1)
            run.font.italic = italic
            run.font.name = "Calibri"
            if colour is not None:
                run.font.color.rgb = colour
    return para


def h1(doc, text):
    doc.add_page_break()
    _p(doc, text, 18, INK, bold=True, before=0, after=10)


def h2(doc, text):
    _p(doc, text, 13.5, INK, bold=True, before=14, after=5)


def h3(doc, text):
    _p(doc, text, 11.5, INK, bold=True, before=10, after=3)


def body(doc, text, indent=0.0):
    _p(doc, text, 10.5, None, indent=indent)


def bullet(doc, text, indent=0.25):
    _p(doc, "•  " + text, 10.5, None, indent=indent, before=1, after=3)


def say(doc, text):
    """A line to be spoken aloud, set apart so it is findable while standing up."""
    _p(doc, text, 11.5, SAY, indent=0.28, before=5, after=5)


def warn(doc, text):
    _p(doc, "⚠  " + text, 10, WARN, indent=0.1, before=5, after=5)


def star(doc, text):
    _p(doc, "⭐  " + text, 10.5, None, indent=0.1, before=5, after=5)


def table(doc, rows, widths=None, header=True):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    for r_i, row in enumerate(rows):
        cells = t.add_row().cells
        for c_i, val in enumerate(row):
            cells[c_i].text = ""
            para = cells[c_i].paragraphs[0]
            para.paragraph_format.space_before = Pt(2)
            para.paragraph_format.space_after = Pt(2)
            for i, chunk in enumerate(str(val).split("**")):
                if chunk:
                    run = para.add_run(chunk)
                    run.font.size = Pt(9.5)
                    run.font.name = "Calibri"
                    run.font.bold = (header and r_i == 0) or (i % 2 == 1)
                    if header and r_i == 0:
                        run.font.color.rgb = INK
    if widths:
        for row in t.rows:
            for c_i, w in enumerate(widths):
                row.cells[c_i].width = Inches(w)
    _p(doc, "", 4, after=0)
    return t


# ----------------------------------------------------------------------------------------

def build(out: pathlib.Path) -> pathlib.Path:
    doc = Document()
    s = doc.sections[0]
    s.left_margin = s.right_margin = Inches(0.85)
    s.top_margin = s.bottom_margin = Inches(0.75)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    # ---------------------------------------------------------------- cover
    _p(doc, "Investor update — the slides you present", 22, INK, bold=True,
       before=0, after=2)
    _p(doc, "Slides 6–10: walkthrough, script, and the questions to expect",
       14, QUIET, after=12)
    table(doc, [
        ["Occasion", "Ryse project progress update · the investors, at Goldman Sachs"],
        ["Split", "Liping presents slides 2–5. You present **6–10**, the last being the two bios."],
        ["Your time", "About **9 minutes**, then questions"],
        ["The deck", "docs/Ryse Presentation v6.pptx"],
        ["Numbers", "All re-measured from a live run on 22 September. Sources on the last page."],
    ], widths=[1.1, 5.7], header=False)

    h2(doc, "How to use this")
    bullet(doc, "**Part 1, the walkthrough** — read tonight. Every number on every slide, "
                "and the finance underneath it, so you can say it without the script.")
    bullet(doc, "**Part 2, the script** — read tomorrow. **The indented blue lines are the "
                "words you say.** Black text is a note to you; don't read it out.")
    bullet(doc, "**Part 3, questions** — what this audience will actually ask, including "
                "the one sharp question.")
    bullet(doc, "**Part 4** — three true stories, for when somebody asks what was hard.")
    bullet(doc, "**Part 5** — a one-page number sheet you can print and hold.")

    warn(doc, "**One thing to confirm before you present: has Liping's mortgage data actually "
              "arrived?** The script says only \"that was requested in July\", which is a "
              "fact either way. **Do not add \"and it is still outstanding\"** unless you have "
              "checked — if it turns out the data landed weeks ago, that one clause costs "
              "you the credibility of everything else on the slides.")

    # ---------------------------------------------------------------- concepts
    h1(doc, "0 · Eight words, and one idea that matters more than all of them")
    body(doc, "These eight carry every slide you present. Once they are solid, everything "
              "else in this document follows.")

    table(doc, [
        ["Term", "In plain words"],
        ["**Bond**",
         "An IOU. The issuer borrows, pays interest (the coupon) on a schedule, and repays "
         "the principal at maturity. Quoted per **100**, so a price of 90 means 90 cents on "
         "the dollar."],
        ["**Yield curve**",
         "What a government pays to borrow, at each length of time (1 year 0.5%, 10 years "
         "3%, and so on). It is the baseline everything else is measured against."],
        ["**Spread**",
         "⭐ The core idea. How much more the market demands from this borrower than from "
         "its own government. Measured in basis points — 1 bp = 0.01%. "
         "**This is the main thing our system produces.**"],
        ["**Duration**",
         "How much the price moves when rates move. Duration 5 means: rates up 1%, price "
         "down about 5%. Confusingly, it is measured in years."],
        ["**Custodian**",
         "The bank that holds the securities for the pension fund and keeps the official "
         "records. It computes its own figures too — that is the second check on slide 8."],
        ["**Callable bond**",
         "The issuer may repay early. Hard to price, because you have to value that right to "
         "repay, which needs an interest-rate tree rather than a formula."],
        ["**Inflation-linked bond** (TIPS)",
         "The principal is adjusted for inflation since issue. That adjustment factor is the "
         "**index ratio** — the thing the third check on slide 8 rebuilds from scratch."],
        ["**Pooled products** (MBS / CMO / ABS / CMBS)",
         "Many loans bundled into one security. Home loans bundled = MBS; that bundle sliced "
         "into risk tranches = CMO; car and card loans = ABS; commercial property = CMBS. "
         "The hard part is that borrowers can repay early, so you need a prepayment model."],
    ], widths=[1.6, 5.2])

    h3(doc, "⭐ The one idea: how the system actually runs")
    body(doc, "Three inputs go in: (a) the bond's terms, (b) that day's government rate "
              "curve, and (c) **the price the custodian recorded**. We then solve for the "
              "spread that makes our model reproduce that price, and compute the risk "
              "figures on the calibrated model.")
    star(doc, "So: **the price is an input, not an output.** That single sentence is why "
              "slide 8 exists, and it is the answer to the sharpest question you may be "
              "asked. Be able to say it without thinking.")

    # ---------------------------------------------------------------- Liping's half
    h1(doc, "0.5 · Liping's half, in five lines")
    body(doc, "You present 6–10, but questions do not respect slide boundaries. This is "
              "enough to field one about her half and hand it back to her gracefully.")
    table(doc, [
        ["Slide", "Her point", "The number in it"],
        ["2 · Situation",
         "Pricing today rests on years of accumulated VBA across workbooks only its owner "
         "can run or change. Scenario analysis is not slow — it is out of reach. And a "
         "spreadsheet cannot be tested.",
         "**~14,000 lines** of VBA"],
        ["3 · Goal",
         "One system for every instrument class; reproducible and testable; cloud parallel "
         "execution puts a thousand-scenario what-if back in reach; portfolio risk on top of "
         "that.",
         "—"],
        ["4 · Current stage",
         "Six of thirteen categories done. Inputs and outputs are JSON dictionaries, which is "
         "what makes parallel execution straightforward. The code already runs unchanged on "
         "Azure.",
         "**949** securities, **766** priced; the whole book in **40 seconds**"],
        ["5 · What it does today",
         "Given a bond, the day's rates and the market price, it returns the spread and the "
         "rate sensitivity. Three ways to run it — spreadsheet, command line, or a service "
         "— same answer from all three. Reproducible to the byte.",
         "Built against a real pension book, **March 2009**"],
    ], widths=[1.15, 4.0, 1.65])
    warn(doc, "If asked how long the **old** tool takes: **nobody has measured it.** Say that. "
              "Liping and Mario know the current workflow; we never timed it, and pairing a "
              "guess with our 40 seconds to claim a speed-up is exactly the kind of number "
              "that gets checked later.")

    # ================================================================ PART 1
    h1(doc, "1 · Walkthrough, slide by slide")

    # ---- slide 6
    h2(doc, "Slide 6 — Coverage")
    body(doc, "**In one sentence:** the book holds 2,260 securities; the six categories "
              "covering 949 of them are finished, 882 have their engine built and are waiting "
              "on data, and 429 have not been started.")

    h3(doc, "The bar on screen")
    table(doc, [
        ["Colour", "Label", "Count", "What it is"],
        ["Dark blue", "Complete", "**949**",
         "Six bond categories. Engine built and running."],
        ["Orange", "Engine built — next", "**882**",
         "The government mortgage book. Built and tested; what it lacks is data."],
        ["Grey", "Not yet built", "**429**",
         "412 pooled products + 16 futures and options + 1 fund unit"],
    ], widths=[0.8, 1.7, 0.7, 3.6])

    h3(doc, "What the two bullets are saying")
    bullet(doc, "**\"Six of the thirteen categories are complete — 42%\"** — that is "
                "949 ÷ 2,260 = 42.0%.")
    bullet(doc, "**\"Of those 949, 766 carry our own price; the remaining 183 are "
                "individually named\"** — this is the line most easily misread, and it is "
                "worth getting right.")

    star(doc, "**\"Complete\" does not mean every bond has a number.** It means the category's "
              "engine is built and running. 183 of the 949 have no price from us — and not "
              "because we cannot compute one, but because **their terms are absent from the "
              "source records we were given**.")
    body(doc, "Present that as a design decision, not an apology. A tool meant to be pointed "
              "at any portfolio **has to be able to say what it cannot price, rather than "
              "guess**. Every one of the 183 is named in a register with its reason. Real "
              "books have incomplete records; the question is whether the tool admits it.")

    h3(doc, "How an investor hears this slide")
    body(doc, "They want to know how far along you are and how much is left. 42% sounds "
              "middling. **The real content is that of the 1,311 securities remaining, 882 "
              "— about two-thirds — are not waiting on us.** That is the sentence to land.")

    # ---- slide 7
    h2(doc, "Slide 7 — The thirteen categories")
    body(doc, "**In one sentence:** the whole book laid out, nothing rolled up, and both "
              "totals reconcile.")

    h3(doc, "Why the two columns differ")
    body(doc, "2,366 **lines** against 2,260 **securities**. One bond held by two managers "
              "appears on two lines; we count it once. **The line count reconciles against "
              "the client's own sheet exactly, at 2,366.**")
    warn(doc, "Say this before anyone asks. Somebody who works with holdings files will spot "
              "two different totals immediately, and explaining it first reads as command of "
              "the data; explaining it second reads as being caught.")

    h3(doc, "What the thirteen categories actually are")
    table(doc, [
        ["#", "Category", "Securities", "In plain words"],
        ["1", "Corporate Bonds", "732", "Companies borrowing"],
        ["2", "Government Bonds", "147", "Sovereign states borrowing"],
        ["3", "Government Agencies", "39", "Quasi-government bodies — Fannie Mae and the like"],
        ["4", "Index-Linked Government", "15", "Government bonds whose principal tracks inflation"],
        ["5", "Guaranteed Fixed Income", "9",
         "Government-guaranteed — these are all FDIC crisis-era guaranteed bank debt"],
        ["6", "Municipal / Provincial", "7", "States, cities and provinces borrowing"],
        ["7", "Government Mortgage-Backed", "**882**",
         "Government-guaranteed home loans, bundled — **the largest block left**"],
        ["8", "Non-Government C.M.O.s", "264", "Mortgage bundles sliced into tranches, no guarantee"],
        ["9", "Asset-Backed Securities", "79", "Car loans, card balances and similar, bundled"],
        ["10", "Commercial Mortgage-Backed", "69", "Commercial property loans, bundled"],
        ["11–12", "FI Derivatives — Futures / Options", "7 / 9",
         "**Not bonds.** They would need machinery we have not designed."],
        ["13", "Other Fixed Income", "1",
         "A fund unit: no ISIN, no maturity, no rating of any kind"],
    ], widths=[0.5, 2.25, 0.8, 3.25])

    h3(doc, "How to handle the last three rows")
    star(doc, "Futures and options count as work **still to do**, not work written off. They "
              "are 16 securities out of 2,260, and they are the only remaining rows that "
              "would need machinery we have not built. The last row is a fund unit — there "
              "is nothing in it for a bond model to price.")
    warn(doc, "**This is the one place where the deck and the project record disagree.** Our "
              "own documentation still lists futures and options as out of scope; the deck "
              "says \"Scoped, not started\", which is Liping's read. If Mario raises it, say "
              "exactly what the slide says: the wording is \"not yet built\", which commits to "
              "nothing.")

    # ---- slide 8
    h2(doc, "Slide 8 — How we know the numbers are right   ⭐ the important one")
    body(doc, "**In one sentence:** our price always matches, because the price is an input "
              "— so we validate against three things that sit **entirely outside** the "
              "system.")

    h3(doc, "The problem this slide solves (say this first)")
    body(doc, "We solve for a spread that makes the model price equal the custodian's price. "
              "That price will therefore always match. **So the price cannot be used as "
              "evidence that the model is right.** You need outside evidence. There are three "
              "pieces of it.")

    h3(doc, "Check 1 — a thermometer has to read zero in ice water")
    bullet(doc, "What we compute is how much more a bond pays than its own government's cost "
                "of borrowing.")
    bullet(doc, "So take a **government's own bond** and price it against **that same "
                "government's curve**, and the answer has to be zero — you are comparing "
                "the thing to itself.")
    bullet(doc, "Japan: 11 bonds, median **+0.02 bp = 0.00%**. "
                "The UK: 12 bonds, **+4.42 bp = 0.04%**.")
    star(doc, "The force of this is that **nothing was tuned to land there**. If the machinery "
              "were wrong, it would not arrive at zero by accident.")

    h3(doc, "Check 2 — somebody else computes the same thing, and we match")
    bullet(doc, "The custodian publishes its own measure of how much each bond moves when "
                "rates move.")
    bullet(doc, "We compute ours from scratch — **without ever looking at theirs**.")
    bullet(doc, "Five callable agency bonds have both figures: **four agree within 0.75 of a "
                "year** (gaps of 0.200, 0.316, 0.633 and 0.741), on durations that themselves "
                "span 1.1 to 9.4 years.")
    warn(doc, "**The fifth differs by 2.2 years.** If asked, say so plainly: all five are "
              "bonds the issuer may repay early, and the two sides treat that right somewhat "
              "differently. Four matching is strong evidence precisely because we never "
              "referred to their figure. **Volunteer this rather than hoping nobody asks** "
              "— offering the weak case unprompted is what makes the strong one credible.")

    h3(doc, "Check 3 — we rebuilt the client's own figures from public data")
    bullet(doc, "An inflation-linked bond's principal is scaled by inflation since issue. "
                "That scale factor is the index ratio.")
    bullet(doc, "We recomputed all **13** of the US ones from **published US government CPI "
                "statistics**, using the **US Treasury's own published rule**.")
    bullet(doc, "They agree to **six parts in a million**.")
    star(doc, "And it turned up something the client did not know: **their factors are struck "
              "one day after the valuation date, not on it.** We found that because on the "
              "valuation date the agreement was ten times worse. That detail carries weight "
              "— it shows the check was real enough to discover a fact, not just confirm "
              "one.")

    # ---- slide 9
    h2(doc, "Slide 9 — What's next")
    body(doc, "**In one sentence:** four things, in dependency order.")
    table(doc, [
        ["", "What", "The point to get right"],
        ["1", "The mortgage book (882)",
         "Engine built and tested. **It needs data, not development.**"],
        ["2", "Three pooled classes (412)",
         "**Genuine remaining engineering — do not dress it up.** What makes it tractable "
         "is that the hard parts (cash-flow machinery, the option model, the market-data "
         "plumbing) are built and proven on the 766 already priced."],
        ["3", "Host it as a service, then run in parallel",
         "⭐ **The easiest thing on this slide to overstate.** Today: each of us runs the "
         "code in our own Azure terminal (measured 16 September, whole book in 40 seconds). "
         "Hosting it so other systems can call it is the **next** step."],
        ["4", "Portfolio risk layer", "Last, once coverage is complete."],
    ], widths=[0.35, 1.9, 4.55])
    warn(doc, "Never let **\"runs on Azure\"** be heard as **\"deployed as a service\"**. The "
              "first is true and measured; the second is not done. This is the single "
              "sentence in your half most likely to be quoted back at you later.")

    # ---- slide 10
    h2(doc, "Slide 10 — The team")
    body(doc, "**In one sentence:** two short biographies, one half each.")
    star(doc, "**This slide earns its place for a reason that is easy to miss: it is the one "
              "that stays on screen for the whole of Q&A.** That is the most-looked-at "
              "stretch of the meeting — people are watching you answer and deciding "
              "whether the name is worth remembering. It is the best real estate in the deck "
              "for exactly what you want out of today, which is why it goes at the end rather "
              "than bolted onto slide 9.")
    bullet(doc, "Liping writes her own half. The deck is built so that she can — both "
                "halves are plain text boxes, the one thing that arrives in Google Slides "
                "fully editable.")
    bullet(doc, "**Mario is not on it.** Slide 1 credits him as directing, and Liping asked "
                "for the two presenters. If he expects a third column that is a two-minute "
                "change — better asked tonight than discovered tomorrow.")
    warn(doc, "**The build refuses to produce a shippable deck while any <<placeholder>> "
              "survives**, and names each one; a draft for circulating is `--draft`. So the "
              "failure this guards against — a blank going up on a screen in front of "
              "the investors — cannot happen quietly.")

    # ================================================================ PART 2
    h1(doc, "2 · The script")
    body(doc, "**Indented blue is what you say.** Black is a note to you — don't read it "
              "out. The timings are counted, not guessed: about 900 spoken words, 6.7 minutes "
              "of pure reading, roughly **8.8 minutes** at presenting pace with pauses. Slide "
              "10 adds about fifteen seconds, because you barely speak over it.")

    h2(doc, "Taking over from Liping (slide 5 → 6)")
    body(doc, "Give the room a map of your half before you start. An audience that knows "
              "where you are going stays with you.")
    say(doc, "Thanks, Liping. Liping has told you what the system does. I'll cover three "
             "things: how much of the portfolio it covers, how we know the numbers are "
             "right, and what's left.")

    h2(doc, "Slide 6 — Coverage · about 2 minutes")
    say(doc, "This is the whole portfolio — two thousand two hundred and sixty securities.")
    say(doc, "The blue block is finished: nine hundred and forty-nine securities, six of the "
             "thirteen categories. That's forty-two percent.")
    say(doc, "The orange block is the mortgage book — eight hundred and eighty-two "
             "securities. I want to be precise about this one, because it's the single "
             "largest block left and it is not blocked on us. The engine for it is built and "
             "tested. What it needs is the terms data, and that was requested in July.")
    warn(doc, "Stop at \"requested in July\". **Do not add \"still outstanding\"** unless you "
              "have confirmed that Liping's mortgage data has not arrived.")
    say(doc, "The grey block is genuine remaining engineering.")
    say(doc, "One honest note on the blue. ‘Complete’ means the category is built and "
             "running — it does not mean every bond in it has our number. Of those nine "
             "hundred and forty-nine, seven hundred and sixty-six carry a price we computed. "
             "The other hundred and eighty-three don't, because their terms aren't in the "
             "records we were given.")
    say(doc, "That's deliberate, and it's worth a sentence. A tool that's going to be pointed "
             "at any portfolio has to be able to say what it cannot price, rather than guess "
             "at it. Every one of those hundred and eighty-three is named in a register, with "
             "its reason.")

    h2(doc, "Slide 7 — The thirteen categories · about 1.5 minutes")
    body(doc, "Do not read the table row by row. Explain the two columns, point at three "
              "blocks, and move on.")
    say(doc, "Here's the same thing with nothing rolled up.")
    say(doc, "Two columns, because they measure different things. The holdings file counts "
             "lines — two thousand three hundred and sixty-six. We count securities — "
             "two thousand two hundred and sixty. The difference is that a bond held by two "
             "managers appears twice. The line count reconciles against the client's own "
             "sheet exactly.")
    say(doc, "The top six are the bond categories, and they're done. Row seven is the "
             "mortgage book. Rows eight to ten are the pooled products — mortgage "
             "obligations, asset-backed, and commercial mortgage-backed.")
    say(doc, "The last three rows are small, and different in kind. The futures and options "
             "aren't bonds — they'd need machinery we haven't designed. They're sixteen "
             "securities out of two thousand two hundred and sixty, and they're counted as "
             "work still to do, not work written off.")

    h2(doc, "Slide 8 — How we know the numbers are right · about 3 minutes  ⭐")
    body(doc, "**This is the centre of your half. Slow down.** Lead with why the slide needs "
              "to exist — that opening is not on the screen, but it is the key to the "
              "whole page, and it defuses the sharpest question before it is asked.")
    say(doc, "This is the slide I'd most like you to take away.")
    say(doc, "Here's the problem it solves. The way this system works is: we take the bond's "
             "terms, the market rates for that day, and the price the custodian recorded — "
             "and we solve for the spread that reproduces that price. Which means the price "
             "always matches. Of course it does. The price is an input.")
    say(doc, "So the price can't tell us the model is right. We need checks that don't use "
             "anything we control. There are three.")
    say(doc, "First — a thermometer has to read zero in ice water. What we compute is what "
             "a bond pays above its own government's cost of borrowing. So take a "
             "government's own bond, and price it against that same government's curve, and "
             "the answer has to be zero — you're comparing the thing to itself. Japan comes "
             "out at zero point zero zero percent. The UK at zero point zero four. We didn't "
             "tune anything to land there; if the machinery were wrong, it wouldn't.")
    say(doc, "Second — somebody else computes some of the same numbers, and ours match. "
             "The custodian, the bank that holds these securities and keeps the official "
             "records, publishes its own measure of how much each bond moves when rates "
             "move. We compute ours from scratch, without looking at theirs. On four of the "
             "five bonds where both figures exist, they agree.")
    say(doc, "Third — we rebuilt the client's own figures from public data. An "
             "inflation-linked bond carries a factor for the inflation since it was issued. "
             "We recomputed all thirteen of the US ones from published government inflation "
             "statistics, using the Treasury's own rule. They match to six parts in a "
             "million.")
    say(doc, "And that third check found something. The client's factors are struck one day "
             "after the valuation date, not on it. Nobody knew that — we found it because "
             "at the valuation date the numbers were ten times worse.")
    say(doc, "So none of the three is us grading our own homework. One is a mathematical "
             "identity, one is somebody else's calculation, and one is public government "
             "data.")

    h2(doc, "Slide 9 — What's next · about 2 minutes")
    say(doc, "Four things, in order.")
    say(doc, "The mortgage book. Engine built and tested — it needs terms data, not "
             "development.")
    say(doc, "The three pooled classes — mortgage obligations, asset-backed, commercial "
             "mortgage-backed. That's genuine remaining engineering and I won't dress it up "
             "as anything else. What makes it tractable is that the hard parts — the "
             "cash-flow machinery, the option model, the market-data plumbing — are already "
             "built and proven on the seven hundred and sixty-six we price today.")
    say(doc, "Third, hosting it as a service and then running it in parallel, with Ryse's "
             "engineer. I want to be precise here. Today each of us runs the code in our own "
             "Azure terminal — that's what the September trial proved, and it reprices the "
             "whole book in forty seconds. Hosting it so that Excel, or another system, can "
             "call it over the network is the next step. It's a defined piece of work rather "
             "than a rewrite, because the system already answers one request at a time, "
             "which is exactly the shape a service wants.")
    say(doc, "And last, the portfolio risk layer — once coverage is complete.")
    say(doc, "That's where we are. Happy to take questions.")

    h2(doc, "Slide 10 — The team · about 15 seconds")
    body(doc, "Advance to it **on** the word \"questions\", not after a pause, so it is "
              "already up when the first hand goes. Then one line, and stop.")
    say(doc, "And that's us. Do get in touch.")
    warn(doc, "**Do not read your own biography aloud.** They can read, it takes longer than "
              "it is worth, and narrating your own credentials is the easiest way there is to "
              "make a good slide awkward. Say the one line and let the room ask something.")

    # ================================================================ PART 3
    h1(doc, "3 · Questions to expect")
    body(doc, "Ordered by likelihood of being asked multiplied by the cost of answering "
              "badly.")

    h2(doc, "Q1  ⭐  \"You calibrate to the custodian's price — so of course your price "
            "matches. How is that validation?\"")
    body(doc, "**The sharpest question in the room, and a real possibility here.** Anyone who "
              "has worked in fixed income sees it immediately. Answering it well is worth "
              "more than the rest of the presentation.")
    say(doc, "You're right that it isn't — and that's exactly why that slide exists. The "
             "price is an input, not an output. What we produce is the spread and the risk "
             "numbers. The three checks are chosen precisely because none of them touches "
             "the calibration: a government bond on its own curve has to give zero by "
             "identity, the rate sensitivity is computed by somebody else, and the inflation "
             "factors come from public CPI data.")

    h2(doc, "Q2  \"Why 2009 data?\"")
    say(doc, "It's the client's own reference case — they chose it because the answers are "
             "already known, so we can be checked against them. It also happens to be the "
             "hardest test available: March 2009 is the crisis trough, when spreads were at "
             "their widest and the market was least well behaved.")

    h2(doc, "Q3  \"Once the mortgage data lands, how long?\"")
    say(doc, "The engine is built against an exact eight-field interface, so when the data "
             "lands it runs — no code change, by design. I'd rather not put a date on the "
             "validation, because that depends on what the data actually looks like.")
    warn(doc, "**Do not commit to a date.** Investors remember dates.")

    h2(doc, "Q4  \"Is it production-ready? Could the client run it tomorrow?\"")
    say(doc, "They can run it today — it runs on Azure from a clean checkout and reproduces "
             "the published results exactly. What's not done is hosting it as a shared "
             "service that other systems call over the network. That's the third item on the "
             "last slide.")

    h2(doc, "Q5  \"Why is the US number forty basis points and not zero, if the zero test "
            "works?\"")
    body(doc, "⭐ **If somebody asks this, there is a real fixed-income person in the "
              "room.** This answer will make them remember you.")
    say(doc, "That's the off-the-run liquidity premium — a real market effect, not model "
             "error. We checked it directly: at the same maturity, the on-the-run ten-year "
             "comes out at about four basis points, while the older off-the-run bond at that "
             "same maturity is at forty-three. Recently issued Treasuries have a median "
             "under three.")

    h2(doc, "Q6  \"How big is the team? How long?\"")
    say(doc, "Two of us, twelve weeks, directed by Mario.")

    h2(doc, "Q7  \"What's the commercial case?\"")
    body(doc, "Liping's territory, but you should be able to carry it for thirty seconds and "
              "hand back.")
    say(doc, "The capability that's missing today isn't speed — it's scenario analysis at "
             "all. Running a thousand what-if scenarios in the spreadsheet isn't practical, "
             "so nobody asks for it. At forty seconds for a full revaluation, a thousand "
             "scenarios becomes a capacity question — and capacity you can buy.")
    warn(doc, "**Do not put a number on how long the old tool takes.** We have never timed "
              "it. \"Isn't practical\" is Liping's and Mario's description of the workflow and "
              "is safe; \"takes days\" is an invention, and Mario could correct you in the "
              "room.")

    h2(doc, "Q8  \"What did you build?\"")
    warn(doc, "**The most important question for your own purposes.** Be specific. Vague "
              "modesty costs you exactly as much as overclaiming. Answer it with one of the "
              "three stories overleaf — a concrete technical judgement lands far harder "
              "than a list of responsibilities.")

    # ================================================================ PART 4
    h1(doc, "4 · Three true stories, for when someone asks what was hard")
    body(doc, "All three are true, and each takes under a minute. Pick by audience: "
              "**A for a quant, B for an engineer, C for anyone.**")

    h2(doc, "A · A measurement that stopped us building the wrong thing   ⭐ first choice")
    body(doc, "Best for this audience: a quantitative insight that prevented wasted work.")
    say(doc, "Mario asked us to make inflation a parameter — per-country assumptions, "
             "sourced ourselves. Before building it, we measured what a constant inflation "
             "assumption actually does. At two percent, every single calibrated spread moved "
             "by exactly the same amount — a hundred and ninety-eight basis points — and "
             "nothing else moved at all. Not the price, not the duration.")
    say(doc, "The reason is that one-plus-pi to the t is exp of t times log one-plus-pi, so a "
             "constant inflation assumption folds straight into the discount exponent. It and "
             "a flat spread are mathematically the same single knob. Twenty-six countries of "
             "constants would have been twenty-six no-ops.")
    say(doc, "So we put the data where it does bite — the index ratio, which scales every "
             "cash flow, and which had never actually been validated. A one percent error "
             "there moves a published breakeven by six basis points.")

    h2(doc, "B · A bond that nothing in the system priced")
    body(doc, "Best for an engineer: silent failure, and who owns a decision.")
    say(doc, "We found a bond that nothing in the system priced. One module sent bonds with a "
             "short call gap to the simple pricer; another took only long gaps. This one had "
             "a ninety-day gap and fell in the hole between them. It wasn't in any output, "
             "any error log, or any report — two files each owned half of one decision, and "
             "neither knew it.")
    say(doc, "And the option value it reported as zero wasn't a small option — the option "
             "had never been evaluated at all. The fix wasn't to make the two numbers agree; "
             "it was to separate the responsibilities, so one place decides whether a bond is "
             "a candidate and another decides whether we can actually represent it.")

    h2(doc, "C · \"The data isn't arbitrage-free\" — the bug was ours")
    body(doc, "Best for anyone: intellectual honesty, and a rule that came out of it.")
    say(doc, "For two months we believed the UK gilt curve data was broken. Our bootstrap "
             "kept refusing it as not arbitrage-free, and we'd asked the client for a "
             "replacement file. It turned out our own loader multiplied every curve file by a "
             "hundred — and two of the twenty-six files were already in percent. So the "
             "gilt curve was arriving with its short end at seventy-three percent and its "
             "thirty-year at four hundred.")
    say(doc, "The error message was real. The conclusion was wrong. We fixed it with an "
             "explicit registry rather than a rule that guesses from the values, because no "
             "threshold separates a half-percent yield from a decimal of zero point five. And "
             "we added a rule to the project: a claimed data gap whose only evidence is your "
             "own error message isn't a data gap yet — reproduce it against the raw file "
             "first.")

    h2(doc, "A few practical notes")
    bullet(doc, "**Your real advantage is explaining a technical system to people who don't "
                "build them.** This presentation is a demonstration of that skill — "
                "**being clear is itself the content.**")
    bullet(doc, "**Say \"I don't know\" when you don't:** \"I don't know — I can find out "
                "and follow up.\" This audience tests for it. **Inventing a number in the "
                "room costs far more than admitting a gap.**")
    bullet(doc, "Default to \"we\", but **when asked directly what you did, be specific**. "
                "Blurry modesty reads no better than overclaiming.")
    bullet(doc, "**Afterwards, pick one person and one concrete topic.** The best possible "
                "follow-up is \"You asked about X — I looked into it, here's the answer.\" "
                "It beats any cold introduction.")
    warn(doc, "Don't raise jobs during the presentation. Today has exactly one objective: "
              "that they leave remembering **this person explained it clearly and their "
              "numbers held up.** Everything else follows from that.")

    # ================================================================ PART 5
    h1(doc, "5 · Number sheet (print this page)")
    table(doc, [
        ["Number", "What it is", "Where it comes from"],
        ["**2,260 / 2,366**", "securities / lines", "the holdings workbook's Summary sheet"],
        ["**949**", "in the six completed categories", "same"],
        ["**42%**", "949 ÷ 2,260", ""],
        ["**766**", "carry a price we computed",
         "555 corporate + 3 callable + 147 sovereign/municipal + 61 agency/guaranteed/linker"],
        ["**183**", "inside completed categories but individually named", "949 − 766"],
        ["**882**", "mortgage book, engine built", "data requested in July"],
        ["**429**", "not yet built", "412 pooled + 16 futures/options + 1 fund unit"],
        ["**0.00% / 0.04%**", "Japan / UK, the zero test",
         "n=11 / n=12; +0.02 bp and +4.42 bp, near-maturity excluded"],
        ["**4 of 5**", "agency durations agreeing with the custodian",
         "within 0.75 y; the fifth differs by 2.2 y"],
        ["**6 in 1,000,000**", "error rebuilding 13 US index ratios",
         "CPI-U NSA via the US Treasury's published rule"],
        ["**40 seconds**", "full revaluation of the book on Azure", "measured 16 September 2026"],
        ["**12 weeks**", "project duration", "26 June – 22 September 2026"],
        ["**+40.6 bp**", "US Treasury median = off-the-run liquidity premium",
         "same maturity: on-the-run +3.9 bp, off-the-run +42.8 bp"],
    ], widths=[1.35, 2.6, 2.85])

    warn(doc, "Every figure here came from a live run on 22 September 2026, and the 766 uses "
              "the same census the deck's own source table uses. If any driver is re-run "
              "before the meeting, check them against `docs/release_facts_<date>.md` rather "
              "than trusting this page.")

    doc.save(str(out))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="docs/Presenter Notes v6.docx")
    args = ap.parse_args()
    out = build(pathlib.Path(args.output))
    print("wrote %s (%s bytes)" % (out, format(out.stat().st_size, ",")))


if __name__ == "__main__":
    main()
