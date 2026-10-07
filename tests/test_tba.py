"""Locks for the TBA forward layer (2026-09-25).

A TBA is the pass-through engine seen through a settlement date. Three things have to hold or
it is a second engine wearing the first one's name: it must reduce to the spot path exactly at
zero settle, its terms must come from the description rather than from a master that is wrong
for these securities, and a contract that has already delivered must be refused rather than
rolled forward a year.

The third one is here because the 2009-06-10 control date found it and a single valuation date
never would have.
"""
import datetime

import pytest

from dataio.phase2 import TBA_TERMS_MONTHS, parse_tba_terms
from pricer.assets.securitized import pool, tba

VAL = datetime.date(2009, 3, 31)


class FlatCurve:
    def __init__(self, z):
        self.z = z

    def zero_rate(self, t):
        return self.z


# --------------------------------------------------------------------------- the degenerate limit

def test_a_zero_settle_forward_is_the_spot_price_bit_for_bit():
    """⭐ The property that makes this a forward ON the engine rather than a second engine.

    Not `approx`. The wrapper delegates at zero settle instead of re-deriving, so any drift
    here means somebody wrote an independent code path that will diverge quietly.
    """
    curve = FlatCurve(0.04)
    for coupon, term, cpr, spread in ((5.5, 360, 25.0, 100.0), (6.0, 180, 8.0, 0.0),
                                      (4.5, 360, 35.0, 250.0)):
        fwd = tba.forward_price(coupon, term, cpr, curve, settle=0.0, spread=spread)
        spot = pool.calculated_price(coupon + tba.TBA_SERVICING_SPREAD_PCT, term, cpr, curve,
                                     spread=spread, net_coupon=coupon)
        assert fwd == spot, f"{coupon}%/{term}m diverged at zero settle"


def test_on_a_flat_curve_at_zero_spread_the_forward_equals_the_spot():
    """The carry identity, and it is not the one I first assumed.

    I expected a premium pool to be cheaper forward than spot. On a FLAT curve it is not:
    with a constant z, PV of the shifted flows is exp(-s(z+spread)) times the spot PV, and
    dividing by DF(s) = exp(-s*z) leaves exactly exp(-s*spread) * spot. At zero spread the
    carry cancels completely and the forward IS the spot price.

    So the forward adjustment measured on the real book — 17.4 bp at a May settle — comes
    from the SHAPE of the 2009 curve (0.42% at six months against 3.92% at thirty years) and
    from the spread, not from the security being at a premium.
    """
    curve = FlatCurve(0.02)
    spot = tba.forward_price(6.0, 360, 20.0, curve, settle=0.0, spread=0.0)
    for s in (0.05, 0.25, 1.0):
        assert tba.forward_price(6.0, 360, 20.0, curve, settle=s, spread=0.0) == \
            pytest.approx(spot, rel=1e-12)


def test_a_spread_makes_the_forward_cheaper_by_exactly_its_carry():
    """With a flat curve the whole effect is exp(-s * spread), which is checkable in closed
    form rather than by eyeball."""
    import math
    curve, s, bp = FlatCurve(0.02), 0.25, 300.0
    spot = tba.forward_price(6.0, 360, 20.0, curve, settle=0.0, spread=bp)
    fwd = tba.forward_price(6.0, 360, 20.0, curve, settle=s, spread=bp)
    assert fwd < spot
    assert fwd == pytest.approx(spot * math.exp(-s * bp * 1e-4), rel=1e-12)


def test_an_upward_sloping_curve_makes_the_forward_cheaper():
    """The real 2009 curve is steep at the short end, which is where the forward adjustment
    on this book actually comes from."""
    class Sloped:
        def zero_rate(self, t):
            return 0.004 + 0.0012 * min(t, 30.0)

    c = Sloped()
    assert tba.forward_price(6.0, 360, 20.0, c, settle=0.125, spread=0.0) < \
        tba.forward_price(6.0, 360, 20.0, c, settle=0.0, spread=0.0)


# --------------------------------------------------------------------------- settlement

