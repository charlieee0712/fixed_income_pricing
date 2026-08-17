"""
monthly_curve.py — `zeroyield4` curve replica for the Monthly-sheet reconciliation.

Rebuilds, to the letter, the curve construction that priced the Monthly golden
table: `zeroyield4(countryname, valuation)` in the legacy workbook's Module1
(`extracted/project_vba.txt` l.1011–2270).  This is the SHEET-INTERNAL bootstrap,
deliberately distinct from both production variants (CLAUDE.md lock "two legacy
bootstraps" — now three known variants):

  * `src/curves/bootstrap.py` (port of the "auditable" `zeroyield4auditable`
    rewrite): closed recursion at EVERY coupon date with par linearly
    interpolated onto the coupon grid;
  * `BondPrice`'s embedded bootstrap (semiannual z expression) — not used here;
  * `zeroyield4` (THIS replica): 12 monthly deposits money-market-discounted
    `DF = 1/(1 + r·tenor)`, then ONE continuous zero solved per annual pillar
    (months 24..360) so the frequency-matched par bond reprices to 100 under
    `exp(−z·t)`, with linear-in-z fill on the coupon months between pillars.

The auditable variant and this one differ at bp order on interior/short nodes,
which is material against the reconciliation's ≤2bp OAS tolerance — hence the
replica.  Never import this from production pricing code.

USD pillar inputs (the `H15T*` Bloomberg pulls at l.1082–1092) are H.15
Treasury CMT rates = treasury.gov daily par yield curve = FRED `DGS*`,
tracked in `data/h15_pillars_monthly_recon.csv`.
"""

from __future__ import annotations

import csv
import math
import os

# The 41-tenor grid exactly as zeroyield4 hard-codes it (VBA l.1034–1074).
# NOTE the sub-annual tenors are the VBA's rounded literals (0.08, 0.17, ...),
# NOT i/12: deposit DFs use these tenors, while zero rates divide by i/12
# (l.299–300 in the shared bootstrap body).
TERM2_TENORS = [
    0.08, 0.17, 0.25, 0.33, 0.42, 0.5, 0.58, 0.67, 0.75, 0.83, 0.92, 1.0,
    2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0,
    15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0,
    27.0, 28.0, 29.0, 30.0,
]

# Term2 row (1-based) filled by each USD pillar pull (VBA l.1082–1092).
PILLAR_ROWS = {
    "DGS1MO": 1, "DGS3MO": 3, "DGS6MO": 6, "DGS1": 12, "DGS2": 13,
    "DGS3": 14, "DGS5": 16, "DGS7": 18, "DGS10": 21, "DGS20": 31, "DGS30": 41,
}

FREQUENCIES = (1, 2, 4, 12)


def default_pillar_csv() -> str:
    return os.path.join(os.environ.get("FIP_DATA_DIR", "data"),
                        "h15_pillars_monthly_recon.csv")


def load_pillars(date_iso: str, csv_path: str | None = None) -> dict:
    """
    Load the 11 USD H.15 pillars for one valuation date.

    Inputs
    ------
    1. date_iso  : valuation date "YYYY-MM-DD" (must exist in the CSV)
    2. csv_path  : pillar file (default data/h15_pillars_monthly_recon.csv)

    Returns {term2_row (1-based): rate_percent}; raises if any pillar missing.
    """
    csv_path = csv_path or default_pillar_csv()
    rows: dict[int, float] = {}
    with open(csv_path, newline="") as fh:
        for rec in csv.DictReader(fh):
            if rec["date"] == date_iso:
                rows[PILLAR_ROWS[rec["series"]]] = float(rec["rate_percent"])
    missing = set(PILLAR_ROWS.values()) - set(rows)
    if missing:
        raise ValueError(f"pillars missing for {date_iso}: Term2 rows {sorted(missing)}")
    return rows


