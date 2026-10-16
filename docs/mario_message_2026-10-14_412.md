# Asking Mario for the 412 — 2026-10-14, message two of two

**Channel:** WhatsApp, same thread. **Attachment:** `docs/bloomberg_412_request_2026-10-14.xlsx`
(two sheets, 29 KB, forwardable as-is). **Generator:** `scripts/make_412_request.py`, which
refuses to write unless the counts reconcile.

⚠️ **Both messages are being sent together**, so this one opens by ranking itself *below* the
other. Two asks arriving at once risk the bigger one crowding out the small, nearly-free one —
and the small one is the better trade for him. The first line of this message exists to stop
that.

⭐ **Why two messages rather than one, even sent together.** They are two different DECISIONS,
not two populations: the other message asks him to finish a book that is already running; this
one asks him to open a class we have not started. He can reasonably say yes to one and defer
the other, and a single message forces one answer on unequal things.

---

## The message

> *Second one, and it's the bigger of the two* — the other message is small and quick, so do
> that one first if you only have time for one. This can wait.
>
> *The 412 we still can't value at all.* The non-government CMOs, the commercial
> mortgage-backeds and the asset-backeds. They're about 18% of the portfolio by number of
> holdings but only around 5% by par value — the count makes it sound bigger than it is — but
> it's the last category with nothing behind it at all.
>
> *What we need, and both in one go:*
>
> • *MTG_FACTOR*, monthly, 1 March 2009 to now, for all 412 — how much of each one was repaid
> each month. Same field and same window as the pull that came back complete in September, just
> pointed at the securities that request never covered.
>
> • *CPN*, monthly, same window, for the 201 of them whose coupon moves. We know which 201 from
> the file you sent this week, and the list marks them.
>
> Both together rather than one and then the other: for a bond whose coupon moves, a balance
> with no coupon and a coupon with no balance each leave us unable to build a cash flow, so
> splitting it would only mean coming back for the other half.
>
> *Attached* is the list — 412 securities with CUSIP, class, coupon type, and a column saying
> which of the two series each one needs. The security string is already built so it can be
> pasted straight in. I've deliberately not prewired any formulas: the last three pulls came
> back clean, so I assumed you'd rather build it your own way. If a ready-to-run sheet would be
> easier, or if someone else is going to run it, just say and we'll send one.
>
> One good thing, and it comes from your own file: 37 of these 412 had no usable identifier in
> the custodian data and we were going to have to leave them out. Your mortgage file supplied
> CUSIPs for all 37 — so this is the full set, with nothing missing.

---

## Why it is shaped this way

**It ranks itself first, before anything else.** Sent alongside a smaller ask, a 129,000-value
request will otherwise absorb all the attention and the cheap one gets lost. ⭐ The six index
series in the other message cost him minutes and unblock 42 pools; this one is a real session.
Saying so is both honest and in our interest.

**Both series, one sitting — and that is a rule, not a preference.** `missing_data.md` and the
2026-09-29 lessons: *never ship a request with a second round baked into it.* 211 of the 412
are fixed or zero and need only the factor; **201 need both**, because a balance without a
coupon and a coupon without a balance each give no cash flow. Asking for the factor now and the
coupon later would be a second request in a cheap costume.

```
412 x 211 months  =  86,932   MTG_FACTOR
201 x 211 months  =  42,411   CPN
                    -------
                    129,343 values
```

⚠️ That is about 1.6× September's 79,336, which returned complete — worth him knowing the size,
which is why the README states it plainly rather than burying it.

⭐ **Both percentages are quoted, and that is deliberate.** The 412 are **18.2% of the book by
count and 4.9% by par value**. Mario reads a portfolio percentage as value, so the count alone
overstates by about four times — in the direction that flatters the ask. The standing rule is
quote both, or say which.

## ⭐⭐ A list, not a pack — because the operator changed

The 2026-10-02 pack (`docs/bloomberg_request_2026-10-02/`) carried four prewired formula sheets
because it was built for an operator who might lack the mortgage entitlement, might open a .csv
and see no functions, and could not be asked to debug a transposed spill. **Mario has since run
three pulls himself**, including a transposed multi-value field that spilled correctly and a
47-column index file. That machinery is overhead for him.

⚠️ **And three of that pack's four sheets are now wrong or obsolete anyway:**

| sheet | was | now |
|---|---|---|
| `01_CHECK_FIRST` | entitlement probe | moot — he has already pulled, three times |
| `02_factor_history` | 375 × 211 | ⚠️ population stale: **412**, see below |
| `03_coupon_monthly` | 156 × 211 | ⚠️ built from a union later measured at **40.3% recall**; the right population is 201 |
| `04_coupon_classify` | 595 × 4 | ⭐ **answered outright** by `Type of Coupon` — delete |

⇒ "send the pack" would mean rebuilding essentially all of it for someone who does not need it.
The attachment is a plain list with a README sheet, and the message offers the runnable version
on request — ⭐ built then, for a known operator, rather than speculatively now.

## ⭐⭐ The 37 are back, and it is his own data that did it

The old pack could write only **375** request lines; **37 of the 412 carried no ISIN or CUSIP in
the custodian file**, and both its README and its covering message had to disclose that, because
"375 ≠ 412 is the first thing a careful reader notices". Measured 2026-10-14 against
`data/coupon_structure.csv`: **all 37 now carry a well-formed CUSIP**, supplied by
`data/mtge.xlsx`, none malformed.

⇒ the ask is **412 of 412 with no caveat to apologise for**, and the generator ASSERTS 412 so
the old number cannot creep back. ⭐ It goes in the message because it is a concrete second
payoff from a pull he has already run, and because it is the kind of thing worth telling someone
who is about to be asked for more.

## Deliberately NOT in the message

**① The formulas, prewired.** See above — offered, not assumed.

**② Any repetition of the other message.** No thanks, no win report, no context. They arrive
together; repeating would waste the reader's attention and make two messages read as one long
one.

**③ The 37's old provenance.** He does not need to know that we previously could not reach them
by CUSIP and considered finding them by deal/series/class by hand. The fact that matters is that
they are in.

**④ What we will do with it.** The factor route is already proven and described in the earlier
material; restating the method here would turn an ask into a report.
