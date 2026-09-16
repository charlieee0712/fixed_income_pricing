"""The text fingerprint does what it claims (added 2026-09-15).

``dataio.output_digest`` exists to answer one question across machines: did anything
that carries no arithmetic change? Its whole value rests on two properties that pull in
opposite directions, and both are asserted here rather than assumed:

  * **blind to float noise** -- a price whose last digits differ, as they do on every
    other processor, must not move the digest;
  * **sensitive to text** -- a changed identifier, route, flag or reason code must move
    it, because that is never rounding.

It replaced a version built on ``pandas.select_dtypes(...).to_csv()``, which failed the
first property in the worst way: it was not blind to float noise but to LIBRARY VERSION.
Azure Cloud Shell runs pandas 3.0 against a record written under 2.3, every digest
differed, and nothing could say whether the text had changed or the serializer had.
"""
import pathlib

import pytest

from dataio.output_digest import column_digests, text_columns, text_digest

CSV = ("asset_id,valuation_date,route,clean,eff_dur,flag\n"
       "TNTD03978845,2009-03-31,callable-lattice,122.0400000000001,0.39,par call from AB\n"
       "TNTD03983600,2009-03-31,zero,91.67300000000002,4.05,\n"
       "TNTG630781W,2009-03-31,vanilla,-0.5,12.5,quoted per 1000\n")


def write(tmp_path, text, name="out.csv"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8", newline="")
    return path


def test_text_columns_are_the_ones_carrying_no_arithmetic(tmp_path):
    """Dates and identifiers are text; prices and durations are not.

    The rule is "any non-empty value that fails to parse as a float makes the column
    text", so a negative price stays numeric and an ISO date does not.
    """
    assert text_columns(write(tmp_path, CSV)) == ["asset_id", "valuation_date", "route", "flag"]


def test_a_float_moving_in_its_last_digits_does_not_move_the_digest(tmp_path):
    """⭐ The defining property. Without it the check is just a slower sha256.

    This is exactly the size of difference two processors produce: a convexity divides a
    second difference by the square of a small bump and multiplies a last-digit rounding
    by a hundred million.
    """
    original = write(tmp_path, CSV, "a.csv")
    nudged = write(tmp_path, CSV
                   .replace("122.0400000000001", "122.04000000000008")
                   .replace("91.67300000000002", "91.67299999999994")
                   .replace("4.05", "4.050000000000001"), "b.csv")
    assert original.read_bytes() != nudged.read_bytes(), "the fixture must actually differ"
    assert text_digest(original) == text_digest(nudged)


@pytest.mark.parametrize("before,after", [
    ("TNTD03978845", "TNTD03978846"),          # an identifier
    ("callable-lattice", "vanilla"),           # a route
    ("par call from AB", "par call from XY"),  # a flag's wording
    ("2009-03-31", "2009-06-10"),              # a date
])
def test_any_text_change_moves_the_digest(tmp_path, before, after):
    """Sensitivity, one field family at a time. None of these is ever rounding."""
    assert text_digest(write(tmp_path, CSV, "a.csv")) != \
        text_digest(write(tmp_path, CSV.replace(before, after, 1), "b.csv"))


def test_a_renamed_or_reordered_column_moves_the_digest(tmp_path):
    """The FULL header is hashed, not only the text columns.

    A numeric column inserted between two text ones changes the file without changing a
    single text value, and a reader comparing digests should hear about it.
    """
    base = write(tmp_path, CSV, "a.csv")
    renamed = write(tmp_path, CSV.replace("eff_dur", "duration_years", 1), "b.csv")
    assert text_digest(base) != text_digest(renamed)


def test_the_digest_does_not_depend_on_pandas_being_installed(tmp_path):
    """⚠️ The reason this module exists at all.

    ``dataio.output_digest`` must import and work with nothing but the standard library,
    so that a machine on a different pandas cannot produce a different answer for the
    same bytes.
    """
    source = pathlib.Path(__file__).resolve().parents[1] / "src" / "dataio" / "output_digest.py"
    text = source.read_text(encoding="utf-8")
    for banned in ("import pandas", "import numpy", "from pandas", "from numpy"):
        assert banned not in text, f"{banned} defeats the point of this module"


def test_column_digests_name_the_columns_they_cover(tmp_path):
    """Locating a difference, not merely detecting one."""
    per_column = column_digests(write(tmp_path, CSV))
    assert list(per_column) == ["asset_id", "valuation_date", "route", "flag"]
    assert all(len(v) == 8 for v in per_column.values())

    changed = column_digests(write(tmp_path, CSV.replace("zero", "vanilla", 1), "b.csv"))
    moved = [k for k in per_column if per_column[k] != changed[k]]
    assert moved == ["route"], "only the column that changed may move"


def test_an_empty_file_is_reported_rather_than_crashing(tmp_path):
    assert text_digest(write(tmp_path, "", "empty.csv")) == "empty"
    assert text_columns(write(tmp_path, "a,b,c\n", "header_only.csv")) == []
