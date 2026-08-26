"""JSON/Excel interface locks (Mario follow-up, 2026-08-25).

The endpoint is an ARRANGEMENT layer: it must reproduce the approved vanilla
functions exactly, refuse the inputs that would silently mis-price a bond, and be
explicit about the inputs a generic Excel form sends that vanilla does not use.

The three groups below are, in order: parity with direct function calls, the firm
rules (economics), and the lenient rules (presentation). The CLI gets its own two
tests because the Excel bridge talks to the process, not to Python.

Curve fixtures are real repo data at the adopted 2009-03-31 baseline; the three
currencies are chosen because each fails differently and all three failures are live
(EUR prices, CHF has no file, KRW has the file but not that date, GBP has both but
its par curve is not arbitrage-free there).
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

from pricer.assets.corporate import vanilla
from pricer.core.market.curves import resolve_curve
from pricer.endpoints import contracts
from pricer.endpoints import pricing as endpoint_pricing
from pricer.endpoints.main import analyze_vanilla_payload

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DATA = _ROOT / "data"

VAL = "2009-03-31"
MAT = "2017-01-15"
COUPON = 6.5
FREQ = 2
PRICE = 94.25


@pytest.fixture(autouse=True)
def _data_dir(monkeypatch):
    """Point the endpoint at the repo's own curve exports, whatever the CWD."""
    monkeypatch.setenv("FIP_DATA_DIR", str(_DATA))


def request_payload(**overrides):
    """A valid USD calibrate request, with dotted-path overrides for the odd field."""
    payload = {
        "schema_version": "1.0",
        "request_id": "TEST-0001",
        "operation": "calibrate_and_risk",
        "bond": {
            "instrument_id": "TEST-BOND-001",
            "currency": "USD",
            "coupon_pct": COUPON,
            "coupon_frequency": FREQ,
            "maturity_date": MAT,
            "day_count_label": "30/360",
        },
        "market": {"valuation_date": VAL, "clean_price_per_100": PRICE},
        "analysis": {"spread_shift_bp": 10.0},
    }
    for dotted, value in overrides.items():
        section, _, field = dotted.partition(".")
        if not field:
            if value is None:
                payload.pop(section, None)
            else:
                payload[section] = value
        elif value is None:
            payload[section].pop(field, None)
        else:
            payload.setdefault(section, {})[field] = value
    return payload


def usd_curve(freq=FREQ):
    """The same curve the endpoint resolves, for direct-call comparisons."""
    return resolve_curve("USD", VAL, freq, data_dir=str(_DATA))


def error_of(response):
    """The single error entry of a refused response."""
    assert response["status"] == "error", response
    assert len(response["errors"]) == 1
    return response["errors"][0]


# --------------------------------------------------------------------------- parity

def test_usd_calibrate_returns_every_vanilla_output():
    response = analyze_vanilla_payload(request_payload())
    assert response["status"] == "ok", response["errors"]
    results = response["results"]
    assert set(results) == {
        "model_clean_price_per_100", "model_dirty_price_per_100", "accrued_interest_per_100",
        "implied_oas_bp", "oas_source", "effective_duration_years", "dv01_per_100",
        "convexity", "price_spread_tighter_per_100", "price_spread_wider_per_100",
        "calibration_residual_per_100",
    }
    assert results["oas_source"] == "calibrated_from_clean_price"
    assert results["implied_oas_bp"] > 0
    assert abs(results["calibration_residual_per_100"]) < 1e-8      # it reprices the mark
    assert results["model_dirty_price_per_100"] > results["model_clean_price_per_100"]
    assert response["market_data"]["curve_id"] == f"USD|{VAL}|Semiannual"


