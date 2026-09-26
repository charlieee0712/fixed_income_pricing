"""Mortgage pass-through pool — per-metric simple functions (template:
``assets/securitized/pool.py``).

Serves the master's **Government Mortgage Backed Securities** sub-category: 888 rows -> 882
securities. One simple function per output, legacy units in and out, no arithmetic of its own —
every number comes from ``core.pricing.prepayment``.

Units at this boundary, and they differ from the core's: **wac / cpr / net_coupon in PERCENT,
spread in BASIS POINTS, prices per 100 of CURRENT face, WAL in years.** The core works in
decimals throughout and these wrappers convert, which is the same split the corporate and
government surfaces use.

⭐ **The calibration you want here is the CPR, not the spread**, and that is a settled decision
rather than a preference. One price identifies one unknown; the delivered Bloomberg pull is
as-of 2026 (``scripts/mbs_data_check.py``) so its trailing CPRs describe the wrong decade and
cannot be the 2009 input. For government-guaranteed paper the credit spread is defensibly near
zero, so :func:`implied_cpr_pct` is the primary route and :func:`implied_spread_bp` waits for a
2009-dated CPR to arrive — at which point the two become a cross-check on each other rather
than alternatives.

⚠️ **No date arguments anywhere.** A pool is described by months remaining, not by a calendar
maturity, and the month grid is anchored at the valuation date implicitly. Two consequences
worth naming: intra-month accrued is not modelled, and neither is the agency payment delay
(the ~14-45 days between the record date and cash arriving). Both are real and both are absent;
they are worth perhaps a few cents of price and belong with the v2 work.
"""
from __future__ import annotations

from pricer.assets.securitized.bonds_input import validate_pool_inputs
from pricer.core.pricing.prepayment import (
    implied_cpr_pool,
    implied_spread_pool,
    pool_cash_flows,
    pool_risk_metrics,
    price_pool,
)

_BP = 1e-4
_PCT = 1e-2

#: The price must move at least this much, per 100 of face, across the whole attainable CPR
#: range before an implied CPR means anything. Set to the precision a price is QUOTED to — if
#: the entire range from 0% to 99% prepayment is narrower than the last digit of the price you
#: are solving against, the answer is determined by rounding noise, not by prepayment.
#: Not a solver tolerance: the root may be perfectly well defined and still carry no
#: information. See :func:`implied_cpr_pct`.
CPR_IDENTIFIABLE_MIN_PRICE_RANGE = 1e-4


def _net(net_coupon_pct):
    return None if net_coupon_pct is None else net_coupon_pct * _PCT


def calculated_price(wac: float, wam_months: int, cpr: float, curve,
                     spread: float = 0.0, net_coupon=None, face: float = 100.0) -> float:
    """Price of the pool per 100 current face at a given CPR and spread.

    Inputs (see bonds_input.INPUT_CATALOGUE)
    ------
    1. wac         : float — gross weighted-average coupon in PERCENT (6.42 = 6.42%).
    2. wam_months  : int — weighted-average remaining maturity in MONTHS.
    3. cpr         : float — constant prepayment rate in PERCENT per year.
    5. curve       : ZeroCurve — nominal discount curve.
    6. spread      : float — flat spread in BASIS POINTS (default 0 = on-curve).
    4. net_coupon  : float | None — pass-through rate in PERCENT (None = equal to wac).
    7. face        : float — current face (default 100).

    Returns: float — present value per ``face`` of current balance.
    """
    validate_pool_inputs(wac, wam_months, cpr, net_coupon)
    return price_pool(curve, wac * _PCT, int(wam_months), cpr * _PCT, spread * _BP,
                      net_coupon=_net(net_coupon), face=face)


