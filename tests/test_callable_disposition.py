"""Callable disposition and exercise-schedule representability (Round 2b hardening, 2026-08-31).

Two defects of the same family are pinned here. Both were found at Gate 0 of the delivery-quality
pass, and both are instances of the failure class this project keeps meeting: a security that is
neither priced nor flagged, or a right that is accepted and then quietly not applied.

**Defect 1 — a routing hole between two thresholds.** ``dataio.universe`` routed a call gap of
<= 7 days to vanilla and excluded everything else as ``callable``; ``scripts/callable_risk.py``
then priced only gaps > 366 days. Anything in between was excluded from the vanilla output AND
never seen by the lattice, with no message anywhere. ``TNTD04920858`` (gap 90 days) lived in that
hole. It was even written down once — WORKLOG, "1 short-gap callable (32-180d) still unpriced ...
minor loose end" — and then fell out of every subsequent count.

The fix is not to align two numbers. It is to separate the responsibilities:

    routing layer (universe)   decides WHETHER a bond is a callable candidate
    driver                     consumes EVERY candidate; it does not re-classify
    tree / wrapper             decides whether the contract is REPRESENTABLE on the grid

**Defect 2 — a non-empty schedule that maps to no exercise node.** The lattice exercises on
coupon dates, and by design never at the root or at maturity. A call date falling between the
last interior coupon and maturity therefore lands on no node at all: ``call_array`` comes back
all-``inf`` and the bond silently prices as a straight bond while the caller believes an option
was applied. That is exactly what made ``TNTD04920858``'s option value read as 0.000000 — the
option was never evaluated, not proven worthless.

⚠️ Do not weaken these into "the number came out the same". Both defects produce a **plausible**
number; only the disposition and the refusal distinguish them from a correct one.
"""
import datetime as dt
import os

import pytest

from curves.zero_curve import ZeroCurve
from dataio.dispositions import DispositionError, reconcile
from pricer.assets.corporate import embedded_option
from pricer.assets.corporate.embedded_option import ExerciseScheduleNotRepresentable
from pricer.core.market.curves import flat_zero_curve

VAL = "2009-03-31"
MAT = "2012-03-01"          # semiannual coupon steps land at 0.4286 ... 2.9286 years
COUPON = 5.0
FREQ = 2

# 2011-12-02 is 2.6813y out: after the last interior coupon step (2.4286) and before
# maturity (2.9286). There is no exercise node in that window.
UNREACHABLE = dt.date(2011, 12, 2)
REACHABLE = dt.date(2010, 12, 2)
FLAT = flat_zero_curve(0.03)


def _price(**rights):
    return embedded_option.calculated_price(COUPON, FREQ, MAT, VAL, FLAT, oas=0.0, **rights)


# ------------------------------------------------- defect 2: an accepted-then-ignored right

def test_a_call_schedule_that_reaches_no_exercise_node_is_refused():
    """The bug in one line: without this, the bond prices as a straight bond and says nothing."""
    with pytest.raises(ExerciseScheduleNotRepresentable):
        _price(call_schedule=[(UNREACHABLE, 100.0)])


def test_a_put_schedule_that_reaches_no_exercise_node_is_refused():
    with pytest.raises(ExerciseScheduleNotRepresentable):
        _price(put_schedule=[(UNREACHABLE, 100.0)])


def test_a_sinking_schedule_that_reaches_no_exercise_node_is_refused():
    with pytest.raises(ExerciseScheduleNotRepresentable):
        _price(sinking_schedule=[(UNREACHABLE, 0.5, 100.0)], fraction_basis="outstanding")


def test_each_right_is_checked_separately_not_just_the_union():
    """A live put must NOT license silently dropping a dead call.

    This is the subtle half. A guard written as "at least one array is active" passes this
    case and loses the call — which is the original defect wearing a different hat.
    """
    with pytest.raises(ExerciseScheduleNotRepresentable, match="call"):
        _price(call_schedule=[(UNREACHABLE, 100.0)],
               put_schedule=[(REACHABLE, 100.0)])


def test_a_reachable_schedule_still_prices():
    """The guard must not fire on the ordinary case, or it is worse than the bug."""
    straight = _price()
    callable_px = _price(call_schedule=[(REACHABLE, 100.0)])
    assert callable_px < straight          # an issuer right can only take value away
    puttable_px = _price(put_schedule=[(REACHABLE, 100.0)])
    assert puttable_px > straight


