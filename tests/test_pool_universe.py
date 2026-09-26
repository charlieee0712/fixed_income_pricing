"""Locks for the Govt-MBS pool layer (router + driver, 2026-09-25).

Three things here are load-bearing and each was wrong at least once while being built:

  * the structure classification, which decides whether a security reaches the engine at all;
  * the face convention, which decides whether every position is right or half;
  * the finding that the zero-spread anchor fails, which is the reason the driver reports a
    trade-off curve instead of a valuation.

The last one is unusual to assert in a test. It is here because it is the round's actual
result: if a future change makes the zero-spread CPR look reasonable, either the engine or the
data changed materially and somebody must look.
"""
import datetime

import pandas as pd
import pytest

from dataio.phase2 import (POOL_ROUTE, POOL_STRUCTURE_PATTERNS, build_pool_universe,
                           load_master_phase2, pool_structure)

WB = "data/URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"
VAL = datetime.date(2009, 3, 31)


@pytest.fixture(scope="module")
def pools():
    master = load_master_phase2(WB)
    p, recon, counts = build_pool_universe(master, valuation_date=VAL)
    return p.merge(recon, on="asset_id", how="left"), counts


# --------------------------------------------------------------------------- the census

def test_the_pool_census_is_mece(pools):
    """888 rows -> 882 securities, every one with exactly one structure and one route."""
    p, counts = pools
    assert (counts["rows"], counts["unique"]) == (888, 882)
    assert len(p) == 882
    assert sum(counts["routes"].values()) == 882
    assert p["route"].isna().sum() == 0


def test_the_structure_split_is_the_recorded_one(pools):
    """The golden census. A change here changes which securities reach the engine."""
    p, _ = pools
    assert p["structure"].value_counts().to_dict() == {
        "pass-through": 490, "remic-tranche": 185, "io-strip": 76, "po-strip": 76,
        "tba-forward": 29, "unclassified": 18, "cmo-tranche": 7, "arm": 1}


def test_only_pass_throughs_reach_the_engine(pools):
    p, _ = pools
    assert set(p.loc[p["route"] == "pool", "structure"]) == {"pass-through"}
    assert (p["route"] == "pool").sum() == 490


# --------------------------------------------------------------------------- the slash

@pytest.mark.parametrize("desc, expected", [
    ("I/O FHLMC MULTICLASS REMIC 3260 CL CS B VAR RT", "io-strip"),
    ("P/O FHLMC MULTICLASS FHR 3331 PO/XX/7854685", "po-strip"),
    ("FHLMC MULTICLASS REMIC SER 2766 SX 03-15-2034", "remic-tranche"),
    ("FHLMC GOLD POOL E00721 6.5 07-01-2014", "pass-through"),
    ("FNMA 15 YEAR PASS-THROUGHS 5.5% 15 YEARS SETTLES APRIL", "tba-forward"),
    ("FNMA ADJUSTABLE RATE SERIES 2001-72 CLASS-SX", "arm"),
])
def test_the_structure_tags_are_read_in_priority_order(desc, expected):
    """A strip tag outranks a structure tag: "I/O ... REMIC ..." is both, and only one of
    those facts decides whether a pass-through model may touch it."""
    assert pool_structure(desc, "") == expected


def test_the_strip_patterns_require_the_slash(pools):
    """⚠️ The bug this exists for. A first version matched \\bIO\\b, which never matches "I/O",
    and 76 interest-only strips sat in the REMIC bucket looking like ordinary tranches. An IO
    strip receives no principal at all; pricing one as a level-pay pool is wrong by
    construction and produces a confident number.
    """
    p, _ = pools
    io = p[p["structure"] == "io-strip"]
    assert len(io) == 76, "the IO population changed; check the slash in the pattern"
    assert io["desc_long"].str.upper().str.contains(r"I/O", regex=True).all()
    # and the naive pattern really does miss them, which is why this test is not redundant
    import re
    assert not re.search(r"\bIO\b", "I/O FHLMC MULTICLASS REMIC 3260")


def test_every_structure_has_a_route(pools):
    p, _ = pools
    assert set(p["structure"]) <= set(POOL_ROUTE)
    assert {name for name, _ in POOL_STRUCTURE_PATTERNS} | {"unclassified"} == set(POOL_ROUTE)


# --------------------------------------------------------------------------- the face convention

def test_par_value_is_current_face_not_original(pools):
    """⚠️ If this is wrong every position is wrong, and by about half.

    ``MV == par * BT/100 * fx`` holds, so ``par_value`` is already the CURRENT balance and the
    paydown factor must NOT be applied on top. The same identity with the factor multiplied in
    gives 1.886, which is what the mistake would look like.
    """
    p, _ = pools
    d = p[(p["par_value"] > 0) & (p["gold_price"] > 0) & p["gold_mkt_value"].notna()]
    ratio = d["gold_mkt_value"] / (d["par_value"] * d["gold_price"] / 100.0)
    assert ratio.median() == pytest.approx(1.0, abs=1e-4)
    assert (ratio.sub(1).abs() > 0.01).sum() <= 6

    f = d[d["paydown_factor"].notna() & (d["paydown_factor"] > 0)]
    wrong = f["gold_mkt_value"] / (f["par_value"] * f["paydown_factor"] * f["gold_price"] / 100.0)
    assert wrong.median() > 1.5, "the factor-applied identity should be badly wrong, and is"


