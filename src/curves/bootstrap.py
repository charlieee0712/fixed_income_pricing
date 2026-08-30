"""
bootstrap.py
============
Par-yield curve -> zero (spot) curve bootstrapping.

Faithful Python port of the "auditable" VBA routine
(`Zero_Yield_Curve_VBA_Code.txt` / `zeroyield4auditable`) from the legacy
fixed-income pricing workbooks. The goal of this module is *reproduction*:
it is designed to reproduce the legacy `Bootstrapped/XX_yield_curves.csv`
golden outputs to the digit, NOT to "improve" the methodology. Improvements
(e.g. monotone-convex interpolation, multi-curve) belong in a later phase.

Pipeline (per the legacy method):
    raw par yields (N market tenors, one row per date)
      -> map onto the 41-point standard tenor grid
      -> fill gaps by linear interpolation, flat-extrapolate the ends
      -> for each compounding frequency f in {1, 2, 4, 12}:
             build coupon grid at step 1/f out to ~31y
             linearly interpolate par yields onto the coupon grid
             bootstrap par -> discount factors -> zero rates
             resample zero rates onto a monthly grid; DF = exp(-z * t)

Key conventions (read out of the VBA, confirmed against golden output):
    coupon per period : cpn   = 100 * par / f
    bootstrap step     : DF_i  = (100 - cpn * sum_{k<i} DF_k) / (100 + cpn)
    zero rate          : z_i   = -ln(DF_i) / t_i      (CONTINUOUS compounding)
    output DF          : DF(t) = exp(-z(t) * t)
    rates are stored in PERCENT in the CSV (z * 100).

No Bloomberg dependency: the legacy `GetBloomberg` data source is replaced by
the per-currency `*_Yield_Curve.txt` history files.

Validation (US, valuation date 2024-01-16, vs golden US_yield_curves.csv):
    Annual / Semiannual / Quarterly rates : exact (max |err| = 0.000000 pp)
    Monthly rate                          : max |err| = 0.0806 pp, at the very
                                            short end only. This residual comes
                                            from the 1m/2m grid points, which the
                                            USD txt does not carry (shortest tenor
                                            is 3m) and which this module fills by
                                            flat extrapolation. If the colleague's
                                            pipeline sources 1m/2m explicitly, that
                                            is a one-line change in `_fill_grid`.
"""

from __future__ import annotations
import datetime as dt
import os
import numpy as np
import pandas as pd

# 41-point standard tenor grid, in years (VBA: LoadStandardTenorsAudit).
STANDARD_TENORS = np.array([
    0.08, 0.17, 0.25, 0.33, 0.42, 0.5, 0.58, 0.67, 0.75, 0.83, 0.92, 1.0,
    2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0,
    15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0,
    27.0, 28.0, 29.0, 30.0,
])

FREQUENCIES = {"Annual": 1, "Semiannual": 2, "Quarterly": 4, "Monthly": 12}
_MAX_MONTHS = 374  # output grid length (~31.17y), matches the legacy output

# ---------------------------------------------------------------- par-yield file units
#
# The *_Yield_Curve.txt exports are NOT uniform: most store par yields as DECIMALS
# (0.0304 = 3.04%), but two store them as PERCENT (3.04 = 3.04%). The unit is a property
# of the FILE, not of anything readable inside a single row, so it is declared here
# rather than sniffed — a threshold rule would have to distinguish a 0.5% Danish yield
# from a 0.5 decimal, and it would get it wrong.
#
# Verified 2026-08-30 across all 26 data/*_Yield_Curve.txt files, by checking each
# against the actual market at known dates:
#   GBP  8,201 rows 1994-2026, median 3.897, max 10.64  -> UK rates in PERCENT
#        (2009-03-31: 0.731 / 1.183 / 2.341 / 3.157 / 4.157 = the gilt curve that day)
#   DKK  4,300 rows, median 0.543, min -1.90, max 4.399 -> Danish rates in PERCENT
#        (2020-06-15: -0.463 ... +0.295 = the negative-rate curve of that summer)
# Every other file is decimal, including USD, EUR, JPY, AUD and KRW.
#
# ⚠️ This mattered: read as decimals, the GBP file becomes a 73%-415% par curve, whose
# bootstrap fails at the 3-year node with "par curve is not arbitrage-free". That message
# was taken at face value for two months, and the one GBP holding was carried unpriced
# with a Bloomberg curve request open against it. The curve was always fine.
PAR_YIELD_UNITS = {
    "GBP_Yield_Curve.txt": "percent",
    "DKK_Yield_Curve.txt": "percent",
}
DEFAULT_PAR_YIELD_UNITS = "decimal"
_UNIT_SCALE = {"decimal": 100.0, "percent": 1.0}    # factor to reach PERCENT

# A par yield above this (in percent) is not a market: it is a units or data error.
# The widest legitimate value across all 26 files is ~23% (SEK in the early 1990s).
_MAX_PLAUSIBLE_PAR_PCT = 100.0


