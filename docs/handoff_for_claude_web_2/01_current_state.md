# Current state

**2026-09-16 · main `01e0848` · 495 tests · all six non-securitised asset classes complete.**

*Rewritten rather than appended this refresh. The previous version had grown four dated
"update" sections and a reader had to reconstruct the present from strata. History lives
in `32_worklog_verbatim.md`; this file states today.*

---

## 1. The one-paragraph version

The legacy Excel/VBA fixed-income toolkit is ported to Python and **all six
non-securitised asset classes are priced end to end** — 1,040 of the book's 2,366 rows,
949 of its 2,260 unique securities. Everything runs on the `pricer/` template Mario
approved (core engines + thin asset wrappers + one JSON endpoint), reachable from a real
spreadsheet for five instrument types and from Python for eight products. What remains
is the **securitised block** — mortgage pools, CMOs, ABS, CMBS — which is 1,294
securities and is blocked on a Bloomberg data pull requested 2026-07-22. The newest
workstream is **Azure**: the code has been proven to run there, and the shape of a
shared environment for Mario's group is undecided.

---

## 2. Pricing coverage

⭐ **The `Summary` sheet is a FLAT pivot of `Asset sub category`. There is no "corporate
bonds" parent group** — `Corporate Bonds` is a sibling of `Government Bonds`, and the
master has exactly one `super_category` (`Fixed Income`).

| sub-category | rows | unique | status |
|---|---:|---:|---|
| Corporate Bonds | 811 | 732 | **566 in output @3-31** (555 priced + 11 at the custodian mark) |
| Government Bonds | 153 | 147 | done 2026-09-03 |
| Government Agencies | 42 | 39 | done; restructured 2026-09-10 |
| Index Linked Government Bonds | 16 | 15 | done; engine migrated 2026-09-10 |
| Guaranteed Fixed Income | 11 | 9 | done; restructured 2026-09-10 |
| Municipal/Provincial Bonds | 7 | 7 | done 2026-09-03 |
| **six non-securitised classes** | **1,040** | **949** | **COMPLETE** |
| Government MBS | 888 | 882 | engine skeleton, awaiting Bloomberg |
| Non-Government CMOs | 265 | 264 | not started |
| Asset Backed Securities | 79 | 79 | not started |
| Commercial Mortgage-Backed | 73 | 69 | not started |
| FI Derivatives + Other | 21 | 17 | out of scope |
| **Grand Total** | **2,366** | **2,260** | |

⚠️ **Corporate has THREE different totals and they are easy to confuse:** the master
sub-category is **811 rows / 732 unique**; the `Corporate Bonds` TAB is **676 rows / 616
unique** (60 ids listed twice — the F13 trap); our output is **566**.

### The five production outputs, and what each covers

| file | rows | driver | classes |
|---|---:|---|---|
| `implied_oas_2009-03-31.csv` | 566 | `calibrate_risk.py` | corporate |
| `implied_oas.csv` (the 6-10 control) | 561 | same | corporate |
| `callable_risk.csv` | 3 | `callable_risk.py` | corporate callables on the lattice |
| `phase2_risk_<date>.csv` | 63 | `phase2_risk.py` | agency 39 / guaranteed 9 / linker 15 |
| `sovereign_risk_<date>.csv` | 154 | `sovereign_risk.py` | government 147 / municipal 7 |

Plus **six dated disposition sidecars** (732 / 732 / 5 / 5 / 154 / 154) which name a
reason for every security that did not reach an output. ⭐ Rows, sha256 **and text
fingerprint** for all thirteen are in `41_release_facts_verbatim.md`. Quote that file.

---

## 3. Code structure

`src/pricer/` is the template Mario approved: **core** (the mathematics) + **assets**
(one short file per product, legacy units, no arithmetic) + **endpoints** (one request
in, one answer out).

```
core/pricing/    analytical  cashflows  discounting  coupon_schedule
                 tree  floating  hybrid  inflation          [prepayment PLANNED]
core/risk/       sensitivities
core/market/     spreads  curves
core/utils/      dates
assets/corporate/ bonds_input vanilla embedded_option callable puttable sinking
                  floating hybrid stepped
assets/government/ bonds_input linker agency guaranteed sovereign     [NEW 09-10]
assets/securitized/                                      [PLANNED, with the MBS phase]
endpoints/       main  contracts  pricing  dependencies
errors.py        the domain exception family
```

The legacy `src/pricing/*` modules are **thin shims that re-export the same objects**, so
every old import still works. ⚠️ `docs/shim_exit_policy_2026-08-31.md` has four exit
criteria and **criterion 1 is still unmet** — retire nothing.