def test_the_refusal_names_what_a_reader_needs_to_act_on():
    """A refusal that does not say WHICH right, WHEN it starts and WHERE the grid ends
    sends the reader to the wrong file — the same failure the sinking-basis message had."""
    with pytest.raises(ExerciseScheduleNotRepresentable) as excinfo:
        _price(call_schedule=[(UNREACHABLE, 100.0)])
    message = str(excinfo.value)
    for needed in ("call", "2011-12-02", "2012-03-01", "coupon"):
        assert needed in message, f"refusal does not mention {needed!r}: {message}"


def test_the_live_short_gap_callable_is_the_case_this_guards():
    """TNTD04920858 on its real terms, on the real USD curve: 5.00% of 2012-03-01, callable
    at par from 2011-12-02. Its call is 90 days before maturity, inside the final coupon
    period. Before this guard it priced as a straight bond and the option read as exactly
    0.000000 — which was the right not being applied, NOT the right being worthless."""
    curve = ZeroCurve.from_currency("data", "USD", VAL, freq="Semiannual")
    with pytest.raises(ExerciseScheduleNotRepresentable):
        embedded_option.implied_oas(COUPON, FREQ, MAT, VAL, 85.1226, curve,
                                    call_schedule=[(UNREACHABLE, 100.0)])


# -------------------------------------------------------- defect 1: complete disposition

def test_reconcile_demands_exhaustive_and_disjoint_dispositions():
    candidates = {"A", "B", "C"}
    table = reconcile(candidates, priced={"A"},
                      skipped={"B": ("schedule-unavailable", "no row"),
                               "C": ("not-representable", "no node")})
    assert set(table["asset_id"]) == candidates
    assert len(table) == len(candidates)                       # each appears exactly once
    assert set(table["status"]) == {"priced", "skipped"}

    with pytest.raises(DispositionError, match="undisposed"):   # exhaustive
        reconcile(candidates, priced={"A"}, skipped={"B": ("x", "y")})
    with pytest.raises(DispositionError, match="both"):         # disjoint
        reconcile(candidates, priced={"A", "B"},
                  skipped={"A": ("x", "y"), "B": ("x", "y"), "C": ("x", "y")})
    with pytest.raises(DispositionError, match="reason"):       # every skip is explained
        reconcile(candidates, priced={"A"},
                  skipped={"B": ("", "no code"), "C": ("not-representable", "no node")})


def test_reconcile_rejects_a_bond_that_is_in_neither_set():
    """The shape of the original defect: TNTD04920858 was in no set at all, and every count
    still balanced, because it carried a named exclusion reason one layer up."""
    with pytest.raises(DispositionError) as excinfo:
        reconcile({"TNTD04920858"}, priced=set(), skipped={})
    assert "TNTD04920858" in str(excinfo.value)


# ------------------------------------------- the five callable names, locked individually

def _callable_candidates():
    """The callable bucket as the ROUTING layer defines it — the authoritative population."""
    import os

    from dataio.loaders import load_corporate_terms, load_master
    from dataio.term_overrides import load_make_whole_overrides
    from dataio.universe import build_universe

    wb = os.path.join("data", "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx")
    if not os.path.exists(wb):
        pytest.skip("URS workbook not present")
    _canon, excl, _funnel, _extras = build_universe(
        load_master(wb), load_corporate_terms(wb), VAL,
        make_whole_overrides=load_make_whole_overrides(
            os.path.join("data", "make_whole_overrides.csv")))
    return excl[excl["primary_reason"] == "callable"]


def test_the_five_callable_candidates_are_named_not_just_counted():
    """A count check (3 priced + 2 skipped == 5) passes even with the wrong bond in the
    wrong set. That is exactly how TNTD04920858 stayed invisible while every total
    balanced, so the names are locked individually.

    ⚠️ If this fails after a data delivery, it is probably CORRECT: a call schedule
    arriving for TNTD04923866 moves it from skipped to priced. Update the lock and say so
    in the WORKLOG — do not relax it into a count.
    """
    from dataio.call_schedules import load_call_schedules

    candidates = _callable_candidates()
    assert set(candidates["asset_id"].astype(str)) == {
        "TNTD04115619", "TNTD04441873", "TNTG701850W",   # priced on the lattice
        "TNTD04923866",                                   # awaiting a call schedule
        "TNTD04920858",                                   # call inside the final coupon period
    }

    schedules = load_call_schedules(os.path.join("data", "call_schedules.csv"))
    assert "TNTD04923866" not in schedules, (
        "TNTD04923866's blocker is a genuinely missing schedule; seeding one would "
        "manufacture terms nobody has")
    assert "TNTD04920858" in schedules, (
        "TNTD04920858 must HAVE a seeded schedule, so its reported blocker is the real one "
        "(no exercise node on the grid) and not a fabricated 'no schedule data' gap")


