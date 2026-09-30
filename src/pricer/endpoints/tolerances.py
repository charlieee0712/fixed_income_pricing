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


def budget_used(path: str, committed: float, fresh: float) -> float:
    """How much of this field's tolerance the difference consumes, as a fraction.

    ⚠️ Scaled by ``max(1, |committed|)`` rather than by ``|committed|``. Several published
    fields are near zero by construction — a calibration residual (~6.6e-09), an inactive
    put's price effect per volatility point (~1.1e-11) — and a purely relative measure on
    those reports enormous deviations that are machine epsilon in absolute terms.
    """
    return (abs(fresh - committed) / max(1.0, abs(committed))) / tolerance(path)