def test_endpoint_equals_direct_function_calls():
    """The parity requirement (plan §7): no endpoint-specific arithmetic anywhere."""
    response = analyze_vanilla_payload(request_payload())
    results = response["results"]
    curve = usd_curve()

    oas = vanilla.implied_oas(COUPON, FREQ, MAT, VAL, PRICE, curve)
    assert results["implied_oas_bp"] == oas
    assert results["model_clean_price_per_100"] == vanilla.calculated_price(
        COUPON, FREQ, MAT, VAL, curve, oas=oas)
    assert results["effective_duration_years"] == vanilla.duration(
        COUPON, FREQ, MAT, VAL, oas, curve)
    assert results["dv01_per_100"] == vanilla.dv01(COUPON, FREQ, MAT, VAL, oas, curve)
    assert results["convexity"] == vanilla.convexity(COUPON, FREQ, MAT, VAL, oas, curve)
    assert results["price_spread_wider_per_100"] == vanilla.widening(
        COUPON, FREQ, MAT, VAL, oas, curve, bp_adjust=10.0)
    assert results["price_spread_tighter_per_100"] == vanilla.tightening(
        COUPON, FREQ, MAT, VAL, oas, curve, bp_adjust=10.0)


def test_price_at_oas_equals_direct_call_and_round_trips():
    calibrated = analyze_vanilla_payload(request_payload())["results"]["implied_oas_bp"]
    response = analyze_vanilla_payload(request_payload(
        operation="price_at_oas", **{"analysis.oas_bp": calibrated, "market.clean_price_per_100": None}))
    assert response["status"] == "ok", response["errors"]
    results = response["results"]
    assert results["oas_source"] == "supplied_by_caller"
    assert results["implied_oas_bp"] == calibrated
    assert results["calibration_residual_per_100"] is None
    assert results["model_clean_price_per_100"] == vanilla.calculated_price(
        COUPON, FREQ, MAT, VAL, usd_curve(), oas=calibrated)
    assert abs(results["model_clean_price_per_100"] - PRICE) < 1e-8      # round trip


def test_own_currency_curve_is_used_for_a_non_usd_bond():
    response = analyze_vanilla_payload(request_payload(**{"bond.currency": "EUR"}))
    assert response["status"] == "ok", response["errors"]
    assert response["market_data"]["curve_id"] == f"EUR|{VAL}|Semiannual"
    assert response["market_data"]["pricing_currency"] == "EUR"
    usd = analyze_vanilla_payload(request_payload())["results"]["implied_oas_bp"]
    assert response["results"]["implied_oas_bp"] != usd      # a different curve, really


def test_coupon_frequency_selects_the_matching_curve_variant():
    response = analyze_vanilla_payload(request_payload(**{"bond.coupon_frequency": 4}))
    assert response["status"] == "ok", response["errors"]
    assert response["market_data"]["curve_id"] == f"USD|{VAL}|Quarterly"


# ----------------------------------------------------------------------------- firm

def test_excel_date_serial_is_refused():
    """pd.Timestamp(39903) is 1970-01-01 — a serial must never reach the engine."""
    error = error_of(analyze_vanilla_payload(request_payload(**{"market.valuation_date": 39903})))
    assert error["code"] == contracts.VALIDATION_ERROR
    assert error["field"] == "market.valuation_date"
    assert "1970" in error["message"]


def test_missing_currency_is_refused():
    error = error_of(analyze_vanilla_payload(request_payload(**{"bond.currency": None})))
    assert error["code"] == contracts.VALIDATION_ERROR
    assert error["field"] == "bond.currency"


def test_unmapped_currency_is_curve_not_found():
    error = error_of(analyze_vanilla_payload(request_payload(**{"bond.currency": "CHF"})))
    assert error["code"] == contracts.CURVE_NOT_FOUND
    assert "CHF" in error["message"]


def test_missing_curve_date_is_curve_not_found():
    """KRW has a par-curve file, but no row for the 2009-03-31 baseline."""
    error = error_of(analyze_vanilla_payload(request_payload(**{"bond.currency": "KRW"})))
    assert error["code"] == contracts.CURVE_NOT_FOUND
    assert VAL in error["message"]


