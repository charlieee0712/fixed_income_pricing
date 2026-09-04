"""Phase-2 asset classes (Mario 2026-07-20): Government Agencies / Guaranteed (FDIC-TLGP) /
Index-Linked government bonds — master-sheet loader + per-class mini-universe with engine routes.

Findings basis: ``docs/phase2_inventory_2026-07-20.md`` (read-only recon) + the 2026-07-22 build
recon. Everything here is data-driven off the master ``Fixed Income`` sheet only — none of the
three classes has a terms tab (the corporate-tab join does not apply); the coupon carrier is
**BG "Income rate"** (validated vs the description figures), payment frequency **CB**, maturity
**BW**, call date **AB**.

Class routing (decisions of 2026-07-22, evidence in ``docs/phase2_methods_2026-07-22.md``):
  * **agency** (42 rows / 39 unique) —
      - ``zero``: the 2 Resolution Funding CPN STRIPS (BG ~ 1e-5, CB blank) -> degenerate vanilla.
      - ``callable-lattice``: the 5 with a master AB call date (all genuine gaps, 4.7-20y) ->
        BDT lattice, Bermudan par call @100 from AB (the industry-standard agency-debenture
        assumption — unlike corporate make-whole, par call is the CORRECT default here, not a
        placeholder). Schedule rows live in ``data/call_schedules.csv`` (the single call-terms
        source); sigma = the house 0.15.
      - ``call-passed-vanilla``: 4 whose description shows a maturity/call date PAIR with the call
        in 2006 — passed UNEXERCISED (custodian AB agrees: blank) -> a bullet now; priced vanilla,
        flagged (evidence beats a terms-unavailable mark).
      - ``cmo-tranche``: TNTD04733316 "FHLMC SER 3122 CL ZB" — a REMIC Z-tranche misfiled as an
        agency debenture (Monthly freq, ISIN NULL, $72k). BT-marked for the CMO phase, NOT
        force-priced as a 27y bullet (the Sempra lesson).
      - else ``vanilla`` (FNMA/FHLB/FHLMC bullets + quasi-sovereigns KDB/KEXIM/PEMEX/HQ/Israel/
        KfW/EIB/Farmer Mac; EUR 2 / JPY 1 / AUD 1 route via ``ZeroCurve.from_currency``).
  * **guaranteed** (11 / 9) — all FDIC-TLGP crisis paper -> ``vanilla``, ``group`` =
    ``TLGP-guaranteed``: reported as its OWN bucket, never in bank rating buckets (the credit is
    the FDIC guarantee — the master even rates them AAA/Aaa; a bank-name bucket would distort the
    by-rating table).
  * **linker** (16 / 15) — ``ilb`` where the per-bond index ratio is recoverable as
    ``BG / description real coupon`` (14 TIPS + JGBi; ratios 1.008-1.31, a sensible CPI-accretion
    pattern); the KTBi shows BG == coupon exactly and no description coupon -> the Korea
    indexation convention is unverified -> ``ilb-indexation-unverified`` (BT mark, Mario list).

Data-quality: duplicate asset-ids across accounts are deduped with par (and market value / book
cost) **summed** — with the summed MV the ``BT == BU/par*100`` identity is exact per unique id.
Negative-par rows (shorts) net into the sum and set ``is_short``; the master ``Y``
Asset/Liability indicator does NOT discriminate them (uniformly 'A' — verified 2026-07-22; the
10 negative rows in this book are all Govt-MBS TBA-style hedges, none in these three classes).
"""
from __future__ import annotations

import re

import pandas as pd

from dataio.loaders import GOLDEN_FIELDS, MASTER_COLS, _read_sheet

MASTER_SHEET = "Fixed Income"

# Master letters beyond the corporate set (recon 2026-07-22; header names verified on 47).
PHASE2_MASTER_COLS = {
    **MASTER_COLS,
    "Q": "desc_short",            # 'Asset description - short'
    "T": "desc_long",             # 'Asset description - long'
    "Y": "asset_liability",       # 'Asset/Liability Indicator' (uniformly 'A'; kept as audit)
    "BG": "income_rate",          # 'Income rate' = the coupon carrier (percent; linkers: x ratio)
    "BH": "income_rate_ann",      # 'Income rate - annualized'
    "BX": "orig_face",            # 'Original face value' (empty for the MBS rows)
    "CA": "paydown_factor",       # 'Paydown factor' (== Govt MTGE tab BZ where both exist)
    "CB": "pay_freq",             # 'Payment frequency' (text)
    "AQ": "dur_eff_custodian",    # 'Duration - effective' (free external cross-check)
}

