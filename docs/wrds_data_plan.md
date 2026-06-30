# WRDS Data-Pull Plan

**Status:** execute-ready, **blocked on WRDS account reactivation** (account currently *inactive*).
**Environment:** ✅ ready on server 47 — `wrds` + `psycopg2-binary` installed in the `PengSX` conda env;
`wrds-pgdata.wharton.upenn.edu:9737` confirmed reachable from 47; golden suite still 26/26.
**Run location:** server 47 (has outbound to WRDS). Do **not** assume local Python.

Three pulls, all keyed off the URS holdings' **ISIN → CUSIP**, in priority/dependency order:

1. **Mergent FISD** — rescue the 135 MTN terms + callable call schedules → expand the canonical universe past 476.
2. **Enhanced TRACE** — actual 2009 market prices for the 20 distressed BB/B/CCC names (index OAS can't recover them).
3. **Industry × rating spreads** — self-built from FISD industry + TRACE prices → narrow the AA-bank "sector-vs-index" gap.

DAG: **1 → 2 → 3** (3 needs terms from 1 and prices from 2; 2 needs CUSIPs; 1 is standalone and highest value).

---

## 0. Connection + discovery (do this FIRST, every session)

Auth is via `~/.pgpass` on 47 (so the non-interactive Bash tool never hits a password prompt):
```
# ~/.pgpass  (chmod 600)
wrds-pgdata.wharton.upenn.edu:9737:wrds:<WRDS_USERNAME>:<WRDS_PASSWORD>
```
```python
import wrds
db = wrds.Connection(wrds_username="<WRDS_USERNAME>")   # reads ~/.pgpass, no prompt

# CONFIRM names before any bulk pull — do not trust the names in this doc blindly:
db.list_libraries()                                       # is it 'fisd'? 'trace'? 'wrdsapps'?
db.list_tables(library="fisd")
db.describe_table(library="fisd", table="fisd_mergedissue")   # exact column names + types
db.describe_table(library="fisd", table="fisd_redemption")    # where is the call SCHEDULE?
db.list_tables(library="trace")
db.describe_table(library="trace", table="trace_enhanced")
```
Everything below is the **best-known** schema as of writing; treat column names as *hypotheses* until
`describe_table` confirms them. Build the tested helper `src/dataio/wrds_pull.py` only after a smoke query succeeds.

### Conventions used throughout

**ISIN → CUSIP** (URS holdings are USD/US ISINs → middle-9 of the ISIN *is* the 9-char CUSIP):
```python
def isin_to_cusip(isin: str) -> str | None:
    # ISIN = 2-char country + 9-char NSIN + 1 check digit; for US/CA the NSIN == CUSIP(9).
    if not isin or len(isin) != 12 or isin[:2] not in ("US", "CA"):
        return None                      # non-US domicile: NSIN != CUSIP -> handle manually / flag
    return isin[2:11]
# illustration (PUBLIC example, not client data): US0378331005 -> 037833100  (Apple ISIN -> CUSIP)
```
**Join strategy:** prefer a **direct ISIN match** (`fisd_mergedissue.isin`) where populated; fall back to
the CUSIP-derived join on `complete_cusip` (9-char, FISD's primary key). Keep both match flags so we can
audit coverage.

**Data governance (hard rule):** the query *input* (the list of holding ISINs/CUSIPs) **is the client
portfolio** → it and all WRDS outputs stay **git-ignored**. Write pulls to `data/wrds/` (already ignored;
`*.csv/*.txt/*.parquet` are gitignored). Never commit CUSIP/ISIN lists or raw pulls.

**Reproducibility:** for every pull save a small manifest next to the data — `{pulled_at, wrds_username,
sql, row_count, n_input_keys, n_matched}` — so a re-pull is auditable (WRDS data is versioned/updated).

---

## 1. Mergent FISD — rescue MTN terms + callable schedules  *(highest priority)*

**Why:** the 135 master-only "MTN" bonds are excluded as `terms-unavailable` (coupon/maturity in *neither*
sheet). FISD has issue-level terms → rescue them and the canonical count rises above 476. Call schedules
feed the v2 callable model.

**Library:** `fisd`

| Table | Take | Use |
|---|---|---|
| `fisd.fisd_mergedissue` | `issue_id, issuer_id, complete_cusip, isin, offering_date, maturity, coupon, coupon_type, interest_frequency, day_count_basis, principal_amt, offering_amt, bond_type, security_level, redeemable, convertible, putable` | the **terms** to rescue MTNs + flags to refine the universe (zeros/floaters/convertibles) |
| `fisd.fisd_mergedissuer` | `issuer_id, sic_code, industry_group, industry_code, country_domicile, cusip_name` | **industry** classification for Part 3 |
| `fisd.fisd_redemption` | `issue_id, redemption flags, first call date/price, call type` (+ confirm the **full call-price schedule** table) | v2 callable inputs |
| `fisd.fisd_amount_outstanding` | `issue_id, amount_outstanding, effective_date` *(optional)* | liquidity weight for Part 3 aggregation |

**Codes to map (confirm against the FISD data dictionary):**
- `interest_frequency` (typical FISD): `1`=annual, `2`=semiannual, `4`=quarterly, `12`=monthly, `0`=at-maturity/zero → map to our `freq_n`.
- `coupon_type`: `F`=fixed, `V`=variable/floating, `Z`=zero (→ confirms our structured/floating exclusions independently).
- `day_count_basis`: real-world basis (often 30/360) — note vs our VBA **ACT/364**; potential future day-count refinement, *not* part of v1.

**Query skeleton:**
```python
holdings = load_universe(...)                     # the 732 unique bonds (asset_id, isin)
holdings["cusip9"] = holdings["isin"].map(isin_to_cusip)
keys = holdings["cusip9"].dropna().unique().tolist()

issue = db.raw_sql("""
    SELECT issue_id, issuer_id, complete_cusip, isin, offering_date, maturity,
           coupon, coupon_type, interest_frequency, day_count_basis,
           principal_amt, offering_amt, bond_type, security_level,
           redeemable, convertible, putable
    FROM fisd.fisd_mergedissue
    WHERE complete_cusip = ANY(%(k)s)
""", params={"k": keys})

issuer = db.raw_sql("""
    SELECT issuer_id, sic_code, industry_group, industry_code, country_domicile, cusip_name
    FROM fisd.fisd_mergedissuer
    WHERE issuer_id = ANY(%(i)s)
""", params={"i": issue["issuer_id"].dropna().unique().tolist()})
```

**QA gate (do this before trusting FISD for the 135 MTNs):** we already have terms for the 476 from the
`Corporate Bonds` tab. Join FISD to *those* and check FISD `coupon`/`maturity`/`interest_frequency` reproduce
the tab values (tolerance: coupon ±1bp, maturity exact). If the known-terms match rate is high, trust the
FISD join for the unknown MTNs; otherwise debug the key before rescuing anything.

**Output / success:** merge rescued terms into `dataio/universe.py` inputs, **re-run the funnel**; the
`terms-unavailable` bucket should shrink and `canonical` rise from 476. Persist call schedules to
`data/wrds/fisd_redemption.parquet` for v2. Log per-bond: matched / unmatched / still-missing-terms.

---

## 2. Enhanced TRACE — real 2009 marks for the 20 distressed names

**Why:** the 20 BB/B/CCC names are marked near-default by the custodian (BT ≈ 12–29). A rating-average index
OAS structurally cannot reproduce single-name distress → we need their **actual traded price**. This is the
only hard data that recovers them.

**Library:** `trace` (Enhanced TRACE) — academic-cleaned alternative: WRDS Bond Returns (`wrdsapps.bondret`
or similar; confirm name) for pre-aggregated daily/monthly prices.

| Table | Take |
|---|---|
| `trace.trace_enhanced` | `cusip_id, trd_exctn_dt, trd_exctn_tm, rptd_pr, yld_pt, entrd_vol_qt, rpt_side_cd, cntra_mp_id, trc_st, asof_cd` |

**Cleaning (required — `enhanced` ≠ `cleaned`):** apply the **Dick-Nielsen (2009/2014)** filters — drop
cancellations/corrections/reversals (`trc_st`/`asof_cd`), drop when-issued and special-condition trades,
de-duplicate interdealer double-counts. WRDS publishes sample cleaning code; port the filter set. Cross-check
the cleaned series against `bondret` where it exists.

**Window:** holdings are **2009-03-31** (the BT mark date) but our model curve is **2009-06-10**. Pull a
window spanning both — `2009-03-01 … 2009-07-31` — so we can (a) compare to BT at 3-31 and (b) mark at 6-10
for model consistency. Distressed names trade thinly → take the **volume-weighted last trade near the target
date**, and record the trade date used (the staleness matters).

**Query skeleton:**
```python
distressed = recon[recon.group == "HY"]            # the ~20 BB/B/CCC names from recon_oas.csv
dkeys = distressed["isin"].map(isin_to_cusip).dropna().tolist()

trace = db.raw_sql("""
    SELECT cusip_id, trd_exctn_dt, trd_exctn_tm, rptd_pr, yld_pt, entrd_vol_qt,
           rpt_side_cd, cntra_mp_id, trc_st, asof_cd
    FROM trace.trace_enhanced
    WHERE cusip_id = ANY(%(k)s)
      AND trd_exctn_dt BETWEEN '2009-03-01' AND '2009-07-31'
""", params={"k": dkeys})
# -> Dick-Nielsen clean -> per cusip, VWAP of last trading day on/before target date
```

**Output / success:** a per-name distressed mark table (`data/wrds/distressed_marks_2009.parquet`) used as the
**reconciliation benchmark for the 20 HY names** (replacing the index-OAS price that can't recover them).
Report how many of the 20 have any 2009 trades (coverage caveat: some may simply not trade).

---

## 3. Industry × rating spreads — narrow the IG "sector-vs-index" gap

**Why:** v1's residual is index-OAS *dispersion* (one spread per rating); the clearest example is AA bank debt
trading wider than the AA index. A finer **industry × rating** spread is the single real lever to push IG
below ~5%.

**Method — Z-spread by inverting our own engine (NOT a raw yield spread):**
The right measure is the **Z-spread**: the flat spread over our bootstrapped **2009-06-10 zero curve** that
reprices the bond. That is *exactly* the flat-spread input `price_bond(..., oas=s)` already takes (we currently
plug the ICE index OAS there). So compute it by **root-finding on our existing pricer**:
```python
from scipy.optimize import brentq
def zspread(price_mkt, val, mat, cpn, curve, freq):
    f = lambda s: price_bond(val, mat, cpn, curve, oas=s, freq=freq).clean - price_mkt
    return brentq(f, -0.05, 1.0)        # spread in decimal
```
For **option-free** bonds Z-spread ≡ OAS, so this is methodologically clean for the vanilla IG universe
(callables conflate the embedded option → those are v2 anyway, exclude here).

**Pipeline:**
1. Pull TRACE prices (Part 2 method, but for the **broad priceable universe**, not just the 20) around 2009-06-10.
2. Invert each to a Z-spread on our curve.
3. Attach FISD `sic_code`/`industry_group` (Part 1) + our rating bucket.
4. Aggregate **median Z-spread per (industry × rating)** cell (weight by amount-outstanding or volume; require a
   min cell count, e.g. ≥5 names, else fall back to the rating-only index OAS).

**Sanity check (validates the whole idea):** the **rating-only** median of these Z-spreads should land near
the **ICE BofA index OAS** we already use per rating. If it does, the industry split is trustworthy; if not,
debug before replacing anything.

**WRDS index sub-indices (route B):** WRDS *may* not carry ICE/BAML industry sub-index OAS (subscription-
dependent) — check `list_libraries`. The self-built route A above is the robust path and reuses our engine.

**Output / success:** an `industry × rating` spread dict for **2009-06-10**; re-run reconciliation substituting
it for the flat rating OAS on the IG set; measure whether the AA-bank (and overall IG) |diff%| narrows toward
<5%. This is v1.5/v2 territory — record the result either way.

---

## Open items to confirm on first live connection
- [ ] Exact library/table/column names (`describe_table`) — especially the **full call-price schedule** location in FISD, and the cleaned-TRACE product name (`bondret`?).
- [ ] FISD `interest_frequency` / `coupon_type` / `day_count_basis` code dictionaries.
- [ ] FISD ISIN-column coverage (drives ISIN-direct vs CUSIP-fallback split).
- [ ] WRDS subscription scope (is any ICE/BAML index library present?).
- [ ] TRACE coverage for the 20 distressed names in 2009 (some may not trade at all).
- [ ] After a smoke query succeeds → promote skeletons to a tested `src/dataio/wrds_pull.py` + golden-style row-count checks.