def test_the_remaining_term_comes_from_the_master_not_the_pull(pools):
    """The pull's WAM is as-of 2026 and ~220 months short; the holdings file had it all along."""
    p, _ = pools
    w = p["wam_months"].dropna()
    assert len(w) >= 860
    assert (w < 0).sum() == 0, "no pool in a 2009 portfolio had already matured"
    assert 250 <= w.median() <= 330


# --------------------------------------------------------------------------- the finding

def test_the_zero_spread_anchor_still_fails():
    """⭐ The round's actual result, asserted so it cannot quietly stop being true.

    Fixing the spread at zero and solving for the CPR gives a median around 66% against the
    10-25% agency pools really prepaid in early 2009, and leaves pools that no CPR can reach.
    That is why the driver reports a trade-off curve rather than a valuation. If this ever
    starts looking reasonable, something material changed and the anchor decision needs
    revisiting rather than inheriting.
    """
    out = "outputs/pool_risk_2009-03-31.csv"
    try:
        d = pd.read_csv(out)
    except FileNotFoundError:
        pytest.skip(f"{out} not built in this checkout")
    assert d["implied_cpr_pct_at_zero_spread"].median() > 50.0
    assert d["implied_cpr_pct_at_zero_spread"].isna().sum() > 0


def test_the_spread_is_robust_to_the_cpr_assumption():
    """Why the missing 2009 CPR costs less than it looks like it should.

    Twenty points of prepayment uncertainty move the spread by well under a hundred basis
    points, so "roughly 220-270 bp at 2009-03-31" survives not knowing the CPR.
    """
    out = "outputs/pool_risk_2009-03-31.csv"
    try:
        d = pd.read_csv(out)
    except FileNotFoundError:
        pytest.skip(f"{out} not built in this checkout")
    width = (d["implied_spread_bp_at_cpr_15"] - d["implied_spread_bp_at_cpr_35"]).abs()
    assert width.median() < 100.0
    for cpr in (15, 25, 35):
        assert 100.0 < d[f"implied_spread_bp_at_cpr_{cpr}"].median() < 400.0


def test_the_pool_driver_does_not_touch_the_phase2_universe():
    """govt_mbs is COUNT_ONLY in PHASE2_CLASSES on purpose: letting it build a universe there
    would push 882 rows into phase2_risk.py's 63-row hashed artifact."""
    from dataio.phase2 import COUNT_ONLY, PHASE2_CLASSES, build_phase2_universe
    assert "govt_mbs" in PHASE2_CLASSES and "govt_mbs" in COUNT_ONLY
    master = load_master_phase2(WB)
    bonds, _, _ = build_phase2_universe(master)
    assert len(bonds) == 63
    assert "govt_mbs" not in set(bonds["asset_class"])


# --------------------------------------------------------------------------- moneyness

def test_the_mortgage_rate_lookup_does_not_look_ahead():
    """⚠️ The survey publishes weekly on a Thursday, so a valuation date usually sits days
    after the last print and days BEFORE the next one. Taking the nearest observation would
    reach into the future: 2009-06-10 is one day before the 06-11 survey, and using 5.59%
    there would price the book with a rate the market had not yet seen.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("pool_risk", "scripts/pool_risk.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    rate, src = mod.mortgage_rate_on(datetime.date(2009, 6, 10))
    assert rate == 5.29 and "2009-06-04" in src, "must take the last print BEFORE the date"
    assert mod.mortgage_rate_on(datetime.date(2009, 3, 31))[0] == 4.85
    # before every row -> nothing, rather than reaching forward to the first one
    assert mod.mortgage_rate_on(datetime.date(2000, 1, 1))[0] is None


@pytest.mark.parametrize("val", ["2009-03-31", "2009-06-10"])
def test_spread_rises_with_moneyness_on_the_in_the_money_side(val):
    """⭐ The cross-sectional check, and the part of it that is robust.

    Deeper in the money means more spread, at BOTH dates. This is the ITM half of the OAS
    smile in NY Fed Staff Report 674, obtained from custodian prices and a static engine with
    no dealer quote and no prepayment model.

    The OTM bucket is deliberately EXCLUDED. Its upturn appears at 3-31 over fourteen
    securities and reverses at 6-10; asserting it would lock in a result the data does not
    support at both dates.
    """
    out = f"outputs/pool_risk_{val}.csv"
    try:
        d = pd.read_csv(out)
    except FileNotFoundError:
        pytest.skip(f"{out} not built in this checkout")
    itm = d[d["moneyness_pct"] > -0.5]
    b = pd.cut(itm["moneyness_pct"], [-0.5, 0.5, 1.5, 2.5, 99])
    med = itm.groupby(b, observed=True)["implied_spread_bp_at_cpr_25"].median()
    assert len(med) == 4
    assert list(med) == sorted(med), f"not monotonic in moneyness: {list(med.round(1))}"
    assert med.iloc[-1] - med.iloc[0] > 50, "the effect should be worth more than noise"
