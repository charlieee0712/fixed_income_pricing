# Reply to Mario's call — 2026-10-16

**Channel:** WhatsApp, same thread. **No attachment** — three answers to three questions he
asked on the phone.

⚠️ **The call is the user's RECOLLECTION, flagged as approximate** (same standing as the
2026-10-14 instruction and the 2026-10-06 phone points). What he asked, as recorded:

1. He will send the **six index histories** — and asked *"didn't the index dataset I already
   sent you have those six?"*
2. He will send **`MTG_FACTOR` for the 412** — and asked *"how does your method simplify the
   traditional Tier 2 approach?"*
3. He checked and **Bloomberg does carry formulas for the 201** — so *"why not just use the
   formula? why do you also need CPN?"* The user answered **"it's more accurate"**, which is
   right and is made concrete below.

⭐ Every number in the reply was measured on 2026-10-16 against **his own files**, not recalled.

---

## The message

> Thanks for the call — and for the six series and the factor history, that clears the way on
> both fronts.
>
> *On the index file: no, those six aren't in it — I checked it column by column.* What you
> sent carries eleven series, and only five of them reach back to 2009 at all: US0001M,
> US0003M, COF 11, 12MTA and H15T1Y. The rest are Term SOFR and the SOFR averages, which start
> in 2018-19, plus ECOFC which starts in 2022 — all empty at a March-2009 valuation date. And
> the six I asked for come straight out of your own formulas: *RFUCCT1Y* appears in 30 of them,
> *RFUCCT6M* in 13, *US0012M* and *EUR003M* in five each, *US0006M* and *H15T5Y* in one each.
> One trap worth naming: TSFR6M is in the file and US0006M isn't, and those two look
> interchangeable but aren't — Term SOFR is a different rate and didn't exist in 2009. The
> first two alone unlock 42 of the 60 adjustable-rate pools we currently can't even test.
>
> *On how this sits against Tier 2.* It doesn't simplify Tier 2 so much as remove the need for
> it at this particular date. *Tier 2 exists to predict how much principal comes back each
> month. For a March-2009 valuation we don't have to predict it — it already happened, and the
> trustee published it month by month.* On 349 of the 373 securities where we hold a path —
> 94% — the whole cash flow from the valuation date to the last dollar is recorded fact, a
> median of 127 monthly observations, with no prepayment assumption anywhere in it. Only 24
> needed any projection at all.
>
> What it saves against the structural route is the waterfall. To know what one slice receives
> you normally need the rules for the entire deal — for the government mortgage book alone that
> was roughly 170 complete deal models, because most of those deals contribute exactly one
> slice to your portfolio. A slice's factor *is* the waterfall's output, already computed by the
> trustee. Two subtractions a month replace the rulebook.
>
> The limit is worth stating plainly: it only works backwards. Value the same securities at
> today's date and you'd have history up to now and an unknown future — which is exactly what
> Tier 2 is for. So this isn't a substitute for Tier 2, it's Tier 2's input. Your own slide
> lists historical monthly repayments and observed realised behaviour as the existing
> engineering work: that is this.
>
> *On the formulas versus the coupon history* — and here I owe you a correction, because what I
> sent last week was put more strongly than the facts support.
>
> We did use the formulas. They're parsed and in the code from the files you sent on the 14th.
> Running them against the 201 at 31 March gives: *94 have no formula at all*; 14 have one that
> says fixed while the coupon type says it moves; one names an index the file doesn't carry;
> and *92 produce a coupon*.
>
> The 92 are the problem, not the reassurance. They produce a number whether or not it is the
> right one, and nothing in the formula tells us which. 27 come out at or below 0.75%, which is
> exactly where a floor would bite if there is one; 12 are inverse floaters, whose coupon with
> LIBOR at 0.50% sits against a lifetime cap we don't hold; the highest computes 19.2%. And on
> the one population where we *can* check — the agency ARM pools, where you also report the
> coupon — the formula came out one to three points below your own number on all seventeen we
> could test, every one in the same direction. The formula was right. The reset date and the
> caps simply aren't in it.
>
> *The correction:* I said the two series were needed together. That isn't right. *The factor
> history on its own unblocks all 412* — we would hold the custodian's coupon flat, which is
> your own rule and exactly what we already do for the 192 moving-coupon pools in the government
> book. The coupon history doesn't decide whether we can price them; it decides whether we can
> publish a duration for the 201 without a caveat attached to it. So the factor history is the
> one that blocks and the coupon history is the one that qualifies. Send the first and we're
> away; the second whenever it suits.

---

## The measurements behind it (2026-10-16, all from his own files)

### ① The index file — `data/index.xlsx`, 11 series

