# The Monthly sheet — what it is good for, and what it is not

The most important negative result in the project. A plan that treats the Monthly sheet as a
numeric golden will produce work that has to be thrown away.

---

## 1. What the sheet is

Inside `Project Pricing Fixed Income Instruments.xlsm`, sheet `Monthly`:

```text
rows 47-60    a demo block: one legacy function per metric (CorpBondOAS, CorpBondDuration,
              CorpBondwidening, ...)  -> the model for our per-output asset functions
rows 61-98    input dictionaries: Input No | Field Name | Options | Description | used-flag
              -> the model for bonds_input.py
row 99        header
rows 100+     ~2,600 bonds of SAVED legacy output (2,642 extracted rows, 81 columns)
```

Cells **Q62:Q71** are the ten `analysisType` options of input #1 — the **numbers** are in
column P and the **labels** in Q:

```text
1 Bullet · 2 Callable · 3 Puttable · 4 SinkingF · 5 OAS · 6 Duration
7 FRN price · 8 FRN OAS · 9 FRN duration · 10 Mortgage price
```

**The sheet is authoritative for function shape, input terminology and route inventory.**
That is how it was used to design the asset layer and the input catalogue, and that use is
sound.

## 2. What the sheet is not

The saved numbers are mostly unusable, and that is a finding with evidence, not a hunch.

**Valuation dates present:**

```text
2010-03-01   2,187 rows        <- the bulk
2012-12-12     274 rows        <- sound
2012-06-01     122 rows
2012-09-04      43 · 2012-07-02 8 · 2012-08-20 5
```

**The 2010-03-01 batch is a `legacy-stale-session`**: an older code revision run against
mixed-vintage cached market data. Four independent proofs (2026-08-17):

1. **the cached Q column equals duration ÷ 100 exactly** — an older code revision's output
   format, not a value our engine or any current one would produce;
2. **dead T/U cells** — the steepening/flattening columns are `#NAME?`, so the session ran
   without the SteepFlat table it needed;
3. **sub-annual rows reprice EXACTLY on the run-time Libor deposits** that survive in the
   sheet's top block, while **no single curve fits the pillar rows** — a fit/holdout split
   confirmed it. The batch mixes market data of different vintages;
4. the Q = duration/100 ratio test across the batch has a median of 1.03.

**The 2012-12-12 batch, by contrast, reproduces at the legacy solver's own noise floor**:
government bonds 32/32 within tolerance (ΔOAS ≤ 0.9 bp, median 0.51; Δduration ≤ 0.0003 y;
ΔPV ≤ 0.0085). Those caches **are** numeric goldens.

## 3. The consequence for this week's families

Route census from the frozen extract (`outputs/monthly_golden_rows.csv`, `mty_typ`):

```text
callable 464   (CALLABLE 442 + CALL/SINK 10 + PERP/CALL 5 + CALL/PUT 4 + CALL/EXT 2
                + CONV/PUT/CALL 1)
puttable   7   (PUTABLE 2 + CALL/PUT 4 + CONV/PUT/CALL 1)
sinking   18   (SINKABLE 8 + CALL/SINK 10)
```

```text
tree-family rows in the SOUND 2012-12 cohort     0
tree-family rows in the STALE 2010-03 batch    474      100%
```

**There is no numeric golden for callable, puttable or sinking-fund bonds anywhere in the
workbook.** Not a difficult one — none. Validation for those families is therefore
production parity, `==` direct-call parity, invariants and the Bloomberg three-way.

Also: even for the stale rows we do not hold the **exercise schedules** the legacy used — it
fed them from Bloomberg at run time and never saved them. A row-by-row comparison is not
merely unreliable, it is not reconstructible.

## 4. Curve truth

Every golden row prices via `zeroyield4(ccy, valuation-date)` = **government par curves**
(USD = H.15/CMT, 11 pillars → a 41-tenor gap-fill → a continuous 374-month × 4-frequency
bootstrap — our own architecture). The `BondOAS` tree consumes the same build; Libor appears
only as 1–5 month stubs.

The Libor/swap block at the top of the sheet and the `c:\blp\curves\` files are a **separate
manual chain, off the golden path** — dead `#NAME?` cells and mixed-epoch cached rates. An
early reading of the sheet assumed those were the pricing curves; Gate 0 refuted it.

USD pillars for all three valuation dates are recoverable from public data
(`data/h15_pillars_monthly_recon.csv`), so the curves are a **rebuild**, not a recovery.

## 5. Convention findings that still matter

From reading the VBA (Gate 0, 2026-08-17):

- **the legacy vanilla chain is convention-consistent** — continuous z, `exp(−(z+OAS)·t)`.
  There is no `BondPrice` bug on this path, which is why `vba_compat` was dropped from that
  workstream;
- **the month-grid convention** is real and would have to be replicated for any true
  row-level parity: Δmonth counts, a coupon every 12/freq months, face at the last step
  (maturity truncated), **no accrued interest**, a 30-year cap on the corporate path, and a
  frequency-matched curve table;
- **routing is by live Bloomberg fields** (`mty_typ`, `calc_typ_des`) cached in columns
  AB/AC with gaps; an empty field falls back to the FRN tree, and Government Bonds go to the
  vanilla path unconditionally.

## 6. How to use the sheet in a plan

**Do**: derive function names, input vocabulary and route inventory from it; quote counts
with the column they came from; use the 2012-12 cohort as a golden where a family has rows
there.

**Do not**: propose reconciling to 2010 numbers; quote a Monthly count as if it were a URS
production count (they are different populations); assume the exercise schedules exist;
open the lost SteepFlat ask before the T/U work actually starts.

Existing artifacts: the plan (`docs/monthly_reconciliation_plan_2026-08-15.md`, Rev B), the
Gate-0 memo with cell and VBA-line citations
(`docs/monthly_gate0_memo_2026-08-17.md`), the results
(`docs/monthly_recon_report_2026-08-17.md`), and this round's mapping memo (file `38`).
