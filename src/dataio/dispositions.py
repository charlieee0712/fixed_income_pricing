"""Every candidate gets exactly one named outcome.

This module exists because of a specific, repeated failure: a security that is neither
priced nor flagged, and therefore absent from every headline count, while every count
still balances.

It has now happened twice.

* the GBP bond (2026-08-30) — a curve that would not build made the driver ``skip`` a
  plain fixed bond. The header printed ``skipped=1`` for months and nobody read it;
* ``TNTD04920858`` (2026-08-31) — the universe routed it to the callable lattice, and the
  lattice driver's own maturity threshold silently declined to consume it. It appeared in
  no output at all. It had even been written down once, as a "minor loose end", and then
  fell out of every subsequent count.

The second one is the instructive case, because a naive reconciliation **passes** it:

    732 funnel population = 565 corporate output + 3 lattice output + 164 excluded

balances perfectly, since the missing bond carries a named exclusion reason one layer up.
But ``callable`` is not a disposition — it is a **routing instruction** meaning "the
lattice driver handles this", and the destination never honoured it. So counting is not
enough, and neither is "every bond has a reason somewhere":

    a routing reason is only discharged when the destination either
    PRICED the bond or SKIPPED it with a named, non-empty reason code.

:func:`reconcile` enforces that, over sets of identifiers rather than counts, and returns
the result as data so a caller can write it out and a test can read it. A count check
(``3 + 2 == 5``) would pass even if the wrong bond were in the wrong set; a set check
cannot.
"""
from __future__ import annotations

import pandas as pd


class DispositionError(AssertionError):
    """A candidate population that is not exactly covered by its outcomes.

    Subclasses ``AssertionError`` because that is what it is: a broken invariant, not a
    bad input. It should stop a driver run, not be caught and logged.
    """


def reconcile(candidates, priced, skipped) -> pd.DataFrame:
    """Prove that every candidate has exactly one named outcome, and return the table.

    Inputs
    ------
    1. candidates : iterable of str — every identifier the routing layer sent here. This
       is the authoritative population; it is not re-derived or re-filtered.
    2. priced     : iterable of str — identifiers this engine produced a number for.
    3. skipped    : mapping ``{identifier: (reason_code, reason_text)}`` — identifiers it
       deliberately did not price, each with a short machine-readable code and a sentence
       a human can act on.

    Returns: ``DataFrame[asset_id, status, reason_code, reason]``, one row per candidate,
    sorted by identifier. ``status`` is ``"priced"`` or ``"skipped"``.

    Raises :class:`DispositionError` when the cover is not exact:

    * **undisposed** — a candidate in neither set. This is the defect this module exists
      for, and the message names the identifiers so the reader does not have to diff.
    * **both** — a candidate in both sets; the outcome would depend on read order.
    * **reason** — a skip with an empty code or an empty explanation. "Skipped" without a
      reason is how a real blocker becomes invisible; an empty string is not a reason.
    * **unknown** — an identifier reported that was never a candidate, which means the
      caller and the routing layer disagree about the population.
    """
    candidates = {str(c) for c in candidates}
    priced = {str(p) for p in priced}
    skipped = {str(k): v for k, v in dict(skipped).items()}

    unknown = (priced | set(skipped)) - candidates
    if unknown:
        raise DispositionError(
            f"unknown identifier(s) reported that are not candidates: {sorted(unknown)} — "
            f"the caller and the routing layer disagree about the population")

    both = priced & set(skipped)
    if both:
        raise DispositionError(
            f"identifier(s) reported as both priced and skipped: {sorted(both)} — the "
            f"outcome would depend on which set is read first")

    undisposed = candidates - priced - set(skipped)
    if undisposed:
        raise DispositionError(
            f"undisposed candidate(s): {sorted(undisposed)} — routed here but neither "
            f"priced nor skipped with a reason. A bond in this state is absent from every "
            f"output and every count, and nothing reports it. Either price it, or skip it "
            f"with a named reason.")

    for asset_id, entry in sorted(skipped.items()):
        code, text = (tuple(entry) + ("", ""))[:2] if not isinstance(entry, str) else (entry, "")
        if not str(code).strip() or not str(text).strip():
            raise DispositionError(
                f"{asset_id} is skipped without a reason (code={code!r}, text={text!r}) — "
                f"a skip with no reason is how a blocker becomes invisible")

    rows = [{"asset_id": a, "status": "priced", "reason_code": "", "reason": ""}
            for a in sorted(priced)]
    rows += [{"asset_id": a, "status": "skipped",
              "reason_code": str(skipped[a][0]), "reason": str(skipped[a][1])}
             for a in sorted(skipped)]
    return pd.DataFrame(rows).sort_values("asset_id").reset_index(drop=True)
