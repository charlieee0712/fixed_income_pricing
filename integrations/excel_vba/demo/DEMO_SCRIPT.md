# Live demo — run sheet

A five-minute demonstration that a spreadsheet sends one JSON request, Python prices the
bond, and one JSON answer comes back. Everything below has been run end to end on this
machine; the timings are real.

---

## Before the meeting (two minutes, do it once)

```powershell
# 1. rebuild the workbook and its runner for THIS machine
powershell -ExecutionPolicy Bypass -File integrations\excel_vba\demo\Build-DemoWorkbook.ps1 `
    -PythonExe C:\Users\cnc\anaconda3\anaconda2025\python.exe

# 2. prove the whole bridge still works (no Excel window opens)
powershell -ExecutionPolicy Bypass -File integrations\excel_vba\tests\Run-BridgeTests.ps1 `
    -PythonExe C:\Users\cnc\anaconda3\anaconda2025\python.exe      # expect 23/23
```

Then open `RYSE_Pricing_Demo.xlsm` once and click **Price this bond**, so that any
"enable macros" prompt is already dealt with and the first (slightly slower) run is behind
you. A normal run takes **under two seconds**.

> The workbook must sit inside the repository folder, because the engine reads the curve
> files from `data/`. The runner command is the only machine-specific piece; rebuild it on
> any other laptop.

---

## The demo

### 1. Show the sheet (20 seconds)

Yellow cells on the left are the inputs, blue cells on the right are what comes back. Say:

> "There is no pricing logic anywhere in this spreadsheet. It reads these cells, writes one
> request file, runs one command, and puts the answer back. The same engine does the
> production runs."

### 2. Click **Price this bond** (30 seconds)

Everything fills in about a second and a half. Worth pointing at:

- **Implied OAS 523.30 bp** — the extra yield the market is demanding from this borrower,
  once the curve has been accounted for;
- **Effective duration 6.09** — how much the price moves when rates move;
- **Curve used: `USD|2009-03-31|Semiannual`** — every answer says which curve produced it;
- **Volatility: "not used by vanilla…"** — the engine states plainly that it did not use the
  volatility it was given, rather than returning a zero that would look calculated.

### 3. Change the price and click again (40 seconds)

Type **88** into the clean market price and click. The spread jumps to about **635 bp** and
the duration shortens slightly. Say:

> "The spread is solved from the price, not typed in. A lower price means the market is
> demanding more yield, and that is the number the risk system needs."

Put **94.25** back and click again — it returns to 523.30.

### 4. Show what actually crossed the boundary (40 seconds)

Click **Show the request JSON**, and open the file it names. This is Mario's own proposal on
screen: one JSON in, one JSON out. Point out that the date left Excel as `"2017-01-15"` text
and not as the number 42750 — the conversion the bridge does, and the reason a wrong date
cannot slip through silently.

### 5. Break it on purpose (30 seconds)

Type **CHF** into the currency cell and click. You get:

```text
Status   error
Errors   CURVE_NOT_FOUND: no yield curve is configured for currency 'CHF'
         (configured: AUD, EUR, GBP, JPY, KRW, USD)
```

and the numbers **clear** rather than leaving the previous bond's values on screen. Say:

> "It refuses instead of guessing. Pricing a Swiss franc bond on a dollar curve would give a
> wrong number that looks perfectly reasonable — that is the failure worth preventing."

Put **USD** back.

### 6. The volatility answer, in the terminal (60 seconds)

The spreadsheet path prices plain bonds today; callable bonds join it next week. So show
this part from a command line:

```powershell
$env:PYTHONPATH="src"
C:\Users\cnc\anaconda3\anaconda2025\python.exe scripts\demo_volatility.py
```

It prints, for a real holding, both experiments side by side — price at a fixed spread, and
spread at a fixed price, at 10 / 15 / 20% volatility. Say:

> "This is the question you asked. They are two different questions and we answer them
> separately. One volatility point is worth about ten cents of price, or about one basis
> point of spread, on this bond — and on our other two callables it is worth essentially
> nothing, because their call is nowhere near the money."

---

## If something goes wrong

| Symptom | Cause | What to do |
|---|---|---|
| A macro-security bar appears | Excel's normal prompt for a macro workbook | click *Enable Content* once |
| `The pricing runner did not produce a response file` | the runner path is wrong for this machine | re-run `Build-DemoWorkbook.ps1` with the right `-PythonExe` |
| `CURVE_NOT_FOUND … date` | the workbook was moved out of the repository, so `data/` is not found | put it back, or run the runner from the repo root |
| Python is missing on the machine | a borrowed laptop | click **Load a saved answer** and pick `integrations/excel_vba/examples/vanilla_response_v1.json` — the mapping demonstrates without Python |

The last row is the safety net: the whole spreadsheet side can be shown with no Python
installed at all.

---

## What this demo does not claim

- **Plain bonds only, through Excel.** Callable, puttable and sinking-fund bonds price in
  Python today; connecting them to this interface is next week's work, and the terminal step
  above is how they are shown until then.
- **One bond per click.** A portfolio run is a loop over the same call, not a different
  design — but it is not what this sheet does.
- **This is a demonstration workbook.** The authoritative holdings file is never opened for
  writing and has no macros in it.
