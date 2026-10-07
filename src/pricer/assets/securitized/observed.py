"""Per-metric wrappers over the OBSERVED-paydown engine, in legacy units.

The product layer for :mod:`pricer.core.pricing.observed_paydown`, shaped like its sibling
:mod:`pricer.assets.securitized.pool`: **percent in, basis points out**, one simple function
per metric, inputs named and numbered in each docstring — the convention the client's own
Monthly sheet uses (rows 47-60 are per-metric functions, rows 61-98 the input dictionary).

⚠️ **This layer exists because of the boundary it owns.** The core works in decimals; the
custodian and the client speak percent and basis points. Calling the core directly from a
driver skipped that conversion and produced a calibrated spread of **46,478 bp** on 487
pools — a 465% spread, from passing a 6.000 where 0.06000 was wanted. The two-layer design
is for exactly this, and bypassing it is how a units error reaches an output.

⚠️⚠️ **AND IT OWNS THE ONE REFUSAL.** An interest-only strip's rate sensitivity is almost
entirely prepayment response, which fixed cash flows cannot express, so a duration computed
here has the wrong SIGN — 74 of 74 positive on this book against 49 negative custodian
figures. :func:`duration`, :func:`dv01`, :func:`convexity` and :func:`implied_spread_bp`
therefore **raise** :class:`UnpublishableRiskMetric` for an I/O rather than returning a
number a caller might publish. ⭐ The decision belongs here and not in a driver: a modelling
choice left to "the caller" is a choice nobody makes the same way twice.
"""
from __future__ import annotations

from pricer.core.pricing.observed_paydown import (
    AMORTISING,
    INTEREST_ONLY,
    KINDS,
    PRINCIPAL_ONLY,
    implied_spread_observed,
    observed_risk_metrics,
    observed_schedule,
    price_observed,
)
from pricer.errors import PricingDomainError

_BP = 1e-4

__all__ = [
    "AMORTISING", "INTEREST_ONLY", "PRINCIPAL_ONLY", "KINDS",
    "UnpublishableRiskMetric", "calculated_price", "implied_spread_bp",
    "duration", "dv01", "convexity", "weighted_average_life", "cash_flow_life",
    "tail_report", "risk_is_publishable",
]


class UnpublishableRiskMetric(PricingDomainError):
    """A metric this model can compute but whose value would mislead.

    ⚠️ Rooted at :class:`~pricer.errors.PricingDomainError`, **not** at ``ValueError`` — the
    spread solvers catch ``ValueError``, and a refusal swallowed by a solver comes back as
    "no spread reprices this security", which is a different and false statement.
    """


def risk_is_publishable(kind: str) -> bool:
    """Whether a risk number from this model may be published for this cash-flow shape.

    ⭐ The rule, stated once: **publish a risk number only when its sign is known to be
    right.** Amortising and principal-only pass; interest-only does not.
    """
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}; got {kind!r}")
    return kind != INTEREST_ONLY


def _guard(kind: str, metric: str) -> None:
    if not risk_is_publishable(kind):
        raise UnpublishableRiskMetric(
            f"{metric} is withheld for an interest-only strip: its rate sensitivity is "
            "dominated by prepayment response, which a fixed cash-flow schedule cannot "
            "express, so the value this model produces has the wrong sign (74 of 74 "
            "positive on this book against 49 negative custodian figures). The price and "
            "market value remain valid; use the custodian's own duration as evidence and "
            "never as a substitute in this model's column.")


def _validate(path, coupon_pct, kind) -> None:
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}; got {kind!r}")
    if coupon_pct is None:
        raise ValueError("coupon_pct is required, in PERCENT, as the custodian states it")
    if coupon_pct < 0:
        raise ValueError(f"coupon_pct must not be negative; got {coupon_pct}")
    if not path or len(path) < 2:
        raise ValueError("an observed path needs at least two monthly factors")


def calculated_price(path, coupon_pct: float, kind: str, curve, spread_bp: float = 0.0,
                     *, max_months: int | None = None, face: float = 100.0) -> float:
    """Model price per 100 current face (per 100 of NOTIONAL for an interest-only strip).

    Inputs
    ------
    1. path        : list[float] — the observed monthly factors, element 0 **at the
       valuation date**. :mod:`dataio.factor_history` owns the T+1 alignment.
    2. coupon_pct  : float — the coupon in PERCENT, as the custodian states it.
    3. kind        : str — one of :data:`KINDS`, from :func:`dataio.phase2.pool_structure`.
    4. curve       : ZeroCurve — nominal discount curve.
    5. spread_bp   : float — flat spread in BASIS POINTS.
    6. max_months  : int | None — months to the LEGAL maturity; bounds the projected tail.
    7. face        : float — current face (default 100).

    Returns: float — present value per ``face``.
    """
    _validate(path, coupon_pct, kind)
    return price_observed(curve, path, coupon_pct, kind, spread_bp * _BP,
                          face=face, max_months=max_months)


