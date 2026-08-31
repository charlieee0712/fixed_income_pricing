"""The project's own exception family.

Every failure this package raises deliberately is one of these, and they descend from
``Exception`` rather than from ``ValueError`` for a reason that has now cost three
debugging sessions.

**The problem being solved.** A spread solver has to catch *something* around its pricing
callback: a bond that cannot be repriced to its mark at any spread is a real, reportable
outcome. When the engine's refusals were also ``ValueError``, that catch swallowed them,
and a contradictory pair of exercise dates came back as

    "no spread reprices this bond - check the price, the coupon and the maturity"

— three fields, every one of them correct, and the reader sent to the wrong file. It
happened with the sinking-fund basis, then with a schedule the model grid could not place,
then with a put priced above a call. Each was fixed in the place it surfaced, and the next
one arrived anyway, because *being a ``ValueError``* was the defect.

**The rule.** A refusal that describes the CONTRACT is a :class:`ContractTermsError`. A
failure of the SOLVER is a :class:`CalibrationError`. Nothing else may be reported as a
calibration failure, and a broad ``except ValueError`` can no longer reach either.

``ValueError`` keeps its ordinary meaning here: a caller passed something malformed — a
coupon in the wrong units, a frequency the engine does not support, a schedule that is not
a list of pairs. Those are programming errors at the call site, not statements about a
bond, and they should keep propagating.
"""
from __future__ import annotations


class PricingDomainError(Exception):
    """Base for every deliberate refusal or failure raised by the pricing package.

    Deriving from ``Exception`` rather than ``ValueError`` is the whole point: no generic
    numeric-input handler anywhere can absorb one of these by accident.
    """


class ContractTermsError(PricingDomainError):
    """The instrument's terms, as described, cannot be priced.

    Not a solver failure and not bad input formatting — a statement about the bond. The
    caller usually has to change a term, a schedule or a source, so the exception carries
    the JSON path of the field to look at.

    Inputs
    ------
    1. message : str — plain-language explanation, safe to show in a spreadsheet cell.
    2. field   : str — the request path at fault, e.g. ``"bond.call_schedule"``. The
       endpoint uses it verbatim; defaults to ``"bond"`` when no field is more specific.
    """

    def __init__(self, message, field="bond"):
        super().__init__(message)
        self.field = field


class ExerciseTermsError(ContractTermsError):
    """Exercise rights — call, put, sinking — that cannot be priced as described.

    Covers contradictory prices on one date, a put above a call, a sinking date colliding
    with a call, a fraction basis the engine does not implement, a schedule entirely after
    maturity, and a schedule the model's time grid cannot place.
    """


class CalibrationError(PricingDomainError):
    """No spread reprices the instrument to the given price.

    Raised only by the root finders, and the ONLY thing an endpoint or driver may report as
    a calibration failure. If this is raised, the terms were fine and the arithmetic was
    fine; the price and the terms simply do not meet.
    """
