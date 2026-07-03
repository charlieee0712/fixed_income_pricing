"""Black-Derman-Toy-style short-rate lattice for callable / putable bond OAS + risk (v2).

The v2 engine for bonds with embedded call/put options. It is a CLEAN, standard implementation,
**not** a replica of the legacy VBA ``BondOAS`` (Project Pricing xlsm / Module1 l.4397-5861). That
is a deliberate, documented decision (WORKLOG 2026-07-02): the legacy lattice cannot be reproduced
or reconciled in our environment — it fed its inputs from Bloomberg (short-end fixings + call / put /
sink *schedules*) and bespoke "SteepFlat" ASCII tables we do not have, and it fitted the curve with a
hand-rolled per-step "sloperow" hack rather than a standard calibration. So — the same design
philosophy as the BondPrice port (a correct engine over a faithful replica of a flaw), except here a
faithful replica is not even possible. We build on firmer ground: our already-validated bootstrapped
:class:`curves.zero_curve.ZeroCurve` (par-bond self-test + golden reconciliation) feeds a textbook BDT
calibration. Validation is therefore by INVARIANTS (see ``tests/test_lattice.py``), not a legacy golden.

Model (the legacy's *family*, done cleanly):
  * recombining binomial short-rate tree; LOGNORMAL short rate (stays positive — right for the 2009
    ZIRP curve); CONSTANT volatility ``sigma``; risk-neutral p = 0.5 (BDT convention).
  * short rate at node (i, j):  ``r(i, j) = a_i * exp(sigma * sqrt(dt) * (2j - i))``,  j = 0..i.
  * the level ``a_i`` at each step is calibrated by FORWARD INDUCTION with Arrow-Debreu (state) prices
    so the tree reprices the input curve's discount factors ``P(0, t_i)`` exactly — arbitrage-free by
    construction. One 1-D monotone root per step (the step DF decreases in the rate level).
  * discounting is CONTINUOUS per step: one-period DF at a node = ``exp(-(r + oas) * dt)``, so the OAS
    adds flat to the continuous short rate — identical in spirit to the vanilla engine, where bumping
    the OAS == a parallel curve shift. Consequence: the straight-bond lattice price is independent of
    ``sigma`` and equals the direct curve-discounted price (a strong internal check).

Conventions / simplifications (v2 — assumption-driven, NOT a golden port; documented):
  * regular time grid: ``dt = 1/freq``, ``N = round(T*freq)`` steps, ``t_i = i/freq``; maturity is
    snapped to N periods (< half a period). Coupons ``coupon_rate/freq*100`` paid at each step. The
    valuation date sits on ``t_0`` (no accrued modelled) -> the root value is a CLEAN price. Real
    coupon-date offsets / accrued are a later refinement.
  * embedded options are Bermudan on the step grid: at a callable step the node value is capped at the
    call price (issuer min); at a putable step floored at the put price (holder max); exercise is
    tested on the ex-coupon continuation, then the coupon is added (the legacy order).
"""
from __future__ import annotations

import numpy as np


def _root_decreasing(f, lo, hi, xtol=1e-12, maxiter=200):
    """Root of a strictly DECREASING ``f`` on a bracket auto-expanded until it straddles 0. Bisection
    (dependency-free, bulletproof for a monotone function)."""
    flo, fhi = f(lo), f(hi)
    it = 0
    while flo < 0 and it < 100:          # lo gives f<0 -> move lo down
        span = (hi - lo) or 1.0
        lo -= span; flo = f(lo); it += 1
    it = 0
    while fhi > 0 and it < 100:          # hi gives f>0 -> move hi up
        span = (hi - lo) or 1.0
        hi += span; fhi = f(hi); it += 1
    if flo < 0 or fhi > 0:
        raise ValueError(f"cannot bracket root: f({lo})={flo}, f({hi})={fhi}")
    for _ in range(maxiter):
        mid = 0.5 * (lo + hi)
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < xtol:
            break
    return 0.5 * (lo + hi)


