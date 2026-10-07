"""Tier-1 driver: an amortising, market-calibrated spread and risk for the Government-MBS book.

**What this produces.** One row for **every** one of the 882 Government Mortgage-Backed
securities, of which **858** carry a modelled amortising cash flow and the remaining **24** are
named. Nothing else in the portfolio moves.

⭐ The plan written before any of it ran said 861 and 21, and the difference is exactly three
securities: two whose factor is already zero at the valuation date and one whose measured path
produces no net cash at all. **Neither is visible until the path is read**, which is why the
estimate could not have been better and why the three are named rather than absorbed.

Phase 1 of the client's three-tier method (`docs/cc_plan_govt_mbs_amortising_tier1_2026-10-06.md`
and the two decks of 2026-10-06): the custodian's own price is the anchor, the cash flows are
**fixed**, one flat spread is solved so the model reproduces that price, and the risk comes from
bumping rates and spreads.

⚠️⚠️ **THE CASH FLOWS AMORTISE; THEY ARE NOT A BULLET — and that is the whole point of this
driver.** The client's slide 19 says Phase 2 will "replace legal-maturity bullet behaviour",
which implies Phase 1 bullets. Measured on the 373 securities whose real paydown we hold, a
bullet at the legal final overstates the timing by **6.87x** — legal life median 24.32y against
a realised WAL of 2.99y — i.e. roughly **+21 years of duration** on the median security, on
57% of the portfolio by count, on the one output the project exists to produce. Amortising
costs nothing (the engine already prices the 505 pools that way) and is still Phase 1: fixed
flows, one spread, no response to rates.

**Two cash-flow generators, and which one a row used is on the row.**

==========================  =====  ====================================================
``paydown_source``             n    where the balance schedule comes from
==========================  =====  ====================================================
``observed-factor-path``      373  :mod:`pricer.core.pricing.observed_paydown` — the
                                   MEASURED monthly factor history from Bloomberg
``assumed-cpr``               458  :mod:`pricer.assets.securitized.pool` — level-pay at
                                   :data:`BOOK_CPR_PCT`
``tba-forward-generic-pool``   27  :mod:`pricer.assets.securitized.tba` — the generic pool
                                   the forward delivers, discounted to its settlement date
(named, no numbers)            24  19 with neither a path nor a usable pool WAC, 3 degenerate
                                   paths, 2 forwards whose description states no settlement
                                   month
==========================  =====  ====================================================

⚠️ 376 securities have a factor path; 373 of them produce numbers. The other three are the
degenerate ones above, and they are counted as named, not as a source.

⭐ :data:`BOOK_CPR_PCT` is **measured, not chosen**: the 32 pass-through pools whose real paths
we hold realised a whole-life median of **25.05%** and a forward-12-month median of **25.83%**.
The two agree, and 25% is already the middle point of the three-point grid
``pool_risk.py`` publishes — so this driver's single-speed number sits on a speed the data
supports rather than on a convention.

⚠️⚠️ **THE 76 INTEREST-ONLY STRIPS SHIP WITH A PRICE AND NO RISK NUMBERS.** An I/O's rate
sensitivity is almost entirely prepayment response — rates up, refinancing slows, the notional
survives longer, more interest arrives — and fixed cash flows cannot express it. Measured over
the 74 that price: **74 of 74** come out with a POSITIVE duration while **49** of their
custodian durations are negative, and the calibrated spreads run **−56,670 to +6,719 bp**. They
are computable, not usable. ⭐ The rule: **publish a risk number only when its sign is known to
be right.** So their price and market value are published (those are exact, being calibrated to
the custodian's own mark), their spread and duration are **blank**, the route says
``io-strip-prepayment-dominated``, and the custodian's duration sits in its own column as
evidence. ⚠️ Our column is never filled with their number — the standing rule is that custodian
duration is evidence, never a router, and a column that sometimes holds our model and sometimes
theirs is worse than a blank.

⭐⭐ **THE 27 TBA FORWARDS ARE THE ONLY ROWS IN THIS BOOK WHERE DV01 AND CS01 ARE DIFFERENT
NUMBERS.** Every other security here is discounted at ``z(t) + s``, so a parallel rate bump and
a spread bump are the same arithmetic and the two columns hold one number twice — across the
757 rows priced before these forwards the difference was exactly 0.0, every row. A TBA is a
forward: its price is struck for a settlement date weeks out, the spread sits in the numerator
only, and the financing leg carries the rate without the spread. So its rate duration is
shorter than its spread duration by EXACTLY the settlement lag (15 or 45 days here, measured
residual 1.0e-08). ``eff_duration_years``, ``dv01`` and ``convexity`` are all taken from the
RATE bump and only ``cs01`` from the spread bump, because a rate duration beside a spread
convexity cannot be used together to approximate a move. ⚠️ Their static duration is also
one-sided rather than merely approximate: all 27 are premiums, median 2.85y against a custodian
1.82y, 5 of 27 beyond the 1.5y reporting threshold — the same shape and nearly the same
proportion as the 478 spot pools (21%), but in one direction only.

⚠️ **Not an OAS, and the name is locked.** The spread here is an *implied, bond-equivalent*
spread; the client's own slide 13 says *"a true OAS requires explicit modeling of
option-dependent cash flows such as prepayments."* ``tests/test_tier1_structured.py`` injects
the banned name and fails.

Inputs
------
1. ``FIP_VAL_DATE``   valuation date, default ``2009-03-31``.
2. ``FIP_OUT``        output CSV, default ``outputs/tier1_structured_<date>.csv``.
3. ``data/factor_history.csv``        the measured paths, via :mod:`dataio.factor_history`.
4. ``data/govt_mtge_bdp.xlsm``        the pull's WAC, via ``pool_risk.load_pool_terms``.
5. the holdings workbook              master superset, via :func:`dataio.phase2.load_master_phase2`.

Outputs
-------
* ``outputs/tier1_structured_<date>.csv``              882 rows (858 priced, 24 named)
* ``outputs/tier1_structured_disposition_<date>.csv``  every security and its disposition
"""
import datetime
import os
import sys