class ParYieldUnitError(ValueError):
    """A par-yield row that cannot be a market curve — a units or data problem.

    Raised BEFORE the bootstrap, so a file read in the wrong units is reported as what it
    is instead of resurfacing three years down the coupon grid as a non-arbitrage-free
    node, which sends the reader looking at the market data instead of the loader.
    """

# Excel's 1900 date system (valid for dates after 1900-02-28).
_EXCEL_EPOCH = dt.date(1899, 12, 30)


def excel_serial_to_date(serial: int) -> dt.date:
    """Convert an Excel serial date (1900 system) to a calendar date."""
    return _EXCEL_EPOCH + dt.timedelta(days=int(serial))


def date_to_excel_serial(d: dt.date) -> int:
    """Convert a calendar date to an Excel serial date (1900 system)."""
    return (d - _EXCEL_EPOCH).days


def _interp_flat(x: float, xs: np.ndarray, ys: np.ndarray) -> float:
    """Linear interpolation with FLAT extrapolation (VBA: InterpLinearAudit)."""
    if x <= xs[0]:
        return float(ys[0])
    if x >= xs[-1]:
        return float(ys[-1])
    return float(np.interp(x, xs, ys))


def par_yield_units(txt_path: str) -> str:
    """Which units a par-yield file stores, from :data:`PAR_YIELD_UNITS`.

    Inputs
    ------
    1. txt_path : str — path to a ``*_Yield_Curve.txt`` file (only its file name matters).

    Returns: ``"decimal"`` (the default) or ``"percent"``.
    """
    return PAR_YIELD_UNITS.get(os.path.basename(str(txt_path)), DEFAULT_PAR_YIELD_UNITS)


def load_par_curve(txt_path: str, valuation_date, units: str = None
                   ) -> tuple[np.ndarray, np.ndarray]:
    """
    Read one valuation date's par-yield row from a *_Yield_Curve.txt file.

    The file's header is `Date,<tenor>,<tenor>,...` where each tenor column is a
    maturity in years and each row is a date (Excel serial) of par yields.

    Inputs
    ------
    1. txt_path       : str — the par-yield export.
    2. valuation_date : date | str — the row to read; no nearest-date substitution.
    3. units          : str | None — ``"decimal"`` or ``"percent"``; ``None`` (the
       default) looks the file up in :data:`PAR_YIELD_UNITS`, which is decimal for every
       file but GBP and DKK.

    Returns
    -------
    tenors  : market tenors present in the file (years), ascending
    par_pct : par yields at those tenors, in PERCENT, for the given date

    Raises :class:`ParYieldUnitError` when the scaled row is not a plausible market curve
    — which is what a file read in the wrong units looks like.
    """
    if isinstance(valuation_date, str):
        valuation_date = dt.date.fromisoformat(valuation_date)
    serial = date_to_excel_serial(valuation_date)

    df = pd.read_csv(txt_path)
    tenor_cols = [c for c in df.columns if c != "Date"]
    tenors = np.array([float(c) for c in tenor_cols])

    hit = df.loc[df["Date"] == serial]
    if hit.empty:
        raise ValueError(
            f"Valuation date {valuation_date} (serial {serial}) not found in "
            f"{txt_path}. Nearest available dates must be chosen explicitly."
        )
    units = par_yield_units(txt_path) if units is None else str(units).lower()
    if units not in _UNIT_SCALE:
        raise ValueError(f"units must be 'decimal' or 'percent'; got {units!r}")
    par_pct = hit[tenor_cols].to_numpy(dtype=float).ravel() * _UNIT_SCALE[units]

    worst = float(np.nanmax(np.abs(par_pct))) if par_pct.size else 0.0
    if worst > _MAX_PLAUSIBLE_PAR_PCT:
        raise ParYieldUnitError(
            f"{os.path.basename(str(txt_path))} at {valuation_date} gives a par yield of "
            f"{worst:.1f}% after reading it as {units}. No market curve looks like that, "
            f"so the file is almost certainly stored in the other unit — declare it in "
            f"curves.bootstrap.PAR_YIELD_UNITS. (Left unchecked this surfaces later as "
            f"'par curve is not arbitrage-free', which points at the market data instead "
            f"of at the units.)"
        )
    return tenors, par_pct


def _fill_grid(tenors: np.ndarray, par_pct: np.ndarray) -> np.ndarray:
    """
    Map market par yields onto the 41-point standard grid, then fill gaps by
    linear interpolation and flat-extrapolate the ends (VBA: FillMissingLinear /
    Back/ExtrapolateLinear, generalised so it is driven by the tenors actually
    present in the data file).
    """
    grid = np.full(STANDARD_TENORS.size, np.nan)
    for t, y in zip(tenors, par_pct):
        j = int(np.argmin(np.abs(STANDARD_TENORS - t)))  # nearest grid node
        grid[j] = y
    known = ~np.isnan(grid)
    kx, ky = STANDARD_TENORS[known], grid[known]
    for i in range(grid.size):
        if np.isnan(grid[i]):
            grid[i] = _interp_flat(STANDARD_TENORS[i], kx, ky)
    return grid


