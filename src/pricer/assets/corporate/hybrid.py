"""Fixed-then-floating ("hybrid") corporate bonds — thin wrappers over
``core.pricing.hybrid`` (template: ``assets/corporate/hybrid.py``).

Serves Mario's "Pivot of Corp Bonds" column-F row 12 — "Fixed -> Floating" — and, by the
same construction, rows 6-11 ("Fixed -> Reset ..."), which are the same instrument shape.

**What the product is, in one sentence:** the borrower pays a fixed coupon up to a
contractual switch date, and a floating coupon from that date to maturity. Every such
bond in this portfolio was still inside its FIXED leg at the valuation date, with
switches falling between 2009 and 2037.

**Why it is one bond and not two.** The two legs are priced on exactly the conventions of
the two validated engines — the fixed leg on the vanilla engine's ACT/364 grid anchored
at the SWITCH, the floating leg on the FRN engine's grid anchored at MATURITY and
truncated at the switch — but they are discounted by ONE curve and ONE calibrated spread,
because it is one borrower's one promise. Splitting the spread would be inventing a
second credit.

**Inputs that are specific to this product** (see ``bonds_input.INPUT_CATALOGUE``):

* ``switch_date`` — when the coupon stops being fixed. This is the input that decides
  nearly everything about the risk numbers.
* ``fixed_coupon_pct`` — the coupon in force until then.
* ``quoted_margin_bp`` — the margin over the index afterwards. **If this is unknown the
  bond must NOT be priced here.** A hybrid with a guessed post-switch margin is a bond
  half-modelled and fully reported, which is worse than a flagged one; the drivers route
  those to ``hybrid-margin-unavailable`` and carry the custodian price instead.

Effective duration bumps the CURVE (the FRN convention): the floating leg reprojects its
forwards, so post-switch rate risk largely cancels and the bond's duration is roughly
bounded by the time to the switch — far below a same-maturity fixed bond. That is why
``next_switch_years`` is returned alongside it.

Units are the legacy sheet's: coupons in PERCENT, prices per 100, spreads and margins in
BASIS POINTS. Nothing here does arithmetic.
"""
from __future__ import annotations

from pricer.assets.corporate import vanilla
from pricer.assets.corporate.bonds_input import validate_hybrid_inputs
from pricer.core.pricing import hybrid as _core

_BP = 1e-4  # one basis point, in decimal


def calculated_price(fixed_coupon_pct: float, cpn_freq: int, maturity, valuation_date,
                     curve, switch_date, oas: float = 0.0, *,
                     quoted_margin_bp: float = 0.0, float_freq=None,
                     face: float = 100.0) -> float:
    """CLEAN price of a fixed-then-floating bond at a given spread.

    Inputs (see bonds_input.INPUT_CATALOGUE)
    ------
    1. fixed_coupon_pct : float — the fixed-leg coupon in PERCENT.
    2. cpn_freq         : int — fixed-leg payments per year (1, 2, 4, 12).
    3. maturity         : date — final maturity (a perpetual is truncated far out by the
       caller; the drivers use 90 years, where the face is worth essentially nothing).
    4. valuation_date   : date — date of valuation.
    5. curve            : ZeroCurve — own-currency curve; projects the floating leg AND
       discounts both legs.
    6. switch_date      : date — when the coupon turns floating.
    7. oas              : float — flat spread in BASIS POINTS, applied to both legs.
    8. quoted_margin_bp : float — post-switch margin over the index, bp.
    9. float_freq       : int | None — floating resets per year; ``None`` = same as
       ``cpn_freq``.
    10. face            : float — face value (default 100).

    Returns: float — clean price per ``face``.

    The two degenerate cases delegate rather than approximate, so they agree with the
    single-engine answer bit for bit: a switch at or after maturity is the vanilla fixed
    engine; a switch at or before valuation is the FRN engine.
    """
    validate_hybrid_inputs(fixed_coupon_pct, cpn_freq, quoted_margin_bp)
    return _core.price_hybrid(valuation_date, maturity, curve, oas=oas * _BP,
                              fixed_rate=fixed_coupon_pct / 100.0, switch_date=switch_date,
                              spread=quoted_margin_bp * _BP, fixed_freq=cpn_freq,
                              float_freq=float_freq, face=face).clean


