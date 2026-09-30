# The securitised book — mortgage pools, and the third of the portfolio behind them

**New 2026-09-26.** The mortgage book was the last asset class with an engine waiting on data.
The data arrived, the engine moved into the template, a driver now prices it — and the round
found something that reaches well past MBS and should shape any plan touching the remaining
classes.

---

## 1. The headline, if you read nothing else

**Only 56% of the "Government MBS" class is a simple pass-through pool.** The other 39% are
tranches of structured deals, and their cash flows come from each deal's own waterfall, which
is in no field-level data pull we have or have asked for.

Counting the same structure across the classes still to do:

| class | securities | needs deal structure |
|---|---:|---:|
| Government MBS | 882 | 344 |
| Non-Government CMOs | 264 | 264 (100% tranche) |
| Commercial Mortgage-Backed | 69 | 69 (100% tranche) |
| Asset-Backed Securities | 79 | **79 (all)** |
| **total** | | **756 = 33% of the 2,260-security book** |

⚠️ **The ABS cell read `47 (59%)` until 2026-09-30 and was wrong; the TOTAL was right** — 344+264+69+47 is 724, not 756, so the total had been computed with ABS = 79 and the cell disagreed with it in plain sight.

Re-deriving it showed how. ``pool_structure()`` reads the custodian description, and its patterns are MORTGAGE vocabulary (REMIC, CMO, I/O). Run against ABS it returns ``unclassified`` for **71 of 79** — which means *this classifier cannot read these descriptions*, not *these are simple pass-throughs*. The text says otherwise plainly: `WAMU ASSET-BACKED CTFS SER 2007-HE3`, `CWABS INC 2005-16 ASSET BKD CTF CL`, `NELNET STUDENT LN TR 2008-4` — and **44 of the 79 carry a CLASS/CL token**. They are securitisation trusts with tranches, all of them.

⭐ **So the per-class counts rest on two different kinds of evidence, and the distinction is worth keeping.** Government MBS is **measured per security**, because that class genuinely mixes 490 simple pass-throughs with 344 tranches. CMO / CMBS / ABS are **by definition** — the class is what it is named — corroborated by the description text wherever the classifier can read it. Quoting a classifier's output as a count for a class it was never built for is exactly how the 47 happened.

⭐ **This is a purchase decision, not a scheduling one.** Writing a CMO engine without the
waterfalls produces a program with nothing to feed it, and every deal's rules differ — 264
CMOs are 264 different contracts. Intex exists because this is a business, not an afternoon.
Put to Mario 2026-09-26; unanswered.

⚠️ Do not plan "we write the CMO engine next quarter". Plan "we ask whether the structure
data is being bought, and what we do in each branch".

### ⭐ Measured 2026-09-29 — the claim above is now evidence, not reasoning

The Government-MBS 344 were taken apart before asking a colleague to spend terminal time on
them. Four findings, all reproducible from `scripts/pool_risk.py`'s own loaders:

* **344 tranches sit in 170 distinct deals, and 144 of those deals contribute exactly ONE
  tranche.** ⭐ This is the load-bearing number. We hold a single slice of a deal that may
  have twenty, and a waterfall cannot be run for one slice — it allocates across all of
  them. So the requirement is **~170 complete deal models**, not 344 security records, and
  no per-security field pull can express that. It is the same argument as "264 contracts",
  but measured, and about a quantity a vendor actually sells.
* **39% of the class by count, 28.5% by value** — $473.4M of $1,660.8M. Real money, smaller
  average tickets than the pools.
* ⚠️ **The tranche class letter is a per-deal convention with no cross-deal standard.** Of
  the 54 whose class token starts with `P`, **29 are PRINCIPAL ONLY strips, not PACs** —
  a 54% error rate on the one letter anybody would be tempted to route on. Any plan that
  says "we can at least classify them from the description" is wrong.
* **The cheap route was checked and is closed.** IO and PO come to exactly **76 each**,
  which looks like matched pairs — and a held IO+PO pair off one collateral reconstitutes
  that collateral, pricing with the pass-through engine we already have. We hold both
  halves in **one** deal (FHLMC 2827), and even there the two are not complementary
  (`CL XO` against `CL PS`). No reconstitution.

