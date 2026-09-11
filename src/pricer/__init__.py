"""``pricer`` — the target code structure (Mario's template, Ver Aug 5 2026).

Layout = ``core/`` (reusable engines, ~80% of code) + ``assets/`` (thin per-asset
wrappers, ~20%) + ``endpoints/`` (one request in, one answer out). Many simple
functions, every input documented — see the ``bonds_input.py`` in each asset family
for the per-function input catalogue and the legacy "Monthly" sheet it mirrors.

Read this map first: it is the fastest route from "where did the legacy VBA go" to the
file that answers it. It is kept honest by ``tests/test_pricer_structure.py``, which
fails if an entry claims a file that is absent, omits a file that exists, or leaves
something marked PLANNED after it has shipped.

core/ — the mathematics
-----------------------
  core/pricing/analytical.py      DONE  was pricing/bond_price.py (the DCF engine)
  core/pricing/cashflows.py       DONE  cash-flow generation + THE accrued formula
  core/pricing/discounting.py     DONE  DF / PV + legacy-compat rate conventions
  core/pricing/coupon_schedule.py DONE  dated coupon tables (stepped / step-up bonds)
  core/pricing/tree.py            DONE  was pricing/lattice.py — the ONE binomial
                                        short-rate lattice: callable, puttable, sinking
  core/pricing/floating.py        DONE  was pricing/frn.py — forward projection + reset
  core/pricing/hybrid.py          DONE  was pricing/hybrid.py — fixed leg then floating
  core/pricing/inflation.py       DONE  was pricing/ilb.py — index-linked (2026-09-10)
  core/pricing/prepayment.py      PLANNED  from pricing/mbs.py (CPR/SMM; awaiting the
                                        Bloomberg pool pull — the engine skeleton exists)
  core/risk/sensitivities.py      DONE  DV01 / duration / convexity, engine-agnostic
  core/market/spreads.py          DONE  implied-spread calibration (Brent) + near-maturity
  core/market/curves.py           DONE  curve resolution, the flat-curve helper and the
                                        CurveUnavailable seam; ZeroCurve itself still
                                        lives in curves/ and is re-exported here
  core/utils/dates.py             DONE  ACT/364 calendar, the 182-day schedule walk, and
                                        the ONE exercise-schedule conversion

assets/ — one short file per product, no arithmetic
---------------------------------------------------
  assets/corporate/bonds_input.py DONE  the corporate input catalogue (inputs 1-17)
  assets/corporate/vanilla.py     DONE  per-metric functions (CorpBondOAS/Duration/...)
  assets/corporate/embedded_option.py DONE the shared tree surface, the exercise-terms
                                        refusals, and the representability guard
  assets/corporate/callable.py    DONE  thin over embedded_option
  assets/corporate/puttable.py    DONE  thin over embedded_option
  assets/corporate/sinking.py     DONE  thin over embedded_option
  assets/corporate/floating.py    DONE  thin over core/pricing/floating
  assets/corporate/hybrid.py      DONE  thin over core/pricing/hybrid
  assets/corporate/stepped.py     DONE  thin over the coupon-schedule path
  assets/government/bonds_input.py DONE the government input catalogue — its OWN
                                        numbering, not a continuation of corporate's
  assets/government/linker.py     DONE  index-linked per-metric surface (2026-09-10)
  assets/government/agency.py     DONE  agency conventions + the option verdict rule
  assets/government/guaranteed.py DONE  the FDIC-TLGP reporting bucket
  assets/government/sovereign.py  DONE  government-side path to the shared engines
  assets/securitized/             PLANNED  with the MBS / CMO phase

endpoints/ — the outside world's single door
--------------------------------------------
  endpoints/main.py          DONE  analyze_payload(payload) -> response; failures are
                                   values, never exceptions
  endpoints/contracts.py     DONE  the request/response contract, standard library only
  endpoints/pricing.py       DONE  orchestration over the approved wrappers, zero formulas
  endpoints/dependencies.py  DONE  the only environment-aware file (swap for the cloud)
  errors.py                  DONE  the domain exception family, rooted at Exception so a
                                   solver's ``except ValueError`` cannot swallow a
                                   contract refusal and report it as a failed calibration

⚠️ **Two things this map does NOT say.**

*What is reachable from a worksheet is narrower than what exists here.* The engine and
the contract support seven instrument types; the Excel bridge can construct five. That
gap is deliberate — a type becomes reachable from a spreadsheet only once Mario has
chosen the layout for its inputs. The index-linked engine above is the current example:
migrated and wrapped, with no endpoint type, because the sheet has no cells for a real
coupon, an index ratio or an inflation assumption.

*Nothing here routes a security to an engine.* Routing lives in ``dataio`` — one owner
per book (``dataio.universe`` for corporate, ``dataio.phase2`` for the government and
sovereign classes). A wrapper that re-derived a routing rule would put two files in
charge of one decision, which is the defect pattern this project has closed five times.

Old import paths (``pricing.bond_price``, ``pricing.frn``, ``pricing.ilb`` …) keep
working — they are thin shims over these modules that re-export the SAME objects, so
every existing driver, test and golden number is unchanged. New code should import
``pricer.*`` directly; see ``docs/shim_exit_policy_2026-08-31.md`` for the four
conditions under which a shim may finally be retired (criterion 1 is not yet met).
"""
