"""Instrument-type dispatch through the JSON interface (Round 2b, 2026-08-30).

v1.0 priced one product through one entry point. v1.1 keeps the entry point and the
envelope and adds ``bond.instrument_type``, so one integration reaches every corporate
bond in the book. What must hold, and is pinned here:

1. **v1.0 callers are untouched** — a payload naming no type is a vanilla bond, returns
   the same engine name, and comes back through the old function name unchanged;
2. **the endpoint adds no arithmetic** — every number equals the direct wrapper call
   with ``==``, for every product, not a tolerance;
3. **each product reports what it alone is worth reporting** — the next reset, the
   switch and its reference column, the volatility answer — and nothing it does not have;
4. **volatility is answered, not shrugged at** — the three tree products return real
   numbers in both directions; the four option-free ones return ``null`` with a reason
   that names why THAT product has none;
5. **a missing product input is refused where the caller can act on it** — naming the
   field, not surfacing later as "no spread reprices this bond".

The volatility-direction cases use a deliberately option-ACTIVE bond (a 9.5% coupon
marked at 104 against a par call): a call struck at 100 on a bond worth 96 is worthless,
and asserting a direction there would assert nothing.
"""
import datetime as dt

import pytest

from curves.zero_curve import ZeroCurve
from pricer.assets.corporate import embedded_option, floating, hybrid, stepped, vanilla
from pricer.endpoints import contracts
from pricer.endpoints.main import analyze_payload, analyze_vanilla_payload

VAL = "2009-03-31"
MAT = "2014-04-01"
FREQ = 2
PRICE = 96.5
COUPON = 6.25
MARGIN = 45.0
SWITCH = "2011-04-01"
SCHEDULE = [{"effective_from": None, "rate_pct": 7.0},
            {"effective_from": "2006-03-01", "rate_pct": 7.5}]
ENGINE_SCHEDULE = [(None, 0.07), (dt.date(2006, 3, 1), 0.075)]

# option-ACTIVE fixture: high coupon, marked above the call price
ACTIVE_COUPON = 9.5
ACTIVE_PRICE = 104.0
CALL = [{"date": "2011-04-01", "price_per_100": 100.0}]
ENGINE_CALL = [(dt.date(2011, 4, 1), 100.0)]
PUT = [{"date": "2011-04-01", "price_per_100": 100.0}]
SINK = [{"date": "2011-04-01", "fraction": 0.2, "price_per_100": 100.0}]


def curve():
    return ZeroCurve.from_currency("data", "USD", VAL, freq="Semiannual")


def payload(kind=None, price=PRICE, **bond):
    """One request; ``kind=None`` deliberately omits instrument_type (the v1.0 shape)."""
    body = {"instrument_id": "TEST", "currency": "USD", "coupon_frequency": FREQ,
            "maturity_date": MAT}
    if kind is not None:
        body["instrument_type"] = kind
    body.update(bond)
    return {"operation": "calibrate_and_risk", "bond": body,
            "market": {"valuation_date": VAL, "clean_price_per_100": price}}


def ok(response):
    assert response["status"] == "ok", response.get("errors")
    return response


def error_of(response):
    assert response["status"] == "error", response.get("results")
    return response["errors"][0]


# --------------------------------------------------------------- v1.0 stays untouched

def test_a_payload_with_no_instrument_type_is_still_a_vanilla_bond():
    response = ok(analyze_payload(payload(coupon_pct=COUPON)))
    assert response["engine"] == "corporate_vanilla"
    assert response["inputs_used"]["instrument_type"] == contracts.VANILLA


def test_the_v1_entry_point_name_still_works_and_agrees_exactly():
    a = analyze_vanilla_payload(payload(coupon_pct=COUPON))
    b = analyze_payload(payload(coupon_pct=COUPON))
    assert a["results"] == b["results"]


def test_a_vanilla_response_is_not_padded_with_other_products_inputs():
    used = ok(analyze_payload(payload("vanilla", coupon_pct=COUPON)))["inputs_used"]
    for absent in ("switch_date", "quoted_margin_bp", "call_schedule", "coupon_schedule"):
        assert absent not in used


def test_each_type_reports_its_own_engine_name():
    assert ok(analyze_payload(payload("floating")))["engine"] == "corporate_floating"
    assert ok(analyze_payload(payload("fixed_to_floating", coupon_pct=COUPON,
                                      switch_date=SWITCH, quoted_margin_bp=225.0))
              )["engine"] == "corporate_fixed_to_floating"


