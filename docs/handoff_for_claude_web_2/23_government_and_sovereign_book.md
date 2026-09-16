# 23 — The government and sovereign book

*New file, 2026-09-15. Everything the corporate-centric domain files (11–13, 15) do not
cover, because until 2026-09-03 this material had no home in the bundle at all.*

Two rounds built it:

| round | what | tests after |
|---|---|---|
| **2026-09-03** | Government Bonds + Municipal/Provincial priced end to end | 390 → 423 |
| **2026-09-10** | Government Agencies + Index-Linked + Guaranteed restructured onto the `pricer/` template | 424 → 468 |

---

## 1. Where these classes sit in the book

⭐ **The `Summary` sheet is a FLAT pivot of `Asset sub category`. There is no "corporate
bonds" parent group.** `Corporate Bonds` is a *sibling* of `Government Bonds`, and the
master has exactly one `super_category` (`Fixed Income`). Any plan that says "these
finish the corporate category" has the sheet's shape wrong.

| sub-category | rows | unique | status |
|---|---:|---:|---|
| Corporate Bonds | 811 | 732 | done — 566 in output @3-31 |
| Government Bonds | 153 | 147 | done 2026-09-03 |
| Government Agencies | 42 | 39 | done; restructured 2026-09-10 |
| Index Linked Government Bonds | 16 | 15 | done; engine migrated 2026-09-10 |
| Guaranteed Fixed Income | 11 | 9 | done; restructured 2026-09-10 |
| Municipal/Provincial Bonds | 7 | 7 | done 2026-09-03 |
| **six non-securitised classes** | **1,040** | **949** | **COMPLETE** |
| Government MBS | 888 | 882 | skeleton, awaiting Bloomberg |
| Non-Government CMOs | 265 | 264 | not started |
| Asset Backed Securities | 79 | 79 | not started |
| Commercial Mortgage-Backed | 73 | 69 | not started |
| FI Derivatives + Other | 21 | 17 | out of scope |
| **Grand Total** | **2,366** | **2,260** | |

**The accurate sentence is "all six non-securitised classes are complete — 1,040 of
2,366 rows."** ⚠️ MBS was never inside the corporate category; do not describe it as
what "remains in corporate".

---

## 2. Two drivers, three output files

| driver | classes | output | rows |
|---|---|---|---:|
| `scripts/sovereign_risk.py` | government, municipal | `sovereign_risk_<date>.csv` + `sovereign_disposition_<date>.csv` | 154 |
| `scripts/phase2_risk.py` | agency, guaranteed, linker | `phase2_risk_<date>.csv` | 63 |

⭐ **The three phase-2 classes are one indivisible unit** and this is why the 09-10
round could not take only the two Mario named: they share ONE loader
(`dataio/phase2.py`), ONE driver, and ONE 63-row hashed CSV. Migrating two of three
would have left the third an un-migrated island inside migrated code — the
"two files owning half a decision" shape this project has closed five times.

### Route census, read from the production CSV (2009-03-31)

```
agency       vanilla                    27
             callable-lattice            5
             call-passed-vanilla         4
             zero                        2
             cmo-tranche                 1     -> 39 securities
guaranteed   vanilla                     9     ->  9
linker       ilb                        14
             ilb-indexation-unverified   1     -> 15
                                             ------
                                                 63
```

Sovereign, same date: **154 rows, 147 priced**; 150 priced at the 6-10 control (KRW
gains a curve there). 15 currencies. Unpriced at 3-31: 5 `vanilla` (curve-blocked or
terms), 1 `coupon-schedule-unavailable`, 1 `floating-reference-unverified`.

---

## 3. The curve convention — LOCKED, and the reason is coverage

**Everything discounts on its OWN CURRENCY's curve, never a per-country curve.**
Matches legacy `zeroyield4(ccy)`, `ZeroCurve.from_currency`, and the corporate book.

The alternative was live, not theoretical: a German Bund reprices at **+1.34 bp** on
`Germany_Yield_Curve.txt` and **−44.88 bp** on `EUR_Yield_Curve.txt`. The choice moves
every euro number.

⭐ **The decider was coverage, not elegance: Ireland has no curve file.** A per-country
rule would have put 2 Irish holdings on a different footing from their 28 euro peers —
manufacturing the split this project keeps closing. Per-country curves remain the
**cross-check**, not the production path. Fable was consulted before any code.

