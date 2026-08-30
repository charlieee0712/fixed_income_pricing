# Testing and validation

What counts as evidence in this project, and why. A plan that asks for the wrong *kind* of
evidence wastes a round.

---

## 1. Four kinds of evidence, and when each applies

| Kind | What it proves | Used when |
|---|---|---|
| **Golden-master** | our output reproduces a trusted external number | a legacy output exists and is sound (the bootstrap CSVs; the 2012-12 Monthly caches) |
| **Production parity** | a change altered nothing that already worked | every migration — freeze the driver CSVs, hash, compare |
| **Direct-call parity (`==`)** | a new surface is the same computation, not a similar one | wrappers and the endpoint |
| **Invariants** | the model behaves as the economics require | anything with no golden: the lattice, FRN, hybrid, ILB, MBS, sinking |

The project's honest position is that **most new work has no golden**, because the legacy
system cannot be re-run (its Bloomberg inputs are gone) and its saved outputs are mostly a
stale session. Invariants plus parity are therefore the primary evidence, and saying so
plainly is part of the deliverable.

## 2. The suite, 223 checks

```text
test_bootstrap             the par->zero golden, with SEGMENTED thresholds
test_ratings               the S&P/Moody notch map
test_universe              53 checks: the funnel reproduces every documented count exactly
test_oas                   the archived index-OAS reader
test_lattice               29 lattice invariants (par reprice, arb-free, ordering, σ=0)
test_call_schedules        the loader: multi-row grouping, date->time clamping
test_coupon_schedule       free-text parsing + schedule-aware pricing
test_frn                   7 FRN invariants incl. the negative-duration case
test_hybrid                10: bit-exact degenerate limits, the margin-0 identity
test_ilb                   exact degeneration to price_bond, the -breakeven identity
test_mbs                   annuity degeneration, principal conservation, par-at-WAC
test_phase2_universe       goldens 39 / 9 / 15 + routes + ratios
test_price_convention      16: clean-form vs dirty-form OAS roots agree to 1e-10
test_term_overrides        the three override tables
test_monthly_curves        13: the zeroyield4 replica
test_pricer_structure      8: the template layout, shim identity, unit round-trips
test_vanilla_json_endpoint 28: endpoint parity, firm rules, leniency, the CLI
test_pricer_tree_structure 29: migration identity, one-tree invariants, sinking
```

Plus **23 Excel checks** in PowerShell, outside pytest.

Runtime: ~19 s locally, ~92 s on the server (the difference is disk and load, not the tests).
The slow ones are the workbook-loading suites, not the engines.

## 3. The invariants that carry the most weight

**Curve and discounting**
- a curve reprices its own par bonds to exactly 100 (this is what proves the corrected
  discounting is *correct*, not merely chosen);
- a straight bond on the lattice equals the directly discounted price to machine precision,
  and is independent of σ.

**Clean / dirty**
- clean-form and dirty-form calibration find the **same root** (< 1e-10), per engine;
- the lattice's straight-bond price equals `price_bond`'s dirty value.

**Options**
- callable ≤ straight ≤ puttable; callable-only ≤ call+put ≤ puttable-only;
- no schedule ⇒ exactly the straight bond;
- σ = 0 degenerates correctly;
- sinking at f=1 **is** the call cap, bit for bit; f=0 is the straight bond; value is
  monotone in f.

**Floating**
- a par floater stays at par under **any** curve shift when spread and OAS are zero;
- near-par duration ≈ 0; FRN duration ≪ a same-maturity fixed bond's, even at 78 years.

**Hybrid**
- degenerate limits delegate bit-exactly to the two underlying engines;
- with margin 0 and OAS 0 the floating leg telescopes exactly to `face · DF(t_switch)` on
  any curve — the composition test.

**Interface**
- endpoint results equal direct calls with `==`;
- every response is standard JSON with `allow_nan=False`;
- no error message contains a file path.

## 4. Migration proof — the procedure that has worked three times

