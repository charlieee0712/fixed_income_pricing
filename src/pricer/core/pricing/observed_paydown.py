"""Cash flows from an **observed** paydown path — the sibling of :mod:`prepayment`.

:mod:`prepayment` builds a balance schedule from an **assumed** constant CPR.
This module builds one from the **measured** monthly factor history. Same mathematics —
a balance schedule becomes cash flows — and the pair is deliberate: Mario's three-tier
methodology deck (2026-10-06, Defensible slide 18) puts the two phases side by side and the only thing
that differs between them is the cash-flow generator. The code says that by having two.

    principal(t) = 100 x ( f(t-1) - f(t) ) / f(0)
    interest(t)  = 100 x   f(t-1)          / f(0) x coupon / 12

⭐ **Per 100 of CURRENT face, so only factor RATIOS are needed** — ``f(0)`` divides out of
both lines and the original face is never read. That deletes the ``orig_face = par/factor``
derivation, which matters because ``orig_face`` is empty in the master.

⭐ **And the decomposition is structure-agnostic**: it reproduces what a deal's waterfall
did without knowing the waterfall, because the factor already records the outcome.
Validated 2026-10-01 on 20 ordinary pools the assumed-CPR engine already prices — principal
conservation to **1.28e-13**, and a median **8.2 bp** against that engine evaluated at each
pool's own realised speed, with no systematic bias (signed median −2.6 bp). This module
reproduces those three figures exactly and ``tests/test_observed_paydown.py`` pins them.

Discounting matches :mod:`prepayment` exactly — ``exp(-t*(z(t)+spread))`` on a month grid
``t = k/12`` off the nominal :class:`curves.zero_curve.ZeroCurve`, per 100 current face. A
difference arising from pricing conventions rather than from the method would prove nothing.

⚠️ **STATIC FLOWS.** The path is what happened; it does not respond to a rate shock. So the
risk metrics here are spread-durations of fixed flows, and ``dv01`` and ``cs01`` are
**identically equal** — the price depends only on ``z + s``, so a parallel curve bump and a
spread bump are the same arithmetic. They separate only once cash flows react to rates,
which is the next phase, not this one.

⚠️⚠️ **AND FOR AN INTEREST-ONLY STRIP THAT COSTS THE SIGN OF THE DURATION — measured at
population scale, not guessed.** An I/O's rate sensitivity has two parts: discounting
(rates up, PV down, duration positive) and prepayment response (rates up, prepayment slows,
the notional lives longer, MORE interest arrives, duration negative). For an I/O the second
dominates, and Tier 1 can only see the first. Over the 74 I/O strips in this book that price:

* **74 of 74** come out with a POSITIVE duration,
* **49 of 74** have a custodian duration that is NEGATIVE,
* the calibrated spreads run **−56,670 to +6,719 bp**.

⇒ **the level is right (it is calibrated to the observed price) and the rate risk is
structurally wrong, not merely noisy.** Callers must publish the price and refuse the
duration. ``assets/securitized`` routes them to ``io-strip-prepayment-dominated``.
⭐ The rule behind that: **publish a risk number only when its sign is known to be right.**

⚠️ **Two things a real path does that are NOT errors**, so nothing here rejects them:
a REMIC accrual tranche (Z / VZ / ZC) rolls interest into its own balance, so its factor
**rises** and can **exceed 1** (6 of the 376 rise; the largest factor in the book is 3.1368).
``principal(t)`` is then negative, which is exactly right: the negative principal and the
positive interest cancel to zero net cash, with no special case anywhere.

⚠️⚠️ **THE TRUNCATED TAIL IS NOT UNIFORMLY SMALL, AND THE ENGINE REPORTS WHAT IT DID.**
The series ends 2026-09; balance still outstanding then is a median **1.18%** of the
starting balance, but p90 is **7.8%** and the maximum is **260%** (an accrual tranche whose
balance grew and never paid down inside the window). So "the residual is small" is true of
the typical row and false of the tail. Every schedule therefore carries
:attr:`ObservedSchedule.treatment` — **a fact about what the engine did, returned by the
engine**, never re-derived downstream. An earlier version inferred it from
``any(flow.projected)`` after the fact, which could not distinguish "the caller asked for a
lump" from "amortising did not fit inside the legal maturity", and silently mislabelled a
third case it dropped outright.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from scipy.optimize import brentq

MONTHS_PER_YEAR = 12.0

#: The three shapes a securitised cash flow takes. ⚠️ Chosen by the custodian's own
#: description text (``P/O``, ``I/O``), **never** sniffed from a price or a duration — the
#: ``PAR_YIELD_UNITS`` lesson: an explicit registry, because no threshold separates these
#: cleanly. (``\bPO\b`` does not match ``P/O``; that spelling already cost a mislabel of
#: 76 securities on 2026-10-02.)
AMORTISING = "amortising"
INTEREST_ONLY = "interest_only"
PRINCIPAL_ONLY = "principal_only"
KINDS = (AMORTISING, INTEREST_ONLY, PRINCIPAL_ONLY)

#: What the caller ASKS for. ⚠️ ``drop`` exists only so the 2026-10-01 first run can be
#: reproduced, and that run is why it is not the default: dropping the tail removes PV, so
#: the calibrated spread comes out too NARROW and every still-alive security read negative
#: against the independent engine (signed median −11.4 bp). Repaying the residual fixed the
#: bias to +0.8 bp.
RESIDUAL_MODES = ("amortise", "repay", "drop")

#: What the engine DID — reported, not inferred. Four of these are lumps for four different
#: reasons, and a reader who cannot tell them apart cannot tell a decision from a fallback.
T_NONE = "none"                                  # nothing outstanding when the series ended
T_AMORTISED = "amortised"                        # projected on at the terminal speed
T_REPAID_REQUESTED = "repaid_as_requested"       # caller passed residual="repay"
T_REPAID_OVERRUN = "repaid_tail_would_overrun"   # amortising would pass the legal maturity
T_REPAID_NOT_DECAYING = "repaid_tail_not_decaying"   # flat or accreting tail: no speed to use
T_REPAID_BELOW_FLOOR = "repaid_below_floor"      # already economically dead, repaid for exactness
T_DROPPED = "dropped"                            # caller passed residual="drop"
TREATMENTS = (T_NONE, T_AMORTISED, T_REPAID_REQUESTED, T_REPAID_OVERRUN,
              T_REPAID_NOT_DECAYING, T_REPAID_BELOW_FLOOR, T_DROPPED)

#: Months of history used to estimate the terminal paydown speed for ``residual="amortise"``.
TERMINAL_WINDOW_MONTHS = 12

#: Stop projecting once the surviving fraction falls below this — 0.1% of the original
#: balance, i.e. economically dead. ⚠️ **Measured, not chosen by feel:** at 1e-9 the
#: projection could never finish inside the legal maturity and the ``amortise`` default
#: fired on **0 of 258** securities, silently falling back to the lump on every one of them.
#: A default that never happens is worse than no default, because the docstring says
#: otherwise. At 1e-3 it fires on 10 of 258; at 1e-2, on 59.
#: ⚠️ A residual already BELOW this is still repaid, never dropped — see
#: :data:`T_REPAID_BELOW_FLOOR`. An earlier version returned without repaying it, which
#: silently broke principal conservation (99.9500 instead of 100.0000) while the label
#: claimed the balance had been repaid.
RESIDUAL_FLOOR = 1e-3

#: And never project further than this, however slow the terminal speed looks.
RESIDUAL_MAX_MONTHS = 600


@dataclass
class ObservedFlow:
    """One month of an observed path. ``principal`` may be negative on an accrual tranche."""
    month: int
    t: float                  # years = month / 12
    factor_start: float       # the factor outstanding through this month
    principal: float
    interest: float
    total: float
    projected: bool           # True once past the last observation


@dataclass
class ObservedSchedule:
    """The flows, plus what the engine did about the tail and how big that tail was.

    ⭐ ``treatment`` is returned by the code that applied it. Nothing downstream recomputes
    it, for the same reason the T+1 shift has exactly one owner.
    """
    flows: list[ObservedFlow] = field(default_factory=list)
    treatment: str = T_NONE
    residual_fraction: float = 0.0          # of the starting balance, at the last observation
    terminal_smm: float | None = None       # the speed used, when one was


def terminal_smm(path, window: int = TERMINAL_WINDOW_MONTHS):
    """Geometric average monthly decay over the last ``window`` live observations.

    ``None`` when the path is too short, or not decaying — an accrual tranche or a flat
    tail has no speed to continue at, and inventing one would be worse than a lump.

    ⚠️ **The window supplies the MAGNITUDE; the last step supplies the LICENCE.** A path
    that fell hard and then went flat averages to a brisk speed over any window that reaches
    back past the regime change — ``[1.0, 0.5, 0.5, 0.5]`` returned 20.6% a month, which
    would then "pay off" a balance that has visibly stopped paying. Found by a test, not in
    production. So a terminal speed is only offered when the **final observed step actually
    decayed**; otherwise the caller gets ``None`` and falls back to a lump, which brings the
    money forward and is the conservative error of the two.
    """
    live = [f for f in path if f is not None and f > 0]
    if len(live) < 3:
        return None
    if live[-1] >= live[-2]:
        return None                       # the tail is flat or accreting: no licence
    k = min(window, len(live) - 1)
    first, last = live[-1 - k], live[-1]
    if first <= 0 or last <= 0 or last >= first:
        return None
    return 1.0 - (last / first) ** (1.0 / k)


def observed_schedule(path, coupon_pct, kind: str = AMORTISING, *,
                      residual: str = "amortise", face: float = 100.0,
                      max_months: int | None = None) -> ObservedSchedule:
    """Build the monthly schedule implied by an observed factor path.

    ``path[0]`` is the factor **at the valuation date** — :mod:`dataio.factor_history` owns
    the T+1 alignment and nothing here shifts again. ``coupon_pct`` is in percent, as the
    custodian states it.

    ⚠️ ``max_months`` bounds the projected tail and **should be the months to the security's
    LEGAL maturity**, which the caller holds and this module does not. Without it a slowly
    decaying tail projects for :data:`RESIDUAL_MAX_MONTHS`; one security ran to 809 months,
    i.e. 50 years of invented cash flow past a bond that legally ends decades earlier.
    Inventing flow beyond the contract is worse than the lump it was meant to replace.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}; got {kind!r}")
    if residual not in RESIDUAL_MODES:
        raise ValueError(f"residual must be one of {RESIDUAL_MODES}; got {residual!r}")
    clean = [f for f in path if f is not None]
    if len(clean) < 2 or not clean[0] or clean[0] <= 0:
        return ObservedSchedule()

    f0 = clean[0]
    g = (coupon_pct / 100.0) / MONTHS_PER_YEAR
    pays_interest = kind != PRINCIPAL_ONLY
    pays_principal = kind != INTEREST_ONLY
    flows: list[ObservedFlow] = []

    last = 0
    for i in range(1, len(clean)):
        a, b = clean[i - 1], clean[i]
        if a <= 0:
            break
        prin = face * (a - b) / f0 if pays_principal else 0.0
        inte = face * a / f0 * g if pays_interest else 0.0
        flows.append(ObservedFlow(i, i / MONTHS_PER_YEAR, a, prin, inte, prin + inte, False))
        last = i
    if not flows:
        return ObservedSchedule()

    surviving = clean[last] if last < len(clean) else 0.0
    frac = surviving / f0 if surviving > 0 else 0.0
    sch = ObservedSchedule(flows=flows, residual_fraction=frac)

    def _lump(why: str) -> ObservedSchedule:
        if pays_principal:
            flows[-1].principal += face * frac
            flows[-1].total = flows[-1].principal + flows[-1].interest
        sch.treatment = why
        return sch

    if surviving <= 0:
        sch.treatment = T_NONE
        return sch
    if residual == "drop":
        sch.treatment = T_DROPPED
        return sch
    if residual == "repay":
        return _lump(T_REPAID_REQUESTED)

    # ⚠️ Already below the floor: economically dead, but principal conservation is an
    # IDENTITY and must still hold, so repay it rather than returning without it.
    if frac <= RESIDUAL_FLOOR:
        return _lump(T_REPAID_BELOW_FLOOR)

    smm = terminal_smm(clean)
    if smm is None or smm <= 0:
        return _lump(T_REPAID_NOT_DECAYING)

    cap = RESIDUAL_MAX_MONTHS if max_months is None else max(0, int(max_months) - last)
    need = math.ceil(math.log(RESIDUAL_FLOOR / frac) / math.log(1.0 - smm))
    if need > cap:
        return _lump(T_REPAID_OVERRUN)

    bal, m = surviving, last
    while bal / f0 > RESIDUAL_FLOOR and m - last < cap:
        m += 1
        nxt = bal * (1.0 - smm)
        prin = face * (bal - nxt) / f0 if pays_principal else 0.0
        inte = face * bal / f0 * g if pays_interest else 0.0
        flows.append(ObservedFlow(m, m / MONTHS_PER_YEAR, bal, prin, inte, prin + inte, True))
        bal = nxt
    # whatever is left under the floor still belongs to the holder
    if pays_principal and bal > 0:
        flows[-1].principal += face * bal / f0
        flows[-1].total = flows[-1].principal + flows[-1].interest
    sch.treatment = T_AMORTISED
    sch.terminal_smm = smm
    return sch


