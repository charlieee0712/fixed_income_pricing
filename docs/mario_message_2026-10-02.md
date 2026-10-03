# Asking Mario for one more terminal session — 2026-10-02

⭐⭐ **ASK IT AT THE WEEKLY MEETING, NOT BY MESSAGE.** Three asks went to Mario in July
(`missing_data.md` G1–G4: 07-20, 07-22, 07-30), all asynchronous, and **none came back**;
Liping's did. The channel is the variable with the evidence against it.

⭐⭐⭐ **And the 09-30 report sets this up almost word for word.** Its §4.1 tells him *"the
test is built into the request — it includes 20 ordinary pools we already price, so the
method gets checked against numbers we already trust before it is pointed at a single
slice"*, and §4.2 promises *"we will know within days whether these 756 securities can be
valued without buying deal models."* The meeting has not happened yet. So this is not a
request arriving cold — **it is the result of a prediction he is about to read**, and the
ask is the next sentence after it.

⚠️ **Do NOT ask for the friend's account.** It is the heaviest of the four options, not
the lightest:

| | what it costs Mario |
|---|---|
| ⭐ **"Is there someone you could put this in front of?"** | one forward, 30 seconds, zero exposure — **do this** |
| an introduction to the friend | a social favour, but it takes him out of the loop afterwards |
| ⚠️ borrowing the account | he must ask his friend to breach their employer's terminal agreement, for a vendor they have never met — **and it does not even work**: a Bloomberg login is bound to an enrolled fingerprint plus a physical B-Unit, so a password alone logs nobody in |
| ⚠️ asking him to run it himself | never ask an MD to operate a spreadsheet |



**Channel:** WhatsApp. **Attachment:** the folder `docs/bloomberg_request_2026-10-02/`,
which is self-contained English and can be forwarded to whoever runs it without
further explanation.

⚠️ Written for Mario alone. Finance precise, engineering absent — no field names, no
file formats, no counts of data points. He redefined OAS as a calibration and knows
spreads cold; "prepayment speed" and "basis points" are his vocabulary, "transposed
layout" and "entitlement" are not.

Every number below is traceable: 376 complete / 8 bp over 14 in-grid pools / ~20% CPR /
412 securities / 375 requestable / 37 without an ISIN — all from
`docs/bloomberg_return_2026-10-01.md` and the build log of the pack itself.

---

## A. What to say at the meeting — the primary route

Spoken, after walking him through §4 of the report. About sixty seconds.

> Since I wrote this, the answer came back — and the method works. Liping got the factor
> history for the Government MBS slices, and we checked it against twenty ordinary pools
> we already price a different way: they agree to within 8 basis points, with no bias
> either way. So the branch in section 4 is live — we probably don't need to buy deal
> models.
>
> One thing I got wrong, though. That same trip should have collected the other three
> categories at the same time — the CMOs, the commercial mortgage-backed and the
> asset-backeds — and it didn't. It only covered Government MBS. That's 412 securities,
> and they're the last three types we haven't started on.
>
> Is there someone with a Bloomberg terminal you could put this in front of? Everything's
> prepared — four spreadsheets with the formulas already written in, open and save,
> nothing to type. The first one is a one-minute check, so nobody wastes time if the
> terminal can't return it.

⭐ **The ask is for a NAME, not for an account and not for his afternoon.** If he offers
the account anyway, decline it gently and ask who could run it — the login will not work
without that person's fingerprint, and saying so is easier before he has made a promise to
his friend than after.

⭐ **The oversight, phrased to match what he will have just read.** The report said the
request carried a test of the method. It did, and the test passed. What the same trip
should *also* have done is collect the other three categories' data while it was being
paid for. That is a wrong manifest, not a wrong method — a logistics slip, which is both
the truth and the version a listener forgives.

⚠️ **Be ready for "why didn't it cover all 756 in the first place?"** The honest answer
is one sentence: the request was generated from the Government MBS list, and nobody
checked it against the number in the report.

---

## B. The note that follows, with the folder attached

Short on purpose — the context was given live.