sys.path[:0] = ["src", "scripts"]

import pandas as pd  # noqa: E402

import pool_risk as D  # noqa: E402  — reuse its loaders rather than copy them
from curves.zero_curve import ZeroCurve  # noqa: E402
from dataio.dispositions import reconcile  # noqa: E402
from dataio.factor_history import factor_path, load_factor_history  # noqa: E402
from dataio.phase2 import (build_pool_universe, load_master_phase2,  # noqa: E402
                           parse_tba_terms)
# ⚠️ Through the ASSETS layer, never the core. That layer owns the percent/decimal
# boundary and the one refusal; reaching past it into the core produced a calibrated spread
# of 46,478 bp on 487 pools -- a 465% spread, from passing 6.000 where 0.06000 was wanted.
from pricer.assets.securitized import observed as obs  # noqa: E402
from pricer.assets.securitized import pool  # noqa: E402
from pricer.assets.securitized import tba  # noqa: E402

VAL = os.environ.get("FIP_VAL_DATE", "2009-03-31")
VAL_DATE = datetime.date.fromisoformat(VAL)
OUT = os.environ.get("FIP_OUT", f"outputs/tier1_structured_{VAL}.csv")
DISPOSITION = OUT.replace(".csv", "_disposition.csv").replace(
    f"tier1_structured_{VAL}_disposition", f"tier1_structured_disposition_{VAL}")

#: ⭐ MEASURED on the 32 pass-through pools whose realised paths we hold: whole-life median
#: 25.05%, forward-12-month median 25.83%. The two agree, so the choice between them does not
#: matter, and 25 is already the centre of ``pool_risk.CPR_GRID_PCT``. ⚠️ It is a BOOK-level
#: assumption, not a per-pool measurement, and every row that uses it says so in
#: ``paydown_source``.
BOOK_CPR_PCT = 25.0

#: The cash-flow shape per structural kind. ⚠️ :func:`dataio.phase2.pool_structure` is the ONE
#: owner of the classification; this maps its answer onto an engine mode and nothing here
#: re-reads a description.
KIND_FOR_STRUCTURE = {
    "io-strip": obs.INTEREST_ONLY,
    "po-strip": obs.PRINCIPAL_ONLY,
}