⚠️ **And the custodian's own risk number does not rescue them either.** Effective duration
(master `dur_eff_custodian`) on the 344 runs **−102.5 to +57.1, with 61 negative and 72
below 0.1y**, against a well-behaved 0.85–3.95 on the 490 pass-throughs. Those extremes are
not noise — a −100y IO strip is economically correct, since an IO gains value as
prepayments slow. Which is the point: **they are a different risk object, and approximating
them as pools would be a category error, not an approximation.**

### ⭐⭐ 2026-09-29 — the 344 are probably NOT blocked, and the blocker was our question

Everything above says these need a deal-structure purchase. ⭐ **That was the wrong ask.**

> A waterfall's only job is to decide how much principal each tranche receives each month.
> **The factor file records that decision.**
>
> ```
> principal(t) = orig_face × (factor(t−1) − factor(t))
> interest(t)  = orig_face × factor(t−1) × coupon(t) / 12
> ```

That is the complete cash flow vector with **no knowledge of the structure at all** — and
it is structure-agnostic as arithmetic, not as a claim. A PO has no interest term, an IO no
principal term, and a **Z accrual needs no special case**: during accrual the interest term
and the negative principal term are equal and opposite, so net cash flow is **exactly
zero**, which is what a Z does.

⭐ **And because the valuation date is seventeen years ago, most of that vector is already
observed.** Measured on the 344: **89 have paid off entirely** ($114.3M) so their realised
cash flow is complete with zero tail assumption; the **255 survivors** ($359.1M) have a
median **6.7 years** left against 17 years elapsed, so the observed window dominates and
the short tail takes the CPR grid the pools already use. `factor` and `par` are on hand for
**341 of 344** (⚠️ the master's `orig_face` is empty — derive it as `par / factor`; and
⚠️ factors run to **1.868**, correct for a Z whose balance grew).

⭐ **Why the new ask is easier than the one it replaces:** a factor is a *published monthly
fact with a date*, which is the category `BDH` serves. A cash flow *projection* is a
computed analytic off today's collateral, and dating that to 2009 is a different problem.

⭐ **Validation is built in and comes first.** The request carries **20 pass-through pools
our engine already prices** beside the 344, so the method is checked against a number we
trust before it touches a tranche. And the same history on the 490 pools yields their
**realised CPR**, turning the 15/25/35 grid from three scenarios into three plus the answer.

⚠️ **The limit that must travel with every number:** a realised path is **hindsight** — it
gives the rate the holder actually earned, not the spread the market demanded in March
2009. For *risk* metrics (spread duration, DV01, convexity) a cash flow vector is a cash
flow vector, on the same footing as the pools' fixed-CPR numbers, and **neither is an OAS**.
For "what was it worth that morning", the deal structure is still required.

⇒ **Re-scope the securitised plan.** "≈756 securities need a purchase" should now read
"≈756 need *either* a purchase *or* factor history, and factor history is worth trying
first because it is one BDH call per security." Pack: `docs/bloomberg_request_2026-09-29/`,
record: `docs/bloomberg_request_2026-09-29.md`.

### The narrower question that had not been asked

⭐ Our own text says the capability is a purchase "**(Intex, or Bloomberg CMO analytics)**"
— and the 09-29 data request then told Liping, who was about to sit at a Bloomberg terminal,
that the tranches were a conversation for Mario. One of the two sources we had named was
within reach and nobody asked it. Corrected same day.

**Bloomberg will not hand over a waterfall** — the rules live inside its analytics, not in
any field, and no BDP/BDH mnemonic returns them. But a waterfall's *job* is to emit a cash
flow schedule, and **if the terminal will give us the schedule for our tranche we never need
the rules**: discount the vector on our curve, solve for the spread, bump for risk — the
path every other bond in this book already takes. No CMO engine at all.