⚠️ **`pricer/__init__.py`'s module map was stale for a whole round** (tree, callable and
floating marked `PLANNED` months after shipping). Rewritten 09-10, and **three tests now
hold it honest** — the load-bearing one being *nothing marked PLANNED may already exist*.
See `05` §1.21.

### ⭐ 8 / 7 / 5 / 5 — the distinction plans get wrong

| | count | which |
|---|---:|---|
| products the **engine** prices | **8** | the seven below + inflation-linked |
| types the **contract** can express | **7** | vanilla · stepped · floating · fixed_to_floating · callable · puttable · sinking |
| types the **VBA builder** can construct | **5** | minus stepped (no coupon-table cells) and fixed_to_floating (no switch-date cell) |
| verified by a **real-Excel round trip** | **5** | vanilla · callable · puttable · sinking · floating |

Until 2026-09-10 the first two were the same number. The gap is one named, reversible
decision — see §7.

---

## 4. The four rounds since the last bundle refresh

### 4.1 — 2026-09-03 · Government and Municipal/Provincial

The only two `no` marks in the `Summary` sheet's K column (`K23`, `K55`). **154 unique
securities, 147 priced at the 3-31 baseline, 150 at the 6-10 control** (KRW gains a curve
there). New driver `sovereign_risk.py`; `CURVE_FILE` grew 6 → 14 currencies; **390 → 423
tests**; all five pre-existing CSVs and all four sidecars byte-identical.

Three genuine findings, all in `23`:

* **The own-currency curve convention, locked** — and the decider was coverage, not
  taste: Ireland has no curve file, so a per-country rule would split 2 Irish holdings
  from 28 euro peers. Fable consulted before any code.
* ⚠️ **`EUR_Yield_Curve.txt` is a euro-area sovereign COMPOSITE**, verified by
  reconstruction to 7 bp mean. A euro sovereign's spread is relative value against that
  average, never an asset-swap spread. Output carries `spread_meaning` per row.
* ⚠️ **One price quoted per 1,000** (`TNTG630781W`, 916.73 → 91.673) — caught before
  shipping, and **the custodian made the same error**, so its own `DI` yield reads −23.1%
  and is not a usable cross-check there.

### 4.2 — 2026-09-10 · The government book onto the template

Mario's ask was Government Agencies and Index-Linked. **Guaranteed went with them by
decision**, because the three share ONE loader, ONE driver and ONE 63-row hashed CSV.

**63 securities before, 63 after; all 22 files in `outputs/` byte-identical after
re-running every driver. That invariance is the deliverable.** 424 → 468 tests.

* **Only the inflation-linked engine actually migrated** (`pricing/ilb.py` →
  `core/pricing/inflation.py`, body spliced not retyped). ⭐ **Government Agencies never
  had an engine of its own** — all five of its routes were already migrated in Rounds
  2a/2b. Overstating that is the round's one honesty risk and the report says so.
* `assets/government/` created — five modules, its own numbered input catalogue.
* ⚠️ `implied_spread_vs_nominal_bp` is **banned from being renamed `implied_oas`**; a
  test injects the banned name and fails.
* `check_representable` added to the agency lattice — the last hand-built lattice path
  without it. **Result: latent, not live.** All five schedules reach a node, nothing was
  refused, CSVs byte-identical. Reported as that rather than as a fix.
* ⭐ **Gate 0 was §1 of the instruction document and ran before any code** — the first
  round where the alignment gate was front-loaded. See `06` §6.

### 4.3 — 2026-09-13 · The interface was documenting numbers that rot

Prompted by the question "is the Excel/JSON interface in sync?", answered by measurement:
**nine of eleven committed fixtures reproduced byte-for-byte** after two rounds of
restructuring. Functionally, yes. The documentation was not:

* the input catalogue named **six currencies** where fourteen are priced — now computed
  from the registry;
* the interface document's header said **"194 automatic checks"** and **"Scope: vanilla"**
  while the README beside it in the same folder said 468 and seven types — the header no
  longer quotes a count at all;
* **"7 / 5 / 5" became "8 / 7 / 5 / 5"**, documented in a new §14.6.1.

⭐ And the new fixture test found something nobody knew: **the endpoint's JSON is not
byte-identical across platforms** for the lattice products, contradicting a CLAUDE.md
claim written when the endpoint was vanilla-only. See `24` §3. 468 → 483.

### 4.4 — 2026-09-15 · Azure, and the tooling that policed it

Mario wants the code on Azure so **"everyone in our group can run and test these codes"**.
One trial, in Cloud Shell:

```
Linux x86_64 | Python 3.12.14 | numpy 2.5.3 | pandas 3.0.5 | scipy 1.18.1
483 passed in 40.17s
```