# --------------------------------------------- the endpoint adds naming, not arithmetic

def test_floating_endpoint_equals_the_direct_wrapper_call_exactly():
    results = ok(analyze_payload(payload("floating", quoted_margin_bp=MARGIN)))["results"]
    c = curve()
    kw = dict(quoted_margin_bp=MARGIN)
    oas = floating.implied_oas(FREQ, MAT, VAL, PRICE, c, **kw)
    assert results["implied_oas_bp"] == oas
    assert results["effective_duration_years"] == floating.duration(FREQ, MAT, VAL, oas, c, **kw)
    assert results["dv01_per_100"] == floating.dv01(FREQ, MAT, VAL, oas, c, **kw)
    assert results["convexity"] == floating.convexity(FREQ, MAT, VAL, oas, c, **kw)
    assert results["next_reset_years"] == floating.next_reset_years(FREQ, MAT, VAL, c, **kw)


def test_hybrid_endpoint_equals_the_direct_wrapper_call_exactly():
    results = ok(analyze_payload(payload("fixed_to_floating", coupon_pct=COUPON,
                                         switch_date=SWITCH,
                                         quoted_margin_bp=225.0)))["results"]
    c = curve()
    kw = dict(quoted_margin_bp=225.0, float_freq=None)
    oas = hybrid.implied_oas(COUPON, FREQ, MAT, VAL, PRICE, c, SWITCH, **kw)
    assert results["implied_oas_bp"] == oas
    assert results["effective_duration_years"] == \
        hybrid.duration(COUPON, FREQ, MAT, VAL, oas, c, SWITCH, **kw)
    assert results["reference_oas_to_switch_bp"] == \
        hybrid.reference_implied_oas_to_switch(COUPON, FREQ, VAL, PRICE, c, SWITCH)


def test_stepped_endpoint_equals_the_direct_wrapper_call_exactly():
    results = ok(analyze_payload(payload("stepped", coupon_schedule=SCHEDULE)))["results"]
    c = curve()
    oas = stepped.implied_oas(ENGINE_SCHEDULE, FREQ, MAT, VAL, PRICE, c)
    assert results["implied_oas_bp"] == oas
    assert results["effective_duration_years"] == \
        stepped.duration(ENGINE_SCHEDULE, FREQ, MAT, VAL, oas, c)
    assert results["coupon_pct_in_force_at_valuation"] == 7.5


def test_callable_endpoint_equals_the_direct_wrapper_call_exactly():
    results = ok(analyze_payload(payload("callable", price=ACTIVE_PRICE,
                                         coupon_pct=ACTIVE_COUPON,
                                         call_schedule=CALL)))["results"]
    c = curve()
    oas = embedded_option.implied_oas(ACTIVE_COUPON, FREQ, MAT, VAL, ACTIVE_PRICE, c,
                                      call_schedule=ENGINE_CALL)
    assert results["implied_oas_bp"] == oas
    assert results["effective_duration_years"] == \
        embedded_option.duration(ACTIVE_COUPON, FREQ, MAT, VAL, oas, c,
                                 call_schedule=ENGINE_CALL)
    assert results["volatility_used_decimal"] == contracts.DEFAULT_VOLATILITY


def test_a_stepped_bond_whose_steps_are_all_past_matches_the_plain_bond():
    """Row 13's real shape: by 2009 only the 7.50% leg is left."""
    stepped_oas = ok(analyze_payload(payload("stepped",
                                             coupon_schedule=SCHEDULE)))["results"]["implied_oas_bp"]
    plain_oas = ok(analyze_payload(payload("vanilla",
                                           coupon_pct=7.5)))["results"]["implied_oas_bp"]
    assert stepped_oas == pytest.approx(plain_oas, abs=1e-6)


def test_every_response_reprices_the_market_price_it_was_calibrated_to():
    for request in (payload("vanilla", coupon_pct=COUPON),
                    payload("stepped", coupon_schedule=SCHEDULE),
                    payload("floating", quoted_margin_bp=MARGIN),
                    payload("fixed_to_floating", coupon_pct=COUPON, switch_date=SWITCH,
                            quoted_margin_bp=225.0),
                    payload("callable", price=ACTIVE_PRICE, coupon_pct=ACTIVE_COUPON,
                            call_schedule=CALL)):
        results = ok(analyze_payload(request))["results"]
        assert abs(results["calibration_residual_per_100"]) < 1e-6


