"""Structure locks for the government asset layer (restructure of 2026-09-10).

Flat stub curve throughout — no workbook needed, never skipped, in the style of
``test_ilb.py``. These tests pin the things a later refactor could break QUIETLY: the
shim's object identity, the wrapper's bit-exact agreement with the engine, the one
function name that must never become OAS-shaped, the independence of the two input
dictionaries, and the thresholds that are stated in two places on purpose.

⚠️ Deliberately not reading ``outputs/`` — it is git-ignored and can be stale, the same
rule ``test_callable_disposition.py`` states. Where a driver constant has to be kept in
step, the test reads the DRIVER SOURCE instead.
"""
import math
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class FlatCurve:
    def __init__(self, z=0.04):
        self.z = z

    def zero_rate(self, t, spread=0.0):
        return self.z + spread


VAL = "2009-03-31"


# --------------------------------------------------------------------------------------
# 1. The shim. The engine moved; every old import path must reach the SAME object.
# --------------------------------------------------------------------------------------
def test_the_ilb_shim_re_exports_the_identical_objects():
    """Object identity, not importability.

    A shim that accidentally re-implements instead of re-exporting passes every
    import-by-name test while production quietly runs a second copy that can drift. The
    frn and lattice shims are pinned the same way.
    """
    import pricing.ilb as shim
    from pricer.core.pricing import inflation as core

    for name in ("price_ilb", "implied_spread_ilb", "ilb_risk_metrics", "IlbResult",
                 "YEAR_DAYS", "_as_date"):
        assert getattr(shim, name) is getattr(core, name), name


def test_the_inflation_engine_does_not_import_from_the_legacy_package():
    """A core module reaching up into ``pricing.*`` looks migrated and is not.

    This is the layering violation already closed once in ``core/pricing/cashflows.py``,
    which imported ``coupon_at`` from the legacy package.
    """
    src = (ROOT / "src" / "pricer" / "core" / "pricing" / "inflation.py").read_text(encoding="utf-8")
    offenders = re.findall(r"^\s*(?:from|import)\s+pricing\b.*$", src, re.M)
    assert offenders == [], offenders


# --------------------------------------------------------------------------------------
# 2. The wrapper. Legacy units in, identical numbers out.
# --------------------------------------------------------------------------------------
def test_the_linker_wrapper_reprices_bit_exactly():
    """The asset layer converts units and delegates; it must add no arithmetic of its own."""
    from pricer.assets.government import linker
    from pricer.core.pricing import inflation as core

    c = FlatCurve(0.035)
    got = linker.calculated_price(3.875, 2, "2029-04-15", VAL, c, -95.48,
                                  index_ratio=1.284379, inflation_pct=0.0)
    want = core.price_ilb(VAL, "2029-04-15", 0.03875, c, -95.48e-4,
                          index_ratio=1.284379, inflation=0.0, face=100.0, freq=2).clean
    assert got == want


def test_the_linker_wrapper_converts_percent_and_basis_points():
    """A unit slip here would be invisible: every number still computes, just wrongly."""
    from pricer.assets.government import linker
    from pricer.core.pricing import inflation as core

    c = FlatCurve(0.03)
    # 2% inflation at this layer means 0.02 to the engine.
    got = linker.calculated_price(2.0, 2, "2019-01-15", VAL, c, 20.0,
                                  index_ratio=1.1, inflation_pct=2.0)
    want = core.price_ilb(VAL, "2019-01-15", 0.02, c, 0.0020,
                          index_ratio=1.1, inflation=0.02, face=100.0, freq=2).clean
    assert got == want


def test_linker_accrued_is_scaled_by_the_ratio_at_valuation():
    """The seller has earned the inflation that HAS happened, not the period's end ratio."""
    from pricer.assets.government import linker

    c = FlatCurve(0.03)
    kw = dict(index_ratio=1.0, inflation_pct=0.0)
    base = linker.accrued_interest(4.0, 2, "2020-01-15", VAL, c, **kw)
    scaled = linker.accrued_interest(4.0, 2, "2020-01-15", VAL, c,
                                     index_ratio=2.0, inflation_pct=0.0)
    assert scaled == pytest.approx(2.0 * base, rel=1e-12)


