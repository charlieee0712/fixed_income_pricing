"""Monthly factor history — the observed record of how much principal came back, when.

A **factor** is one number per security per month: the fraction of the original balance
still outstanding. ``1.00`` means nothing has been repaid, ``0.40`` that 60% has come back,
``0.00`` that the security is finished. A monthly series of them is therefore a complete
record of the paydown, and — this is the point of the whole route — **it records the
OUTCOME of a deal's rules without anybody needing to know the rules**:

    principal(t) = original_face x ( factor(t-1) - factor(t) )
    interest(t)  = original_face x   factor(t-1)             x coupon / 12

⭐ Pricing per 100 of CURRENT face needs only factor RATIOS, never the original face, so
``original_face`` cancels and is never read. That deletes the ``orig_face = par / factor``
derivation, which is just as well: ``orig_face`` is empty in the master.

Source: ``data/factor_history.csv``, 376 securities x 211 months, returned by Liping from a
Bloomberg terminal on 2026-10-01 and verified complete (79,336 of 79,336 values, zero gaps).
Missing file = no history, the same convention as every other optional table here.

⚠️⚠️⚠️ **THE T+1 CONVENTION, AND THIS MODULE IS ITS ONLY OWNER.**
Bloomberg's month label sits **one month ahead** of the custodian's: the column it calls
``2009-04`` IS the position as at **2009-03-31**. Measured against the custodian's own
``paydown_factor`` over 373 securities:

====================  ==========================  ===============
the row labelled      median relative difference  within 1e-6
====================  ==========================  ===============
``2009-03``           1.6e-02                     78 / 373
**``2009-04``**       **2.9e-08**                 **370 / 373**
``2009-05``           1.6e-02                     72 / 373
====================  ==========================  ===============

On ``3133T5MR1`` the labelled row is wrong by a factor of **six** (custodian 0.00196067;
Bloomberg's ``2009-03`` 0.01212421, its ``2009-04`` 0.00196067).

⚠⚠ **CORRECTED 2026-10-23 — this lag is a property of THESE SECURITIES, not a house
convention, and the module is scoped accordingly.** It was recorded here as "the same house
convention as the TIPS index ratios (2026-09-19) — the custodian strikes at T+1". That
explanation is refuted by its own logic: a custodian striking a day late would do it to every
security it holds. Measured per security against the custodian's own ``paydown_factor``, the
Government MBS pools this module serves shift (**238 of the 241 that can be decided**), while
private-label CMOs mostly do **not** (168 of 191) and 23 of them shift anyway — so no rule
keyed on asset class is safe either. The constant below stays correct for the 376; **a caller
loading any other population must align per security and must not reuse this module's lag.**
See ``docs/three_tier_method_explained_2026-10-06.md`` §3.17.

**So the CSV keeps Bloomberg's own labels, unshifted**, because a stored record should be
checkable against what the terminal returned; and every caller receives *as-of dates*
instead, because three "two owners, one decision" bugs in this project were all one
convention applied in two places. ``bloomberg_month`` is named that way so no reader can
mistake it for an as-of date.

⚠️ **Two things a factor path may legitimately do, so neither is validated away:**

* **exceed 1.0** — a REMIC accrual tranche (Z / VZ / ZC) rolls its interest into its own
  balance, so its factor *grows*. Confirmed against the master in 2026-07-22.
* **rise month on month** — the same case. ``principal(t)`` then comes out **negative**,
  which is correct and is exactly what an accrual tranche does: the negative principal and
  the positive interest cancel to zero net cash, with no special-casing anywhere.
"""
from __future__ import annotations

import csv
import datetime as dt
import os

#: ⚠️ THE SINGLE OWNER OF THE T+1 SHIFT. Bloomberg's label is this many months AHEAD of
#: the position date it describes. Nothing else in the codebase may apply it again.
BLOOMBERG_MONTH_LAG = 1

FACTOR_FILE = "factor_history.csv"
SECURITIES_FILE = "factor_history_securities.csv"

#: The 2026-10-23 delivery for the 412 CMO / CMBS / ABS securities, same three columns.
#: ⚠️ **Its population does not share the lag above** — most of these do not shift at all.
#: Pass the alignment table to :func:`factor_path` when reading it.
FACTOR_FILE_412 = "factor_history_412.csv"

#: Per-security month lag, derived by :mod:`scripts.build_factor_alignment` from the
#: custodian's own ``paydown_factor``. Missing file = fall back to :data:`BLOOMBERG_MONTH_LAG`.
ALIGNMENT_FILE = "factor_alignment.csv"

#: A lag is an answer about neighbouring months. Anything further is not an alignment.
MAX_MONTH_LAG = 2

#: How a row's lag was arrived at. ``matched``/``nearest`` mean the security's own factor
#: picked the month; the rest mean it could not, and the class majority was used.
ALIGNMENT_STATUSES = frozenset({"matched", "nearest", "tied", "no-custodian-factor",
                                "unmatched", "out-of-range"})


def _shift_month(year: int, month: int, by: int) -> tuple[int, int]:
    i = (year * 12 + (month - 1)) + by
    return i // 12, i % 12 + 1


def bloomberg_month_for(as_of: dt.date, lag: int = BLOOMBERG_MONTH_LAG) -> str:
    """The label Bloomberg files a given position date under. ``2009-03-31`` -> ``2009-04``.

    ``lag`` defaults to :data:`BLOOMBERG_MONTH_LAG`, which is correct for the Government MBS
    pools. ⚠️ For any other population pass the security's own lag from
    :func:`load_factor_alignment` — see ``three_tier_method_explained`` §3.17.
    """
    y, m = _shift_month(as_of.year, as_of.month, lag)
    return f"{y:04d}-{m:02d}"


