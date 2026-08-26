# Weekly report — fixed-income pricing module

**Date:** 2026-08-25 · **Covers:** the work since the code-structure sample was approved

Two things happened this week. First, your three follow-up points on the sample are all
answered and built. Second, three more bond types now price through the restructured code.
Everything that already worked still produces exactly the same numbers — that is checked
automatically, to the last digit, after every change.

This report is written to be read without the code. Section 5 is aimed at the engineering
team; the rest is not.

---

## 1. Where the module stands

The module takes a bond, a market price and an interest-rate curve, and produces the
numbers a risk system needs: what the bond is worth, what extra yield the market is
charging this borrower, and how much the price moves when interest rates move.

| | Where it stands today |
|---|---|
| Bond types priced | plain bonds, callable, puttable, sinking-fund, plus floating-rate and several others already in the engine |
| Automatic checks | **223**, run in about 19 seconds |
| Numbers changed by this week's restructuring | **none** — verified by comparing full output files, digit for digit |
| Ways to run it | directly in Python, from a command line, or **from Excel** |

---

## 2. Your three follow-up points

### 2.1 "Add currency to our input"

Done. Currency is now an explicit input, and it does one specific job: it selects the
interest-rate curve of the bond's **own** currency. A euro bond discounted on a dollar
curve is simply a wrong number that looks like a right one, so if we do not have a usable
curve for a currency, the request is **refused** rather than quietly falling back to
dollars. Six currencies are configured today — USD, EUR, GBP, JPY, AUD and KRW — and a
curve must also exist for the exact valuation date being priced, which is why a request can
come back saying the currency is fine but that date is not available. Both cases are
reported as separate, named reasons rather than as one vague failure.

One clarification worth stating: currency here chooses a pricing curve. It is *not* an
instruction to convert anything — portfolio values stay on the custodian's base-dollar
figures exactly as before.

### 2.2 "What happens if the volatility of yield changes — for OAS and for price?"

This turned out to be two different questions, and they have to be answered separately —
running them together is the usual way this gets reported wrongly:

- **hold the credit spread fixed, change volatility** → what happens to the **price**;
- **hold the market price fixed, change volatility** → what happens to the **spread**.

For a plain bond the answer to both is *nothing at all*, and that is not a shortcut: a
plain bond has no early-repayment right, so there is nothing for volatility to act on. The
module says so explicitly in its output rather than returning a zero, because a zero would
look like a number we calculated.

For a bond the borrower can repay early, the answer is real, and this week it became
quantitative. See section 4.

### 2.3 "Can the team run the Python from Excel — cells to JSON, one JSON in, one JSON out?"

Yes, and it is built and tested end to end. A spreadsheet sends one request file and gets
one answer file back:

```text
Excel cells  →  small VBA bridge  →  request.json
                                          ↓
                                    Python engine
                                          ↓
Excel cells  ←  small VBA bridge  ←  response.json
```

The spreadsheet knows exactly **one** thing about the engine: a command to run. Pointing
that at a packaged program, or later at a web service, changes nothing else — not a field,
not a cell, not a line of the spreadsheet code. There is no pricing logic in the
spreadsheet, and none in the message layer either; both simply carry values to and from the
same engine the production runs use.

We tested it on a real copy of Excel, driving the actual spreadsheet code: **23 checks,
all passing**, including a full round trip where Excel really does call Python and gets a
priced bond back. That exercise immediately earned its keep — it exposed a genuine defect
in which any *failed* request would have shown a technical error box instead of the reason
the bond could not be priced. That is exactly the moment a user most needs the reason. It
is fixed, and the case is now a permanent test.

One safeguard is worth mentioning because it is invisible when it works. Excel stores
31 March 2009 internally as the number 39903. If that number reached the engine it would be
read as a date in 1970, and the bond would be priced on the wrong day, on the wrong curve,
with nothing looking broken. Dates must therefore arrive as text (`2009-03-31`); a bare
number is refused. Converting it is the bridge's job, and that conversion is tested.

---

## 3. Three more bond types, one shared engine

The Monthly sheet lists ten analysis types. Removing the plain bond (already delivered) and
the mortgage item (waiting on data) leaves four families. **Three are now built:**

- **callable** — the borrower may repay early, on set dates, at a set price;
- **puttable** — the investor may hand the bond back early, on set dates, at a set price;
- **sinking fund** — the borrower may retire *part* of the bond early on set dates.

They share **one** engine rather than having one each. The workbook itself makes the case:
fourteen of its rows are bonds carrying two of these rights at the same time. A separate
engine per product cannot price those without copying the other product's code into itself.
One shared engine prices them by construction, and each bond type is a short file that names
its inputs and passes them down — no calculation of its own.

What was proven, stated separately because the evidence differs:

- **Callable** — proven against the live portfolio. The existing engine was *moved*, not
  rewritten, and the new front door reproduces the production calculation exactly, to the
  last digit.
- **Puttable** — no holding in the portfolio is a puttable bond today, so there is no live
  comparison to make. What is tested is that the investor's right behaves as the exact
  mirror of the borrower's. The route exists so a real one prices the day its terms arrive.
- **Sinking fund** — the one genuinely new piece of modelling. It is validated by behaviour,
  including one exact check: retiring *all* of a bond on a date is arithmetically the same
  operation as calling it on that date, and the code produces the identical value.