```text
1. freeze     run all three production drivers, keep the CSVs
2. move       copy the implementation verbatim; old path becomes a shim
3. re-run     the full suite, plus the three drivers
4. compare    SHA-256 of each CSV, before vs after — identity is the acceptance criterion
5. repeat 3-4 after every code-bearing commit in the round
```

This is stronger than "the new tests pass" and it costs about ten seconds. It is why the
tree migration could be asserted as *no behaviour change* rather than *no observed change*.

## 5. Three-way comparison, for when there is no golden

Where the workbook carries Bloomberg's own columns, a session-independent comparison is
possible: ours vs Bloomberg vs the legacy cache. On the 2010 stale rows, **our durations
track Bloomberg's better than the sheet's own saved values for 94% of ~200 bonds** (median
|Δ| 0.49 y versus the cache's 4.30 y).

The OAS three-way was pre-registered as **not decidable** — the Bloomberg pull date is
unknown and the basis differs — and it was reported that way rather than being spun.

## 6. What a plan should ask for

- for a **migration**: production parity by hash, plus the whole existing suite;
- for a **new surface over existing mathematics**: `==` parity against direct calls;
- for a **new model**: invariants on controlled fixtures, with at least one *exact* anchor
  (the sinking fund's f=1 case is the pattern to copy);
- for anything touching the Monthly sheet: a classification of which rows are usable at all
  (see `19`) **before** any numeric comparison is proposed.

---

## Update 2026-08-30 — 287 tests, and a correction to the parity protocol

**223 → 287.** New files: `test_pricer_floating_structure.py` (31) and
`test_json_endpoint_dispatch.py` (29), plus 4 in `test_bootstrap.py` for the par-yield units.

### ⚠️ The parity protocol changed, because the old one was measuring the wrong thing

The checked-in `outputs/*.csv` were produced on **47**. A fresh **local** run of the same code
differs by up to **3.6e-8 relative, entirely in the `convexity` column** — convexity is a
second difference divided by the square of a 1 bp bump, so it amplifies a last-bit
floating-point difference by 10⁸. Every text column matches exactly; prices, spreads and
durations agree to ~1e-12.

Before relying on that diagnosis, **two local runs of the same driver were checked and are
byte-identical to each other**. So parity this round was asserted **local-fresh vs
local-fresh** — byte-exact, and therefore a *stricter* test than the cross-platform comparison
it replaces.

The practical warning: a `sha256` diff of a driver CSV across platforms shows a difference
that is **not a regression**. Do not diagnose it as one, and do not "fix" it.

### What counted as evidence this round

No numeric golden exists for the floating families — every relevant Monthly row is in the
stale 2010-03-01 batch — so, in descending strength:

1. **Production parity by hash** — all five driver CSVs byte-identical to a pre-change
   baseline, after **every** code-bearing commit, not just at the end.
2. **`==` parity** — every wrapper and every endpoint result equals the direct engine call
   exactly, per instrument type. Not a tolerance: a tolerance permits a second, drifting
   implementation.
3. **Shim identity on the object** — `a is b`, not `a == b`. A shim that returns an equal
   value from a re-implementation would pass the weaker check.
4. **Invariants with at least one exact anchor** — the par-at-last-reset identity to 1e-12 at
   every curve level; the margin-0 telescoping exact on any curve; both hybrid degenerate
   limits bit-exact.

### A test-writing lesson worth keeping

**Two of this round's tests were written wrong before the engine was checked.** Both concerned
the floating-rate duration; the docstring described one regime and the engine implements two,
with opposite signs. The engine was right both times. When a test disagrees with an engine
that has been in production for two months, **measure before editing either** — the numbers
here (+0.104396 vs −0.395604, against 17.44 for the fixed bond) settled it in one run.

**And do not let a test borrow a data defect.** Two endpoint tests used GBP as their
"unbuildable curve" fixture; fixing the curve broke them. The subject was the error *mapping*,
so they now monkeypatch the loader. Any fixture of the form "this real thing happens to be
broken" will one day fail for the right reason and look like a regression.
