"""Locks for the observed-paydown engine and the factor-history loader.

⚠️ Written after an audit found the engine shipped with **zero** deliberate tests — the
suite count had risen by two only because ``test_exception_wiring`` is parametrized over
source files and picked the new modules up on its own. An addition is not a check.

The order below is "what would have caught today's defects":

1. principal conservation as an IDENTITY, including the sub-floor residual that broke it
   (99.9500 instead of 100.0000) while the label claimed the balance had been repaid;
2. the 2026-10-01 validation figures, pinned so a later edit cannot drift them in silence;
3. ``dv01 == cs01``, as a property of fixed flows rather than a coincidence;
4. the T+1 shift, mutation-verified — set the lag to 0 and the test must go red;
5. the kind routing, because ``\\bPO\\b`` not matching ``P/O`` already cost 76 securities.
"""
import datetime as dt
import math
import pathlib

import pytest

from curves.zero_curve import ZeroCurve
from dataio import factor_history as fh
from pricer.core.pricing import observed_paydown as op

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
OUTPUTS = pathlib.Path(__file__).resolve().parents[1] / "outputs"
VAL = dt.date(2009, 3, 31)


class FlatCurve:
    """A data-free curve, so the arithmetic tests do not depend on a file."""

    def __init__(self, rate=0.04):
        self.rate = rate

    def zero_rate(self, t):
        return self.rate


# --------------------------------------------------------------------------- 1. identity

@pytest.mark.parametrize("path,label", [
    ([1.0, 0.8, 0.6, 0.4, 0.2, 0.0], "runs to zero inside the window"),
    ([1.0, 0.9, 0.8, 0.7, 0.6, 0.5], "ends with half the balance outstanding"),
    ([1.0, 0.5, 0.2, 0.05, 0.01, 0.0005], "ends BELOW the residual floor"),
    ([1.0, 1.2, 1.5, 1.3, 0.9, 0.4], "accrual tranche — factor rises above 1 first"),
])
def test_principal_is_conserved_whatever_the_tail_does(path, label):
    """Every unit of starting balance must be accounted for. This is an identity, not a
    tolerance — and the third case is the one that was silently violated."""
    sch = op.observed_schedule(path, 6.0, op.AMORTISING, max_months=600)
    total = sum(f.principal for f in sch.flows)
    assert abs(total - 100.0) < 1e-12, (
        f"{label}: principal summed to {total!r}, not 100 — treatment was "
        f"{sch.treatment!r}, residual {sch.residual_fraction!r}")


def test_a_sub_floor_residual_is_repaid_and_SAYS_so():
    """⚠️ The exact defect found in the audit: the residual was dropped, conservation broke,
    and ``residual_treatment`` still claimed the balance had been repaid."""
    path = [1.0, 0.5, 0.2, 0.05, 0.01, 0.0005]
    frac = path[-1] / path[0]
    assert frac < op.RESIDUAL_FLOOR, "fixture no longer exercises the sub-floor branch"
    sch = op.observed_schedule(path, 6.0, op.AMORTISING, max_months=600)
    assert sch.treatment == op.T_REPAID_BELOW_FLOOR
    assert abs(sum(f.principal for f in sch.flows) - 100.0) < 1e-12


def test_the_treatment_distinguishes_a_decision_from_a_fallback():
    """Four of the seven treatments are lumps for four different reasons. A reader who
    cannot tell them apart cannot tell what the engine chose from what it fell back to."""
    slow = [1.0] + [1.0 - 0.002 * i for i in range(1, 60)]      # decays, but very slowly
    assert op.observed_schedule(slow, 6.0, residual="repay").treatment == op.T_REPAID_REQUESTED
    assert op.observed_schedule(slow, 6.0, residual="drop").treatment == op.T_DROPPED
    # amortising cannot finish within a 2-month legal bound -> an overrun, not a request
    assert op.observed_schedule(slow, 6.0, max_months=61).treatment == op.T_REPAID_OVERRUN
    # a flat tail has no speed to continue at
    flat = [1.0, 0.9, 0.5, 0.5, 0.5, 0.5]
    assert op.observed_schedule(flat, 6.0).treatment == op.T_REPAID_NOT_DECAYING
    # and one that genuinely finishes inside the window
    done = [1.0, 0.8, 0.5, 0.2, 0.0]
    assert op.observed_schedule(done, 6.0).treatment == op.T_NONE


