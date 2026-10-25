"""Locks for the securitised Tier-1 driver — the 412 CMO, CMBS and asset-backed securities.

Each corresponds to something that went wrong, or could have, while building it:

* the **borrowed bound** — the government book's flag text quotes a 1.77-year bound on the
  interest leg, measured on *its* paths. Letting this population inherit that sentence would
  be the weaker claim taking the stronger one's number, so a lock forbids the text here;
* **principal conservation**, the check the 882 actually rest on. ⚠️ My first attempt
  telescoped the raw factor path and reported a worst deviation of 57, because a telescoped
  path only reaches 100 when the factor runs to zero. The engine's own flows include the
  residual treatment, and they conserve to 1.4e-14;
* the **I/O refusal**, inherited from the assets layer rather than re-implemented;
* the **cover**, because 412 is the whole remaining structured book and a security falling
  out silently is the defect ``reconcile`` exists to prevent;
* the **separation from the 882**, since growing that delivered artifact instead of writing
  a sibling would have silently restated a number already in a client's hands.
"""
import csv
import pathlib

import pytest

from dataio.factor_history import (FACTOR_FILE_412, factor_path,
                                   load_factor_alignment, load_factor_history)
from pricer.assets.securitized import observed as obs

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "tier1_securitized_2009-03-31.csv"
DISPO = ROOT / "outputs" / "tier1_securitized_disposition_2009-03-31.csv"
GOVT = ROOT / "outputs" / "tier1_structured_2009-03-31.csv"
DRIVER = ROOT / "scripts" / "tier1_securitized.py"

pytestmark = pytest.mark.skipif(
    not OUT.exists(),
    reason="outputs/tier1_securitized_2009-03-31.csv is absent; run "
           "`PYTHONPATH=src python scripts/tier1_securitized.py`")