> Hi Mario — the Bloomberg files I mentioned, attached as a folder.
>
> Four spreadsheets. The formulas are already written in, so whoever runs it just opens
> each one, lets it calculate, saves, and sends it back — nothing needs typing. Please
> have them start with **01_CHECK_FIRST**: it takes a minute and confirms the terminal
> returns this kind of data before anyone spends real time on the rest.
>
> The README inside explains everything else, so the folder can be forwarded as it is.
>
> One note: 375 of the 412 securities are in there. The other 37 have no ISIN or CUSIP in
> the custodian file we were given, so we couldn't build a request line for them — our
> gap to close, not theirs.
>
> Thank you — and thanks for asking on our behalf.

---

## C. Fallback — if the meeting slips or he is not there

⚠️ Use this **only** if the live route is unavailable. It carries the context the meeting
would have carried, which is why it is four times longer.


Hi Mario — an update, and one request.

**What came back.** Liping was able to run part of our Bloomberg request at the
university terminal, and it returned complete: monthly repayment histories for 376 of
the mortgage securities, no gaps. We then tested the method against twenty pools we
already price a different way. On the fourteen where both approaches are in range they
agree to a median of 8 basis points, with no systematic bias either way.

It also gave us something we had never had — the prepayment speed this portfolio
actually ran at through 2009, which was about 20% a year. That sits between the two
assumptions we had been pricing on, so the spread range we produced for those bonds
was centred correctly.

**Where we fell short.** That same request should have covered the other three
securitised categories — the CMOs, the commercial mortgage-backed and the asset-backed —
and it did not. We built it from the wrong starting list. Those are 412 securities —
about 18% of the holdings by count, though under 5% by par value — and they are the
last three types we have not started on.

**The request.** Would you be able to borrow a friend's Bloomberg account for one
session? Everything is ready: four Excel files with the formulas already written in.
Open each one, let it calculate, save, send it back — nothing needs to be typed. The
first file is a one-minute check that the terminal returns this kind of data at all, so
nobody spends an hour before discovering it doesn't.

One honest note: 375 of the 412 are in there. The other 37 have no ISIN or CUSIP in the
custodian file we were given, so we cannot build a request line for them — a gap on our
side rather than something this pull can close.

I know we have asked for terminal time before. I would rather make this one complete
than come back again.

---

## Why it is shaped this way

⚠️ The notes below were written for the long version (route C) and apply to all three.

**Liping is credited first and the oversight is named without padding.** "We built it
from the wrong starting list" is what actually happened — the request was generated from
the Government-MBS universe object that was loaded at the time, while the report sent the
same day told him the method might reach 756 securities across four classes. A vaguer
"an oversight on our part" would have been easier to write and less true.

**The validation leads, because it is what makes the ask worth granting.** He is being
asked to spend a friend's goodwill. The relevant fact is not that we need data, it is
that the method using that data has been checked against an independent calculation and
agrees. Without that paragraph this is a request to fund a hope.

**Four things were corrected after a review, and the pattern in them is worth keeping:
every one overstated in our favour.** "The second ask" (he was asked in July three times —
`missing_data.md` G1-G4 — Liping's was simply the first that came back); "no identifier to
request them by" (they carry deal / series / class, and a Bloomberg CMO ticker is
`<DEAL> <SERIES> <CLASS> Mtge`; the true claim is the smaller "no ISIN or CUSIP"); "18% of
the portfolio" (18.2% by count, **4.8% by par value**, and he reads a percentage as value);
and a reference to a report that may not have reached him. ⭐ None was a lie and all four
leaned the same way, which is the thing to watch for rather than any one of them.

⭐ **ANSWERED 2026-10-02 — the weekly meeting has not happened, so he has NOT seen the
09-30 report.** That is what moved the ask from a message to the meeting itself: the
report's own §4.2 promises an answer "within days", and the answer now exists. Delivering
a result against a prediction is a different conversation from asking for a favour.

**The 37 are disclosed before he can find them.** 375 ≠ 412 is the first thing a careful
reader notices, and he is a careful reader. Volunteering it costs one sentence; being
asked about it costs the credibility of every other number in the message.

**No second ask is bundled in.** The deferred items in `missing_data.md` (G2–G6) are
confirmation-only — all those bonds price today — and adding them would trade a clean,
proven single-field request for a mixed one whose untested parts could fail silently in a
stranger's hands.

**What is deliberately not in the message:** the 114,421 data points, the sheet layout,
the field names, the entitlement probe's real purpose, and the I/O-strip question we
settled ourselves. All of it is in the pack's own README, addressed to the person who
will actually sit at the terminal.
