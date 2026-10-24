"""Tier 1 for the rest of the securitised book — the 412 CMO, CMBS and asset-backed
securities, on their measured factor paths.

These were the last category in the portfolio with nothing behind them. Mario's 2026-10-23
delivery supplied a monthly factor history for 371 of them, which is the same input the 882
government mortgage holdings already run on, so they price the same way.

WHY A SEPARATE DRIVER AND A SEPARATE ARTIFACT
---------------------------------------------
``outputs/tier1_structured_2009-03-31.csv`` is a delivered, quoted artifact of **882 rows**.
Growing it to 1,294 would silently restate a number already in a client's hands. The two
populations also arrived from different pulls with different month alignment, so keeping the
records apart keeps each checkable against the delivery it came from.

⭐ **But the pricing is not duplicated.** ``price_observed_row`` is imported from
``tier1_structured``, so the two tables cannot disagree about how a measured path is priced —
the same argument that module makes for sharing ``parse_tba_terms`` with ``pool_risk``. The
reason texts are imported for the same reason: one security named in two dispositions should
be named in the same words.

WHAT THIS DRIVER DOES NOT DO
----------------------------
No assumed-CPR route and no TBA route. Both are Government-MBS shapes: these securities have
no pool WAC to fall back on and none of them is a forward. A security with no measured path
is **named**, never priced on an assumption borrowed from another book.

⚠️ **The month a factor label describes is read per security**, from
``data/factor_alignment.csv``. Most of this population does **not** carry the one-month shift
the government pools do, and 36 of them disagree with their own asset class — see
``docs/three_tier_method_explained_2026-10-06.md`` §3.17. Without that table 224 CMO tranches
would start a month out, silently, because a factor one month off is still a plausible factor.

Run: ``PYTHONPATH=src python scripts/tier1_securitized.py``
"""

import datetime
import os
import sys

import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pool_risk as D                                               # noqa: E402
from curves.zero_curve import ZeroCurve                             # noqa: E402
from dataio.coupon_structure import (load_coupon_structure,         # noqa: E402
                                     rate_behaviour)
from dataio.dispositions import reconcile                           # noqa: E402
from dataio.factor_history import (FACTOR_FILE_412, factor_path,    # noqa: E402
                                   load_factor_alignment, load_factor_history)
from dataio.phase2 import (SECURITIZED_CLASSES, build_pool_universe,  # noqa: E402
                           load_master_phase2)
from pricer.assets.securitized import observed as obs               # noqa: E402
# ⭐ The pricing core, the blank-risk shape and the reason wording all come from the
# Government-MBS driver so the two artifacts stay comparable line for line.
from tier1_structured import (KIND_FOR_STRUCTURE, _REASON, _ZeroCurve,  # noqa: E402
                              _blank_risk, _num, price_observed_row)

VAL = os.environ.get("FIP_VAL_DATE", "2009-03-31")
VAL_DATE = datetime.date.fromisoformat(VAL)
OUT = os.environ.get("FIP_OUT", f"outputs/tier1_securitized_{VAL}.csv")
DISPOSITION = f"outputs/tier1_securitized_disposition_{VAL}.csv"

#: The one reason this book needs that the government book does not: there, a pool without a
#: path still has a WAC to fall back on, so the reason names both. Here there is no fallback.
NO_PATH = ("no-factor-path",
           "no monthly factor history for this security, so there is no measured repayment "
           "profile and no pool-level assumption that could stand in for one")

#: ⚠️ The government book's text quotes a **1.77-year** bound on the interest leg. That bound
#: was measured on *its* paths — p90 interest share times p90 interest life — and it is NOT
#: transferred here. Letting this population borrow it would be the weaker claim taking the
#: stronger one's number. Measuring the equivalent for this book is a named follow-up.
_COUPON_NOTE = (
    "coupon-structure: Bloomberg reports {kind}; this duration assumes the coupon stays at "
    "the custodian's valuation-date level. Principal timing comes from the measured factor "
    "path, so only the interest leg is affected -- but the 1.77y bound measured on the "
    "government mortgage book does NOT apply to this population and no equivalent has been "
    "measured for it yet."
)


def _cusip_from_isin(isin) -> str:
    """The 9-character CUSIP inside a US ISIN, or ``""``.

    ⚠️ Only for a ``US`` ISIN, where the national number IS the CUSIP. Every one of the 371
    securities with a factor history satisfies that, and :func:`main` asserts that every
    delivered path finds a security, so a silent mapping failure cannot pass.
    """
    s = "" if isin is None or pd.isna(isin) else str(isin).strip().upper()
    return s[2:11] if s.startswith("US") and len(s) >= 11 else ""


