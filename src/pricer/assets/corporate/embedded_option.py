"""Bonds with embedded exercise rights — the shared asset-layer surface
(template: ``assets/corporate/``).

ONE implementation serves every product that is priced on the short-rate tree. The
per-product modules (``callable.py``, ``puttable.py``, ``sinking.py``) are thin: they
name the right, document its inputs, and pass a schedule through to the functions here.
Nothing in this module does arithmetic on a lattice node — that lives in
``core.pricing.tree``, which is the single implementation the migration exists to keep.

Units at this layer are the legacy sheet's: **coupon in PERCENT, prices per 100 face,
spreads in BASIS POINTS, volatility in DECIMAL** (0.15 = 15%). The core works in
decimals; these wrappers convert. Every price returned is CLEAN (the tree's root value
is dirty; the shared ACT/364 accrued is subtracted here, never a second formula).

Schedules are dated at this layer — ``[(date, price_per_100), ...]`` — and converted to
the tree's ACT/364 time axis by ``core.pricing.tree.schedule_times``.

Leniency (deliberate, and only about presentation): schedules may arrive unsorted, with
prices as numeric strings and dates in any form the date parser accepts; exact duplicate
entries are deduped with a warning. What is refused is economic contradiction — a put
above a call on the same date (the core would silently resolve that in the holder's
favour), a schedule that is entirely inert, or a redemption fraction outside (0, 1].
"""
from __future__ import annotations

import warnings

from pricer.assets.corporate.bonds_input import validate_vanilla_inputs
from pricer.core.pricing.tree import bond_tree, schedule_times
from pricer.core.utils.dates import as_date

_BP = 1e-4              # one basis point, in decimal
SIGMA_DEFAULT = 0.15    # Mario's v1 short-rate volatility (2026-07-03)
VOL_POINT = 0.01        # one volatility percentage point, in decimal
DEFAULT_VOL_SCENARIOS = (0.10, 0.15, 0.20)


# --------------------------------------------------------------------------- schedules

def normalize_schedule(schedule, valuation_date, maturity, label: str):
    """Clean one dated exercise schedule and refuse the contradictory cases.

    Inputs
    ------
    1. schedule       : ``[(date, price_per_100), ...]`` — may be unsorted; prices may be
       numeric strings.
    2. valuation_date : date-like — pricing "as of" date.
    3. maturity       : date-like — bond maturity; entries after it can never fire.
    4. label          : str — "call" / "put" / "sinking", used in messages.

    Returns: ``[(date, price), ...]`` sorted by date, deduped, with post-maturity entries
    dropped — or ``None`` when ``schedule`` is None.
    Raises ``ValueError`` on a duplicate date with two different prices, or on a schedule
    every entry of which falls after maturity (that would price a straight bond while the
    caller believes an option was applied).
    """
    if schedule is None:
        return None
    mat = as_date(maturity)
    by_date = {}
    dropped = 0
    for entry in schedule:
        date, price = as_date(entry[0]), float(entry[1])
        if date > mat:
            dropped += 1
            continue
        if date in by_date:
            if by_date[date] != price:
                raise ValueError(
                    f"{label} schedule has two different prices on {date}: "
                    f"{by_date[date]} and {price} — one date, one price"
                )
            warnings.warn(f"duplicate {label} entry on {date} ignored", stacklevel=3)
            continue
        by_date[date] = price
    if not by_date:
        raise ValueError(
            f"{label} schedule is entirely inert: all {dropped} date(s) fall after the "
            f"maturity {mat}, so the bond would price as a straight bond"
        )
    if dropped:
        warnings.warn(f"{dropped} {label} date(s) after maturity ignored", stacklevel=3)
    return sorted(by_date.items())


def check_call_put_conflict(call_schedule, put_schedule) -> None:
    """Refuse a put priced above a call on the same date.

    Inputs
    ------
    1. call_schedule : normalised ``[(date, price)]`` or None.
    2. put_schedule  : normalised ``[(date, price)]`` or None.

    Returns: None. Raises ``ValueError`` naming both prices when they contradict.

    Why this is a refusal and not a convention: the core applies the issuer's cap and
    then the holder's floor, so a put above a call on one date is silently resolved in
    the holder's favour. There is no economically right answer to pick — the terms are
    contradictory — so the data is refused rather than quietly reinterpreted.
    """
    if not call_schedule or not put_schedule:
        return
    calls = dict(call_schedule)
    for date, put_price in put_schedule:
        call_price = calls.get(date)
        if call_price is not None and put_price > call_price:
            raise ValueError(
                f"contradictory terms on {date}: put price {put_price} is above the call "
                f"price {call_price}. The issuer could call at {call_price} whatever the "
                f"holder does, so these terms cannot both hold — check the schedules."
            )


