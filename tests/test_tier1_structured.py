"""Locks for the Tier-1 structured driver and its assets-layer wrapper.

Each of these corresponds to something that went wrong, or could have, in building it:

* the **banned name** — the client's own slide 13 reserves "OAS" for a model whose cash flows
  respond to rates, so a column called ``implied_oas`` here would contradict the deck;
* the **I/O refusal** living in the assets layer rather than in the driver, so that any caller
  gets it and not just this one;
* the **units boundary** the assets layer owns — reaching past it into the core produced a
  calibrated spread of 46,478 bp on 487 pools;
* the **cover**, asserted against the driver that already prices the same pools, because a
  superset turned out to be a bug and not a win: 2 TBA forwards were being priced as spot
  pools with their settlement adjustment silently missing;
* the **inert classification discrepancy** on two ``CL PO`` tranches, pinned so it cannot
  start to matter unnoticed.
"""
import csv
import pathlib

import pytest

from pricer.assets.securitized import observed as obs

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "tier1_structured_2009-03-31.csv"
DISPO = ROOT / "outputs" / "tier1_structured_disposition_2009-03-31.csv"
SRC = ROOT / "src"
DRIVER = ROOT / "scripts" / "tier1_structured.py"


class FlatCurve:
    @staticmethod
    def zero_rate(_t):
        return 0.04


