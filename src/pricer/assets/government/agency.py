"""Government agency debentures — the class conventions, and a government-side path to the
shared option surface (template: ``assets/government/agency.py``).

Serves the master's **Government Agencies** sub-category: 42 rows -> 39 securities, routed
``vanilla`` 27 / ``callable-lattice`` 5 / ``call-passed-vanilla`` 4 / ``zero`` 2 /
``cmo-tranche`` 1.

⚠️ **Agencies have no engine of their own, and that is the honest headline.** Every route above
is priced by an engine migrated in Rounds 2a/2b: the optionless ones by
``core.pricing.analytical``, the five live callables by ``core.pricing.tree`` through the shared
``assets.corporate.embedded_option`` surface. Nothing was ported for this class. What this
module adds is the part that was genuinely unwritten — the rules by which an agency result is
*read*.

⚠️ **This module does not route.** Which engine a security reaches is decided in exactly one
place, ``dataio.phase2._route_agency``, with its named constants ``ZERO_COUPON_MAX_PCT``,
``MAKE_WHOLE_MAX_GAP_DAYS``, ``_DATE_PAIR`` and ``_CMO_CLASS``. Re-stating any of those rules
here would put two files in charge of one decision — the defect pattern this project has found
and closed five times. A reader looking for the routing rules should go there.

The class conventions, documented rather than re-implemented
------------------------------------------------------------
* **Bermudan par call at 100 from the custodian AB date**, at a short-rate volatility of
  :data:`SIGMA_DEFAULT` (0.15, Mario's v1 choice of 2026-07-03 and the industry default for
  agency debentures). ⚠️ The par-call price is applied when a row is **seeded** into
  ``data/call_schedules.csv``, never inferred in code, and every seeded row carries
  ``exercise_terms_status = provisional``: a custodian date with a market convention laid on
  top, confirmed by nobody. Zero of the nine rows are confirmed.
* **A call date already in the past is not a call.** Four securities carry a maturity/call
  date PAIR in their description with no AB date: the one-time call came and went unexercised,
  so the bond is a bullet. It is flagged, not silently treated as optionless.
* **A misfiled security is refused, not force-priced.** ``TNTD04733316`` ("FHLMC SER 3122 CL
  ZB") is a REMIC accrual tranche sitting in the agency sub-category; it is carried at the
  custodian mark and belongs to the CMO phase. Forcing a debenture model onto it would produce
  a number that looks fine and means nothing — the Sempra lesson.

Units are the legacy sheet's: coupon in PERCENT, prices per 100, spreads in BASIS POINTS,
volatility in DECIMAL.
"""
from __future__ import annotations

from pricer.assets.corporate.embedded_option import (  # noqa: F401
    DEFAULT_VOL_SCENARIOS,
    SIGMA_DEFAULT,
    VOL_POINT,
    ExerciseScheduleNotRepresentable,
    calculated_price,
    check_representable,
    convexity,
    duration,
    dv01,
    implied_oas,
    implied_oas_at_volatility,
    price_at_volatility,
    tightening,
    volatility_sensitivity,
    widening,
)

# ---------------------------------------------------------------------------------------
# Reading a callable agency result: two spreads, side by side.
#
# The driver calibrates each callable debenture TWICE — once with the call in the model and
# once as if it were a bullet — and the pair is what carries the information. These three
# thresholds decided how that pair was described, and until now they were unnamed numbers
# inside scripts/phase2_risk.py. Naming them is the point of this block.
# ---------------------------------------------------------------------------------------

#: Below this the callable spread is not a spread at all. A negative option-adjusted spread
#: means no credit spread reprices the bond once the call is valued, i.e. the Bermudan
#: par-call-from-AB assumption conflicts with the custodian price. It is a statement about
#: our ASSUMPTION, not about the bond — hence "lie detector".
LIE_DETECTOR_BP = 0.0

#: Above this gap the market is not pricing the call we assumed. In 2009 agencies frequently
#: did NOT call, so a callable spread far wider than the same bond's straight spread means the
#: market is pricing extension — or the Bermudan par-call assumption is too strong for an MTN.
EXTENSION_PRICING_GAP_BP = 100.0

#: Within this gap the call has no economic effect: the two calibrations agree, so the option
#: is out of the money at every node. The bond prices as a bullet and the number is sound.
CALL_NOT_BINDING_GAP_BP = 1.0


def option_verdict(oas_callable_bp: float, oas_straight_bp: float) -> str:
    """How to read a callable agency's two calibrated spreads.

    Inputs
    ------
    1. oas_callable_bp : float — spread in bp from the calibration WITH the call in the model.
    2. oas_straight_bp : float — spread in bp from the same bond calibrated as a bullet.

    Returns: str — one of

    ``"lie-detector"``
        The callable spread is negative (:data:`LIE_DETECTOR_BP`). Our call terms are wrong
        for this bond, most likely a one-time call recorded as a Bermudan par call. The
        number must not be published as a credit spread.
    ``"extension-priced"``
        The callable spread exceeds the straight one by more than
        :data:`EXTENSION_PRICING_GAP_BP`. The market is pricing the bond to maturity, not to
        the call. Reportable as a finding; the bond is kept, flagged.
    ``"call-not-binding"``
        The two agree within :data:`CALL_NOT_BINDING_GAP_BP`. The option never binds, and the
        callable and bullet numbers are the same number.
    ``"call-active"``
        The ordinary case: the call has value and the option-adjusted spread is the credit
        spread with that value removed.

    ⚠️ This function states the rule; it does not run in production. ``scripts/phase2_risk.py``
    applies the same thresholds inline to build its flag text, and the structure tests assert
    that this function reproduces the verdict on every callable row of the published output.
    Keeping the driver's wording untouched is deliberate — this round changes no output byte.
    """
    if oas_callable_bp < LIE_DETECTOR_BP:
        return "lie-detector"
    if oas_callable_bp - oas_straight_bp > EXTENSION_PRICING_GAP_BP:
        return "extension-priced"
    if abs(oas_callable_bp - oas_straight_bp) < CALL_NOT_BINDING_GAP_BP:
        return "call-not-binding"
    return "call-active"


def volatility_applies(route: str) -> bool:
    """Whether short-rate volatility is an input for a given agency route.

    Inputs
    ------
    1. route : str — the loader's route label for the security.

    Returns: bool — ``True`` only for ``"callable-lattice"``.

    Rationale, and why this is a function rather than a comment: for every other route the
    security carries no option, so there is nothing for volatility to act on. The project
    reports such sensitivities as **unused (null), never as zero** — a zero would read as
    "measured and found to be nil" when the truth is "not applicable". Same structural
    statement the vanilla and floating wrappers make.
    """
    return route == "callable-lattice"
