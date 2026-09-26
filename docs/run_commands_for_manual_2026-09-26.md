# Running the pricing system — one command per asset class

For the manual document. Covers every class completed **before** the mortgage book: corporate,
government, municipal, agency, guaranteed and index-linked. Mortgage-backed is at the end,
marked separately, because it landed this week and its numbers are not final.

Everything runs on server 47 from the repo root, `/home/PengSX/fixed_income_pricing`.
Each command is self-contained — no state carries between them.

---

## 1. The four commands

**The valuation date is always given explicitly.** The drivers do not agree on a default
(one is 2009-06-10, the rest 2009-03-31), so leaving it out is the easiest way to produce a
file that looks right and is dated wrong. **2009-03-31 is the baseline**; 2009-06-10 is the
control date we re-run everything against.

### Corporate bonds — 732 securities, 566 in the output

```bash
FIP_VAL_DATE=2009-03-31 FIP_OUT=outputs/implied_oas_2009-03-31.csv \
  PYTHONPATH=src python3 scripts/calibrate_risk.py
```

### Corporate callables — the binomial tree, 3 priced

```bash
FIP_VAL_DATE=2009-03-31 FIP_VOL=0.15 \
  PYTHONPATH=src python3 scripts/callable_risk.py
```

⚠️ This one writes `outputs/callable_risk.csv` with **no date in the filename**, so running
the control date afterwards overwrites the baseline. Add `FIP_OUT=…` if you need both.
`FIP_VOL` is the short-rate volatility — 0.15 is Mario's v1 choice, and it is an assumption
rather than a market quote.

### Government and municipal bonds — 154 securities

```bash
FIP_VAL_DATE=2009-03-31 \
  PYTHONPATH=src python3 scripts/sovereign_risk.py
```

### Agency, guaranteed and index-linked — 63 securities

```bash
FIP_VAL_DATE=2009-03-31 FIP_OUT=outputs/phase2_risk_2009-03-31.csv FIP_INFL=0.0 \
  PYTHONPATH=src python3 scripts/phase2_risk.py
```

`FIP_INFL` is the inflation assumption for the index-linked bonds, as a decimal. At 0 the
calibrated spread is minus the market breakeven, which is why the output reports a breakeven
column rather than a credit spread.

### One bond at a time — the interface Excel and the browser both call

```bash
PYTHONPATH=src python3 scripts/price_json.py \
  --input  integrations/excel_vba/examples/vanilla_request_v1.json \
  --output /tmp/response.json
```

One JSON in, one JSON out. Exit code 0 priced, 1 refused *with a readable reason still
written to the output file*, 2 the files themselves could not be read. Nine worked examples
live in `integrations/excel_vba/examples/`.

---

## 2. Which command covers which kind of bond

This is probably the more useful table for the manual: the drivers are organised by the
portfolio's asset classes, but the modelling is organised by **product type**, and one command
covers several. Counts are from the 2009-03-31 run.

| Product type | Command | Engine | Count |
|---|---|---|---:|
| Plain fixed-rate | `calibrate_risk.py` | discounted cash flows, ACT/364 | 481 |
| Make-whole callable (priced as plain) | `calibrate_risk.py` | same — the call is worth ~nothing | 47 |
| Stepped / step-up / zero | `calibrate_risk.py` | dated coupon table | 10 |
| Fixed-then-floating | `calibrate_risk.py` | fixed leg + floating leg on one curve | 10 |
| Floating-rate | `calibrate_risk.py` | forward projection + margin | 7 |
| Defaulted | `calibrate_risk.py` | recovery mark, no spread | 3 |
| **Callable / puttable / sinking** | `callable_risk.py` | **binomial short-rate tree** | 3 |
| Sovereign fixed-rate | `sovereign_risk.py` | discounted cash flows, own-currency curve | 120 |
| Sovereign zero / STRIPS | `sovereign_risk.py` | single discounted payment | 31 |
| Callable Treasury | `sovereign_risk.py` | binomial tree | 1 |
| Agency / guaranteed fixed | `phase2_risk.py` | discounted cash flows | 36 |
| **Index-linked** | `phase2_risk.py` | **nominal curve × index ratio path** | 14 |
| Agency callable | `phase2_risk.py` | binomial tree | 5 |
| Agency call passed | `phase2_risk.py` | priced as a bullet, flagged | 4 |
| Agency STRIPS | `phase2_risk.py` | single discounted payment | 2 |

Every security that is **not** priced carries a named reason in a companion
`*_disposition_<date>.csv`, one row per security. Nothing is silently dropped, and the
counts reconcile — that file is the evidence.

---

## 3. Mortgage-backed — this week's work, numbers not final

```bash
FIP_VAL_DATE=2009-03-31 \
  PYTHONPATH=src python3 scripts/pool_risk.py
```

882 securities: 490 pass-through pools and 29 to-be-announced forwards reach the engine,
505 carry numbers. The remaining 344 are tranches of structured deals (CMO, REMIC, and the
interest-only / principal-only strips) whose cash flows depend on each deal's own waterfall —
that data is not in any field-level pull, so they are named rather than priced.

⚠️ **The spread numbers here carry a prepayment assumption and should not go into the manual
as final.** The Bloomberg pull came back as of the pull date rather than 2009, so the output
reports a range across three prepayment assumptions instead of one number.

---

## 4. On your FRN question — do we use a forward curve?

**Yes, we project forward rates. But there is no separate forward curve.**

A floating-rate bond resets its coupon every period, so to price one you have to know what
those future coupons will be. We do not guess them — they are implied by today's curve. If you
know today's one-year rate and today's two-year rate, then the one-year rate *starting a year
from now* is already pinned down: any other value would let somebody borrow at one and lend at
the other for a riskless profit. That implied number is the forward rate, and it is what each
future coupon is built from.

The part worth stressing is that it comes out of **the same curve we discount with**. One
curve does both jobs:

```
future coupon  =  forward rate implied by the curve  +  the bond's quoted margin
discounting    =  the same curve, plus the spread we solve for
```

In the code: `core/pricing/floating.py` — `simple_forward()` defined on line 80, used on line
148 for the coupon and line 150 for the discount factor, with literally the same curve object
passed to both.

### Why one curve and not two

After 2008 the market moved to **two** curves — discount on one, project coupons off another —
because the crisis made it plain that the rate banks lend to each other at is not the same
thing as a risk-free rate.

We use one, for two reasons. Our valuation date is **March 2009**, when single-curve was still
the convention; and the legacy system we are reproducing does exactly this, which we confirmed
against its floating-rate tree during the reconciliation work. So it is a match to the period
rather than a simplification. Moving to two curves is written up in the code as a future
enhancement, so nobody later mistakes it for an oversight.

### Two details that may earn a line in the manual

**The first coupon period starts at the bond's last reset, not at the valuation date.** A
floater's current coupon was fixed at the previous reset, which is in the past. Starting that
period at the valuation date would treat a coupon that has already been set as if it were
still floating. The check that catches it: a floater trading at par should be worth par no
matter how you shift the curve — get this wrong and that stops holding.

**A floater's duration is short, and that is the whole point of the instrument.** For an
ordinary bond, duration is roughly its maturity. For a floater it is not: when rates rise the
coupon rises with them, so the price barely moves. Duration lands near the time to the **next
reset** instead — a thirty-year floater can have a duration of a few months. We get that by
shifting the *curve*, so the coupons re-project along with it, rather than by shifting the
spread; shifting the spread would leave the coupons frozen and give a long duration, which
would be the wrong answer for the right-looking reason.