def test_unbuildable_curve_is_reported_as_a_build_failure():
    """GBP has the file and the date; its par curve is not arbitrage-free there."""
    error = error_of(analyze_vanilla_payload(request_payload(**{"bond.currency": "GBP"})))
    assert error["code"] == contracts.CURVE_BUILD_FAILED
    assert "GBP" in error["message"]


@pytest.mark.parametrize("currency", ["CHF", "KRW", "GBP"])
def test_curve_errors_never_leak_a_file_path(currency):
    message = error_of(analyze_vanilla_payload(request_payload(
        **{"bond.currency": currency})))["message"]
    assert "/" not in message and "\\" not in message and ".txt" not in message


def test_supplied_oas_is_refused_in_calibration_mode():
    """The methodology lock: this operation CALIBRATES the spread from the mark."""
    error = error_of(analyze_vanilla_payload(request_payload(**{"analysis.oas_bp": 400.0})))
    assert error["code"] == contracts.VALIDATION_ERROR
    assert error["field"] == "analysis.oas_bp"
    assert "price_at_oas" in error["message"]


def test_maturity_on_or_before_valuation_is_refused():
    error = error_of(analyze_vanilla_payload(request_payload(**{"bond.maturity_date": "2009-03-31"})))
    assert error["code"] == contracts.VALIDATION_ERROR
    assert error["field"] == "bond.maturity_date"


def test_unknown_operation_and_batch_payloads_are_refused_clearly():
    error = error_of(analyze_vanilla_payload(request_payload(operation="price_the_book")))
    assert error["code"] == contracts.UNSUPPORTED_OPERATION

    batch = error_of(analyze_vanilla_payload({"requests": [request_payload()]}))
    assert batch["code"] == contracts.UNSUPPORTED_OPERATION
    assert "batch" in batch["message"].lower()


def test_an_unreachable_price_is_reported_as_a_calibration_failure(monkeypatch):
    """The solver widens its own bracket, so an unbracketable price is hard to build
    from real inputs — what matters here is that its ValueError becomes a structured
    CALIBRATION_FAILED and never a traceback."""
    def refuses(*args, **kwargs):
        raise ValueError("cannot bracket implied spread for target_price=...")

    monkeypatch.setattr(endpoint_pricing.vanilla, "implied_oas", refuses)
    error = error_of(analyze_vanilla_payload(request_payload()))
    assert error["code"] == contracts.CALIBRATION_FAILED
    assert error["field"] == "market.clean_price_per_100"
    assert "Traceback" not in error["message"]


# -------------------------------------------------------------------------- lenient

def test_volatility_is_accepted_echoed_and_reported_as_unused():
    response = analyze_vanilla_payload(request_payload(model={"yield_volatility_decimal": 0.15}))
    assert response["status"] == "ok", response["errors"]
    applicability = response["applicability"]["yield_volatility"]
    assert applicability["input_value_decimal"] == 0.15
    assert applicability["used"] is False
    assert applicability["price_effect_per_1pct_vol"] is None       # null, never 0.0
    assert applicability["oas_effect_bp_per_1pct_vol"] is None
    assert "volatility" in applicability["reason"].lower()
    # ...and it changed no number at all
    assert response["results"] == analyze_vanilla_payload(request_payload())["results"]


def test_applicability_is_reported_when_volatility_and_day_count_are_absent():
    response = analyze_vanilla_payload(request_payload(**{"bond.day_count_label": None}))
    assert response["applicability"]["yield_volatility"]["input_value_decimal"] is None
    day_count = response["applicability"]["day_count"]
    assert day_count["input_value_label"] is None
    assert day_count["used"] is False
    assert "ACT/364" in day_count["convention_used"]


def test_day_count_label_is_echoed_and_marked_unused():
    day_count = analyze_vanilla_payload(request_payload())["applicability"]["day_count"]
    assert day_count["input_value_label"] == "30/360"
    assert day_count["used"] is False