def test_the_short_gap_callable_reports_the_grid_blocker_not_a_data_gap():
    """Habit 5 in code: a blocker must be the true one. Without the seeded schedule row the
    driver would report 'no schedule data' — a data gap that does not exist."""
    import datetime as _dt
    import os as _os

    from dataio.call_schedules import load_call_schedules

    schedules = load_call_schedules(_os.path.join("data", "call_schedules.csv"))
    entries = schedules["TNTD04920858"]
    curve = ZeroCurve.from_currency("data", "USD", VAL, freq="Semiannual")
    with pytest.raises(ExerciseScheduleNotRepresentable) as excinfo:
        embedded_option.implied_oas(5.0, 2, "2012-03-01", VAL, 85.1226, curve,
                                    call_schedule=[(e[0], e[1]) for e in entries])
    assert excinfo.value.right == "call"
    assert excinfo.value.first_exercise == _dt.date(2011, 12, 2)
    assert excinfo.value.maturity == _dt.date(2012, 3, 1)


# ------------------------------------------------- CI coverage of the disposition guarantee
#
# The runtime check inside the drivers cannot go stale, but it also does not run under
# pytest. These add the CI half WITHOUT reading a git-ignored output file: the reconciliation
# primitive is unit-tested directly, and one integration test runs the real driver into a
# fresh temporary destination.

def test_reconcile_accepts_a_terminal_reason():
    """A terminal reason IS a disposition: the bond is not priced, and here is why."""
    table = reconcile({"A", "B"}, priced={"A"},
                      skipped={"B": ("terms-unavailable", "terms in neither sheet")})
    row = table[table["asset_id"] == "B"].iloc[0]
    assert row["status"] == "skipped"
    assert row["reason_code"] == "terms-unavailable"
    assert row["reason"]


def test_reconcile_rejects_an_undischarged_routing_reason():
    """The shape of the TNTD04920858 defect, at the primitive.

    A ROUTING reason ("the lattice driver handles this") is not a disposition. The driver
    proves it discharged by naming the bond; if the destination never honoured it, the bond
    reaches reconcile in neither set and must be named, not absorbed.
    """
    with pytest.raises(DispositionError, match="undisposed"):
        reconcile({"routed-away"}, priced=set(),
                  skipped={})                       # nobody claimed it
    # discharged properly, it passes
    table = reconcile({"routed-away"}, priced=set(),
                      skipped={"routed-away": ("routed-to-callable",
                                               "priced by the lattice driver")})
    assert table.iloc[0]["reason_code"] == "routed-to-callable"


def test_the_callable_driver_emits_a_complete_disposition(tmp_path):
    """The integration half: run the REAL driver into a fresh destination and check the
    sets it produced. Deliberately not reading outputs/, which is git-ignored and can be
    stale on a machine that has not re-run — which is the whole failure mode being guarded.
    """
    import subprocess
    import sys

    import pandas as pd

    wb = os.path.join("data", "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx")
    if not os.path.exists(wb):
        pytest.skip("URS workbook not present")

    out = tmp_path / "callable_risk.csv"
    disposition = tmp_path / "callable_disposition.csv"
    env = {**os.environ, "PYTHONPATH": "src", "FIP_VAL_DATE": VAL,
           "FIP_OUT": str(out), "FIP_DISPOSITION_OUT": str(disposition)}
    run = subprocess.run([sys.executable, os.path.join("scripts", "callable_risk.py")],
                         env=env, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr[-2000:]
    assert disposition.exists(), "the driver produced no disposition file"

    table = pd.read_csv(disposition, dtype={"asset_id": str})
    candidates = set(_callable_candidates()["asset_id"].astype(str))

    # exhaustive and disjoint, over identifiers rather than counts
    assert set(table["asset_id"]) == candidates
    assert len(table) == len(candidates)
    priced = set(table.loc[table["status"] == "priced", "asset_id"])
    skipped = set(table.loc[table["status"] == "skipped", "asset_id"])
    assert priced | skipped == candidates
    assert not (priced & skipped)

    # every skip carries a machine-readable code AND a sentence
    for _, row in table[table["status"] == "skipped"].iterrows():
        assert str(row["reason_code"]).strip(), row.to_dict()
        assert str(row["reason"]).strip(), row.to_dict()
