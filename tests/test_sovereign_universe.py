"""Locks for the Government / Municipal classes (Mario, Summary!K23 + K55, 2026-09-03).

Three things are pinned here, in rising order of how quietly they could break:

1. **Counts and routes** -- the ordinary golden-master check.
2. **The price/par quotation** -- one identity that must hold for every security after
   conversion, plus the requirement that the registry agree with the denomination token the
   custodian wrote in the description. A wrong ``TITLE_FACE`` entry would otherwise show up
   only as a spread that looks plausible, which is exactly how the GBP units bug survived
   two months.
3. **The anchor property** -- a sovereign discounted on its own government curve must
   reprice to roughly zero. This is the end-to-end check: it fails if the curve is
   mis-routed, if a par-yield file is read in the wrong units, or if a price is on the
   wrong scale, none of which the count tests can see.

Workbook-dependent tests skip when the URS file is absent; the routing and label tests are
synthetic and always run.
"""
import os
import pathlib

import pandas as pd
import pytest

from curves.bootstrap import PAR_YIELD_UNITS, load_par_curve
from curves.zero_curve import CURVE_FILE, ZeroCurve
from dataio.phase2 import (PHASE2_CLASSES, SOVEREIGN_CLASSES, SUBCATS, TITLE_FACE,
                           _route_sovereign, _spread_meaning, _terms_note,
                           build_phase2_from_path)
from pricing.calibrate import implied_oas

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DEFAULT = "data/URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"
VAL = "2009-03-31"


def _find_urs():
    p = os.environ.get("FIP_URS_XLSX")
    if p and pathlib.Path(p).exists():
        return pathlib.Path(p)
    c = _ROOT / _DEFAULT
    return c if c.exists() else None


URS = _find_urs()
DATA = str(_ROOT / "data")


@pytest.fixture(scope="module")
def sovereign():
    if URS is None:
        pytest.skip("URS workbook not found; set FIP_URS_XLSX")
    return build_phase2_from_path(str(URS), classes=SOVEREIGN_CLASSES)


@pytest.fixture(scope="module")
def merged(sovereign):
    bonds, recon, _ = sovereign
    return bonds.merge(recon.drop(columns=["asset_class", "price_quotation"]), on="asset_id")


# --------------------------------------------------------------- routing (synthetic)
def _row(coupon_pct, short="", long="", call=None, maturity="2020-01-01"):
    return {"coupon_pct": coupon_pct, "desc_short": short, "desc_long": long,
            "has_call": call is not None, "call_date": call,
            "maturity": pd.Timestamp(maturity)}


def test_a_stripped_security_is_claimed_by_the_zero_rule_first():
    # TNTD03983600 "TREAS BD STRIPPED CALL" carries a call date EQUAL to its maturity. It
    # would also survive the exercise branch, but for the wrong reason; the zero rule owns it.
    r = _row(0.0, "UNITED STATES TREAS BD STRIPPED CALL", call="2009-11-15",
             maturity="2009-11-15")
    assert _route_sovereign(r) == "zero"


def test_a_call_on_the_maturity_date_is_a_redemption_not_an_option():
    assert _route_sovereign(_row(5.0, call="2020-01-01", maturity="2020-01-01")) == "vanilla"
    # and inside the make-whole window it is still a bullet
    assert _route_sovereign(_row(5.0, call="2019-12-28", maturity="2020-01-01")) == "vanilla"


def test_a_call_after_maturity_is_named_as_a_data_error():
    assert _route_sovereign(_row(5.0, call="2021-01-01", maturity="2020-01-01")) \
        == "call-after-maturity"


def test_a_genuine_gap_routes_to_the_lattice():
    assert _route_sovereign(_row(12.5, call="2015-01-01", maturity="2020-01-01")) \
        == "callable-lattice"


def test_a_floater_and_a_step_up_are_refused_rather_than_priced_flat():
    assert _route_sovereign(_row(1.0, "JAPAN FRN 11/2021")) == "floating-reference-unverified"
    assert _route_sovereign(_row(7.5, "RUSSIAN FEDERATION", "REG NT REG-S STEP UP DUE")) \
        == "coupon-schedule-unavailable"


def test_the_zero_rule_outranks_the_floating_and_step_up_tokens():
    # a stripped security has no coupon to schedule, whatever the description says
    assert _route_sovereign(_row(0.0, "SOMETHING FRN STEP UP")) == "zero"


