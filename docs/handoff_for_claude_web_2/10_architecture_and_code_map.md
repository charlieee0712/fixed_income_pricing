# Architecture and code map

What exists, where, and which parts have been migrated into the approved layout.

---

## 1. The three layers

Mario's directive (2026-08-15) was: the code is "difficult to follow, a bit nested"; a Google
team is taking it over for cloud optimisation; therefore **many simple functions**, not one
complicated one, with **inputs highlighted** per function. His template is roughly 80%
reusable engines, 20% thin per-asset wrappers, plus an API layer.

```text
core/       reusable mathematics. Knows nothing about a bond type or a transport.
assets/     one short file per bond type. Legacy units, documented inputs, NO arithmetic.
endpoints/  one request in, one result out. NO arithmetic either.
```

The discipline that makes this real: a new bond type is a new file in `assets/`, never a new
engine. When two bond types need the same mathematics with a different right attached, the
right goes in the wrapper and the mathematics stays in `core/`.

## 2. The live tree

```text
src/pricer/
├── __init__.py                 the map: what is DONE vs PLANNED, and where each piece came from
├── core/
│   ├── pricing/
│   │   ├── cashflows.py        cash-flow table + THE accrued formula + lattice_inputs
│   │   ├── discounting.py      DF = exp(-t(z+s)); the vba_compat reproduction of the legacy bug
│   │   ├── analytical.py       plain fixed-rate bonds — ~25 lines of orchestration
│   │   └── tree.py             the short-rate lattice: call / put / sinking, + schedule_times,
│   │                           bond_tree, sink_arrays                        [NEW 2026-08-25]
│   ├── risk/sensitivities.py   DV01 / effective duration / convexity as pure arithmetic on
│   │                           three prices — point it at ANY pricing function
│   ├── market/
│   │   ├── curves.py           resolve_curve · curve_id · CurveUnavailable · flat_zero_curve;
│   │   │                       re-exports the validated ZeroCurve
│   │   └── spreads.py          solve_spread_to_price (the OAS inverse) · near_maturity
│   └── utils/dates.py          the 364/182 calendar and the one schedule walk
├── assets/corporate/
│   ├── bonds_input.py          the input catalogue: every field, its units, whether it is used,
│   │                           and the JSON path an external caller uses
│   ├── vanilla.py              plain bonds — one function per output
│   ├── embedded_option.py      the shared surface for every tree product      [NEW]
│   ├── callable.py             thin: names the call schedule                  [NEW]
│   ├── puttable.py             thin: names the put schedule                   [NEW]
│   └── sinking.py              thin: names the redemption schedule + basis    [NEW]
└── endpoints/
    ├── main.py                 analyze_vanilla_payload(payload) -> response; never raises
    ├── contracts.py            normalisation, validation, envelopes — stdlib only
    ├── pricing.py              the seven-step orchestration
    └── dependencies.py         the ONLY environment-aware file (FIP_DATA_DIR)
```

## 3. What has NOT been migrated

These still live at their original paths and are the real implementations:

```text
src/pricing/frn.py        the FRN engine            <- Round 2b migrates this
src/pricing/hybrid.py     fixed-then-float          <- depends on frn.py's PRIVATE names
src/pricing/ilb.py        inflation-linked
src/pricing/mbs.py        the static-CPR skeleton
src/pricing/coupon_schedule.py   stepped / step-up coupon tables
src/curves/               bootstrap + ZeroCurve (re-exported by core/market/curves.py)
src/credit/               ratings notch-map + the archived OAS history reader
src/dataio/               loaders, universe funnel, coupon types, term overrides,
                          call schedules, phase-2 loaders
src/recon/                the Monthly-sheet replica (never imported by production)
```

Migrated already: `pricing/bond_price.py`, `calibrate.py`, `risk.py`, `lattice.py` — all now
**shims**. A test asserts the shim re-exports the *same object*, not a copy.

## 4. Drivers and scripts

```text
scripts/calibrate_risk.py    the corporate book: universe -> routes -> calibrate -> risk
scripts/callable_risk.py     the corporate callables on the lattice
scripts/phase2_risk.py       agencies / guaranteed / inflation-linked
scripts/price_json.py        request file -> response file (what Excel invokes)
scripts/md_to_pdf.py         markdown -> styled PDF, one local command
scripts/demo_volatility.py   the callable volatility table, for the live demo
scripts/monthly_*.py         the Monthly-sheet extraction and reconciliation runs
scripts/init_call_schedules.py   seeds data/call_schedules.csv from the master AB column
```

All drivers are environment-parameterised: `FIP_VAL_DATE`, `FIP_OUT`, `FIP_DATA_DIR`,
`FIP_VOL`, `FIP_INFL`.

## 5. Integrations

```text
integrations/excel_vba/
├── RysePricingBridge.bas    the adapter: cells -> JSON -> command -> JSON -> cells
├── JsonConverter.bas        VBA-JSON v2.3.1 (Tim Hall, MIT), vendored unmodified
├── LICENSE_JSON_PARSER.txt  provenance and licence
├── runner_example.cmd       the one configurable seam
├── README.md                install, named ranges, runner config, fixture testing
├── examples/                REAL request/response pairs, generated by running the CLI
├── tests/                   23 checks driving actual Excel (PowerShell + a VBA harness)
└── demo/                    the demonstration workbook, its builder, and a run sheet
```

## 6. Why the shims matter more than they look

Every migration so far has been provable *because* the old paths kept working: the entire
pre-existing test suite ran unchanged against the moved code, and the three production
drivers produced byte-identical CSVs. That is a much stronger claim than "the new tests
pass", and it is only available while the shims exist.

Retiring them is a separate, deliberate decision that has not been taken.

## 7. Reading the code cold

If a plan needs to reference real files, the fastest orientation is:

1. `src/pricer/__init__.py` — the map, with a DONE/PLANNED table;
2. `assets/corporate/vanilla.py` and `callable.py` — see how thin a wrapper is;
3. `core/pricing/analytical.py` — see how little the price function does;
4. `core/pricing/tree.py` — the one genuinely intricate file, and its docstring carries the
   model, the conventions and the sinking-fund reasoning;
5. `endpoints/main.py` — the whole external surface, in about 50 lines.