def implied_spread_bp(path, coupon_pct: float, kind: str, market_price: float, curve,
                      *, max_months: int | None = None, face: float = 100.0) -> float:
    """The flat spread that reproduces the custodian's price on the observed path.

    Inputs: 1-4 and 6-7 as :func:`calculated_price`, plus
    5. market_price : float — the observed price per 100 current face.

    Returns: float — the implied spread in BASIS POINTS.

    ⚠️ **Not an OAS.** The cash flows are fixed, so nothing option-dependent is modelled; the
    client's methodology deck calls this an *implied or bond-equivalent spread* and reserves
    "OAS" for a model whose cash flows respond. Raises
    :class:`UnpublishableRiskMetric` for an interest-only strip — a spread calibrated to a
    realised path is, for an I/O, absorbing the very prepayment expectation the strip is a bet
    on, which is why those come out between −56,670 and +6,719 bp.
    """
    _validate(path, coupon_pct, kind)
    _guard(kind, "an implied spread")
    return implied_spread_observed(market_price, curve, path, coupon_pct, kind,
                                   face=face, max_months=max_months) / _BP


def _metrics(path, coupon_pct, kind, curve, spread_bp, max_months, face) -> dict:
    _validate(path, coupon_pct, kind)
    return observed_risk_metrics(curve, path, coupon_pct, kind, spread_bp * _BP,
                                 face=face, max_months=max_months)


def duration(path, coupon_pct: float, kind: str, curve, spread_bp: float = 0.0,
             *, max_months: int | None = None, face: float = 100.0) -> float:
    """Effective duration in YEARS. Inputs as :func:`calculated_price`.

    ⚠️ With fixed cash flows this is a SPREAD duration and equals the rate duration exactly;
    see :func:`dv01`. Raises for an interest-only strip."""
    _guard(kind, "a duration")
    return _metrics(path, coupon_pct, kind, curve, spread_bp, max_months, face)["eff_duration"]


def dv01(path, coupon_pct: float, kind: str, curve, spread_bp: float = 0.0,
         *, max_months: int | None = None, face: float = 100.0) -> float:
    """Price change per 1bp, per 100 face. Inputs as :func:`calculated_price`.

    ⚠️ **Identically equal to CS01 here, and that is a property rather than an oversight.**
    The price depends only on ``z + s``, so with fixed cash flows a parallel curve bump and a
    spread bump are the same arithmetic. They separate only when the cash flows respond to
    rates, which is the next phase. Raises for an interest-only strip."""
    _guard(kind, "a DV01")
    return _metrics(path, coupon_pct, kind, curve, spread_bp, max_months, face)["dv01"]


def convexity(path, coupon_pct: float, kind: str, curve, spread_bp: float = 0.0,
              *, max_months: int | None = None, face: float = 100.0) -> float:
    """Second-order price sensitivity. Inputs as :func:`calculated_price`. Raises for I/O."""
    _guard(kind, "a convexity")
    return _metrics(path, coupon_pct, kind, curve, spread_bp, max_months, face)["convexity"]


def weighted_average_life(path, coupon_pct: float, kind: str, *,
                          max_months: int | None = None, face: float = 100.0) -> float:
    """Principal-weighted average life in YEARS.

    Inputs: 1-3 and 6-7 as :func:`calculated_price`.
    Returns: float — ``nan`` for an interest-only strip, which has no principal.

    ⭐ Not guarded: a WAL is a statement about cash-flow timing, not a risk sensitivity, and
    for an I/O it is simply undefined rather than wrong. Discounting does not enter, so no
    curve is taken — the same choice its pool sibling makes.
    """
    _validate(path, coupon_pct, kind)
    return observed_risk_metrics(_NoCurve(), path, coupon_pct, kind, 0.0,
                                 face=face, max_months=max_months)["wal"]


def cash_flow_life(path, coupon_pct: float, kind: str, *,
                   max_months: int | None = None, face: float = 100.0) -> float:
    """Total-cash-flow-weighted average life in YEARS — defined for all three kinds.

    ⭐ The measure to quote for an I/O, where the principal-weighted WAL does not exist.

    ⚠️ **This is a TIMING measure, not a rate sensitivity, and for an interest-only strip it
    must not be read as one.** It is deliberately unguarded — it is a fact about when cash
    arrives — but that leaves a path around the refusal in :func:`duration`: a caller could
    take this number and call it a duration. An I/O's rate risk cannot be read off its
    cash-flow timing at all, because the timing itself is what moves when rates move.
    """
    _validate(path, coupon_pct, kind)
    return observed_risk_metrics(_NoCurve(), path, coupon_pct, kind, 0.0,
                                 face=face, max_months=max_months)["cf_life"]


def tail_report(path, coupon_pct: float, kind: str, *,
                max_months: int | None = None, face: float = 100.0) -> dict:
    """What the engine did with the balance outstanding when the observed series ended.

    Returns ``{treatment, residual_pct, months_observed, months_projected}``.

    ⭐ Reported by the code that applied it, never inferred. The residual is a median 1.18%
    of the starting balance on this book but p90 7.8% and max 260%, so a row that depends
    heavily on the treatment must be able to say so.
    """
    _validate(path, coupon_pct, kind)
    sch = observed_schedule(path, coupon_pct, kind, face=face, max_months=max_months)
    projected = sum(1 for f in sch.flows if f.projected)
    return {"treatment": sch.treatment, "residual_pct": 100.0 * sch.residual_fraction,
            "months_observed": len(sch.flows) - projected, "months_projected": projected}


class _NoCurve:
    """A zero curve, for the measures where discounting is a category error.

    WAL and cash-flow life are properties of the flows. Passing a real curve would let
    discounting silently matter; refusing the parameter outright would break the shared
    metric helper. A flat zero makes the irrelevance explicit.
    """

    @staticmethod
    def zero_rate(_t):
        return 0.0