def _rows(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _num(row, key):
    value = (row.get(key) or "").strip()
    try:
        return float(value)
    except ValueError:
        return None


@pytest.fixture(scope="module")
def table():
    return _rows(OUT)


@pytest.fixture(scope="module")
def priced(table):
    return [r for r in table if (r.get("paydown_source") or "")]


def test_the_whole_remaining_structured_book_is_covered(table, priced):
    named = [r for r in table if not (r.get("paydown_source") or "")]
    assert len(table) == 412
    assert len(priced) == 371
    assert len(named) == 41
    assert {r["route"] for r in named} == {"no-factor-path"}


def test_it_is_the_three_classes_and_does_not_touch_the_882(table):
    assert {r["asset_class"] for r in table} == {"cmo", "abs", "cmbs"}
    counts = {}
    for r in table:
        counts[r["asset_class"]] = counts.get(r["asset_class"], 0) + 1
    assert counts == {"cmo": 264, "abs": 79, "cmbs": 69}
    if GOVT.exists():
        govt = {r["asset_id"] for r in _rows(GOVT)}
        assert not ({r["asset_id"] for r in table} & govt)


def test_the_io_strips_publish_a_price_and_no_risk_number(priced):
    """The refusal lives in the assets layer, so this driver inherits it."""
    io = [r for r in priced if r["route"] == "io-strip-prepayment-dominated"]
    assert io, "no interest-only strips in the output at all"
    for r in io:
        assert _num(r, "bt") is not None and _num(r, "mv_base_usd") is not None
        assert (r.get("implied_spread_bp") or "").strip() == ""
        assert (r.get("eff_duration_years") or "").strip() == ""
        assert "wrong sign" in (r.get("flag") or "")


def test_every_priced_row_carries_a_price_and_a_market_value(priced):
    for r in priced:
        assert _num(r, "bt") is not None and _num(r, "bt") > 0, r["asset_id"]
        assert _num(r, "mv_base_usd") is not None, r["asset_id"]


def test_principal_is_conserved_on_every_measured_path(priced):
    """⚠️ Sum the ENGINE's flows, which include the residual treatment — not the raw path,
    which only telescopes to 100 when the factor runs to zero."""
    history = load_factor_history(str(ROOT / "data"), FACTOR_FILE_412)
    if not history:
        pytest.skip("data/factor_history_412.csv is absent")
    alignment = load_factor_alignment(str(ROOT / "data"))
    worst, checked = 0.0, 0
    for r in priced:
        kind = r.get("cash_flow_kind") or obs.AMORTISING
        if kind == obs.INTEREST_ONLY:
            continue
        path = factor_path(history, (r.get("cusip") or "").strip(),
                           __import__("datetime").date(2009, 3, 31), alignment)
        if len(path) < 2:
            continue
        wam = _num(r, "wam_months")
        schedule = obs.observed_schedule(path, 0.0, kind,
                                         max_months=int(wam) if wam and wam > 0 else None)
        worst = max(worst, abs(sum(f.principal for f in schedule.flows) - 100.0))
        checked += 1
    assert checked >= 360, f"only {checked} paths were checkable"
    assert worst < 1e-12, f"principal conservation worst deviation {worst:.3e}"


def test_no_figure_measured_on_the_government_book_appears_here(table):
    """⭐ A measured number belongs to the population it was measured on.

    Two of the government driver's figures must never turn up in this table: the 1.77y
    interest-leg bound, and the 3.19-year rate-versus-spread gap measured on its floaters.
    This book's own gap is 6.89 years, more than twice it.
    """
    for r in table:
        flag = r.get("flag") or ""
        assert "bounded at 1.77y" not in flag, r["asset_id"]
        assert "p90 interest share" not in flag, r["asset_id"]
        assert "median of 3.19 years" not in flag, r["asset_id"]
    disclosed = [r for r in table if "coupon-structure:" in (r.get("flag") or "")]
    assert disclosed, "nothing disclosed a moving coupon at all"
    for r in disclosed:
        assert "median of 6.89 years" in r["flag"], r["asset_id"]
        assert "SPREAD duration" in r["flag"], r["asset_id"]


def test_an_unknown_coupon_multiplier_is_blank_and_never_one(table):
    """⚠️ 97 of the 180 disclosed rows here have no multiplier at all. A blank that a reader
    could mistake for 1.0 would make an assumed rate sensitivity indistinguishable from a
    measured one."""
    known = [r for r in table if (r.get("coupon_multiplier") or "").strip()]
    assert len(known) == 90, len(known)
    inverse = [r for r in known if float(r["coupon_multiplier"]) < 0]
    assert len(inverse) == 10, len(inverse)
    disclosed = [r for r in table if "coupon-structure:" in (r.get("flag") or "")]
    without = [r for r in disclosed if not (r.get("coupon_multiplier") or "").strip()]
    assert len(without) == 97, len(without)


def test_the_moving_coupon_disclosure_lands_on_exactly_the_right_rows(table):
    for r in table:
        has_note = "coupon-structure:" in (r.get("flag") or "")
        publishes = (r.get("eff_duration_years") or "").strip() != ""
        if has_note:
            assert publishes, f"{r['asset_id']} disclosed but publishes no duration"
            assert (r.get("coupon_structure") or "").strip()


def test_the_disposition_names_every_security_exactly_once(table):
    if not DISPO.exists():
        pytest.skip("the disposition sidecar is absent")
    rows = _rows(DISPO)
    assert len(rows) == 412
    assert len({r["asset_id"] for r in rows}) == 412
    assert {r["asset_id"] for r in rows} == {r["asset_id"] for r in table}
    skipped = [r for r in rows if r["status"] == "skipped"]
    assert len(skipped) == 41
    for r in skipped:
        assert r["reason_code"] and r["reason"]


def test_the_driver_does_not_reimplement_the_pricing(table):
    """⭐ It imports the core from the government driver, so the two tables cannot disagree
    about how a measured path is priced."""
    source = DRIVER.read_text(encoding="utf-8")
    assert "from tier1_structured import" in source
    assert "price_observed_row" in source
    assert "def price_observed_row" not in source, "the pricing core was copied, not imported"


def test_the_cusip_is_only_derived_from_a_us_isin():
    """A non-US ISIN's national number is not a CUSIP; deriving one anyway would key the
    factor history to the wrong security."""
    import sys

    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    import tier1_securitized as drv

    assert drv._cusip_from_isin("US31283KLA12") == "31283KLA1"
    assert drv._cusip_from_isin("XS0229705008") == ""
    assert drv._cusip_from_isin("") == ""
    assert drv._cusip_from_isin(None) == ""