def implied_cpr_pct(wac: float, wam_months: int, market_price: float, curve,
                    spread: float = 0.0, net_coupon=None, face: float = 100.0) -> float:
    """⭐ Constant CPR that reproduces the market price at a FIXED spread — the primary
    calibration for this class.

    Inputs
    ------
    1. wac          : float — gross coupon in PERCENT.
    2. wam_months   : int — remaining term in MONTHS.
    8. market_price : float — observed price per 100 current face (the custodian's BT).
    5. curve        : ZeroCurve — nominal discount curve.
    6. spread       : float — the spread HELD FIXED, in BASIS POINTS (default 0).
    4. net_coupon   : float | None — pass-through rate in PERCENT.
    7. face         : float — current face (default 100).

    Returns: float — the implied CPR in PERCENT per year.

    ⚠️ **A par-priced pool has no identifiable CPR** and this raises rather than returning a
    number. Price is monotone in CPR only away from par — a premium pool cheapens as prepayment
    rises, a discount richens — so at par the function being solved is flat and every CPR fits
    equally well. That is a property of the instrument, not a solver limitation, and the
    refusal is the honest answer.

    ⭐ The refusal is enforced HERE rather than in the engine, and the distinction matters. The
    core solver has an exact-hit shortcut: if the target happens to equal the price at CPR = 0
    it returns 0.0 immediately, which at par is true of every CPR and therefore reports "no
    prepayment" for a pool about which nothing can be said. The engine body is the 2026-07-22
    file spliced unchanged, so the guard goes in the wrapper — the same division Round 2a used
    when the call/put conflict was refused at the wrapper and the core float path left alone.
    """
    validate_pool_inputs(wac, wam_months, None, net_coupon)
    # Does the price respond to prepayment at all? Asked before solving, because a solver
    # cannot distinguish "the root is here" from "every point is a root".
    at_zero = calculated_price(wac, wam_months, 0.0, curve, spread, net_coupon, face)
    at_full = calculated_price(wac, wam_months, 99.0, curve, spread, net_coupon, face)
    if abs(at_zero - at_full) < CPR_IDENTIFIABLE_MIN_PRICE_RANGE * max(1.0, face / 100.0):
        raise ValueError(
            f"CPR is not identifiable: over the whole range from 0% to 99% prepayment this "
            f"pool prices between {min(at_zero, at_full):.6f} and {max(at_zero, at_full):.6f}, "
            f"a spread of {abs(at_zero - at_full):.2e} per 100 — narrower than the price is "
            f"quoted to. Any answer would be reading prepayment out of rounding. This happens "
            f"at par, where the discount rate matches the pass-through coupon.")
    return implied_cpr_pool(market_price, curve, wac * _PCT, int(wam_months),
                            spread=spread * _BP, net_coupon=_net(net_coupon),
                            face=face) / _PCT


def implied_spread_bp(wac: float, wam_months: int, cpr: float, market_price: float, curve,
                      net_coupon=None, face: float = 100.0) -> float:
    """Flat spread that reproduces the market price at a GIVEN CPR — the other branch.

    Inputs
    ------
    1. wac          : float — gross coupon in PERCENT.
    2. wam_months   : int — remaining term in MONTHS.
    3. cpr          : float — the prepayment rate HELD FIXED, in PERCENT per year.
    8. market_price : float — observed price per 100 current face.
    5. curve        : ZeroCurve — nominal discount curve.
    4. net_coupon   : float | None — pass-through rate in PERCENT.
    7. face         : float — current face (default 100).

    Returns: float — the implied spread in BASIS POINTS.

    ⚠️ Usable only with a CPR dated to the valuation date. Feeding it the delivered pull's
    trailing CPRs would produce a spread that silently absorbs seventeen years of prepayment
    history — a number for every pool, every one of them wrong, and nothing in the output
    saying so.
    """
    validate_pool_inputs(wac, wam_months, cpr, net_coupon)
    return implied_spread_pool(market_price, curve, wac * _PCT, int(wam_months), cpr * _PCT,
                               net_coupon=_net(net_coupon), face=face) / _BP


def _metrics(wac, wam_months, cpr, curve, spread, net_coupon, face) -> dict:
    """Shared bump-and-reprice metric set (duration / dv01 / convexity / WAL)."""
    validate_pool_inputs(wac, wam_months, cpr, net_coupon)
    return pool_risk_metrics(curve, wac * _PCT, int(wam_months), cpr * _PCT, spread * _BP,
                             net_coupon=_net(net_coupon), face=face)