# --------------------------------------------------------------------------------------
# 3. The breakeven identity — the reason this class gets its own column name.
# --------------------------------------------------------------------------------------
def test_breakeven_is_minus_the_spread_at_zero_inflation():
    """The form ``scripts/phase2_risk.py`` publishes: ``breakeven_bp = -spread``."""
    from pricer.assets.government import linker

    c = FlatCurve(0.04)
    kw = dict(index_ratio=1.2, inflation_pct=0.0)
    target = linker.calculated_price(2.5, 2, "2027-01-15", VAL, c, -120.0, **kw)
    spread = linker.implied_spread_vs_nominal_bp(2.5, 2, "2027-01-15", VAL, target, c, **kw)
    be = linker.breakeven_bp(2.5, 2, "2027-01-15", VAL, target, c, **kw)
    assert be == pytest.approx(-spread, abs=1e-9)
    assert spread < 0 < be, "a healthy linker calibrates NEGATIVE; the breakeven is positive"


def test_breakeven_holds_at_a_non_zero_inflation_assumption():
    """``breakeven = ln(1+pi) - spread`` — exact under exponential discounting.

    The driver only publishes the zero-inflation form; the wrapper is the general
    statement, and this is the check that generalising it did not invent anything.
    """
    from pricer.assets.government import linker

    c = FlatCurve(0.04)
    pi_pct = 2.5
    price = linker.calculated_price(2.5, 2, "2027-01-15", VAL, c, -120.0,
                                    index_ratio=1.2, inflation_pct=0.0)
    kw = dict(index_ratio=1.2, inflation_pct=pi_pct)
    spread = linker.implied_spread_vs_nominal_bp(2.5, 2, "2027-01-15", VAL, price, c, **kw)
    be = linker.breakeven_bp(2.5, 2, "2027-01-15", VAL, price, c, **kw)
    assert be == pytest.approx(math.log1p(pi_pct / 100.0) * 1e4 - spread, abs=1e-9)

    # And it is the SAME market breakeven however the projection was set up.
    be0 = linker.breakeven_bp(2.5, 2, "2027-01-15", VAL, price, c,
                              index_ratio=1.2, inflation_pct=0.0)
    assert be == pytest.approx(be0, abs=1e-4)


def test_the_linker_wrapper_never_exposes_an_oas_shaped_name():
    """⚠️ The one naming lock in this package.

    A linker's calibrated spread is approximately MINUS a breakeven inflation rate, not a
    credit spread. A government function called ``implied_oas`` would invite exactly the
    mix-up the separate output column exists to prevent — so the name is banned from this
    module, not merely discouraged in prose.
    """
    src = (ROOT / "src" / "pricer" / "assets" / "government" / "linker.py").read_text(encoding="utf-8")
    code = "\n".join(line for line in src.splitlines() if not line.lstrip().startswith("#"))
    # Strip docstrings: the word is legitimate there, where it is being ruled OUT.
    code = re.sub(r'""".*?"""', "", code, flags=re.S)
    assert "implied_oas" not in code

    from pricer.assets.government import linker
    assert not hasattr(linker, "implied_oas")
    assert hasattr(linker, "implied_spread_vs_nominal_bp")


# --------------------------------------------------------------------------------------
# 4. Two input dictionaries, neither renumbering the other.
# --------------------------------------------------------------------------------------
def test_the_government_catalogue_numbers_itself_independently():
    """Government input 9 and corporate input 9 are DIFFERENT fields, on purpose.

    The legacy sheet keeps one input dictionary per asset family. A reader who
    cross-references "input 9" against the wrong family reads the wrong description and
    gets no warning at all.
    """
    from pricer.assets.corporate.bonds_input import INPUT_CATALOGUE as CORP
    from pricer.assets.government.bonds_input import INPUT_CATALOGUE as GOVT

    assert [r["n"] for r in GOVT] == list(range(1, len(GOVT) + 1))
    by_n_govt = {r["n"]: r["field"] for r in GOVT}
    by_n_corp = {r["n"]: r["field"] for r in CORP}
    assert by_n_govt[9] == "spread_vs_nominal_bp"
    assert by_n_corp[9] == "bp_adjust"
    assert by_n_govt[1] == "real_coupon" and by_n_corp[1] == "coupon"


