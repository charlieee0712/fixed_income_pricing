# Missing-data registry (living table)

Created **2026-07-30** on Mario's directive. This file is THE table of every data field the model
needs but does not have: which securities, what fields, how the data lands (the zero-code-change
path), what the interim treatment is, and where each request stands. Update it whenever a gap
opens, a request goes out, or data arrives.

## Mario's directive (2026-07-30, WhatsApp — recorded verbatim gist)

> Remember how we typed the ISIN code for those securities using the chatgpt — we all know that
> this is not as precise as bloomberg. But we are building a tool with an all purpose application.
> What we need is the process itself to be automated and working, and secondly the fields of data
> that are not available to be specified on a table. So when we get new data with all in, then
> we'll run all what you've built.

Working rules derived:
1. **Bloomberg is the authoritative terms source.** The 2026-07-20 web/AI ISIN lookups
   (`docs/isin_lookup_2026-07-20.md`) are accepted as INTERIM values — see the provisional queue
   at the bottom: on any Bloomberg return, diff, let Bloomberg win, log the deltas.
2. **The deliverable is the automated process**, not hand-curated numbers: portfolio-specifics
   live in data tables (`data/*.csv`), engines stay generic.
3. **Every unavailable field is enumerated HERE** — this file is the "specified on a table".
4. **Data arrival = re-run** (`calibrate_risk.py` / `callable_risk.py` / `phase2_risk.py`), no
   code edits — except the two engines explicitly planned to be built on arrival (G1 driver
   wiring + pool routing; G2 amortizing loader/engine).

## Summary table (status @ 2026-07-30)

| # | gap | securities | blocks | lands via | status |
|---|---|---|---|---|---|
| G1 | Govt-MBS pool stats, 8 fields | 882 CUSIPs | whole Govt-MBS class (888 rows) | `PoolTerms.from_bloomberg` (+ driver/routing on arrival) | ⏳ Mario 07-22 · Liping 07-30 |
| G2 | pass-through amortization | 13 uniques (16 tab rows) | 13 corporate securities (out of output) | new schedule table + amortizing-vanilla engine on arrival | ⏳ Mario 07-20 · Liping 07-30 |
| G3 | FRN/hybrid terms | 11 (3 all-terms + 8 margins) | 8 BT-marked hybrids; 3 FRNs priced imprecisely | `frn_spreads.csv` / `hybrid_switch_terms.csv` — one cell each | ⏳ Mario 07-20 · Liping 07-30 |
| G4 | call schedule | 1 (AssuredGty US04622DAA90) | the unpriced 5th corporate callable | one `call_schedules.csv` row | ⏳ Liping 07-30 (first ask) |
| G5 | deferred / confirmation-only | KTBi · GBP+KRW curves · 5 AGY confirms · 1 rating quirk · FHR 3122 ZB | 1 ILB + 2-3 GBP bonds; rest = confirmation | curve txt rows / `call_schedules.csv` / master fix | ⏳ Liping 07-30 (opportunistic); standing plan = Mario MBS touchpoint |

Channels: **Mario** (client side, owns G1/G2/G3 since 07-20/07-22, no reply yet) and **Liping**
(colleague, occasional campus Bloomberg access; full request incl. BDP template sent 2026-07-30).
**Dedupe returns across the two channels before loading.**

## G1 — Govt-MBS pool stats: 882 CUSIPs × 8 fields

The `Govt MTGE` tab's analytics block is dead cached `#NAME?` (0/888) — the surviving mnemonics
(FB2:FI2) are the exact request, keyed `CUSIP + " Mtge"`, percent units:

`MTG_WACPN · MTG_WAM · MTG_STATED_WALA · MTG_AOLS · MTG_GEN_CPR_3M · MTG_GEN_CPR_6M ·
MTG_GEN_CPR_12M · MTG_HIST_COLLAT_CPR_LIFE`

- **As-of requirement:** holdings date = 2009-03-31; WAM/WALA/trailing-CPR are time-varying.
  Preference order: historical as-of values (field date override / BDH) → current values + pull
  date noted (WAM can be rolled back; WAC/AOLS ≈ static). Paid-off pools returning N/A is
  expected — leave blank, they route to the paid-down bucket in the routing方案.
- **Lands via:** `pricing/mbs.py::PoolTerms.from_bloomberg` ({mnemonic: value} rows, built
  2026-07-22, zero code change). Then planned work: pool routing方案 (REMIC Z / paid-down rows)
  + driver reconciled vs the BS golden (888/888 filled).
