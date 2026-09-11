"""Sovereign and sub-sovereign bonds — the government-side path to the shared engines
(template: ``assets/government/sovereign.py``).

Serves the two classes built on 2026-09-03: **Government Bonds** (153 rows -> 147 securities)
and **Municipal/Provincial Bonds** (7 -> 7). Their driver is ``scripts/sovereign_risk.py``.

Why this module exists
----------------------
``scripts/sovereign_risk.py`` prices one genuinely callable **US Treasury** — a 12.5% 2014
bond with a call in August 2009 — and to do it, it imports
``pricer.assets.corporate.embedded_option``. A government driver reaching into a module named
*corporate* to price a Treasury is a naming problem, and this package is the right place to
fix it: government code now takes the shared surface from a government-side path.

⚠️ **The shared surface is mis-located, not mis-written, and it is NOT moved.** One binomial
lattice prices every bond with an embedded option in this book — corporate callables, agency
debentures and that Treasury alike — and having one implementation is the point. Relocating it
to a level both asset families can see would touch the corporate tree cluster and the hashed
CSVs behind it, for a naming gain. Recorded instead as a follow-up with its own trigger: move
it when a third non-corporate caller appears, or alongside the securitized layer.

Conventions that belong to this book, and where they live
---------------------------------------------------------
Each has exactly one owner, named here so a reader can find it rather than re-deriving it:

* **Discount on the OWN-CURRENCY curve, never a per-country curve.** ``dataio.phase2`` routes
  the sovereign classes; ``curves.zero_curve.CURVE_FILE`` maps the fourteen currencies. The
  decider was coverage, not taste — Ireland has no curve file of its own, so a per-country rule
  would split two Irish holdings from twenty-eight euro peers.
* ⚠️ **``EUR_Yield_Curve.txt`` is a euro-area sovereign COMPOSITE, not a bank-lending curve**
  (verified: it lies strictly between the German and Italian curves at every tenor, and a
  debt-weighted average of six countries reproduces it to 7bp mean). So a euro sovereign's
  spread is relative value against the euro average — never an asset-swap spread. The output
  says which reading applies, per row, in ``spread_meaning``.
* **Par-as-titles quotation.** ``dataio.phase2.TITLE_FACE`` is an explicit per-currency
  registry, never a price sniffer: the identity that detects the quotation cannot tell you the
  denomination, because it holds for MXN 100 and BRL 1000 alike.
* **Custodian duration (AQ) is evidence, never a router.** It means different things per class,
  so a rule keyed on it would have priced the corporate callables as bullets.

Units are the legacy sheet's: coupon in PERCENT, prices per 100, spreads in BASIS POINTS.
"""
from __future__ import annotations

from pricer.assets.corporate.embedded_option import (  # noqa: F401
    SIGMA_DEFAULT,
    ExerciseScheduleNotRepresentable,
    check_representable,
)
from pricer.assets.corporate.embedded_option import calculated_price as callable_price
from pricer.assets.corporate.embedded_option import convexity as callable_convexity
from pricer.assets.corporate.embedded_option import duration as callable_duration
from pricer.assets.corporate.embedded_option import dv01 as callable_dv01
from pricer.assets.corporate.embedded_option import implied_oas as callable_implied_oas
from pricer.assets.corporate.vanilla import (  # noqa: F401
    calculated_price,
    convexity,
    duration,
    dv01,
    implied_oas,
    tightening,
    widening,
)

#: What a calibrated spread MEANS for a sovereign, which depends on the curve it was measured
#: against. The output carries one of these per row; mixing them in one average is the error
#: this vocabulary exists to prevent.
SPREAD_MEANINGS = (
    "own-curve-anchor",             # the bond's own government is the curve: ~0 by construction
    "relative-to-euro-composite",   # a euro sovereign vs the euro-area average, not a credit spread
    "spread-over-government",       # a sub-sovereign or foreign issuer over that currency's govt
)