SUBCATS = {
    "agency": "Government Agencies",
    "guaranteed": "Guaranteed Fixed Income",
    "linker": "Index Linked Government Bonds",
    "govt_mbs": "Government Mortgage Backed Securities",   # counted only; engine awaits Bloomberg
    "government": "Government Bonds",                      # Summary!K23, Mario 2026-09-03
    "municipal": "Municipal/Provincial Bonds",             # Summary!K55, Mario 2026-09-03
}

# Which driver owns which class. ``build_phase2_universe`` defaults to PHASE2_CLASSES so
# ``scripts/phase2_risk.py`` and its committed CSV are untouched by the sovereign work;
# ``scripts/sovereign_risk.py`` passes SOVEREIGN_CLASSES.
PHASE2_CLASSES = ("agency", "guaranteed", "linker", "govt_mbs")
SOVEREIGN_CLASSES = ("government", "municipal")
COUNT_ONLY = frozenset({"govt_mbs"})       # inventoried; the engine awaits the Bloomberg pull

FREQ_FROM_TEXT = {"Semi-Annually": 2, "Annually": 1, "Quarterly": 4, "Monthly": 12}

ZERO_COUPON_MAX_PCT = 0.01        # BG below this (percent) = zero-coupon (the strips carry 1e-5)
RATIO_SANITY = (0.9, 1.6)         # plausible 2009 index-ratio window for held vintages
MAKE_WHOLE_MAX_GAP_DAYS = 7       # same guard as the corporate universe (none trigger here)

# description parsing (the None principle: no number -> None, never a guess)
_CPN_PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_CPN_DUE = re.compile(r"(\d+(?:\.\d+)?)\s+DUE\b", re.I)
_DATE_TOKEN = re.compile(r"\d{1,2}[-/^]\d{1,2}[-/^]\d{2,4}")
_DECIMAL = re.compile(r"\d+\.\d+")
# "05-12-2020/05-12-2010" — the agency maturity/call date-pair notation
_DATE_PAIR = re.compile(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\s*/\s*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}")
_CMO_CLASS = re.compile(r"\bSER\b.{0,12}\bCL\b", re.I)     # "SER 3122 CL ZB" = a REMIC class


# sovereign / municipal description tokens. Each fires on a holding that was read and
# identified individually (evidence: docs/sovereign_municipal_scope_2026-09-03.md), so these
# route by a documented contract feature, never by a guess at the price.
_FRN_TOKEN = re.compile(r"\bFRN\b|\bFLOAT", re.I)
_STEP_UP_TOKEN = re.compile(r"\bSTEP\s*-?\s*UP\b", re.I)
_SINKING_TOKEN = re.compile(r"\bSINKING\b|\bSINK\s*FD\b", re.I)

# ------------------------------------------------------------------- price quotation
# For a few local-market sovereigns the custodian records ``par_value`` as a COUNT OF TITLES
# rather than a currency face amount, and quotes the price per title. The detector is the
# custodian's own identity -- BT against market value / par -- and NOT the price level:
#
#     currency face   BT  ==  MV_base * fx / par * 100      (148 of the 154 govt+muni)
#     titles of F     BT  ==  MV_base * fx / par            (5 MXN + 1 BRL, ratio exactly 0.01)
#
# The identity alone cannot say what F is -- it holds for MXN (F=100) and BRL (F=1000)
# alike -- so F comes from an explicit per-currency registry and never from a sniff at the
# price. That is the PAR_YIELD_UNITS lesson: no threshold separates a 916.73 per-1000 quote
# from a per-100 one. Both registry values are corroborated inside the data itself: every MXN
# long description carries the token "MXN100" and the BRL carries "BRL1000", which
# ``tests/test_sovereign_universe.py`` asserts so the registry cannot drift from the source.
#
# Once F is known:   bt_per_100 = BT / (F / 100)      par_face = par * F
# so the five MXN prices (99.46-117.79) pass through unchanged and only the BRL is rescaled,
# 916.73 -> 91.673. The custodian's own yield made exactly this mistake -- DI = -23.1% on that
# bond against 6.45-8.41% for the five MXN -- so DI is not a usable cross-check there.
TITLE_FACE = {"MXN": 100.0, "BRL": 1000.0}
QUOTATION_TOL = 0.02          # the identity holds to ~1e-4 in practice; 2% is a loose fence