- **Files:** CUSIP list `outputs/govt_mtge_cusips.csv` (882 rows, `cusip,asset_id`); prewired
  formula sheet `outputs/govt_mtge_bdp_template.csv` (882 × `=BDP($C_,"<field>")`, opens straight
  into add-in Excel; regenerable from the CUSIP csv — WORKLOG 2026-07-30). Both git-ignored
  (`outputs/`), mirrored local+47, WhatsApp'd to Liping.

## G2 — Corporate pass-through: 13 unique securities (16 tab rows incl. duplicate holdings)

`Coupon_Formula2 = "Pass-through cash flow"`; excluded from the output since the 2026-07-20
meeting (`excluded-per-Mario: requires prepayment model`). All 13 are **scheduled-amortization
structures** (airline EETCs / private-placement pass-thru certificates), so the expected v1
treatment once schedules land is **amortizing-vanilla on a known principal schedule** (a true
prepayment model likely unnecessary — decide on arrival). Identified 2026-07-30 (workbook dump
on 47 — first time enumerated):

| asset_id | ISIN | security | cpn % | maturity (tab) |
|---|---|---|---|---|
| TNTD04007129 | US02378JAC27 | American Airlines 1999-1 Cl A-2 | 7.024 | 2011-04-15 |
| TNTD03021172 | US909287AA20 | United Air Lines 2007-1A Cl A | 6.636 | 2022-07-02 |
| TNTD03096416 | US247367BH79 | Delta Air Lines pass-thru | 6.821 | 2022-08-10 |
| TNTD04201221 | US210805BU05 | Continental 1997-4A | 6.900 | 2019-07-02 |
| TNTD04201277 | US210805CQ83 | Continental 1999-1 Cl A | 6.545 | 2020-08-02 |
| TNTD04201291 | US210805DD61 | Continental 2000-2 Cl A-1 | 7.707 | 2022-10-02 |
| TNTD04201293 | US210805DE45 | Continental 2000-2 Cl A-2 | 7.487 | 2012-10-02 |
| TNTD04492972 | US126650AW08 | CVS Caremark pass-thru (144A) | 5.298 | 2027-01-11 |
| TNTD04916068 | US126650BF65 | CVS Caremark pass-thru (144A) | 6.036 | 2028-12-10 |
| TNTD04356207 | US377672AA80 | Glen Meadow pass-thru (144A) | 6.505 | 2067-02-12 |
| TNTD04447809 | US87203RAA05 | Systems 2001 AT (BAE) Cl G (144A) | 6.664 | 2013-09-15 |
| TNTD04851923 | US87203RAC60 | BAE Systems 2001 AT Cl B (144A) | 7.156 | 2011-12-15 |
| TNTD04830158 | US84254QAA76 | Southern Capital 2002-1 Cl G (144A) | 5.700 | 2023-06-30 |

- **Fields needed per security:** current factor as of 2009-03-31 + the principal amortization /
  factor schedule (dates & amounts) + coupon/frequency confirmation.
- ⚠️ Several carry **expected vs legal-final maturity** discrepancies (master `BW` ≠ tab `C`:
  Continental 1997-4A 2018-01-02 vs 2019-07-02; 2000-2 A-2 2012-04-02 vs 2012-10-02; names quote
  "EXP" dates) — the schedule pull resolves which date governs; do NOT price these as bullets.
- **Lands via:** a new tracked schedule table (shape TBD on arrival, `call_schedules.csv`
  pattern) + amortizing-vanilla engine — the agreed on-arrival work (meeting 2026-07-20).

## G3 — FRN/hybrid missing terms: 11 securities

Full evidence + history in `docs/isin_lookup_2026-07-20.md` (its final table = this list).

**3 exempt US FRNs — ALL terms (index + margin + freq); zero public documentation.**
Interim: FRN-priced under the spread→0 convention (margin folds into implied OAS).
Lands via `data/frn_spreads.csv` (one row each → margin priced explicitly).

| asset_id | ISIN | security |
|---|---|---|
| TNTD03035014 | US61532RAA77 | Monumental Global Funding II 2005-C FRN, due 2010-06-16 |
| TNTD04955876 | US61532XAB29 | Monumental Global Funding III FRN, due 2014-01-15 |
| TNTD03080834 | US634902LH11 | National City Bank FRN, due 2010-01-21 (current cpn 1.2425% known) |

**8 hybrids — post-call/post-switch floating formula only (fixed leg fully sourced).**
Interim: BT-marked `hybrid-margin-unavailable` (never half-modelled). Lands via
`data/hybrid_switch_terms.csv` — the rows exist with empty margin cells; **one cell fill → the
bond prices on the hybrid engine, zero code change.**