⚠️ **Expect no.** A projection is a computed analytic off *today's* collateral state, and
dating it to 2009-03-31 is strictly harder than dating a stored field — many of these deals
have since paid off. But `outputs/cmo_structure_probe.csv` (3 securities × 5 questions,
~5 minutes) asks it anyway, with **Q1 = "can it be dated to 2009 at all"** first so the
other four can be skipped on a no. ⚠️ The sheet asks *questions*, never invented mnemonics
— guessing a field name is what cost the July pull.

⭐ **A measured no is the deliverable either way.** The purchase question has sat with Mario
since 09-26 on the strength of our reasoning; "we checked at a terminal" is a different
class of evidence, and it is this project's own rule (habit 5) that a claimed data gap needs
evidence from the source.

---

## 2. What the Bloomberg pull actually delivered

`data/govt_mtge_bdp.xlsm`, run by Liping **2026-07-30** (the workbook's own docProps, not the
file mtime — an upload resets that), reaching us 09-25. Regenerate the whole check with
`PYTHONPATH=src python scripts/mbs_data_check.py`.

**The delivery is complete: 882 requested, 882 returned, nothing missing or extra.** Everything
below is about what the values can be used for.

### It is a CURRENT pull, not as-of 2009

Two independent confirmations: WALA median **241 months** against a 208-month gap to the
valuation date, and Bloomberg's WAM median **69** against **289** computed from the master's
own maturity dates — a 220-month difference that is simply elapsed time.

⭐ **The master already held the field we most needed.** WAM at 2009-03-31 comes straight from
the holdings file's maturity dates for **868 of 882**, none negative. Bloomberg was never
required for it. The pull's genuine contribution is the WAC.

### Per field

| field | usable for 2009? | note |
|---|---|---|
| `MTG_WACPN` | mostly | drifts slowly; ⚠️ **RESETS** on an ARM, see §5 |
| `MTG_AOLS` | yes | average ORIGINAL loan size is static by construction |
| `MTG_WAM` / `MTG_STATED_WALA` | **no** | as-of quantities; use the master's maturity instead |
| `MTG_GEN_CPR_3M/6M/12M` | **no** | 2026 prepayment behaviour, a different rate regime |
| `MTG_HIST_COLLAT_CPR_LIFE` | **n/a** | ⚠️ **not a Bloomberg field** — see below |

⚠️ **One field we asked for does not exist.** 877 × `#N/A Invalid Field` is the terminal
rejecting the *mnemonic*, not the security. **That is an error in the request we wrote**, and
nothing short of running it could have surfaced it. The four `#N/A` strings are four different
problems with four different owners and must be counted separately:

```
#N/A Invalid Field         the MNEMONIC is wrong        -> ours
#N/A Invalid Security      the ticker did not resolve   -> 1 row
#N/A Field Not Applicable  wrong security type          -> expected, benign
#N/A N/A                   valid everything, no data    -> a real gap
```

A single "missing" count hides the first one, which is the finding.

---

## 3. Routing: 882 into eight kinds

`dataio.phase2._route_pool`, beside `_route_agency` and `_route_sovereign` — routing has one
owner here and has been re-split by accident five times in this project.

| structure | n | route |
|---|---:|---|
| pass-through | 490 | **priced** |
| remic-tranche | 185 | needs a waterfall engine |
| io-strip | 76 | a strip receives no principal; not a level-pay pool in any parameterisation |
| po-strip | 76 | receives no interest |
| tba-forward | 29 | **priced** — see §6 |
| unclassified | 18 | named rather than guessed |
| cmo-tranche | 7 | needs a waterfall engine |
| arm | 1 | the coupon resets; one fixed WAC cannot describe it |

⚠️ **The IO population was 2 before somebody noticed the slash.** `\bIO\b` never matches
`I/O`, so **76 interest-only strips sat inside the REMIC bucket** looking like ordinary
tranches. An IO strip has no principal cash flow; a level-pay model would have produced 76
confident wrong prices. Pinned by a test that also asserts the naive pattern misses them.

⭐ **Corroborated independently of the text:** Bloomberg returns `MTG_WACPN` for **490 of 490**
pass-throughs and for 67–83% of every other bucket. The terminal's willingness to describe a
security as a pool agrees with the description-based classification, and was not consulted
when the patterns were written.