# Which issuer is the currency's OWN sovereign. This decides what a calibrated spread MEANS,
# never what it is. Patterns are per-currency, so a match cannot leak across currencies (the
# AUD "QUEENSLAND TREASURY CORP" holdings cannot match the GBP gilt pattern).
SOVEREIGN_ISSUER = {
    "USD": r"UNITED STATES TREAS|US TREAS|UTD STATES TREAS",
    "GBP": r"UK\(GOVT|UNITED KINGDOM\(GOVERNMENT",
    "JPY": r"\bJAPAN\b",
    "MXN": r"MEXICO|UTD MEX",
    "KRW": r"KOREA",
    "NOK": r"NORWAY",
    "SEK": r"SWEDEN",
    "SGD": r"SINGAPORE",
    "CAD": r"\bCDA\b|CANADA",
    "ILS": r"ISRAEL",
    "BRL": r"NOTA DO TESOURO|BRAZIL",
    "MYR": r"MALAYSIA",
    "DKK": r"DENMARK",
    "AUD": r"AUSTRALIA",
}
# EUR has many sovereign issuers and EUR_Yield_Curve.txt is a euro-area COMPOSITE (verified
# 2026-09-03: strictly between Germany and Italy at every tenor, and a debt-weighted
# six-country average reproduces it to 7bp mean / 18bp max), so a euro sovereign priced on it
# shows relative value against the euro-area average, not a spread over its own government.
_EURO_AREA = re.compile(
    r"GERMANY|BUNDERSREPUBLIK|FRANCE|NETHERLANDS|BELGIUM|IRELAND|BONOS Y OBLIG|SPAIN|"
    r"ITALY|AUSTRIA|PORTUGAL|GREECE|FINLAND", re.I)


def parse_desc_coupon(*texts):
    """Coupon rate in PERCENT parsed from custodian description text, or ``None``.

    Order: an explicit ``x%`` figure; then ``x DUE ...`` (the TIPS style: "2.00 DUE 07-15-2014");
    then the first standalone decimal that is not part of a date token ("FHLB ... 5.53
    11-03-2014"). Values outside (0, 25) are rejected. No number -> ``None`` (a data gap to flag).
    """
    for s in texts:
        if s is None or (isinstance(s, float) and pd.isna(s)):
            continue
        s = str(s)
        for pat in (_CPN_PCT, _CPN_DUE):
            m = pat.search(s)
            if m and 0.0 < float(m.group(1)) < 25.0:
                return float(m.group(1))
        no_dates = _DATE_TOKEN.sub(" ", s)
        for m in _DECIMAL.finditer(no_dates):
            if 0.0 < float(m.group(0)) < 25.0:
                return float(m.group(0))
    return None


def load_master_phase2(path):
    """The master ``Fixed Income`` sheet with the phase-2 column superset (all sub-categories)."""
    return _read_sheet(path, MASTER_SHEET, PHASE2_MASTER_COLS)


def _present(v):
    return not (v is None or pd.isna(v) or str(v).strip() in ("", "NULL"))


def _uniques(cls_rows):
    """One record per Asset ID: par / market value / book cost SUMMED across duplicate account
    legs (so BT == mv/par*100 holds per id), other fields first non-null."""
    c = cls_rows.copy()
    for col in ("par_value", "gold_mkt_value", "book_cost"):
        c[col] = pd.to_numeric(c[col], errors="coerce")
    agg = {col: "first" for col in c.columns if col != "asset_id"}
    for col in ("par_value", "gold_mkt_value", "book_cost"):
        agg[col] = "sum"
    n = c.groupby("asset_id").size().rename("n_rows")
    u = c.groupby("asset_id", as_index=False).agg(agg).merge(n, on="asset_id")
    return u