def test_lowercase_currency_and_numeric_strings_are_normalised():
    response = analyze_vanilla_payload(request_payload(
        **{"bond.currency": " usd ", "bond.coupon_pct": "6.5", "bond.coupon_frequency": "2"}))
    assert response["status"] == "ok", response["errors"]
    assert response["inputs_used"]["currency"] == "USD"
    assert response["results"] == analyze_vanilla_payload(request_payload())["results"]


def test_face_value_other_than_100_warns_and_still_quotes_per_100():
    response = analyze_vanilla_payload(request_payload(**{"bond.face_value": 1000.0}))
    assert response["status"] == "ok", response["errors"]
    assert response["results"] == analyze_vanilla_payload(request_payload())["results"]
    codes = [w["code"] for w in response["warnings"]]
    assert contracts.FACE_VALUE_NOT_APPLIED in codes
    assert response["inputs_used"]["face_value_supplied"] == 1000.0
    assert response["inputs_used"]["face_value_per_quote"] == 100.0


def test_unknown_fields_are_ignored_with_a_warning():
    response = analyze_vanilla_payload(request_payload(**{"bond.sector": "utilities"}))
    assert response["status"] == "ok", response["errors"]
    warning = [w for w in response["warnings"] if w["code"] == contracts.UNUSED_FIELD]
    assert warning and warning[0]["field"] == "bond.sector"
    assert response["results"] == analyze_vanilla_payload(request_payload())["results"]


def test_missing_request_id_operation_and_shift_get_defaults():
    payload = request_payload(request_id=None, operation=None, **{"analysis.spread_shift_bp": None})
    response = analyze_vanilla_payload(payload)
    assert response["status"] == "ok", response["errors"]
    assert response["request_id"].startswith("auto-")
    assert response["operation"] == contracts.OPERATION_CALIBRATE
    assert response["inputs_used"]["spread_shift_bp"] == contracts.DEFAULT_SPREAD_SHIFT_BP


def test_inputs_used_echoes_what_the_engine_ran_on():
    used = analyze_vanilla_payload(request_payload())["inputs_used"]
    assert used["currency"] == "USD" and used["coupon_pct"] == COUPON
    assert used["maturity_date"] == MAT and used["valuation_date"] == VAL
    assert used["clean_price_per_100"] == PRICE and used["oas_bp_supplied"] is None


def test_every_response_is_standard_json():
    for payload in (request_payload(), request_payload(**{"bond.currency": "CHF"})):
        text = json.dumps(analyze_vanilla_payload(payload), allow_nan=False)
        assert json.loads(text)["schema_version"] == contracts.SCHEMA_VERSION


# -------------------------------------------------------------------------------CLI

def run_cli(tmp_path, payload_text, name="request.json"):
    """Run scripts/price_json.py on a request file; return (exit code, response)."""
    request_file = tmp_path / name
    request_file.write_text(payload_text, encoding="utf-8")
    response_file = tmp_path / "response.json"
    env = dict(os.environ, FIP_DATA_DIR=str(_DATA), PYTHONPATH="src")
    done = subprocess.run(
        [sys.executable, "scripts/price_json.py",
         "--input", str(request_file), "--output", str(response_file)],
        cwd=str(_ROOT), env=env, capture_output=True, text=True,
    )
    response = json.loads(response_file.read_text(encoding="utf-8"))
    return done, response


def test_cli_writes_a_response_and_exits_zero(tmp_path):
    done, response = run_cli(tmp_path, json.dumps(request_payload()))
    assert done.returncode == 0, done.stderr
    assert response["status"] == "ok"
    assert done.stdout.strip() == "ok request_id=TEST-0001"
    assert "coupon_pct" not in done.stdout          # the payload is never echoed


def test_cli_turns_malformed_json_into_an_error_response(tmp_path):
    done, response = run_cli(tmp_path, "{ this is not json ]")
    assert done.returncode == 1
    assert response["status"] == "error"
    assert response["errors"][0]["code"] == contracts.INVALID_JSON
    assert "Traceback" not in done.stdout and "Traceback" not in done.stderr
