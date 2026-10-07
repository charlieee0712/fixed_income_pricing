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
Bloomberg's ``2009-03`` 0.01212421, its ``2009-04`` 0.00196067). ⭐ The same house
convention was found independently on the TIPS index ratios (2026-09-19) — the custodian
strikes at T+1.

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


def _shift_month(year: int, month: int, by: int) -> tuple[int, int]:
    i = (year * 12 + (month - 1)) + by
    return i // 12, i % 12 + 1


def bloomberg_month_for(as_of: dt.date) -> str:
    """The label Bloomberg files a given position date under. ``2009-03-31`` -> ``2009-04``."""
    y, m = _shift_month(as_of.year, as_of.month, BLOOMBERG_MONTH_LAG)
    return f"{y:04d}-{m:02d}"


def as_of_for(bloomberg_month: str) -> tuple[int, int]:
    """The ``(year, month)`` a Bloomberg label actually describes. ``2009-04`` -> 2009-03."""
    y, m = (int(x) for x in bloomberg_month.split("-"))
    return _shift_month(y, m, -BLOOMBERG_MONTH_LAG)


def load_factor_history(data_dir: str = "data") -> dict[str, dict[str, float]]:
    """``{cusip: {bloomberg_month: factor}}``. Missing file = ``{}``.

    ⚠️ The keys are Bloomberg's labels, NOT as-of dates. Callers should use
    :func:`factor_path`, which hands back a path already aligned to a valuation date.
    """
    path = os.path.join(data_dir, FACTOR_FILE)
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


def factor_path(history: dict[str, dict[str, float]], cusip: str,
                as_of: dt.date) -> list[float]:
    """The observed factor path from ``as_of`` forward, aligned by :data:`BLOOMBERG_MONTH_LAG`.

    Element 0 is the factor **at the valuation date**; element *k* is *k* months later.
    Returns ``[]`` when the security is absent, and stops at the first gap — a series that
    ends is a security that has finished paying, not an error.
    """
    months = history.get(cusip)
    if not months:
        return []
    y, m = as_of.year, as_of.month
    out: list[float] = []
    while True:
        key = bloomberg_month_for(dt.date(y, m, 1))
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