def _exercise_arrays(lattice, valuation_date, call_schedule, put_schedule):
    """Build the tree's call / put price arrays from normalised dated schedules."""
    call_array = (lattice.call_array(schedule_times(valuation_date, call_schedule))
                  if call_schedule else None)
    put_array = (lattice.put_array(schedule_times(valuation_date, put_schedule))
                 if put_schedule else None)
    return call_array, put_array


def _prepare(coupon, cpn_freq, maturity, valuation_date, curve, volatility,
             call_schedule, put_schedule):
    """Validate inputs, build the calibrated tree, and return everything pricing needs.

    Returns ``(lattice, accrued, call_array, put_array)``.
    """
    validate_vanilla_inputs(coupon, cpn_freq)
    if not (0.0 < float(volatility) <= 2.0):
        raise ValueError(f"volatility must be a decimal in (0, 2]; got {volatility!r} "
                         f"(0.15 = 15%)")
    calls = normalize_schedule(call_schedule, valuation_date, maturity, "call")
    puts = normalize_schedule(put_schedule, valuation_date, maturity, "put")
    check_call_put_conflict(calls, puts)
    lattice, accrued = bond_tree(valuation_date, maturity, coupon / 100.0, curve,
                                 freq=cpn_freq, sigma=float(volatility))
    call_array, put_array = _exercise_arrays(lattice, valuation_date, calls, puts)
    return lattice, accrued, call_array, put_array


# ----------------------------------------------------------------------- price and risk

def calculated_price(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                     oas: float = 0.0, *, volatility: float = SIGMA_DEFAULT,
                     call_schedule=None, put_schedule=None) -> float:
    """CLEAN price of a bond with embedded exercise rights, at a given spread.

    Inputs
    ------
    1. coupon         : float — annual coupon in PERCENT (6.5 = 6.5%).
    2. cpn_freq       : int — payments per year (1, 2, 4, 12).
    3. maturity       : date — bond maturity.
    4. valuation_date : date — date of valuation.
    5. curve          : ZeroCurve — discount curve (bond's own currency).
    6. oas            : float — flat spread in BASIS POINTS.
    7. volatility     : float — short-rate volatility, DECIMAL (default 0.15).
    8. call_schedule  : ``[(date, price_per_100), ...]`` or None — issuer's right.
    9. put_schedule   : ``[(date, price_per_100), ...]`` or None — holder's right.

    Returns: float — clean price per 100 face (tree dirty value minus shared accrued).
    """
    lattice, accrued, call_array, put_array = _prepare(
        coupon, cpn_freq, maturity, valuation_date, curve, volatility,
        call_schedule, put_schedule)
    dirty = lattice.price_bond(coupon / 100.0, oas * _BP, call_array, put_array)
    return dirty - accrued


def implied_oas(coupon: float, cpn_freq: int, maturity, valuation_date,
                market_price: float, curve, *, volatility: float = SIGMA_DEFAULT,
                call_schedule=None, put_schedule=None) -> float:
    """Implied OAS calibrated to a clean market price (legacy ``BondOAS`` analysisType 5).

    Inputs
    ------
    1-5. as :func:`calculated_price` (``market_price`` replaces ``oas``): the existing
       CLEAN price per 100 from the custodian or Bloomberg.
    6. curve          : ZeroCurve.
    7. volatility     : float — DECIMAL; the spread is conditional on it, which is the
       whole point of the volatility scenarios below.
    8-9. call_schedule / put_schedule.

    Returns: float — the flat spread in BASIS POINTS that reprices the bond to
    ``market_price``. Clean-vs-clean: the tree's dirty root minus the shared accrued.
    """
    lattice, accrued, call_array, put_array = _prepare(
        coupon, cpn_freq, maturity, valuation_date, curve, volatility,
        call_schedule, put_schedule)
    return lattice.implied_oas(market_price, coupon / 100.0, call_array, put_array,
                               accrued=accrued) * 1e4