def gap_fill_usd(pillars: dict) -> list:
    """
    Fill the 11 USD pillars onto the 41-tenor grid EXACTLY as zeroyield4 does
    (VBA l.1094–1132), quirks included: the fill step is the per-YEAR slope
    applied per ROW, so the monthly rows 4–5 and 7–11 overshoot (they only
    enter the Quarterly/Monthly deposit strip, not the Annual/Semiannual
    tables the vanilla golden rows price on).  Annual rows are exact linear.

    Inputs
    ------
    1. pillars : {term2_row: rate_percent} from load_pillars()

    Returns a 41-element list of par rates in percent (Term2 order).
    """
    r = [None] * 42            # 1-based working array
    for row, rate in pillars.items():
        r[row] = rate
    t = [None] + TERM2_TENORS

    r[2] = (r[1] + r[3]) / 2.0                                 # l.1094
    p = (r[6] - r[3]) / (t[6] - t[3])                          # l.1095
    for i in (4, 5):                                           # l.1097–1099
        r[i] = r[i - 1] + p
    p = (r[12] - r[6]) / (t[12] - t[6])                        # l.1101
    for i in range(7, 12):                                     # l.1103–1105
        r[i] = r[i - 1] + p
    r[15] = (r[14] + r[16]) / 2.0                              # l.1107
    p = (r[18] - r[16]) / (t[18] - t[16])                      # l.1110
    r[17] = r[16] + p                                          # l.1112–1114
    p = (r[21] - r[18]) / (t[21] - t[18])                      # l.1116
    for i in (19, 20):                                         # l.1118–1120
        r[i] = r[i - 1] + p
    p = (r[31] - r[21]) / (t[31] - t[21])                      # l.1123
    for i in range(22, 31):                                    # l.1125–1127
        r[i] = r[i - 1] + p
    p = (r[41] - r[31]) / (t[41] - t[31])                      # l.1128
    for i in range(32, 41):                                    # l.1130–1132
        r[i] = r[i - 1] + p
    return r[1:]


def _solve_pillar(pv) -> float:
    """Exact root of pv(q) == 100 (q = continuous zero, decimal).  pv is
    monotone decreasing in q; the legacy used the Veloz grid search
    (|PV/100 − 1| < 1e-4, ~1e-5 z granularity) — this is its clean limit."""
    lo, hi = -0.5, 1.5
    flo, fhi = pv(lo) - 100.0, pv(hi) - 100.0
    if not (flo > 0.0 > fhi):
        raise ValueError("pillar solve not bracketed — degenerate par inputs")
    for _ in range(120):
        mid = 0.5 * (lo + hi)
        fm = pv(mid) - 100.0
        if fm > 0.0:
            lo = mid
        else:
            hi = mid
        if abs(fm) < 1e-13:
            break
    return 0.5 * (lo + hi)


def zeroyield4_tables(par41: list) -> dict:
    """
    The zeroyield4 bootstrap (VBA l.2067–2270, structurally l.255–447):
    four frequency-matched zero tables from one 41-tenor par curve.

    Inputs
    ------
    1. par41 : 41 par rates in percent (Term2 order), from gap_fill_usd()

    Returns {freq: (z, df)} where z/df are dicts keyed by month index; filled
    months are 1..12 (deposits) plus that frequency's coupon months up to 360.
    z is the CONTINUOUS zero (decimal), df = exp(−z·(month/12)).
    """
    tables: dict[int, tuple[dict, dict]] = {}
    for freq in FREQUENCIES:
        salti = 12 // freq
        z: dict[int, float] = {}
        df: dict[int, float] = {}
        for i in range(1, 13):                                 # deposits, l.296–301
            dfi = 1.0 / (1.0 + par41[i - 1] / 100.0 * TERM2_TENORS[i - 1])
            df[i] = dfi
            z[i] = -math.log(dfi) / (i / 12.0)
        prev = 12
        for pm in range(24, 361, 12):                          # annual pillars, l.309–390
            par = par41[pm // 12 + 10]                         # Term2 row = year + 11
            zprev = z[prev]

            def pv(q, _par=par, _zprev=zprev, _prev=prev, _pm=pm,
                   _salti=salti, _freq=freq, _z=z, _df=df):
                acc = 0.0
                for k in range(_salti, _prev + 1, _salti):     # known coupons, l.334–338
                    acc += _df[k]
                c = 1
                for m in range(_prev + _salti, _pm, _salti):   # linear-in-z fill, l.340–345
                    zm = ((_freq - c) * _zprev + c * q) / _freq
                    acc += math.exp(-zm * (m / 12.0))
                    c += 1
                dfp = math.exp(-q * (_pm / 12.0))              # l.346–348
                return (_par / _freq) * (acc + dfp) + 100.0 * dfp   # l.355

            q = _solve_pillar(pv)
            z[pm] = q                                          # l.377–379
            df[pm] = math.exp(-q * (pm / 12.0))
            c = 1
            for m in range(prev + salti, pm, salti):           # commit the fill, l.380–385
                zm = ((freq - c) * zprev + c * q) / freq
                z[m] = zm
                df[m] = math.exp(-zm * (m / 12.0))
                c += 1
            prev = pm
        tables[freq] = (z, df)
    return tables


def build_tables(date_iso: str, csv_path: str | None = None) -> dict:
    """load_pillars -> gap_fill_usd -> zeroyield4_tables, one call per date."""
    return zeroyield4_tables(gap_fill_usd(load_pillars(date_iso, csv_path)))
