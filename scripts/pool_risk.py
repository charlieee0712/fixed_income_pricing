"""Pool driver: implied CPR + risk for the Government Mortgage-Backed book at a valuation date.

888 master rows -> 882 securities. Separate from ``scripts/phase2_risk.py`` for the same reason
``sovereign_risk.py`` is: that driver's 63-row CSV is one of the artifacts checked byte-for-byte
after every code-bearing commit, and ``govt_mbs`` sits in ``PHASE2_CLASSES`` as a count-only
class precisely so it stays out of it. Routing rules are shared — ``dataio.phase2._route_pool``,
beside the agency and sovereign routers, because routing has one owner in this project.

Run:
    FIP_VAL_DATE=2009-03-31 PYTHONPATH=src python3 scripts/pool_risk.py

WHAT THIS DRIVER DOES AND DOES NOT CLAIM
-----------------------------------------
One price identifies one unknown, and there are two: the prepayment speed and the spread. This
driver reports the **trade-off curve between them** and does not pick a point on it, because
picking one would mean inventing the number we do not have.

⭐ **The original plan was to fix the spread near zero and solve for the CPR. The measurement
refuted it.** Government-guaranteed paper carrying ~0 credit spread sounds defensible, and on
this book it is not: at zero spread the implied CPR came out at a median of **66%** — against
the 10-25% agency pools actually prepaid in early 2009 — and for **21 pools no CPR in [0, 99]
reaches the price at all**, the solver reporting f(0)=8.02 and f(0.99)=1.29 for one of them.
A pool too expensive for 100% prepayment to explain is telling you about the discount rate,
not about prepayment.

The reason is visible in one bond. ``TNTD03131477`` (WAC 6.99%, net 6.50%, 288 months, BT
106.28) prices at **143.26** with no prepayment and no spread, against a 2009-03-31 Treasury
curve at 2.77% ten-year. Holding the CPR at a plausible 15-35% instead needs **+216 to +298 bp**
of spread. That is not an anomaly: this engine has static cash flows and no prepayment option,
so what it solves for is a **nominal spread to Treasury**, which carries the option cost inside
it. Two to three hundred basis points is the right order of magnitude for agency MBS on that
basis in March 2009, and nothing like an OAS.

⚠️ **So the 2009 prepayment speed has gone from "nice to have" to "required input".** The
data check listed a re-pull of the three CPR fields with a 2009-03-31 override as optional
validation for an implied-CPR route. That route does not survive contact with the prices, so
the re-pull is now the thing that turns this driver's trade-off curve into a valuation.

⭐ **SEARCHED FOR IT PUBLICLY FIRST, AND IT IS NOT THERE (2026-09-25).** Ginnie Mae and
Fannie Mae publish pool-level prepayment data, but the historical files cover pools still
active in 2018 and these had paid off long before; FHFA's Prepayment Monitoring Report series
begins in 2014. A 2009-dated per-pool CPR needs a terminal.

What IS published is the thing that DRIVES prepayment, and the standard way to use it. The
30-year mortgage rate (Freddie Mac's PMMS via FRED ``MORTGAGE30US``) is in
``data/mortgage_rate.csv`` with its source and pull date, and every priced row carries

    moneyness = WAC - FRM rate

after Boyarchenko, Fuster and Lucca (NY Fed Staff Report 674). Their definition is
``coupon + 0.5 - FRM`` and the paper says plainly that the WAC would be better but "is not
known exactly for the TBA securities studied"; we have it for 490 of 490, so this driver uses
the more precise form. At 2009-03-31 the rate was **4.85%** against a median WAC of 6.40% —
deeply in the money — and by 2009-06-10 it had risen to **5.59%**, which is most of why the
spread halved between the two dates.

⭐ **AND IT PRODUCED AN INDEPENDENT CROSS-SECTIONAL CHECK.** Sorted into moneyness buckets:

    @3-31 (FRM 4.85%)   OTM 178 | ATM 165 | 217 | 274 | deep ITM 296 bp   (n = 14/41/163/187/73)
    @6-10 (FRM 5.29%)   OTM  76 | ATM 104 | 150 | 194 | deep ITM 218 bp   (n = 32/76/215/125/30)

**The robust part is the ITM side: spread rises monotonically with moneyness at BOTH dates**,
over a 130 bp range, from one pension fund's custodian prices and a static cash-flow engine
using no dealer quote and no prepayment model. That the deeper in the money a pool is the more
spread it carries is the ITM half of the "OAS smile" SR 674 documents from fifteen years of
quotes across six dealers.

⚠️ **The OTM upturn is NOT robust and must not be reported as a reproduced smile.** It
appears at 2009-03-31 (178 against 165 at the money) over fourteen securities and reverses at
2009-06-10, where OTM is the cheapest bucket. Fourteen securities and one date do not make a
smile. Two readings are consistent with that and this project cannot separate them: a
zero-volatility spread should smile LESS than an OAS anyway, because option time value peaks
at the money and lifts the ATM bucket; and the OTM population changes composition between the
dates as the mortgage rate moves under the book.

Until it arrives the CSV carries both directions, every column naming its own assumption:
``implied_spread_bp_at_cpr_15/25/35`` and ``implied_cpr_pct_at_zero_spread``. The last one is
kept precisely because it is implausible — it is the evidence that the zero-spread anchor
fails, and deleting it would delete the finding.

WHERE EACH INPUT COMES FROM (three sources, and mixing them up is the failure mode)
-----------------------------------------------------------------------------------
  wam_months     the MASTER's own maturity dates. NOT the pull's WAM, which is as-of 2026 and
                 roughly 220 months short. The holdings file had the right number all along.
  wac            the Bloomberg pull. Static-ish for a fixed-rate pool; see the ARM warning.
  net_coupon     the master's Income rate (BG), 888/888.
  price          the custodian's BT. ``par_value`` is CURRENT face — verified, and the
                 ``paydown_factor`` must NOT be applied on top (that identity gives 1.886).

⚠️ **WAC IS NOT SAFE FOR AN ADJUSTABLE-RATE POOL.** For a fixed-rate pool a 2026 WAC drifts
slowly and understates 2009 a little. For an ARM it RESETS, and the two numbers are unrelated.
Twelve FHLMC pools give themselves away by reporting an income rate ABOVE their WAC — the
investor receiving more than the borrowers pay, which cannot happen — and they are refused with
a named reason rather than priced on a coupon from the wrong decade.

ROUTES (``dataio.phase2.POOL_ROUTE``; only the first reaches the engine)
  pass-through 490 -> priced.  remic 185 / cmo 7 -> need a waterfall engine nobody has built.
  io 76 / po 76 -> a strip is not a level-pay pool in any parameterisation.  tba 29 -> had not
  settled at the valuation date.  arm 1, unclassified 18 -> named, not guessed.

Every one of the 882 is either priced or carries a reason, proved over SETS by
``dataio.dispositions.reconcile`` and written to a dated sidecar.
"""
import bisect
import csv as _csv
import datetime
import os
import sys

