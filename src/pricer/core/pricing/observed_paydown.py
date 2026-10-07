"""Cash flows from an **observed** paydown path — the sibling of :mod:`prepayment`.

:mod:`prepayment` builds a balance schedule from an **assumed** constant CPR.
This module builds one from the **measured** monthly factor history. Same mathematics —
a balance schedule becomes cash flows — and the pair is deliberate: Mario's three-tier
deck (2026-10-06, slide 18) puts the two phases side by side and the only thing that
differs between them is the cash-flow generator. The code says that by having two.

    principal(t) = 100 x ( f(t-1) - f(t) ) / f(0)
    interest(t)  = 100 x   f(t-1)          / f(0) x coupon / 12

⭐ **Per 100 of CURRENT face, so only factor RATIOS are needed** — ``f(0)`` divides out of
both lines and the original face is never read. That deletes the ``orig_face = par/factor``
derivation, which matters because ``orig_face`` is empty in the master.

⭐ **And the decomposition is structure-agnostic**: it reproduces a deal's waterfall
without knowing it, because the factor already records what the waterfall did. Validated
2026-10-01 on 20 ordinary pools the assumed-CPR engine already prices — principal
conservation to **1.28e-13**, and a median **8.2 bp** against that engine evaluated at each
pool's own realised speed, with no systematic bias (signed median −2.6 bp).

Discounting matches :mod:`prepayment` exactly — ``exp(-t*(z(t)+spread))`` on a month grid
``t = k/12`` off the nominal :class:`curves.zero_curve.ZeroCurve`, per 100 current face. A
difference arising from pricing conventions rather than from the method would prove nothing.

⚠️ **STATIC FLOWS.** The path is what happened; it does not respond to a rate shock. So the
risk metrics here are spread-durations of fixed flows, and ``dv01`` and ``cs01`` are
**identically equal** — the price depends only on ``z + s``, so a parallel curve bump and a
spread bump are the same arithmetic. They separate only once cash flows react to rates,
which is the next phase, not this one.

⚠️⚠️ **AND FOR AN INTEREST-ONLY STRIP THAT COSTS THE SIGN OF THE DURATION.** An I/O's rate
sensitivity is almost entirely prepayment response: rates up, prepayment slows, the interest
stream lives longer, the strip is worth MORE. A fixed schedule can only ever produce a
positive duration. Measured on this book the custodian's own effective duration for I/Os is
a median of **−6.685** against our necessarily-positive number. The level is still right —
it is calibrated to the observed price — but **the duration sign is systematically wrong and
callers must flag it**, not quietly publish it.

⚠️ **Two things a real path does that are NOT errors**, so nothing here rejects them:
a REMIC accrual tranche (Z / VZ / ZC) rolls interest into its own balance, so its factor
**rises** and can **exceed 1** (6 of the 376 rise; the largest factor in the book is 3.1368).
``principal(t)`` is then negative, which is exactly right: the negative principal and the
positive interest cancel to zero net cash, with no special case anywhere.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

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

#: What to do with balance still outstanding when the observed series ends (2026-09 here).
#: ⚠️ ``drop`` is offered only so a caller can reproduce the 2026-10-01 first run, which
#: showed why it is wrong: dropping the tail removes PV, so the calibrated spread comes out
#: too NARROW, and every still-alive security read negative against the independent engine
#: (median −11.4 bp). Repaying the residual at the last observation fixed the bias to
#: +0.8 bp. ``amortise`` is the honest treatment and the default — it continues the path at
#: its own terminal speed instead of inventing a lump.
RESIDUAL_MODES = ("amortise", "repay", "drop")

#: Months of history used to estimate the terminal paydown speed for ``residual="amortise"``.
TERMINAL_WINDOW_MONTHS = 12

#: Stop projecting once the surviving fraction falls below this — 0.1% of the original
#: balance, i.e. economically dead. ⚠️ **Measured, not chosen by feel:** at 1e-9 the
#: projection could never finish inside the legal maturity and the ``amortise`` default
#: fired on **0 of 258** securities, silently falling back to the lump on every one of them.
#: A default that never happens is worse than no default, because the docstring says
#: otherwise. At 1e-3 it fires on 10 of 258; at 1e-2, on 59.
RESIDUAL_FLOOR = 1e-3

#: And never project further than this, however slow the terminal speed looks.
RESIDUAL_MAX_MONTHS = 600


@dataclass
class ObservedFlow:
    """One month of an observed path. ``principal`` may be negative on an accrual tranche."""
    month: int
    t: float                  # years = month / 12
    factor_start: float       # the factor that was outstanding through this month
    principal: float
    interest: float
    total: float
    projected: bool           # True once past the last observation


def terminal_smm(path, window: int = TERMINAL_WINDOW_MONTHS):
    """Geometric average monthly decay over the last ``window`` observations.

    ``None`` when the path is too short, or not decaying — an accrual tranche or a flat
    tail cannot be amortised away and the caller must fall back to ``repay``.
    """
    live = [f for f in path if f is not None and f > 0]
    if len(live) < 3:
        return None
    k = min(window, len(live) - 1)
    first, last = live[-1 - k], live[-1]
    if first <= 0 or last <= 0 or last >= first:
        return None
    return 1.0 - (last / first) ** (1.0 / k)


def observed_cash_flows(path, coupon_pct, kind: str = AMORTISING, *,
                        residual: str = "amortise", face: float = 100.0,
                        max_months: int | None = None):
    """Monthly investor cash flows implied by an observed factor path.

    ``path[0]`` is the factor **at the valuation date** (the loader
    :mod:`dataio.factor_history` owns the T+1 alignment; do not shift again here).
    ``coupon_pct`` is in percent, as the custodian states it.

    ⚠️ ``max_months`` bounds the projected tail and **should be the months to the security's
    LEGAL maturity**, which the caller holds and this module does not. Without it a slowly
    decaying tail projects for :data:`RESIDUAL_MAX_MONTHS` — one security ran to 809 months,
    i.e. 50 years of invented cash flow past a bond that legally ends decades earlier.
    Inventing flow beyond the contract is worse than the lump it was meant to replace, so
    when the projection would overrun the bound the residual is **repaid at the last
    observation instead** and the caller can see it in ``months_projected == 0``.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}; got {kind!r}")
    if residual not in RESIDUAL_MODES:
        raise ValueError(f"residual must be one of {RESIDUAL_MODES}; got {residual!r}")
    clean = [f for f in path if f is not None]
    if len(clean) < 2 or not clean[0] or clean[0] <= 0:
        return []

    f0 = clean[0]
    g = (coupon_pct / 100.0) / MONTHS_PER_YEAR
    pays_interest = kind != PRINCIPAL_ONLY
    pays_principal = kind != INTEREST_ONLY
    out: list[ObservedFlow] = []

    last = 0
    for i in range(1, len(clean)):
        a, b = clean[i - 1], clean[i]
        if a <= 0:
            break
        prin = face * (a - b) / f0 if pays_principal else 0.0
        inte = face * a / f0 * g if pays_interest else 0.0
        out.append(ObservedFlow(i, i / MONTHS_PER_YEAR, a, prin, inte, prin + inte, False))
        last = i
    if not out:
        return []

    # ---------------------------------------------------------------- the truncated tail
    surviving = clean[last] if last < len(clean) else 0.0
    if surviving <= 0 or residual == "drop":
        return out

    if residual == "repay":
        out[-1].principal += face * surviving / f0 if pays_principal else 0.0
        out[-1].total = out[-1].principal + out[-1].interest
        return out

    def _repay_lump():
        out[-1].principal += face * surviving / f0 if pays_principal else 0.0
        out[-1].total = out[-1].principal + out[-1].interest
        return out

    smm = terminal_smm(clean)
    if smm is None or smm <= 0:
        # ⚠️ cannot amortise a flat or accreting tail; bound it instead of inventing a speed
        return _repay_lump()

    cap = RESIDUAL_MAX_MONTHS if max_months is None else max(0, int(max_months) - last)
    # how many months the tail actually needs at this speed
    need = math.ceil(math.log(RESIDUAL_FLOOR * f0 / surviving) / math.log(1.0 - smm))
    if need > cap:
        # ⚠️ the projection would outrun the contract (or the hard cap). Repaying at the
        # last observation overstates how EARLY the money comes back; projecting past the
        # legal maturity invents money that cannot exist. The lump is the smaller lie, and
        # `months_projected == 0` is how a reader tells which one they are looking at.
        return _repay_lump()

    bal, m = surviving, last
    while bal / f0 > RESIDUAL_FLOOR and m - last < cap:
        m += 1
        nxt = bal * (1.0 - smm)
        prin = face * (bal - nxt) / f0 if pays_principal else 0.0
        inte = face * bal / f0 * g if pays_interest else 0.0
        out.append(ObservedFlow(m, m / MONTHS_PER_YEAR, bal, prin, inte, prin + inte, True))
        bal = nxt
    return out


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
    draws exactly this distinction (2026-10-06, slide 13). For an interest-only strip it is
    absorbing prepayment expectation rather than credit, which is why its level runs in the
    hundreds-to-thousands of basis points.
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
    price depends only on ``z + s``. The key is reported anyway so a caller can carry both
    columns unchanged into the phase where they genuinely differ.

    ``wal`` is principal-weighted and is therefore **NaN for an interest-only strip**, which
    has no principal; ``cf_life`` is weighted by total cash flow and is defined for all three
    kinds, which makes it the one comparable to the duration.
    """
    def priced(s):
        return price_observed(curve, path, coupon_pct, kind, s, residual=residual,
                              face=face, max_months=max_months)

    p0 = priced(spread)
    p_up, p_dn = priced(spread + bump), priced(spread - bump)
    flows = observed_cash_flows(path, coupon_pct, kind, residual=residual, face=face,
                                max_months=max_months)

    # ⚠️ HOW BIG WAS THE TAIL, AND WHAT HAPPENED TO IT. Measured across this book the
    # residual is a median 1.18% of the starting balance — but p90 is 7.8% and the maximum
    # is **260%**, an accrual tranche whose balance grew and never paid down inside the
    # window. "The residual is small" is true of the typical row and false of the tail, so
    # every row carries its own number instead of inheriting a reassurance.
    clean0 = [f for f in path if f is not None]
    f0 = clean0[0] if clean0 and clean0[0] else None
    observed = [f for f in flows if not f.projected]
    surviving = 0.0
    if f0 and observed:
        k = observed[-1].month
        surviving = (clean0[k] / f0) if k < len(clean0) else 0.0
    treatment = ("none" if surviving <= 0
                 else "amortised" if any(f.projected for f in flows)
                 else "repaid_at_last_observation")

    prin = sum(f.principal for f in flows)
    wal = (sum(f.principal * f.t for f in flows) / prin) if prin > 0 else float("nan")
    tot = sum(f.total for f in flows)
    cf_life = (sum(f.total * f.t for f in flows) / tot) if tot > 0 else float("nan")
    projected = sum(1 for f in flows if f.projected)

    if p0 == 0:
        return {"price": p0, "dv01": float("nan"), "cs01": float("nan"),
                "eff_duration": float("nan"), "convexity": float("nan"),
                "wal": wal, "cf_life": cf_life, "months": len(flows),
                "months_projected": projected, "residual_pct": 100.0 * surviving,
                "residual_treatment": treatment}
    dv01 = (p_dn - p_up) / (2.0 * bump) * 1e-4
    return {
        "price": p0,
        "dv01": dv01,
        "cs01": dv01,          # identical with fixed flows — see the docstring
        "eff_duration": (p_dn - p_up) / (2.0 * bump * p0),
        "convexity": (p_up + p_dn - 2.0 * p0) / (bump * bump * p0),
        "wal": wal,
        "cf_life": cf_life,
        "months": len(flows),
        "months_projected": projected,
        "residual_pct": 100.0 * surviving,
        "residual_treatment": treatment,
    }
