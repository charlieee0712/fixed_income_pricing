# Monthly-sheet Gate-0 inventory memo — 2026-08-17

**Executes:** Gate 0 of `docs/monthly_reconciliation_plan_2026-08-15.md` (pure reads, no product
code — inside the sample-first freeze by design).
**Evidence base:** openpyxl reads of `data/Project Pricing Fixed Income Instruments.xlsm` (run on
47; sheet `Monthly`, 2,896 rows × 81 cols, golden-table header = **row 99**) + targeted reads of
the olevba extraction `extracted/project_vba.txt` (line numbers below refer to that file) + zip /
curve-txt checks on the local mirror. Every claim carries a cell or line citation.
**Outcome:** all eight questions answered; **three findings overturn the plan's §2/§3 premises**
— the plan was revised in the same commit (Rev B). Nothing here requires a counterparty ask
today; the single lost input (SteepFlat file) stays a deferred ask tied to the T/U gate.

---

## 1. Three plan-changing findings

### F1 — The golden table prices on GOVERNMENT curves, not the top-block Libor/swap curves

The plan's "central hazard" (§2: sheet = Libor/swap regime vs our Treasury regime) is **refuted
by the code path**. `BondCalc` calls **`zeroyield4(Currname, valuation)`** before pricing every
row (l.3391 for Government Bonds, l.3554 for everything else non-Comdty/non-Govt-ticker), and
`zeroyield4` (l.1011) builds the curve from **government pillars pulled per valuation date**:

- **USD = H.15 Treasury CMT**: `GetBloomberg("H15T1M/3M/6M/1Y/2Y/3Y/5Y/7Y/10Y/20Y/30Y Index")`
  (l.1082–1092) — 11 pillars, linearly gap-filled to the familiar **41-tenor 0.08…30y grid**
  (`Term2`, l.1034–1074; fill arithmetic l.1094–1132: 2M = avg(1M,3M), 4–5M on the 3M–6M slope,
  7–11M on the 6M–1Y slope, 4Y = avg(3Y,5Y), 6Y/8–9Y/11–19Y/21–29Y on the bracketing slopes).
- **15 other ccys** = Bloomberg country government-curve tickers (DKK C267\*, AUD c127\*, BRL
  C802\*, CAN/EUR/GBP/ILS/JPY/KRW/MXN/MYR/NOK/SEK/SGD/THB; Case list l.1080–1950).
- Both engine families consume this one build: the **Corp\* vanilla chain** reads the in-memory
  4-frequency zero tables it fills (`Annual/Semiannual/Quarterly/Monthly`, the `For wq = 1 To 4`
  bootstrap at l.2067 — same algorithm as `zeroyield` l.255); the **BondOAS tree** reads the same
  build's 31-point par vector `IYC` (tenors {0.5, 1..30}y, decimal; filled l.2047–2057, copied to
  `Discterm` → `DiscountMat_I/Discountrate_I` at l.4441–4470 — the file read at l.4449 is
  **commented out**). The only Libor anywhere in the golden path = BondOAS's month-1..5 deposit
  stubs (`US0001M/2M/3M` + slope-extension, l.4687–4697).
- The sheet's top block (`=Zeroyield(R3:S43,"USD","c:\blp\curves\")` in row 1, per-ccy blocks
  R/S=USD, U/V=DKK, W/X=EUR, Y/Z=GBP, AA/AB=JPY, AC/AD=SEK, rows 3–43) is a **separate manual
  tool-chain** — `zeroyield` (l.194) reads the *range*, writes par + 4 zero tables as text files
  under the *path* (l.253, 404–443; `.txt` appended by `WriteToATextFile` l.2306), and returns an
  unassigned Double (cached cell value = `#NAME?` today, dead UDF). **None of its outputs are in
  the golden table's data path.**