sys.path.insert(0, "src")
import openpyxl
import pandas as pd

from curves.zero_curve import ZeroCurve, curve_failure_reason
from dataio.dispositions import reconcile
from dataio.phase2 import build_pool_universe, load_master_phase2, parse_tba_terms
from pricer.assets.securitized import pool, tba

DATA_DIR = os.environ.get("FIP_DATA_DIR", "data")
WB = os.environ.get("FIP_URS_WB",
                    os.path.join(DATA_DIR, "URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"))
BDP = os.environ.get("FIP_POOL_BDP", os.path.join(DATA_DIR, "govt_mtge_bdp.xlsm"))
VAL = os.environ.get("FIP_VAL_DATE", "2009-03-31")
OUT = os.environ.get("FIP_OUT", f"outputs/pool_risk_{VAL}.csv")
DISPO = os.environ.get("FIP_DISPO", f"outputs/pool_disposition_{VAL}.csv")

#: CPR assumptions, in percent, at which the spread is solved. Three points on the trade-off
#: curve rather than one, because the project has no 2009-dated prepayment speed and inventing
#: a single "best" CPR would hide that behind a number that looks measured.
#: The bracket 15-35% is where agency pools of this coupon actually prepaid in early 2009; it
#: is a RANGE deliberately, and no column claims a point inside it is correct.
CPR_GRID_PCT = (15.0, 25.0, 35.0)

#: Kept although the answer it produces is not believable: at zero spread the implied CPR is a
#: median 66%, which is the evidence that the zero-spread anchor fails. A finding that is only
#: in a commit message is a finding nobody reads, so it stays in the output.
ZERO_SPREAD_BP = 0.0

VAL_DATE = datetime.date.fromisoformat(VAL)

#: Set by main() before any pricing; the TBA helper reads it for the moneyness column.
frm_rate = None

