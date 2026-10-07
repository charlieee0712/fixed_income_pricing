"""Tier-1 driver: an amortising, market-calibrated spread and risk for the Government-MBS book.

**What this produces.** One row for **every** one of the 882 Government Mortgage-Backed
securities, of which **861** carry an amortising cash flow and the remaining 21 are named.
Nothing else in the portfolio moves and no existing artifact is touched.

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

===========================  =====  ===================================================
``paydown_source``             n    where the balance schedule comes from
===========================  =====  ===================================================
``observed-factor-path``       376  :mod:`pricer.core.pricing.observed_paydown` — the
                                    MEASURED monthly factor history from Bloomberg
``assumed-cpr``                458  :mod:`pricer.assets.securitized.pool` — level-pay at
                                    :data:`BOOK_CPR_PCT`
(named, no numbers)             51  3 degenerate paths, 29 TBA forwards whose settlement
                                    this table does not model, 19 with neither a path nor a
                                    usable pool WAC
===========================  =====  ===================================================

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
* ``outputs/tier1_structured_<date>.csv``              882 rows
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
from dataio.phase2 import build_pool_universe, load_master_phase2  # noqa: E402
# ⚠️ Through the ASSETS layer, never the core. That layer owns the percent/decimal
# boundary and the one refusal; reaching past it into the core produced a calibrated spread
# of 46,478 bp on 487 pools -- a 465% spread, from passing 6.000 where 0.06000 was wanted.
from pricer.assets.securitized import observed as obs  # noqa: E402
from pricer.assets.securitized import pool  # noqa: E402

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
    "tba-forward-settlement-not-modelled":
        "a TBA is a forward on a GENERIC pool: its price carries a settlement adjustment that "
        "assets/securitized/tba.py applies and this table does not model. Pricing it as a "
        "spot pool would drop that correction silently, so it is named here and its spread is "
        "taken from pool_risk_<date>.csv, which does apply it",
}


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

        # ---------------------------------------------------------- otherwise the pool engine
        # ⚠️ A TBA is NOT a spot pool. Its price embeds a forward settlement that
        # `assets/securitized/tba.py` adjusts for and this table does not model, so it is
        # named rather than priced as if it settled today.
        if r["route"] == "tba-forward":
            named[aid] = ("tba-forward-settlement-not-modelled",
                          _REASON["tba-forward-settlement-not-modelled"])
            continue
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
