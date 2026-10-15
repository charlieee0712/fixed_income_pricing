# Replying to Mario's coupon formulas — 2026-10-14

**Channel:** WhatsApp, the thread the three files arrived in. **No attachment** — the ask is six
index names and a choice, which fit in the message.

⚠️ **Written in WhatsApp's own markup, not Markdown:** `*text*` renders as bold there and tables
do not render at all, so the numbers are bulleted lines. (Same lesson as "a .csv is not a
spreadsheet": the container has to match the channel.)

⚠️⚠️ **`docs/mario_message_2026-10-08.md` was NEVER SENT** (confirmed by the user, 2026-10-14),
and that changes this message in two directions:

* ⭐ **Its central correction is now moot.** It was built around "your note said all fixed or
  zeros; a third of the securitised book is not." Mario's own 2026-10-14 instruction opens
  *"And now for floating, variable etc."* — **he is already there.** Restating it would
  relitigate something he has moved past, so it is gone, and the per-class shares survive only
  as planning information folded into the last line.
* ⚠️ **But the 412 CMO/CMBS/ABS factor-history ask has therefore never reached him**, and it is
  the largest outstanding gap in the project. He has just invited the Tier-2 ask, so it is
  NAMED here in one line and sent separately rather than crowding this.

⭐ Nothing needs correcting to him: the false clause ("the rows out of step") never left the
building. We do not mention the misreading at all — it would introduce a problem he never had.

---

## The message

> Hi Mario, Liping — the corporate file did something I wasn't expecting. Thank you.
>
> *Four bonds now price that couldn't before.* Chuo Mitsui and three Resona issues were all
> sitting at the custodian's mark, because no public source states what their coupon becomes
> after the call date. Your file has it. They come out between 920 and
> 1,130 basis points of implied spread, which is about where distressed Japanese bank capital
> belonged in March 2009. One of the four we had down as "all terms unknown" — it came back
> identical to its sister tranche, which also confirms the two are one issue in two wrappers.
>
> *It also checked our earlier work.* Where we'd had to find a margin ourselves from
> prospectuses, your file agrees to the basis point on all eight — Allstate, Lincoln, Chubb,
> AmEx, GE, Bank of America, BNP, UniCredit — with the same switch dates. Good to know that
> approach holds up.
>
> *The formulas are in the code now*, as dated rules — one bond, several periods, each with its
> own start date, index and margin, exactly the shape you described.
>
> *One thing they can't do, and it's worth knowing.* For the agency ARM pools, working the
> formula out at 31 March 2009 gives a coupon one to three points *below* what the custodian
> reports — all seventeen we can currently test, every one the same direction. It's the reset:
> these pools reset annually on their own anniversary, so in March 2009 one carries a rate set
> the previous June near 2.4% and another set in December nearer 0.5%. The one-year Treasury
> moved about two and a half points across that window, which is almost exactly the range of
> the gaps we see. The formula is right; it just can't tell us which date to use. A few are
> also leveraged — one reads 2370 × LIBOR − 15405%, which plainly needs its cap and floor to
> mean anything.
>
> So for those pools we're staying with the custodian's own coupon, which is the actual rate
> after caps and resets — the better input, not a workaround.
>
> *What would help, smallest first:*
>
> • Six index histories the formulas reference but the index file doesn't carry — *RFUCCT1Y,
> RFUCCT6M, US0012M, EUR003M, US0006M, H15T5Y*. The first two alone block 42 of the 60 ARM
> pools; we can't even test those.
>
> • For the ARMs, the reset anniversary and the periodic and lifetime caps, if the terminal
> gives them.
>
> • Or instead of both — the *realised monthly coupon* for the 192 pools in the government
> mortgage book that aren't fixed-rate, 2009 onward. Same shape as the factor history, and it
> makes the other two unnecessary, because it records what the formula, the index and the caps
> all actually did.
>
> One note so you don't spend time on it: four margins are still missing — BTMU, a Resona euro
> issue, the two Shinsei tranches — and all four *are* in the file; the formula field just comes
> back empty. Re-pulling it won't help.
>
> Behind this there's a larger one: the 412 CMOs, CMBS and asset-backeds still have no repayment
> history at all, and about half have moving coupons — worth knowing before that gets scoped.
> I'll send it separately.

---

## Why it is shaped this way

**It replies to what he asked, rather than catching him up.** He gave an instruction (turn the
formulas into Python) and three files. The message reports the result, says what the formulas
cannot do and why, and makes one ask. ⭐ Four jobs, in the order a reader can act on.

**The win leads, and it is genuinely his.** Four bonds that were held at the custodian's mark
since 2026-07-20 now carry a spread, and the fourth had been recorded at LOW confidence with
*all* terms unresolved. That is the strongest possible opening and it costs no exaggeration.

⭐ **The eight confirmations are in because of what they say about method, not about the
bonds.** Mario's standing view (2026-07-30) is that web-sourced terms are "fine as INTERIM but
not as precise as bloomberg". Eight of eight agreeing to the basis point, with matching switch
dates, tells him the interim channel is sound — which affects how he scopes every future gap.

**The ARM finding is stated as a property of ARMs, not as a problem with his data.** It is: the
formula is correct, the missing thing is which date to evaluate it on. ⚠️ Saying it any other
way would read as "your method doesn't work", and his method *did* work — it closed G3.

⭐ **`2370 × LIBOR − 15405%` is quoted verbatim** because one real example does the work of a
paragraph, and he will recognise a leveraged inverse floater instantly.

⚠️⚠️ **A DEFECT IN THE ASK, caught on review and corrected.** The third bullet first read
**"the realised monthly coupon for the 393 that aren't fixed-rate"**. Measured: of those 393,
**192 are in the government mortgage book — which we price — and 201 are in the 412
CMO/CMBS/ABS, which we price none of**, because they have no factor history and none has ever
been requested. ⭐ A coupon without a balance builds no cash flow, so half of that request would
have arrived unusable, and it invites the obvious question of why we want coupons for bonds we
cannot price. **Scoped to 192.** The 412 need *both* series and they go in their own message —
see below.

**The ask is ordered smallest-first and ends with the option that replaces the other two.** The
six index series are small, definite and block 42 of 60 pools. The reset dates and caps may not
be terminal fields at all. The realised coupon history is the one that closes everything —
⭐ and it is the same argument that already won for the factor extraction, so it is framed as a
choice for him rather than as a rejection of the formulas.

**The four empty-field margins are flagged to save him a wasted pull.** They are *in* the file
with the field blank, which is a different fact from "absent" and implies a different remedy.

---

## Deliberately NOT in the message

**① The "all fixed or zeros" correction.** Moot — his own 2026-10-14 wording already treats
floating and variable as the live case. Restating it would be pedantic and would spend the
opening paragraph on something settled.

**② Our 40.3% recall, and the 132 disclosed durations.** Both were written for the unsent 10-08
message. ⭐ The recall figure earned an ask that this message no longer needs to earn — his file
already arrived. The 132 disclosures are internal bookkeeping about a bound he has not
questioned. Keeping them would double the length for no decision he has to make.
⚠️ The per-class shares survive, compressed to one clause ("about half of them have moving
coupons") on the 412 line, where they are planning information rather than a correction.

**③ Anything about the first file being hard to read.** It was not: the block was correctly
keyed and we misread its row pitch. ⭐ Telling him would create a problem he never had, and the
10-08 clause that said so was never sent.

**④ The 412 factor-history pull itself.** Named in one line, sent separately. ⚠️ This is the
largest outstanding gap in the project and it has NEVER been put to him — the 2026-10-02 pack
that carried it was never sent either.

⭐ **Separate, and the reason is that it is a different DECISION for him, not just a different
population.** This message asks him to finish a book that is already running; that one asks him
to open a class we have not started. He can reasonably say yes to one and defer the other, and
bundling forces a single answer on unequal things. It also needs room of its own: **412
securities** (not 375 — see below), **two** series rather than one, about **129,000** values,
and the 18.2%-by-count against 4.8%-by-par framing.

⭐⭐ **And the caveat that pack had to carry is GONE, because of his own files.** The 2026-10-02
pack could write only **375** request lines; **37 of the 412 carried no ISIN or CUSIP in the
custodian file**, which the README and message had to disclose because "375 ≠ 412 is the first
thing a careful reader notices". Measured 2026-10-14: **all 37 now have a well-formed CUSIP**,
supplied by `data/mtge.xlsx`, none malformed. ⇒ **the ask is 412 of 412 with nothing to
apologise for** — a second, unplanned payoff from the pull he already ran.

**⑤ Anything about who is at a terminal.** He signed both messages "Mario & Lipping"; we address
both and say nothing about availability.

---

## One thing for us, not for him

⚠️ **Mario's own exception rule and our treatment diverge on exactly four securities.** He said:
*"if floating/variable bonds, but with no formula, treated them as fixed, because no data."*
The mortgage book already complies — the custodian's coupon is held constant and the row says
so. But the four remaining corporate hybrids are BT-marked instead, and applying his rule would
fix a perpetual's coupon at 3.5–3.75% forever on a bond priced at 40–52, which would produce a
wild spread. ⭐ That is his call, not ours; it is not in this message because it needs a
conversation rather than a line, and because nothing is blocked while it waits.