⚠️ **`par_value` is CURRENT face.** `MV/(par×BT/100×fx)` has a median of **1.000000** over 872
securities; the same identity with `paydown_factor` applied gives **1.886**. Getting this
backwards halves every position. The factor is descriptive here.

---

## 4. ⭐ The anchor was refuted by its own measurement

**The plan was to fix the spread near zero (government-guaranteed paper) and solve for the
CPR. The prices refused it.** At zero spread the implied CPR came out at a median **66%** —
against the 10–25% agency pools actually prepaid in early 2009 — and for **21 pools no CPR in
[0, 99] reaches the price at all**.

Visible in one bond. `TNTD03131477` (WAC 6.99%, net 6.50%, 288 months, BT 106.28) prices at
**143.26** with no prepayment and no spread, against a 2009-03-31 curve at 2.77% ten-year.
Holding the CPR at a plausible 15–35% instead needs **+216 to +298 bp**.

⭐ **Why that is not an anomaly:** static cash flows with no prepayment option solve for a
**zero-volatility spread (ZVS)**, not an OAS. ZVS carries the option cost inside it, and
200–300 bp is the right order for agency MBS on that basis in March 2009. **Never compare
these numbers to a published OAS** — different quantities, an order of magnitude apart. The
term is Boyarchenko/Fuster/Lucca's (NY Fed Staff Report 674, footnote 9).

**So the driver reports the CPR/spread trade-off curve and picks no point on it**, because
picking one would mean inventing the number we do not have. The implausible zero-spread CPR
stays in the output — it is the evidence, and a test asserts it still looks wrong.

### What that costs, measured

| CPR estimate error | spread error |
|---|---:|
| ±2 pp | ±4.8 bp |
| ±5 pp | ±12 bp |
| ±10 pp | ±24 bp |

Slope **2.40 bp per 1 pp of CPR**. So "roughly 220–270 bp at 2009-03-31" **survives not
knowing the CPR**, and the re-pull sharpens the answer rather than unlocking it.

---

## 5. The 2009 CPR is not public, but what drives it is

Searched before asking anyone (2026-09-25). **Not obtainable free:** Ginnie Mae and Fannie Mae
publish pool-level prepayment data but the historical files cover pools still active in 2018
and these had paid off long before; FHFA's Prepayment Monitoring Report series begins in 2014.
A 2009-dated per-pool CPR needs a terminal.

**What is published is the rate that drives it.** `data/mortgage_rate.csv` carries the 30-year
mortgage rate (Freddie Mac PMMS via FRED `MORTGAGE30US`) with source and pull date, and every
priced row carries

```
moneyness = WAC − FRM rate
```

after NY Fed SR 674. Their definition is `coupon + 0.5 − FRM`; the paper says the WAC would be
better but "is not known exactly for the TBA securities studied" — we have it for 490 of 490.

⚠️ **The lookup takes the last survey ON OR BEFORE the valuation date, never the nearest.**
2009-06-10 is one day before the 06-11 print; taking the nearest would price the book at a
rate the market had not yet seen. Pinned by a test.

### ⭐ And it produced a cross-sectional check

```
@3-31 (FRM 4.85%)   OTM 178 | ATM 165 | 217 | 274 | deep ITM 296 bp   (n = 14/41/163/187/73)
@6-10 (FRM 5.29%)   OTM  76 | ATM 104 | 150 | 194 | deep ITM 218 bp   (n = 32/76/215/125/30)
```

**Spread rises monotonically with moneyness on the ITM side at BOTH dates**, over a 130 bp
range — from one pension fund's custodian prices and a static engine, using no dealer quote
and no prepayment model. That is the ITM half of the OAS smile SR 674 documents from fifteen
years of quotes across six dealers.

⚠️ **The OTM upturn is NOT robust and must not be reported as a reproduced smile.** Fourteen
securities at one date, reversing at the other. (It was overstated once before the second date
was checked.)

