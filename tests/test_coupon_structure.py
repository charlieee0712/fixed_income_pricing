"""Tests for the coupon-structure loader (``dataio.coupon_structure``).

The contract tests are hermetic — a temp CSV per test. The last three read the real
``data/coupon_structure.csv``, which is tracked, and lock the facts the file exists to carry:
that it covers the whole securitised book, that STEP is kept apart from FLOATING, and ⭐ that
the source file's stale ``Coupon`` column was **not** imported. That last one is the lock that
matters: the rate was measured to be wrong for floaters (0 of 59 matching the custodian at
2009-03-31, median +1.21 points, while 259 of 259 fixed rows matched exactly), so a later
reader reaching for a coupon in this table must fail rather than silently find one.
"""
import pytest

from dataio.coupon_structure import (COUPON_TYPES, load_coupon_structure,
                                     rate_behaviour)

HEADER = ("asset_id,cusip,isin,sub_category,desc_short,coupon_type,"
          "coupon_type_raw,cpn_freq,source_file,source,as_of\n")


def _write(tmp_path, body, name="coupon_structure.csv"):
    p = tmp_path / name
    p.write_text(HEADER + body)
    return str(p)


def test_missing_file_is_no_data_not_an_error(tmp_path):
    """A missing table means no data, the same contract as term_overrides and inflation."""
    assert load_coupon_structure(str(tmp_path / "absent.csv")) == {}


def test_rows_load_with_frequency_as_an_int_and_blank_as_none(tmp_path):
    path = _write(
        tmp_path,
        "AAA,111111111,US111111111X,Government Mortgage Backed Securities,FNMA 6%,"
        "fixed,FIXED,12,formulas_for_cpn_pmts.xlsx,Bloomberg via Mario 2026-10-07,2026-10-07\n"
        "BBB,222222222,US222222222X,Government Agencies,FHLB ZERO,"
        "zero,ZERO,,Agencies CPN Data.xlsx,Bloomberg via Mario 2026-10-07,2026-10-07\n",
    )
    got = load_coupon_structure(path)
    assert set(got) == {"AAA", "BBB"}
    assert got["AAA"]["coupon_type"] == "fixed"
    assert got["AAA"]["cpn_freq"] == 12
    assert got["BBB"]["cpn_freq"] is None          # blank, never defaulted to a number
    assert got["BBB"]["source_file"] == "Agencies CPN Data.xlsx"
    assert got["AAA"]["coupon_type_raw"] == "FIXED"


def test_an_unrecognised_coupon_type_is_refused(tmp_path):
    """An unknown token must not be mapped to anything reassuring."""
    path = _write(
        tmp_path,
        "AAA,111111111,US111111111X,Asset Backed Securities,SOMETHING,"
        "inverse,INVERSE FLOATER,12,f.xlsx,s,2026-10-07\n",
    )
    with pytest.raises(ValueError, match="unrecognised coupon_type"):
        load_coupon_structure(path)


def test_a_duplicate_asset_id_that_disagrees_is_refused(tmp_path):
    """13 securities are listed more than once and every duplicate agrees; a disagreement
    is two owners of one fact and must be loud, not last-one-wins."""
    path = _write(
        tmp_path,
        "AAA,111111111,US111111111X,Government Mortgage Backed Securities,P1,"
        "fixed,FIXED,12,f.xlsx,s,2026-10-07\n"
        "AAA,111111111,US111111111X,Government Mortgage Backed Securities,P1,"
        "floating,FLOATING,12,f.xlsx,s,2026-10-07\n",
    )
    with pytest.raises(ValueError, match="different coupon types"):
        load_coupon_structure(path)


def test_an_agreeing_duplicate_loads_once(tmp_path):
    path = _write(
        tmp_path,
        "AAA,111111111,US111111111X,Government Mortgage Backed Securities,P1,"
        "fixed,FIXED,12,f.xlsx,s,2026-10-07\n"
        "AAA,111111111,US111111111X,Government Mortgage Backed Securities,P1,"
        "fixed,FIXED,12,f.xlsx,s,2026-10-07\n",
    )
    assert list(load_coupon_structure(path)) == ["AAA"]


# --------------------------------------------------------------------------- behaviour

def test_step_is_a_schedule_and_not_rate_sensitive():
    """⭐ The load-bearing distinction. A stepped coupon changes on known dates, so a
    fixed-schedule duration is right once the schedule is supplied; a floater's is not."""
    assert rate_behaviour("step") == "schedule"
    assert rate_behaviour("floating") == "rate-sensitive"
    assert rate_behaviour("variable") == "rate-sensitive"
    assert rate_behaviour("step") != rate_behaviour("floating")


