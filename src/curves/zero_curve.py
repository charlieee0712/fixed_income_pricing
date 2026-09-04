"""ZeroCurve — a bootstrapped zero (spot) curve for one valuation date, with linear
interpolation (the pricing convention in PROJECT_STATUS §3).

A thin wrapper over the validated :func:`curves.bootstrap.bootstrap`: it holds the monthly
output grid for one compounding-frequency variant and serves continuous-compounding zero
rates and discount factors at arbitrary times, with an optional flat credit spread (the OAS
that the rating layer supplies). Interpolation is linear on the dense monthly grid; outside
the grid ``np.interp`` clamps to the endpoints (flat extrapolation), matching the bootstrap.

    zc = ZeroCurve.from_par_txt("data/USD_Yield_Curve.txt", "2009-06-10")
    zc.zero_rate(5.0)               # continuous zero rate (decimal) at 5y
    zc.discount_factor(5.0, 0.013)  # DF at 5y with a 130 bp OAS added to the rate
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from curves.bootstrap import FREQUENCIES, bootstrap

# Par-curve export file per currency (in the data/ dir). Country-name aliases exist (JAPAN==JPY)
# but the URS holdings use ISO codes; extend as needed. JPY/AUD/KRW added for the phase-2 classes
# (KfW-JPY + EIB-AUD agencies, JGBi/KTBi linkers); all three files carry the 2009 dates
# (KRW lacks 2009-03-31 — its bootstrap raises there, which the drivers flag, not mask).
#
# The eight below were added 2026-09-03 for the Government / Municipal classes. Each was
# checked against the RAW file before being mapped -- the rule in docs/missing_data.md is that
# a units claim needs the source, not one of our own error messages. Reading the longest tenor
# at the earliest usable 2009 date gives BRL 0.1236, MXN 0.0838, NOK 0.0596, ILS 0.0442,
# SGD 0.0377, CAD 0.0356, SEK 0.0304 -- all DECIMALS, which is the default in
# ``curves.bootstrap.PAR_YIELD_UNITS``, so none of them needed a units entry (GBP and DKK
# remain the only two files that store percent).
#   * CAD maps to CAN_Yield_Curve.txt -- that file is named for the country, not the ISO code.
#   * DKK is mapped but carries NO 2009-03-31 or 2009-06-10 row, so its single holding is
#     reported curve-blocked rather than quietly priced off a neighbouring date.
#   * MYR has no file at all and is deliberately ABSENT here: ``from_currency`` raises, and the
#     driver turns that into a named disposition instead of a silent skip.
#
# What these files ARE matters for reading the calibrated spread. A file named for a country
# is that sovereign's own curve, so its own bonds reprice to ~0 (Bund +1.34bp, USTs within
# ~20bp) -- an anchor, not a credit signal. ``EUR_Yield_Curve.txt`` is the exception: it is a
# euro-area sovereign COMPOSITE, not a swap curve. Verified 2026-09-03 -- it sits strictly
# between Germany and Italy at every tenor, and a debt-weighted six-country average reproduces
# it to 7bp mean / 18bp max. So a euro sovereign priced on it shows relative value against the
# euro-area average (Germany rich, Ireland cheap), NOT an asset-swap spread.
CURVE_FILE = {
    "USD": "USD_Yield_Curve.txt",
    "EUR": "EUR_Yield_Curve.txt",
    "GBP": "GBP_Yield_Curve.txt",
    "JPY": "JPY_Yield_Curve.txt",
    "AUD": "AUD_Yield_Curve.txt",
    "KRW": "KRW_Yield_Curve.txt",
    "BRL": "BRL_Yield_Curve.txt",
    "CAD": "CAN_Yield_Curve.txt",
    "DKK": "DKK_Yield_Curve.txt",
    "ILS": "ILS_Yield_Curve.txt",
    "MXN": "MXN_Yield_Curve.txt",
    "NOK": "NOK_Yield_Curve.txt",
    "SEK": "SEK_Yield_Curve.txt",
    "SGD": "SGD_Yield_Curve.txt",
}


class ZeroCurve:
    """Zero curve for one valuation date and one compounding-frequency variant.

    Rates are stored continuous-compounding in decimal. ``freq`` selects which of the four
    bootstrap variants backs the curve; Semiannual is the default (most URS corporates pay
    semiannually). The discount factor adds an optional flat ``spread`` to the rate:
    ``DF(t) = exp(-(z(t) + spread) * t)``.
    """

    def __init__(self, grid: pd.DataFrame, freq: str = "Semiannual", valuation_date=None):
        if freq not in FREQUENCIES:
            raise ValueError(f"freq must be one of {list(FREQUENCIES)}; got {freq!r}")
        rate_col, df_col = f"{freq}_Rate", f"{freq}_DF"
        if rate_col not in grid.columns or df_col not in grid.columns:
            raise ValueError(f"grid is missing {rate_col}/{df_col}")
        self.freq = freq
        self.valuation_date = valuation_date
        self.grid = grid.reset_index(drop=True)
        self._t = self.grid["Maturity"].to_numpy(dtype=float)
        self._z = self.grid[rate_col].to_numpy(dtype=float) / 100.0   # percent -> decimal
        self._df = self.grid[df_col].to_numpy(dtype=float)

    @classmethod
    def from_par_txt(cls, txt_path: str, valuation_date, freq: str = "Semiannual"):
        """Bootstrap the par-yield txt at ``valuation_date`` and wrap the result."""
        grid = bootstrap(txt_path, valuation_date)
        return cls(grid, freq=freq, valuation_date=valuation_date)

    @classmethod
    def from_currency(cls, data_dir, currency, valuation_date, freq: str = "Semiannual"):
        """Bootstrap the par-yield curve for ``currency`` (USD/EUR/GBP/…) from ``data_dir``.

        Routes a bond to its OWN-currency discount curve — a non-USD bond discounted on the USD
        curve is mispriced (the v1 pipeline did exactly that for the 17 EUR/GBP corporates). Raises
        if the currency has no mapped par-curve file."""
        import os

        code = str(currency).strip().upper()
        fname = CURVE_FILE.get(code)
        if fname is None:
            raise ValueError(f"no par-curve file for currency {currency!r} (have {sorted(CURVE_FILE)})")
        return cls.from_par_txt(os.path.join(data_dir, fname), valuation_date, freq=freq)

    def zero_rate(self, t, spread: float = 0.0):
        """Continuous zero rate (decimal) at year ``t`` (linear-interpolated) + ``spread``."""
        return np.interp(t, self._t, self._z) + spread

    def discount_factor(self, t, spread: float = 0.0):
        """``DF(t) = exp(-(z(t) + spread) * t)`` — the rating OAS enters via ``spread``."""
        z = self.zero_rate(t, spread)
        return np.exp(-z * np.asarray(t, dtype=float))

    @property
    def max_tenor(self) -> float:
        return float(self._t[-1])

    def __repr__(self):
        return (f"ZeroCurve(date={self.valuation_date}, freq={self.freq}, "
                f"nodes={len(self._t)}, max_tenor={self.max_tenor:.2f}y)")