def test_a_settle_month_already_past_is_refused_not_rolled():
    """⚠️ The bug the control date caught.

    The holdings file is a 2009-03-31 snapshot, so "SETTLES APRIL" is April 2009. Re-valued at
    2009-06-10 an earlier version rolled the year and priced a forward fourteen months out —
    a contract that had delivered two months before. It returned a perfectly plausible number.
    """
    assert tba.settlement_date(VAL, 4) == datetime.date(2009, 4, 15)
    assert tba.settlement_date(datetime.date(2009, 6, 10), 4) == datetime.date(2009, 4, 15), \
        "must NOT advance to 2010 — the contract is stale, not future"
    with pytest.raises(ValueError, match="already delivered"):
        tba.settle_years(datetime.date(2009, 6, 10), datetime.date(2009, 4, 15))


def test_settle_years_is_act_365_from_valuation():
    assert tba.settle_years(VAL, datetime.date(2009, 4, 15)) == pytest.approx(15 / 365.0)
    assert tba.settle_years(VAL, VAL) == 0.0


# --------------------------------------------------------------------------- term parsing

@pytest.mark.parametrize("short, long_, income, expect", [
    # the ordinary case
    ("", "FHLMC GOLD SINGLE FAMILY 5% 30 YEARS SETTLES APRIL",
     5.0, {"issuer": "FHLMC", "term_months": 360, "coupon_pct": 5.0, "settle_month": 4}),
    # ⚠️ fixed-width fields run together: "YEARS" and "SETTLES" with no space between them
    ("", "FNMA 30 YEAR PASS-THROUGHS 6.5% 30 YEARSSETTLES MAY",
     6.5, {"issuer": "FNMA", "term_months": 360, "coupon_pct": 6.5, "settle_month": 5}),
    # ⚠️ desc_short ENDS on the word SETTLES and the month is over in desc_long. Searching a
    # joined string matched SETTLES in one field and took "GNMA" from the other.
    ("GNMA II JUMBOS 6.0 MAT 30 YEARS SETTLES", "GNMA II JUMBOS 6% 30 YEARS SETTLES APRIL",
     6.0, {"issuer": "GNMA", "term_months": 360, "coupon_pct": 6.0, "settle_month": 4}),
    # ⚠️ no percent sign and an Income rate of exactly 0.000 — both sources needed
    ("", "GNMA I 30 YR SINGLE FAMILY PASS-THROUGHS(SF) 6 30 YEARS SETTLES APR",
     0.0, {"issuer": "GNMA", "term_months": 360, "coupon_pct": 6.0, "settle_month": 4}),
    # ⚠️ the month with no SETTLES in front of it at all
    ("", "FHLMC GOLD 5.5 TBA POOL 30YR APRIL",
     0.0, {"issuer": "FHLMC", "term_months": 360, "coupon_pct": 5.5, "settle_month": 4}),
])
def test_tba_terms_are_read_off_the_description(short, long_, income, expect):
    assert parse_tba_terms(short, long_, income) == expect


def test_a_description_with_no_month_yields_none_rather_than_a_guess():
    """`TBA POOL #9999999 ... DUE 03-15-2030` states no settlement month. Two securities are
    like this and both are named in the disposition instead of priced."""
    got = parse_tba_terms("", "FHLMC GOLD TBA POOL #9999999 5.5 DUE 03-15-2030 REG", 5.5)
    assert got["settle_month"] is None
    assert got["coupon_pct"] == 5.5          # the rest still reads


def test_only_standard_terms_are_accepted():
    """A TBA trades in standard terms. Anything else has been misread, and guessing 20 or 40
    years would put the whole amortisation schedule on the wrong footing."""
    assert set(TBA_TERMS_MONTHS) == {15, 30}
    assert parse_tba_terms("", "FNMA 20 YEARS 5% SETTLES APRIL", 5.0)["term_months"] is None