# --------------------------------------------------------------- labels (synthetic)
def test_spread_meaning_separates_an_anchor_from_a_real_spread():
    assert _spread_meaning("USD", "UNITED STATES TREAS NTS") == "own-curve-anchor"
    assert _spread_meaning("USD", "RUSSIAN FEDERATION 7.5%") == "spread-over-government"
    assert _spread_meaning("USD", "UNITED MEXICAN STS MEDIUM TERM NTS") == "spread-over-government"
    assert _spread_meaning("GBP", "UK(GOVT OF) 4% STK") == "own-curve-anchor"
    assert _spread_meaning("AUD", "QUEENSLAND TREASURY CORP") == "spread-over-government"
    assert _spread_meaning("JPY", "ONTARIO(PROV OF) 1.875%") == "spread-over-government"


def test_every_euro_sovereign_is_relative_to_the_composite_and_others_are_not():
    for issuer in ("GERMANY(FEDERAL REPUBLIC)", "IRELAND(REPUBLIC OF)", "BONOS Y OBLIG DEL ESTADO"):
        assert _spread_meaning("EUR", issuer) == "relative-to-euro-composite"
    # a non-euro-area issuer borrowing in EUR is a spread, not relative value
    assert _spread_meaning("EUR", "BRAZIL(FED REP OF)") == "spread-over-government"


def test_a_documented_sinking_fund_is_noted_but_does_not_block():
    note = _terms_note("ILLINOIS ST TAXABLE-PENSION", "TAXABLE SINKING FD 06-01-2024 N/C")
    assert "sinking fund" in note and "bullet" in note
    assert _terms_note("UK(GOVT OF) 4% STK") == ""


# --------------------------------------------------------------- curve registry
def test_every_mapped_currency_points_at_a_file_that_exists():
    for ccy, fname in CURVE_FILE.items():
        assert (pathlib.Path(DATA) / fname).exists(), f"{ccy} -> {fname} missing"


def test_malaysia_is_deliberately_absent_so_the_driver_names_the_gap():
    # MYR has no par-curve file at all. Mapping it to a neighbour would silently price a
    # Malaysian government bond on someone else's curve.
    assert "MYR" not in CURVE_FILE


@pytest.mark.parametrize("ccy", ["BRL", "CAD", "ILS", "MXN", "NOK", "SEK", "SGD"])
def test_the_currencies_added_for_this_class_really_do_store_decimals(ccy):
    # The registry claim, reproduced against the RAW file -- the standing rule after the GBP
    # units bug. A file storing percent would come back ~100x larger.
    assert CURVE_FILE[ccy] not in PAR_YIELD_UNITS      # i.e. it takes the decimal default
    _, par = load_par_curve(str(pathlib.Path(DATA) / CURVE_FILE[ccy]), VAL)
    assert 0.05 < float(max(par)) < 30.0, f"{ccy} long-end par yield {max(par)}% is not a market"


# --------------------------------------------------------------- counts and routes
def test_the_two_classes_reproduce_marios_two_summary_rows(sovereign):
    _, _, counts = sovereign
    assert counts["government"]["rows"] == 153
    assert counts["government"]["unique"] == 147
    assert counts["municipal"]["rows"] == 7
    assert counts["municipal"]["unique"] == 7


def test_the_route_split_is_what_the_holdings_say(sovereign):
    _, _, counts = sovereign
    assert counts["government"]["routes"] == {
        "vanilla": 113, "zero": 31, "callable-lattice": 1,
        "coupon-schedule-unavailable": 1, "floating-reference-unverified": 1}
    assert counts["municipal"]["routes"] == {"vanilla": 7}


def test_the_legacy_class_list_is_untouched_by_the_sovereign_work():
    # phase2_risk.py calls with no class argument and its CSV is a production artifact.
    if URS is None:
        pytest.skip("URS workbook not found")
    _, _, counts = build_phase2_from_path(str(URS))
    assert tuple(counts) == PHASE2_CLASSES
    assert (counts["agency"]["unique"], counts["guaranteed"]["unique"],
            counts["linker"]["unique"]) == (39, 9, 15)
    assert counts["agency"]["routes"] == {
        "vanilla": 27, "callable-lattice": 5, "call-passed-vanilla": 4, "zero": 2,
        "cmo-tranche": 1}


def test_asking_for_a_class_that_does_not_exist_is_refused():
    if URS is None:
        pytest.skip("URS workbook not found")
    with pytest.raises(ValueError, match="unknown asset class"):
        build_phase2_from_path(str(URS), classes=["not_a_class"])


def test_both_new_classes_are_registered_sub_categories():
    assert SUBCATS["government"] == "Government Bonds"
    assert SUBCATS["municipal"] == "Municipal/Provincial Bonds"


# --------------------------------------------------------------- the quotation
def test_the_quotation_split_is_the_one_the_custodian_identity_gives(sovereign):
    bonds, _, _ = sovereign
    assert bonds["price_quotation"].value_counts().to_dict() == {
        "currency-face": 148, "titles-of-100": 5, "titles-of-1000": 1}