def _metrics(coupon, cpn_freq, maturity, valuation_date, oas, curve, volatility,
             call_schedule, put_schedule) -> dict:
    """Shared bump-and-reprice metric set on the tree (dirty-price denominator)."""
    lattice, accrued, call_array, put_array = _prepare(
        coupon, cpn_freq, maturity, valuation_date, curve, volatility,
        call_schedule, put_schedule)
    return lattice.risk_metrics(coupon / 100.0, oas * _BP, call_array, put_array,
                                accrued=accrued)


def duration(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
             *, volatility: float = SIGMA_DEFAULT, call_schedule=None,
             put_schedule=None) -> float:
    """Effective duration in YEARS at the calibrated spread (``BondOAS`` analysisType 6).

    Inputs: as :func:`calculated_price`, with ``oas`` = the bond's implied spread in bp.
    Returns: float — option-adjusted effective duration, dirty-price base. For a callable
    this is shorter than the straight-bond duration: the call truncates the upside.
    """
    return _metrics(coupon, cpn_freq, maturity, valuation_date, oas, curve, volatility,
                    call_schedule, put_schedule)["eff_duration"]


def dv01(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
         *, volatility: float = SIGMA_DEFAULT, call_schedule=None,
         put_schedule=None) -> float:
    """Price change per +1 bp parallel shift (EXTENSION — no legacy counterpart).

    Inputs: identical to :func:`duration`.
    Returns: float — price drop per 100 face for +1 bp; scale by par / 100 for a position.
    """
    return _metrics(coupon, cpn_freq, maturity, valuation_date, oas, curve, volatility,
                    call_schedule, put_schedule)["dv01"]


def convexity(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
              *, volatility: float = SIGMA_DEFAULT, call_schedule=None,
              put_schedule=None) -> float:
    """Effective convexity in YEARS^2 (EXTENSION — no legacy counterpart).

    Inputs: identical to :func:`duration`. Returns: float; a callable can show NEGATIVE
    convexity, which is the economically correct signature of the issuer's option.
    """
    return _metrics(coupon, cpn_freq, maturity, valuation_date, oas, curve, volatility,
                    call_schedule, put_schedule)["convexity"]


def widening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
             bp_adjust: float = 10.0, *, volatility: float = SIGMA_DEFAULT,
             call_schedule=None, put_schedule=None) -> float:
    """Scenario clean price after the spread WIDENS by ``bp_adjust`` bp.

    Inputs: as :func:`duration`, plus ``bp_adjust`` (default +10, the legacy step).
    Returns: float — clean price at ``oas + bp_adjust``.
    """
    return calculated_price(coupon, cpn_freq, maturity, valuation_date, curve,
                            oas=oas + bp_adjust, volatility=volatility,
                            call_schedule=call_schedule, put_schedule=put_schedule)


def tightening(coupon: float, cpn_freq: int, maturity, valuation_date, oas: float, curve,
               bp_adjust: float = 10.0, *, volatility: float = SIGMA_DEFAULT,
               call_schedule=None, put_schedule=None) -> float:
    """Scenario clean price after the spread TIGHTENS by ``bp_adjust`` bp (positive size).

    Inputs: identical to :func:`widening`. Returns: clean price at ``oas - bp_adjust``.
    """
    return widening(coupon, cpn_freq, maturity, valuation_date, oas, curve,
                    bp_adjust=-bp_adjust, volatility=volatility,
                    call_schedule=call_schedule, put_schedule=put_schedule)


# ------------------------------------------------------------- the volatility question

def price_at_volatility(coupon: float, cpn_freq: int, maturity, valuation_date, curve,
                        oas: float, volatilities=DEFAULT_VOL_SCENARIOS, *,
                        call_schedule=None, put_schedule=None) -> dict:
    """EXPERIMENT 1 — hold the spread, move volatility: what happens to the PRICE?

    Inputs
    ------
    1-5. as :func:`calculated_price` (curve, dates, coupon).
    6. oas          : float — the spread held FIXED across the scenarios, in bp
       (normally the baseline implied OAS).
    7. volatilities : iterable of float — DECIMAL scenarios (default 10% / 15% / 20%).
    8-9. call_schedule / put_schedule.

    Returns: ``{volatility: clean_price}``. For a call-active bond, higher volatility
    makes the issuer's option worth more, so the price FALLS. For a put-active bond the
    holder's option gains and the price RISES.
    """
    return {float(v): calculated_price(coupon, cpn_freq, maturity, valuation_date, curve,
                                       oas=oas, volatility=float(v),
                                       call_schedule=call_schedule,
                                       put_schedule=put_schedule)
            for v in volatilities}


