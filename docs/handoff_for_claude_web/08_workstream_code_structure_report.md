<style>
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; font-size: 10.5pt; line-height: 1.5;
       max-width: 19cm; margin: auto; color: #1a1a1a; }
h1 { font-size: 17pt; border-bottom: 2px solid #2c5f8a; padding-bottom: 4px; }
h2 { font-size: 13pt; color: #2c5f8a; margin-top: 1.3em; }
table { border-collapse: collapse; width: 100%; font-size: 9pt; margin: 0.6em 0; }
th, td { border: 1px solid #bbb; padding: 3px 6px; text-align: left; vertical-align: top; }
th { background: #eef3f8; }
code { font-family: Consolas, monospace; font-size: 9pt; background: #f4f4f4; padding: 0 2px; }
pre { background: #f4f4f4; padding: 8px; font-size: 8.5pt; line-height: 1.35; overflow-x: hidden; }
.small { font-size: 8.5pt; color: #555; }
</style>

# New Code Structure — First Sample

**To:** Mario · **Date:** 2026-08-15 · **Scope:** corporate bonds (the part already built) ·
**Result:** restructured sample ready; every number identical to before (all 153 automatic checks pass)

## 1. What we did

You asked us to make the code easier to follow: **many simple functions instead of one big
complicated one**, with **the inputs of each function clearly listed**, following your
folder template and the *Monthly* sheet as the reference. We restructured one first slice —
the core chain for a normal fixed-coupon bond — as a sample for your review. If you are
happy with the shape, we roll the same pattern out to everything else; nothing else has
been touched yet.

The idea, in plain words: the old code was one long recipe that did everything in one go.
The new code is a set of small building blocks. Each block does exactly one thing, says
exactly what it needs as input, and can be tested — or run on many bonds in parallel in the
cloud — on its own.

```
BEFORE — one big function:
  price_bond(...)  =  dates + cash flows + discounting + accrued, all in one loop

AFTER — many simple functions:
  list the coupon dates       ->  coupon_dates(...)
  build the cash flows        ->  bond_cashflows(...)
  discount one cash flow      ->  discount_factor(...)
  add up, subtract accrued    ->  the price function just calls the blocks above
```

## 2. The new folder layout (matches your template)

`core/` holds the general machinery (≈80% of the code, reusable for every asset class);
`assets/` holds a thin layer per asset class (≈20%). Done now vs. planned next:

```
pricer/
├── core/
│   ├── pricing/analytical.py     DONE     prices a bond by discounting its cash flows
│   ├── pricing/cashflows.py      DONE     builds the cash-flow table; accrued interest
│   ├── pricing/discounting.py    DONE     discount factors ("value today of $1 paid later")
│   ├── pricing/tree.py           PLANNED  callable bonds (bond can be repaid early)
│   ├── risk/sensitivities.py     DONE     how much the price moves when rates move
│   ├── market/spreads.py         DONE     finds the spread that matches the market price
│   ├── market/curves.py          DONE*    interest-rate curves (*points to the tested code)
│   └── utils/dates.py            DONE     the calendar rules (day counts, coupon schedule)
└── assets/
    └── corporate/
        ├── bonds_input.py        DONE     the full input catalogue (see below)
        ├── vanilla.py            DONE     one simple function per output (see below)
        ├── floating.py           PLANNED  bonds whose coupon resets with market rates
        └── callable.py           PLANNED  wrapper for callable bonds
```

The old function names still work (they now simply forward to the new blocks), so all
existing scripts, tests and results are unchanged.

## 3. One simple function per output

Same shape as the *Monthly* sheet's example block — each output has its own small function,
and they all share one input list:

| Function | What it answers | Monthly-sheet equivalent |
|---|---|---|
| `calculated_price` | what is this bond worth on our model? | *Calculated Price* |
| `implied_oas` | what extra yield (spread, in bp) over the risk-free curve makes our model match the market price? | `CorpBondOAS` |
| `duration` | if all interest rates rise 1%, roughly what % of value does the bond lose? | `CorpBondDuration` |
| `widening` / `tightening` | the price if that spread moves up / down by X bp | `CorpBondwidening` (+/−) |
| `dv01`, `convexity` | the $ price change for a 0.01% rate move; the second-order correction | — (new; legacy had none) |
| *steepening / flattening* | price if the curve tilts rather than shifts | planned — needs the curve-tilt block, next step |

## 4. Every input, in one catalogue

Each function's help text lists its inputs as a numbered table, and
`bonds_input.py` holds the master catalogue — the same style as the *Monthly* sheet's input
dictionaries, including which inputs are **not** actually used:

| No | Field | What it is | Used by |
|---|---|---|---|
| 1 | `coupon` | the bond's annual interest, in percent (6.5 = 6.5%) | all functions |
| 2 | `cpn_freq` | how many coupon payments per year (1 / 2 / 4 / 12) | all |
| 3 | `maturity` | the date the bond pays back its principal | all |
| 4 | `valuation_date` | the "as of" date of the calculation | all |
| 5 | `curve` | the risk-free interest rates for every future date (per currency) | all |
| 6 | `market_price` | the observed price we calibrate to (custodian / Bloomberg) | `implied_oas` |
| 7 | `oas` | the calibrated spread in bp — output of `implied_oas`, input to the others | price & risk |
| 8 | `bp_adjust` | size of the spread move for the widening/tightening scenario | scenarios |
| 9 | `face` | the principal amount (default 100) | all |
| 10 | `coupon_schedule` | a dated coupon table, for bonds whose coupon steps over time | optional |
| 11 | `day_count` | the market's day-counting label (30/360, ACT/ACT, …) — **carried as data, not used in pricing**; the legacy sheet itself notes "30/360, but is not used" | none |
| 12 | `spread_over_libor` | a floating bond's fixed margin over the reference rate | floating (next) |
| 13 | `volatility` | how much rates wobble — needed only for callable bonds | callable (next) |

## 5. The Monthly sheet — how we will use it

We decoded the sheet completely; it gives us three things:

1. **The function shape** (its example block, rows 47–60) — adopted above.
2. **The input-dictionary style** (rows 61+) — adopted above.
3. **An answer key.** From row 99 down it holds ~2,600 real bonds — their terms, market
   prices, and the results the old system computed (spread, duration, scenario prices),
   mostly as of 2010-03-01, with that day's interest-rate curves for six currencies at the
   top of the sheet. Once you approve the structure, we will rebuild those curves, run our
   new code over all ~2,600 bonds, and compare our numbers to the sheet's, column by column
   — a large-scale check that the rebuilt engine reproduces the old system. (The sheet even
   carries Bloomberg's own spread next to the legacy one, so we can compare against both.)

## 6. Proof that nothing changed

The project keeps a suite of automatic checks (fixed reference numbers and internal
consistency rules). All **145 existing checks pass unchanged** on the restructured code,
plus 8 new ones that lock the new layout itself — **153 green**, run time ~10s. The sample
lives in one isolated commit, so it is trivial to adjust or undo.

## 7. Questions for you

1. OK to roll this pattern out to the rest (floating → callable → the ~2,600-bond Monthly
   comparison → inflation-linked/agency → MBS when the data arrives)?
2. Naming: your template says `bons_input.py`; we wrote `bonds_input.py` — keep?
3. Where should the data-loading code (reading the holdings workbook, building the bond
   list) live in your template — inside each asset class, or as its own layer?
4. We read `endpoints/` as "batch runs first, web API later" — correct?