def test_dropping_the_tail_is_the_only_mode_that_loses_principal():
    """``drop`` exists to reproduce the 10-01 first run; it must be the *only* way to lose
    balance, so no other mode can leak silently."""
    path = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5]
    dropped = sum(f.principal for f in op.observed_cash_flows(path, 6.0, residual="drop"))
    assert dropped == pytest.approx(50.0, abs=1e-12)
    for mode in ("amortise", "repay"):
        kept = sum(f.principal for f in op.observed_cash_flows(path, 6.0, residual=mode,
                                                               max_months=600))
        assert abs(kept - 100.0) < 1e-12, mode


def test_an_accrual_tranche_nets_to_exactly_zero_cash_while_it_accretes():
    """⭐ The Z-tranche identity, and it is exact rather than approximate.

    A 6% coupon accrues 0.5% of balance a month. If the factor also GROWS by 0.5% that
    month, the negative principal term and the positive interest term cancel to **zero net
    cash** — which is precisely what an accrual tranche pays. No special case anywhere.

    ⚠️ The path must run on to zero, otherwise the residual lump lands on the first flow and
    masks the sign (an earlier version of this test used a two-element path and measured the
    lump instead of the accretion).
    """
    path = [1.0, 1.005, 0.8, 0.5, 0.2, 0.0]
    sch = op.observed_schedule(path, 6.0, op.AMORTISING)
    assert sch.treatment == op.T_NONE, "the path repays fully; no tail treatment should apply"
    first = sch.flows[0]
    assert first.principal == pytest.approx(-0.5, abs=1e-12), "accretion is negative principal"
    assert first.interest == pytest.approx(0.5, abs=1e-12)
    assert abs(first.total) < 1e-12, "accrual month must net to exactly zero cash"


# --------------------------------------------------------------------------- 2. the record

def _validation_rows():
    import csv
    hist = fh.load_factor_history(str(DATA))
    grp = fh.load_request_groups(str(DATA))
    with open(OUTPUTS / f"pool_risk_{VAL}.csv", encoding="utf-8-sig", newline="") as f:
        risk = list(csv.DictReader(f))
    with open(OUTPUTS / "mbs_data_check_2026-07-30.csv", encoding="utf-8-sig", newline="") as f:
        cus = {r["asset_id"]: r["cusip"] for r in csv.DictReader(f)}
    out = []
    for r in risk:
        c = cus.get(r["asset_id"])
        if c and grp.get(c) == "validation-pool":
            out.append((c, float(r["bt"]), float(r["net_coupon_pct"]),
                        [float(r[f"implied_spread_bp_at_cpr_{k}"]) for k in (15, 25, 35)]))
    return hist, out


@pytest.mark.skipif(not (DATA / "factor_history.csv").exists(),
                    reason="factor history not present")