def _bootstrap_frequency(par_grid: np.ndarray, freq: int):
    """
    Bootstrap one compounding frequency.

    Returns (maturities, zero_pct, dfs) on the monthly output grid, INCLUDING the
    t=0 row (zero rate flat-extrapolated from the front, DF = 1.0).
    """
    step = 1.0 / freq
    n_periods = int((_MAX_MONTHS / 12.0) * freq)

    coupon_times = np.array([(i + 1) * step for i in range(n_periods)])
    par_at_coupons = np.array(
        [_interp_flat(t, STANDARD_TENORS, par_grid) / 100.0 for t in coupon_times]
    )

    dfs = np.zeros(n_periods)
    zeros = np.zeros(n_periods)
    for i in range(n_periods):
        cpn = 100.0 * par_at_coupons[i] / freq
        prev = dfs[:i].sum()
        dfs[i] = (100.0 - cpn * prev) / (100.0 + cpn)
        if dfs[i] <= 0.0:
            raise ValueError(
                f"Non-positive discount factor at t={coupon_times[i]:.3f} "
                f"(freq={freq}); par curve is not arbitrage-free at this node."
            )
        zeros[i] = -np.log(dfs[i]) / coupon_times[i]

    # Output grid matches the legacy golden CSV exactly: {0, 1/12, ..., 373/12}.
    months = np.arange(1, _MAX_MONTHS) / 12.0
    zero_m = np.array([_interp_flat(t, coupon_times, zeros) for t in months])
    df_m = np.exp(-zero_m * months)

    # prepend t=0 (short-rate flat, DF=1) to match the golden CSV layout
    maturities = np.concatenate(([0.0], months))
    zero_pct = np.concatenate(([zero_m[0] * 100.0], zero_m * 100.0))
    dfs_out = np.concatenate(([1.0], df_m))
    return maturities, zero_pct, dfs_out


def bootstrap(txt_path: str, valuation_date) -> pd.DataFrame:
    """
    Bootstrap a full zero curve (all four compounding frequencies) for one date.

    Returns a DataFrame whose columns match the legacy golden output:
        Maturity,
        Monthly_Rate, Monthly_DF, Quarterly_Rate, Quarterly_DF,
        Semiannual_Rate, Semiannual_DF, Annual_Rate, Annual_DF
    (rates in percent, DFs dimensionless).
    """
    tenors, par_pct = load_par_curve(txt_path, valuation_date)
    par_grid = _fill_grid(tenors, par_pct)

    out = {}
    maturities = None
    for name, freq in FREQUENCIES.items():
        m, z, d = _bootstrap_frequency(par_grid, freq)
        maturities = m if maturities is None else maturities
        out[f"{name}_Rate"] = z
        out[f"{name}_DF"] = d

    cols = ["Maturity"]
    for name in ("Monthly", "Quarterly", "Semiannual", "Annual"):
        cols += [f"{name}_Rate", f"{name}_DF"]
    df = pd.DataFrame({"Maturity": maturities, **out})
    return df[cols]


def _self_test(txt_path: str, golden_csv: str, valuation_date: str = "2024-01-16"):
    """Bootstrap and compare against a golden CSV; print max abs errors per column."""
    got = bootstrap(txt_path, valuation_date).set_index("Maturity")
    gold = pd.read_csv(golden_csv).set_index("Maturity")

    # align on nearest maturity (grids are identical up to float repr)
    aligned = got.reindex(gold.index, method="nearest")
    print(f"Self-test  |  valuation date = {valuation_date}")
    print(f"  rows: got={len(got)}  golden={len(gold)}")
    worst = 0.0
    for col in gold.columns:
        if col not in aligned.columns:
            continue
        err = float(np.max(np.abs(aligned[col].to_numpy() - gold[col].to_numpy())))
        worst = max(worst, err)
        unit = "pp" if col.endswith("Rate") else "  "
        print(f"  max|err| {col:18s}: {err:.6f} {unit}")
    print(f"  GLOBAL max abs error: {worst:.6f}")
    return worst


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Bootstrap a zero curve from a par-yield txt file.")
    p.add_argument("txt", help="path to <CCY>_Yield_Curve.txt")
    p.add_argument("date", help="valuation date, YYYY-MM-DD")
    p.add_argument("--golden", help="optional golden CSV to validate against")
    p.add_argument("--out", help="optional path to write the bootstrapped curve CSV")
    args = p.parse_args()

    if args.golden:
        _self_test(args.txt, args.golden, args.date)
    else:
        curve = bootstrap(args.txt, args.date)
        if args.out:
            curve.to_csv(args.out, index=False)
            print(f"wrote {args.out}  ({len(curve)} rows)")
        else:
            print(curve.head(12).to_string(index=False))
