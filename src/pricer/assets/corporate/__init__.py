"""Corporate bonds: input catalogue + per-metric pricing/risk functions.

    from pricer.assets.corporate import vanilla, bonds_input
    print(bonds_input.describe_inputs())          # the highlighted-input table
    vanilla.implied_oas(6.5, 2, "2017-06-26", "2009-03-31", 105.1, curve)  # -> bp

One module per product, each a thin wrapper that names its inputs and delegates:

    vanilla           plain fixed-coupon bullet          (Coupon_Formula2 "Fixed")
    stepped           known coupon time-table            (stepped / step-up)
    floating          floating-rate note                 (... + Spread)
    hybrid            fixed-then-floating                (Fixed -> Floating / Reset)
    callable          issuer may repay early             ) all three share
    puttable          investor may sell back early       ) embedded_option, on
    sinking           issuer may retire part early       ) the one shared tree
"""
from pricer.assets.corporate import (bonds_input, floating, hybrid,  # noqa: F401
                                     stepped, vanilla)