def test_the_engine_reproduces_the_2026_10_01_validation():
    """⭐ The three figures that justified building this route. Pinned so a tidy-up cannot
    drift them without going red: principal 100.0000, realised CPR median 23.94%, and
    n=14 in-grid at median 8.2 bp / signed −2.6 bp against the assumed-CPR engine."""
    hist, rows = _validation_rows()
    assert len(rows) == 20, f"expected the 20 validation pools, found {len(rows)}"
    curve = ZeroCurve.from_currency(str(DATA), "USD", VAL, freq="Monthly")

    diffs, cprs, worst = [], [], 0.0
    for cusip, bt, cpn, grid in rows:
        path = fh.factor_path(hist, cusip, VAL)
        # 10-01 used residual="repay"; match it exactly before comparing
        sch = op.observed_schedule(path, cpn, residual="repay")
        worst = max(worst, abs(sum(f.principal for f in sch.flows) - 100.0))
        s = op.implied_spread_observed(bt, curve, path, cpn, residual="repay")
        live = [x for x in path if x and x > 0]
        cpr = 1 - (live[-1] / live[0]) ** (12 / (len(live) - 1))
        cprs.append(cpr)
        if 0.15 <= cpr <= 0.35:
            lo, mid, hi = grid
            eng = (lo + (cpr - .15) / .10 * (mid - lo) if cpr <= .25
                   else mid + (cpr - .25) / .10 * (hi - mid))
            diffs.append(s * 1e4 - eng)

    cprs.sort()
    median_cpr = cprs[len(cprs) // 2 - 1:len(cprs) // 2 + 1]
    median_cpr = sum(median_cpr) / len(median_cpr)
    assert worst < 1e-9, f"principal conservation worst deviation {worst:.2e}"
    assert abs(100 * median_cpr - 23.94) < 0.05, f"realised CPR median {100*median_cpr:.2f}%"
    assert len(diffs) == 14, f"{len(diffs)} in-grid pools, expected 14"
    ab = sorted(abs(d) for d in diffs)
    med_abs = (ab[6] + ab[7]) / 2
    sg = sorted(diffs)
    med_signed = (sg[6] + sg[7]) / 2
    assert abs(med_abs - 8.2) < 0.15, f"median |diff| {med_abs:.2f} bp, record 8.2"
    assert abs(med_signed - (-2.6)) < 0.15, f"signed median {med_signed:+.2f} bp, record -2.6"


# --------------------------------------------------------------------------- 3. dv01 == cs01

def test_dv01_equals_cs01_because_the_flows_do_not_respond():
    """With fixed cash flows the price depends only on ``z + s``, so bumping the curve and
    bumping the spread are the same arithmetic. ⭐ Asserted as a PROPERTY so that the day a
    generator makes flows respond to rates, this test is the one that notices."""
    path = [1.0, 0.85, 0.7, 0.55, 0.4, 0.2, 0.0]
    k = op.observed_risk_metrics(FlatCurve(0.04), path, 6.0, spread=0.01)
    assert k["dv01"] == k["cs01"]

    # and the mechanism, shown rather than asserted: a curve shifted by 1bp gives the same
    # price as a spread raised by 1bp
    p_curve = op.price_observed(FlatCurve(0.0401), path, 6.0, spread=0.01)
    p_spread = op.price_observed(FlatCurve(0.04), path, 6.0, spread=0.0101)
    assert p_curve == pytest.approx(p_spread, rel=1e-15)


def test_an_interest_only_strip_cannot_produce_a_negative_duration():
    """⚠️ The boundary, locked. An I/O's rate risk is dominated by prepayment response,
    which fixed flows cannot express, so its duration here is always POSITIVE — measured
    74 of 74 on the real book against 49 custodian durations that are negative. The lock
    exists so nobody later mistakes the sign for a modelling success."""
    path = [1.0, 0.8, 0.6, 0.45, 0.3, 0.15, 0.05]
    k = op.observed_risk_metrics(FlatCurve(0.04), path, 6.0, op.INTEREST_ONLY, spread=0.05)
    assert k["eff_duration"] > 0
    assert math.isnan(k["wal"]), "an I/O has no principal, so a principal-weighted WAL is NaN"
    assert k["cf_life"] > 0, "cf_life is defined for all three kinds"


# --------------------------------------------------------------------------- 4. T+1

@pytest.mark.skipif(not (DATA / "factor_history.csv").exists(),
                    reason="factor history not present")
def test_the_T_plus_one_shift_lands_on_the_custodians_own_number():
    """``3133T5MR1`` is the security the check earned its keep on: reading Bloomberg's own
    label puts the balance out by a factor of six."""
    hist = fh.load_factor_history(str(DATA))
    assert fh.factor_path(hist, "3133T5MR1", VAL)[0] == pytest.approx(0.00196067, abs=1e-12)
    assert hist["3133T5MR1"]["2009-03"] == pytest.approx(0.01212421, abs=1e-12)


@pytest.mark.skipif(not (DATA / "factor_history.csv").exists(),
                    reason="factor history not present")
def test_the_T_plus_one_lock_is_not_decorative(monkeypatch):
    """Mutation: with the lag set to 0 the path must start on the WRONG number. A lock that
    passes under its own mutation is decorative."""
    hist = fh.load_factor_history(str(DATA))
    monkeypatch.setattr(fh, "BLOOMBERG_MONTH_LAG", 0)
    assert fh.factor_path(hist, "3133T5MR1", VAL)[0] == pytest.approx(0.01212421, abs=1e-12)


def test_the_month_label_round_trips_across_a_year_boundary():
    assert fh.bloomberg_month_for(dt.date(2009, 12, 31)) == "2010-01"
    assert fh.as_of_for("2010-01") == (2009, 12)
    assert fh.as_of_for(fh.bloomberg_month_for(dt.date(2015, 7, 31))) == (2015, 7)


def test_a_negative_factor_is_refused_by_the_loader(tmp_path):
    (tmp_path / "factor_history.csv").write_text(
        "cusip,bloomberg_month,factor\nX,2009-04,-0.5\n", encoding="utf-8")
    with pytest.raises(ValueError, match="negative factor"):
        fh.load_factor_history(str(tmp_path))


def test_a_missing_file_means_no_history_not_an_error(tmp_path):
    assert fh.load_factor_history(str(tmp_path)) == {}
    assert fh.load_request_groups(str(tmp_path)) == {}


# --------------------------------------------------------------------------- 5. kinds

def test_each_kind_drops_exactly_the_leg_it_should():
    path = [1.0, 0.7, 0.4, 0.0]
    amort = op.observed_cash_flows(path, 6.0, op.AMORTISING)
    po = op.observed_cash_flows(path, 0.0, op.PRINCIPAL_ONLY)
    io = op.observed_cash_flows(path, 6.0, op.INTEREST_ONLY)
    assert all(f.interest == 0.0 for f in po), "a P/O pays no interest"
    assert sum(f.principal for f in po) == pytest.approx(100.0, abs=1e-12)
    assert all(f.principal == 0.0 for f in io), "an I/O repays no principal"
    assert sum(f.interest for f in io) > 0
    assert sum(f.principal for f in amort) == pytest.approx(100.0, abs=1e-12)
    assert sum(f.interest for f in amort) > 0


def test_an_unknown_kind_or_residual_mode_is_refused():
    with pytest.raises(ValueError, match="kind must be one of"):
        op.observed_schedule([1.0, 0.5], 6.0, "bullet")
    with pytest.raises(ValueError, match="residual must be one of"):
        op.observed_schedule([1.0, 0.5], 6.0, residual="ignore")


def test_terminal_smm_refuses_to_invent_a_speed():
    assert op.terminal_smm([1.0, 0.5]) is None, "too short to estimate"
    assert op.terminal_smm([1.0, 1.1, 1.2, 1.3]) is None, "accreting: no decay to continue"
    assert op.terminal_smm([1.0, 0.5, 0.5, 0.5]) is None, "flat tail: no decay to continue"
    smm = op.terminal_smm([1.0, 0.9, 0.81, 0.729, 0.6561])
    assert smm == pytest.approx(0.10, abs=1e-12), "a clean 10%/month decay"


def test_a_dead_path_produces_no_flows_rather_than_a_division_by_zero():
    assert op.observed_schedule([0.0, 0.0], 6.0).flows == []
    assert op.observed_schedule([1.0], 6.0).flows == []
    assert op.observed_schedule([], 6.0).flows == []