### ⚠️ `EUR_Yield_Curve.txt` is a euro-area sovereign COMPOSITE, not a swap curve

Verified, not assumed: it lies strictly between Germany and Italy at every tenor, and a
debt-weighted six-country average reproduces it to **7 bp mean / 18 bp max**.

**Consequence for what a number MEANS:** a euro sovereign's calibrated spread is
*relative value against the euro-area average*, and **never** an asset-swap spread. The
output carries `spread_meaning` per row so the same arithmetic is not read three ways:

| label | rows @3-31 |
|---|---:|
| `own-curve-anchor` (the bond's own government IS the curve; ~0 by construction) | 110 |
| `relative-to-euro-composite` | 30 |
| `spread-over-government` (sub-sovereign or foreign issuer) | 14 |

### `CURVE_FILE` grew 6 → 14

Added BRL CAD DKK ILS MXN NOK SEK SGD; CAD maps to `CAN_Yield_Curve.txt`. Units were
**reproduced against each raw file** — all decimals, so no `PAR_YIELD_UNITS` entry was
needed (GBP and DKK remain the only percent files). **MYR is deliberately ABSENT** so
`from_currency` raises and the driver names the gap rather than silently substituting.

---

## 4. ⭐ Quotation: par-as-titles, and one price per 1,000

6 of 154 securities fail the identity `BT == MV_base * fx / par * 100` by a ratio of
**exactly 0.01**. The custodian is quoting *par as a number of titles* rather than a
currency face amount.

⚠️ **The identity cannot tell you the denomination.** It holds for MXN 100 and BRL 1,000
alike. So `dataio.phase2.TITLE_FACE` is an **explicit per-currency registry, never a
price sniffer** — the `PAR_YIELD_UNITS` lesson applied in advance rather than after a
two-month misdiagnosis.

```python
bt_per_100 = BT / (F / 100.0)     # written this way round on purpose
```

With F = 100 that divides by exactly 1.0, so the five MXN prices are **bit-identical**
to their input (`==` asserted in a test). Only **`TNTG630781W` rescales: 916.73 →
91.673**. The registry is corroborated *in the data* — `MXN100` / `BRL1000` tokens
appear in `desc_long`, and a test asserts it.

⚠️ **The custodian made the same mistake**: its own `DI` yield for that bond reads
**−23.1%** against 6.45–8.41% for the MXN five. So DI is not a usable cross-check there,
and a plan that proposes "validate against the custodian yield" must carve this out.

---

## 5. Four names that were read individually

Not batch-routed. Each is a distinct lesson.

1. **`TNTD03978845` — a genuine callable US Treasury** (12.5% 2014, call 2009-08-15).
   Priced on the BDT lattice *with* `check_representable`. ⚠️ **Read its two columns
   together**: **122 bp callable vs 950 bp straight**, duration 0.39y vs 4.05y. The 950
   is option value, **not** a sovereign spread.
2. **`TNTD03983600` "STRIPPED CALL"** — call date *equals* maturity, so the `zero` rule
   claims it first. It would survive the exercise branch too, but for the wrong reason.
3. **`TNTD04437091` Russia 2030** — `coupon-schedule-unavailable`. The description says
   STEP UP and the custodian duration is **4.08** against a 21-year bullet's ~10, so it
   amortises. Not force-priced.
4. **`TNTG630227U` Japan FRN** — `floating-reference-unverified`, and ⚠️ **this is NOT a
   missing-margin ask**. The 15-year series resets off the **10-year JGB auction yield**,
   which a simple-forward engine cannot represent. Custodian duration −0.475 confirms it.

---

## 6. ⚠️ Custodian duration (AQ) is evidence in flag text, never a router

It means different things per class — it missed the call on corporate callables, and it
*is* option-adjusted on agencies. A rule keyed on it would have priced the corporate
callables as bullets. Divergence beyond **1.5 years** is reported with both numbers side
by side, and decides nothing.

---

## 7. The inflation-linked engine, and what its number means

`core/pricing/inflation.py` (was `pricing/ilb.py`, moved verbatim 2026-09-10, body
spliced not retyped, sha256 `ea475752…`, 105 lines).

**Method (v1):** there are no real-yield curves in this project, so an ILB is priced on
the **nominal** own-currency curve with an explicit index path:

```
ratio(t) = index_ratio * (1 + inflation)**t
coupon at t = real_coupon/freq * face * ratio(t)
redemption  = face * ratio(T)
```

`index_ratio` is recovered per bond from the custodian file itself: master BG "income
rate" = real coupon × current ratio, so ratio = BG ÷ the description coupon.
`RATIO_SANITY = (0.9, 1.6)` is the loader's plausibility window for a *recovered* ratio.

### ⭐ The calibrated number is approximately MINUS the breakeven inflation rate

With cash flows projected at zero inflation and the price taken from the market, the
spread must absorb exactly the inflation the projection omitted. So it comes out
**negative for a healthy linker**, and that is the engine being right.

Exactly: pricing with inflation π at spread s equals pricing with inflation 0 at spread
`s − ln(1+π)` — an identity of the exponential discounting, unit-tested. Therefore

```
breakeven = ln(1 + inflation) − spread
```

which at the production assumption of zero inflation is simply `−spread`, the form the
driver publishes.

⚠️ **The wrapper function is `implied_spread_vs_nominal_bp` and the name `implied_oas`
is BANNED from `assets/government/linker.py`** — a test injects the banned name and
fails, so the lock is not decorative. Mixing this number into a credit-spread average is
the failure it exists to prevent.

### What it read at 2009-03-31

Source: `outputs/phase2_risk_<date>.csv`. ⚠️ **Population: 13 linkers, near-maturity
excluded — the driver's own median population.** All 14 gives 82 bp, not 85; quote the
driver's.

| bond matures | breakeven |
|---|---:|
| Jan 2010 | **−34 bp** (falling prices priced within the year) |
| Jul 2014 | +35 |
| Jan 2017 | +69 |
| Jan 2025 | +85 |
| Apr 2032 | **+139** |

**Median 85 bp at 3-31 against 215 bp at 6-10** — the deflation scare unwinding in ten
weeks. The near-dated bond **flips −33.8 → +60.0 bp** between the dates. The Japanese
linker sits at **−229 bp (−2.3%/yr)**: the sign goes the other way, and it goes the
right way. That is the check that the method works.

**v1 boundaries, documented and deliberate:** the TIPS deflation floor is ignored (it is
an inflation-vol option — worthless for the seasoned high-ratio holdings, real for the
near-par 2009 vintages); the static index path makes the measured duration a **REAL-rate**
duration, not a nominal one; indexation lags and seasonality are not modelled.

**`KTBi` is BT-marked `ilb-indexation-unverified`** — BG equals the coupon exactly (no
ratio embedded) and the description carries no coupon, so the ratio is underivable. One
$1.2M position, no downstream dependency, on the deferred-ask queue.

---

## 8. ⭐ Government Agencies has no engine of its own

**This is the round's one honesty risk and the report says it plainly.** All five routes
were already built and migrated in Rounds 2a/2b:

| route | how many | engine |
|---|---:|---|
| vanilla | 27 | `core/pricing/analytical` |
| callable-lattice | 5 | `core/pricing/tree` via the shared `embedded_option` |
| call-passed-vanilla | 4 | same as vanilla — a one-time call already passed unexercised |
| zero | 2 | same, coupon 0 (RefCorp STRIPS, 107–113 bp) |
| cmo-tranche | 1 | **not priced** — see below |

Nothing was ported for this class. What moved on 09-10 was the **wrapper and the
labelling**. Saying "we restructured two classes" implies engine work that did not
happen.

**Conventions:** Bermudan par call at 100 from the custodian AB date, σ = 0.15 (Mario's
v1 choice, and the industry default for agency debentures). ⚠️ The par-call price is
applied when a row is **seeded** into `data/call_schedules.csv`, never inferred in code,
and every seeded row carries `exercise_terms_status = provisional` — **0 of 9 confirmed**.

**`TNTD04733316` ("FHLMC SER 3122 CL ZB") is refused, not force-priced.** It is a REMIC
accrual tranche misfiled as an agency debenture; carried at the custodian mark, priced
in the CMO phase. The Sempra lesson.

**Median agency spread 121 bp.** The wides are quasi-sovereign credit: KDB 607 /
KEXIM 594 / PEMEX 620 / FHLB-Chicago SUB 392.

⚠️ **On agencies the custodian AQ IS option-adjusted** — the reverse of corporate — which
made it a free validation of the lattice: 4 of 5 land within 0.75 years of AQ.

---

## 9. Guaranteed Fixed Income — a reporting rule, not a pricing one

Nine FDIC-TLGP securities, all `vanilla`, median **86 bp**. The credit being priced is
the United States government's, not the issuing bank's, so the class reports in its
**own bucket** (`TLGP-guaranteed`) and **never** in a bank rating bucket. Mixing them
would make both numbers wrong — the bank bucket too tight and the guaranteed spread
invisible.

Applied in production by `dataio/phase2.py`; stated and tested in
`assets/government/guaranteed.py::reporting_bucket`, which accepts an issuer bucket and
deliberately ignores it (the "echoed but not applied" convention).

---

## 10. `assets/government/` — what each module owns

| module | owns |
|---|---|
| `bonds_input.py` | 16 numbered inputs, **its OWN numbering** — government 9 is `spread_vs_nominal_bp`, corporate 9 is `bp_adjust`. Different dictionaries; neither renumbers the other. The currency options are **computed from the curve registry**, never written out |
| `linker.py` | seven per-metric functions over `core.pricing.inflation`, legacy units |
| `agency.py` | the option verdict rule and its named thresholds |
| `guaranteed.py` | the TLGP bucket rule |
| `sovereign.py` | the government-side path to the shared lattice surface |

⚠️ **Nothing in this package routes.** Routing has one owner —
`dataio.phase2._route_agency` with its named constants `ZERO_COUPON_MAX_PCT`,
`MAKE_WHOLE_MAX_GAP_DAYS`, `_DATE_PAIR`, `_CMO_CLASS` — and a test forbids the
government package from redefining any of them.

### The three thresholds `agency.py` took over

They were unnamed magic numbers inside the driver, deciding how a callable result gets
described:

| constant | value | meaning |
|---|---:|---|
| `LIE_DETECTOR_BP` | 0 | a negative callable spread means our par-call-from-AB assumption conflicts with the price — a statement about the ASSUMPTION, not the bond |
| `EXTENSION_PRICING_GAP_BP` | 100 | the market is pricing to maturity, not to the call (2009 agencies frequently did not call) |
| `CALL_NOT_BINDING_GAP_BP` | 1 | the two calibrations agree; the option never binds |

The driver keeps its inline copy so its output stays byte-identical, so **a test parses
the driver source** and fails if the numbers ever diverge. At 3-31 all five callables
read `call-active`.

---

## 11. Decisions taken, with their triggers

| decision | date | reopens when |
|---|---|---|
| **No ILB endpoint type** | 2026-09-10 | the worksheet grows cells for a real coupon, an index ratio and an inflation assumption. `contracts.py`, `schema_version` (1.1) and the `.bas` are untouched; every government input's `external` reads `-`, test-pinned to the 7-type contract |
| **`sovereign.py` = a government-side import path, not a rewrite** | 2026-09-10 | a third non-corporate caller appears, or the securitized layer lands. `embedded_option.py` is **mis-located, not mis-written** — one lattice prices every optioned bond in the book, and moving it would touch the corporate hashed CSVs |
| **Own-currency curve** | 2026-09-03 | not expected to |
| **`TITLE_FACE` explicit registry** | 2026-09-03 | a new currency with a non-100 denomination arrives |

⭐ **"7 / 5 / 5" became "8 / 7 / 5 / 5" on 2026-09-10** and this is the distinction a
plan most often gets wrong: **8** products the engine prices, **7** types the contract
can express, **5** the VBA builder can construct, **5** verified by real-Excel round
trips. Until the ILB migration, the first two were the same number.

---

## 12. What is open

1. **The ILB worksheet layout** — the engine and wrapper are finished. Where do the three
   inputs sit on the sheet? Mario's to answer; in the 09-10 report as the open question.
2. **KTBi indexation terms + the KRW 3-31 curve row** — deferred, confirmation-only, no
   downstream dependency. ⚠️ Do NOT re-ask before Mario returns the MBS data.
3. **Agency call schedules** — the par-call lattice already matches custodian AQ, so this
   is confirmation-only and on the same deferred queue.
4. **`outputs/callable_risk.csv` is still undated** — running 6-10 after 3-31 overwrites
   it. `scripts/platform_parity.py` works around it by running June before March; the
   real fix is a named carry-over.
