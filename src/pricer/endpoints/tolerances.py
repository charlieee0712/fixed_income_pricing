"""How close is close enough, when the same request is priced on two machines.

⭐ **One owner.** These numbers were measured once and are now asked by two callers —
``tests/test_excel_fixture_parity.py`` (Windows against 47) and
``scripts/remote_smoke.py`` (this machine against a deployed instance). A second copy
would be a second thing to keep true, and this project has shipped that failure three
times under the name "two owners, one decision".

## Why there is more than one bound

Every published number here is a difference of prices divided by a bump. Duration divides
one difference by 1e-4; **convexity divides a SECOND difference by 1e-8**, so a last-bit
disagreement in a price arrives amplified by 1e8. The amplification belongs to the
formula, not to the endpoint.

⚠️ **A single bound was wrong, and a mutation test caught it before it shipped.** Sizing
one tolerance for convexity and applying it to everything let a deliberate **1e-4 price
perturbation** through at 9.6e-07 — comfortably inside a 1e-6 gate. One rule covering two
populations hides the smaller one, which is the same shape as the `PAR_YIELD_UNITS` bug.

Measured across the shipped fixtures:

| quantity | measured (47) | bound | headroom |
|---|---|---|---|
| prices, spreads | <= 6e-16 rel | 1e-10 | vast |
| durations, dv01 | <= 4e-13 | 1e-10 | 250x |
| **convexity** | **2.11e-08** | **1e-6** | 47x |

⭐ **The worst-offending QUANTITY changes with the platform** — convexity on 47, effective
duration on Azure Cloud Shell. That is the argument for per-quantity bounds rather than
against them: a single bound gets calibrated to whichever machine you measured first.
"""
from __future__ import annotations

#: The one quantity a second difference amplifies by 1e8.
TOL_CONVEXITY = 1e-6

#: Everything else: prices, spreads, durations, accrued, residuals.
TOL_DEFAULT = 1e-10

#: Set-level gate: the worst deviation anywhere, as a FRACTION OF ITS OWN BUDGET, must stay
#: under this. Deliberately separate from the per-field bounds — the noise floor could grow
#: tenfold with every per-field check still passing, and nobody would hear about it.
BUDGET_USED_MAX = 0.10


def tolerance(path: str) -> float:
    """The applicable bound for a numeric field, by name.

    Inputs: ``path`` — the dotted path of the field.
    Returns: :data:`TOL_CONVEXITY` for convexity, :data:`TOL_DEFAULT` otherwise.
    """
    return TOL_CONVEXITY if path.endswith("convexity") else TOL_DEFAULT


#: Human-readable fields, exempt from an exact match when comparing against the frozen
#: v1.0 corpus. ⚠️ The machine-readable ``code`` and ``field`` beside them are NOT exempt.
FREE_TEXT = ("message",)


def is_number(value) -> bool:
    """A JSON number, excluding bool — which is an int in Python and is not a measurement."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def shortfalls(frozen, fresh, path: str = ""):
    """Everything the frozen document carries that today's answer does NOT still honour.

    Returns an empty list when ``fresh`` is a SUPERSET of ``frozen``: every key present,
    every number within tolerance, extra keys allowed. That asymmetry is the point — the
    contract is additive, so a v1.1 answer legitimately carries fields a v1.0 document
    never had, and comparing the two with plain equality would report the contract working
    as a failure.

    Two exemptions, each for a stated reason rather than to make a check pass:
    ``schema_version`` (1.0 -> 1.1 IS the version string doing its job) and the free-text
    ``message`` fields listed in :data:`FREE_TEXT`.

    ⭐ Shared by ``tests/test_excel_fixture_parity.py`` and ``scripts/remote_smoke.py``.
    The gate needs it to check the two frozen fixtures numerically instead of merely
    confirming they are accepted; a second copy of this rule would be one more thing to
    keep true.
    """
    if path == ".schema_version":
        return []
    if path.split(".")[-1] in FREE_TEXT:
        return [] if isinstance(fresh, str) == isinstance(frozen, str) else \
               [f"{path}: text field changed type"]
    if is_number(frozen) and is_number(fresh):
        used = budget_used(path, frozen, fresh)
        return [] if used <= 1.0 else [f"{path}: {frozen!r} -> {fresh!r}"]
    if isinstance(frozen, dict):
        if not isinstance(fresh, dict):
            return [f"{path}: was an object, now {type(fresh).__name__}"]
        out = []
        for key in frozen:
            if key not in fresh:
                out.append(f"{path}.{key}: dropped")
            else:
                out += shortfalls(frozen[key], fresh[key], f"{path}.{key}")
        return out
    if isinstance(frozen, list):
        if not isinstance(fresh, list):
            return [f"{path}: was an array, now {type(fresh).__name__}"]
        if len(fresh) < len(frozen):
            return [f"{path}: had {len(frozen)} entries, now {len(fresh)}"]
        out = []
        for i, entry in enumerate(frozen):   # prefix semantics: extra entries are additive
            out += shortfalls(entry, fresh[i], f"{path}[{i}]")
        return out
    return [] if frozen == fresh else [f"{path}: {frozen!r} -> {fresh!r}"]


def budget_used(path: str, committed: float, fresh: float) -> float:
    """How much of this field's tolerance the difference consumes, as a fraction.

    ⚠️ Scaled by ``max(1, |committed|)`` rather than by ``|committed|``. Several published
    fields are near zero by construction — a calibration residual (~6.6e-09), an inactive
    put's price effect per volatility point (~1.1e-11) — and a purely relative measure on
    those reports enormous deviations that are machine epsilon in absolute terms.
    """
    return (abs(fresh - committed) / max(1.0, abs(committed))) / tolerance(path)
