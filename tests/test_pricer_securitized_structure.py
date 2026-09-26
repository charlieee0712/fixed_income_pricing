"""Structure locks for the securitised layer (migrated 2026-09-25).

``pricing/mbs.py`` was the last engine outside the template. The move is only safe if three
things are true and stay true: the shim hands back the SAME objects rather than a
re-implementation, the engine body was spliced rather than retyped, and the wrapper's
percent/basis-point boundary converts exactly to the core's decimals.

The wrappers themselves carry no arithmetic, so most of what is worth locking is the boundary
and the refusals — including the two unit errors this project has already made at data
boundaries (``PAR_YIELD_UNITS``, ``TITLE_FACE``), both caught late and both preventable by a
validator that knows a mortgage coupon is never 0.065.
"""
import hashlib
import math
import pathlib

import pytest

from pricer.assets.securitized import bonds_input, pool
from pricer.core.pricing import prepayment

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"


class FlatCurve:
    """The minimum a pool needs: a continuously-compounded zero rate at any tenor."""

    def __init__(self, z):
        self.z = z

    def zero_rate(self, t):
        return self.z


# --------------------------------------------------------------------------- the move itself

def test_the_mbs_shim_re_exports_the_identical_objects():
    """Importability is not enough.

    A shim that re-implemented the engine would satisfy every import-by-name check and then
    drift silently against the module it claims to forward to. Identity is the only assertion
    that cannot be satisfied by a copy.
    """
    import pricing.mbs as shim

    assert shim.__all__, "the shim must declare its contract"
    for name in shim.__all__:
        assert getattr(shim, name) is getattr(prepayment, name), \
            f"{name} in the shim is NOT the same object as in core.pricing.prepayment"


def test_the_engine_body_was_spliced_not_retyped():
    """The body below the docstring is byte-for-byte the file written 2026-07-22.

    Retyping an engine during a move is how a number changes without anybody deciding to
    change it. The docstring was rewritten on purpose; everything below it was not touched.
    """
    text = (SRC / "pricer/core/pricing/prepayment.py").read_text(encoding="utf-8")
    body = text.split('"""', 2)[2]
    assert hashlib.sha256(body.encode()).hexdigest()[:16] == "45a0ef7d5d98d893", (
        "the prepayment engine body changed. If that was deliberate, re-measure the hash and "
        "say in the commit which number moved and why.")


def test_the_prepayment_engine_does_not_import_from_the_legacy_package():
    """core/ must never reach up into pricing/ — the layering violation closed in Round 2b."""
    text = (SRC / "pricer/core/pricing/prepayment.py").read_text(encoding="utf-8")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")):
            assert not stripped.startswith(("from pricing", "import pricing")), \
                f"core reaches up into the legacy package: {stripped}"


# --------------------------------------------------------------------------- the unit boundary

def test_the_pool_wrapper_reprices_bit_exactly():
    """The wrapper adds no arithmetic: percent in, decimals down, the same float back."""
    curve = FlatCurve(0.04)
    wrapped = pool.calculated_price(6.5, 240, 8.0, curve, spread=50.0, net_coupon=6.0)
    direct = prepayment.price_pool(curve, 0.065, 240, 0.08, 0.0050, net_coupon=0.060)
    assert wrapped == direct


def test_the_pool_wrapper_converts_percent_and_basis_points():
    """A spread given in bp must mean bp, and a CPR in percent must mean percent."""
    curve = FlatCurve(0.04)
    assert pool.calculated_price(6.5, 240, 8.0, curve, spread=100.0) == \
        prepayment.price_pool(curve, 0.065, 240, 0.08, 0.01)
    # and the two knobs are not interchangeable: 100 bp of spread is not 100% of CPR
    assert pool.calculated_price(6.5, 240, 8.0, curve, spread=100.0) != \
        pool.calculated_price(6.5, 240, 100.0 - 1e-9, curve, spread=0.0)


