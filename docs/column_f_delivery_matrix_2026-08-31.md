# Column-F delivery matrix and reconstruction evidence

**2026-08-31 · internal evidence document.** Everything here is generated or reproduced from
a run; nothing is transcribed from an earlier summary. Regenerate the tables with:

```text
PYTHONPATH=src FIP_VAL_DATE=2009-03-31 python scripts/column_f_audit.py
    -> outputs/column_f_delivery_audit_2009-03-31.csv  (one row per security)
```

The directive this answers is recorded in `docs/client_directive_pivot_column_f_2026-08-27.md`.

---

## 0. The four populations, before any count

Confusing these is the single most common way a number in this project goes wrong, so they
are stated once, here, and every table below says which one it uses.

```text
676   ROWS on the Corporate Bonds tab            <- what Mario's pivot counts
616   unique SECURITIES on that tab              <- 60 asset IDs are listed more than once
566   held / rated / matched positions in the output at 2009-03-31
555   of those, fully model-priced
```

⚠️ **A correction to our own earlier reporting.** The 2026-08-30 report, both handoff
bundles and the execution plan all describe `F13` as "2 tab rows, 1 held", which reads as
*one of those rows is not a holding*. That is false. The two rows are the **same security**,
`TNTD04283895`, listed twice on the tab. One bond, held once, priced once. The correct
sentence is "the tab lists it twice", and the corrected chain for Mario's six cells is:

```text
30 pivot ROWS  ->  29 unique SECURITIES  ->  29 held  ->  23 priced + 6 named
```

The 30→29 step is a duplicate listing, **not** a security missing from the book. The audit
script now prints all four populations and flags the difference whenever rows ≠ securities.

## 1. The six cells

| Cell | Coupon family | Pivot rows | Securities | Held | Priced | Not priced |
|---|---|---:|---:|---:|---:|---:|
| `F12` | Fixed → Floating | 5 | 5 | 5 | 4 | 1 |
| `F13` | 7.00% / 7.50% date-segmented | 2 | **1** | 1 | 1 | 0 |
| `F14` | GBP LIBOR + Spread | 1 | 1 | 1 | 1 | 0 |
| `F15` | Reference Rate + Spread | 12 | 12 | 12 | 11 | 1 |
| `F16` | EURIBOR + Spread | 9 | 9 | 9 | 5 | 4 |
| `F20` | Step-up schedule | 1 | 1 | 1 | 1 | 0 |
| | **total** | **30** | **29** | **29** | **23** | **6** |

**Adjacent, and deliberately not part of the ask:** `Fixed → Reset` (rows 6–11) — 6 pivot
rows, 6 securities, 6 held, 3 priced. They share the fixed-then-floating engine with `F12`
and were covered as a by-product. They are never folded into the totals above.

**`F21`** (`Zero coupon / structured payoff`) is not a newly built engine. Mario's own
annotation says it remains an ordinary fixed corporate bond, and that is the treatment: the
custodian's 0% coupon was a data error for a 6.95% fixed bond.

## 2. The six that do not model-price, named

**None of them is a code or model gap.**

| Cell | Asset ID | Route | Missing field | Lands via |
|---|---|---|---|---|
| `F12` | `TNTD04627285` | `hybrid-margin-unavailable` | post-switch margin | `data/hybrid_switch_terms.csv` |
| `F15` | `TNTD04769276` | `recovery` | — (defaulted) | — |
| `F16` | `TNTG023603W` | `hybrid-margin-unavailable` | post-switch margin | `data/hybrid_switch_terms.csv` |
| `F16` | `TNTG527525U` | `hybrid-margin-unavailable` | post-switch margin | `data/hybrid_switch_terms.csv` |
| `F16` | `TNTG614042U` | `hybrid-margin-unavailable` | post-switch margin | `data/hybrid_switch_terms.csv` |
| `F16` | `TNTG614044U` | `hybrid-margin-unavailable` | post-switch margin | `data/hybrid_switch_terms.csv` |

The five margin-gapped names are already on the **existing** 11-security Bloomberg request
(sent to Mario 2026-07-20, to Liping 2026-07-30). **No new request is opened by this round.**
A margin arriving is one cell in a CSV and the bond prices with zero code change — the
structure is documented, only the number is absent. They are deliberately not half-modelled:
a placeholder margin would price the floating leg as if the borrower paid pure index and
report a confident number for a bond nobody has fully specified.

The defaulted name is carried at the custodian mark on purpose, with **no OAS presented** —
a spread measured against a borrower who has stopped paying is a number without a meaning.

## 3. Per-security disposition (the 29)

Source: `outputs/column_f_delivery_audit_2009-03-31.csv`.

