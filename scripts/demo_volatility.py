"""Print the volatility answer for a real callable holding — the live-demo companion to
the Excel sheet, which prices plain bonds only until the callable dispatch lands.

    PYTHONPATH=src python scripts/demo_volatility.py

Shows the two experiments side by side, because they answer different questions and are
easy to conflate:

    hold the spread fixed, move volatility   -> what happens to the PRICE
    hold the market price fixed, move it     -> what happens to the SPREAD

Reads the real call schedule from data/call_schedules.csv and the real curve for the
valuation date, so every number on screen is the production calculation, not an example.
"""
import os
import sys

sys.path.insert(0, "src")

from curves.zero_curve import ZeroCurve                       # noqa: E402
from dataio.call_schedules import load_call_schedules         # noqa: E402
from pricer.assets.corporate import callable as callable_bond  # noqa: E402

VAL = os.environ.get("FIP_VAL_DATE", "2009-03-31")
DATA = os.environ.get("FIP_DATA_DIR", "data")

# The portfolio's one genuinely call-active corporate: the call is close enough to the
# money for volatility to matter. Coupon in PERCENT, price per 100.
BOND = {"asset_id": "TNTD04441873", "label": "6.45% of 2034-06-15 (A rated)",
        "coupon": 6.45, "freq": 2, "maturity": "2034-06-15", "market_price": 90.0426,
        "currency": "USD"}


def main() -> int:
    """Print both volatility experiments for the demo bond."""
    schedules = load_call_schedules(os.path.join(DATA, "call_schedules.csv"))
    call_schedule = [(d.date(), p) for d, p in schedules[BOND["asset_id"]]]
    curve = ZeroCurve.from_currency(DATA, BOND["currency"], VAL, freq="Semiannual")
    args = (BOND["coupon"], BOND["freq"], BOND["maturity"], VAL)

    baseline = callable_bond.implied_oas(*args, BOND["market_price"], curve, call_schedule)
    prices = callable_bond.price_at_volatility(*args[:2], BOND["maturity"], VAL, curve,
                                               call_schedule, baseline)
    spreads = callable_bond.implied_oas_at_volatility(*args, BOND["market_price"], curve,
                                                      call_schedule)
    slope = callable_bond.volatility_sensitivity(*args, BOND["market_price"], curve,
                                                 call_schedule)

    print(f"\n  {BOND['label']}   marked {BOND['market_price']:.4f}   "
          f"callable {call_schedule[0][0]} @ {call_schedule[0][1]:.0f}   as of {VAL}\n")
    print("  volatility   price at a fixed spread    spread at the fixed market price")
    print("  " + "-" * 68)
    for vol in sorted(prices):
        mark = " <- baseline" if abs(vol - 0.15) < 1e-12 else ""
        print(f"  {vol:>6.0%}       {prices[vol]:>10.4f}                 "
              f"{spreads[vol]:>8.2f} bp{mark}")
    print("  " + "-" * 68)
    print(f"  per 1 volatility point:  price {slope['price_change_per_1_vol_point']:+.4f} "
          f"per 100      spread {slope['oas_change_bp_per_1_vol_point']:+.2f} bp\n")
    print("  Higher volatility makes the issuer's right to repay early worth more, so the")
    print("  bond is worth less. With the market price unchanged, more of that same discount")
    print("  is the cost of the call and less of it is credit — so the credit spread comes in.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