⭐ **A whole major version of pandas ahead of the development machine, everything green.**
Also measured: **tier 2** — market curves and our override tables but **no client
portfolio and no proprietary workbooks**, 14 MB — runs **435 pass / 48 skip / 0 fail** and
prices a real bond. Mario has since said the data is not sensitive, so the repo was
cloned whole.

New: `scripts/platform_parity.py` and `src/dataio/output_digest.py`. ⚠️ **Both of the
parity tool's first two checks were themselves wrong** — a text digest built on pandas
(and the first machine ran pandas 3.0), and a tolerance report that could not distinguish
"zero deviation" from "compared nothing". Both fixed; see `24` §5–6 and `05` §1.27–1.28.
483 → **495**.

---

## 5. Test suite — 495

| file | n | file | n |
|---|---:|---|---:|
| `test_exception_wiring` | 83 | `test_price_convention` | 16 |
| `test_json_endpoint_dispatch` | 38 | `test_excel_fixture_parity` | 14 |
| `test_pricer_government_structure` | 34 | `test_monthly_curves` | 13 |
| `test_sovereign_universe` | 33 | `test_mbs` | 13 |
| `test_pricer_floating_structure` | 32 | `test_bootstrap` | 13 |
| `test_pricer_tree_structure` | 30 | `test_pricer_structure` | 12 |
| `test_lattice` | 29 | `test_universe` / `test_term_overrides` / `test_hybrid` | 11 each |
| `test_vanilla_json_endpoint` | 28 | `test_output_digest` | 10 |
| `test_callable_disposition` | 18 | `test_coupon_schedule` | 10 |
| | | the remaining six files | 36 |

⚠️ **`test_exception_wiring` is parametrised per SOURCE file**, so adding a module to
`src/` or `scripts/` raises the count by one without anyone writing a test. Several
"test count went up" lines in the history are that, and the commit messages say so.

**Real-Excel checks: 57 with no Python installed / 61 against a live engine.** ⚠️ Not
re-run since 2026-08-31 — nothing in the dependency chain changed, but it must run
before the next delivery that touches `endpoints/` or the `.bas`.

---

## 6. What is blocked, and on what

| blocked | on | since |
|---|---|---|
| Government MBS (882 securities) | Mario's 8-field × 882-CUSIP Bloomberg pull; `pricing/mbs.py` skeleton built and waiting | requested 2026-07-22 |
| CMOs / ABS / CMBS (411) | the MBS phase landing first | — |
| 8 hybrid securities | post-call margins (one CSV cell each → priced, zero code change) | 2026-07-20 |
| 3 exempt US FRNs | all terms | 2026-07-20 |
| The ILB worksheet | ⭐ **Mario choosing where three inputs sit on the sheet** | 2026-09-10 |

⚠️ **Deferred asks that must NOT be re-raised before Mario returns the MBS data:** KTBi
indexation terms + the KRW 3-31 curve row; agency call schedules (confirmation-only —
the par-call lattice already matches custodian AQ); the `TNTD04366584` rating quirk; the
`SteepFlat` file; `FHR-3122-ZB`.

---

## 7. Open decisions

1. ⭐ **The ILB worksheet layout.** The engine and wrapper are finished and deliberately
   unreachable from Excel, because the sheet has no cells for a real coupon, an index
   ratio or an inflation assumption. The 7/5/5 discipline exists to keep a type off a
   worksheet whose layout Mario has not chosen. **His answer unlocks it; nothing else
   does.**
2. ⭐ **Azure: which tenant, and which shape.** A personal free subscription on a
   university email is not where a group's shared environment belongs — not a
   sensitivity point, just that "everyone in our group" needs a tenant they can be added
   to. And his words point at *a shell each*, while his Excel proposal points at *a
   called service*. Worth asking directly. See `25` §6.
3. **Relocating `embedded_option.py`** out of `assets/corporate/`. It is mis-located, not
   mis-written — one lattice prices every optioned bond including a US Treasury. Trigger:
   a third non-corporate caller, or the securitized layer.
4. **`requirements.txt` has no upper version bounds.** Meeting pandas 3.0 was luck that
   paid off.
5. **`outputs/callable_risk.csv` is still undated** — a 6-10 run overwrites a 3-31 run.

---

## 8. Immediate next steps, as they stand

1. **Finish the Azure trial** — fix the Cloud Shell mount (region mismatch, `25` §5), then
   re-run `scripts/platform_parity.py --run` with the corrected text digest. ⚠️ **The
   Azure parity verdict is UNRESOLVED**; do not record one until that has run.
2. **Ask Mario the two questions** in §7.1 and §7.2, with the demo in hand.
3. **MBS remains the largest single unlock** — 882 securities behind one data pull.