def main() -> int:
    data_dir = os.environ.get("FIP_DATA_DIR", "data")
    master = load_master_phase2(D.WB)
    pools, recon, counts = build_pool_universe(master, None, VAL_DATE,
                                               classes=SECURITIZED_CLASSES)
    pools = pools.merge(recon, on="asset_id", how="left")
    pools["cusip"] = [_cusip_from_isin(v) for v in pools["isin"]]

    hist = load_factor_history(data_dir, FACTOR_FILE_412)
    align = load_factor_alignment(data_dir)

    reachable = {c for c in pools["cusip"] if c and c in hist}
    orphan = sorted(set(hist) - reachable)
    if orphan:
        print(f"REFUSING: {len(orphan)} delivered factor paths reach no security in the "
              f"universe, e.g. {orphan[:5]}")
        return 2

    try:
        curve = ZeroCurve.from_currency(data_dir, "USD", VAL_DATE, freq="Monthly")
    except Exception as exc:                                        # noqa: BLE001
        curve = None
        print(f"  USD curve unavailable: {type(exc).__name__}")

    print(f"Tier-1 securitised, the rest of the structured book @ {VAL}")
    print(f"  universe {counts['rows']} rows -> {counts['unique']} securities")
    print(f"  factor paths in hand: {len(hist)}")

    records, named = [], {}
    for _, r in pools.iterrows():
        aid = r["asset_id"]
        base = dict(
            asset_id=aid, cusip=r.get("cusip") or None, isin=r.get("isin"),
            asset_class=r.get("asset_class"), structure=r["structure"],
            desc_short=r.get("desc_short"),
            par_current_face=_num(r["par_value"]), bt=_num(r["gold_price"]),
            mv_base_usd=_num(r["gold_mkt_value"]),
            aq_custodian=_num(r["dur_eff_custodian"]),
            cash_flow_kind=None, paydown_source=None, route=None, flag="",
        )
        bt, cpn = _num(r["gold_price"]), _num(r["net_coupon_pct"])
        path = factor_path(hist, r["cusip"], VAL_DATE, align) if r["cusip"] else []

        if curve is None:
            named[aid] = ("curve-blocked", _REASON["curve-blocked"])
            continue
        if not path:
            named[aid] = NO_PATH
            continue
        if bt is None or bt <= 0:
            named[aid] = ("no-price", _REASON["no-price"])
            continue
        if cpn is None:
            named[aid] = ("no-coupon", _REASON["no-coupon"])
            continue
        if len(path) < 2 or not path[0] or path[0] <= 0:
            named[aid] = ("dead-path", _REASON["dead-path"])
            continue

        kind = KIND_FOR_STRUCTURE.get(r["structure"], obs.AMORTISING)
        wam = _num(r["wam_months"])
        max_m = int(wam) if wam and wam > 0 else None
        if abs(obs.calculated_price(path, cpn, kind, _ZeroCurve(), 0.0,
                                    max_months=max_m)) < 1e-12:
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

    for aid, (reason, text) in named.items():
        r = pools[pools.asset_id == aid].iloc[0]
        records.append(dict(
            asset_id=aid, cusip=r.get("cusip") or None, isin=r.get("isin"),
            asset_class=r.get("asset_class"), structure=r["structure"],
            desc_short=r.get("desc_short"),
            par_current_face=_num(r["par_value"]), bt=_num(r["gold_price"]),
            mv_base_usd=_num(r["gold_mkt_value"]),
            aq_custodian=_num(r["dur_eff_custodian"]),
            paydown_source=None, cash_flow_kind=None, route=reason, flag=text,
            **_blank_risk()))

    out = pd.DataFrame(records)
    out["aq_divergence"] = (out["eff_duration_years"] - out["aq_custodian"]).abs()

    # ⚠️ ADDITIVE and placed after every number: one column appended, one text column
    # extended, no arithmetic touched. A missing `data/coupon_structure.csv` leaves the
    # column blank and changes nothing else.
    structure = load_coupon_structure()
    out["coupon_structure"] = out["asset_id"].map(
        lambda a: (structure.get(a) or {}).get("coupon_type") or "")
    moves = out["coupon_structure"].map(
        lambda kind: bool(kind) and rate_behaviour(kind) == "rate-sensitive")
    disclose = moves & out["eff_duration_years"].notna()
    for i in out.index[disclose]:
        text = _COUPON_NOTE.format(kind=out.at[i, "coupon_structure"].upper())
        out.at[i, "flag"] = " ".join(x for x in (out.at[i, "flag"], text) if x)

    out = out.sort_values(["paydown_source", "route", "asset_id"], na_position="last")
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    out.to_csv(OUT, index=False)

    # ⚠️ reconcile over SETS, not counts — a count can balance while the wrong securities
    # move. This RAISES when the cover is not exact.
    reconcile(
        candidates=list(pools["asset_id"]),
        priced=list(out.loc[out["paydown_source"].notna(), "asset_id"]),
        skipped=named,
    ).to_csv(DISPOSITION, index=False)

    priced = int(out["paydown_source"].notna().sum())
    print(f"  wrote {OUT}: {len(out)} rows = {priced} priced + {len(named)} named")
    print(f"  wrote {DISPOSITION}")
    for route, g in out[out["paydown_source"].notna()].groupby("route"):
        spread = g["implied_spread_bp"].dropna()
        tail = f"  spread median {spread.median():8.1f}bp" if len(spread) else \
               "  spread withheld"
        print(f"     {route:38s} {len(g):4d}{tail}")
    for reason, g in out[out["paydown_source"].isna()].groupby("route"):
        print(f"     {reason:38s} {len(g):4d}")
    a = out[out["paydown_source"].notna()].dropna(subset=["eff_duration_years",
                                                          "aq_custodian"])
    if len(a):
        print(f"\n  ** duration median {a.eff_duration_years.median():.2f}y against the "
              f"custodian's own {a.aq_custodian.median():.2f}y")
    print(f"  ** disclosed moving coupon on {int(disclose.sum())} priced rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
