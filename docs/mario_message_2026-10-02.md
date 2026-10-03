# Message to Mario — 2026-10-02

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

## The message

Hi Mario — an update, and one request.

**What came back.** Liping was able to run part of our Bloomberg request at the
university terminal, and it returned complete: monthly repayment histories for 376 of
the mortgage securities, no gaps. We then tested the method against twenty pools we
already price a different way. On the fourteen where both approaches are in range they
agree to a median of 8 basis points, with no systematic bias either way.

It also gave us something we had never had — the prepayment speed this portfolio
actually ran at through 2009, which was about 20% a year. That sits between the two
assumptions behind last week's report, so the 220–265 bp range we showed you was
correctly centred.

**Where we fell short.** That same request should have covered the other three
securitised categories — the CMOs, the commercial mortgage-backed and the asset-backed —
and it did not. We built it from the wrong starting list. Those are 412 securities,
about 18% of the portfolio, and they are the last three types we have not started on.

**The request.** Would you be able to borrow a friend's Bloomberg account for one
session? Everything is ready: four Excel files with the formulas already written in.
Open each one, let it calculate, save, send it back — nothing needs to be typed. The
first file is a one-minute check that the terminal returns this kind of data at all, so
nobody spends an hour before discovering it doesn't.

One honest note: 375 of the 412 are in there. The other 37 have no ISIN in the custodian
file, so there is no identifier to request them by. That is a gap on our side, not
something this pull can close.

I know this is the second ask. I would rather make one complete request than come back a
third time.

---

## Why it is shaped this way

**Liping is credited first and the oversight is named without padding.** "We built it
from the wrong starting list" is what actually happened — the request was generated from
the Government-MBS universe object that was loaded at the time, while the report sent the
same day told him the method might reach 756 securities across four classes. A vaguer
"an oversight on our part" would have been easier to write and less true.

**The validation leads, because it is what makes the ask worth granting.** He is being
asked to spend a friend's goodwill. The relevant fact is not that we need data, it is
that the method using that data has been checked against an independent calculation and
agrees. Without that paragraph this is a request to fund a hope.

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
