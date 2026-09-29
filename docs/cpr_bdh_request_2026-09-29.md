# Prepayment speeds at the 2009 valuation dates — Bloomberg request

**For:** Liping (university terminal) · **Date:** 2026-09-29
**Files:** `outputs/cpr_bdh_pilot.csv` (5 rows — **run this one first**) ·
`outputs/cpr_bdh_template.csv` (505 rows) ·
`outputs/cmo_structure_probe.csv` (3 × 5 questions, separate topic, ~5 min)
**Regenerate:** `PYTHONPATH=src python scripts/make_cpr_request.py`

---

## In one paragraph

We already have these fields — they came back in the July pull. The problem is that they
came back **as of the pull date**, and we are pricing a book at **2009-03-31**. A prepayment
speed is the single largest driver of a mortgage bond's value, so a 2026 speed on a 2009
valuation is not an approximation, it is the wrong number. `BDP` can only return the current
value; reaching a historical one needs `BDH`. That is the whole request: **the same field on
the same securities, re-dated.**

The list is **505 securities, not 882** — see "what we are *not* asking for" below.

| | July pull | this request |
|---|---:|---:|
| securities | 882 | **505** |
| fields | 8 | 3 |
| dates | current only | 2 |
| data points | 7,056 | **3,030** |

---

## Run the 5-row pilot first

`outputs/cpr_bdh_pilot.csv`. This is not a sample — each row answers a different question,
and together they take about a minute.

**Why it exists:** the July pull came back **complete and unusable**. Every value was as of
the pull date rather than the valuation date, and one of the eight field names did not exist
at all. Both were visible in the first row. Neither was noticed until all 882 had been
pulled. Five rows would have caught both, so five rows come first this time.

Each row carries four columns asking the same thing four ways:

| col | formula | what it tells us |
|---|---|---|
| **E** | `BDP(…,"MTG_GEN_CPR_3M")` | today's value — the baseline to compare against |
| **F** | `BDH(…, 20090331, 20090331, "Dts=H","cols=1;rows=1")` | a single day, laid out as one cell |
| **G** | `BDH(…, 20090301, 20090331, …)` | the whole month, in case a single day misses |
| **H** | `BDH(…, 20090331, 20090331)` | no layout options — shows the raw array shape |

**⭐ The acceptance test, and it is quantitative.** These pools are seasoned and burnt out:
today they run at a **median 8.3% CPR** (tightly clustered, 7.2–11.7 across the book). At
2009 the same collateral sat a **median 1.53pp in the money** — WAC above the prevailing
30-year rate — in the middle of a refinancing wave. A 2009 speed should be **several times
today's**, plausibly 20–40%. So:

> **If column F reads ≈8% like column E, the date did not apply.** That is the July failure
> repeating, and it is visible without leaving the sheet.

Three things the pilot settles that cannot be settled away from a terminal:

1. **Does a single-day range return anything?** CPR is published **monthly** against a
   factor date, so 2009-03-31 to 2009-03-31 may fall between publications and come back
   empty. If **F is blank and G has a value**, we switch the whole request to the month form
   and nothing else changes.
2. **How does the answer lay itself out?** `BDH` returns an array. The `Dts=H` and
   `cols=1;rows=1` options are meant to suppress the date column and hold each answer to a
   single cell — otherwise 505 rows each spill into their neighbours. ⚠️ **We have not
   verified that spelling at a terminal**; column H shows the unsuppressed shape so the two
   can be compared side by side. If our spelling is wrong, whatever you find that works is
   the right one — the template is one regenerated file.
3. **Does the history reach a security the current field cannot?** Row 2 is a pool that
   **paid off years ago**. ⚠️ Bloomberg does not blank a dead pool's CPR, it **freezes** it
   at whatever it last was — 215 of our 221 dead pools still return a number, and a frozen
   number is indistinguishable from a live one. (The July check hit the same freezing
   behaviour on WALA from the other direction.) If F differs from E on that row, the date
   reached back past the payoff, which is the strongest single confirmation on the sheet.

If a row is simply blank everywhere, that is a fine answer too — please leave it blank
rather than substituting anything. **A gap we can see costs us far less than a number we
cannot trust**, and every one of these has a documented fallback on our side.

---

## The main request

`outputs/cpr_bdh_template.csv` — 505 rows, columns A–D identify the security (column **D**
is the `<cusip> Mtge` ticker the formulas reference), columns E–J are the six asks:

| field | 2009-03-31 | 2009-06-10 |
|---|:-:|:-:|
| `MTG_GEN_CPR_3M` | ✓ | ✓ |
| `MTG_GEN_CPR_6M` | ✓ | ✓ |
| `MTG_GEN_CPR_12M` | ✓ | ✓ |

