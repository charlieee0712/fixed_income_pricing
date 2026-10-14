"""Whether a securitised security's coupon MOVES — the one bit the holdings file cannot carry.

``data/coupon_structure.csv`` holds Bloomberg's ``Type of Coupon`` for every securitised and
agency security in the portfolio: **1,333 securities**, from the three files Mario sent on
2026-10-07. It exists because the custodian's ``income_rate`` (master column BG) reports a
*rate* and can never say whether that rate is fixed, and that single bit decides whether a
security's effective duration is its own life or close to zero.

The file is optional. A missing file means no data, never a default — the same contract as
``dataio.term_overrides`` and ``dataio.inflation``.

WHAT IS IN IT, AND WHAT IS DELIBERATELY NOT
-------------------------------------------
In: ``coupon_type`` and ``cpn_freq``, with the raw Bloomberg token kept beside the normalised
one so a reader can always get back to the source string.

⚠️ **NOT the coupon rate itself, and this was measured rather than assumed.** The source file
carries a ``Coupon`` column, and for a floater it is *not* the 2009-03-31 reset: joined to the
custodian's own figure, **259 of 259 fixed rows agree to within 1 bp (median difference exactly
0.0000) while 0 of 59 floating rows do**, the floating ones running a median **+1.21 points**
high with every difference positive. A third source breaks the tie — the custodian's own
``Asset description`` embeds the rate, and it matches the master on **48** rows and the source
file on **none**. ⇒ master BG is the valuation-date coupon, the source file's is stale, and
``scripts/tier1_structured.py`` was already reading the right one. Importing the other would
have moved 192 securities' cash flows for no reason.

⚠️ **The source file's ``STRUCTURED_NOTE_CPN_FORMULA`` block is still not here, but NOT for the
reason this docstring used to give.** It said the block was "not keyed to its rows", citing a
fixed 6.5% FNMA pass-through that carried ``1.000 * US0001M + 0.390%`` and an agreement rate
below chance. ⚠️ **RETRACTED 2026-10-14.** The field returns a **transposed table**, so each
security occupies SIX sheet rows while the identifier block runs at one; pairing by row number
fails, which is what that test detected, but the block was sound. The 437 fixed records among
the 505 priced pools match the custodian's own coupon EXACTLY (max |diff| 0.000000, 437 of 437).

⭐ The formulas live in ``data/mtge.xlsx`` / ``data/corp.xlsx`` and are read by
``dataio.coupon_formula``, deliberately a SEPARATE table from this one: this file answers
*does the coupon move*, that one answers *by what rule*. ⚠️ And a rule is still not a coupon —
an ARM's realised rate needs its own reset anniversary and its caps, neither of which the field
carries, so ``docs/missing_data.md`` G7a/G7d stay open.

WHY THE AGENCY ROWS COME FROM A DIFFERENT FILE
----------------------------------------------
``formulas_for_cpn_pmts.xlsx`` returns ``#N/A Invalid Security`` for 41 of its 42 Government
Agencies rows, which is presumably why a separate ``Agencies CPN Data.xlsx`` was produced. The
builder takes agencies from that file (35 rows upgraded) and everything else from the first,
and asserts the two CUSIP sets are identical before writing. ⇒ ``unresolved`` falls from 43 to
**5**, and all five are named in ``docs/missing_data.md`` rather than defaulted to anything.

⭐ STEP IS NOT A FLOATER, AND THE DISTINCTION IS LOAD-BEARING
------------------------------------------------------------
A stepped coupon changes on known dates and **not with rates**, so it keeps a fixed-cash-flow
duration and needs a coupon *schedule* — the ``data/coupon_schedules.csv`` route the corporate
book has used since 2026-07-08. A floating or variable coupon re-projects under a curve bump
and is the case where a fixed-schedule duration has the wrong magnitude. :func:`rate_behaviour`
keeps the three apart so a caller cannot collapse them by accident. (There are no stepped
securities inside Government MBS; all 6 are in the CMO and ABS classes.)
"""
from __future__ import annotations

import csv
import os

#: The normalised tokens. An unrecognised one is REFUSED, never mapped to something
#: reassuring — the rule ``dataio.call_schedules`` applies to exercise terms and
#: ``dataio.inflation`` to index-ratio status.
COUPON_TYPES = frozenset({"fixed", "zero", "floating", "variable", "step", "unresolved"})

#: How a coupon type behaves under a curve bump. ``None`` means unknown and must stay unknown.
_BEHAVIOUR = {
    "fixed": "fixed",
    "zero": "fixed",
    "step": "schedule",        # known dates, not rate-driven
    "floating": "rate-sensitive",
    "variable": "rate-sensitive",
    "unresolved": None,
}

_FIELDS = ("cusip", "isin", "sub_category", "desc_short", "coupon_type",
           "coupon_type_raw", "cpn_freq", "source_file", "source", "as_of")


def load_coupon_structure(path: str = "data/coupon_structure.csv") -> dict:
    """Bloomberg's coupon structure, per security.

    Inputs
    ------
    1. path : str — the CSV. A missing file yields ``{}``; it is data, not a requirement.

    Returns: ``{asset_id: {"cusip", "isin", "sub_category", "desc_short", "coupon_type",
    "coupon_type_raw", "cpn_freq", "source_file", "source", "as_of"}}``, where ``cpn_freq``
    is an ``int`` or ``None`` and every other value is a ``str``.

    Raises ``ValueError`` on a ``coupon_type`` outside :data:`COUPON_TYPES`, and on a repeated
    ``asset_id`` whose rows disagree — the holdings master lists 13 of these securities more
    than once, every duplicate agrees, and a silent last-one-wins is how two owners of one
    fact begin.
    """
    out: dict = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            asset_id = (row.get("asset_id") or "").strip()
            if not asset_id:
                continue
            kind = (row.get("coupon_type") or "").strip().lower()
            if kind not in COUPON_TYPES:
                raise ValueError(
                    "unrecognised coupon_type %r for %s; expected one of %s"
                    % (kind, asset_id, sorted(COUPON_TYPES)))
            freq = (row.get("cpn_freq") or "").strip()
            rec = {name: (row.get(name) or "").strip() for name in _FIELDS}
            rec["coupon_type"] = kind
            rec["cpn_freq"] = int(float(freq)) if freq else None
            prior = out.get(asset_id)
            if prior is not None and prior["coupon_type"] != kind:
                raise ValueError(
                    "%s appears twice with different coupon types (%s, %s)"
                    % (asset_id, prior["coupon_type"], kind))
            out[asset_id] = rec
    return out


def rate_behaviour(coupon_type: str):
    """How a coupon type responds to a curve bump.

    Inputs
    ------
    1. coupon_type : str — one of :data:`COUPON_TYPES`.

    Returns ``"fixed"`` (the cash flows do not move), ``"schedule"`` (they change on known
    dates but not with rates, so a fixed-schedule duration is right once the schedule is
    supplied), ``"rate-sensitive"`` (a curve bump re-projects the coupon), or ``None`` when
    the type is ``unresolved``.

    ⚠️ ``None`` is not ``"fixed"``. A caller that needs a decision must name the security,
    the way every other unresolved term in this project is named rather than assumed.
    """
    kind = (coupon_type or "").strip().lower()
    if kind not in COUPON_TYPES:
        raise ValueError("unrecognised coupon_type %r; expected one of %s"
                         % (kind, sorted(COUPON_TYPES)))
    return _BEHAVIOUR[kind]