| asset_id | ISIN | security | missing |
|---|---|---|---|
| TNTD04627285 | US76117JAB44 | Resona 5.85% perp (144A) | reset formula after 2016-04-15 |
| TNTD04509751 | US17133PAA66 | Chuo Mitsui 5.506% perp (144A) | reset formula after 2015-04-15 |
| TNTG023603W | XS0238543416 | BTMU 3.50% due 2015 | margin after 2010-12-16 call |
| TNTG527525U | XS0212517550 | Resona EUR 3.75% due 2015 | margin after 2010-04-15 call |
| TNTG532803U | XS0229704886 | Resona 4.125% perp | formula after 2012-09-27 call |
| TNTG532805U | XS0229705008 | Resona perp sister tranche | ALL terms (tranche type unresolved) |
| TNTG614042U | XS0244642889 | Shinsei LT2 10NC5 (144A) | margin after 2011-02-23 |
| TNTG614044U | XS0244642616 | Shinsei LT2 10NC5 (RegS) | same margin |

Immaterial footnotes (not blocking): Liberty US53079EAN40 freq/day-count; Bear US073928X243
day-count.

## G4 — Call schedule: Assured Guaranty US Holdings 6.4% due 2066-12-15

`TNTD04923866 / US04622DAA90`, BT 15.033 — the 5th corporate callable, the only one without a
`data/call_schedules.csv` row, hence unpriced (BT mark). **First requested 2026-07-30 (Liping)**
— absent from every earlier ask. Need: call schedule (dates + prices); given the 2066 maturity
and jr-sub profile, also check fixed-to-float terms (if so → `hybrid_switch_terms.csv` too).
Lands via: one CSV row → the BDT lattice prices it, zero code change.

## G5 — Deferred / confirmation-only items

Standing plan (2026-07-22): these wait for **Mario's** MBS-data touchpoint — do NOT re-ask him
before then. Asked **opportunistically of Liping 2026-07-30** (different channel, zero marginal
cost); the Mario-side deferral discipline is unchanged.

| item | ids | unlocks | lands via |
|---|---|---|---|
| KTBi indexation terms (index ratio / base CPI @2009-03-31) | TNTG673976U / KR1035027T36 | the 1 BT-marked ILB (`ilb-indexation-unverified`, $1.2M) | ratio_0 input to `pricing/ilb.py` |
| KRW govt par curve, 2009-03-31 row | — | KTBi at the 3-31 baseline (file has 06-10 only) | row in the KRW curve txt |
| UK Gilt par curve @2009-03-31 & 06-10 | — | FT-GBP (coupon path seeded) + 2 GBP calibration bonds (our GBP file has a non-arb 3y node) | replacement GBP curve file/rows |
| Agency call schedules (confirmation) | US3133XKKW43 · US3128X4BE02 · US3128X4UZ20 · US31359ML849 · US31359M2B87 | none — par@100-from-AB lattice already matches custodian AQ 4/5 | `call_schedules.csv` rows if they differ |
| FNMA 6.25 2011 rating quirk | TNTD04366584 / US31359MGT45 | senior-vs-sub identity behind the master's A/Aa2 | note / master correction |
| FHR 3122 ZB (REMIC Z, misfiled as AGY debenture) | TNTD04733316 | CMO-phase input (BT-marked now, no force-pricing) | DES terms for the future CMO engine |

## Provisional (web-sourced) values — Bloomberg confirmation queue

Per directive rule 1, every override value seeded from the 2026-07-20 public-source lookups is
**PROVISIONAL until Bloomberg confirms**. On any Bloomberg return covering these, diff →
confirm (note here) or override (Bloomberg wins; log the delta in WORKLOG + here). Sources and
confidence per value: `docs/isin_lookup_2026-07-20.md`.

- `data/coupon_schedules.csv` — 9 coupon paths (Aquila 11.875 · Comcast 6.95 · BT step path ·
  Sogerim 7.50 · TI-2012 7.25 · TI-2033 7.75 · Anglian 5.375 · RBS 6.00 · FT-GBP 7.50 floor).
- `data/frn_spreads.csv` — 4 margins (Bear L+40 Q · PNC L+14 Q · MS L+45 Q · IndepComm L+182).
- `data/hybrid_switch_terms.csv` — 10 documented switch/margin sets (Allstate · Lincoln ·
  Liberty · Chubb · AmEx · GE · SMBC · BofA · BNP · UniCredit).
- `data/make_whole_overrides.csv` — Sempra make-whole-only (SEC 424B2).

All were FULL/HIGH-confidence primary-source finds; the MEDIUM/LOW ones were never loaded — they
are the open items in G3 above.