def test_a_linkers_real_coupon_is_a_separate_input_from_a_nominal_coupon():
    """Conflating them is a modelling error no unit check would catch."""
    from pricer.assets.government.bonds_input import INPUT_CATALOGUE

    fields = {r["field"]: r for r in INPUT_CATALOGUE}
    assert "real_coupon" in fields and "coupon" in fields
    assert fields["real_coupon"]["used"] == "linker"
    assert "agency" in fields["coupon"]["used"]


def test_no_government_input_is_reachable_from_a_worksheet():
    """Encodes the 2026-09-10 decision: no ILB endpoint type this round.

    The Excel bridge has no cells for a real coupon, an index ratio or an inflation
    assumption, and the project's 7/5/5 rule keeps an instrument type off a sheet whose
    layout Mario has not chosen. When that changes, this test changes WITH the contract —
    which is the point of pinning it.
    """
    from pricer.assets.government.bonds_input import INPUT_CATALOGUE
    assert {r["external"] for r in INPUT_CATALOGUE} == {"-"}

    from pricer.endpoints import contracts
    assert not any("linked" in t or "ilb" in t or "inflation" in t
                   for t in contracts.INSTRUMENT_TYPES)
    assert len(contracts.INSTRUMENT_TYPES) == 7


def test_describe_inputs_renders_every_row():
    from pricer.assets.government.bonds_input import INPUT_CATALOGUE, describe_inputs
    text = describe_inputs()
    assert len(text.splitlines()) == len(INPUT_CATALOGUE) + 1
    for row in INPUT_CATALOGUE:
        assert row["field"] in text


# --------------------------------------------------------------------------------------
# 5. Validators refuse the contract violations, and only those.
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("kwargs", [
    dict(real_coupon=-1.0, cpn_freq=2, index_ratio=1.0, inflation_pct=0.0),
    dict(real_coupon=0.03875, cpn_freq=3, index_ratio=1.0, inflation_pct=0.0),
    dict(real_coupon=387.5, cpn_freq=2, index_ratio=1.0, inflation_pct=0.0),
    dict(real_coupon=3.875, cpn_freq=2, index_ratio=0.0, inflation_pct=0.0),
    dict(real_coupon=3.875, cpn_freq=2, index_ratio=1.0, inflation_pct=200.0),
])
def test_linker_validator_refuses_out_of_contract_inputs(kwargs):
    from pricer.assets.government.bonds_input import validate_linker_inputs
    with pytest.raises(ValueError):
        validate_linker_inputs(**kwargs)


def test_linker_validator_allows_a_ratio_outside_the_loader_plausibility_window():
    """⚠️ The wrapper validates the CONTRACT; the loader validates the DATA.

    ``dataio.phase2.RATIO_SANITY`` is the plausibility window for a ratio RECOVERED from
    the custodian file. Enforcing it here too would put two modules in charge of one
    decision and would refuse a legitimate synthetic or stress value.
    """
    from dataio.phase2 import RATIO_SANITY
    from pricer.assets.government.bonds_input import validate_linker_inputs

    assert RATIO_SANITY == (0.9, 1.6)
    validate_linker_inputs(3.875, 2, RATIO_SANITY[1] + 1.0, 0.0)   # must not raise


@pytest.mark.parametrize("kwargs", [
    dict(coupon=-1.0, cpn_freq=2),
    dict(coupon=5.25, cpn_freq=3),
    dict(coupon=0.0525, cpn_freq=2, volatility=0.0),
    dict(coupon=5.25, cpn_freq=2, volatility=15.0),
])
def test_agency_validator_refuses_out_of_contract_inputs(kwargs):
    from pricer.assets.government.bonds_input import validate_agency_inputs
    with pytest.raises(ValueError):
        validate_agency_inputs(**kwargs)


# --------------------------------------------------------------------------------------
# 6. The agency verdict rule — named here, applied inline by the driver.
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize("callable_bp,straight_bp,expected", [
    (-15.0, 120.0, "lie-detector"),
    (620.0, 400.0, "extension-priced"),
    (121.0, 121.5, "call-not-binding"),
    (121.0, 160.0, "call-active"),
])
def test_option_verdict_reads_the_two_spreads(callable_bp, straight_bp, expected):
    from pricer.assets.government.agency import option_verdict
    assert option_verdict(callable_bp, straight_bp) == expected


