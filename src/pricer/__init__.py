"""``pricer`` — the target code structure (Mario's template, Ver Aug 5 2026).

Layout = ``core/`` (reusable engines, ~80% of code) + ``assets/`` (thin per-asset
wrappers, ~20%). Many simple functions, every input documented — see
``assets/corporate/bonds_input.py`` for the per-function input catalogue and the
legacy "Monthly" sheet it mirrors.

Migration status (sample = the corporate vanilla chain; the rest follows on approval):

  core/pricing/analytical.py    DONE   was pricing/bond_price.py  (DCF engine)
  core/pricing/cashflows.py     DONE   cash-flow generation + THE accrued formula
  core/pricing/discounting.py   DONE   DF / PV + legacy-compat rates
  core/risk/sensitivities.py    DONE   DV01 / duration / convexity, engine-agnostic
  core/market/spreads.py        DONE   implied-spread calibration (Brent), near-maturity flag
  core/market/curves.py         POINTER re-exports curves/ (bootstrap + ZeroCurve move later)
  core/utils/dates.py           DONE   ACT/364 calendar, the 182-day schedule walk
  assets/corporate/bonds_input.py DONE the input catalogue (highlighted parameters)
  assets/corporate/vanilla.py   DONE   per-metric functions (CorpBondOAS/Duration/... shape)
  core/pricing/tree.py          PLANNED  from pricing/lattice.py   (callable/putable BDT)
  assets/corporate/callable.py  PLANNED  thin wrapper over tree.py
  assets/corporate/floating.py  PLANNED  from pricing/frn.py + hybrid.py
  core/pricing/prepayment.py    PLANNED  from pricing/mbs.py (CPR/SMM; awaiting data)
  assets/government/, securitized/ PLANNED from pricing/ilb.py, phase2 drivers
  endpoints/                    PLANNED  batch runners (today: scripts/)

Old import paths (``pricing.bond_price`` etc.) keep working — they are thin shims
over these modules, so every existing driver, test and golden number is unchanged.
"""
