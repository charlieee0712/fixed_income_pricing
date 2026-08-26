"""Where the endpoint's inputs come from (template: ``endpoints/dependencies.py``).

The ONE place that knows about the environment: which directory holds the par-curve
exports. Everything else in ``endpoints/`` is pure. A cloud deployment that keeps its
curves in object storage replaces this file and nothing else.
"""
from __future__ import annotations

import os

from pricer.core.market.curves import resolve_curve

DATA_DIR_ENV = "FIP_DATA_DIR"
DEFAULT_DATA_DIR = "data"      # repo-root relative, as every driver script assumes


def data_dir() -> str:
    """Directory holding the ``*_Yield_Curve.txt`` par-curve exports.

    Inputs: none (reads the ``FIP_DATA_DIR`` environment variable).
    Returns: str — the configured directory, or ``"data"``.
    """
    return os.environ.get(DATA_DIR_ENV, DEFAULT_DATA_DIR)


def curve_for(currency, valuation_date, coupon_frequency: int):
    """The discount curve for one request, in the bond's OWN currency.

    Inputs
    ------
    1. currency         : str — ISO code from the request.
    2. valuation_date   : str — ISO valuation date from the request.
    3. coupon_frequency : int — payments per year (selects the bootstrap variant).

    Returns: :class:`curves.zero_curve.ZeroCurve`.
    Raises :class:`pricer.core.market.curves.CurveUnavailable` — already worded for
    an external caller (no file paths).
    """
    return resolve_curve(currency, valuation_date, coupon_frequency, data_dir=data_dir())