def observed_cash_flows(path, coupon_pct, kind: str = AMORTISING, *,
                        residual: str = "amortise", face: float = 100.0,
                        max_months: int | None = None):
    """The flows alone — a convenience over :func:`observed_schedule` for callers that do
    not need to know what happened to the tail. One computation, two views."""
    return observed_schedule(path, coupon_pct, kind, residual=residual, face=face,
                             max_months=max_months).flows


def price_observed(curve, path, coupon_pct, kind: str = AMORTISING, spread: float = 0.0, *,
                   residual: str = "amortise", face: float = 100.0,
                   max_months: int | None = None) -> float:
    """PV per 100 current face (per 100 of NOTIONAL for an interest-only strip)."""
    flows = observed_cash_flows(path, coupon_pct, kind, residual=residual, face=face,
                                max_months=max_months)
    return sum(f.total * math.exp(-f.t * (float(curve.zero_rate(f.t)) + spread)) for f in flows)


def _solve_decreasing(f, lo, hi, xtol=1e-10, max_expand=40, what="root"):
    """Bracket-and-solve, mirroring :mod:`prepayment` so the two engines behave alike."""
    flo, fhi, n = f(lo), f(hi), 0
    while flo < 0 and n < max_expand:
        lo -= 0.20
        flo = f(lo)
        n += 1
    while fhi > 0 and n < max_expand:
        hi += 1.0
        fhi = f(hi)
        n += 1
    if flo * fhi > 0:
        raise ValueError(f"cannot bracket {what}: f({lo:.3f})={flo:.4f}, f({hi:.3f})={fhi:.4f}")
    return brentq(f, lo, hi, xtol=xtol)


