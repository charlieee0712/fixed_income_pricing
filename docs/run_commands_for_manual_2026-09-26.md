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

**Yes for the projection, but there is no second curve.**

A floating-rate bond's future coupons are projected as implied forwards taken off the *same*
zero curve we discount with:

```
F(t0, t1)  =  ( DF(t0) / DF(t1) − 1 ) / (t1 − t0)        simple, not compounded
coupon     =  F(t0, t1) + the quoted margin
discount   =  the same curve, plus the bond's calibrated spread
```

In code: `core/pricing/floating.py`, `simple_forward()` at line 80, used at line 148 for the
coupon and line 150 for the discount factor — the same `curve` object both times.

**This is a single-curve framework, and that is deliberate.** The modern convention is
dual-curve: discount on OIS, project on a separate LIBOR curve. We use one curve for both
because that was the market convention at the 2009 valuation date, and because the legacy
VBA system we are reproducing does exactly this — we confirmed that against its floating-rate
tree during the reconciliation work. Moving to dual-curve is a documented future enhancement,
not an oversight, and it is written into the module docstring so nobody has to re-derive why.

Two details worth having in the manual:

* **The first coupon period starts at the bond's true last reset**, which is before the
  valuation date. Getting this wrong breaks the property that a par floater prices at par
  under any curve shift — which is the test we use to check the engine.
* **Effective duration bumps the curve, not the spread**, so the coupons re-project and the
  duration comes out near the time to the next reset rather than near the maturity. That is
  the signature behaviour of a floating-rate note and the reason its duration is short even
  on a thirty-year bond.
