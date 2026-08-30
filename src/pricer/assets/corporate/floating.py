"""Floating-rate corporate notes — thin wrappers over ``core.pricing.floating``
(template: ``assets/corporate/floating.py``; legacy ``BondOAS`` analysisType 7 price,
8 implied OAS, 9 effective duration).

Serves Mario's "Pivot of Corp Bonds" column-F rows 14 / 15 / 16 — "GBP LIBOR + Spread",
"Reference Rate + Spread" and "EURIBOR + Spread". One simple function per output,
sharing one input set, as the legacy "Monthly" dictionary lays them out. Nothing here
does arithmetic.

**What is different about a floater's INPUTS** — the single most useful thing to know
when reading this next to ``vanilla.py``:

* there is **no ``coupon``**. A floating coupon is not known in advance; each future
  coupon is *projected* from the curve as a simple forward, plus the note's quoted
  margin. So ``coupon`` is replaced by two inputs:
  ``quoted_margin_bp`` (the contractual spread over the index) and
  ``current_coupon_pct`` (the one coupon already fixed at the last reset, if known).
* **volatility is not an input at all.** A plain floater carries no option, so there is
  nothing for rate volatility to act on — the same statement the vanilla engine makes,
  and for the same structural reason. (A callable floater would need the tree; none is
  held.)
* **effective duration bumps the CURVE, not the spread.** Under a parallel curve shift
  the projected forwards rise with the discount rate and largely cancel it, which is
  why a floater's duration is roughly the time to its next reset rather than its time
  to maturity. Bumping only the spread would make the floater look like a fixed bond —
  the signature error this convention exists to prevent. See ``core.pricing.floating``.

Units at this layer are the legacy sheet's: prices per 100, spreads and margins in
BASIS POINTS, coupons in PERCENT. The core engine underneath works in decimals. All
functions are pure — one note per call, no shared state.
"""
from __future__ import annotations

from pricer.assets.corporate.bonds_input import validate_floating_inputs
from pricer.core.pricing import floating as _core

_BP = 1e-4  # one basis point, in decimal


def _pct(x):
    """PERCENT -> decimal, passing ``None`` through (an unknown current coupon)."""
    return None if x is None else x / 100.0


def calculated_price(cpn_freq: int, maturity, valuation_date, curve,
                     oas: float = 0.0, *, quoted_margin_bp: float = 0.0,
                     current_coupon_pct=None, face: float = 100.0) -> float:
    """CLEAN price of a floating-rate note at a given spread.

    Inputs (see bonds_input.INPUT_CATALOGUE)
    ------
    1. cpn_freq           : int — resets/payments per year (1, 2, 4, 12).
    2. maturity           : date — note maturity.
    3. valuation_date     : date — date of valuation.
    4. curve              : ZeroCurve — own-currency curve. It does BOTH jobs here:
       it projects the future coupons and it discounts them (single-curve, the 2009
       convention; OIS dual-curve is a documented future enhancement, not this).
    5. oas                : float — flat discount spread in BASIS POINTS.
    6. quoted_margin_bp   : float — the note's contractual margin over its index, bp.
       When the workbook carries no number ("EURIBOR + Spread"), pass 0 and let the
       calibrated spread absorb it — see :func:`implied_oas`.
    7. current_coupon_pct : float | None — the coupon already fixed at the last reset,
       in PERCENT. ``None`` = project that period off the curve too.
    8. face               : float — face value (default 100).

    Returns: float — clean price per ``face``.
    """
    validate_floating_inputs(cpn_freq, quoted_margin_bp, current_coupon_pct)
    return _core.price_frn(valuation_date, maturity, curve, oas=oas * _BP,
                           current_coupon=_pct(current_coupon_pct),
                           spread=quoted_margin_bp * _BP, face=face, freq=cpn_freq).clean


def accrued_interest(cpn_freq: int, maturity, valuation_date, curve, *,
                     quoted_margin_bp: float = 0.0, current_coupon_pct=None,
                     face: float = 100.0) -> float:
    """Accrued interest of the current (already-fixed) period.

    Inputs: as :func:`calculated_price` without ``oas`` — accrued depends only on dates
    and the running coupon, never on the discount spread.

    Returns: float — accrued per ``face``; dirty price = clean + this.
    """
    validate_floating_inputs(cpn_freq, quoted_margin_bp, current_coupon_pct)
    return _core.price_frn(valuation_date, maturity, curve, oas=0.0,
                           current_coupon=_pct(current_coupon_pct),
                           spread=quoted_margin_bp * _BP, face=face, freq=cpn_freq).accrued


