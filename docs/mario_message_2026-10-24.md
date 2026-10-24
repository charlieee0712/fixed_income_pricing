# Reply to Mario's 2026-10-23 delivery — and it REPLACES three unsent drafts

**Channel:** WhatsApp, the thread the three files arrived in.
**Attachment:** `docs/bloomberg_37_request_2026-10-24.xlsx` — the 41 securities still
outstanding, 37 of them one keying case.

⚠️ **WhatsApp markup, not Markdown:** `*text*` renders as bold there and **tables do not
render at all**, so every number is a sentence or a bulleted line.

---

## ⚠️⚠️ Why this is ONE message and not a fourth

Three drafts are on file and **none was sent**:

| draft | words | status now |
|---|---:|---|
| `mario_message_2026-10-14.md` | 730 | the win and the ARM finding never reached him; its six-index ask is **half answered** |
| `mario_message_2026-10-14_412.md` | 348 | ⚠️ **obsolete** — it asks for the 412 factor history, which he has now sent |
| `mario_message_2026-10-16.md` | 738 | two of its three answers still live; the third is now **confirmed by what he chose to send** |

⭐ A fourth on top of three would be the opposite of efficient. This one carries forward
everything still live, drops what the delivery has overtaken, and is the only thing to send.
It is shorter than the three it replaces put together by about half.

⭐⭐ **And one paragraph had to be deleted rather than carried.** The 10-16 draft opens its
third answer with *"here I owe you a correction, because what I sent last week was put more
strongly than the facts support"* — referring to the claim in the 412 message that a balance
without a coupon cannot build a cash flow. **That message was never sent, so the claim never
reached him.** Apologising for it would hand him a problem he does not have and make him
wonder what he missed. The corrected position is simply stated as our position.

---

## The message

> Hi Mario, Liping — the factor pull came through, and it does the job.
>
> *371 of the 412 came back with full repayment histories* — the non-government CMOs,
> commercial mortgage-backeds and asset-backeds, the last category in the portfolio with
> nothing behind it. They can now be valued the same way the 882 government mortgage holdings
> already are. The histories also reach back to each deal's issue date, which changes nothing
> for March 2009 but roughly doubles the observed history behind any forward-looking
> prepayment work later.
>
> *The files from the 14th paid off too.* Four Japanese bank bonds that had sat at the
> custodian's mark since July now price — Chuo Mitsui and three Resona issues, 920 to 1,130
> basis points, about where distressed bank capital belonged in March 2009. And where we had
> found a margin ourselves from prospectuses, your file agrees to the basis point on all eight.
>
> *One thing to fix, and it's small.* 41 of the 412 came back without a usable history, and 37
> are one cause: the pull was built from the ISIN column, and those 37 have no ISIN, so the
> ticker came out as NULL. The list I sent has a ready-made ticker in its first column — CUSIP
> followed by "Mtge" — for all 412; re-running those 37 off that column closes it. Attached are
> all 41 with what happened to each. The other four are separate cases and three may not be
> retrievable at all.
>
> *Two indices you can stop worrying about.* RFUCCT1Y and RFUCCT6M — you said they aren't on
> Bloomberg and suggested finding something similar. I'd rather not. They affect 43 securities,
> under 2% of the portfolio, and all 43 already price on the coupon you report, so nothing is
> blocked. I did try to identify them by working backwards from those coupons: between the
> series we hold and a plausible range of reset lags there are about 240 combinations, so
> something always lands within a few basis points — which tells you nothing.
>
> *On coupons, we're doing it your way.* Your rule is: coupon moves, no formula, treat it as
> fixed. Measured across the 412, that is already exactly what we do on 320 of them, 78%. One
> thing worth knowing: of the 201 whose coupon moves, *108 have no formula at all*, so your
> fallback is carrying more than half that population rather than a few edge cases.
>
> For the 93 that do have a working formula, we still use the coupon you report, and the
> measurement is why. Run the formulas at 31 March: 85% land within five basis points of your
> own coupon, so the formulas are sound. But 77 of the 93 come out *low*, and the misses aren't
> random — the two COF-11 bonds are both out by exactly 1.130 points, precisely the gap between
> that index's March and December prints, and three 12MTA bonds all by 0.193, the
> March-to-January gap. An identical error on securities sharing nothing but an index points at
> the date the index was read, not the formula; the reset lag isn't in the formula field. One
> inverse floater goes the other way, 4.499% against your 1.980% — a cap.
>
> So at the valuation date your coupon is the observation and the formula is a reconstruction
> of it. We keep the observation. What the formula adds is how the coupon *moved* afterwards,
> which nothing else we hold can tell us.
>
> *One exception, and it's yours to settle.* The other four of that Japanese family — BTMU, a
> second Resona euro issue and the two Shinsei tranches — are in your file too, with the margin
> field empty, so re-pulling won't help. They're the one place we don't follow your rule: each
> switches to a floating coupon one to two years out with about five years to run after, so
> fixing the coupon would assert a rate they don't pay for three quarters of their remaining
> life. Priced your way anyway: 137, 713, 1,133 and 1,315 basis points — each an upper bound,
> because the euro curve implies 2.7% rising to 5.1% across that window before any margin. Say
> the word and they go in with that caveat.
>
> *One thing in your factor data worth knowing.* A factor's month label doesn't always mean the
> month it says. For the agency pools the column marked April is the March balance; for most
> private-label CMOs March means March — and it isn't an asset-class rule either, since two
> CMOs in the same category go opposite ways. The only reliable test is your own holdings file:
> whichever month's factor equals the balance you report is the right one, and we now set it
> per security across 747 of them. It caught three of our own rows reading a month late — the
> spreads moved under a third of a basis point, but those rows had been understating how much
> of their history was actually recorded. Anyone else reading these files will hit the same
> thing.
>
> *And your Tier 2 question.* It doesn't simplify Tier 2 so much as remove the need for it at
> this date. *Tier 2 exists to predict how much principal comes back each month; for a March
> 2009 valuation we don't predict it — the trustee published it, and we read it.* On 349 of the
> 373 securities where we hold a path, the whole cash flow from the valuation date to the last
> dollar is recorded fact, a median of 127 monthly observations. What it saves against the full
> structural route is the waterfall: a slice's factor *is* the waterfall's output — roughly 170
> deal models for the government book alone, replaced by two subtractions a month. The limit,
> plainly: it only works backwards. At today's date you'd have history up to now and an unknown
> future, which is what Tier 2 is for — so this isn't a substitute for Tier 2, it's Tier 2's
> input, which your own slide already lists as the existing engineering work.
>
> Next from us: pricing the 412 the way the 882 are priced.