def _rows(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------- the banned name

BANNED = ("implied_oas", "oas_bp", "option_adjusted")


def test_the_output_never_calls_this_an_OAS():
    """⚠️ Mario's own slide 13: *"a true OAS requires explicit modeling of option-dependent
    cash flows such as prepayments."* These cash flows are fixed, so the column is an
    implied, bond-equivalent spread and must not borrow the other name."""
    if not OUT.exists():
        pytest.skip("driver output not present")
    cols = _rows(OUT)[0].keys()
    for bad in BANNED:
        assert not any(bad in c.lower() for c in cols), (
            f"column named {bad!r} in the Tier-1 output: these cash flows do not respond to "
            "rates, so the number is not an OAS")


def test_the_banned_name_lock_is_not_decorative():
    """Mutation: a column list that DOES contain the banned name must fail the same check."""
    mutated = ["asset_id", "implied_oas_bp", "wal_years"]
    assert any(b in c.lower() for c in mutated for b in BANNED), (
        "the check cannot detect the name it exists to forbid")


def test_neither_the_driver_nor_the_wrapper_emits_the_banned_name():
    for path in (DRIVER, SRC / "pricer/assets/securitized/observed.py"):
        text = path.read_text(encoding="utf-8")
        body = "\n".join(ln for ln in text.splitlines()
                         if not ln.lstrip().startswith("#") and '"""' not in ln)
        assert "implied_oas" not in body, f"{path.name} names implied_oas outside prose"


# --------------------------------------------------------------- the I/O refusal

def test_the_assets_layer_refuses_an_interest_only_risk_number():
    """⭐ The refusal lives here, not in a driver — a modelling choice left to "the caller"
    is a choice nobody makes the same way twice."""
    path = [1.0, 0.8, 0.6, 0.4, 0.2, 0.05]
    for fn, args in ((obs.implied_spread_bp, (path, 6.0, obs.INTEREST_ONLY, 8.0, FlatCurve())),
                     (obs.duration, (path, 6.0, obs.INTEREST_ONLY, FlatCurve(), 100.0)),
                     (obs.dv01, (path, 6.0, obs.INTEREST_ONLY, FlatCurve(), 100.0)),
                     (obs.convexity, (path, 6.0, obs.INTEREST_ONLY, FlatCurve(), 100.0))):
        with pytest.raises(obs.UnpublishableRiskMetric):
            fn(*args)


def test_the_refusal_is_not_a_ValueError():
    """⚠️ The spread solvers catch ``ValueError``. A refusal swallowed by a solver comes back
    as "no spread reprices this security", which is a different and false statement."""
    assert not issubclass(obs.UnpublishableRiskMetric, ValueError)
    from pricer.errors import PricingDomainError
    assert issubclass(obs.UnpublishableRiskMetric, PricingDomainError)


def test_timing_measures_are_still_available_for_an_interest_only_strip():
    """What is refused is the RISK number, not every number: an I/O keeps its cash-flow life
    and its tail report, and its principal-weighted WAL is NaN because it has no principal."""
    import math
    path = [1.0, 0.8, 0.6, 0.4, 0.2, 0.05]
    assert math.isnan(obs.weighted_average_life(path, 6.0, obs.INTEREST_ONLY))
    assert obs.cash_flow_life(path, 6.0, obs.INTEREST_ONLY) > 0
    assert obs.tail_report(path, 6.0, obs.INTEREST_ONLY)["treatment"] in (
        "amortised", "repaid_as_requested", "repaid_tail_would_overrun",
        "repaid_tail_not_decaying", "repaid_below_floor", "none")


def test_amortising_and_principal_only_are_publishable():
    path = [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
    assert obs.risk_is_publishable(obs.AMORTISING)
    assert obs.risk_is_publishable(obs.PRINCIPAL_ONLY)
    assert not obs.risk_is_publishable(obs.INTEREST_ONLY)
    assert obs.duration(path, 6.0, obs.AMORTISING, FlatCurve(), 100.0) > 0


# --------------------------------------------------------------- the units boundary

def test_the_wrapper_speaks_percent_and_basis_points():
    """⭐ The boundary this layer exists for. A 6% coupon passed as 6.0 must behave like 6%,
    not 600% — the error that produced a 46,478 bp spread when the core was called directly."""
    path = [1.0, 0.9, 0.8, 0.7, 0.6, 0.0]
    at_zero = obs.calculated_price(path, 6.0, obs.AMORTISING, FlatCurve(), 0.0)
    assert 90 < at_zero < 115, f"a 6% amortiser near par should price near par, got {at_zero}"
    # a 100bp spread must cost a modest amount, not a catastrophic one
    at_100bp = obs.calculated_price(path, 6.0, obs.AMORTISING, FlatCurve(), 100.0)
    assert 0 < at_zero - at_100bp < 5, "100 bp should cost single digits on a ~2y amortiser"


def test_the_driver_does_not_import_the_core_engines_directly():
    """⚠️ The percent/decimal boundary is the assets layer's job. The driver reached past it
    once and shipped a 465% spread; this is the lock that stops the next time."""
    text = DRIVER.read_text(encoding="utf-8")
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    for banned in ("from pricer.core.pricing import observed_paydown",
                   "from pricer.core.pricing import prepayment"):
        assert banned not in code, f"{banned!r}: go through pricer.assets.securitized instead"


# --------------------------------------------------------------- the cover

@pytest.mark.skipif(not OUT.exists() or not DISPO.exists(), reason="driver output not present")
def test_every_security_has_exactly_one_disposition():
    rows, dispo = _rows(OUT), _rows(DISPO)
    assert len(rows) == len(dispo) == 882, f"{len(rows)} output rows, {len(dispo)} dispositions"
    assert {r["asset_id"] for r in rows} == {d["asset_id"] for d in dispo}
    priced = {d["asset_id"] for d in dispo if d["status"] == "priced"}
    with_numbers = {r["asset_id"] for r in rows if r["paydown_source"]}
    assert priced == with_numbers, "the disposition and the output disagree about who is priced"


@pytest.mark.skipif(not OUT.exists(), reason="driver output not present")
def test_the_assumed_cover_is_not_a_superset_of_the_driver_that_already_prices_these():
    """⚠️ The check that caught a real defect. Pricing 2 securities ``pool_risk`` had
    deliberately skipped was not extra coverage — they were TBA forwards being priced as spot
    pools with the settlement adjustment silently missing."""
    pool_out = ROOT / "outputs" / "pool_risk_2009-03-31.csv"
    if not pool_out.exists():
        pytest.skip("pool_risk output not present")
    rows = _rows(OUT)
    assumed = {r["asset_id"] for r in rows if r["paydown_source"] == "assumed-cpr"}
    already = {r["asset_id"] for r in _rows(pool_out)}
    extra = assumed - already
    assert not extra, (
        f"{len(extra)} securities priced on an assumed speed here that pool_risk.py skipped: "
        f"{sorted(extra)[:5]} — it skipped them for a reason")


@pytest.mark.skipif(not OUT.exists(), reason="driver output not present")
def test_interest_only_rows_carry_a_price_and_no_risk_numbers():
    io = [r for r in _rows(OUT) if r["route"] == "io-strip-prepayment-dominated"]
    assert len(io) == 74, f"{len(io)} I/O rows, expected 74"
    for r in io:
        assert r["bt"], "an I/O keeps its custodian price — that number is exact"
        assert not r["implied_spread_bp"], "an I/O must not publish a spread"
        assert not r["eff_duration_years"], "an I/O must not publish a duration"
        assert r["cf_life_years"], "but it keeps its cash-flow life"
        assert r["flag"], "and it must say why the numbers are withheld"


@pytest.mark.skipif(not OUT.exists(), reason="driver output not present")
def test_the_forwards_are_priced_as_forwards_and_the_unreadable_two_are_named():
    """⚠️ They were a NAMED route until 2026-10-07, because pricing a forward as a spot pool
    drops its settlement adjustment silently. Now ``tba.py`` carries the bump metrics, so the
    27 whose description states a settlement month are priced AS forwards; the 2 whose
    description states none keep the same reason ``pool_risk.py`` gives them."""
    rows = _rows(OUT)
    priced = [r for r in rows if r["route"] == "tba-forward"]
    unreadable = [r for r in rows if r["route"] == "tba-terms-unreadable"]
    assert len(priced) == 27, f"{len(priced)} priced forwards, expected 27"
    assert len(unreadable) == 2, f"{len(unreadable)} unreadable, expected 2"
    assert all(r["implied_spread_bp"] and r["eff_duration_years"] for r in priced)
    assert all(not r["implied_spread_bp"] for r in unreadable)
    assert all(r["paydown_source"] == "tba-forward-generic-pool" for r in priced)


@pytest.mark.skipif(not OUT.exists(), reason="driver output not present")
def test_only_the_forwards_separate_dv01_from_cs01_and_by_exactly_the_settlement_lag():
    """⭐⭐ The property that makes two columns worth having.

    With fixed cash flows the price depends only on ``z + s``, so a rate bump and a spread
    bump are one number: across every spot row in this table the two columns differ by exactly
    0.0. A forward's spread sits in the numerator only, so the two separate — and they
    separate by precisely the settlement lag, which is the arithmetic, not an estimate.
    """
    rows = [r for r in _rows(OUT) if r["dv01"] and r["cs01"]]
    assert len(rows) > 700, f"only {len(rows)} rows carry both numbers"
    differ = [r for r in rows if float(r["dv01"]) != float(r["cs01"])]
    assert {r["route"] for r in differ} == {"tba-forward"}, (
        "dv01 and cs01 may differ only for a forward; they differ on "
        f"{sorted({r['route'] for r in differ})}")
    assert len(differ) == 27, f"{len(differ)} rows differ, expected the 27 forwards"
    # and the spread bump is the LONGER of the two, never the other way round
    for r in differ:
        assert float(r["cs01"]) > float(r["dv01"]) > 0, r["asset_id"]


@pytest.mark.skipif(not OUT.exists(), reason="driver output not present")
def test_the_forward_numbers_are_the_same_numbers_the_pool_driver_publishes():
    """⚠️ Two tables, one security, two spreads would be the worst outcome of adding this
    route. The spread must be BIT-IDENTICAL to ``pool_risk``'s grid-mid column: same engine,
    same terms, same 25% CPR. Anything else means one of them reads the description
    differently."""
    pool_out = ROOT / "outputs" / "pool_risk_2009-03-31.csv"
    if not pool_out.exists():
        pytest.skip("pool_risk output not present")
    mine = {r["asset_id"]: r for r in _rows(OUT) if r["route"] == "tba-forward"}
    theirs = {r["asset_id"]: r for r in _rows(pool_out) if r["route"] == "tba-forward"}
    assert set(mine) == set(theirs), "the two tables disagree about WHICH forwards price"
    for aid, r in mine.items():
        assert float(r["implied_spread_bp"]) == float(theirs[aid]["implied_spread_bp_at_cpr_25"]), \
            f"{aid}: two tables, two spreads"
        # pool_risk publishes the SPREAD bump in a column called spread_dur_years; this table
        # publishes the RATE bump. The difference is the settlement lag, exactly.
        gap = float(theirs[aid]["spread_dur_years"]) - float(r["eff_duration_years"])
        assert abs(gap - float(theirs[aid]["settle_years"])) < 1e-7, f"{aid}: gap {gap}"


@pytest.mark.skipif(not OUT.exists(), reason="driver output not present")
def test_the_two_cash_flow_generators_agree_on_the_level():
    """⭐ Two different generators over two different populations. A large gap between their
    median spreads would mean one of them is wrong; they came out 10 bp apart."""
    rows = _rows(OUT)

    def med(route):
        xs = sorted(float(r["implied_spread_bp"]) for r in rows
                    if r["route"] == route and r["implied_spread_bp"])
        return xs[len(xs) // 2]

    observed, assumed = med("observed-amortising"), med("pool-assumed-speed")
    assert abs(observed - assumed) < 60, (
        f"observed-path median {observed:.1f}bp against assumed-speed {assumed:.1f}bp — a gap "
        "this large means one generator is wrong, not that the populations differ")


# --------------------------------------------------------------- the inert discrepancy

def test_the_two_CL_PO_tranches_are_numerically_inert():
    """⚠️ ``dataio.phase2.pool_structure`` calls two securities ``remic-tranche`` whose
    descriptions read ``CL PO``. Both carry a 0.000% income rate, so an amortising treatment
    produces cash flows IDENTICAL to a principal-only one — the interest leg is balance x 0/12.
    Pinned so that if either ever acquires a coupon, this goes red instead of the difference
    appearing in a published number."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("t1", DRIVER)
    path = [1.0, 0.7, 0.4, 0.1, 0.0]
    amort = obs.calculated_price(path, 0.0, obs.AMORTISING, FlatCurve(), 0.0)
    po = obs.calculated_price(path, 0.0, obs.PRINCIPAL_ONLY, FlatCurve(), 0.0)
    assert amort == po, "at a zero coupon the two treatments must be indistinguishable"
    assert spec is not None