def implied_spread_observed(target_price, curve, path, coupon_pct, kind: str = AMORTISING, *,
                            residual: str = "amortise", face: float = 100.0,
                            max_months: int | None = None,
                            lo: float = -0.20, hi: float = 2.0) -> float:
    """The flat spread that reprices the observed path to the custodian's own price.

    ⚠️ **This is an implied, bond-equivalent spread — NOT an OAS.** The cash flows are
    fixed, so nothing option-dependent has been modelled; the client's own methodology deck
    draws exactly this distinction (2026-10-06, Defensible deck slide 13 — ⚠️ the other
    deck's slide 13 is a different slide: *"a true OAS requires explicit
    modeling of option-dependent cash flows such as prepayments"*). For an interest-only
    strip it absorbs prepayment expectation rather than credit, which is why its level runs
    to thousands of basis points and why :mod:`assets.securitized` refuses to publish it.
    """
    return _solve_decreasing(
        lambda s: price_observed(curve, path, coupon_pct, kind, s, residual=residual,
                                 face=face, max_months=max_months) - target_price,
        lo, hi, what=f"observed-path spread for target={target_price}")


def observed_risk_metrics(curve, path, coupon_pct, kind: str = AMORTISING, spread: float = 0.0,
                          *, residual: str = "amortise", face: float = 100.0,
                          max_months: int | None = None, bump: float = 1e-4) -> dict:
    """Duration / DV01 / convexity by a central bump, plus two measures of life.

    ⚠️ ``dv01`` and ``cs01`` are the same number by construction here — with fixed flows the
    price depends only on ``z + s``, so bumping the curve and bumping the spread are the
    same arithmetic. Both keys are emitted anyway so a caller can carry the two columns
    unchanged into the phase where they genuinely differ.

    ``wal`` is principal-weighted and is therefore **NaN for an interest-only strip**, which
    has no principal; ``cf_life`` is weighted by total cash flow, is defined for all three
    kinds, and is the one comparable to the duration.

    ``residual_treatment`` comes from the schedule that applied it — see
    :class:`ObservedSchedule`.
    """
    sch = observed_schedule(path, coupon_pct, kind, residual=residual, face=face,
                            max_months=max_months)
    flows = sch.flows

    def priced(s):
        return sum(f.total * math.exp(-f.t * (float(curve.zero_rate(f.t)) + s)) for f in flows)

    p0, p_up, p_dn = priced(spread), priced(spread + bump), priced(spread - bump)

    prin = sum(f.principal for f in flows)
    wal = (sum(f.principal * f.t for f in flows) / prin) if prin > 0 else float("nan")
    tot = sum(f.total for f in flows)
    cf_life = (sum(f.total * f.t for f in flows) / tot) if tot > 0 else float("nan")

    base = {
        "price": p0,
        "wal": wal,
        "cf_life": cf_life,
        "months": len(flows),
        "months_projected": sum(1 for f in flows if f.projected),
        "principal_total": prin,
        "residual_pct": 100.0 * sch.residual_fraction,
        "residual_treatment": sch.treatment,
        "terminal_smm": sch.terminal_smm,
    }
    if p0 == 0:
        return {**base, "dv01": float("nan"), "cs01": float("nan"),
                "eff_duration": float("nan"), "convexity": float("nan")}
    dv01 = (p_dn - p_up) / (2.0 * bump) * 1e-4
    return {
        **base,
        "dv01": dv01,
        "cs01": dv01,          # identical with fixed flows — see the docstring
        "eff_duration": (p_dn - p_up) / (2.0 * bump * p0),
        "convexity": (p_up + p_dn - 2.0 * p0) / (bump * bump * p0),
    }