def _route_agency(r):
    cpn = r["coupon_pct"]
    if pd.notna(cpn) and cpn < ZERO_COUPON_MAX_PCT:
        return "zero"
    desc = f"{r['desc_short']} {r['desc_long']}"
    if r["has_call"]:
        gap = (pd.Timestamp(r["maturity"]) - pd.Timestamp(r["call_date"])).days \
            if _present(r["call_date"]) and pd.notna(r["maturity"]) else None
        if gap is not None and gap <= MAKE_WHOLE_MAX_GAP_DAYS:
            return "vanilla"                       # make-whole guard (corporate rule; none trigger)
        return "callable-lattice"
    if str(r["pay_freq"]).strip() == "Monthly" and _CMO_CLASS.search(desc):
        return "cmo-tranche"
    if _DATE_PAIR.search(desc):
        return "call-passed-vanilla"               # date pair, no AB -> call passed unexercised
    return "vanilla"


def _resolve_quotation(u):
    """Resolve the custodian's price / par quotation for one class frame.

    Inputs
    ------
    1. u : DataFrame -- one row per unique asset id, still carrying the golden columns
       ``gold_price`` / ``gold_mkt_value`` alongside ``par_value``, ``fx_rate``, ``currency``.

    Returns ``(quotation, par_face, bt_per_100)``, three Series aligned to ``u``:

    * ``quotation``  -- ``"currency-face"``, ``"titles-of-<F>"``, or a refusal label:
      ``"quotation-unregistered"`` (the identity says titles but the currency has no
      :data:`TITLE_FACE` entry), ``"quotation-unresolved"`` (neither form fits), or
      ``"quotation-underivable"`` (no par / price / market value to test with).
    * ``par_face``   -- the position restated as a CURRENCY FACE amount.
    * ``bt_per_100`` -- the custodian price restated per 100 of face, the only form any
      engine here accepts.

    A refusal is a LABEL, not an exception. The driver turns it into a named disposition, so
    a security whose quotation we cannot read appears in the output with a reason rather than
    disappearing -- the failure mode ``dataio.dispositions`` exists to prevent.
    """
    par = pd.to_numeric(u["par_value"], errors="coerce")
    mv = pd.to_numeric(u["gold_mkt_value"], errors="coerce")
    fx = pd.to_numeric(u["fx_rate"], errors="coerce").fillna(1.0)
    bt = pd.to_numeric(u["gold_price"], errors="coerce")
    face = u["currency"].astype("string").str.strip().str.upper().map(TITLE_FACE).astype(float)

    # market value is base-USD and fx is local-per-USD, so local MV = MV_base * fx
    implied = (mv * fx / par * 100.0).where(par.notna() & (par != 0))
    ratio = bt / implied

    as_face = (ratio - 1.0).abs() < QUOTATION_TOL
    as_titles = (ratio * 100.0 - 1.0).abs() < QUOTATION_TOL

    quotation = pd.Series("quotation-unresolved", index=u.index, dtype=object)
    quotation[ratio.isna()] = "quotation-underivable"
    quotation[as_face] = "currency-face"
    quotation[as_titles & face.isna()] = "quotation-unregistered"
    titles = as_titles & face.notna()
    quotation[titles] = "titles-of-" + face.where(titles).astype("Int64").astype(str)

    # ``face / 100`` first, then divide: for F=100 the divisor is exactly 1.0, so a price
    # already quoted per 100 passes through BIT-IDENTICALLY rather than picking up a
    # last-ulp wobble from multiplying and dividing by 100. Asserted with ``==`` in
    # tests/test_sovereign_universe.py, so the five MXN numbers are provably untouched.
    return quotation, par.where(~titles, par * face), bt.where(~titles, bt / (face / 100.0))


def _spread_meaning(currency, *texts):
    """What a spread calibrated on the currency's curve MEANS for this issuer.

    Returns ``"own-curve-anchor"`` (the issuer IS the currency's sovereign, so the number is a
    validation anchor and should sit near zero), ``"relative-to-euro-composite"`` (a euro-area
    sovereign against the composite EUR curve -- relative value, not credit), or
    ``"spread-over-government"`` (a foreign sovereign, a province or a municipality against the
    local government curve -- a genuine spread). A label, never an input: it cannot move a
    number, which ``tests/test_sovereign_universe.py`` asserts with ``==``.
    """
    ccy = str(currency).strip().upper()
    blob = " ".join(str(t) for t in texts if t is not None)
    if ccy == "EUR":
        return "relative-to-euro-composite" if _EURO_AREA.search(blob) else "spread-over-government"
    pattern = SOVEREIGN_ISSUER.get(ccy)
    if pattern and re.search(pattern, blob, re.I):
        return "own-curve-anchor"
    return "spread-over-government"