#: ⚠️ `pool_structure` calls two securities `remic-tranche` whose description reads `CL PO`
#: (31394L4L3, 31397PP87). Both carry `income_rate = 0.000%`, so an amortising treatment
#: produces cash flows IDENTICAL to a principal-only one — the interest leg is balance x 0/12.
#: The discrepancy is therefore numerically inert and is left alone rather than given a second
#: classifier; `tests/test_tier1_structured.py` pins the inertness so it cannot start to matter
#: unnoticed. Fixing the pattern is a named follow-up for whoever next touches `pool_structure`
#: (it would move two route labels in `pool_disposition_*.csv` and no priced number).
INERT_PO_DISCREPANCY = ("31394L4L3", "31397PP87")

#: Terminal reasons: the security has no amortising representation at all.
_REASON = {
    "no-path-no-pool-terms": "neither a measured factor path nor a usable pool WAC",
    "no-price": "no custodian price to calibrate against",
    "no-coupon": "no income rate in the holdings file",
    "dead-path": "the factor is already zero at the valuation date: no remaining cash flow",
    "observed-flows-sum-to-zero":
        "the measured path produces no net cash at all, so no spread can reprice it to the "
        "custodian's mark — a strip whose factor does not move in the observed window, or an "
        "accrual tranche whose negative principal exactly cancels its interest",
    "observed-not-calibratable":
        "no flat spread in [-95%, +2000%] reprices the measured cash flows to the custodian's "
        "mark; the price and the realised path are inconsistent with each other",
    "pool-maturity-unavailable": "no maturity date, so the remaining term cannot be computed",
    "pool-coupon-inconsistent": "income rate exceeds the gross WAC: not a fixed-rate pool",
    "curve-blocked": "the USD curve could not be built at this date",
    # ⚠️ The three TBA reasons are worded as `pool_risk.py` words them, deliberately: the
    # two dispositions name the same security with the same words, so a reader comparing them
    # does not have to work out whether two phrasings mean one thing.
    "tba-terms-unreadable": "the description does not state ",
    "tba-spread-not-solvable":
        "no spread reproduces the quoted forward at the assumed CPR: ",
}

#: The four description-derived terms a forward cannot be priced without. ``parse_tba_terms``
#: is the one owner of the reading; this driver only checks that it succeeded.
TBA_REQUIRED_TERMS = ("issuer", "term_months", "coupon_pct", "settle_month")


class _ZeroCurve:
    """Zero discounting, for the one check that asks whether there is any cash flow at all."""

    @staticmethod
    def zero_rate(_t):
        return 0.0


def _num(v):
    x = pd.to_numeric(pd.Series([v]), errors="coerce").iloc[0]
    return None if pd.isna(x) else float(x)


def _blank_risk():
    return dict(implied_spread_bp=None, eff_duration_years=None, dv01=None, cs01=None,
                convexity=None, wal_years=None, cf_life_years=None, residual_pct=None,
                residual_treatment=None, months_observed=None, months_projected=None)


def price_observed_row(r, path, curve, kind):
    """One security on its MEASURED path. Returns ``(record_fields, flag)``.

    ⭐ The timing measures and the tail report are always valid, so they are taken first. The
    spread and the sensitivities are guarded, and for an interest-only strip the assets layer
    RAISES rather than handing back a number with a known-wrong sign — so the blanks below
    are a consequence of that refusal, not a decision this driver makes.
    """
    bt, cpn = _num(r["gold_price"]), _num(r["net_coupon_pct"])
    wam = _num(r["wam_months"])
    max_m = int(wam) if wam and wam > 0 else None

    tail = obs.tail_report(path, cpn, kind, max_months=max_m)
    out = dict(
        wal_years=obs.weighted_average_life(path, cpn, kind, max_months=max_m),
        cf_life_years=obs.cash_flow_life(path, cpn, kind, max_months=max_m),
        residual_pct=tail["residual_pct"], residual_treatment=tail["treatment"],
        months_observed=tail["months_observed"], months_projected=tail["months_projected"],
    )
    try:
        spread = obs.implied_spread_bp(path, cpn, kind, bt, curve, max_months=max_m)
        one_bp = obs.dv01(path, cpn, kind, curve, spread, max_months=max_m)
        out.update(
            implied_spread_bp=spread,
            eff_duration_years=obs.duration(path, cpn, kind, curve, spread, max_months=max_m),
            dv01=one_bp,
            cs01=one_bp,          # identical with fixed flows; see the wrapper's docstring
            convexity=obs.convexity(path, cpn, kind, curve, spread, max_months=max_m),
        )
        return out, ""
    except obs.UnpublishableRiskMetric as exc:
        out.update(implied_spread_bp=None, eff_duration_years=None, dv01=None, cs01=None,
                   convexity=None)
        return out, str(exc)


