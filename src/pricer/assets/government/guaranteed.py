"""Guaranteed fixed income — FDIC-TLGP crisis paper (template:
``assets/government/guaranteed.py``).

Serves the master's **Guaranteed Fixed Income** sub-category: 11 rows -> 9 securities, every
one of them ``vanilla``. There is no engine here and no arithmetic; the bonds price on
``core.pricing.analytical`` exactly as any optionless bond does, through the corporate vanilla
surface re-exported below.

What makes the class a class is a **reporting** rule, not a pricing one — which is why nine
plain bonds need a module at all.

⚠️ **The credit being priced is the government's, not the bank's.** These are bonds issued by
banks in 2008-09 under the FDIC's Temporary Liquidity Guarantee Program: the issuer's name is
on the paper, but the United States government guarantees the payments. Putting a
TLGP-guaranteed bond into its issuer's rating bucket would mix a government-guaranteed spread
into a bank-credit average and make both numbers wrong — the bank bucket too tight, the
guaranteed spread invisible. The class therefore reports as its OWN bucket, always.

This is applied in production by ``dataio.phase2``, which sets ``group = "TLGP-guaranteed"``
for every security in the class. :func:`reporting_bucket` is the named statement of the same
rule, so that the reason is written down somewhere other than a comment on one line of a
loader, and so that it can be tested.
"""
from __future__ import annotations

from pricer.assets.corporate.vanilla import (  # noqa: F401
    calculated_price,
    convexity,
    duration,
    dv01,
    implied_oas,
    tightening,
    widening,
)

#: The one bucket every security in this class reports in.
TLGP_BUCKET = "TLGP-guaranteed"


def reporting_bucket(issuer_rating_bucket=None) -> str:
    """The rating bucket a guaranteed security reports in.

    Inputs
    ------
    1. issuer_rating_bucket : str | None — the ISSUING BANK's own rating bucket, if the
       caller happens to have it. **Accepted and deliberately not used** — the same
       "echoed but not applied" convention the endpoint uses for inputs that must be seen
       to be refused rather than silently ignored.

    Returns: str — always :data:`TLGP_BUCKET`.

    ⚠️ The argument exists to make the refusal explicit at the call site. A caller holding a
    bank rating for one of these bonds is holding the rating of the wrong obligor: the payment
    comes from the FDIC guarantee. Returning the issuer's bucket here would be the quiet kind
    of error — every number still computes, and a bank-credit average silently absorbs nine
    government-guaranteed spreads.
    """
    return TLGP_BUCKET