# ------------------------------------------------------- per-product extras and absences

def test_a_floater_reports_where_its_spread_came_from():
    supplied = ok(analyze_payload(payload("floating", quoted_margin_bp=MARGIN)))["results"]
    assert supplied["quoted_margin_source"] == "supplied_by_caller"
    assert "credit spread" in supplied["spread_interpretation"]

    absorbed = ok(analyze_payload(payload("floating")))["results"]
    assert absorbed["quoted_margin_source"] == "absorbed_into_the_calibrated_spread"
    assert "discount margin" in absorbed["spread_interpretation"]


def test_a_floater_is_not_asked_for_a_coupon_and_says_so_if_given_one():
    response = ok(analyze_payload(payload("floating", coupon_pct=6.0)))
    codes = [w["field"] for w in response["warnings"]]
    assert "bond.coupon_pct" in codes
    assert response["inputs_used"]["coupon_pct"] is None


def test_a_hybrid_reports_its_switch_and_flags_its_reference_column():
    results = ok(analyze_payload(payload("fixed_to_floating", coupon_pct=COUPON,
                                         switch_date=SWITCH,
                                         quoted_margin_bp=225.0)))["results"]
    assert results["next_switch_years"] > 0
    assert "spurious" in results["reference_note"]


def test_the_audit_echo_uses_the_callers_own_units_and_shape():
    """A wrong cell mapping must be visible without reading Python — so the echo comes
    back as objects in PERCENT, not the engine's internal decimals."""
    used = ok(analyze_payload(payload("stepped", coupon_schedule=SCHEDULE)))["inputs_used"]
    assert used["coupon_schedule"] == [{"effective_from": None, "rate_pct": 7.0},
                                       {"effective_from": "2006-03-01", "rate_pct": 7.5}]


# ------------------------------------------------------------------ the volatility answer

def test_the_option_free_products_return_null_volatility_effects_with_a_reason():
    cases = {
        "vanilla": payload("vanilla", coupon_pct=COUPON),
        "stepped": payload("stepped", coupon_schedule=SCHEDULE),
        "floating": payload("floating", quoted_margin_bp=MARGIN),
        "fixed_to_floating": payload("fixed_to_floating", coupon_pct=COUPON,
                                     switch_date=SWITCH, quoted_margin_bp=225.0),
    }
    for kind, request in cases.items():
        block = ok(analyze_payload(request))["applicability"]["yield_volatility"]
        assert block["used"] is False
        assert block["price_effect_per_1pct_vol"] is None      # null, never 0.0
        assert block["oas_effect_bp_per_1pct_vol"] is None
        assert len(block["reason"]) > 40, kind


def test_a_callable_answers_the_volatility_question_in_both_directions():
    """More volatility -> the issuer's right is worth more -> the bond is worth less at a
    fixed spread, and at a fixed price more of the discount is option cost, so the credit
    spread comes IN. Both signs are economics, not convention."""
    block = ok(analyze_payload(payload("callable", price=ACTIVE_PRICE,
                                       coupon_pct=ACTIVE_COUPON,
                                       call_schedule=CALL)))["applicability"]["yield_volatility"]
    assert block["used"] is True
    assert block["price_effect_per_1pct_vol"] < 0
    assert block["oas_effect_bp_per_1pct_vol"] < 0


def test_a_puttable_flips_every_volatility_sign():
    block = ok(analyze_payload(payload("puttable", price=ACTIVE_PRICE,
                                       coupon_pct=ACTIVE_COUPON,
                                       put_schedule=PUT)))["applicability"]["yield_volatility"]
    assert block["price_effect_per_1pct_vol"] > 0
    assert block["oas_effect_bp_per_1pct_vol"] > 0


def test_the_scenario_table_is_opt_in_and_reproduces_the_market_price_at_the_baseline():
    request = payload("callable", price=ACTIVE_PRICE, coupon_pct=ACTIVE_COUPON,
                      call_schedule=CALL)
    assert "scenarios" not in ok(analyze_payload(request))["applicability"]["yield_volatility"]

    request["analysis"] = {"volatility_scenarios": [0.10, 0.15, 0.20]}
    block = ok(analyze_payload(request))["applicability"]["yield_volatility"]
    rows = block["scenarios"]
    assert [r["volatility_decimal"] for r in rows] == [0.10, 0.15, 0.20]
    baseline = next(r for r in rows if r["volatility_decimal"] == 0.15)
    assert baseline["clean_price_at_baseline_oas"] == pytest.approx(ACTIVE_PRICE, abs=1e-6)
    prices = [r["clean_price_at_baseline_oas"] for r in rows]
    spreads = [r["implied_oas_bp_at_market_price"] for r in rows]
    assert prices == sorted(prices, reverse=True)      # price falls as volatility rises
    assert spreads == sorted(spreads, reverse=True)    # spread tightens