**Both dates, please.** 2009-03-31 is the valuation date the whole project is built on;
2009-06-10 is the control we run everything against. The control is not ceremony — it caught
a real settlement-date bug in this same mortgage work last week that was invisible at a
single date.

**All three tenors.** The 3-month is the one the pricing uses; the 6- and 12-month give the
trend (a speed that is accelerating prices differently from one that is flat) and act as a
fallback where the 3-month is thin.

**Units:** whatever the terminal gives, unconverted — we will read them as percent per annum
(so `24.5` = 24.5% CPR) and will check that against the values you send. Please don't
rescale anything.

---

## What we are **not** asking for, and why

* **WAC / WAM / WALA are not re-pulled.** The July values are as of 2026, and for WAC that
  turns out not to matter: measured on this book, a **0.50pp error in WAC moves the
  calibrated spread by 0.24 bp at the median and 0.87 bp at the worst**. Not worth your
  time. (WAM is different, but we reconstruct it from the custodian file rather than from
  Bloomberg.)
* **The 344 REMIC / CMO / IO / PO tranches are not in *this* request** — a prepayment speed
  alone prices none of them, because their cash flows are set by each deal's own waterfall.
  ⭐ **They have their own five-minute sheet instead** (`cmo_structure_probe.csv`, below);
  an earlier draft of this note dropped them entirely, which was wrong.
* **`MTG_HIST_COLLAT_CPR_LIFE` is not in this request.** It was in the July one and returned
  "Invalid Field" on every security. That was our error, not a data gap, and we are not
  repeating it.

---

## ⭐ A separate five-minute sheet: the 344 structured tranches

`outputs/cmo_structure_probe.csv` — **3 securities × 5 questions.** Questions to answer at
the terminal, not formulas to run.

**Why it exists.** Our own handoff says the deal structure behind these is *"a purchase
decision (Intex, **or Bloomberg CMO analytics**)"* — and then the first draft of this note
told you the tranches were a conversation for Mario. One of the two sources we named was
the terminal you are already sitting at, and we did not ask it. That was our oversight.

**The question is narrower than it first looks.** Bloomberg will not hand over a waterfall
— the payment rules live inside its analytics, not in any field. But a waterfall's *job* is
to produce a cash flow schedule, and **if the terminal will give us that schedule for our
tranche, we never need the rules.** We discount the vector on our own curve and solve for
the spread exactly as we already do for every other bond in the book. No CMO engine.

⚠️ **We expect the answer to be no**, and that is fine. A projected cash flow is computed
off *today's* collateral state, and dating it back to 2009 is much harder than dating a
stored field — a lot of these deals have paid off since. But a measured *no* is worth five
minutes: the purchase question has been sitting with Mario since 2026-09-26 on the strength
of our reasoning alone, and a *"we checked at a terminal and it cannot do X"* is a much
better thing to put in front of him than *"we think it cannot."*

**Q1 is the deciding one** — can a projection be dated to 2009-03-31 at all? If no, skip
Q2–Q5 and we have our answer.

### What we found on our side while writing this

Three numbers that may save you time, and that argue the structure really is a purchase:

* **344 tranches, but 170 distinct deals — and 144 of those deals contribute only ONE
  tranche to the portfolio.** We hold a single slice of a deal that may have twenty. To run
  the waterfall for our slice you need the *whole* deal, so the requirement is ~170 complete
  deal models, not 344 security records.
* **They are 39% of the class by count but 28.5% by value** ($473M of $1,661M) — real money,
  smaller average positions.
* ⚠️ **The tranche class letter is a per-deal convention, not a standard.** Of the 54 whose
  class token starts with `P`, **29 are PRINCIPAL ONLY strips, not PACs.** So we cannot
  classify these from the description text, which is part of why Q5 is on the sheet.

And one thing that rules out the cheap route: **IO and PO come to exactly 76 each**, which
looked like matched pairs — if we held both halves of a strip, the pair reconstitutes the
underlying pool and prices with the engine we already have. Checked: **we hold both halves
in one deal, and even there the two are not complementary.** That route is closed.

---

## If something looks wrong

Worth thirty seconds before pulling 505 rows: `MTG_GEN_CPR_3M` `FLDS<GO>` at the terminal
shows whether the field is history-enabled and what its date coverage is. If it is not
history-enabled, no `BDH` spelling will work and we need a different field name — in which
case please just tell us what the terminal offers rather than picking one, since guessing a
field name is exactly what cost us the July pull.

Any of this can be regenerated in seconds, so if the shape is inconvenient — different
layout, one date at a time, fewer securities per file — say so and we will send it in
whatever form is easiest to run.