def test_one_identity_holds_for_every_security_after_conversion(merged):
    """The anti-rot check. ``bt_per_100`` and ``par_face`` are two halves of one restatement;
    if a future TITLE_FACE entry is wrong, or a currency is added without one, this fails
    loudly instead of producing a spread that merely looks odd."""
    implied = merged["gold_mkt_value"] * merged["fx_rate"].fillna(1.0) / merged["par_face"] * 100.0
    gap = (merged["bt_per_100"] - implied).abs()
    worst = merged.loc[gap.idxmax()]
    assert gap.max() < 0.05, (
        f"{worst['asset_id']} ({worst['currency']}, {worst['price_quotation']}): "
        f"bt_per_100 {worst['bt_per_100']} vs {implied[gap.idxmax()]}")
    assert len(merged) == 154


def test_the_registry_agrees_with_the_denomination_the_custodian_wrote(merged):
    """``TITLE_FACE`` is market convention, so it is corroborated against the data: every
    title-quoted holding carries its own denomination token in the long description."""
    titled = merged[merged["price_quotation"].str.startswith("titles-of-")]
    assert len(titled) == 6
    for r in titled.itertuples():
        face = int(TITLE_FACE[r.currency])
        token = f"{r.currency}{face}"
        assert token in str(r.desc_long).upper(), (
            f"{r.asset_id}: registry says {token} but the description does not say so")


def test_only_the_brazilian_price_is_actually_rescaled(merged):
    # MXN titles are 100, so the price passes through untouched; only the BRL per-1000 quote
    # moves. Stating it here stops a future "simplification" from scaling all six.
    titled = merged[merged["price_quotation"].str.startswith("titles-of-")]
    mxn = titled[titled["currency"] == "MXN"]
    assert (mxn["bt_per_100"] == mxn["gold_price"]).all()
    brl = titled[titled["currency"] == "BRL"].iloc[0]
    assert brl["gold_price"] == pytest.approx(916.73)
    assert brl["bt_per_100"] == pytest.approx(91.673)


def test_the_three_original_classes_all_read_as_currency_face():
    """The quotation resolution was made universal. It is inert for the agency / guaranteed /
    linker classes by EVIDENCE, not by assumption -- which is why their CSV is unchanged."""
    if URS is None:
        pytest.skip("URS workbook not found")
    bonds, _, _ = build_phase2_from_path(str(URS))
    assert set(bonds["price_quotation"]) == {"currency-face"}


# --------------------------------------------------------------- the anchor property
def _price(row, curve):
    return implied_oas(float(row["bt_per_100"]), VAL, row["maturity"], float(row["coupon"]),
                       curve, freq=int(row["freq"]) if pd.notna(row["freq"]) else 2) * 1e4


@pytest.mark.parametrize("ccy,limit", [("GBP", 25.0), ("JPY", 25.0), ("MXN", 60.0)])
def test_a_sovereign_on_its_own_government_curve_reprices_to_about_zero(merged, ccy, limit):
    """The end-to-end invariant. A gilt discounted on the gilt curve, a JGB on the JGB curve
    and a Bono on the Mexican curve are the same credit as the curve itself, so the calibrated
    spread is a validation anchor near zero -- not a credit signal. This fails on a wrong
    curve, on a par-yield file read in the wrong units, and on a mis-scaled price."""
    curve = ZeroCurve.from_currency(DATA, ccy, VAL, freq="Semiannual")
    sel = merged[(merged["currency"] == ccy) & (merged["route"] == "vanilla")
                 & merged["maturity"].notna()]
    spreads = [_price(r, curve) for _, r in sel.iterrows()
               if (pd.Timestamp(r["maturity"]) - pd.Timestamp(VAL)).days > 365]
    assert len(spreads) >= 5
    assert abs(pd.Series(spreads).median()) < limit, sorted(round(s, 1) for s in spreads)


def test_using_the_unconverted_brazilian_price_would_be_obviously_wrong(merged):
    """Proof that the per-1000 conversion is load-bearing rather than cosmetic: the raw quote
    produces a spread no sovereign has ever traded at, so the rescale cannot be dropped."""
    brl = merged[merged["currency"] == "BRL"].iloc[0]
    curve = ZeroCurve.from_currency(DATA, "BRL", VAL, freq="Semiannual")
    converted = _price(brl, curve)
    assert abs(converted) < 200.0, converted
    raw = implied_oas(float(brl["gold_price"]), VAL, brl["maturity"], float(brl["coupon"]),
                      curve, freq=2) * 1e4
    assert raw < -1000.0, raw