def test_widening_and_tightening_are_symmetric_about_the_spread():
    curve = FlatCurve(0.04)
    base = pool.calculated_price(6.5, 240, 8.0, curve, spread=120.0)
    wide = pool.widening(6.5, 240, 8.0, curve, 120.0, bp_adjust=25.0)
    tight = pool.tightening(6.5, 240, 8.0, curve, 120.0, bp_adjust=25.0)
    assert wide < base < tight
    assert wide == pool.calculated_price(6.5, 240, 8.0, curve, spread=145.0)
    assert tight == pool.calculated_price(6.5, 240, 8.0, curve, spread=95.0)


# --------------------------------------------------------------------------- the calibrations

def test_implied_cpr_round_trips():
    """The adopted branch: spread held fixed, the price gives back the CPR."""
    curve = FlatCurve(0.04)
    price = pool.calculated_price(6.5, 240, 12.0, curve, spread=0.0)
    assert pool.implied_cpr_pct(6.5, 240, price, curve, spread=0.0) == pytest.approx(12.0, abs=1e-6)


def test_implied_spread_round_trips():
    """The other branch, kept for the day a 2009-dated CPR arrives."""
    curve = FlatCurve(0.04)
    price = pool.calculated_price(6.5, 240, 8.0, curve, spread=75.0)
    assert pool.implied_spread_bp(6.5, 240, 8.0, price, curve) == pytest.approx(75.0, abs=1e-4)


def test_a_par_priced_pool_has_no_identifiable_cpr():
    """Price is flat in CPR at par, so every CPR fits, and the wrapper refuses.

    Note what this is NOT testing. The core solver, handed that same target, returns 0.0 via
    its exact-hit shortcut -- a confident "no prepayment" about a pool on which no statement
    is possible. The guard lives in the wrapper because the engine body is the 2026-07-22 file
    spliced unchanged; the assertion below pins both halves of that arrangement.
    """
    # The degenerate point is the CONTINUOUS rate equivalent to a monthly wac/12, not a flat
    # 6.5%: those differ by 17 bp and the naive version is not degenerate at all (its price
    # still moves 1.3e-01 across the CPR range). test_mbs.py line 59 uses the same conversion.
    curve = FlatCurve(12.0 * math.log(1.0 + 0.065 / 12.0))
    par = pool.calculated_price(6.5, 240, 0.0, curve, spread=0.0)
    assert par == pytest.approx(100.0, abs=1e-9), "the construction must actually be at par"

    assert prepayment.implied_cpr_pool(par, curve, 0.065, 240, spread=0.0) == 0.0, (
        "the core's shortcut behaviour changed; the wrapper guard was written against it")

    with pytest.raises(ValueError, match="not identifiable"):
        pool.implied_cpr_pct(6.5, 240, par, curve, spread=0.0)


def test_the_identifiability_guard_lets_a_real_calibration_through():
    """The guard must not be so eager that it refuses pools that do carry information.

    A single threshold that silences the degenerate case AND a working one would be the
    "one tolerance, two populations" failure this project has already hit twice.
    """
    curve = FlatCurve(0.04)                  # well away from the 6.5% coupon: a premium pool
    price = pool.calculated_price(6.5, 240, 12.0, curve, spread=0.0)
    assert pool.implied_cpr_pct(6.5, 240, price, curve, spread=0.0) == pytest.approx(12.0, abs=1e-6)


# --------------------------------------------------------------------------- pool behaviour

def test_weighted_average_life_shortens_as_prepayment_rises():
    assert (pool.weighted_average_life(6.5, 240, 0.0)
            > pool.weighted_average_life(6.5, 240, 8.0)
            > pool.weighted_average_life(6.5, 240, 25.0))


def test_weighted_average_life_ignores_the_curve_it_accepts():
    """WAL is a property of the cash flows. The parameter exists for signature symmetry and
    must not be able to influence the answer."""
    assert pool.weighted_average_life(6.5, 240, 8.0, curve=FlatCurve(0.01)) == \
        pool.weighted_average_life(6.5, 240, 8.0, curve=FlatCurve(0.40))