⚠️ **The 12 pools whose income rate exceeds their WAC are the as-of warning made concrete.**
The investor cannot receive more than the borrowers pay. These are FHLMC ARM pools (`1A`/`1B`/
`1J`/`78xxxx` prefixes) where the 2026 WAC has **reset** since 2009 — for an adjustable pool
the WAC is not a slowly drifting quantity, it is an unrelated one. Named, not patched.

---

## 6. TBA — the pool engine seen through a settlement date

29 to-be-announced forwards, 27 priced at 3-31 (median **+237.0 bp at CPR 25%**), par
**2.84bn**. The custodian carries them at full value — `MV/(par×BT/100)` = 1.000000 on 29 of
29 — so reproducing BT is the same job as for a cash pool, with one difference:

```
F = PV_t0(cash flows beginning at t1) / DF(t0, t1)
```

using the valuation-date curve only. **At zero settle the wrapper delegates to the spot path**,
so it reduces bit-for-bit; an independently written zero branch is how two paths start to
disagree.

Assumptions, each measured rather than argued:

| assumption | worth |
|---|---:|
| gross WAC, coupon+0.50 vs +1.00 | **0.1 bp** |
| settlement day (SIFMA 2009 calendar unavailable; the 15th is used) | ~4 bp per 10 days |
| CPR, over the plausible range | ~21 bp |

⭐ **The WAC being worth 0.1 bp is why the pull's 2026-dated WAC is harmless here**: a
360-month pool barely amortises in its early years, so the flows are interest at the net
coupon (known exactly) plus prepayment.

⚠️ **The control date caught a settlement bug a single valuation date never would.**
`settlement_date` rolled the year when the settle month had passed — correct for a December
valuation quoting January. The holdings file is a **2009-03-31 snapshot**, so at the 06-10
control "SETTLES APRIL" became April **2010** and a contract that had delivered two months
earlier was priced as a forward fourteen months out. Plausible number, no error. The roll is
gone; 27 are named `tba-already-settled` at the control date.

Term parsing needed **both** the description and the master and neither alone: three
securities carry `Income rate = 0.000` while their description states a coupon, several
descriptions omit the percent sign, the fixed-width fields run together
(`30 YEARSSETTLES APRIL`, no boundary before SETTLES), and `desc_short` can END on the word
SETTLES with the month in `desc_long` — searching the joined string returned **"GNMA" as a
month**. Searched per field now, on the bare month name. Coverage 19/29 → **27/29**.

---

## 7. Where the code lives

```
core/pricing/prepayment.py     was pricing/mbs.py, spliced (sha 45a0ef7d…), 2026-09-25
assets/securitized/pool.py     per-metric surface; implied_cpr_pct is the primary calibration
assets/securitized/tba.py      the forward
assets/securitized/bonds_input.py   its OWN numbering 1-11; every `external` is "-"
dataio.phase2._route_pool      structure classification + POOL_ROUTE
scripts/pool_risk.py           the driver
scripts/mbs_data_check.py      regenerates the data check
```

⭐ **The migration was done at the only risk-free moment there will be.** Every earlier
migration had to hold production CSVs byte-identical; this one had no driver and no hashed
output yet, so there was nothing to hold. That window closed the day the driver was written.

**No MBS endpoint type.** Same 7/5/5 decision as ILB: the worksheet has no pool cells and
Mario has not chosen a layout. `contracts.py`, `schema_version` and the `.bas` are untouched.

---

## 8. State and open items

**505 priced + 377 named = 882 at 2009-03-31** (478 + 404 at the control date, the difference
being the settled TBAs). **594 tests.** `release_facts` extended to 17 artifacts on 09-26.

⚠️ **The spreads here carry a prepayment assumption and are not final.** They should not go
into an investor-facing document as point estimates.

Asked of Mario 2026-09-26, both unanswered:

1. Re-pull `MTG_GEN_CPR_3M/6M/12M` **with a 2009-03-31 as-of override**, and drop the invalid
   mnemonic. Sharpens rather than unlocks.
2. **Deal-level structure data for the ~756 tranche securities** — a different kind of request
   from the field pulls, and probably a cost decision.