def test_a_date_in_the_description_is_not_mistaken_for_a_coupon():
    """The bare-number fallback must not read the 03 out of 03-15-2030."""
    got = parse_tba_terms("", "FHLMC GOLD TBA POOL #9999999 DUE 03-15-2030 REG", None)
    assert got["coupon_pct"] is None


# --------------------------------------------------------------------------- the assumption

def test_the_wac_convention_barely_moves_the_answer():
    """⭐ Why the Bloomberg pull's 2026-dated WAC — an as-of error everywhere else in this
    book — is harmless for a TBA. Scheduled amortisation is negligible in a new pool's early
    years, so the flows are interest at the known net coupon plus prepayment at the CPR.
    """
    curve = FlatCurve(0.03)
    settle = tba.settle_years(VAL, datetime.date(2009, 5, 15))
    at = {w: tba.implied_spread_bp(5.5, 360, 25.0, 103.531, curve, settle, wac=w)
          for w in (6.0, 6.25, 6.5)}
    assert max(at.values()) - min(at.values()) < 1.0, \
        f"WAC convention is supposed to be worth under a basis point, got {at}"


# ----------------------------------------------------------------- the two bump kinds (2026-10-07)

class SlopedCurve:
    """z(t) = base + slope*t, so the denominator's rate differs from every flow's."""

    def __init__(self, base, slope):
        self.base, self.slope = base, slope

    def zero_rate(self, t):
        return self.base + self.slope * float(t)


#: The two settlement lags that actually occur in this book: an April 15 and a May 15 settle
#: seen from 2009-03-31, i.e. 15 and 45 days on an Act/365 clock.
REAL_SETTLES = (15 / 365.0, 45 / 365.0)

#: Measured residual of the identity below, on the real 27 at the real 2009-03-31 curve: max
#: 9.99e-09, median 3.25e-09. It is NOT zero — the identity is exact in the derivative and the
#: metrics use a finite 1 bp central bump — so the lock is a measured bound with a 10x margin,
#: not an equality. ⚠️ And it is still 4,000x smaller than the smallest settle it has to
#: distinguish, so a rate bump that silently became a spread bump cannot hide inside it.
IDENTITY_TOLERANCE = 1e-7


@pytest.mark.parametrize("curve", [FlatCurve(0.04), SlopedCurve(0.01, 0.002)])
@pytest.mark.parametrize("settle", REAL_SETTLES)
@pytest.mark.parametrize("coupon,term,cpr,spread", [(5.5, 360, 25.0, 250.0),
                                                    (4.5, 180, 15.0, 180.0),
                                                    (6.5, 360, 35.0, 300.0)])
def test_the_forward_separates_rate_risk_from_spread_risk_by_exactly_the_settlement_lag(
        curve, settle, coupon, term, cpr, spread):
    """⭐⭐ The one place in this book where DV01 and CS01 are different numbers.

    Every other security is discounted at ``z(t) + s``, so a curve bump and a spread bump are
    the same arithmetic. A forward's spread sits in the NUMERATOR only — the financing leg
    carries the rate and not the spread — so differentiating the log picks up ``+settle`` from
    the denominator in the rate case and nothing in the spread case.
    """
    a = (coupon, term, cpr, curve, settle, spread)
    spread_dur, rate_dur = tba.duration(*a), tba.rate_duration(*a)
    assert abs((spread_dur - settle) - rate_dur) < IDENTITY_TOLERANCE, (
        f"spread duration {spread_dur:.9f} minus settle {settle:.9f} should be the rate "
        f"duration {rate_dur:.9f}")
    assert spread_dur > rate_dur, "a forward's spread duration is the longer of the two"


def test_the_identity_lock_is_not_decorative():
    """Mutation: a ``rate_duration`` that silently bumped the spread instead would miss by the
    whole settlement lag, which is four hundred thousand times the tolerance above."""
    curve = FlatCurve(0.04)
    settle = REAL_SETTLES[0]
    spread_dur = tba.duration(5.5, 360, 25.0, curve, settle, 250.0)
    rate_dur = tba.rate_duration(5.5, 360, 25.0, curve, settle, 250.0)
    assert abs((spread_dur - settle) - rate_dur) < IDENTITY_TOLERANCE, "the true pair"
    # the substitution: a rate_duration that returned the spread duration instead
    assert abs((spread_dur - settle) - spread_dur) > 1000 * IDENTITY_TOLERANCE, \
        "the check cannot detect the substitution it exists to forbid"


