# Asking Mario for one more terminal session — 2026-10-02

**Channel:** WhatsApp. **Attachment:** the folder `docs/bloomberg_request_2026-10-02/`,
self-contained English, forwardable as-is to whoever runs it.

⚠️ **The weekly meeting was cancelled — Mario is too busy this week.** An earlier draft
built the ask around presenting it live, off the back of the 09-30 report's §4.2 promise
("we will know within days whether these 756 securities can be valued without buying deal
models"). That route is gone, and with it the context the meeting would have supplied.

⭐ **So the message does NOT reference the 09-30 report.** He has not read it, and a
pointer to something unread adds a question instead of answering one. The message has to
stand completely on its own.

---

## The message

> Hi Mario — I know it's been a busy week, so I've kept this short. Is there someone with
> a Bloomberg terminal you could pass a file to?
>
> **What it's for.** The last 412 securities in the portfolio we can't yet value — the
> CMOs, the commercial mortgage-backed and the asset-backeds. All we need is how much of
> each one was repaid in each month since 2009. With that we can value them from what
> actually happened to them, instead of buying the deal models that describe how each
> structure divides its payments.
>
> **What it takes.** Attached is a folder with four spreadsheets. The formulas are
> already written in, so whoever runs it just opens each file, lets it calculate, saves,
> and sends it back — nothing needs typing. The first file is a one-minute check that the
> terminal returns this kind of data at all, so nobody spends real time before finding
> out. If they're short on time, the second file is the one that matters.
>
> **Why it's still outstanding after Liping's pull.** Hers came back complete, and the
> method works — we checked it against twenty pools we already price a different way and
> the two agree closely. But it only covered one of the four securitised categories,
> Government MBS; these three were never in the request. That was our oversight — we
> built it from the Government MBS list and didn't extend it.
>
> One note: 375 of the 412 are in there. The other 37 have no ISIN or CUSIP in the
> custodian file we were given, so we couldn't build a request line for them — our gap to
> close.
>
> No urgency on this at all. What Liping already sent gives us a few weeks of work, so
> nothing is waiting on it. Thank you.

---

## Why it is shaped this way

**It answers two questions and stops.** What is still missing, and why Liping's pull did
not close it. Everything earlier drafts carried to *justify* the ask — the measured 2009
prepayment speed, the 8bp agreement in full, the spread band it confirmed — is cut or
reduced to one clause, because an explanation he did not ask for reads as pleading.

**The result survives as a single clause, not a paragraph.** *"The method works: we
checked it against twenty pools we already price a different way, and the two agree
closely."* Without it the message is a fourth request for data with nothing to show; with
a paragraph of it, the message becomes about us. One line is the whole argument — the
previous favour produced something.

⭐ **"Closely" rather than "to a median of 8 basis points."** The precise figure invites a
methodology conversation inside a message whose only job is to get a file in front of a
terminal. It is in the pack and in the report for when he wants it.

**The oversight is stated once, plainly, and not apologised for twice.** *"We built it
from the Government MBS list and didn't extend it."* That is what happened. A second
sentence of contrition would make him manage our feelings.

### ⭐ On tone — the message was deliberately NOT softened overall

Asked whether to make it more deferential, the answer is no, for a reason specific to
what this message contains: **it carries an admission of our error.** The instinct when
apologising is to soften everything, and the effect inverts — soft plus apologetic reads
as *anxious*, and anxiety invites doubt about competence. Crisp ownership with a clear
fix reads as professional. Mario is a technically fluent client and the standing rule for
his documents is **never talk down to him**; excess deference is its own form of that.

⭐ **What WAS changed had nothing to do with politeness and everything to do with not
arguing and not pressuring:**

| | why |
|---|---|
| **cut** *"That purchase is the alternative, and it isn't cheap."* | the only sentence in the message that **argues**. He has not pushed back on anything, so pre-emptive persuasion reads as pleading or as leverage — and telling an MD that a purchase is expensive is informing him of something he knows. State the alternative neutrally; he draws the conclusion himself. |
| **added** *"I know it's been a busy week, so I've kept this short."* | not filler — the meeting was cancelled, we noticed, and saying so pre-excuses a slow reply. It is the user's actual worry (imposing on a busy person) answered in one clause. |
| **added** *"No urgency on this at all… nothing is waiting on it."* | ending on "our gap to close" was abrupt for a request. ⭐ And it is **true**: the ~314 securities unblocked by Liping's pull are weeks of work. ⚠️ Counter-intuitively this raises the odds of a reply — all three ignored July asks carried implied urgency, and an ask that can be done *whenever* does not have to be deferred. |
| **fixed** a comma splice before *"we built it from…"* | a client message |

**Left alone on purpose:** the direct opening question (*"is there someone … you could
pass a file to?"* is already softened by the modal and the indirect form), the bold
labels (scannable beats formal for a phone), and the admission itself.

**No percentages.** "412 securities" is concrete. "18% of the portfolio" is 18.2% **by
count** and **4.8% by par value**, and Mario reads a portfolio percentage as value —
giving both is correct and heavy, giving one is light and misleading, giving neither is
light and true. *"The last three types we haven't started on"* already carries the weight.

**The ask is for a name — not an account, and not his afternoon.**

| | what it costs him |
|---|---|
| ⭐ **"Is there someone you could pass it to?"** | one forward, 30 seconds, zero exposure |
| an introduction to the friend | a social favour, but it takes him out of the loop afterwards |
| ⚠️ borrowing the friend's account | he must ask his friend to breach their employer's terminal agreement for a vendor they have never met — **and it does not work**: a Bloomberg login is bound to an enrolled fingerprint plus a physical B-Unit, so a password alone logs nobody in |
| ⚠️ asking him to run it himself | never ask an MD to operate a spreadsheet |

⚠️ **If he offers the account anyway, decline it before he promises it to his friend.**
One sentence — the login needs that person's own fingerprint, so could they run it
instead. Far easier said before the offer has been passed on than after.

**The 37 are disclosed before he can find them.** `375 ≠ 412` is the first thing a careful
reader notices, and he is a careful reader. One volunteered sentence costs nothing; the
same fact discovered costs the credibility of every other number in the message.

---

## Four claims corrected in drafting, and every one leaned the same way

Worth keeping as a pattern rather than as four separate fixes.

| claimed | true |
|---|---|
| "this is the second ask" | he was asked three times in July (`missing_data.md` G1–G4: 07-20, 07-22, 07-30). Liping's was simply the first pull that came **back** |
| "no identifier to request them by" | they carry deal / series / class, and a Bloomberg CMO ticker is `<DEAL> <SERIES> <CLASS> Mtge`. The true claim is the smaller one — no ISIN or CUSIP in the custodian file |
| "18% of the portfolio" | 18.2% by count, **4.8% by par value** |
| "the range we showed you last week" | he has not seen the report — the meeting was cancelled |

⭐ None was a lie, and all four leaned toward making the ask look more deserved. **The
lean is the thing to watch for, not any one of them.**

---

## What is deliberately not in the message

The 114,421 data points, the sheet layout, the field names, the entitlement probe's real
purpose, the I/O-strip question we settled ourselves, and the deferred registry items
G2–G6. The operating detail belongs in the pack's own README, addressed to whoever
actually sits at the terminal. The deferred items stay out on the rule that a gap which
**blocks** a security belongs in a request and a gap which only **confirms** a convention
does not — every G5 bond prices today.