def test_the_verdict_thresholds_match_the_ones_the_driver_applies():
    """⚠️ The rule is stated in two places ON PURPOSE, so this pins them together.

    ``scripts/phase2_risk.py`` applies these thresholds inline to build its flag text, and
    this round deliberately does not touch that code — the driver's output must stay
    byte-identical. The cost of that choice is that the numbers live twice, so a test
    reads the driver source and fails if they ever diverge. Same pattern as the Excel
    bridge field-set check.
    """
    from pricer.assets.government import agency

    src = (ROOT / "scripts" / "phase2_risk.py").read_text(encoding="utf-8")
    block = src[src.index("if route == \"callable-lattice\":"):]

    def literal(pattern):
        """The numeric literal the driver actually compares against, as a float."""
        m = re.search(pattern, block)
        assert m, f"the driver no longer contains {pattern!r} — the rule moved or changed"
        return float(m.group(1))

    # Each driver threshold is a DECIMAL spread; the constants here are in basis points.
    assert literal(r"oas_cal - oas_str > ([0-9.e-]+)") * 1e4 == agency.EXTENSION_PRICING_GAP_BP
    assert literal(r"abs\(oas_cal - oas_str\) < ([0-9.e-]+)") * 1e4 == agency.CALL_NOT_BINDING_GAP_BP
    assert literal(r"if oas_cal < ([0-9.e-]+):") * 1e4 == agency.LIE_DETECTOR_BP


def test_volatility_applies_only_to_the_callable_route():
    from pricer.assets.government.agency import volatility_applies
    assert volatility_applies("callable-lattice")
    for route in ("vanilla", "call-passed-vanilla", "zero", "cmo-tranche"):
        assert not volatility_applies(route)


# --------------------------------------------------------------------------------------
# 7. The guaranteed bucket rule.
# --------------------------------------------------------------------------------------
def test_a_guaranteed_bond_never_reports_in_a_bank_bucket():
    """The credit is the FDIC guarantee, not the issuing bank's."""
    from pricer.assets.government.guaranteed import TLGP_BUCKET, reporting_bucket
    assert reporting_bucket() == TLGP_BUCKET
    for bank_bucket in ("AAA", "AA", "A", "BBB", "BB", "B", "CCC"):
        assert reporting_bucket(bank_bucket) == TLGP_BUCKET


def test_the_loader_applies_the_same_guaranteed_bucket():
    """One rule, one production owner — the wrapper states it, the loader applies it."""
    from pricer.assets.government.guaranteed import TLGP_BUCKET
    src = (ROOT / "src" / "dataio" / "phase2.py").read_text(encoding="utf-8")
    assert f'u["group"] = "{TLGP_BUCKET}"' in src


# --------------------------------------------------------------------------------------
# 8. The package does not route, and says where routing lives.
# --------------------------------------------------------------------------------------
def test_no_government_wrapper_re_implements_a_routing_rule():
    """Routing has exactly one owner: ``dataio.phase2``.

    A wrapper that re-derived "is this a zero?" or "has the call passed?" would be the
    two-files-owning-half-a-decision defect wearing a new hat.
    """
    pkg = ROOT / "src" / "pricer" / "assets" / "government"
    banned = ("ZERO_COUPON_MAX_PCT =", "MAKE_WHOLE_MAX_GAP_DAYS =", "_DATE_PAIR =",
              "_CMO_CLASS =", "RATIO_SANITY =", "TITLE_FACE =")
    for path in pkg.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{path.name} re-defines {token.strip(' =')}"


def test_the_government_side_reaches_the_shared_option_surface():
    """Decision of 2026-09-10: a government-side import path, not a relocated module.

    One lattice prices every bond with an embedded option in this book. The sovereign
    driver was importing it from a module named *corporate* to price a US Treasury;
    government code now has its own path to the same objects.
    """
    from pricer.assets.corporate import embedded_option as shared
    from pricer.assets.government import agency, sovereign

    assert sovereign.check_representable is shared.check_representable
    assert sovereign.ExerciseScheduleNotRepresentable is shared.ExerciseScheduleNotRepresentable
    assert sovereign.callable_implied_oas is shared.implied_oas
    assert agency.implied_oas is shared.implied_oas
    assert agency.SIGMA_DEFAULT == 0.15