class ShortRateLattice:
    """A BDT-style short-rate tree calibrated to ``curve`` over ``[0, T]`` at ``freq`` steps/yr.

    Build once per (curve, T, freq, sigma); then :meth:`price_bond` / :meth:`implied_oas` /
    :meth:`risk_metrics` reuse the calibration (only the backward pass re-runs, since the OAS and
    coupon do not affect the tree). Default ``sigma`` = 0.15 = the Mario v1 house assumption (2026-07-03).
    """

    def __init__(self, curve, T, freq: int = 2, sigma: float = 0.15):
        self.freq = int(freq)
        self.dt = 1.0 / self.freq
        self.N = max(1, int(round(float(T) * self.freq)))
        self.T = self.N * self.dt
        self.sigma = float(sigma)
        self.t = np.arange(self.N + 1) * self.dt
        # curve discount factors at node times (continuous compounding, OAS-free)
        self.P = np.array([1.0 if ti <= 0 else float(curve.discount_factor(ti)) for ti in self.t])
        self._calibrate()

    def _calibrate(self):
        """Forward induction: solve the per-step level ``a_i`` so the tree reprices ``P(0, t_{i+1})``."""
        sq = self.sigma * np.sqrt(self.dt)
        self.a = np.zeros(self.N)
        Q = np.array([1.0])                       # Arrow-Debreu prices at step 0: Q(0,0)=1
        for i in range(self.N):
            j = np.arange(i + 1)
            kf = np.exp(sq * (2 * j - i))         # rate multipliers exp(sigma*sqrt(dt)*(2j-i))
            target = self.P[i + 1]
            Qc = Q
            a_i = _root_decreasing(lambda a: float(np.sum(Qc * np.exp(-a * kf * self.dt))) - target,
                                   1e-12, 1.0)
            self.a[i] = a_i
            d = np.exp(-a_i * kf * self.dt)       # one-step DF at each node of step i
            Qn = np.zeros(i + 2)
            Qn[:i + 1] += 0.5 * Q * d             # down move (i,j) -> (i+1,j)
            Qn[1:] += 0.5 * Q * d                 # up move   (i,j) -> (i+1,j+1)
            Q = Qn
        self._Q_terminal = Q                      # sums to P(0, T)

    def _short_rates(self, i):
        j = np.arange(i + 1)
        return self.a[i] * np.exp(self.sigma * np.sqrt(self.dt) * (2 * j - i))

    def _schedule_array(self, entries, side):
        """Per-step exercise-price array (length ``N+1``) from an option *schedule*.

        ``entries`` = iterable of ``(time_years, price)`` — the option is exercisable at ``price`` from
        ``time_years`` onward, until a later entry supersedes it (a step-function schedule: e.g. call
        @102 from y1, @101 from y2, @100 from y3+). A single entry ``[(t, p)]`` is the common "one flat
        price from date ``t`` to maturity" case. The root (``i=0``) and terminal (``i=N``) are always
        inactive — you do not exercise at issue or at redemption.

        This is the ONLY place the exercise schedule is built and it is driven ENTIRELY by ``entries``
        (sourced from ``data/call_schedules.csv`` via ``dataio.call_schedules`` in the driver). There is
        no hard-coded par-call: swapping in a real Bloomberg schedule is a data-only change (Mario,
        2026-07-03).

        ``side``: ``+1`` call (issuer caps the node value; inactive = ``+inf``); ``-1`` put (holder
        floors it; inactive = ``-inf``).
        """
        arr = np.full(self.N + 1, np.inf if side > 0 else -np.inf)
        sched = sorted((float(t), float(p)) for t, p in entries)
        for i in range(1, self.N):                       # root & terminal stay inactive
            price = None
            for t0, p in sched:
                if self.t[i] >= t0 - 1e-9:
                    price = p                            # latest entry effective at t_i
                else:
                    break
            if price is not None:
                arr[i] = price
        return arr

    def call_array(self, schedule):
        """Bermudan CALL price array (length ``N+1``) from a ``[(time_years, price), ...]`` schedule."""
        return self._schedule_array(schedule, side=+1)

    def put_array(self, schedule):
        """Bermudan PUT price array (length ``N+1``) from a ``[(time_years, price), ...]`` schedule."""
        return self._schedule_array(schedule, side=-1)

    def price_bond(self, coupon_rate, oas: float = 0.0, call_price=None, put_price=None) -> float:
        """Clean price (per 100 face) by backward induction. ``call_price`` / ``put_price`` are arrays of
        length N+1 (``inf`` / ``-inf`` where the option is inactive), or None for a straight bond."""
        cpn = coupon_rate / self.freq * 100.0
        V = np.full(self.N + 1, 100.0 + cpn)              # terminal: principal + final coupon
        for i in range(self.N - 1, -1, -1):
            r = self._short_rates(i)
            d = np.exp(-(r + oas) * self.dt)
            cont = 0.5 * (V[1:i + 2] + V[0:i + 1]) * d    # p = 0.5 up/down, discounted
            if i >= 1:                                     # exercise (ex-coupon), then pay coupon
                if call_price is not None:
                    cont = np.minimum(cont, call_price[i])
                if put_price is not None:
                    cont = np.maximum(cont, put_price[i])
                V = cont + cpn
            else:
                V = cont
        return float(V[0])

    def implied_oas(self, target_clean, coupon_rate, call_price=None, put_price=None,
                    lo: float = -0.20, hi: float = 2.0, xtol: float = 1e-10) -> float:
        """Flat continuous OAS (decimal) s.t. the lattice clean price == ``target_clean``. Price is
        strictly decreasing in the OAS, so the root is unique (bracket auto-widens)."""
        def f(oas):
            return self.price_bond(coupon_rate, oas, call_price, put_price) - target_clean
        return _root_decreasing(f, lo, hi, xtol=xtol)

    def risk_metrics(self, coupon_rate, oas, call_price=None, put_price=None, bump: float = 1e-4) -> dict:
        """Effective duration / DV01 / convexity by +/- ``bump`` OAS (== parallel short-rate shift). For a
        callable this captures the option's rate response (shorter duration than the straight bond)."""
        p0 = self.price_bond(coupon_rate, oas, call_price, put_price)
        pu = self.price_bond(coupon_rate, oas + bump, call_price, put_price)   # rates up -> price down
        pd = self.price_bond(coupon_rate, oas - bump, call_price, put_price)   # rates down -> price up
        if p0 == 0:
            return {"price": p0, "dv01": float("nan"), "eff_duration": float("nan"),
                    "convexity": float("nan")}
        return {
            "price": p0,
            "dv01": (pd - pu) / (2.0 * bump) * 1e-4,
            "eff_duration": (pd - pu) / (2.0 * bump * p0),
            "convexity": (pu + pd - 2.0 * p0) / (bump * bump * p0),
        }