def _terms_note(*texts):
    """A documented contract feature the vanilla engine does not represent, or ``""``.

    This is a NOTE, not a route: the bond still prices. It exists so a feature we know about
    and deliberately did not model is stated on the row rather than left for a reader to
    notice from a duration that looks slightly wrong.
    """
    blob = " ".join(str(t) for t in texts if t is not None)
    if _SINKING_TOKEN.search(blob):
        return ("description documents a sinking fund; no schedule in our data, so priced as "
                "a bullet to maturity")
    return ""


def _route_sovereign(r):
    """Engine route for one government / municipal holding.

    Order matters and each step is a documented contract feature:

    1. **zero** -- BG below :data:`ZERO_COUPON_MAX_PCT`. This claims all 31 US Treasury STRIPS,
       including ``TNTD03983600`` "TREAS BD STRIPPED CALL", whose master call date EQUALS its
       maturity. That row would also survive step 3, but for the wrong reason, so it is
       claimed here where the reason is true.
    2. **floating-reference-unverified** -- the description says FRN and no reference rate or
       margin exists anywhere in our data. Not priced: see the driver's flag text.
    3. **coupon-schedule-unavailable** -- the description says STEP UP and we hold no coupon
       path. Same treatment the corporate book gives a step-up with no schedule.
    4. exercise rights -- a call strictly after maturity is a DATA ERROR and is named as one;
       a call on or within :data:`MAKE_WHOLE_MAX_GAP_DAYS` of maturity is the redemption
       itself, not an option, so the bond is a bullet; anything earlier is a real Bermudan.
    5. **vanilla** otherwise.
    """
    cpn = r["coupon_pct"]
    if pd.notna(cpn) and cpn < ZERO_COUPON_MAX_PCT:
        return "zero"
    desc = f"{r['desc_short']} {r['desc_long']}"
    if _FRN_TOKEN.search(desc):
        return "floating-reference-unverified"
    if _STEP_UP_TOKEN.search(desc):
        return "coupon-schedule-unavailable"
    if r["has_call"]:
        gap = (pd.Timestamp(r["maturity"]) - pd.Timestamp(r["call_date"])).days \
            if _present(r["call_date"]) and pd.notna(r["maturity"]) else None
        if gap is not None and gap < 0:
            return "call-after-maturity"
        if gap is not None and gap <= MAKE_WHOLE_MAX_GAP_DAYS:
            return "vanilla"
        return "callable-lattice"
    return "vanilla"