def test_volatility_effects_need_a_market_price_and_say_so_when_there_is_none():
    request = payload("callable", coupon_pct=ACTIVE_COUPON, call_schedule=CALL)
    request["operation"] = "price_at_oas"
    request["market"].pop("clean_price_per_100")
    request["analysis"] = {"oas_bp": 400.0}
    block = ok(analyze_payload(request))["applicability"]["yield_volatility"]
    assert block["used"] is True
    assert block["oas_effect_bp_per_1pct_vol"] is None
    assert "market price" in block["reason"]


# ------------------------------------------------------- refusals name an actionable field

def test_an_unknown_instrument_type_is_refused_by_name():
    err = error_of(analyze_payload(payload("mortgage", coupon_pct=COUPON)))
    assert err["code"] == contracts.UNSUPPORTED_INSTRUMENT
    assert err["field"] == "bond.instrument_type"
    assert "vanilla" in err["message"]


def test_a_tree_product_without_its_own_schedule_is_refused():
    err = error_of(analyze_payload(payload("callable", coupon_pct=COUPON)))
    assert err["code"] == contracts.VALIDATION_ERROR
    assert err["field"] == "bond.call_schedule"


def test_a_hybrid_without_a_post_switch_margin_is_refused_not_defaulted():
    """The no-half-modelling rule: a guessed margin would price the floating leg as if
    the borrower paid pure index, and nothing in the output would say so."""
    err = error_of(analyze_payload(payload("fixed_to_floating", coupon_pct=COUPON,
                                           switch_date=SWITCH)))
    assert err["field"] == "bond.quoted_margin_bp"


def test_a_hybrid_without_a_switch_date_is_refused():
    err = error_of(analyze_payload(payload("fixed_to_floating", coupon_pct=COUPON,
                                           quoted_margin_bp=225.0)))
    assert err["field"] == "bond.switch_date"


def test_a_stepped_bond_without_its_schedule_is_refused_with_the_data_gap_named():
    err = error_of(analyze_payload(payload("stepped")))
    assert err["field"] == "bond.coupon_schedule"
    assert "invent" in err["message"]


def test_a_sinking_schedule_must_say_what_its_fractions_are_fractions_of():
    """Without this the engine still refuses — but from inside the spread solver, where
    the message blames the price. The caller must be told the real field."""
    err = error_of(analyze_payload(payload("sinking", coupon_pct=COUPON,
                                           sinking_schedule=SINK)))
    assert err["field"] == "bond.sinking_fraction_basis"
    assert "OUTSTANDING" in err["message"]


def test_an_original_face_sinking_basis_is_refused_with_the_reason():
    err = error_of(analyze_payload(payload("sinking", coupon_pct=COUPON,
                                           sinking_schedule=SINK,
                                           sinking_fraction_basis="original")))
    assert err["field"] == "bond.sinking_fraction_basis"
    assert "sub-bond" in err["message"]


def test_a_schedule_date_sent_as_an_excel_serial_is_refused_like_every_other_date():
    err = error_of(analyze_payload(payload("callable", coupon_pct=COUPON,
                                           call_schedule=[{"date": 40634,
                                                           "price_per_100": 100.0}])))
    assert err["field"] == "bond.call_schedule[0].date"
    assert "1970-01-01" in err["message"]


def test_a_malformed_schedule_is_refused_with_an_example():
    err = error_of(analyze_payload(payload("callable", coupon_pct=COUPON,
                                           call_schedule=["2011-04-01"])))
    assert err["field"] == "bond.call_schedule"
    assert "price_per_100" in err["message"]


def test_refusals_never_leak_a_path_or_a_traceback():
    for request in (payload("mortgage", coupon_pct=COUPON),
                    payload("callable", coupon_pct=COUPON),
                    payload("sinking", coupon_pct=COUPON, sinking_schedule=SINK),
                    payload("fixed_to_floating", coupon_pct=COUPON)):
        message = error_of(analyze_payload(request))["message"]
        assert "/" not in message and "\\" not in message
        assert "Traceback" not in message and ".py" not in message