def accrued_interest(fixed_coupon_pct: float, cpn_freq: int, maturity, valuation_date,
                     curve, switch_date, *, quoted_margin_bp: float = 0.0,
                     float_freq=None, face: float = 100.0) -> float:
    """Accrued interest at the valuation date.

    Inputs: as :func:`calculated_price` without ``oas`` — accrued is a date-only
    quantity, so it is identical at every spread.

    Returns: float — accrued per ``face`` on the leg in force (the fixed leg, for every
    bond in this portfolio); dirty price = clean + this.
    """
    validate_hybrid_inputs(fixed_coupon_pct, cpn_freq, quoted_margin_bp)
    return _core.price_hybrid(valuation_date, maturity, curve, oas=0.0,
                              fixed_rate=fixed_coupon_pct / 100.0, switch_date=switch_date,
                              spread=quoted_margin_bp * _BP, fixed_freq=cpn_freq,
                              float_freq=float_freq, face=face).accrued


def implied_oas(fixed_coupon_pct: float, cpn_freq: int, maturity, valuation_date,
                market_price: float, curve, switch_date, *,
                quoted_margin_bp: float = 0.0, float_freq=None,
                face: float = 100.0) -> float:
    """Spread calibrated to a clean market price — the bond's MAIN spread column.

    Inputs
    ------
    1-4. fixed_coupon_pct / cpn_freq / maturity / valuation_date, as above.
    5. market_price     : float — existing CLEAN price per ``face``.
    6. curve            : ZeroCurve.
    7. switch_date      : date — when the coupon turns floating.
    8. quoted_margin_bp : float — post-switch margin, bp (must be the documented one).
    9. float_freq       : int | None — floating resets per year.
    10. face            : float — face value (default 100).

    Returns: float — the flat spread in BASIS POINTS repricing the bond to
    ``market_price``, one spread over both legs.

    These spreads are kept OUT of the by-rating medians: the hybrids in this book are
    junior-subordinated and capital instruments, whose spreads say more about
    subordination than about the issuer's senior credit.
    """
    validate_hybrid_inputs(fixed_coupon_pct, cpn_freq, quoted_margin_bp)
    return _core.implied_oas_hybrid(market_price, valuation_date, maturity, curve,
                                    fixed_rate=fixed_coupon_pct / 100.0,
                                    switch_date=switch_date,
                                    spread=quoted_margin_bp * _BP, fixed_freq=cpn_freq,
                                    float_freq=float_freq, face=face) * 1e4


def _metrics(fixed_coupon_pct, cpn_freq, maturity, valuation_date, oas, curve,
             switch_date, quoted_margin_bp, float_freq, face) -> dict:
    """Shared curve-bump metric set (duration / dv01 / convexity / next switch)."""
    validate_hybrid_inputs(fixed_coupon_pct, cpn_freq, quoted_margin_bp)
    return _core.hybrid_risk_metrics(valuation_date, maturity, curve, oas * _BP,
                                     fixed_rate=fixed_coupon_pct / 100.0,
                                     switch_date=switch_date,
                                     spread=quoted_margin_bp * _BP, fixed_freq=cpn_freq,
                                     float_freq=float_freq, face=face)


def duration(fixed_coupon_pct: float, cpn_freq: int, maturity, valuation_date,
             oas: float, curve, switch_date, *, quoted_margin_bp: float = 0.0,
             float_freq=None, face: float = 100.0) -> float:
    """Effective duration in YEARS at the calibrated spread.

    Inputs: as :func:`implied_oas`, with ``oas`` (bp) in place of ``market_price``.

    Returns: float — effective duration on a parallel CURVE bump, dirty-price base.
    Read it against :func:`next_switch_years`: the floating leg largely resets its own
    rate risk away, so the number is driven by the fixed leg plus the discounting of the
    floating leg's value back from the switch. A 2066-maturity bond with a 2016 switch
    has a duration of a few years, not fifty — that is the model working, not a bug.
    """
    return _metrics(fixed_coupon_pct, cpn_freq, maturity, valuation_date, oas, curve,
                    switch_date, quoted_margin_bp, float_freq, face)["eff_duration"]


def dv01(fixed_coupon_pct: float, cpn_freq: int, maturity, valuation_date, oas: float,
         curve, switch_date, *, quoted_margin_bp: float = 0.0, float_freq=None,
         face: float = 100.0) -> float:
    """Price change per +1 bp parallel CURVE shift.

    Inputs: identical to :func:`duration`.
    Returns: float — price change per ``face``; multiply by par / ``face`` for a
    position's dollar DV01.
    """
    return _metrics(fixed_coupon_pct, cpn_freq, maturity, valuation_date, oas, curve,
                    switch_date, quoted_margin_bp, float_freq, face)["dv01"]