def build_phase2_universe(master, classes=None):
    """Per-class mini-universe for the three phase-2 classes (MBS counted only).

    Returns ``(bonds, recon, counts)``:
      * ``bonds`` — one row per unique asset id, classes agency/guaranteed/linker, with
        ``asset_class``/``group``/``route``/``flag``, terms (coupon decimal, freq int, maturity,
        call_date), position fields (par summed, ``is_short``), and for linkers
        ``real_coupon`` (decimal) + ``index_ratio0`` (= BG / description coupon @ the file date).
        Custodian golden marks are STRIPPED (input/truth separation, as the corporate universe).
      * ``recon`` — asset_id + gold_price / gold_mkt_value (summed) / gold_ytm.
      * ``counts`` — per class: rows, unique, negative-par rows, route counts (golden-testable).
    """
    m = master.copy()
    m["sub"] = m["sub_category"].astype("string").str.strip()

    classes = tuple(PHASE2_CLASSES if classes is None else classes)
    unknown = [c for c in classes if c not in SUBCATS]
    if unknown:
        raise ValueError(f"unknown asset class(es) {unknown}; known: {sorted(SUBCATS)}")

    frames, counts = [], {}
    for cls in classes:
        rows = m[m["sub"] == SUBCATS[cls]]
        counts[cls] = {"rows": int(len(rows)), "unique": int(rows["asset_id"].nunique()),
                       "negative_par_rows": int((pd.to_numeric(rows["par_value"], errors="coerce") < 0).sum())}
        if cls in COUNT_ONLY:                      # inventoried; engine awaits the Bloomberg pull
            continue
        u = _uniques(rows)
        u["asset_class"] = cls
        u["coupon_pct"] = pd.to_numeric(u["income_rate"], errors="coerce")
        u["freq"] = u["pay_freq"].astype("string").str.strip().map(FREQ_FROM_TEXT)
        u["maturity"] = pd.to_datetime(u["maturity_master"], errors="coerce")
        u["has_call"] = u["call_date"].map(_present)
        u["call_date"] = pd.to_datetime(u["call_date"].where(u["has_call"]), errors="coerce")
        u["is_short"] = u["par_value"] < 0

        if cls == "agency":
            u["group"] = "agency"
            u["route"] = u.apply(_route_agency, axis=1)
            u["real_coupon_pct"] = float("nan")
            u["index_ratio0"] = float("nan")
        elif cls == "guaranteed":
            u["group"] = "TLGP-guaranteed"         # own bucket: the credit is the FDIC guarantee
            u["route"] = "vanilla"
            u["real_coupon_pct"] = float("nan")
            u["index_ratio0"] = float("nan")
        elif cls in SOVEREIGN_CLASSES:
            # Sovereign and sub-sovereign paper both price on the CURRENCY curve, which for
            # every mapped file is that currency's government curve (EUR being a euro-area
            # composite). ``group`` separates the two for reporting only.
            u["group"] = cls
            u["route"] = u.apply(_route_sovereign, axis=1)
            u["real_coupon_pct"] = float("nan")
            u["index_ratio0"] = float("nan")
        else:                                      # linker
            u["group"] = "linker"
            u["real_coupon_pct"] = [parse_desc_coupon(t, q) for t, q in zip(u["desc_long"], u["desc_short"])]
            u["index_ratio0"] = u["coupon_pct"] / u["real_coupon_pct"]
            ok = u["real_coupon_pct"].notna() & u["index_ratio0"].between(*RATIO_SANITY)
            u["route"] = "ilb-indexation-unverified"
            u.loc[ok, "route"] = "ilb"
            u.loc[u["real_coupon_pct"].notna() & ~u["index_ratio0"].between(*RATIO_SANITY),
                  "route"] = "ilb-ratio-implausible"
        u["real_coupon"] = pd.to_numeric(u["real_coupon_pct"], errors="coerce") / 100.0
        # Quotation is resolved for EVERY class, while the golden columns are still here. The
        # three original phase-2 classes all resolve to "currency-face", which
        # tests/test_sovereign_universe.py asserts -- so this is inert for them by evidence
        # rather than by assumption.
        u["price_quotation"], u["par_face"], u["bt_per_100"] = _resolve_quotation(u)
        u["spread_meaning"] = [_spread_meaning(c, a, b) for c, a, b
                               in zip(u["currency"], u["desc_short"], u["desc_long"])]
        u["terms_note"] = [_terms_note(a, b) for a, b in zip(u["desc_short"], u["desc_long"])]
        frames.append(u)

    bonds = pd.concat(frames, ignore_index=True)
    bonds["coupon"] = bonds["coupon_pct"] / 100.0                    # decimal
    bonds.loc[bonds["route"] == "zero", "coupon"] = 0.0              # the 1e-5 strips are zeros

    for cls in classes:
        if cls in COUNT_ONLY:
            continue
        sel = bonds[bonds["asset_class"] == cls]
        counts[cls]["routes"] = {k: int(v) for k, v in sel["route"].value_counts().items()}
        counts[cls]["shorts"] = int(sel["is_short"].sum())

    # ``bt_per_100`` is a custodian mark restated, so it travels with the golden columns and
    # OUT of the pricing inputs -- the same input / truth separation the corporate universe keeps.
    truth = [c for c in list(GOLDEN_FIELDS) + ["bt_per_100"] if c in bonds.columns]
    recon = bonds[["asset_id", "asset_class", "price_quotation"] + truth].copy()
    bonds = bonds.drop(columns=truth)
    return bonds, recon, counts


def build_phase2_from_path(path, classes=None):
    return build_phase2_universe(load_master_phase2(path), classes=classes)