def implied_oas_at_volatility(coupon: float, cpn_freq: int, maturity, valuation_date,
                              market_price: float, curve,
                              volatilities=DEFAULT_VOL_SCENARIOS, *,
                              call_schedule=None, put_schedule=None) -> dict:
    """EXPERIMENT 2 — hold the market price, move volatility: what happens to the OAS?

    Inputs
    ------
    1-4. coupon / frequency / maturity / valuation date.
    5. market_price : float — the CLEAN market price held FIXED across the scenarios.
    6. curve        : ZeroCurve.
    7. volatilities : iterable of float — DECIMAL scenarios.
    8-9. call_schedule / put_schedule.

    Returns: ``{volatility: implied_oas_bp}`` — the spread the model needs to reproduce
    the SAME market price under each volatility. For a call-active bond, a higher
    volatility explains more of the discount as option cost, so the residual credit
    spread TIGHTENS.

    This and :func:`price_at_volatility` answer different questions and must never be
    conflated: one moves the price at a fixed spread, the other moves the spread at a
    fixed price.
    """
    return {float(v): implied_oas(coupon, cpn_freq, maturity, valuation_date,
                                  market_price, curve, volatility=float(v),
                                  call_schedule=call_schedule, put_schedule=put_schedule)
            for v in volatilities}


def volatility_sensitivity(coupon: float, cpn_freq: int, maturity, valuation_date,
                           market_price: float, curve, *,
                           baseline_volatility: float = SIGMA_DEFAULT,
                           bump: float = VOL_POINT, call_schedule=None,
                           put_schedule=None) -> dict:
    """Local slopes of both volatility experiments, around the baseline.

    Inputs
    ------
    1-4. coupon / frequency / maturity / valuation date.
    5. market_price        : float — CLEAN market price, used for the baseline calibration
       and held fixed in the OAS experiment.
    6. curve               : ZeroCurve.
    7. baseline_volatility : float — DECIMAL centre of the bump (default 0.15).
    8. bump                : float — DECIMAL half-step; 0.01 = one volatility point.
    9. call_schedule / put_schedule.

    Returns: dict with the baseline volatility and implied OAS, plus
    ``price_change_per_1_vol_point`` (per 100 face, at the fixed baseline OAS) and
    ``oas_change_bp_per_1_vol_point`` (bp, at the fixed market price). Both are central
    differences, and both name their unit — a vol "point" is 1 percentage point of
    volatility, not 1%.
    """
    base_oas = implied_oas(coupon, cpn_freq, maturity, valuation_date, market_price,
                           curve, volatility=baseline_volatility,
                           call_schedule=call_schedule, put_schedule=put_schedule)
    up, down = baseline_volatility + bump, baseline_volatility - bump
    price_up = calculated_price(coupon, cpn_freq, maturity, valuation_date, curve,
                                oas=base_oas, volatility=up, call_schedule=call_schedule,
                                put_schedule=put_schedule)
    price_down = calculated_price(coupon, cpn_freq, maturity, valuation_date, curve,
                                  oas=base_oas, volatility=down,
                                  call_schedule=call_schedule, put_schedule=put_schedule)
    oas_up = implied_oas(coupon, cpn_freq, maturity, valuation_date, market_price, curve,
                         volatility=up, call_schedule=call_schedule,
                         put_schedule=put_schedule)
    oas_down = implied_oas(coupon, cpn_freq, maturity, valuation_date, market_price,
                           curve, volatility=down, call_schedule=call_schedule,
                           put_schedule=put_schedule)
    scale = VOL_POINT / (2.0 * bump)
    return {
        "baseline_volatility": baseline_volatility,
        "baseline_implied_oas_bp": base_oas,
        "price_change_per_1_vol_point": (price_up - price_down) * scale,
        "oas_change_bp_per_1_vol_point": (oas_up - oas_down) * scale,
    }