def price_assumed_row(r, curve, wac, net, wam, bt):
    """One pool on the ASSUMED speed, through the same wrappers ``pool_risk.py`` uses.

    ⚠️ Every number here is in LEGACY units — ``wac``, ``net`` and the CPR in percent, the
    spread in basis points. That is the assets layer's contract, and the reason this driver
    does not touch the core.
    """
    kw = dict(net_coupon=net if net is not None else None)
    spread = pool.implied_spread_bp(wac, wam, BOOK_CPR_PCT, bt, curve, **kw)
    one_bp = pool.dv01(wac, wam, BOOK_CPR_PCT, curve, spread, **kw)
    return dict(
        implied_spread_bp=spread,
        eff_duration_years=pool.duration(wac, wam, BOOK_CPR_PCT, curve, spread, **kw),
        dv01=one_bp, cs01=one_bp,
        convexity=pool.convexity(wac, wam, BOOK_CPR_PCT, curve, spread, **kw),
        wal_years=pool.weighted_average_life(wac, wam, BOOK_CPR_PCT, net_coupon=net),
        cf_life_years=None, residual_pct=None, residual_treatment=None,
        months_observed=None, months_projected=None,
    ), ""


def price_tba_row(curve, terms, settle, bt):
    """One TBA FORWARD at the same assumed speed as the pools. Returns ``(fields, flag)``.

    ⭐⭐ **The only row shape in this table where ``dv01`` and ``cs01`` are different
    numbers.** Every other security here is discounted at ``z(t) + s``, so a parallel rate
    bump and a spread bump are the same arithmetic and the two columns hold one number twice
    (maximum difference exactly 0.0 across the 757 rows priced before these). A forward's
    spread sits in the NUMERATOR only — the financing leg carries the rate and not the spread
    — so its rate duration is shorter than its spread duration by EXACTLY the settlement lag.

    ⚠️ ``eff_duration_years``, ``dv01`` and ``convexity`` are therefore all taken from the
    RATE bump, and only ``cs01`` from the spread bump. A rate duration beside a spread
    convexity cannot be used together to approximate a move, and mixing them would be
    invisible in every other row of this table.
    """
    coupon, term = float(terms["coupon_pct"]), int(terms["term_months"])
    at = (coupon, term, BOOK_CPR_PCT, curve, settle)
    spread = tba.implied_spread_bp(coupon, term, BOOK_CPR_PCT, bt, curve, settle)
    rate_dur = tba.rate_duration(*at, spread)
    lag_days = round(settle * 365.0)
    return dict(
        implied_spread_bp=spread,
        eff_duration_years=rate_dur,
        dv01=tba.rate_dv01(*at, spread),
        cs01=tba.dv01(*at, spread),                  # ⭐ a DIFFERENT number for a forward
        convexity=tba.rate_convexity(*at, spread),
        wal_years=tba.weighted_average_life(coupon, term, BOOK_CPR_PCT),
        cf_life_years=None, residual_pct=None, residual_treatment=None,
        months_observed=None, months_projected=None,
    ), (f"forward on a generic {term // 12}-year pool, settling in {lag_days} days: dv01 is "
        f"the rate bump and cs01 the spread bump, and for a forward they differ by exactly "
        f"that lag ({tba.duration(*at, spread) - rate_dur:.4f}y)")


