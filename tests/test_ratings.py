"""Tests for the rating notch-map (fip/ratings.py). Run `pytest` from the repo root.

These lock the two red lines from PROJECT_STATUS.md §3.2.
"""

from fip.ratings import (
    BUCKETS, DEFAULTED, NO_RATING, classify, moody_bucket, sp_bucket,
)


def test_seven_parent_buckets():
    assert BUCKETS == ("AAA", "AA", "A", "BBB", "BB", "B", "CCC")


def test_red_line_1_low_grades_to_ccc_not_default():
    # S&P CC / C and Moody Ca / C collapse to CCC (FRED has no lower bucket).
    for r in ("CCC+", "CCC", "CCC-", "CC", "C"):
        assert sp_bucket(r) == "CCC", r
    for r in ("Caa1", "Caa2", "Caa3", "Ca", "C"):
        assert moody_bucket(r) == "CCC", r
    # ...and they are NOT defaulted.
    assert sp_bucket("CC") != DEFAULTED
    assert moody_bucket("Ca") != DEFAULTED


def test_red_line_2_ig_hy_boundary_not_collapsed():
    # BBB- / Baa3 (lowest IG) vs BB+ / Ba1 (highest HY) must differ.
    assert sp_bucket("BBB-") == "BBB"
    assert sp_bucket("BB+") == "BB"
    assert moody_bucket("Baa3") == "BBB"
    assert moody_bucket("Ba1") == "BB"
    assert sp_bucket("BBB-") != sp_bucket("BB+")
    assert moody_bucket("Baa3") != moody_bucket("Ba1")


def test_default_only_d_sd_with_precedence():
    assert sp_bucket("D") == DEFAULTED
    assert sp_bucket("SD") == DEFAULTED
    # Default precedence: S&P D wins even if Moody's still grades it.
    assert classify("D", "Baa2") == (DEFAULTED, "S&P")
    assert classify("SD", "A2") == (DEFAULTED, "S&P")


def test_fallback_then_exclude():
    assert classify("A-", "Baa2") == ("A", "S&P")        # S&P used directly
    assert classify("NR", "A2") == ("A", "Moody")        # S&P NR -> Moody fallback
    assert classify("NR", "WR") == (NO_RATING, None)     # neither -> exclude
    assert classify(None, None) == (NO_RATING, None)
    assert classify("NULL", "NULL") == (NO_RATING, None)


def test_normalisation():
    assert sp_bucket(" bbb+ ") == "BBB"                  # case / whitespace
    assert sp_bucket("BBB−") == "BBB"               # unicode minus -> ASCII
    assert moody_bucket("baa1") == "BBB"


def test_full_sp_scale_maps_to_buckets():
    scale = ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-",
             "BBB+", "BBB", "BBB-", "BB+", "BB", "BB-",
             "B+", "B", "B-", "CCC+", "CCC", "CCC-", "CC", "C"]
    for r in scale:
        assert sp_bucket(r) in BUCKETS, r
