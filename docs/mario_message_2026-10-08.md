# Replying to Mario's coupon files — 2026-10-08

> ⚠️⚠️ **SUPERSEDED 2026-10-14, and one sentence in it is FALSE.** Three further pulls arrived
> (`data/mtge.xlsx`, `corp.xlsx`, `index.xlsx`) and settled what this message got wrong: the
> clause *"the formulas in the big file also came through with the rows out of step, a fixed 6.5%
> Fannie pool sitting next to a LIBOR one"* describes a **row-pitch** problem of our reading, not
> a defect in his export — the field returns a transposed six-row record per security and the
> block was correctly keyed all along (`missing_data.md` G7b, retracted). ⭐ **If this message was
> sent, the next one corrects that clause in a sentence; if it was not, strike it.** The rest of
> the message — the coverage win, our own 40.3% recall, the per-class table, the ask for a monthly
> coupon history — all still stands, and the ask is now sharper (see the 2026-10-14 round).

**Channel:** WhatsApp, the same thread his files arrived in. **No attachment** — the ask is a
list of 393 CUSIPs that is a filter of his own file, so it can go as a spreadsheet when he
says yes, not before.

⚠️ **Written in WhatsApp's own markup, not Markdown, and that is deliberate.** WhatsApp renders
`*text*` as **bold** and does not render tables at all — a Markdown table pastes in as a row of
raw pipes. ⭐ A first draft put the per-class figures in a table and a table check did not catch
it, because the check only looks at lines beginning with `|` and these sat inside a blockquote.
The figures are bulleted lines instead. Same lesson as "a .csv is not a spreadsheet": the
container has to match the channel, and a checker that cannot see the container proves nothing.

**What arrived**, 2026-10-07 21:18, after the weekly call: `formulas_for_cpn_pmts.xlsx`,
`Yield  Reference for CPN.xlsx`, `Agencies CPN Data.xlsx`. His note, verbatim:

> "Lichen, the files include the coupon formulas to all the MBS, ABS, CMOs, Non GOV CMOs and
> the second file the Reference index that is used in the CPN Formula, and the third file is
> the Agencies file, Foruntatelly, they are all Fixed or Zeros, and no FRN or variables, so
> easy to do.... Good luck. Mario & Lipping"

⚠️ **The message has three jobs that pull against each other** — thank him for data that
closed a real gap, correct a sentence in his note, and ask for more. The order below is
deliberate: **what it bought → what we did with it → one thing to know → one ask.** His
contribution leads, because it genuinely was one: our own detection of moving coupons scored
40% against his column.

---

## The message

> Hi Mario, Liping — thank you, this was the one input we couldn't produce ourselves.
>
> *What it closed.* The custodian file gives each holding's coupon rate but never says whether
> that rate moves, and that one fact decides whether a security's duration is its full remaining
> life or close to zero. Your first file answers it for all 1,333 securitised and agency
> holdings — and it replaced guesswork rather than refining it. We'd been inferring it from the
> security descriptions; scored against your answer on the 751 we had looked at that way, we'd
> caught 129 of the 320 that really move — about two thirds of the agency pools, about a quarter
> of the private-label deals. A deal name doesn't say: "2007-OA4" is an option ARM with the word
> nowhere in it.
>
> *One thing to flag.* Your note said all fixed or zeros, no FRNs or variables. That's exactly
> right for the Agencies file — 36 fixed, 2 zeros. The big file reads differently, and most so
> where we haven't started:
>
> • Asset Backed — 43 of 79 not fixed-rate (54%)
> • Non-Government CMOs — 129 of 264 (49%)
> • Commercial Mortgage-Backed — 29 of 69 (42%)
> • Government MBS — 192 of 882 (22%)
> • Agencies — none of 39, as you said
>
> *What we did with it.* Of the 882 Government MBS we value, 192 aren't fixed-rate. The
> valuations are unaffected — the coupon level we use is the custodian's own at 31 March 2009,
> checked three ways before we trusted it over the one in your file. What a fixed coupon
> assumes is that the level *stays*, so the 132 carrying a published duration are now marked as
> resting on that. Where we see principal repaying month by month only the interest moves with
> the coupon — about a sixth of the value — so the error is bounded near 1.8 years, against 21
> for treating these as bullets. That's why we valued them rather than waited. For 61 of the 132
> we don't have the measured principal either, so the bound doesn't apply and those say so.
>
> *What we still need.* For the 393 holdings whose coupon moves: what the coupon actually *was*,
> month by month since 2009 — the same shape and the same 211 months as the factor history. The
> list is your own file filtered, so nothing needs looking up.
>
> Why that rather than the formulas: the same reason the factor history worked. A coupon history
> records what the formula, the index, the reset lag and the rate caps all did, so we model none
> of them — and the caps are the part a formula can't give us. The formulas in the big file also
> came through with the rows out of step, a fixed 6.5% Fannie pool sitting next to a LIBOR one.
>
> Thanks again — the second file is already useful on its own, one-month LIBOR at 31 March 2009
> reading 0.50063%, exactly the reset we'd need.