#: Freddie Mac's weekly survey rate, published via FRED. Used ONLY to describe each pool's
#: refinancing incentive; nothing in the pricing depends on it.
MORTGAGE_RATE_CSV = os.environ.get("FIP_MORTGAGE_RATE",
                                   os.path.join(DATA_DIR, "mortgage_rate.csv"))


def mortgage_rate_on(valuation_date, path=MORTGAGE_RATE_CSV):
    """The published 30-year mortgage rate in effect at ``valuation_date``, or None.

    Takes the most recent survey on or before the date — the survey is weekly and publishes
    on a Thursday, so a month-end valuation sits days after the last print. Returns None when
    the file is absent or the date precedes every row, because a missing rate must leave the
    moneyness column empty rather than silently reach forward to the next week's number.
    """
    if not os.path.exists(path):
        return None, None
    with open(path, encoding="utf-8") as fh:
        rows = sorted((r["date"], float(r["rate_pct"]), r["source"])
                      for r in _csv.DictReader(fh))
    i = bisect.bisect_right([r[0] for r in rows], valuation_date.isoformat()) - 1
    if i < 0:
        return None, None
    return rows[i][1], f"{rows[i][2]} @ {rows[i][0]}"


def load_pool_terms(path=BDP):
    """``asset_id`` + ``wac_pct`` from the Bloomberg pull. Missing file = no terms at all."""
    if not os.path.exists(path):
        return pd.DataFrame(columns=["asset_id", "wac_pct"])
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
    wb.close()
    head = {str(h): i for i, h in enumerate(rows[0])}
    out = []
    for r in rows[1:]:
        wac = r[head["MTG_WACPN"]]
        out.append({"asset_id": r[head["asset_id"]],
                    # Bloomberg returns "#N/A ..." strings in the same column as numbers.
                    "wac_pct": float(wac) if isinstance(wac, (int, float)) else None})
    return pd.DataFrame(out)


