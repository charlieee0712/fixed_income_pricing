"""Golden tests for the phase-2 mini-universe (dataio/phase2.py): class counts, engine routes,
recovered index ratios. Workbook-dependent tests skip when the URS file is absent; the
description-coupon parser tests are synthetic and always run."""
import os
import pathlib

import pytest

from dataio.phase2 import build_phase2_from_path, parse_desc_coupon

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_DEFAULT = "data/URS Fixed Income Mar 2009 - FI Positions V Mainak.xlsx"


def _find_urs():
    p = os.environ.get("FIP_URS_XLSX")
    if p and pathlib.Path(p).exists():
        return pathlib.Path(p)
    c = _ROOT / _DEFAULT
    return c if c.exists() else None


URS = _find_urs()


@pytest.fixture(scope="module")
def built():
    if URS is None:
        pytest.skip("URS workbook not found; set FIP_URS_XLSX")
    return build_phase2_from_path(str(URS))


# ---------- description-coupon parser (the None principle) — synthetic, never skipped ----------
def test_parse_desc_coupon_formats():
    # TIPS "x DUE" style (no % sign)
    assert parse_desc_coupon("US TREAS NTS INFLATION INDEXED 4.25 DUE 01-15-2010 REG") == 4.25
    assert parse_desc_coupon("UNITED STATES TREAS NTS 1.875 DUE       07-15-2015 REG") == 1.875
    # explicit % (JGBi, agencies)
    assert parse_desc_coupon("JAPAN(GOVT OF) 0.5%-IDX LK 10/06/15     JPY'4'") == 0.5
    assert parse_desc_coupon("FNMA 6.0% 18 APR 2036") == 6.0
    # standalone decimal next to a date must pick the coupon, not a date fragment
    assert parse_desc_coupon("FHLB PREASSIGN 00237 5.53 11-03-2014") == 5.53
    assert parse_desc_coupon("FHLMC TRANCHE # TR 00029 5.3  05-12-2020/05-12-2010") == 5.3
    # the KTBi: no coupon anywhere -> None (data gap, never a guess)
    assert parse_desc_coupon("KOREA(REPUBLIC OF) IDX-LKD BDS 10/03/17 KRW") is None
    assert parse_desc_coupon(None, "") is None


# ---------- class counts (rows -> unique ids, the dedupe-and-sum treatment) ----------
def test_class_counts(built):
    _, _, counts = built
    assert (counts["agency"]["rows"], counts["agency"]["unique"]) == (42, 39)
    assert (counts["guaranteed"]["rows"], counts["guaranteed"]["unique"]) == (11, 9)
    assert (counts["linker"]["rows"], counts["linker"]["unique"]) == (16, 15)
    assert (counts["govt_mbs"]["rows"], counts["govt_mbs"]["unique"]) == (888, 882)
    # the 10 negative-par (short/TBA-hedge) rows all sit in Govt MBS, none in the small classes
    assert counts["govt_mbs"]["negative_par_rows"] == 10
    for cls in ("agency", "guaranteed", "linker"):
        assert counts[cls]["negative_par_rows"] == 0
        assert counts[cls]["shorts"] == 0


# ---------- engine routes (the 2026-07-22 routing decisions) ----------
def test_agency_routes(built):
    _, _, counts = built
    assert counts["agency"]["routes"] == {
        "vanilla": 27,               # bullets + quasi-sovereigns
        "callable-lattice": 5,       # master AB call dates (genuine 4.7-20y gaps)
        "call-passed-vanilla": 4,    # desc date-pair, 2006 call passed unexercised, AB blank
        "zero": 2,                   # Resolution Funding CPN STRIPS
        "cmo-tranche": 1,            # FHLMC SER 3122 CL ZB — REMIC Z misfiled as a debenture
    }


def test_guaranteed_routes_and_group(built):
    bonds, _, counts = built
    assert counts["guaranteed"]["routes"] == {"vanilla": 9}
    g = bonds[bonds["asset_class"] == "guaranteed"]
    assert set(g["group"]) == {"TLGP-guaranteed"}    # own bucket, never the bank ratings


def test_linker_routes_and_ratios(built):
    bonds, _, counts = built
    assert counts["linker"]["routes"] == {"ilb": 14, "ilb-indexation-unverified": 1}
    lk = bonds[bonds["asset_class"] == "linker"].set_index("asset_id")
    # recovered 2009-03-31 index ratios (BG / description coupon) — spot goldens
    assert lk.loc["TNTG613068U", "index_ratio0"] == pytest.approx(1.014, abs=1e-3)      # JGBi
    assert lk.loc["TNTD03982260", "index_ratio0"] == pytest.approx(1.284379, abs=1e-4)  # 3.875% 2029
    assert lk.loc["TNTD03000471", "index_ratio0"] == pytest.approx(1.120139, abs=1e-4)  # 2.375% 2025
    assert lk.loc["TNTG673976U", "route"] == "ilb-indexation-unverified"                # the KTBi


def test_golden_separation(built):
    bonds, recon, _ = built
    for col in ("gold_price", "gold_mkt_value", "gold_ytm"):
        assert col not in bonds.columns              # input/truth separation, as the corporate universe
        assert col in recon.columns
