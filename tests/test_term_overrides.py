"""Loader tests for dataio/term_overrides.py + regression locks on the tracked override tables.

The override tables carry primary-source term fills from the 2026-07-20 ISIN lookup
(docs/isin_lookup_2026-07-20.md); the locks here keep their load-bearing rows from silently
disappearing or changing shape.
"""
import datetime as dt
import pathlib

import pytest

from dataio.term_overrides import (load_coupon_schedule_overrides, load_frn_spreads,
                                   load_hybrid_terms, load_make_whole_overrides)

_DATA = pathlib.Path(__file__).resolve().parents[1] / "data"


# ---------- loader mechanics (synthetic files) ----------

def test_missing_files_mean_no_overrides(tmp_path):
    missing = str(tmp_path / "nope.csv")
    assert load_coupon_schedule_overrides(missing) == {}
    assert load_frn_spreads(missing) == {}
    assert load_make_whole_overrides(missing) == set()


def test_header_only_files_mean_no_overrides(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("asset_id,effective_date,coupon_rate\n")
    assert load_coupon_schedule_overrides(str(p)) == {}


def test_missing_column_raises(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("asset_id,rate\nA1,0.05\n")
    with pytest.raises(ValueError, match="missing required column"):
        load_coupon_schedule_overrides(str(p))


def test_schedule_grouping_and_order(tmp_path):
    p = tmp_path / "sched.csv"
    # dated row deliberately BEFORE the base row: the loader must sort base-first.
    p.write_text(
        "asset_id,effective_date,coupon_rate,source\n"
        "A1,2009-07-01,0.09125,step\n"
        "A1,,0.08625,base\n"
        "B2,,0.0695,flat\n"
    )
    out = load_coupon_schedule_overrides(str(p))
    assert out["A1"] == [(None, 0.08625), (dt.date(2009, 7, 1), 0.09125)]
    assert out["B2"] == [(None, 0.0695)]


def test_frn_spreads_bp_to_decimal_and_optional_freq(tmp_path):
    p = tmp_path / "frn.csv"
    p.write_text(
        "asset_id,quoted_margin_bp,freq\n"
        "A1,40,4\n"
        "B2,182,\n"
    )
    out = load_frn_spreads(str(p))
    assert out["A1"] == {"spread": 0.0040, "freq": 4}
    assert out["B2"] == {"spread": 0.0182, "freq": None}


def test_make_whole_set(tmp_path):
    p = tmp_path / "mw.csv"
    p.write_text("asset_id,evidence\nX9,prospectus\n")
    assert load_make_whole_overrides(str(p)) == {"X9"}


# ---------- regression locks on the tracked repo tables (ISIN lookup 2026-07-20) ----------

def test_repo_make_whole_contains_sempra():
    mw = load_make_whole_overrides(str(_DATA / "make_whole_overrides.csv"))
    assert "TNTD03203204" in mw          # Sempra 8.9% 2013: make-whole-only (SEC 424B2)


def test_repo_coupon_schedules_lock():
    sched = load_coupon_schedule_overrides(str(_DATA / "coupon_schedules.csv"))
    # the nine documented deterministic-path bonds
    assert set(sched) == {
        "TNTD04150829",  # Aquila 11.875 flat
        "TNTD03037132",  # Comcast 6.95 (custodian zero = error)
        "TNTD04087449",  # BT rating-step path
        "TNTG700496W",   # Sogerim/TIF 7.50 in force
        "TNTG701369W",   # TI 2012 plain fixed 7.25
        "TNTG701894W",   # TI 2033 plain fixed 7.75
        "TNTG001023W",   # Anglian plain fixed 5.375
        "TNTG405928W",   # RBS plain fixed 6.00
        "TNTG700307W",   # FT GBP 7.50 floor (curve-blocked, seeded)
    }
    # BT is the only multi-step path: 8.625% base, 9.125% from 2009-07-01
    assert sched["TNTD04087449"] == [(None, 0.08625), (dt.date(2009, 7, 1), 0.09125)]
    assert sched["TNTD03037132"] == [(None, 0.0695)]


def test_repo_frn_spreads_lock():
    sp = load_frn_spreads(str(_DATA / "frn_spreads.csv"))
    assert sp["TNTD03027773"] == {"spread": 0.0040, "freq": 4}   # Bear L+40 qtly
    assert sp["TNTD04131505"] == {"spread": 0.0014, "freq": 4}   # PNC L+14 qtly
    assert sp["TNTD04882955"] == {"spread": 0.0045, "freq": 4}   # MS L+45 qtly
    assert sp["TNTD04259874"] == {"spread": 0.0182, "freq": None}  # IndepComm L+182


def test_hybrid_terms_loader(tmp_path):
    p = tmp_path / "hyb.csv"
    p.write_text(
        "asset_id,isin,fixed_rate,fixed_freq,switch_date,float_index,float_margin_bp,float_freq,"
        "first_call_date,first_call_price,maturity,confidence,source_note\n"
        "A1,XX,0.06125,2,2017-05-15,3M USD LIBOR,193.5,4,2017-05-15,100,2067-05-15,HIGH,src\n"
        "B2,YY,0.0375,1,2011-02-23,,,,2011-02-23,100,2016-02-23,HIGH,margin gap\n"
        "C3,ZZ,0.07195,2,2037-06-25,3M USD LIBOR,129,4,2037-06-25,100,,HIGH,perp\n"
    )
    out = load_hybrid_terms(str(p))
    a = out["A1"]
    assert a["fixed_rate"] == 0.06125 and a["fixed_freq"] == 2 and a["float_freq"] == 4
    assert a["margin"] == 0.019350
    assert a["switch_date"] == dt.date(2017, 5, 15) and a["maturity"] == dt.date(2067, 5, 15)
    b = out["B2"]
    assert b["margin"] is None and b["float_freq"] is None       # documented margin gap -> None
    assert b["maturity"] == dt.date(2016, 2, 23)
    assert out["C3"]["maturity"] is None                         # blank maturity = perpetual


def test_repo_hybrid_terms_lock():
    hyb = load_hybrid_terms(str(_DATA / "hybrid_switch_terms.csv"))
    assert len(hyb) == 18
    with_margin = {a for a, h in hyb.items() if h["margin"] is not None}
    assert with_margin == {                     # the 10 fully-termed hybrids on the engine
        "TNTD03009347", "TNTD04735032", "TNTD04967448", "TNTD04986722",   # Allstate/Lincoln/Liberty/Chubb
        "TNTD04794469", "TNTD03057893",                                    # AmEx / GE
        "TNTG010475U", "TNTG522013U",                                      # SMBC / BofA
        "TNTD03020850", "TNTG533596W",                                     # BNP / UniCredit (perps)
    }
    assert hyb["TNTD03009347"]["margin"] == 0.019350             # Allstate 3mL+193.5
    assert hyb["TNTG010475U"]["margin"] == 0.0225                # SMBC 6mE+225
    assert hyb["TNTG010475U"]["float_freq"] == 2                 # ...paid s.a. after the switch
    assert hyb["TNTD03020850"]["maturity"] is None               # BNP = perpetual
    assert hyb["TNTG533596W"]["maturity"] is None                # UniCredit = perpetual
    assert hyb["TNTG614042U"]["margin"] is None                  # Shinsei margin gap -> BT-mark
    assert hyb["TNTG614042U"]["maturity"] == dt.date(2016, 2, 23)  # ...but maturity is resolved