def test_at_zero_settle_the_two_durations_coincide_and_match_the_spot_pool():
    """The degenerate limit, for the metrics as well as the price.

    ⚠️ Not ``==`` for the rate/spread pair: the two paths convert percent to decimal in a
    different ORDER (``(s+bump)*1e-4`` against ``z + bump*1e-4`` then ``+ s*1e-4``), so
    bit-equality is observed here but is not something the arithmetic guarantees. The spot
    comparison is a true delegation and is held to 1e-12 for the same reason — the pool
    wrapper converts its own bump independently.
    """
    curve = SlopedCurve(0.02, 0.001)
    for coupon, term, cpr, spread in ((5.5, 360, 25.0, 200.0), (4.0, 180, 15.0, 0.0)):
        a = (coupon, term, cpr, curve, 0.0, spread)
        assert abs(tba.rate_duration(*a) - tba.duration(*a)) < 1e-12 * tba.duration(*a)
        spot = pool.duration(coupon + tba.TBA_SERVICING_SPREAD_PCT, term, cpr, curve, spread,
                             net_coupon=coupon)
        assert abs(tba.duration(*a) - spot) < 1e-12 * spot, \
            f"{coupon}%/{term}m: the forward at zero settle is not the spot pool"


def test_a_rate_bump_actually_moves_the_curve():
    """Mutation: a ``_Shifted`` that forgot to add its shift would return a zero duration."""
    curve = FlatCurve(0.04)
    shifted = tba._Shifted(curve, 0.01)
    assert shifted.zero_rate(3.0) == pytest.approx(0.05)
    assert tba.rate_duration(5.5, 360, 25.0, curve, REAL_SETTLES[0], 250.0) > 1.0


def test_dv01_is_the_duration_times_the_price_in_both_families():
    """⚠️ The arithmetic that catches a units slip: a DV01 is a duration times a price times
    1e-4, and the two families must each be internally consistent."""
    curve = FlatCurve(0.035)
    settle = REAL_SETTLES[1]
    a = (5.5, 360, 25.0, curve, settle, 250.0)
    price = tba.forward_price(*a)
    assert tba.dv01(*a) == pytest.approx(tba.duration(*a) * price * 1e-4, rel=1e-9)
    assert tba.rate_dv01(*a) == pytest.approx(tba.rate_duration(*a) * price * 1e-4, rel=1e-9)
    assert tba.dv01(*a) > tba.rate_dv01(*a) > 0


def test_both_convexities_are_positive_and_the_rate_one_is_smaller():
    """⚠️ Positive because the flows are fixed; the market's mortgage convexity is negative and
    the difference is the whole prepayment option. The rate convexity is the smaller of the two
    by roughly ``settle x (2D - settle)``, which is the same cross term the durations show."""
    curve = FlatCurve(0.04)
    a = (6.0, 360, 25.0, curve, REAL_SETTLES[1], 275.0)
    assert tba.convexity(*a) > 0 and tba.rate_convexity(*a) > 0
    assert tba.convexity(*a) > tba.rate_convexity(*a)
    gap = tba.convexity(*a) - tba.rate_convexity(*a)
    settle, dur = REAL_SETTLES[1], tba.duration(*a)
    assert abs(gap - settle * (2 * dur - settle)) < 0.05 * gap


def test_the_metrics_refuse_a_settlement_that_has_already_passed():
    """The 06-10 lesson, extended to the new surface: a delivered forward is not a forward.
    ``settle_years`` is the one owner of that refusal, so the metrics inherit it."""
    with pytest.raises(ValueError, match="already delivered"):
        tba.settle_years(VAL, datetime.date(2009, 3, 1))
