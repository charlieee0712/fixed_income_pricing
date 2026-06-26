"""Rating notch-map: collapse S&P / Moody's granular grades into the 7 FRED ICE BofA
US Corporate OAS parent buckets (AAA, AA, A, BBB, BB, B, CCC).

Locked spec — see PROJECT_STATUS.md §3.2. Two red lines (most spread-sensitive):

  1. S&P ``CC``/``C`` and Moody's ``Ca``/``C`` map to the **CCC** bucket (FRED has no lower
     bucket). They are NOT defaulted — only S&P ``D``/``SD`` are defaulted. (Moody's has no
     ``D``; default is flagged via S&P or an external marker.)
  2. The IG/HY boundary: ``BBB-`` (``Baa3``) is the lowest investment grade and ``BB+``
     (``Ba1``) the highest high-yield. They MUST land in different buckets (BBB vs BB) —
     never collapse them together.

Primary agency is S&P; Moody's is the fallback. Default has precedence: a bond that is
``D``/``SD`` on S&P is defaulted even if Moody's still carries a grade.
"""

from __future__ import annotations

# FRED parent buckets, best -> worst.
BUCKETS = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC")

# Non-bucket outcomes (sentinels).
DEFAULTED = "defaulted"
NO_RATING = "no-rating"

# --- S&P granular -> bucket ---
_SP_MAP = {
    "AAA": "AAA",
    "AA+": "AA", "AA": "AA", "AA-": "AA",
    "A+": "A", "A": "A", "A-": "A",
    "BBB+": "BBB", "BBB": "BBB", "BBB-": "BBB",   # BBB- = lowest IG  (red line 2)
    "BB+": "BB", "BB": "BB", "BB-": "BB",         # BB+  = highest HY (red line 2)
    "B+": "B", "B": "B", "B-": "B",
    "CCC+": "CCC", "CCC": "CCC", "CCC-": "CCC", "CC": "CCC", "C": "CCC",  # CC/C -> CCC (red line 1)
}
_SP_DEFAULT = frozenset({"D", "SD"})
_SP_NR = frozenset({"NR", ""})

# --- Moody's granular -> bucket ---
_MOODY_MAP = {
    "AAA": "AAA",
    "AA1": "AA", "AA2": "AA", "AA3": "AA",
    "A1": "A", "A2": "A", "A3": "A",
    "BAA1": "BBB", "BAA2": "BBB", "BAA3": "BBB",  # Baa3 = lowest IG  (red line 2)
    "BA1": "BB", "BA2": "BB", "BA3": "BB",        # Ba1  = highest HY (red line 2)
    "B1": "B", "B2": "B", "B3": "B",
    "CAA1": "CCC", "CAA2": "CCC", "CAA3": "CCC", "CA": "CCC", "C": "CCC",  # Ca/C -> CCC (red line 1)
}
_MOODY_NR = frozenset({"NR", "WR", ""})


def _norm(raw) -> str:
    """Upper-case, trim, unify the minus sign, and treat blank placeholders as empty."""
    if raw is None:
        return ""
    s = str(raw).strip().upper().replace("−", "-")  # U+2212 MINUS SIGN -> ASCII '-'
    if s in {"NULL", "N/A", "#N/A", "-", "NONE", "NAN"}:
        return ""
    return s


def sp_bucket(raw):
    """Map one S&P label to a bucket, DEFAULTED, NO_RATING, or None (unknown label)."""
    s = _norm(raw)
    if s in _SP_DEFAULT:
        return DEFAULTED
    if s in _SP_MAP:
        return _SP_MAP[s]
    if s in _SP_NR:
        return NO_RATING
    return None


def moody_bucket(raw):
    """Map one Moody's label to a bucket, NO_RATING, or None (unknown label).

    Moody's carries no ``D``; default is determined from S&P (see :func:`classify`).
    """
    s = _norm(raw)
    if s in _MOODY_MAP:
        return _MOODY_MAP[s]
    if s in _MOODY_NR:
        return NO_RATING
    return None


def classify(sp_raw, moody_raw):
    """Combine S&P (primary) and Moody's (fallback) with DEFAULT PRECEDENCE.

    Returns a ``(result, source)`` tuple:
      * ``(bucket, "S&P")`` / ``(bucket, "Moody")``  -> covered (bucket in :data:`BUCKETS`)
      * ``(DEFAULTED, "S&P")``                        -> Layer-A defaulted exclusion
      * ``(NO_RATING, None)``                         -> rating-exclusion

    Unknown labels on both agencies fall through to ``NO_RATING`` (conservative exclude).
    """
    sp = sp_bucket(sp_raw)
    if sp == DEFAULTED:               # S&P D/SD wins over any Moody fallback
        return DEFAULTED, "S&P"
    if sp in BUCKETS:
        return sp, "S&P"
    mo = moody_bucket(moody_raw)      # S&P is NR / unknown -> fall back to Moody's
    if mo in BUCKETS:
        return mo, "Moody"
    return NO_RATING, None
