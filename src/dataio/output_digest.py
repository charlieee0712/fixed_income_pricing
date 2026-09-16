"""A fingerprint of a driver output that floating-point noise cannot move.

Two machines running this code do not produce byte-identical CSVs, and they are not
supposed to. A duration divides a bumped price difference by the bump, multiplying a
last-digit rounding by ten thousand; a convexity divides a second difference by the
bump squared and multiplies it by a hundred million. Comparing whole-file hashes across
processors therefore answers "are these the same bytes", which is a question whose
answer is routinely and harmlessly "no".

The question worth asking is different: **did anything that carries no arithmetic
change?** Asset identifiers, routes, flags, dates, provenance labels and reason codes
are decided by logic, not by rounding, so they must be identical everywhere. When they
are not, that is a defect. On 2026-09-03 a driver flag embedded a filesystem path and
so read ``data\\KRW_Yield_Curve.txt`` on Windows and ``data/…`` on Linux; it was found
by a human diffing two CSVs, and this is the comparison that would have found it.

⚠️ **Deliberately built on the standard library, not on pandas.** The first version of
this check went through ``pandas.read_csv(...).select_dtypes(...).to_csv()``, and the
first machine it met was Azure Cloud Shell running **pandas 3.0** against a record
written under pandas 2.3. Every digest differed, and nothing could say whether the text
had changed or the serializer had. A check meant to be invariant across platforms must
not be built on a library whose behaviour varies across versions — so this module parses
the file with :mod:`csv` and hashes the raw strings.

The definition of a text column, stated once so it has one owner:

    a column is TEXT if any non-empty value in it fails to parse as a float.

Dates, identifiers, routes and flags all fail; prices, spreads and durations all pass.
A column that is empty in every row is not text — it carries nothing either way.
"""
from __future__ import annotations

import csv
import hashlib
import pathlib

#: Separator between fields inside the hashed blob. A unit separator cannot occur in a
#: CSV field we produce, so it cannot be confused with content.
_SEP = "\x1f"


def _read(path):
    """The header and body of a CSV, as lists of strings.

    Inputs
    ------
    1. path : str | pathlib.Path — the CSV to read.

    Returns: ``(header, rows)``.
    """
    with pathlib.Path(path).open(newline="", encoding="utf-8") as handle:
        everything = list(csv.reader(handle))
    if not everything:
        return [], []
    return everything[0], everything[1:]


def text_columns(path) -> list:
    """The names of the columns that carry no arithmetic.

    Inputs
    ------
    1. path : str | pathlib.Path — a driver output CSV.

    Returns: list[str] — column names, in file order.
    """
    header, rows = _read(path)
    carries_text = [False] * len(header)
    for row in rows:
        for index, value in enumerate(row):
            if not value or index >= len(carries_text) or carries_text[index]:
                continue
            try:
                float(value)
            except ValueError:
                carries_text[index] = True
    return [header[i] for i, flag in enumerate(carries_text) if flag]


def text_digest(path, length: int = 16) -> str:
    """One fingerprint over every non-arithmetic column of a CSV.

    Inputs
    ------
    1. path   : str | pathlib.Path — a driver output CSV.
    2. length : int — how many hex characters to return (default 16).

    Returns: str — the digest, or ``"empty"`` for a file with no rows.

    The FULL header is hashed as well as the text content, so renaming a column,
    reordering the columns, or inserting a numeric column between two text ones all
    change the answer even though no text value moved.
    """
    header, rows = _read(path)
    if not header:
        return "empty"
    names = set(text_columns(path))
    keep = [i for i, name in enumerate(header) if name in names]
    blob = [_SEP.join(header)]
    blob += [_SEP.join(row[i] if i < len(row) else "" for i in keep) for row in rows]
    return hashlib.sha256("\n".join(blob).encode("utf-8")).hexdigest()[:length]


def column_digests(path, length: int = 8) -> dict:
    """A fingerprint per text column, for locating a difference rather than detecting it.

    Inputs
    ------
    1. path   : str | pathlib.Path — a driver output CSV.
    2. length : int — hex characters per column (default 8).

    Returns: dict ``{column_name: digest}`` in file order.

    :func:`text_digest` says *whether* something moved; this says *where*, which is the
    difference between "the machines disagree" and "the flag text on the curve-blocked
    rows disagrees".
    """
    header, rows = _read(path)
    names = set(text_columns(path))
    out = {}
    for index, name in enumerate(header):
        if name not in names:
            continue
        column = "\n".join(row[index] if index < len(row) else "" for row in rows)
        out[name] = hashlib.sha256(column.encode("utf-8")).hexdigest()[:length]
    return out