def convexity(fixed_coupon_pct: float, cpn_freq: int, maturity, valuation_date,
              oas: float, curve, switch_date, *, quoted_margin_bp: float = 0.0,
              float_freq=None, face: float = 100.0) -> float:
    """Effective convexity in YEARS^2 on the same curve bump.

    Inputs: identical to :func:`duration`.
    Returns: float — (P+ + P- - 2·P0) / (bump² · P0), dirty-price base.
    """
    return _metrics(fixed_coupon_pct, cpn_freq, maturity, valuation_date, oas, curve,
                    switch_date, quoted_margin_bp, float_freq, face)["convexity"]


def next_switch_years(fixed_coupon_pct: float, cpn_freq: int, maturity, valuation_date,
                      curve, switch_date, *, quoted_margin_bp: float = 0.0,
                      float_freq=None, face: float = 100.0) -> float:
    """Years from valuation to the fixed-to-floating switch.

    Inputs: as :func:`calculated_price` without ``oas`` (a calendar fact; no spread
    enters it).

    Returns: float — years to the switch, 0.0 if the bond is already floating. This is
    the per-bond sanity check for :func:`duration`, and the reason the drivers output it
    on every hybrid row.
    """
    validate_hybrid_inputs(fixed_coupon_pct, cpn_freq, quoted_margin_bp)
    return _core.price_hybrid(valuation_date, maturity, curve, oas=0.0,
                              fixed_rate=fixed_coupon_pct / 100.0, switch_date=switch_date,
                              spread=quoted_margin_bp * _BP, fixed_freq=cpn_freq,
                              float_freq=float_freq, face=face).next_switch_t


def widening(fixed_coupon_pct: float, cpn_freq: int, maturity, valuation_date,
             oas: float, curve, switch_date, bp_adjust: float = 10.0, *,
             quoted_margin_bp: float = 0.0, float_freq=None,
             face: float = 100.0) -> float:
    """Scenario price after the spread WIDENS by ``bp_adjust`` bp.

    Inputs: as :func:`duration`, plus ``bp_adjust`` (spread move in bp, legacy ±10).
    Returns: float — clean price at ``oas + bp_adjust`` (widening -> lower price).
    """
    return calculated_price(fixed_coupon_pct, cpn_freq, maturity, valuation_date, curve,
                            switch_date, oas=oas + bp_adjust,
                            quoted_margin_bp=quoted_margin_bp, float_freq=float_freq,
                            face=face)


def tightening(fixed_coupon_pct: float, cpn_freq: int, maturity, valuation_date,
               oas: float, curve, switch_date, bp_adjust: float = 10.0, *,
               quoted_margin_bp: float = 0.0, float_freq=None,
               face: float = 100.0) -> float:
    """Scenario price after the spread TIGHTENS by ``bp_adjust`` bp.

    Inputs: identical to :func:`widening`; ``bp_adjust`` is the tightening SIZE (positive).
    Returns: float — clean price at ``oas - bp_adjust`` (tightening -> higher price).
    """
    return widening(fixed_coupon_pct, cpn_freq, maturity, valuation_date, oas, curve,
                    switch_date, bp_adjust=-bp_adjust, quoted_margin_bp=quoted_margin_bp,
                    float_freq=float_freq, face=face)


def reference_implied_oas_to_switch(fixed_coupon_pct: float, cpn_freq: int,
                                    valuation_date, market_price: float, curve,
                                    switch_date, face: float = 100.0) -> float:
    """REFERENCE ONLY — the spread if the bond were repaid in full at the switch date.

    Inputs
    ------
    1. fixed_coupon_pct : float — the fixed-leg coupon in PERCENT.
    2. cpn_freq         : int — payments per year.
    3. valuation_date   : date — date of valuation.
    4. market_price     : float — existing CLEAN price per ``face``.
    5. curve            : ZeroCurve.
    6. switch_date      : date — treated here as a maturity.
    7. face             : float — face value (default 100).

    Returns: float — the spread in BASIS POINTS of an ordinary bullet bond maturing at
    ``switch_date`` at par.

    ⚠️ **This is a secondary column, never the answer.** Most of these bonds carry an
    issuer call at the switch, so "priced to the switch" is a market convention worth
    reporting — but only while the bond trades near par. For a deep discount it is
    actively misleading: a bond marked at 36 is being priced for EXTENSION, i.e. on the
    expectation that the issuer will *not* repay at the switch, and forcing par at that
    date produces a spread of many hundreds of basis points that describes nothing. The
    main column is always :func:`implied_oas`.

    That this function is a plain vanilla call is itself the point: it delegates to the
    vanilla engine rather than re-deriving a bullet, and the margin-0 identity in the
    core proves the hybrid reduces to exactly this bond when the floating leg is worth
    par at the switch.
    """
    return vanilla.implied_oas(fixed_coupon_pct, cpn_freq, switch_date, valuation_date,
                               market_price, curve, face=face)
