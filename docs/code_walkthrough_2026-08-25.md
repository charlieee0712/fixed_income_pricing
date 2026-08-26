# Code walkthrough — 15 minutes

*Speaking aid for the session with Mario and the engineering team, 2026-08-25. Supersedes
the 2026-08-17 version, which covered only the plain-bond chain. Everything claimed below
is backed by the automatic suite: **223 checks, about 19 seconds**.*

**Opening line:** "The code is organised so that the mathematics lives in one place and each
bond type is a short file that just names its inputs. Everything from the August sample
still produces identical numbers — and there are now three more bond types and two ways to
call it from outside Python. Here is the tour."

---

## The tour, in order

### 1. `src/pricer/__init__.py` — the map (30 seconds)

Three layers, and the split is the point:

```text
core/       the mathematics, shared by every bond type      (~80% of the code)
assets/     one short file per bond type, no arithmetic     (~20%)
endpoints/  the outside world: one request in, one result out
```

Say: *"If you only remember one thing — a new bond type is a new file in `assets/`, not a
new engine."*

### 2. `assets/corporate/` — one file per bond type (3 min)

Open `vanilla.py`, then `callable.py`. They look the same on purpose: one simple function
per output, the same names the legacy Monthly sheet uses.

```text
calculated_price   implied_oas   duration   dv01   convexity   widening   tightening
```

Then point at what differs: `callable.py` takes a **call schedule**, `puttable.py` a **put
schedule**, `sinking.py` a **redemption schedule**. Nothing else changes — and none of those
files does any arithmetic; they convert units and pass the terms down.

Open one function to show the numbered `Inputs` block with units in capitals — this layer
speaks the legacy sheet's units (coupon in PERCENT, prices per 100, spreads in BASIS
POINTS); the engines underneath work in decimals.

**For the engineers:** every one of these is a pure function — no state, no globals, one
bond per call. A portfolio is embarrassingly parallel with no design change.

### 3. `core/pricing/tree.py` — one engine, three products (4 min)

This is the heart of the new work. A callable, a puttable and a sinking-fund bond are the
same calculation with a different right attached:

```text
call right   the issuer caps the value at the call price      min(value, price)
put right    the holder floors it at the put price            max(value, price)
sinking      the issuer retires a fraction f at the price     (1-f)·value + f·min(value, price)
```

Worth saying out loud: **at f = 1 the sinking rule *is* the call rule** — and the code
produces the identical value to the last bit, which is one of the tests.

Why one engine and not three: fourteen rows in the workbook carry two rights at once
(`CALL/SINK`, `CALL/PUT`). Three separate engines could not price those without copying each
other.

If asked how the tree is built: it is calibrated so that it reprices the input curve's own
discount factors exactly — arbitrage-free by construction, not by assumption.

### 4. `core/` — the rest, bottom-up (3 min)

- `utils/dates.py` — the calendar. One year is 364 days, one half-year 182. That is the
  legacy system's own convention, kept deliberately; changing it would break every validated
  number.
- `pricing/cashflows.py` — the cash-flow table and **the one** accrued-interest formula that
  every engine shares.
- `pricing/discounting.py` — the corrected discounting that reprices a curve's own par bonds
  to exactly 100.
- `pricing/analytical.py` — the plain-bond price: dates → cash flows → discount → sum.
  About 25 lines of orchestration.
- `risk/sensitivities.py` — duration, DV01, convexity as pure arithmetic on three prices.
  Point it at *any* pricing function; the tree uses the same one.
- `market/curves.py` — `resolve_curve(currency, date, frequency)`: the one place a bond gets
  its own-currency curve, and the one place a missing curve is refused rather than
  substituted.

### 5. `endpoints/` + `integrations/excel_vba/` — calling it from outside (3 min)

```text
Excel cells → VBA bridge → request.json → analyze_vanilla_payload() → response.json → cells
```

`endpoints/main.py` is one function: a dictionary in, a dictionary out, and it never raises
— failures come back as a status and a reason. `contracts.py` is the request/response shape,
standard library only. `pricing.py` arranges the calls. **No formula anywhere in this layer.**

Two things to demonstrate if there is time:
- `integrations/excel_vba/examples/` — a real request and the real response it produced;
- `Run-BridgeTests.ps1` — 23 checks driving actual Excel, including a live call into Python.

**The line that matters for the cloud move:** the spreadsheet knows one setting, a command
to run. Point it at a packaged executable or an HTTP service and nothing else changes.

### 6. Proof, then close (2 min)

- `src/pricing/*.py` — the old module paths are now thin shims. Every existing script,
  driver and test still works unchanged.
- Migration safety: production output files are compared **by cryptographic hash** before and
  after every change. Identical, three times over.
- `tests/test_pricer_tree_structure.py` — the interesting ones: the new wrapper equals the
  production calculation with `==`; a bond with no rights prices exactly as a plain bond;
  callable ≤ plain ≤ puttable.

---

## Numbers to have ready

| Claim | Number |
|---|---|
| Automatic checks | **223** in ~19 s (194 before this round) |
| Behaviour change from the restructuring | **zero** — production CSVs hash-identical |
| Excel bridge | **23/23**, on real Excel, including a live Python round trip |
| Cross-platform | response file **byte-identical** on Windows and Linux |
| Volatility, call-active bond | ~10 cents of price, or ~1 bp of spread, per vol point |

---

## Likely questions — answers ready

- *"Why 364-day years?"* — the legacy engine's own convention. We keep it so every number
  reconciles. Real day-count labels are carried as data and can drive a future layer.
- *"Why is a callable bond's duration shorter?"* — the issuer's right to repay caps how much
  the price can rise when rates fall, so the bond moves less.
- *"Can we price a bond that is both callable and sinkable?"* — the engine can hold both sets
  of terms. Where the two land on the same date we currently refuse, because the order of the
  two rights changes the answer and no order is tested yet. That is a deliberate boundary,
  not a gap in the mathematics.
- *"Why refuse instead of assuming?"* — every refusal in the code is a case where a silent
  assumption would produce a plausible wrong number: a missing curve, a spreadsheet date sent
  as a number, terms that contradict each other.
- *"How would this scale to a whole portfolio in the cloud?"* — pure functions, one bond per
  call, deterministic across platforms, and one entry point that any transport can wrap.
- *"What is not built yet?"* — floating-rate notes go through the same pattern next week;
  mortgages wait on the data pull; convertibles need an equity model we do not have.