def test_convexity_of_the_static_flows_is_positive():
    """Documented, not celebrated: the market's mortgage convexity is NEGATIVE, and the gap is
    the entire prepayment option this v1 model does not have."""
    assert pool.convexity(6.5, 240, 8.0, FlatCurve(0.04), spread=100.0) > 0


# --------------------------------------------------------------------------- the refusals

@pytest.mark.parametrize("kwargs, match", [
    ({"wac": 0.065, "wam_months": 240}, "looks like a decimal"),
    ({"wac": -1.0, "wam_months": 240}, "non-negative"),
    ({"wac": 6.5, "wam_months": 0}, "positive number of months"),
    ({"wac": 6.5, "wam_months": 240, "cpr": 100.0}, "PERCENT in"),
    ({"wac": 6.5, "wam_months": 240, "cpr": -1.0}, "PERCENT in"),
    ({"wac": 6.5, "wam_months": 240, "net_coupon": 7.0}, "exceeds the gross"),
])
def test_pool_validator_refuses_out_of_contract_inputs(kwargs, match):
    with pytest.raises(ValueError, match=match):
        bonds_input.validate_pool_inputs(**kwargs)


def test_the_validator_catches_a_decimal_wac_before_it_prices():
    """The units error this project made twice at data boundaries, refused at the third.

    0.065 is a perfectly valid float and prices without complaint in the core, producing a
    near-zero-coupon pool and a plausible-looking number. Only the asset layer knows the
    intended units, so only the asset layer can catch it.
    """
    with pytest.raises(ValueError, match="looks like a decimal"):
        pool.calculated_price(0.065, 240, 8.0, FlatCurve(0.04))


# --------------------------------------------------------------------------- the catalogue

def test_the_pool_catalogue_numbers_itself_independently():
    """Three asset families, three dictionaries, none renumbering another."""
    from pricer.assets.corporate import bonds_input as corp
    from pricer.assets.government import bonds_input as govt

    ours = {r["n"]: r["field"] for r in bonds_input.INPUT_CATALOGUE}
    assert sorted(ours) == list(range(1, len(ours) + 1)), "numbering must be 1..N with no gaps"
    assert ours[3] == "cpr"
    assert {r["n"]: r["field"] for r in govt.INPUT_CATALOGUE}[3] != "cpr"
    assert {r["n"]: r["field"] for r in corp.INPUT_CATALOGUE}[3] != "cpr"


def test_no_pool_input_is_reachable_from_a_worksheet():
    """The 7/5/5 rule: no instrument type reaches a sheet whose layout Mario has not chosen."""
    for row in bonds_input.INPUT_CATALOGUE:
        assert row["external"] == "-", \
            f"input {row['n']} ({row['field']}) claims an external name; the contract has none"


def test_the_catalogue_says_which_inputs_drive_nothing():
    """wala and aols are carried, not used. Silence would leave a reader to infer it."""
    carried = {r["field"] for r in bonds_input.INPUT_CATALOGUE if r["used"] == "none (carried)"}
    assert carried == {"wala", "aols"}


def test_describe_inputs_renders_every_row():
    rendered = bonds_input.describe_inputs()
    assert len(rendered.splitlines()) == len(bonds_input.INPUT_CATALOGUE) + 1
    for row in bonds_input.INPUT_CATALOGUE:
        assert row["field"] in rendered


# --------------------------------------------------------------------------- no second owner

def test_no_securitized_wrapper_re_implements_a_routing_rule():
    """Routing has one owner. The same lock the government package carries, for the same
    reason: 'two files owning half a decision' has been closed five times in this project."""
    for path in (SRC / "pricer/assets/securitized").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or '"' in stripped or "'" in stripped:
                continue
            assert not any(tok in stripped for tok in ("_MAX_PCT", "_GAP_BP", "_GAP_DAYS",
                                                       "LIE_DETECTOR", "ROUTE = ")), \
                f"{path.name} defines a routing constant: {stripped}"
