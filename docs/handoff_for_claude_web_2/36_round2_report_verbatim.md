# Round 2 — callable, puttable and sinking-fund bonds on one shared engine

**Date:** 2026-08-25 · **Covers:** Monthly `Q62:Q71` items 2, 3, 4, 5 and 6 ·
**Status:** built, tested, and running against the live portfolio with no change to any
existing number

---

## 1. What we built

Three more bond types now price through the restructured code, and they share **one**
engine rather than having one each:

```text
                                   ┌─ callable      (issuer can retire the bond early)
   one interest-rate tree  ────────┼─ puttable      (holder can sell it back)
                                   └─ sinking fund  (issuer can retire part of it)
```

The three differ only in *whose* right it is and *how much* of the bond it covers. That is
a difference in the terms you feed in, not a difference in the mathematics — so they are
one engine with three thin front doors, each front door offering the same simple, named
functions the Monthly sheet asks for:

```text
calculated_price   implied_oas   duration   dv01   convexity   widening   tightening
price_at_volatility   implied_oas_at_volatility   volatility_sensitivity
```

The floating-rate note (`Q68:Q70`) is deliberately **next week's** work — see §6.

## 2. Why this shape

The alternative was four separate pricing engines, one per product name on the sheet. We
did not do that, for a reason the sheet itself supplies: fourteen rows in the workbook are
`CALL/SINK` or `CALL/PUT` — bonds carrying **two** rights at once. A per-product engine
cannot price those without copying the other product's code into itself. One shared engine
prices them by construction.

It also keeps the promise from the August restructure: the reusable mathematics sits in
`core/`, and each bond type is a short, readable file that names its inputs and passes them
down. Nothing in the callable, puttable or sinking files does any arithmetic.

## 3. What was proven, per family

**Callable — proven against the live portfolio.** The existing engine was *moved*, not
rewritten: the numerical code was copied byte-for-byte into its new home. We froze the
output of all three production drivers before the move and re-ran them after, three times
during the round; the files are identical to the last digit each time (checked by
cryptographic hash, not by eye). The new callable front door reproduces the existing
production calculation exactly — the same floating-point value, not a close one.

**Puttable — proven on the shared engine, honestly labelled.** No holding in the portfolio
is currently a puttable bond, so there is no production cohort to compare against. What is
tested is that the engine treats the holder's right as the exact mirror of the issuer's: a
puttable bond is never worth less than the same bond without the right, its duration is
shorter, and its price *rises* with volatility where a callable's falls. The route exists so
that a real puttable prices the day its terms arrive, with no new engine.

**Sinking fund — a new capability, validated on constructed examples.** This is the only
genuinely new modelling in the round. It is validated by behaviour rather than by a
reference number, including one exact anchor: retiring 100% of the bond at a price on a
date is arithmetically the same operation as calling it at that price on that date, and the
code produces the identical value to the last digit. Retiring 0% gives the plain bond;
value falls smoothly as the redeemable share rises; the spread solves and re-prices back to
the input.

**No numeric target existed for any of the three.** The workbook holds 474 rows for these
families and every one of them belongs to the March-2010 batch we established in August as
an unusable stale session. Not one sits in the sound December-2012 batch. We say this
plainly because the tempting mistake would have been to tune the new code until it matched
those saved values.

## 4. Your volatility question, answered

You asked what happens to price and to OAS when yield volatility changes. Those are two
different questions, and the code now answers them separately — conflating them is the
usual way this gets reported wrongly:

- **hold the spread fixed, move volatility** → what happens to the **price**;
- **hold the market price fixed, move volatility** → what happens to the **OAS**.

On the portfolio's one genuinely call-active holding (6.45% of June 2034, marked 90.04,
callable from August 2014 at par):

| Volatility | Price at a fixed 410.77 bp | OAS at the fixed market price |
|---|---|---|
| 10% | 90.4229 | 414.52 bp |
| **15% (our baseline)** | **90.0426** | **410.77 bp** |
| 20% | 89.5161 | 404.84 bp |

Roughly, **one volatility point costs about 10 cents per 100 of price, or about 1 bp of
spread** on that bond. Both move in the direction the economics require: higher volatility
makes the issuer's right to call more valuable, so the bond is worth less — and if the
market price is not moving, then more of that same discount is the cost of the call and
less of it is credit, so the credit spread tightens.

The answer is bond-specific, and the other two callables show why that matters: both are
priced far from their call price (one is marked at 60), so their call is nowhere near worth
exercising and volatility moves them by **essentially nothing** — under a tenth of a basis
point. A single portfolio-level "volatility sensitivity" number would hide that completely.

For a bond with a *put*, every sign flips: the holder's right gains value, so the price
rises with volatility and the spread widens.

## 5. What we did not do, on purpose

- **No pass-through or amortising bond was reclassified.** A sinking fund is an *option* to
  retire early; an amortising bond simply repays principal on a fixed schedule. They are
  different products, and the portfolio's `Sinking = Yes` flag does not distinguish them. No
  holding was routed into the new engine on the strength of that flag; the securities
  waiting on schedules from Bloomberg are exactly where they were.
- **Convertibles stay out.** One workbook row is `CONV/PUT/CALL`. Its put and call rights
  alone do not price a convertible — that needs an equity model we do not have.
- **Contradictory terms are refused rather than guessed.** If terms say a bond can be put
  back above the price at which the issuer can call it, both cannot be true; the code stops
  and says so instead of silently picking one.
- **Mortgages remain their own phase**, waiting on the data pull.

## 6. Next week

The floating-rate note (`Q68:Q70`) moves to next week, together with connecting these new
bond types to the Excel/JSON interface delivered in the last round. The reason for
splitting it that way: the volatility question above is entirely a story about bonds with
options, and a floating-rate note has no volatility input at all — so keeping them together
would have added a fourth family without adding anything to the answer, while the one piece
of genuinely new modelling (the sinking fund) deserved the attention. Doing the interface
work once, next week, also means a single change covering every new bond type rather than
two.

## 7. In one line

The restructured code now prices bullet, callable, puttable and sinking-fund bonds through
one shared engine and one consistent set of named functions; every number that existed
before is unchanged to the last digit; and your volatility question has a concrete, signed,
per-bond answer.