def duration(wac: float, wam_months: int, cpr: float, curve, spread: float = 0.0,
             net_coupon=None, face: float = 100.0) -> float:
    """Spread duration in YEARS at the given CPR and spread.

    Inputs: 1-7 as :func:`calculated_price`.
    Returns: float — price sensitivity to a parallel spread shift, per unit price.

    ⚠️ **Spread duration, not effective duration.** Under a constant CPR the cash flows do not
    move when rates move, so this measures only the discounting effect. A real pool prepays
    faster as rates fall, which shortens it exactly when a bond would lengthen; that is the
    negative convexity mortgage investors are paid for and it is absent here by construction.
    """
    return _metrics(wac, wam_months, cpr, curve, spread, net_coupon, face)["eff_duration"]


def dv01(wac: float, wam_months: int, cpr: float, curve, spread: float = 0.0,
         net_coupon=None, face: float = 100.0) -> float:
    """Price change per +1 bp of spread (EXTENSION — no legacy counterpart).

    Inputs: 1-7 as :func:`calculated_price`.
    Returns: float — price move per basis point, same sign convention as the bond surfaces.
    """
    return _metrics(wac, wam_months, cpr, curve, spread, net_coupon, face)["dv01"]


def convexity(wac: float, wam_months: int, cpr: float, curve, spread: float = 0.0,
              net_coupon=None, face: float = 100.0) -> float:
    """Second-order spread sensitivity (EXTENSION — no legacy counterpart).

    Inputs: 1-7 as :func:`calculated_price`.
    Returns: float — convexity of the FIXED flows.

    ⚠️ This is positive, like any fixed stream of cash flows, and the market's mortgage
    convexity is negative. The difference is the whole prepayment option, and quoting this
    number as a pool's convexity without that sentence attached would be a real misstatement.
    """
    return _metrics(wac, wam_months, cpr, curve, spread, net_coupon, face)["convexity"]


def weighted_average_life(wac: float, wam_months: int, cpr: float, curve=None,
                          net_coupon=None, face: float = 100.0) -> float:
    """Weighted-average life in YEARS — principal-weighted, the pool's headline term measure.

    Inputs
    ------
    1. wac        : float — gross coupon in PERCENT.
    2. wam_months : int — remaining term in MONTHS.
    3. cpr        : float — prepayment rate in PERCENT per year.
    4. net_coupon : float | None — pass-through rate in PERCENT.
    7. face       : float — current face (default 100).

    Returns: float — average time to receive a dollar of PRINCIPAL, in years.

    ``curve`` is accepted and unused: WAL is a property of the cash flows, not of discounting,
    and the parameter is kept only so the signature matches its siblings. Discounting a WAL
    would be a category error, which is why it is refused by being ignored rather than quietly
    permitted to matter.
    """
    validate_pool_inputs(wac, wam_months, cpr, net_coupon)
    flows = pool_cash_flows(wac * _PCT, int(wam_months), cpr * _PCT,
                            net_coupon=_net(net_coupon), balance=face)
    principal = sum(f.sched_principal + f.prepayment for f in flows)
    if principal <= 0:
        return float("nan")
    return sum((f.sched_principal + f.prepayment) * f.t for f in flows) / principal


def widening(wac: float, wam_months: int, cpr: float, curve, spread: float,
             bp_adjust: float = 10.0, net_coupon=None, face: float = 100.0) -> float:
    """Scenario price after the spread WIDENS by ``bp_adjust`` bp.

    Inputs: 1-7 as :func:`calculated_price` (``spread`` = the pool's calibrated spread in bp).
    9. bp_adjust : float — spread move in bp (default +10).

    Returns: float — price at ``spread + bp_adjust`` (widening -> lower price).

    ⚠️ The CPR is held at the value passed in. A real spread widening is usually accompanied by
    a rate move, and a rate move changes prepayment; this scenario deliberately does not model
    that, so it isolates the discounting effect and nothing else.
    """
    return calculated_price(wac, wam_months, cpr, curve, spread=spread + bp_adjust,
                            net_coupon=net_coupon, face=face)


def tightening(wac: float, wam_months: int, cpr: float, curve, spread: float,
               bp_adjust: float = 10.0, net_coupon=None, face: float = 100.0) -> float:
    """Scenario price after the spread TIGHTENS by ``bp_adjust`` bp.

    Inputs: identical to :func:`widening`; ``bp_adjust`` is the tightening SIZE (positive).
    Returns: float — price at ``spread - bp_adjust`` (tightening -> higher price).
    """
    return widening(wac, wam_months, cpr, curve, spread, bp_adjust=-bp_adjust,
                    net_coupon=net_coupon, face=face)
