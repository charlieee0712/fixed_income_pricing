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