| Cell | Asset ID | Ccy | Coupon | Maturity | Route | Endpoint type | OAS bp | Eff dur | Mark |
|---|---|---|---:|---|---|---|---:|---:|---:|
| F12 | TNTD03009347 | USD | 6.125% | 2067-05-15 | hybrid | fixed_to_floating | 789.22 | 2.258 | 55.41 |
| F12 | TNTD04627285 | USD | — | 2049-09-29 | hybrid-margin-unavailable | fixed_to_floating | — | — | 51.00 |
| F12 | TNTD04735032 | USD | 7.000% | 2066-05-17 | hybrid | fixed_to_floating | 2616.31 | 1.606 | 23.03 |
| F12 | TNTD04967448 | USD | 7.800% | 2087-03-07 | hybrid | fixed_to_floating | 1724.27 | 4.660 | 38.08 |
| F12 | TNTD04986722 | USD | 6.375% | 2067-03-29 | hybrid | fixed_to_floating | 805.88 | 2.432 | 57.08 |
| F13 | TNTD04283895 | USD | 7.500% | 2011-03-01 | vanilla-schedule | stepped | 283.57 | 1.821 | 107.10 |
| F14 | TNTG700307W | GBP | 7.500% | 2011-03-14 | vanilla-schedule | stepped | 205.31 | 1.857 | 108.05 |
| F15 | TNTD03027773 | USD | — | 2010-07-19 | floating | floating | 153.40 | +0.049 | 98.54 |
| F15 | TNTD03035014 | USD | — | 2010-06-16 | floating | floating | 606.08 | −0.332 | 92.92 |
| F15 | TNTD03057893 | USD | 6.375% | 2067-11-15 | hybrid | fixed_to_floating | 967.40 | 2.602 | 50.00 |
| F15 | TNTD03080834 | USD | 1.2425% | 2010-01-21 | floating | floating | 397.33 | **+0.313** | 97.07 |
| F15 | TNTD04087449 | USD | 8.625% | 2010-12-15 | vanilla-schedule | stepped | 567.66 | 1.594 | 104.07 |
| F15 | TNTD04131505 | USD | — | 2012-01-31 | floating | floating | 748.60 | −0.472 | 81.34 |
| F15 | TNTD04259874 | USD | — | 2014-04-01 | floating | floating | 864.34 | −1.366 | 72.64 |
| F15 | TNTD04769276 | USD | — | 2016-06-15 | recovery | — | — | — | 0.01 |
| F15 | TNTD04794469 | USD | 6.800% | 2066-09-01 | hybrid | fixed_to_floating | 1069.16 | 1.711 | 48.23 |
| F15 | TNTD04882955 | USD | — | 2016-10-18 | floating | floating | 618.06 | −1.852 | 67.04 |
| F15 | TNTD04955876 | USD | — | 2014-01-15 | floating | floating | 772.91 | −1.132 | 69.62 |
| F15 | TNTG010475U | EUR | 4.375% | 2014-10-27 | hybrid | fixed_to_floating | 414.61 | 0.440 | 91.38 |
| F16 | TNTG001023W | EUR | 5.375% | 2009-07-02 | vanilla-schedule | stepped | 144.51 | 0.255 | 100.75 |
| F16 | TNTG023603W | EUR | 3.500% | 2015-12-16 | hybrid-margin-unavailable | fixed_to_floating | — | — | 93.77 |
| F16 | TNTG405928W | EUR | 6.000% | 2013-05-10 | vanilla-schedule | stepped | 860.38 | 3.511 | 82.72 |
| F16 | TNTG522013U | EUR | 4.750% | 2019-05-06 | hybrid | fixed_to_floating | 1057.53 | 3.425 | 51.04 |
| F16 | TNTG527525U | EUR | 3.750% | 2015-04-15 | hybrid-margin-unavailable | fixed_to_floating | — | — | 70.53 |
| F16 | TNTG614042U | EUR | 3.750% | perpetual | hybrid-margin-unavailable | fixed_to_floating | — | — | 52.00 |
| F16 | TNTG614044U | EUR | 3.750% | perpetual | hybrid-margin-unavailable | fixed_to_floating | — | — | 46.76 |
| F16 | TNTG700496W | EUR | 7.500% | 2011-04-20 | vanilla-schedule | stepped | 398.27 | 1.861 | 103.61 |
| F16 | TNTG701369W | EUR | 7.250% | 2012-04-24 | vanilla-schedule | stepped | 381.40 | 2.698 | 103.87 |
| F20 | TNTD04150829 | USD | 11.875% | 2012-07-01 | vanilla-schedule | stepped | 864.28 | 2.741 | 105.00 |