---

## Why it is shaped this way

**The correction is framed as attribution, not error.** His sentence is *true of the file he
names last*: `Agencies CPN Data.xlsx` really is 36 fixed and 2 zeros over 42 rows, and file
one's own agency rows are 41-of-42 `#N/A Invalid Security`, which is presumably why a separate
agencies file exists. He almost certainly wrote that line looking at the agencies file. Saying
"that's right for the Agencies file, the big one reads differently" costs nothing and is what
actually happened.

**Our 40% leads the correction.** ⭐ It is the strongest thing in the message and it is true:
the data did not refine an estimate, it replaced a method. Putting our own miss before his
makes the correction land as information rather than as a complaint, and it is the honest
ordering anyway — his column is only valuable *because* our inference was poor.

⭐ **The split (two thirds / a quarter) is better than the flat 40%, and it is planning
information he does not have.** Measured over the 751 securities the earlier request covered,
376 Government MBS with a factor history in hand plus 375 of the CMO/CMBS/ABS: of the 320 that
really move, we caught 79 of 125 in Government MBS and 50 of 195 in the private-label classes.
The heuristic fails hardest exactly where he has not started.

**The per-class table is the one number block included.** It tells him the un-started
categories are roughly half floating, which changes what Phase 2 costs there. Everything else
in the message is prose because he reads it on a phone.

**One ask, sized against a precedent.** 393 securities x 211 months = 82,923 values, against
the September pull that returned complete at 79,336. ⭐ And every one of the 393 has a CUSIP,
because the list is his own CUSIP-keyed file filtered — so unlike the 2026-10-02 pack there is
no "375 of 412" caveat to disclose.

---

## Deliberately NOT in the message

**① The factor history for the 412.** Still the larger outstanding ask, and still untouched by
what arrived. ⚠️ Bundling it here would make this a shopping list and would bury the coupon
question that the message exists to close. It goes separately, after this is answered.

**② A request to re-export the formulas.** The misalignment is mentioned in one clause, as a
*reason the history is the better ask* — not as a second request. We showed the formula route
needs four further things we do not have (the index histories, the reset convention, the
lookback, and the caps), so asking for it would be asking for the weaker input. If he offers,
fine.

**③ The proof that the formula block is mis-keyed.** The below-chance control — 38.2% observed
against 56.2% for a random value, because the index holds 297 monthly points across 6.7
percentage points — is the evidence, and it is engineering. One example he can see for himself
(a fixed 6.5% pool beside a LIBOR formula) does the same job in a clause.

**④ Anything about who is at a terminal.** ⚠️ Our record says Liping was not expected back at
one for some time (2026-10-01); his message is signed by both of them. That is new information
and it may mean the record is stale, but it is not something to raise with him. Addressed to
both, as he signed.

**⑤ The stale coupon column.** His file's `Coupon` is the valuation-date rate for a fixed
security and is not for a floater. We simply do not use it, and the message says so only as
"we checked that three ways before trusting it over the one in your file" — enough that he
knows, without turning a non-issue into a defect report.

---

## Two claims walked back in drafting

**① "Ask him to re-export the formula block keyed to CUSIP" was the wrong primary ask**, and it
was in the previous day's plan. Working through what a formula actually needs — index history,
reset convention, lookback, periodic and lifetime caps — showed it is the *weaker* of the two
routes, and that the argument for the history is the one that already won for the factor
extraction. The formula demotes to a clause.

**② The worry that 128 of the 192 might carry a wrong coupon LEVEL resolved cleanly.** The
concern was that the securities outside the 505 already-priced pools might have been built on
a stale rate. They are not: the driver reads the same custodian column for all 882, and a
third source settles which column is right — the custodian's own description embeds the rate
and agrees with the master on 48 floating rows and with Bloomberg's file on none. So the
exposure is uniform and is an assumption, not an error. ⭐ Worth recording because the wrong
answer would have meant re-pricing 192 securities instead of marking 132.