We should also say what the workbook could **not** give us. For these three families it
holds 474 saved rows, and every one belongs to the March-2010 batch that we established in
August as an unusable stale run — none is in the sound December-2012 batch. So there was no
saved number to reconcile against, and we did not manufacture agreement with the stale ones.
Validation is instead: existing outputs unchanged digit-for-digit, new functions matching
direct calculation exactly, and the economics behaving as they must.

---

## 4. The volatility answer, with numbers

Three corporate bonds price on this engine today — one of them euro-denominated — along
with five agency bonds; a fourth corporate is still waiting on its call terms, which are on
the outstanding data request. Of the three corporates, only one has a repayment right that
is currently worth anything: 6.45% of June 2034, marked at 90.04, repayable at face value
from August 2014.

| Rate volatility | Price, holding the spread at 410.8 bp | Spread, holding the market price at 90.04 |
|---|---|---|
| 10% | 90.4204 | 414.52 bp |
| **15% (our baseline)** | **90.0402** | **410.77 bp** |
| 20% | 89.5138 | 404.84 bp |

In round terms: **one volatility point is worth about ten cents of price, or about one
basis point of spread**, on this bond.

Both directions are what the economics require. If rates are expected to move around more,
the borrower's right to repay early is worth more, so the bond is worth less to us. And if
the market price is *not* moving, then more of that same discount is explained as the cost
of that right and less of it as credit risk — so the credit spread comes in.

The other two make the opposite point, and it matters: both are priced far
away from their repayment price (one is marked at 60), so their early-repayment right is
nowhere near worth using, and volatility moves them by **less than a tenth of a basis
point**. A single portfolio-level volatility sensitivity would have averaged that away
completely. The answer is per-bond, and the module reports it per-bond.

For a bond with an investor's right instead, every sign flips: the price rises with
volatility and the spread widens.

---

## 5. For the engineering team

The structure follows the template: reusable mathematics in `core/`, thin per-bond-type
wrappers in `assets/`, and a transport layer in `endpoints/` that does no arithmetic.

**One entry point.** `analyze_vanilla_payload(request) → response` takes a plain dictionary
and returns a plain dictionary. It never raises: failures come back as a response with a
status and a reason. Whatever carries the message — a file today, an HTTP request later —
calls that same function. There is no second pricing implementation to keep in step, and a
test enforces it: every number the interface returns must equal the direct function call
**exactly**, compared with `==` rather than a tolerance.

**Deterministic across platforms.** The same request produces byte-for-byte identical
output on Windows (Python 3.13, NumPy 2.3) and on the Linux server (different Python,
different NumPy). We checked the full response file, not a rounded summary. That matters
for a move to the cloud: results are reproducible, so they can be cached, replayed and
compared safely.

**Parallel by construction.** Every pricing function is pure — no shared state, no
globals, one bond per call. A portfolio is an embarrassingly parallel workload; nothing in
the design has to change for that.

**Running it.**

```text
python -m pytest -q                       223 checks, ~19 seconds
python scripts/price_json.py --input request.json --output response.json
powershell -File integrations/excel_vba/tests/Run-BridgeTests.ps1    23 Excel checks
```

**Reference documents in the repository:** the field-by-field interface contract, the Excel
bridge how-to with worked request/response examples, and the fifteen-minute guided tour of the
code for the walkthrough.

**What the interface is strict about, and why:** dates must be text, not spreadsheet serial
numbers (a silently wrong date is the worst failure available here); prices are always
quoted per 100 face; the operation that calibrates a spread from a market price will not
also accept a hand-typed spread, because the two can disagree and there is no right way to
choose between them. Everything else is forgiving — lower-case currency, numbers as text,
missing optional fields, unknown extra fields — with a warning rather than a rejection.

---

## 6. What we deliberately did not do

- **No bond was reclassified on a flag alone.** A sinking fund is an *option* to retire debt
  early; an amortising bond simply repays principal on a fixed schedule. They are different
  products and the portfolio's `Sinking = Yes` field does not distinguish them, so nothing
  was moved into the new engine on the strength of it.
- **Convertible bonds stay out.** One workbook row carries conversion rights; pricing it
  properly needs an equity model we do not have, and approximating it would be worse than
  leaving it flagged.
- **Contradictory terms are refused, not guessed.** If terms imply an investor can hand a
  bond back above the price at which the borrower can repay it, both cannot be true; the
  module stops and says so.
- **Mortgages remain their own phase**, still waiting on the data pull.

---

## 7. Next week

- **Floating-rate notes** — the fourth family from the Monthly sheet (items 7 to 9). It was
  deliberately held back: this week's headline is the volatility answer, which is entirely
  about bonds with early-repayment rights, and a floating-rate note has no volatility input
  at all. Holding it back also kept the attention on the one genuinely new piece of
  modelling.
- **Connecting the new bond types to the Excel/JSON interface** — done once, next week, so a
  single change covers callable, puttable and floating together rather than two changes.

## 8. Two questions for you

1. **Which workbook should carry the Excel demonstration?** We will not touch the
   authoritative holdings file; a small demonstration workbook is what we have in mind
   unless you would rather it lived somewhere specific.
2. **Is the rollout order still right?** Floating next, then the remaining families, with
   mortgages waiting on data — that is what we are working to unless you want it changed.