def implied_oas(cpn_freq: int, maturity, valuation_date, market_price: float, curve, *,
                quoted_margin_bp: float = 0.0, current_coupon_pct=None,
                face: float = 100.0) -> float:
    """Discount spread calibrated to a clean market price (legacy ``BondOAS`` type 8).

    Inputs
    ------
    1-3. cpn_freq / maturity / valuation_date, as above.
    4. market_price       : float — existing CLEAN price per ``face`` (custodian/Bloomberg).
    5. curve              : ZeroCurve.
    6. quoted_margin_bp   : float — contractual margin, bp.
    7. current_coupon_pct : float | None — the fixed current coupon, PERCENT.
    8. face               : float — face value (default 100).

    Returns: float — the flat spread in BASIS POINTS that reprices the note to
    ``market_price`` (price is strictly decreasing in the spread, so the root is unique).

    ⚠️ **What this number contains depends on input 6.** With a documented margin it is
    a credit spread over the index. With ``quoted_margin_bp = 0`` — the case for most of
    this book, whose workbook cells read "... + Spread" with no number — it is a
    discount-margin-type spread that ABSORBS the unknown contractual margin as well as
    credit. The price still reprices exactly and the risk numbers are unaffected (a
    floater's rate sensitivity is structural, not spread-level), and once a real margin
    arrives it can be separated back out. The response layer states this explicitly
    rather than leaving the reader to assume a clean credit spread.
    """
    validate_floating_inputs(cpn_freq, quoted_margin_bp, current_coupon_pct)
    return _core.implied_oas_frn(market_price, valuation_date, maturity, curve,
                                 current_coupon=_pct(current_coupon_pct),
                                 spread=quoted_margin_bp * _BP, face=face,
                                 freq=cpn_freq) * 1e4


def _metrics(cpn_freq, maturity, valuation_date, oas, curve, quoted_margin_bp,
             current_coupon_pct, face) -> dict:
    """Shared curve-bump metric set (duration / dv01 / convexity / next reset)."""
    validate_floating_inputs(cpn_freq, quoted_margin_bp, current_coupon_pct)
    return _core.frn_risk_metrics(valuation_date, maturity, curve, oas * _BP,
                                  current_coupon=_pct(current_coupon_pct),
                                  spread=quoted_margin_bp * _BP, face=face, freq=cpn_freq)


def duration(cpn_freq: int, maturity, valuation_date, oas: float, curve, *,
             quoted_margin_bp: float = 0.0, current_coupon_pct=None,
             face: float = 100.0) -> float:
    """Effective duration in YEARS at the calibrated spread (legacy ``BondOAS`` type 9).

    Inputs: as :func:`implied_oas`, with ``oas`` (bp) in place of ``market_price``.

    Returns: float — effective duration on a **parallel curve bump** (the forwards are
    reprojected, then everything is rediscounted), dirty-price base.

    How to read it — these are the documented regimes, so a negative number is never
    mistaken for a bug:

    * **near par, current coupon KNOWN** → duration ≈ +the time to the next reset. The
      note resets its own rate risk away, so a 30-year floater can have a duration of a
      few weeks.
    * **near par, current coupon PROJECTED** (input 7 omitted) → duration ≈ **minus** the
      time SINCE the last reset. This surprises people, and it is exact: a curve bump
      reprices the running period's coupon too, so the note behaves like a claim struck
      at the last reset rather than one paying a coupon already fixed. Supplying the real
      current coupon is what moves the answer to the other end of the same period.
    * **deep discount** (priced well below par on credit) → price ≈ par minus a spread
      annuity; a rate rise discounts that annuity harder, the gap to par shrinks and the
      price RISES, giving a **negative** duration of order spread × annuity duration —
      this one grows with maturity, unlike the two above.
    * **always** |duration| far below a same-maturity fixed-rate bond. That comparison is
      the reliability check to run when a floater's number looks surprising.
    """
    return _metrics(cpn_freq, maturity, valuation_date, oas, curve, quoted_margin_bp,
                    current_coupon_pct, face)["eff_duration"]