⚠️ **Updated 2026-08-31.** This section previously explained that `TNTD03080834` was the one
floater with a positive duration *because* it is the only one whose already-fixed current
coupon is recorded (1.2425%), every other floater's being projected off the curve so that the
rate bump repriced that coupon too and produced minus the time *since* the last reset.

That behaviour was a **bug**, not a second regime. The running coupon was fixed at the last
reset and a bump in today's curve cannot change it, whether or not the custodian file records
the number. It is now frozen in both cases, and the two paths return the same answer for the
same coupon. `TNTD03080834` still reprices exactly — duration `+0.313187` equals its time to
next reset `0.313187` — and two more floaters have crossed into small positives. Four remain
negative for a different and genuine reason: at a deep discount the wide credit spread behaves
like a fixed annuity with ordinary sensitivity. See §5 and
`docs/frn_current_coupon_freeze_2026-08-31.md`.

## 4. Reconstruction manifest

| Legacy implementation | New core location | Old path | Asset wrapper | Endpoint type |
|---|---|---|---|---|
| `pricing/frn.py` | `pricer/core/pricing/floating.py` | shim, retained | `assets/corporate/floating.py` | `floating` |
| `pricing/hybrid.py` | `pricer/core/pricing/hybrid.py` | shim, retained | `assets/corporate/hybrid.py` | `fixed_to_floating` |
| `pricing/coupon_schedule.py` | `pricer/core/pricing/coupon_schedule.py` | shim, retained | `assets/corporate/stepped.py` | `stepped` |

Verified, each by a test rather than by inspection:

1. **The numerical bodies are byte-identical** below the docstring. Hybrid is the one
   exception: its two import lines were repointed at pricer-native modules, and both targets
   are asserted to be *the same objects*
   (`core_hybrid.price_bond is analytical.price_fixed_rate_bond`).
2. **Shims re-export the same object**, `a is b`, not an equal reimplementation. A shim that
   returned an equal value from a second implementation would pass a weaker check.
3. **The FRN shim still exposes the private helpers** `_as_date`, `_rate`, `_df`,
   `simple_forward`, `YEAR_DAYS` — `hybrid` composes its floating leg out of them by name.
   There is a test named after that reason.
4. **`core/` no longer reaches upward** into the legacy `pricing` package for `coupon_at`;
   it imports a sibling, pinned by
   `test_core_no_longer_imports_coupon_at_from_the_legacy_package`.
5. **Each wrapper converts units and orchestrates; it does no pricing arithmetic.**
6. **Each endpoint result equals the direct wrapper call with `==`**, per instrument type —
   not a tolerance, because a tolerance permits a second implementation to drift.
7. **A typeless v1.0 request is still vanilla**, which is what keeps the Excel bridge and its
   23 real-Excel checks passing untouched.
8. **`bonds_input.py` marks which inputs each product uses**, with the JSON path for each,
   and carries a per-product reason for volatility rather than one generic line.

The private-helper coupling in (3) is deliberately **not** refactored in this pass. It is
already protected by an explicit compatibility test; rewriting it now would reduce
auditability rather than improve the delivery.

## 5. Engine evidence — fresh runs

### 5.1 Floating-rate notes

**Par identity.** With margin 0 and spread 0, the note is worth par **at its last reset**,
accreted at the curve rate — exactly, at every level and maturity:

```text
curve    maturity     dirty          100*exp(-t_prev*r)   clean
0.100%   2014-04-01   100.0480885    100.0480885          99.9999995
0.100%   2039-04-01   100.0395683    100.0395683          99.9999979
4.000%   2014-04-01   101.9416872    101.9416872          99.9992506
4.000%   2039-04-01   101.5950041    101.5950041          99.9966563
12.000%  2014-04-01   105.9388980    105.9388980          99.9930762
12.000%  2039-04-01   104.8617393    104.8617393          99.9691773
```

The *clean* price is par to a few cents; the *dirty* price is where the identity is exact.

**OAS round trip** (real USD curve, 45 bp quoted margin): solved 118.186503 bp reprices to
96.5000000000 against a 96.5 target — residual −4.7e-11.

**One duration regime** (two, until 2026-08-31), flat 4%, a 30-year note:

| current coupon | effective duration |
|---|---|
| fixed at 4.00% | **+0.104396** |
| fixed at 6.00% | **+0.104396** (independent of the level) |
| projected off the curve | **+0.104396** (was −0.395604 — the bug) |
| *+time to next reset* | *+0.104396* |
| *same-maturity fixed 4% bond* | *+17.4381* |