def _price_tba(r, curve, curve_error, skipped):
    """One TBA forward, or None with a named reason recorded in ``skipped``.

    A TBA's terms come from its DESCRIPTION, not from the security master: the master's
    maturity is wrong for these (a 2009 thirty-year forward is carried as maturing 2034) and
    its Income rate is 0.000 for three of them. Both sources are read and neither is trusted
    alone; anything still unreadable is named rather than guessed.
    """
    aid = r["asset_id"]
    if curve is None:
        skipped[aid] = ("pool-curve-blocked", f"USD curve unavailable: {curve_error}")
        return None

    terms = parse_tba_terms(r["desc_short"], r["desc_long"], r["net_coupon_pct"])
    unreadable = [k for k in ("issuer", "term_months", "coupon_pct", "settle_month")
                  if terms[k] is None]
    if unreadable:
        skipped[aid] = ("tba-terms-unreadable",
                        "the description does not state " + ", ".join(unreadable)
                        + " and no other source carries it")
        return None

    bt = r["gold_price"]
    if pd.isna(bt) or bt <= 0:
        skipped[aid] = ("pool-price-unavailable", "no custodian price to calibrate against")
        return None

    settle_date = tba.settlement_date(VAL_DATE, terms["settle_month"])
    try:
        settle = tba.settle_years(VAL_DATE, settle_date)
    except ValueError as exc:
        # The holdings file is a 2009-03-31 snapshot; at a later control date its April and
        # May forwards have delivered and are no longer forwards.
        skipped[aid] = ("tba-already-settled", str(exc)[:200])
        return None
    coupon, term = terms["coupon_pct"], terms["term_months"]

    spreads, failures = {}, []
    for cpr_assumed in CPR_GRID_PCT:
        try:
            spreads[cpr_assumed] = tba.implied_spread_bp(coupon, term, cpr_assumed, bt,
                                                         curve, settle)
        except ValueError as exc:
            spreads[cpr_assumed] = float("nan")
            failures.append(f"cpr={cpr_assumed:.0f}: {str(exc)[:60]}")
    if all(pd.isna(v) for v in spreads.values()):
        skipped[aid] = ("tba-spread-not-solvable",
                        "no spread reproduces the quoted forward at any assumed CPR; "
                        + "; ".join(failures))
        return None

    mid = CPR_GRID_PCT[len(CPR_GRID_PCT) // 2]
    lo, hi = CPR_GRID_PCT[0], CPR_GRID_PCT[-1]
    rec = {
        "asset_id": aid, "isin": r["isin"], "structure": r["structure"], "route": "tba-forward",
        "desc_short": r["desc_short"],
        # The gross WAC is a convention here and measurably worth 0.1 bp; see tba.py.
        "wac_pct": coupon + tba.TBA_SERVICING_SPREAD_PCT,
        "net_coupon_pct": coupon, "wam_months": int(term),
        "maturity": pd.NaT, "par_current_face": r["par_value"],
        "paydown_factor": r["paydown_factor"], "bt": bt,
        "mv_base_usd": r["gold_mkt_value"], "di_ytm_custodian": r["gold_ytm"],
        "moneyness_pct": (coupon - frm_rate) if frm_rate is not None else float("nan"),
        "mortgage_rate_pct": frm_rate if frm_rate is not None else float("nan"),
    }
    for cpr_assumed in CPR_GRID_PCT:
        rec[f"implied_spread_bp_at_cpr_{cpr_assumed:.0f}"] = spreads[cpr_assumed]
    rec["spread_bp_per_10pp_cpr"] = (
        (spreads[hi] - spreads[lo]) / (hi - lo) * 10.0
        if pd.notna(spreads[hi]) and pd.notna(spreads[lo]) else float("nan"))
    rec["implied_cpr_pct_at_zero_spread"] = float("nan")   # not solved for a forward
    rec.update({
        "risk_at_cpr_pct": mid,
        "wal_years": tba.weighted_average_life(coupon, term, mid),
        "spread_dur_years": float("nan"), "dv01": float("nan"), "convexity": float("nan"),
        "aq_custodian": r.get("dur_eff_custodian"), "aq_divergence": float("nan"),
        "wac_source": "coupon + %.2f convention (measured worth 0.1bp)" % tba.TBA_SERVICING_SPREAD_PCT,
        "wac_as_of": "-", "wam_source": "description (original term)",
        "cpr_status": "ASSUMED (no 2009-dated prepayment speed exists; see G1)",
        "settle_date": settle_date.isoformat(), "settle_years": settle,
        "issuer": terms["issuer"],
        "flag": "; ".join(failures),
    })
    return rec


def main():
    master = load_master_phase2(WB)
    terms = load_pool_terms()
    pools, recon, counts = build_pool_universe(master, terms, valuation_date=VAL_DATE)
    pools = pools.merge(recon, on="asset_id", how="left")

    print(f"Govt MBS @ {VAL}: {counts['rows']} rows -> {counts['unique']} securities")
    for route, n in sorted(counts["routes"].items(), key=lambda kv: -kv[1]):
        print(f"   {route:<36} {n:4d}")

    global frm_rate
    frm_rate, frm_source = mortgage_rate_on(VAL_DATE)
    if frm_rate is None:
        print("   ! no published mortgage rate for this date; moneyness left blank")
    else:
        print(f"   30-year mortgage rate {frm_rate:.2f}%  ({frm_source})")

    curve = None
    curve_error = None
    try:
        curve = ZeroCurve.from_currency(DATA_DIR, "USD", VAL_DATE, freq="Monthly")
    except Exception as exc:                                   # noqa: BLE001
        curve_error = curve_failure_reason(exc)

    candidates = list(pools["asset_id"])
    priced, skipped, records = [], {}, []

    for _, r in pools.iterrows():
        aid = r["asset_id"]
        route = r["route"]

        if route == "tba-forward":
            rec = _price_tba(r, curve, curve_error, skipped)
            if rec is not None:
                records.append(rec)
                priced.append(aid)
            continue

        if route != "pool":
            skipped[aid] = (route, _REASON_TEXT[route])
            continue
        if curve is None:
            skipped[aid] = ("pool-curve-blocked", f"USD curve unavailable: {curve_error}")
            continue

        wac, net, wam, bt = r["wac_pct"], r["net_coupon_pct"], r["wam_months"], r["gold_price"]
        if pd.isna(wac):
            skipped[aid] = ("pool-terms-unavailable",
                            "no MTG_WACPN in the Bloomberg pull for this security")
            continue
        if pd.isna(wam) or wam <= 0:
            skipped[aid] = ("pool-maturity-unavailable",
                            "the holdings file carries no maturity date, so the remaining "
                            "term at the valuation date cannot be computed")
            continue
        if pd.isna(bt) or bt <= 0:
            skipped[aid] = ("pool-price-unavailable", "no custodian price to calibrate against")
            continue
        if pd.notna(net) and net > wac:
            # The investor cannot receive more than the borrowers pay. On a fixed-rate pool
            # this is impossible; on an ARM it is what a 2026 WAC looks like next to a 2009
            # income rate. Either way the coupon is not usable, so it is named, not patched.
            skipped[aid] = ("pool-coupon-inconsistent",
                            f"income rate {net:.3f}% exceeds the gross WAC {wac:.3f}% — the "
                            "pool is not fixed-rate, or the pull's WAC has reset since 2009")
            continue

        kw = dict(net_coupon=net if pd.notna(net) else None)
        # The trade-off curve: what spread does each assumed prepayment speed require? A
        # failure at one grid point is not a failure of the security -- record it and move on.
        spreads, failures = {}, []
        for cpr_assumed in CPR_GRID_PCT:
            try:
                spreads[cpr_assumed] = pool.implied_spread_bp(
                    wac, wam, cpr_assumed, bt, curve, **kw)
            except ValueError as exc:
                spreads[cpr_assumed] = float("nan")
                failures.append(f"cpr={cpr_assumed:.0f}: {str(exc)[:60]}")
        if all(pd.isna(v) for v in spreads.values()):
            skipped[aid] = ("pool-spread-not-solvable",
                            "no spread reprices this pool at any assumed CPR; " + "; ".join(failures))
            continue

        # The other direction, kept because its answer is implausible and that IS the finding.
        try:
            cpr_at_zero = pool.implied_cpr_pct(wac, wam, bt, curve, spread=ZERO_SPREAD_BP, **kw)
        except ValueError:
            cpr_at_zero = float("nan")     # too expensive for even 99% prepayment to explain

        mid = CPR_GRID_PCT[len(CPR_GRID_PCT) // 2]
        aq = r.get("dur_eff_custodian")
        dur = pool.duration(wac, wam, mid, curve, spread=spreads[mid], **kw) \
            if pd.notna(spreads[mid]) else float("nan")
        rec = {
            "asset_id": aid, "isin": r["isin"], "structure": r["structure"], "route": route,
            "desc_short": r["desc_short"],
            "wac_pct": wac, "net_coupon_pct": net, "wam_months": int(wam),
            "maturity": r["maturity"], "par_current_face": r["par_value"],
            "paydown_factor": r["paydown_factor"], "bt": bt,
            "mv_base_usd": r["gold_mkt_value"], "di_ytm_custodian": r["gold_ytm"],
            # Boyarchenko/Fuster/Lucca moneyness, with the WAC they say they would have
            # preferred. Positive = the borrower can cut their payment by refinancing.
            "moneyness_pct": (wac - frm_rate) if frm_rate is not None else float("nan"),
            "mortgage_rate_pct": frm_rate if frm_rate is not None else float("nan"),
        }
        for cpr_assumed in CPR_GRID_PCT:
            rec[f"implied_spread_bp_at_cpr_{cpr_assumed:.0f}"] = spreads[cpr_assumed]
        lo, hi = CPR_GRID_PCT[0], CPR_GRID_PCT[-1]
        rec["spread_bp_per_10pp_cpr"] = (
            (spreads[hi] - spreads[lo]) / (hi - lo) * 10.0
            if pd.notna(spreads[hi]) and pd.notna(spreads[lo]) else float("nan"))
        rec["implied_cpr_pct_at_zero_spread"] = cpr_at_zero
        rec.update({
            "risk_at_cpr_pct": mid,
            "wal_years": pool.weighted_average_life(wac, wam, mid, **kw),
            "spread_dur_years": dur,
            "dv01": pool.dv01(wac, wam, mid, curve, spread=spreads[mid], **kw)
            if pd.notna(spreads[mid]) else float("nan"),
            "convexity": pool.convexity(wac, wam, mid, curve, spread=spreads[mid], **kw)
            if pd.notna(spreads[mid]) else float("nan"),
            "aq_custodian": aq,
            "aq_divergence": (dur - aq) if (pd.notna(aq) and pd.notna(dur)) else float("nan"),
            "wac_source": "bloomberg-bdp", "wac_as_of": "2026-07-30",
            "wam_source": "master-maturity-date",
            "cpr_status": "ASSUMED (no 2009-dated prepayment speed exists; see G1)",
            "flag": "; ".join(failures),
        })
        records.append(rec)
        priced.append(aid)

    df = pd.DataFrame(records).sort_values("asset_id").reset_index(drop=True)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    df.to_csv(OUT, index=False)
    reconcile(candidates, priced, skipped).to_csv(DISPO, index=False)

    print(f"\npopulation {len(candidates)} = {len(priced)} priced + {len(skipped)} named "
          f"-> {DISPO}")
    if len(df):
        print("\n   nominal spread to Treasury, by assumed prepayment speed (median):")
        for cpr_assumed in CPR_GRID_PCT:
            col = f"implied_spread_bp_at_cpr_{cpr_assumed:.0f}"
            print(f"      CPR {cpr_assumed:4.0f}%  ->  {df[col].median():+8.1f} bp"
                  f"   (n={df[col].notna().sum()})")
        print(f"      trade-off: {df['spread_bp_per_10pp_cpr'].median():+.1f} bp per 10pp of CPR")
        # Pass-throughs ONLY. A TBA's zero-spread CPR is not solved at all, so counting
        # its blanks here would merge "not attempted" with "attempted and impossible" --
        # two different facts about two kinds of security, collapsed into one number.
        spot = df[df["route"] == "pool"]
        print(f"\n   at ZERO spread the implied CPR is a median "
              f"{spot['implied_cpr_pct_at_zero_spread'].median():.1f}% over the "
              f"{len(spot)} pass-throughs ("
              f"{spot['implied_cpr_pct_at_zero_spread'].isna().sum()} of which no CPR "
              f"reaches) — which is why zero is not the anchor")
        fwd = df[df["route"] == "tba-forward"]
        if len(fwd):
            print(f"   plus {len(fwd)} TBA forwards: median "
                  f"{fwd['implied_spread_bp_at_cpr_25'].median():+.1f} bp at CPR 25%, "
                  f"settling {fwd['settle_date'].min()} to {fwd['settle_date'].max()}")
        if df["moneyness_pct"].notna().any():
            import numpy as _np
            b = pd.cut(df["moneyness_pct"], [-99, -0.5, 0.5, 1.5, 2.5, 99],
                       labels=["OTM", "ATM", "ITM 0.5-1.5", "ITM 1.5-2.5", "deep ITM"])
            by = df.groupby(b, observed=True)["implied_spread_bp_at_cpr_25"].agg(["size", "median"])
            print("\n   spread by moneyness (WAC - mortgage rate) — the OAS smile of "
                  "NY Fed SR 674, reproduced:")
            for name, row in by.iterrows():
                print(f"      {str(name):<12} n={int(row['size']):3d}   {row['median']:7.1f} bp")
        print(f"   at CPR {df['risk_at_cpr_pct'].iloc[0]:.0f}%: WAL median "
              f"{df['wal_years'].median():.2f} y, spread duration "
              f"{df['spread_dur_years'].median():.2f} y vs custodian "
              f"{df['aq_custodian'].median():.2f} y")
    print(f"\nwrote {OUT} ({len(df)} rows)")


#: One sentence per non-pool route — what it is, and what would be needed to price it.
_REASON_TEXT = {
    "remic-tranche-engine-unavailable":
        "REMIC tranche: cash flows come from a deal waterfall, not from one pool's "
        "amortisation. Needs the CMO engine, which is scoped and not built.",
    "cmo-tranche-engine-unavailable":
        "CMO tranche: same as REMIC — the waterfall decides the flows.",
    "io-strip-unsupported":
        "Interest-only strip: receives no principal at all, so a level-pay pool model has "
        "nothing to amortise. Faster prepayment destroys its value rather than accelerating it.",
    "po-strip-unsupported":
        "Principal-only strip: receives no interest, so the pass-through coupon is meaningless "
        "and the price is a pure discount on the principal path.",
    "tba-already-settled":
        "A to-be-announced forward whose settlement month is earlier than the valuation date. "
        "The holdings file is a 2009-03-31 snapshot, so at a later valuation date these "
        "contracts have delivered and the position is no longer a forward.",
    "tba-terms-unreadable":
        "A to-be-announced forward whose description does not state everything the contract "
        "needs. Terms come from the description for these, and guessing a settlement month "
        "or a coupon would price a contract nobody wrote.",
    "adjustable-rate-unsupported":
        "Adjustable-rate pool: the coupon resets, so a single fixed WAC cannot describe it.",
    "structure-unclassified":
        "The custodian description matches no known pool structure; classified rather than "
        "guessed at.",
}

if __name__ == "__main__":
    main()