| | series | covers 2009? |
|---|---|---|
| reach back to 2009 | `US0001M` · `US0003M` (both 2000-01-04 → 2024-09-30) · `COF 11` (264 monthly) · `12MTA` (321 monthly) · `H15T1Y` (6,697 daily) | **yes, 5 of 11** |
| start 2018-19 | `TSFR1M` · `TSFR3M` · `TSFR6M` (2019-01-03 →) · `SOFR30A` (2018-05) · `SOFR90A` (2018-07) | no |
| starts 2022 | `ECOFC` (56 obs, 2022-01 →) | no |

**All six asked-for series are ABSENT.** A twelfth column, `us0003 tsfr3M`, is a label with no
values beside it.
⚠️ **The lookalike trap, worth naming to him:** `TSFR6M` is present and `US0006M` is not;
`H15T1Y` is present and `H15T5Y` is not; `US0001M`/`US0003M` are present and `US0012M` is not.
Each pair differs by rate family or tenor, and a reader scanning the sheet would reasonably
think the request was already satisfied — which is precisely what he asked.

**The six come from his own formula table** (`data/coupon_formula.csv`, built from his 10-14
files): `RFUCCT1Y` 30 periods / 30 securities · `RFUCCT6M` 13 / 13 · `US0012M` 5 / 5 ·
`EUR003M` 5 / 5 · `US0006M` 1 / 1 · `H15T5Y` 1 / 1.

### ② Tier 2 — the 94% is the whole answer

From `outputs/tier1_structured_2009-03-31.csv`, the 373 observed-path securities:

| | |
|---|---:|
| months of recorded history used, median | **127** |
| securities needing **zero** projected months | **349 of 373 (94%)** |
| securities needing any projection | **24** |
| residual treatments | `none` 227 · `repaid_tail_would_overrun` 118 · `amortised` 24 · `repaid_below_floor` 3 · `repaid_tail_not_decaying` 1 |

⭐ The liftable sentence, written so he can use it in his own deck: *"Tier 2 exists to predict
how much principal comes back each month; for a 2009 valuation we don't predict it — the
trustee already published it, and we read it."*
⚠️ And the limit, stated in the same breath, because leaving it out would oversell: the method
is backward-looking by construction, so it carries no scenario response. That is what makes it
Tier **1** rather than a shortcut through Tier 2 — and the factor extraction is the very
"existing engineering work" his Tier-2 slide already lists as that tier's input.

### ③ The formulas on the 201 — run, not argued

Rule in force at 2009-03-31, index levels read from his own `index.xlsx`
(`US0001M` 0.50063% · `US0003M` 1.19188% · `H15T1Y` 0.570% · `12MTA` 1.43984% · `COF 11` 1.627%):

| outcome | n |
|---|---:|
| **no formula at all** | **94** |
| produces a coupon | **92** |
| formula says FIXED while `Type of Coupon` says it moves | 14 |
| names an index not in the file | 1 |

Of the 92: median **0.831%**, range **0.531% – 19.198%**; **27 at or below 0.75%** (floor
territory), **12 inverse floaters**, 4 leveraged (|multiplier| ≠ 1).

⚠️⚠️ **Nothing was refused by the sanity band** — so the honest statement is *not* "the formula
gives nonsense here". It gives plausible numbers that we cannot verify. ⭐ The verification
evidence has to come from the one population where both the formula and an observed coupon
exist: the agency ARM pools, **17 of 17 testable, 0.96–3.15 points below the custodian's own
coupon, every one the same sign**, because the reset date is not in the formula. That is the
measurement that answers him, and it is borrowed from a different population — which the
message says.

### ④ ⚠️ The correction we owe him

`docs/mario_message_2026-10-14_412.md` said: *"for a bond whose coupon moves, a balance with no
coupon and a coupon with no balance each leave us unable to build a cash flow"*. **The first
half is false.** Measured today: **all 412 carry a custodian coupon (`income_rate`) and a
maturity** — 385 non-zero, 27 at exactly zero (the P/O strips, which need none). So with
`MTG_FACTOR` alone we can price every one of the 412 on the custodian's coupon held flat, which
is **his own exception rule** and precisely the treatment the 192 moving-coupon Government-MBS
holdings already get, disclosure and all.

⭐ **So the ask re-sorts under our own standing rule — what enters a request is what BLOCKS a
security, never what only qualifies a convention:** `MTG_FACTOR` blocks, `CPN` qualifies.
Saying so costs us nothing real and is the difference between a request he can trust and one he
has to audit.

---

## Deliberately not in the message

- **Any defence of the 10-14 wording beyond the one-line correction.** He asked a fair
  question; the shortest honest answer is to concede the half that was wrong and keep the half
  that is measured.
- **The four BT-marked hybrids / his exception rule.** Already in the 10-14 message and the
  report §5.2, awaiting his word; repeating it here would bury three fresh answers under an old
  open item.
- **The 162 securities touching an index with no 2009 history.** Most of that count is Term
  SOFR and SOFR-average periods that take effect long after the valuation date, so quoting it
  would overstate the gap. The six names, with their own reference counts, are the honest form.