def test_fixed_and_zero_do_not_move_and_unresolved_is_not_fixed():
    assert rate_behaviour("fixed") == "fixed"
    assert rate_behaviour("ZERO") == "fixed"            # case-insensitive
    assert rate_behaviour("unresolved") is None         # ⚠️ not "fixed"
    with pytest.raises(ValueError):
        rate_behaviour("floater")


# --------------------------------------------------------------------------- the real table

def test_the_tracked_table_covers_the_whole_securitised_book():
    """1,333 securities = the master's securitised rows plus agencies, deduped. The counts
    reconcile to the master's own row-versus-unique gap, which is how we know nothing was
    filtered on the way in."""
    got = load_coupon_structure()
    if not got:
        pytest.skip("data/coupon_structure.csv not present")
    assert len(got) == 1333
    by_class = {}
    for rec in got.values():
        by_class[rec["sub_category"]] = by_class.get(rec["sub_category"], 0) + 1
    assert by_class["Government Mortgage Backed Securities"] == 882
    assert by_class["Non-Government Backed C.M.O.s"] == 264
    assert by_class["Asset Backed Securities"] == 79
    assert by_class["Commercial Mortgage-Backed"] == 69
    assert by_class["Government Agencies"] == 39
    assert sum(by_class.values()) == 1333


def test_the_tracked_table_says_a_third_of_the_book_is_not_fixed():
    """⚠️ The reason this file exists. Mario's covering note said the securities are all
    fixed or zeros; that holds for the agencies file and not for the securitised one."""
    got = load_coupon_structure()
    if not got:
        pytest.skip("data/coupon_structure.csv not present")
    kinds = {}
    for rec in got.values():
        kinds[rec["coupon_type"]] = kinds.get(rec["coupon_type"], 0) + 1
    assert kinds["floating"] == 282
    assert kinds["variable"] == 105
    assert kinds["step"] == 6
    # ⭐ 43 -> 5 on 2026-10-07 via the agencies file, then 5 -> 3 on 2026-10-14: `data/mtge.xlsx`
    # resolved both `#N/A Invalid Security` holdings that `missing_data.md` G7c had named.
    # `70337U100` PATRONS LEGACY reads FIXED 5.775% monthly, and `31358BAA6` FNMA PRIN STRIP
    # reads ZERO COUPON -- independently consistent with a description saying "PRIN PMT ON".
    assert kinds["unresolved"] == 3
    assert kinds["fixed"] == 825 and kinds["zero"] == 112
    assert sum(kinds[k] for k in ("floating", "variable", "step")) == 393
    # the agencies really are all fixed or zero -- his sentence, about his third file
    agency = [r for r in got.values() if r["sub_category"] == "Government Agencies"]
    assert {r["coupon_type"] for r in agency} <= {"fixed", "zero", "unresolved"}
    assert not [r for r in agency if r["coupon_type"] in
                ("floating", "variable", "step")]


def test_the_stale_coupon_rate_was_not_imported():
    """⭐ The lock that matters. The source file's `Coupon` is the 2009-03-31 rate for a fixed
    security and is NOT for a floater (0 of 59 matched; median +1.21 points high). The master's
    own column is correct and the driver already reads it, so this table must offer no coupon
    at all -- a reader reaching for one here has to fail rather than quietly find a wrong one.
    """
    got = load_coupon_structure()
    if not got:
        pytest.skip("data/coupon_structure.csv not present")
    rec = next(iter(got.values()))
    for banned in ("coupon", "coupon_pct", "income_rate", "rate", "net_coupon_pct"):
        assert banned not in rec, (
            "%r must not be in the coupon-structure table: the source file's rate is stale "
            "for floaters and the holdings master is authoritative" % banned)
    assert "coupon_type" in rec and "cpn_freq" in rec


def test_every_coupon_type_in_the_tracked_table_has_a_known_behaviour():
    got = load_coupon_structure()
    if not got:
        pytest.skip("data/coupon_structure.csv not present")
    for asset_id, rec in got.items():
        assert rec["coupon_type"] in COUPON_TYPES
        behaviour = rate_behaviour(rec["coupon_type"])
        assert behaviour in ("fixed", "schedule", "rate-sensitive", None), asset_id