def as_of_for(bloomberg_month: str) -> tuple[int, int]:
    """The ``(year, month)`` a Bloomberg label actually describes. ``2009-04`` -> 2009-03."""
    y, m = (int(x) for x in bloomberg_month.split("-"))
    return _shift_month(y, m, -BLOOMBERG_MONTH_LAG)


def load_factor_history(data_dir: str = "data",
                        filename: str = FACTOR_FILE) -> dict[str, dict[str, float]]:
    """``{cusip: {bloomberg_month: factor}}``. Missing file = ``{}``.

    ``filename`` selects the pull: :data:`FACTOR_FILE` (the 376 Government MBS pools) by
    default, or :data:`FACTOR_FILE_412`. They are separate files because they are separate
    deliveries and a stored record should stay checkable against what the terminal returned.

    ⚠️ The keys are Bloomberg's labels, NOT as-of dates. Callers should use
    :func:`factor_path`, which hands back a path already aligned to a valuation date.
    """
    path = os.path.join(data_dir, filename)
    if not os.path.exists(path):
        return {}
    out: dict[str, dict[str, float]] = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            v = row["factor"].strip()
            if not v:
                continue
            f = float(v)
            if f < 0:
                raise ValueError(
                    f"factor_history: negative factor {f} for {row['cusip']} at "
                    f"{row['bloomberg_month']}; a balance fraction cannot be negative")
            out.setdefault(row["cusip"], {})[row["bloomberg_month"]] = f
    return out


def load_request_groups(data_dir: str = "data") -> dict[str, str]:
    """``{cusip: request_group}`` — which bucket of the 2026-09-29 request it came from."""
    path = os.path.join(data_dir, SECURITIES_FILE)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {r["cusip"]: r["request_group"] for r in csv.DictReader(fh)}


def load_factor_alignment(data_dir: str = "data") -> dict[str, dict]:
    """``{cusip: row}`` from :data:`ALIGNMENT_FILE`. Missing file = ``{}``.

    Each row carries ``month_lag`` (int), ``status``, ``lag_source``, ``residual``,
    ``matched_month``, ``sub_category`` and ``population``. ⭐ Read ``lag_source``: where it
    is ``class-majority-default`` the security's own factor could **not** choose the month,
    because it did not move — the lag is a named default and a driver should say so in its
    output rather than present it as measured.

    Raises ``ValueError`` on an unrecognised status, a non-integer lag, a lag beyond
    :data:`MAX_MONTH_LAG`, or a repeated CUSIP — the table is generated, so any of those
    means it was edited by hand.
    """
    path = os.path.join(data_dir, ALIGNMENT_FILE)
    if not os.path.exists(path):
        return {}
    out: dict[str, dict] = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            cusip = (row.get("cusip") or "").strip()
            if not cusip:
                continue
            if cusip in out:
                raise ValueError(f"factor_alignment: {cusip} appears twice")
            status = (row.get("status") or "").strip()
            if status not in ALIGNMENT_STATUSES:
                raise ValueError(
                    f"factor_alignment: unrecognised status {status!r} for {cusip}; "
                    f"expected one of {sorted(ALIGNMENT_STATUSES)}")
            try:
                lag = int(row["month_lag"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(
                    f"factor_alignment: {cusip} has a non-integer month_lag "
                    f"{row.get('month_lag')!r}") from None
            if abs(lag) > MAX_MONTH_LAG:
                raise ValueError(
                    f"factor_alignment: {cusip} has month_lag {lag}, beyond "
                    f"+/-{MAX_MONTH_LAG}; that is not an alignment")
            out[cusip] = dict(row, month_lag=lag, status=status)
    return out


def lag_for(cusip: str, alignment: dict[str, dict] | None = None) -> int:
    """The month lag to use for one security.

    Falls back to :data:`BLOOMBERG_MONTH_LAG` when no alignment table is supplied or the
    security is absent from it, which keeps every existing caller bit-identical.
    """
    if not alignment:
        return BLOOMBERG_MONTH_LAG
    row = alignment.get(cusip)
    return BLOOMBERG_MONTH_LAG if row is None else int(row["month_lag"])


def factor_path(history: dict[str, dict[str, float]], cusip: str, as_of: dt.date,
                alignment: dict[str, dict] | None = None) -> list[float]:
    """The observed factor path from ``as_of`` forward.

    Element 0 is the factor **at the valuation date**; element *k* is *k* months later.
    Returns ``[]`` when the security is absent, and stops at the first gap — a series that
    ends is a security that has finished paying, not an error.

    ⚠️ Without ``alignment`` the months are shifted by :data:`BLOOMBERG_MONTH_LAG`, which is
    measured-correct for the Government MBS pools and **wrong for most of the 412**. Pass
    :func:`load_factor_alignment` for any other population; the lag is then per security,
    because it is not a property of the vendor and not even of the asset class.
    """
    months = history.get(cusip)
    if not months:
        return []
    lag = lag_for(cusip, alignment)
    y, m = as_of.year, as_of.month
    out: list[float] = []
    while True:
        key = bloomberg_month_for(dt.date(y, m, 1), lag)
        if key not in months:
            break
        out.append(months[key])
        y, m = _shift_month(y, m, 1)
    return out


def coverage(history: dict[str, dict[str, float]]) -> dict[str, int]:
    """Counts worth asserting in a test rather than remembering."""
    return {
        "securities": len(history),
        "observations": sum(len(v) for v in history.values()),
        "rising_paths": sum(
            1 for v in history.values()
            if any(b > a for a, b in zip(
                [v[k] for k in sorted(v)], [v[k] for k in sorted(v)][1:]))),
    }
