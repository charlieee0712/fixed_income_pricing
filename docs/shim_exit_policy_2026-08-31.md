# Shim and migration policy — how the old import paths eventually go away

**2026-08-31 · policy, adopted; no shim is retired now**

## Why this document exists

When the code was reorganised into `src/pricer/` for the Google team (Mario's directive of
2026-08-15), the old module paths were kept as **shims**: `src/pricing/bond_price.py` no longer
contains an engine, it re-exports the objects that now live in `src/pricer/core/`. That is what
let the reorganisation ship without a single number changing — every existing caller kept working,
and the migration was proven bit-identical rather than argued to be safe.

The risk with that pattern is well known: "temporary" compatibility layers become permanent
because nobody ever writes down what would end them. This document writes that down. It does not
retire anything.

## Current state, measured rather than remembered

**Seven modules in `src/pricing/` are shims**: `bond_price`, `calibrate`, `coupon_schedule`,
`frn`, `hybrid`, `lattice`, `risk`. Each re-exports objects from `pricer.*`; several tests assert
the re-exported object is the *same object* (`is`), so the two paths cannot drift apart.

**Two modules there are not shims at all** — `ilb.py` and `mbs.py` are unmigrated engines. They
are not covered by this policy; they move under the data/scope rule below.

**All three production drivers still import the legacy surface**, which is worth stating plainly
because it means the first exit criterion is currently *unmet*:

| caller | still imports |
|---|---|
| `scripts/calibrate_risk.py` | `pricing.calibrate`, `pricing.coupon_schedule`, `pricing.frn`, `pricing.hybrid`, `pricing.risk` |
| `scripts/callable_risk.py` | `pricing.bond_price`, `pricing.lattice` |
| `scripts/phase2_risk.py` | `pricing.bond_price`, `pricing.calibrate`, `pricing.ilb`, `pricing.lattice`, `pricing.risk` |

Tests import both paths deliberately — that is how the equivalence is pinned — so test imports are
not evidence either way.

## Exit criteria — all four, not any of them

A shim may be removed only when:

1. **every in-repo production caller imports the `pricer.*` path.** Today: not met, see above.
2. **the Google team has received and exercised the new public surface.** They now attend the
   briefings, and the JSON endpoint is the surface they were given; "exercised" means they have
   actually run against it, not that it was delivered.
3. **at least one release cycle has passed with the deprecation documented.** Written in the
   report the recipients read, not only in a docstring.
4. **removal has its own migration plan and a golden-output freeze**, in the shape this project
   already uses: hashes of all five production CSVs before and after, byte-identical.

Criterion 4 is the one that makes the others safe. A shim removal cannot change a number, so if it
does, the freeze catches it.

## Which layers migrate next, and on what trigger

**Not for neatness.** The five remaining layers stay where they are until an active task benefits:

| layer | trigger |
|---|---|
| `pricing/mbs.py` | when the requested pool data arrives from Mario or Liping |
| `pricing/ilb.py` | only if Mario selects that work |
| `curves/`, `credit/`, `dataio/` | only when an active task needs the move |

The migrations done so far were all pulled by real work — the vanilla chain by the structure
sample, the tree by Round 2a's embedded options, floating and hybrid by Round 2b's column F. Each
carried its own parity proof. A migration with no task behind it has the same risk and none of the
benefit, and it spends review attention that the numbers have a better claim on.

## The one thing to watch while the shims live

A shim's job is to be transparent, and the failure mode is a shim that starts doing something.
Two rules, both already in force:

- **Edit the `pricer.*` module, never the shim.** The shim holds imports and a docstring.
- **Where a shim re-exports a private name, say so and test it.** `src/pricing/frn.py`
  deliberately re-exports `_as_date`, `_rate`, `_df` and `simple_forward`, because the hybrid
  engine reached across for them. As of 2026-08-31 those are aliases of public functions in
  `core/pricing/discounting.py` and `core/utils/dates.py`, so the seam is documented rather than
  hidden — but the re-export stays until the shim itself goes.