**A third regime on the real book** — deep discount, where the price is par minus a spread
annuity, so a rate rise shrinks the gap and the price *rises*. This one grows with maturity,
unlike the two above:

```text
asset          mark    OAS bp    eff-dur   next reset   same-maturity FIXED   running coupon
TNTD03080834  97.07    397.33    +0.3132     0.3132y          +0.801           supplied
TNTD03035014  92.92    606.08    +0.1990     0.2143y          +1.178           base-curve proxy
TNTD03027773  98.54    153.40    +0.0491     0.0549y          +1.261           base-curve proxy
TNTD04131505  81.34    748.60    -0.1669     0.0962y          +2.637           base-curve proxy
TNTD04955876  69.62    772.91    -0.4313     0.3104y          +4.226           base-curve proxy
TNTD04259874  72.64    864.34    -0.6878     0.0192y          +4.283           base-curve proxy
TNTD04882955  67.04    618.06    -1.4814     0.0769y          +6.095           base-curve proxy
```

The ordering is the point: duration rises monotonically with the mark. A floater at 97-99
sits close to its next-reset value; one in the 60s carries the sensitivity of the spread
annuity that pushed it there. All seven are still far below the same-maturity fixed bond,
which is the signature floating-rate check.

In every case `|eff-dur|` is far below the same-maturity fixed bond — the reliability check.

**Spread interpretation.** Where `quoted_margin_bp` is unknown and passed as 0, the
calibrated result is a **discount-margin-like** number that absorbs the note's unknown
contractual margin *as well as* credit. It is not a clean credit spread, and the endpoint
says which of the two meanings applies in `results.spread_interpretation` rather than leaving
a reader to assume.

### 5.2 Fixed-to-floating hybrids

**The degenerate limits delegate, bit-for-bit** — they are not approximations:

```text
switch >= maturity   hybrid 109.41547966413361  ==  vanilla 109.41547966413361   True
switch <= valuation  hybrid  98.70174903311982  ==  FRN      98.70174903311982   True
```

**The composition itself** — margin 0 and OAS 0, the floating leg telescopes exactly to
`face × DF(switch)`, so the hybrid *is* the bullet maturing at the switch, on any curve:

```text
curve  1.0%   hybrid 110.4069405449   bullet 110.4069405449   diff -1.4e-14
curve  4.0%   hybrid 104.2211085525   bullet 104.2211085525   diff -1.4e-14
curve  9.0%   hybrid  94.6900970022   bullet  94.6900970022   diff +1.4e-14
```

**One curve and one calibrated spread price both legs**, because it is one borrower's one
promise. Splitting the spread would invent a second credit.

**Every live hybrid is still in its fixed leg at the baseline** — confirmed on the current
data, not assumed: all 10 priced hybrids have `next_switch_t > 0`, from 0.577 to 28.332
years. Eight more are carried at the custodian mark with the margin named as the gap.

**`reference_oas_to_switch_bp` is a reference column, not the answer.** It prices the bond as
if repaid in full at the switch. That is a real market convention while a bond trades near
par and **actively misleading for a deep discount**, where the market is pricing *extension*
— a bond marked at 36 solves a spread of many hundreds of basis points that describes
nothing. The response labels it; `implied_oas_bp` is always the answer.

### 5.3 Scheduled coupons (`F13`, `F20`)

These are **not a new model.** The coupon varies over time but every future payment is known
today: no option, no projection, no volatility. They price on the ordinary discounting engine
handed a coupon table instead of one coupon.

```text
parsed from the workbook cell:  [(None, 0.07), (2006-03-01, 0.075)]
coupon in force at 2009-03-31:  0.07500
stepped     108.7510404340
plain 7.50% 108.7510404340        difference 0.00e+00
```

By 2009 the 2006 step is in the past, so the bond simply *is* a 7.50% bond — and prices
identically to one, exactly.

**An unparseable schedule is refused, never guessed:** `"Step-up schedule"` names a step-up
without stating the steps, and the parser returns `None`. A documented override in
`data/coupon_schedules.csv` outranks the workbook's free text, which has been wrong before —
one "zero coupon" was a custodian data error for a 6.95% fixed bond (OAS −486 bp → +431 bp),
and two "(VAR)" tags belonged to plain fixed bonds.

## 6. What this round changed numerically

```text
migration of the three engines      no change whatsoever  (five driver CSVs byte-identical)
the GBP par-yield units correction  two GBP securities and the headline counts only
the callable routing fix            no priced number; one bond moved from invisible to named
```

Every production CSV is byte-identical to the pre-change baseline within its own
environment, at both valuation dates. The only new artifacts are two disposition sidecars,
which are intentional structural additions rather than pricing drift.