---

## Why it is shaped this way

**The order is: what it bought → the one action → how we're handling it and why → what we
found → the question you asked.** The single thing Mario has to *do* sits third — early enough
not to be buried, late enough that he knows why it matters. Everything after it is information
he can read or skip without missing an instruction.

⭐ **The ask is framed as a keying accident, not a failure.** It is one: our file shipped a
usable ticker for all 412 and the pull used a different column. Saying so plainly, with the fix
in the same sentence, makes the re-run a thirty-second job. ⚠️ The other four outstanding
securities are named as *separate cases* rather than folded into "41", because a reader who
sees one heading assumes one cause — and three of them probably cannot be retrieved at all.

⭐⭐ **"Two indices you can stop worrying about" may be the most useful paragraph in it.** He
asked us to find substitutes. Telling him not to bother *and showing the work that says so*
saves his time, keeps a wrong number out of the model, and demonstrates the standard we hold
our own shortcuts to. The 240-combination line is the whole argument in one clause.

**The coupon section answers his call question with a measurement, not a position.** He asked
why we wanted the coupon history when the formulas exist, then answered it himself by sending
factor data and no coupon data. So the message agrees with him first (320 of 412 already
treated his way), gives him a fact he does not have (108 of the 201 have no formula at all),
and only then explains the 93. ⭐ Two bonds out by *the same amount to three decimals* is an
argument nobody can wave away.

**The exception is put as a decision with the numbers already computed.** A refusal resting on
a number nobody computed is an opinion, so all four spreads are quoted together with the reason
they are an upper bound rather than a guess. He can say yes in one word.

⭐ **The month-label finding is included although the error was ours.** His own team will read
those files and hit it; it shows we check his data against his holdings file rather than
trusting it; and it reports our own error proportionately in the same breath — under a third of
a basis point, with the real defect named as provenance rather than dressed up or buried.

**The Tier 2 answer stays because he asked it and never got a reply**, and the middle sentence
is written to be liftable straight into his deck.

⚠️ **One number was wrong until the self-review.** The draft said *86%* land within five basis
points, carried from the 10-16 draft where the denominator was 92. It is **79 of 93 = 85%**.
Same lesson as every other count in this project: re-read it from the run, never from the
previous document.

---

## Deliberately NOT in the message

**① The 412 factor-history ask.** Delivered. The entire 10-14 second message is obsolete.

**② An apology for the "balance with no coupon" claim.** It was in an unsent draft and never
reached him. Correcting it would invent a problem.

**③ The ARM-specific version of the reset-lag finding.** The 10-14 draft argued it from the 17
testable agency ARM pools. The 10-16 measurement on the 201 is the same finding on the
population he actually asked about, so the weaker, borrowed version is dropped rather than
stacked on top of it.

**④ The reset anniversaries and the periodic and lifetime caps.** They were the second bullet
of the 10-14 ask. ⚠️ They now belong to a question we are not asking this round: they matter
only for projecting a coupon *path*, and the message has just argued that the valuation-date
coupon comes from his holdings file. Asking for them here would contradict the paragraph above
them.

**⑤ Our own 40.3% floater-detection recall, the 132 disclosed durations, and the per-class
non-fixed shares.** Internal bookkeeping that earns no decision he has to make.

**⑥ Anything about who is at a terminal.** He signs "Mario & Lipping"; we address both and say
nothing about availability.

**⑦ The live-date question** — at what date and for what purpose the tool goes live,
revaluation or scenario risk. ⚠️ It is real and still not raised. It belongs in its own message,
because the answer changes how large the next phase is, and this one is already answering a
question of his.