**Consequences.** (a) Gate 1 becomes a **Treasury-curve rebuild** (zeroyield4 replica): USD
pillars = FRED `DGS1MO…DGS30` — public, full history, all three valuation dates. (b) The 2012
blocks stop being conditional: `zeroyield4` pulls per `O`-date, and FRED covers 2012-06-01 /
2012-12-12. (c) Our tracked `data/*_Yield_Curve.txt` (9-tenor H.15-lineage) contain rows for
**40238 / 41061 / 41255** for USD/EUR/GBP/JPY/SEK (DKK lacks 40238) — an independent cross-check
at the shared tenors. (d) The "Libor/swap bootstrap variant" is no longer Gate-1 scope; what the
tree gate later needs is the deposit-stub replication plus this same par vector.

### F2 — `bondcalc`'s vanilla chain is convention-CONSISTENT: `vba_compat` is dropped

The plan's §3 question (does the `BondPrice` semiannual-vs-continuous bug carry over?) is
answered **statically: no**. The bootstrap stores a **continuous** zero (money-market simple DF
for ≤1y then `z = −ln(DF)/t`, l.299–300; pillar solve discounts `Exp(−z·t)`, l.346–347) and the
pricers discount `Exp(−(z + OAS/10⁴)·t)` on the same z (`CorpBondOAS` l.2495–2496; same in
Duration/widening/Steepening l.2746–2747, 2951–2952, 3141–3143). Same-convention in, same-
convention out — the `BondPrice` mismatch does not exist here. Per the plan's pre-registration
("if Gate 0 finds bondcalc clean"): **H2 collapses to ≈0 and `vba_compat` leaves this
workstream**. The Gate-2 pilot keeps one token dynamic check (both modes on 3 bonds) as the
static/dynamic agreement test.

### F3 — The real hazards: the month-grid convention, and Bloomberg-field ROUTING

**(a) Month-grid cash flows, no accrued.** Every Corp\* function builds the schedule as *month
counting*, dates and day-of-month discarded: `maximo = (Year(mat)−Year(val))·12 +
(Month(mat)−Month(val))` (l.2398–2402); cash flows at months `salto, 2·salto, …` (salto = 12/freq)
with each flow discounted at the table's `t = i/12`; **face pays at the last coupon index**, so a
maturity month not on the coupon step is *truncated down* (l.2492–2502); the first coupon is
always a full period out; **no accrued interest exists anywhere** — PV is compared to the raw
input price (col B) directly (l.2502–2505). Maturities are capped at 30y before counting
(`Maturity = valuation + 30·365`, l.3560–3562). The freq-matched curve table is selected by the
bond's own `cpn_freq` (l.2404–2433). ⇒ Reconciliation requires a **legacy-parity pricing mode**
(month-grid, no AI, truncation, cap, freq-matched table) — our production ACT/364 engine must
not be bent to this; it is a separate thin mode used only for this workstream.

**(b) Routing runs on live Bloomberg fields.** For non-mtge rows BondCalc fetches
`mty_typ`/`calc_typ_des` **inside the pricing call** (l.3564, 3570–3573) and dispatches:
`"at maturity"` → Corp\* vanilla chain (l.3575–3594); `"callable"/"puttable"/"sinkable"/"normal"`
→ `BondOAS` lattice (l.3596–3662); `calc_typ_des = "float rate note"` → `BondOAS(8/7/9)` FRN
tree (l.3733–3749); **unknown/empty `mty_typ` → `Case Else` → the FRN-tree fallback**
(l.3712–3726). MBS/ABS/CMBS route by `asset_type` directly to `BondOAS(10)` (l.3409–3417,
3664–3684) without a mty_typ pull; Government Bonds route to Corp\* **unconditionally**
(l.3389–3405). The sheet **caches these fields** in AB (`MTY_typ`) / AC (`calc_typ_des`) via
`=getbloomberg($M<r>&" Corp",…)` — usable, but partial: AB = CALLABLE×442, AT MATURITY×348,
NORMAL×69, CALL/SINK×10, SINKABLE×8, PERP/CALL×5, CALL/PUT×4, PUTABLE×2, CALL/EXT×2,
CONV/PUT/CALL×1, plus **0×999 / blank×546 / #NAME?×206** (the " Corp" suffix is hard-coded, so
every MBS/CMBS CUSIP resolves invalid → 0; #NAME? = cells whose formulas were recalc'd later
without Bloomberg). Route replication therefore uses AN (asset class) + AB/AC where cached, and
**empirical classification** (does the vanilla parity price match?) for the dead-AB corporates.