def dv01(cpn_freq: int, maturity, valuation_date, oas: float, curve, *,
         quoted_margin_bp: float = 0.0, current_coupon_pct=None,
         face: float = 100.0) -> float:
    """Price change per +1 bp parallel CURVE shift.

    Inputs: identical to :func:`duration`.
    Returns: float — price change per ``face``; multiply by par / ``face`` for a
    position's dollar DV01. Small and possibly negative, for the reasons in
    :func:`duration`.
    """
    return _metrics(cpn_freq, maturity, valuation_date, oas, curve, quoted_margin_bp,
                    current_coupon_pct, face)["dv01"]


def convexity(cpn_freq: int, maturity, valuation_date, oas: float, curve, *,
              quoted_margin_bp: float = 0.0, current_coupon_pct=None,
              face: float = 100.0) -> float:
    """Effective convexity in YEARS^2 on the same curve bump.

    Inputs: identical to :func:`duration`.
    Returns: float — (P+ + P- - 2·P0) / (bump² · P0), dirty-price base.
    """
    return _metrics(cpn_freq, maturity, valuation_date, oas, curve, quoted_margin_bp,
                    current_coupon_pct, face)["convexity"]


def next_reset_years(cpn_freq: int, maturity, valuation_date, curve, *,
                     quoted_margin_bp: float = 0.0, current_coupon_pct=None,
                     face: float = 100.0) -> float:
    """Years to the next coupon reset — the number :func:`duration` should be read against.

    Inputs: as :func:`calculated_price` without ``oas`` (the reset date is a calendar
    fact; no spread enters it).

    Returns: float — years from valuation to the next reset date. For a near-par note
    the effective duration should land close to this; a large gap is the signal to look
    at the price level before trusting the duration.
    """
    validate_floating_inputs(cpn_freq, quoted_margin_bp, current_coupon_pct)
    return _core.price_frn(valuation_date, maturity, curve, oas=0.0,
                           current_coupon=_pct(current_coupon_pct),
                           spread=quoted_margin_bp * _BP, face=face,
                           freq=cpn_freq).next_reset_t


def widening(cpn_freq: int, maturity, valuation_date, oas: float, curve,
             bp_adjust: float = 10.0, *, quoted_margin_bp: float = 0.0,
             current_coupon_pct=None, face: float = 100.0) -> float:
    """Scenario price after the discount spread WIDENS by ``bp_adjust`` bp.

    Inputs: as :func:`duration`, plus ``bp_adjust`` (spread move in bp, legacy ±10).
    Returns: float — clean price at ``oas + bp_adjust`` (widening -> lower price).
    """
    return calculated_price(cpn_freq, maturity, valuation_date, curve,
                            oas=oas + bp_adjust, quoted_margin_bp=quoted_margin_bp,
                            current_coupon_pct=current_coupon_pct, face=face)


def tightening(cpn_freq: int, maturity, valuation_date, oas: float, curve,
               bp_adjust: float = 10.0, *, quoted_margin_bp: float = 0.0,
               current_coupon_pct=None, face: float = 100.0) -> float:
    """Scenario price after the discount spread TIGHTENS by ``bp_adjust`` bp.

    Inputs: identical to :func:`widening`; ``bp_adjust`` is the tightening SIZE (positive).
    Returns: float — clean price at ``oas - bp_adjust`` (tightening -> higher price).
    """
    return widening(cpn_freq, maturity, valuation_date, oas, curve,
                    bp_adjust=-bp_adjust, quoted_margin_bp=quoted_margin_bp,
                    current_coupon_pct=current_coupon_pct, face=face)


def quoted_margin_bp_from_text(*formula_cells):
    """Read a contractual margin out of a free-text coupon cell, in BASIS POINTS.

    Inputs
    ------
    1..n. formula_cells : str | None — the workbook's ``Coupon_Formula`` /
       ``Coupon_Formula2`` cells, tried in order.

    Returns: float — margin in bp ("EURIBOR + 45bp" -> 45.0, "LIBOR + 0.50%" -> 50.0);
    or **None** when the cell carries no number ("EURIBOR + Spread"). ``None`` means a
    DATA GAP to be flagged and sourced — never a guess, and never silently zero. The
    caller decides between "route to the margin-unavailable flag" and "price with the
    spread absorbed into the OAS", and says which it did.
    """
    margin = _core.parse_frn_spread(*formula_cells)
    return None if margin is None else margin * 1e4