def main():
    data_dir = os.environ.get("FIP_DATA_DIR", "data")
    master = load_master_phase2(D.WB)
    pools, recon, counts = build_pool_universe(master, D.load_pool_terms(), VAL_DATE)
    # ⚠️ the price / market-value / custodian-duration columns live on the SECOND return
    # value, exactly as `pool_risk.py` merges them -- not on the universe frame.
    pools = pools.merge(recon, on="asset_id", how="left")
    hist = load_factor_history(data_dir)
    cus = pd.read_csv("outputs/mbs_data_check_2026-07-30.csv")[["asset_id", "cusip"]]
    pools = pools.merge(cus, on="asset_id", how="left")

    try:
        curve = ZeroCurve.from_currency(data_dir, "USD", VAL_DATE, freq="Monthly")
        curve_error = None
    except Exception as exc:                                     # noqa: BLE001
        curve, curve_error = None, str(exc)

    print(f"Tier-1 structured, Government MBS @ {VAL}")
    print(f"  universe {counts['rows']} rows -> {counts['unique']} securities")
    print(f"  factor paths in hand: {len(hist)}")
    print(f"  assumed speed for pools without a path: {BOOK_CPR_PCT}% CPR (measured)")

    records, named = [], {}
    for _, r in pools.iterrows():
        aid = r["asset_id"]
        base = dict(
            asset_id=aid, cusip=r.get("cusip"), isin=r.get("isin"),
            structure=r["structure"], desc_short=r.get("desc_short"),
            par_current_face=_num(r["par_value"]), bt=_num(r["gold_price"]),
            mv_base_usd=_num(r["gold_mkt_value"]),
            aq_custodian=_num(r["dur_eff_custodian"]),
            cpr_assumed_pct=None, cash_flow_kind=None, paydown_source=None,
            route=None, flag="",
        )
        bt, cpn = _num(r["gold_price"]), _num(r["net_coupon_pct"])
        path = factor_path(hist, r["cusip"], VAL_DATE) if pd.notna(r.get("cusip")) else []

        if curve is None:
            named[aid] = ("curve-blocked", _REASON["curve-blocked"])
            continue
        if bt is None or bt <= 0:
            named[aid] = ("no-price", _REASON["no-price"])
            continue

        # ---------------------------------------------------------- the measured path wins
        if len(path) >= 2 and path[0] and path[0] > 0:
            if cpn is None:
                named[aid] = ("no-coupon", _REASON["no-coupon"])
                continue
            kind = KIND_FOR_STRUCTURE.get(r["structure"], obs.AMORTISING)
            # ⚠️ A measured path can still fail to calibrate, and the two reasons are
            # different: cash flows that net to zero (nothing to discount) versus a price the
            # path cannot reach at any spread. Both are NAMED, never dropped and never
            # force-fitted -- the security keeps its price and market value either way.
            _mm = int(_num(r["wam_months"]) or 0) or None
            if abs(obs.calculated_price(path, cpn, kind, _ZeroCurve(), 0.0,
                                        max_months=_mm)) < 1e-12:
                named[aid] = ("observed-flows-sum-to-zero",
                              _REASON["observed-flows-sum-to-zero"])
                continue
            try:
                fields, flag = price_observed_row(r, path, curve, kind)
            except ValueError:
                named[aid] = ("observed-not-calibratable",
                              _REASON["observed-not-calibratable"])
                continue
            route = ("io-strip-prepayment-dominated" if kind == obs.INTEREST_ONLY
                     else f"observed-{kind.replace('_', '-')}")
            records.append({**base, **fields, "paydown_source": "observed-factor-path",
                            "cash_flow_kind": kind, "route": route, "flag": flag})
            continue
        if pd.notna(r.get("cusip")) and r["cusip"] in hist:
            named[aid] = ("dead-path", _REASON["dead-path"])
            continue

        # ---------------------------------------------------------- the forward, on its own route
        # ⚠️ A TBA is NOT a spot pool: its price is struck for a settlement date weeks out,
        # and pricing it as if it settled today drops that adjustment silently. The terms come
        # from the DESCRIPTION, because the master's maturity is wrong for a forward and its
        # income rate is 0.000 for three of them; `parse_tba_terms` owns that reading and
        # `pool_risk.py` makes the same call, so the two tables cannot disagree about what a
        # given forward is.
        if r["route"] == "tba-forward":
            terms = parse_tba_terms(r.get("desc_short"), r.get("desc_long"), cpn)
            missing = [k for k in TBA_REQUIRED_TERMS if terms[k] is None]
            if missing:
                named[aid] = ("tba-terms-unreadable",
                              _REASON["tba-terms-unreadable"] + ", ".join(missing)
                              + " and no other source carries it")
                continue
            try:
                settle = tba.settle_years(
                    VAL_DATE, tba.settlement_date(VAL_DATE, terms["settle_month"]))
            except ValueError as exc:
                # The holdings file is a 2009-03-31 snapshot; at a later control date these
                # April and May forwards have delivered and are no longer forwards.
                named[aid] = ("tba-already-settled", str(exc)[:200])
                continue
            try:
                fields, flag = price_tba_row(curve, terms, settle, bt)
            except ValueError as exc:
                named[aid] = ("tba-spread-not-solvable",
                              _REASON["tba-spread-not-solvable"] + str(exc)[:160])
                continue
            records.append({**base, **fields, "paydown_source": "tba-forward-generic-pool",
                            "cash_flow_kind": obs.AMORTISING, "route": "tba-forward",
                            "cpr_assumed_pct": BOOK_CPR_PCT, "flag": flag})
            continue

        # ---------------------------------------------------------- otherwise the pool engine
        wac, net, wam = _num(r["wac_pct"]), cpn, _num(r["wam_months"])
        if r["route"] != "pool" or wac is None:
            named[aid] = ("no-path-no-pool-terms", _REASON["no-path-no-pool-terms"])
            continue
        if wam is None or wam <= 0:
            named[aid] = ("pool-maturity-unavailable", _REASON["pool-maturity-unavailable"])
            continue
        if net is not None and net > wac:
            named[aid] = ("pool-coupon-inconsistent", _REASON["pool-coupon-inconsistent"])
            continue
        try:
            fields, flag = price_assumed_row(r, curve, wac, net, int(wam), bt)
        except ValueError as exc:
            named[aid] = ("calibration-failed", str(exc)[:120])
            continue
        records.append({**base, **fields, "paydown_source": "assumed-cpr",
                        "cash_flow_kind": obs.AMORTISING, "route": "pool-assumed-speed",
                        "cpr_assumed_pct": BOOK_CPR_PCT, "flag": flag})

    # ------------------------------------------------------------------ the named rows, carried
    for aid, (reason, text) in named.items():
        r = pools[pools.asset_id == aid].iloc[0]
        records.append(dict(
            asset_id=aid, cusip=r.get("cusip"), isin=r.get("isin"),
            structure=r["structure"], desc_short=r.get("desc_short"),
            par_current_face=_num(r["par_value"]), bt=_num(r["gold_price"]),
            mv_base_usd=_num(r["gold_mkt_value"]),
            aq_custodian=_num(r["dur_eff_custodian"]),
            paydown_source=None, cash_flow_kind=None, cpr_assumed_pct=None,
            route=reason, flag=text, **_blank_risk()))

    out = pd.DataFrame(records)
    out["aq_divergence"] = (out["eff_duration_years"] - out["aq_custodian"]).abs()
    out = out.sort_values(["paydown_source", "route", "asset_id"], na_position="last")
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    out.to_csv(OUT, index=False)

    # ⚠️ reconcile over SETS, not counts — a count can balance while the wrong securities
    # move. This RAISES when the cover is not exact, so a security cannot fall out silently.
    reconcile(
        candidates=list(pools["asset_id"]),
        priced=list(out.loc[out["paydown_source"].notna(), "asset_id"]),
        skipped=named,
    ).to_csv(DISPOSITION, index=False)

    priced = int(out["paydown_source"].notna().sum())
    print(f"\n  {len(out)} rows written to {OUT}")
    print(f"  with an amortising cash flow : {priced}")
    print(f"  named without one            : {len(out) - priced}")
    print("\n  by paydown source:")
    for src, g in out.groupby("paydown_source"):
        print(f"     {src:24s} {len(g):4d}")
    print("\n  by route:")
    for route, g in out.groupby("route"):
        sp = g["implied_spread_bp"].dropna()
        extra = (f"  spread median {sp.median():8.1f}bp" if len(sp) else "")
        print(f"     {route:34s} {len(g):4d}{extra}")
    a = out[(out.route.str.startswith("observed-amortising", na=False))]
    if len(a):
        print(f"\n  ** observed amortising: duration median {a.eff_duration_years.median():.2f}y "
              f"against the custodian's own {a.aq_custodian.median():.2f}y")
    return out


if __name__ == "__main__":
    main()