---

## 2. The eight questions, answered

| # | Question | Verdict | Evidence |
|---|---|---|---|
| 0.1 | Zeroyield outputs cached in rows 3–43? | **Formula cells are dead (`#NAME?`); the INPUT rates are static cached values, fully readable.** The UDF never returned the curve anyway (side-effect file writer, unassigned return). | Monthly!T1/V1/X1/Z1/AB1/AD1 = `#NAME?`; rows 3–43 static; VBA l.194–454 |
| 0.2 | Range or file path the live input? | **Range = live input; path = OUTPUT directory** (`c:\blp\curves\`). But the whole chain is out of the golden path (F1). | l.218–253 (reads `Term.Cells`), l.404–443 (writes) |
| 0.3 | `bondcalc` discounting; re-bootstrap or consume? | **Consistent continuous discounting (F2). Re-bootstraps in-memory via `zeroyield4` per row** — consumes neither the sheet block nor the files. Lock #4 status: the golden run used the *auditable-family* (continuous) bootstrap, not `BondPrice`'s semiannual variant. | l.3391/3554; l.2495–2496; l.2067 |
| 0.4 | SteepFlat tables in the workbook? | **No** — nowhere in the workbook's 26 sheets, nor in `All_Yield_Curve.zip` / `Bootstrapped-*.zip`. It is a lost disk file (`donde + "SteepFlat Table Monthly.txt"`, live reads l.3067/4436/5981). Missing file ⇒ `ReadAsciiFile` exits ⇒ steep/flat arrays stay **zero** ⇒ T/U = untwisted reprice. Observed: **43% of FIXED rows have T=U** (zero-twist epoch), 57% T≠U (a real file existed during those runs). ⇒ T/U reconcilable only for the zero-twist part unless the file is recovered — deferred Mario ask, opened only when the T/U gate opens. | sheet scan; input dict Monthly!J79 ("Steepening from File in .txt"); l.3271–3273, 3309–3314 |
| 0.5 | Column X clean or dirty? | **Neither concept exists in the engine.** The calibration input is **col B `MarketPrice`** (X = `Mkt Base Price` is a base-ccy copy; equal for USD). PV (no accrued, coupon-anniversary month grid) is matched to B as-is; the input dictionary describes it only as "Existing price of Bond, from Custodian, or Bloomberg" (Monthly!B73/D73–D74). Parity mode replicates exactly that; our clean/dirty law (lock #3) stays a URS-book concept. | row-100 formulas; l.2502–2505 |
| 0.6 | FLOATING fields; VARIABLE semantics? | FLOATING rows carry the **current reset coupon in C** (e.g. row 106: C=0.68406) and **no margin column** — BondCalc passes `spreadtoLibor = 0` (l.3394); margins were Bloomberg-pulled inside `BondOAS(8)` at run time. **VARIABLE = mostly fix-to-float hybrids priced as CALLABLE FIXED on the lattice** (row 168: Allstate 6.125 2037, AB=CALLABLE, AC=FIX-TO-FLOAT BONDS, P=155, Q=0.66) — a legacy convention divergence vs our `hybrid.py` (note: several VARIABLE names overlap the URS book). | rows 106/168; l.3733–3749 |
| 0.7 | 2012 curve inputs anywhere? | **No 2012 curve blocks in the workbook (numeric scan: none)** — but none are needed: `zeroyield4` pulls per row-date, and USD pillars for 2012-06-01/2012-12-12 are FRED-able; the tracked txt files also carry all three dates (F1c). The 2012 rows (122+274) move from "conditional" to **feasible**. | S7 scan; l.1028–1031 |
| 0.8 | Grid conventions vs our ACT/364? | **Radically different — month-grid, no dates at all** (F3a). The TNTD04441873-style coupon-count check is superseded by exact grid replication in the parity mode. | l.2398–2502 |

---

## 3. The per-row engine map (what the recon must reproduce, per population)

`P/Q/R/S/T/U/V/W` cell formulas (row 100, representative):
`=bondcalc(analysisType, M=ISIN/CUSIP, B=price, G=maturity, O=valuation, E=freq, C=coupon,
D=cpn_typ, N=vol, OASadj, shift, F=ccy, "c:\blp\curves\", AN=asset class)` with:
P=type 1 (OAS); Q=2 (duration, OASadj=P); R/S=4 (price at P±10bp: shift=+10/−10); T/U=5/6
(steep/flat price at P); V=3 with `N+1%` vol; W=3 at N vol. AE==P; **AG =
`|AE−AD|/|AD|` — RELATIVE, not absolute** (row-100 formulas; plan's map corrected).

| Population (AN × AB × D) | n | Legacy path | Recon gate |
|---|---|---|---|
| Corp/Agy/other × AT MATURITY × FIXED | **248** (all @2010-03-01; P med 191bp, 28 zeros, 8 ≥999bp) | Corp\* vanilla, month-grid, Treasury curve | **Gate 3 core** |
| Government Bonds × any × FIXED | ~174 usable (P med 32bp, p25 −5bp, 61 negative — Treasuries ≈ 0 ± small = free sanity anchors) | Corp\* vanilla **unconditionally** (l.3389) | **Gate 3 core** |
| Corp × dead-AB (0/blank/#NAME?) × FIXED | 217 | 0/blank ⇒ FRN-tree *fallback* at run time; #NAME? ⇒ unknowable | Gate 3 empirical: parity-match ⇒ was at-maturity; else exception `route-unknown` |
| Corp/Agy × CALLABLE/NORMAL/SINK/PERP × FIXED | ~450 | BondOAS lattice (Bermudan; schedules were Bloomberg-pulled at run time — not cached in the sheet) | tree gate, schedule-data-gated |
| FLOATING (D) | 426 | `BondOAS(8)` FRN tree; P tails pathological (62 neg, 95 ≥999); **legacy FRN duration = OAS-bump ⇒ SPREAD duration** (Q med 3.56, not time-to-reset) — convention divergence vs our `frn.py` documented up front; short FRNs die (`discountSize=Round((G−O)/365)=0` ⇒ 0, e.g. row 106) | conditional (tree gate) |
| ZERO / ZERO COUPON / OID (D) | 110+16+2 | **ZERO: P=0 for all 110** — `Coupon=0` fails Corp\* validation (l.2356–2362 rescue requires Frequency=0 *and* the generic path forces Frequency=2 first, l.3576–3579). No vanilla-zero golden exists. "ZERO COUPON" (16) went a strip special-case (P med 161bp but Q≈0.056 — degenerate). | **excluded — legacy produced no signal** |
| DEFAULTED (D) | 21 | validation reject ⇒ all 0 (l.2368) | excluded (matches plan) |
| MBS/CMBS/ABS (AN) | ~1,300 | `BondOAS(10)` mortgage engine (`mtge_cflows` files under `c:\blp\` — lost) | out of scope here (MBS phase) |
| STEP / VARIABLE / misc (D) | ~90 | mixed: lattice-as-fixed, FRN fallback; P heavy-tailed garbage (STEP med 1181bp) | case-by-case at Gate 4 |

**Sheet-staleness, measured:** the golden table is essentially **frozen output** — only 56 live
`bondcalc` formulas remain (≈7 rows × 8 cols, e.g. row 100 whose P..W = `#NAME?` today);
~60/col `#VALUE!`/`#NAME?` cells and 3 rows with formulas pasted *as text* (rows 2421/2423/2466)
are the stale class; everything else was pasted as values at production time. `getbloomberg`
formulas: 431 live (AB/AC/AQ on some rows).

**Legacy solver noise floor (for tolerances):** `Veloz` convergence = 1e-4 *relative* price
(l.2505 `0.01/100`) ⇒ OAS slop ≈ 0.01/(dur·100)·10⁴ bp (~0.1–1bp, worst at short maturities);
pillar zeros carry the same tolerance (~0.5bp at 2y, ~0.06bp at 30y). A per-row solver-residual
diagnostic exists for free: for at-maturity rows V=W= reprice at P ⇒ **|V−B| = legacy's own
solve residual** (V=W confirmed on 1,225/1,826 FIXED rows; |V−X|<0.5 on 1,105).

**Bonus third-party column:** besides AD (Bloomberg OAS, n=311, FIXED 297), **col I =
"Duration - effective" (Bloomberg), n=2,278** — the duration three-way has 7× the coverage of
the OAS three-way. Col J = S&P rating (\*AGY×906), K = par, L = weight%.

---

## 4. Gate-1a build spec (curve rebuild — now fully determined)

1. **Pillars:** FRED `DGS1MO/3MO/6MO/1/2/3/5/7/10/20/30` at each valuation date (= H15T\*
   tickers, same H.15 release). Cross-check at {0.25,0.5,1,2,3,5,10,20,30} vs the tracked
   `USD_Yield_Curve.txt` rows 40238/41061/41255.
2. **Gap-fill to 41 tenors** exactly per l.1094–1132 (averages + bracketing slopes as listed
   in F1).
3. **Bootstrap** = the `zeroyield` algorithm (l.255–447): deposits ≤1y simple `DF=1/(1+r·t)`,
   continuous `z=−ln(DF)/t`; annual pillars from month 24 solved so the freq-matched par bond
   reprices 100 under `Exp(−z·t)`, linear-in-z sub-grid between pillars, 374-month tables ×
   {A,S,Q,M}. Expectation: our `bootstrap.py` (the auditable-family port) already reproduces
   this modulo Veloz slop — pilot decides whether a dedicated exact replica is needed.
4. Non-USD (166 rows: EUR 94, GBP 21, JPY 14, tails): Bloomberg country-curve pillars ≠ our
   9-tenor txt grid; treat the txt rows as approximate pillars, USD-first regardless.

## 5. What is NOT being asked of anyone now

- **SteepFlat Table Monthly.txt** — lost; needed only for the T≠U 57%; ask Mario **when the T/U
  gate opens** (deferred-asks discipline, lock #13).
- Callable schedules / FRN margins / mtge cash-flow files for the tree & MBS rows — all were
  live Bloomberg pulls; they become concrete row-lists at their own gates, folded into the
  existing missing-data registry process (`docs/missing_data.md`), not new asks today.
- Top-block cached rates (r3–43) look **mixed-epoch** (USD 12M Libor cached 1.8775 vs ~0.85
  actual on 2010-03-01) — irrelevant to the golden path (F1); date-stamp vs FRED only if the
  manual chain is ever reconciled.

## 6. Plan deltas applied (Rev B, same commit)

1. §2 curve-regime hazard **replaced** by the two real hazards (month-grid parity; routing
   fields) — F1/F3.
2. §3 convention question **resolved statically**; `vba_compat` dropped; H2 collapsed; pilot
   keeps the 3-bond dynamic checksum.
3. Gate 1 re-scoped: Treasury/zeroyield4 rebuild (spec §4 above); swap-variant demoted to the
   tree gate (deposit stubs only).
4. Gate 3 population corrected: **~420 vanilla rows** (248 corp/agy + ~174 govt), not ~1,900;
   ZERO/DEFAULTED excluded (legacy signal = 0); 2012 rows feasible (vanilla: FRED curves).
5. Three-way design: AG is relative; AD n=311; **col I duration three-way added** (n=2,278).
6. Tolerances anchored to the measured Veloz noise floor; |V−B| adopted as the per-row legacy
   solve-residual diagnostic.
7. New exception reasons: `route-unknown`, `legacy-solver-cap` (P=1000 pile-ups), `legacy-dead`
   (P=0 classes).
