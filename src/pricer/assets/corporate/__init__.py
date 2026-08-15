"""Corporate bonds: input catalogue + per-metric pricing/risk functions.

    from pricer.assets.corporate import vanilla, bonds_input
    print(bonds_input.describe_inputs())          # the highlighted-input table
    vanilla.implied_oas(6.5, 2, "2017-06-26", "2009-03-31", 105.1, curve)  # -> bp
"""
from pricer.assets.corporate import bonds_input, vanilla  # noqa: F401
