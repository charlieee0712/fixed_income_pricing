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
> We did use them — they're parsed and in the code from the files you sent on the 14th — and
> running them against the 201 at 31 March gave a more interesting answer than I expected.
>
> The arithmetic first: *94 of the 201 have no formula at all*; 14 have one that says fixed
> while the coupon type says it moves; one names an index the file doesn't carry; and *92
> produce a coupon*.
>
> *And those 92 are mostly right* — 86% land within five basis points of the coupon you already
> report in the holdings file. The formulas are sound. But 75 of the 92 come out *low*, and the
> misses aren't random: the two COF-11 bonds are both out by exactly 1.130 points, and the three
> 12MTA bonds by exactly 0.193. An identical error on securities sharing nothing but an index is
> a date, not a formula — and working backwards says so plainly. Those COF-11 coupons were
> struck on the *December* print, 2.757%, exact to five decimals, while the formula at 31 March
> reads 1.627%. One H15T1Y bond implies a one-year Treasury of 2.375%, which is where it stood
> the previous June. Every index carries its own reset lag, and the lag isn't in the formula
> field. At the other end one inverse floater computes 4.499% against your 1.980% — two and a
> half points the other way, which is what a cap looks like.
>
> *And that is what reframes it.* We don't need the formula to know the coupon at the valuation
> date — you already give us that, for all 412, in the holdings file. The check above is only
> possible because you do. So the formula can at best reproduce a number we already hold, and
> 14% of the time it doesn't. What neither it nor that single number can tell us is how the
> coupon *moved* over the months after it, and that is the only thing the coupon history adds.
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

⚠️⚠️ **Nothing was refused by the sanity band**, so "the formula gives nonsense here" was never
available. ⚠️⚠️ **AND THE FIRST DRAFT'S FALLBACK WAS WRONG TOO:** it said the agency ARM pools
were *"the one population where we can check"*, because both a formula and an observed coupon
exist there. **They are not** — the custodian reports `income_rate` for **all 412**, so the 92
can be checked directly, on the population he actually asked about. Measured 2026-10-16:

| formula minus custodian, 2009-03-31, n=92 | |
|---|---:|
| within 0.05 pt | **79 (86%)** |
| within 0.25 pt | 86 (93%) |
| median difference | **−0.021 pt** |
| formula LOWER / HIGHER | **75 / 15** |
| worst | **+2.519** and **−1.805** |

⭐⭐ **This runs partly AGAINST us, and the message now says so: the formulas are sound.** What
survives is sharper than the overstatement it replaces, because **the misses cluster by INDEX,
identically**, which names the cause:

| index | n | error | implied level | what that level is |
|---|---:|---:|---|---|
| `COF 11` | 2 | **−1.130 each** | **2.757%** | the **2008-12-31** print, exact to 5 dp (31 March reads 1.627%) |
| `12MTA` | 3 | **−0.193 each** | 1.63284% | the **2009-01-31** print (1.63408%) |
| `H15T1Y` | 1 | −1.805 | 2.375% | where the 1-year Treasury stood in **June 2008** |
| inverse | 1 | **+2.519** | — | `9393363R2` computes 4.499% against a reported 1.980% — a cap |

⇒ **the formula is right; the reset LAG is what is missing, and every index has its own.** Two
securities out by the *same* amount to three decimals are not two coincidences.

⭐⭐⭐ **AND THE REFRAMING THAT ACTUALLY ANSWERS HIM:** the formula's competitor was never the
coupon history — it is **the custodian's own valuation-date coupon, which we already hold for
all 412 and already use**. The formula can at best reproduce that number, and 14% of the time
it does not. The coupon history answers a different question: **how the coupon moved over the
following months.** Nothing else on the table answers that one.

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
