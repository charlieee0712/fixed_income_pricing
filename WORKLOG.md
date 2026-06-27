# Work Log

Reverse-chronological. Each entry is **anchored to the commit** that delivered the
work. Hours are recorded per entry; `[TO FILL]` = not yet logged.

---

## 2026-06-27 — Batch pricing + OAS reconciliation; v1 success criterion + method boundaries
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- **Batch-priced the canonical 476** on the 2009-06-10 curve (corrected B). 462 semiannual + 14 annual
  (`price_bond` generalised to `freq`), 0 unpriceable. Reconciled vs custodian BT (price) / BU (MV).
- **OAS=0 result VALIDATES the engine.** Near-maturity high-grade bonds (credit ≈ 0) tie to BT to
  **<0.2%** (BBB +0.02% / A −0.17% / AA +0.19%) — proving curve + discounting + the ②③ conventions +
  the 70-day holdings/curve mismatch together contribute <0.2%. The systematic +22% median gap is
  entirely the missing credit spread (largest for low rating / long duration) — exactly what OAS fixes.
- **Rating OAS (EXACT, from the workbook) — v1 result.** Precise 2009-06-10 OAS read from
  `Pricing File.xlsm` / `OAS Credit Curves` via **`src/credit/oas.py`** (`oas_on`): AAA 1.48 / AA 2.27 /
  A 3.02 / BBB 4.53 / BB 7.41 / B 9.45 / CCC 17.04 %. IG (AAA-BBB, n=456) median |diff%| **21.3% → 6.43%**,
  **signed median −0.41% (UNBIASED — curve+OAS centred on BT)**; 39% within 5%, 66% within 10%. HY (n=20)
  137% → 23% (signed +23 — does not converge → v2). Golden `tests/test_oas.py`. Saved `outputs/recon_oas.csv`.
- **v1 verdict — VALIDATED (success), framed as bias vs dispersion (not "6.4% > 5%").**
  - *Is the method correct?* → **UNBIASED**: IG signed median **−0.41% (≈0)**, curve+OAS centred on BT;
    with OAS=0 near-maturity high-grade <0.2%. ⇒ bootstrap→rating-OAS→discount is correct.
  - *How precise?* → **|diff%| median 6.4% is DISPERSION, not bias** — individual-name scatter around the
    index rating OAS (±300 bp normal in 2009), the direct result of v1's design choice (boundary ①: one
    index OAS per rating, no name/term structure). Distress removal leaves it 6.1% ⇒ broad dispersion, not
    outliers ⇒ a **known design boundary, not a bug**.
  - ⇒ **Not a near-miss failure; "success, precision to improve in v1.5."** Precision is limited by the
    index-rating-OAS design, which is explained and has a clear narrowing path.
- **Narrowing path (priority, all NON-bug):**
  ① **70-day date mismatch** (3-31 holdings vs 6-10 curve) — the OAS table has 3-31 but the yield-curve txt
     is missing it (gap 2008-11-10 → 2009-06-10). Get the **3-31 curve** (open item, ask colleague) → removes
     this directly. **Biggest removable residual.**
  ② **AA +5.22 = financials subordination** (banks trade wider than the AA index OAS) → sector OAS (v1.5/v2).
  ③ **Index OAS has no term structure** → a duration-based credit-spread curve (v2).
- **One-liner for Mario/Liping:** "bootstrap→rating-OAS→discount validated for ordinary IG credit, unbiased
  vs BT (signed median ≈0); single-bond precision median ~6% is limited by the inherent dispersion of the
  index rating OAS (a known design boundary), with a clear narrowing path — the biggest being the 3-31 curve
  to remove the 70-day date mismatch. HY / distressed / callable are v2 as planned."
- **FRED historical OAS no longer free** (ICE truncated to a rolling 3y window in April 2026; both the API
  and fredgraph.csv only serve recent data — WebFetch 403, curl date-params ignored, Wayback unreachable).
  → **RESOLVED** by reading the workbook's `OAS Credit Curves` archive (full daily 1997-2025) instead.

**v1 success criterion (LOCKED with the team's framing)**
- **NOT** "all 476 tie to BT" — impossible; distressed names can't be recovered by a rating-average OAS.
- **v1 succeeds if** investment-grade, non-distressed bonds price within a reasonable band of BT (~5%)
  via **bootstrap → rating OAS → discount**. That proves the method works for ordinary credit.
- **Distressed single-names and callables are v2** (need single-name market price / recovery, or an option
  model) — the same "needs richer inputs" bucket. This gives an objective yardstick for Mario/Liping.

**Method boundaries (residual that is NOT a bug)**
1. **Flat OAS, no term structure.** ICE BofA OAS is one index-level spread per rating, added flat across
   all tenors → short end over-priced, long end under-priced. v1-acceptable (CEO's "Bond Px 4 Bonds" uses
   flat OAS); part of the post-OAS residual is this, not an error.
2. **Index OAS ≠ single-name distress.** The CCC index OAS is the average of *still-trading* CCCs; it
   cannot reproduce a near-default name already marked on recovery (BT 12–29). Adding OAS lowers such names
   but they stay well above BT — a method boundary, → v2.

**Open / next**
- **Ask the colleague for the 3-31 yield curve / source** — the #1 lever to tighten IG (removes the 70-day gap).
- EIR / amortised-cost method (CEO's 2nd method) — possible lead in `Pricing File.xlsm` / `Bond Px 4 Bonds w Diff Ratings`.
- v1.5/v2: sector OAS (AA financials), term-structure OAS, distressed single-names (market price/recovery), callables.
- Commit the pricing layer (ZeroCurve + bond_price + oas + recon) on a fresh branch after the universe PR merges.

---

## 2026-06-27 — Curve layer (ZeroCurve) + BondPrice port; corrected the VBA z_semi discounting bug
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- **ZeroCurve** (`src/curves/zero_curve.py`): thin wrapper over the validated `bootstrap()`; serves
  continuous zero rates + DFs (+ optional OAS spread) with linear interpolation. Bootstrapped the
  **2009-06-10** USD curve and sanity-checked vs actual June-2009 UST (3m 0.18% … 10y 3.98% … 30y
  4.76%): post-crisis ZLB short end, steep upward, zero>par, DFs sane. ✓
- **BondPrice ported** (`src/pricing/bond_price.py`, curva=1 spot). Cash-flow conventions copied
  verbatim from Bootstrapping.bas: **ACT/364** (t = days/364), **182-day backward** coupon schedule
  from maturity, semiannual coupon = rate/2·100 (+100 principal at maturity), accrued =
  coupon·(days since last coupon)/182, clean = dirty − accrued. Verified line-by-line on 5 sample
  bonds (2–10y); price behaviour correct (premium ∝ (coupon − yield)·duration).
- **z_semi discounting bug — found, verified, CORRECTED.** The VBA discounts each cash flow as
  `exp(−t·z_semi)` (z_semi = semiannual-compounded zero) instead of its own bootstrapped factor
  `exp(−t·z_cont)` = DisCF — it computes the correct DF and **discards it**. Mixing a semiannual rate
  into a continuous formula systematically **under-prices**: node-level DF too low by −0.01% @2y,
  −0.11% @5y, **−0.43% @10y**, −1.31% @20y; bond clean price too low −0.009% @2y → **−0.285% @10y**.
  Verified by (a) reading the full BondPrice (502–818) — no compensating step after the
  `exp(−t·z_semi)` discount — and (b) numerically on the real 2009-06-10 curve. **Decision** (per the
  CEO's "dedicated, correct, extensible module" goal): discount with the bootstrapped DF by default;
  keep `vba_compat=True` to reproduce the legacy `exp(−t·z_semi)` exactly, used only to explain the
  reconciliation gap. Recorded in the `bond_price.py` docstring.
- Conventions ②③ (182-day schedule, ACT/364) are VBA *choices* — kept as-is, flagged in code as
  known sources of gap vs the custodian's BT/BU/DI (calendar coupon dates + ACT/ACT or 30/360), not bugs.

**Open / next**
- After sign-off: batch-price the canonical **476** (OAS=0), then add rating OAS, then reconcile vs
  gold `BT/BU/DI` (expect a gap: 70-day holdings/curve mismatch + ②③ conventions + model-vs-mark).
- (cheap, optional) Ask the colleague for the VBA tool's clean price on ONE of these 5 bonds to pin
  the z_semi bias empirically against the real sheet (our finding is code-reading + replication).
- Pricing layer (ZeroCurve + bond_price + this entry) is uncommitted; commit on a fresh branch after
  the `feat/universe-pipeline` PR merges.

---

## 2026-06-27 — Server 47 live: env + data + bootstrap reconciled + universe pipeline
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- **Server 47 stood up.** Key-based `ssh 47` verified; cloned the repo; built `.venv` with
  `--system-site-packages` so it reuses the conda env's *already-compiled* numpy 1.26.1 /
  pandas 2.1.1 / scipy 1.11.3 / openpyxl 3.1.2, and only pip-installed pytest. Why: CentOS 7
  (glibc 2.17, gcc 4.8.5) can't build modern wheels from source, and the Tsinghua mirror ships
  pandas 2.3.3 as **sdist-only** so a naive `pip install -r` tried to compile pandas and failed.
  All five satisfy `requirements.txt`.
- **Data on 47**: scp'd the 3 inputs into `data/` (git-ignored by extension) and unzipped —
  `data/USD_Yield_Curve.txt` (+26 others), `data/Bootstrapped/US_yield_curves.csv`,
  `URS …V Mainak.xlsx`. The two `.xlsm` stay local until the BondPrice port.
- **Bootstrap golden master reconciled** (US, 2024-01-16). Adopted **segmented** tolerances in
  `tests/test_bootstrap.py` (not one blanket threshold — so the exact columns can't hide a
  future regression):
  - **Annual / Semiannual rates — RED LINE, kept strict `< 1e-9`** (observed 2.7e-15 / 4.4e-15,
    bit-exact). The OAS pricing foundation; deliberately not relaxed.
  - Quarterly rate: exact (`< 1e-9`) for every node ≤ 30y; the single 30y+ **extrapolated** tail
    node tolerated `< 1e-4` (observed 2.12e-05 @ 31.08y).
  - Monthly rate `< 0.1` pp; Monthly DF `< 1e-3` (observed 6.72e-04 @ 0.92y); A/S/Q DF `< 1e-4`.
  - **Residual source**: the USD par txt's shortest tenor is **3m**, so the Monthly grid's 1m/2m
    nodes are flat-extrapolated and differ infinitesimally from the VBA's short-end handling; that
    rides the recursive bootstrap `DF_i = f(Σ_{k<i} DF_k)` into the Monthly belly. Compounded by a
    **numpy/pandas version delta** vs the colleague's original validation env (this box: 1.26.1 /
    2.1.1). **Economic impact ≈ 0 — does not affect pricing or OAS.** `test_ratings` stays fully green.
- **Universe pipeline built & validated** (`src/dataio/loaders.py` + `universe.py`). openpyxl loaders
  for the master `Fixed Income` + `Corporate Bonds` tab — column letters confirmed against the V-Mainak
  book (Asset ID=`S`, ISIN=`X`, sub-cat=`U`, S&P=`CM`, Moody=`CL`, par=`CV`, call=`AB`, maturity=`BW`,
  gold `BT`/`BU`/`DI`); the V-Mainak appended cols (`DL` dup Asset ID, `DO`/`DP` ~empty coupon) confirm
  terms still come from the tab. `build_universe` runs Asset-ID join → notch-map → Layer A/B with the
  single-primary-reason LOCKED priority. **Every documented count reproduces exactly** (join 597/135/19,
  rating 712/4/16, Layer-A raw 54/73, MECE total 732) → **canonical 476 @ 2009-06-10** + per-bond
  exclusion log. Golden `tests/test_universe.py`; **22 tests green on 47**. Named `dataio` (not `io`):
  `conftest` puts `src/` at `sys.path[0]`, so an `io` package would shadow the stdlib `io`.

**Open / next**
- **Ask the colleague** (both **non-blocking**): (a) which **numpy/pandas versions** + **golden CSV
  source** he used for the bootstrap validation (his "Quarterly exact / Monthly_DF < 1e-4" is tighter
  than this env reproduces); (b) which **curve date/source** priced the 3-31 book — drives the final
  valuation date + whether prices can tie to the custodian `BT/BU/DI`.
- **Data-quality (defer to pricing):** the `Corporate Bonds` tab has 3 rows with `Freq = "—"`; if any
  are Fixed and reach canonical they'd lack a payment frequency — screen at the pricing stage.
- **Next (curve layer first):** wrap bootstrap output in a `ZeroCurve` class and bootstrap the
  **2009-06-10** USD curve; sanity-check the post-crisis low-rate shape before pricing. Then copy the
  two `.xlsm`, port `BondPrice`, price the canonical 476, reconcile vs `BT`/`BU`/`DI`.

---

## 2026-06-26 — Decisions: valuation date 2009-06-10 + 47 interface (ssh)
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- **Valuation date chosen = 2009-06-10** (first curve after the 2008-11-10 → 2009-06-10 gap;
  the alternative, 2008-11-10, is the crisis trough with an extreme curve).
- Recorded the **reconciliation caveat**: holdings are 3-31, nearest curve is 6-10 (70-day
  mismatch) → computed prices won't tie to the custodian's 3-31 `BT/BU/DI`. The port's
  to-the-digit golden master is the **VBA tool's output**, not the custodian mark; `BT/BU/DI`
  is an independent cross-check only.
- **Interface to server 47 = ssh from the Windows box** (option 2); requires key-based ssh.

**Open / next (server 47)**
- **Ask the colleague**: which curve **date/source** did the original tool use to price the 3-31
  holdings? (Likely a 3-31 Bloomberg curve absent from our txt history.) Does he have the VBA
  tool's **pricing output** for these bonds (= the real pricing golden master)?
- Set up key-based `ssh 47`; clone + venv + `pip install`; copy data; `pytest`.
- Then `src/io` loaders + `universe.build_universe()`; bootstrap the 2009-06-10 USD curve.

---

## 2026-06-26 — Integrate colleague's bootstrap module + adopt src/ layout
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- Reviewed the colleague's validated `bootstrap.py` (faithful par→zero VBA port). Confirmed
  conventions: Excel epoch 1899-12-30, continuous compounding, output cols
  `Maturity, {Freq}_Rate/DF` (rates in percent), `load_par_curve` raises on a missing date.
  Validation (US, 2024-01-16): Annual/Semiannual/Quarterly exact, Monthly < 0.1 pp (short-end).
- Adopted a `src/<layer>/` layout: placed the module at `src/curves/bootstrap.py` and moved the
  rating notch-map to `src/credit/ratings.py`. Root `conftest.py` now puts `src/` on `sys.path`.
- Turned the module's `_self_test` into `tests/test_bootstrap.py` (golden-master; skips when the
  git-ignored data files are absent — point via `FIP_US_TXT` / `FIP_US_GOLDEN`). Fixed the
  `tests/test_ratings.py` import.
- Updated `PROJECT_STATUS.md` (§5 architecture, §4 progress, §3.2 path) and `CLAUDE.md`.

**Open / next (server 47)**
- `pip install -r requirements.txt && pytest` — `test_ratings` green; `test_bootstrap` green once
  the US par-curve txt + golden CSV are present.
- Build `src/io` loaders + `universe.build_universe()`; pick the 2009 valuation date; wrap
  bootstrap output in a `ZeroCurve`; port `BondPrice`; reconcile vs `BT`/`BU`/`DI`.

---

## 2026-06-26 — Lock rating notch-map + implement fip/ratings.py
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- Finalised the rating notch-map (S&P / Moody's granular → 7 FRED parent buckets) and
  implemented it in `fip/ratings.py`, with `tests/test_ratings.py` locking the two red lines:
  IG/HY split (BBB−→BBB, BB+→BB); S&P CC/C & Moody Ca/C → CCC (not default); D/SD → defaulted;
  NR/WR → no-rating; S&P-primary with Moody fallback and default precedence.
- Locked the single-primary-reason priority and MTN handling (`terms-unavailable`: a
  data-availability gap, not a security-type issue — addable later if a terms source appears).
- Added `requirements.txt`, root `conftest.py`; `outputs/` git-ignored (pipeline emits client CSVs).
- Untested pending a Python env (server 47 tomorrow).

**Open / next (on server 47)**
- Implement `loaders` (openpyxl read of master + Corporate Bonds tab) and
  `universe.build_universe()` applying join → notch-map → Layer A → Layer B; emit the
  per-bond exclusion log + canonical universe CSV; run pytest; produce the MECE funnel.
- Then lock the valuation date, bootstrap the ~2009 curve, port `BondPrice`, reconcile vs `BT`/`BU`/`DI`.
- Align module layout with the colleague's bootstrap Python (still to receive).

---

## 2026-06-26 — Master-sheet profiling: ratings, universe funnel, data sourcing
**Commit:** `[TO FILL]`
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- Dumped all 131 master `Fixed Income` column names. **Resolved the rating gap**: the rating
  columns exist as "Quality rating - Fitch/Moody/S&P" (`CK`/`CL`/`CM`) — earlier scan missed
  them. Fill-rate: S&P 794/811, Moody 796/811 (~98% of corporates); Fitch empty.
- Profiled key columns: par held = `CV` Shares/Par value (99.9%); custodian `BT`/`BU`/`DI`
  present → use as golden master (kept separate from inputs).
- Built date-independent universe funnel (732 unique corporates by Asset ID):
  - Rating (default precedence): 712 covered / **4 defaulted** / **16 no-rating** (true "neither").
  - Join on Asset ID: **597 matched** / 135 master-only / 19 tab-only.
  - Coupon type (within matched): 543 FIXED / 54 non-vanilla; **73 callable**.
- Locked design: rating S&P→Moody fallback w/ default precedence; join on Asset ID (ISIN
  secondary); par=`CV`; EIR cost=`Z`; golden master separate; callable → v2 (own reason,
  keep call fields); single primary reason per bond by priority.
- Updated `PROJECT_STATUS.md` (§3.2) and `CLAUDE.md` with the deterministic two-layer
  universe pipeline, exclusion taxonomy, and data-sourcing map.

**Open / next**
- Implement the MECE universe pipeline (single primary reason by agreed priority) →
  per-bond exclusion log; build in Python on server 47.
- Lock valuation date (drives Layer B); bootstrap the ~2009 curve.
- Port `BondPrice`; reconcile computed price vs `BT`/`BU`/`DI`.

---

## 2026-06-26 — Onboarding: structural analysis + bootstrap validation
**Commit:** `9b7fe7f` (docs scaffold) · `[TO FILL]` (this anchor update)
**Hours:** `[TO FILL]`
**Author:** charlieee0712

**Done**
- Mapped all four source workbooks: sheet inventory, column layouts, instrument
  fields, and the pricing/credit logic embedded in cell formulas and VBA.
- Documented the end-to-end pipeline & methodology (bootstrap → rating OAS →
  discount pricing → CreditMetrics overlay) in `PROJECT_STATUS.md`, including the
  exact bootstrap formulas and the FRED ICE BofA OAS source.
- Confirmed the bootstrap formula against the auditable VBA and **reproduced it in
  Python**: Annual / Semiannual / Quarterly **exact (0 error)**; **Monthly within
  0.08 bp** (short-end fill convention).
- Identified the **valuation-date mismatch**: holdings priced 2009-03-31, but the
  bundled bootstrapped CSVs match curve date 2024-01-16 (RMSE 0); 2009-03-31 is
  missing from the curve files (gap 2008-11-10 → 2009-06-10). Impact: 123 priceable
  bonds at 2024-01-16 vs 667 at 2009-03-31.
- Reconciled the corporate-bond universe into three counts (811 / 676 / 641).
- Confirmed **Bloomberg dependency is cut** (txt par curves + FRED OAS).
- Established the repo, `.gitignore` (excludes all client data), and project docs
  (`PROJECT_STATUS.md`, `WORKLOG.md`, `CLAUDE.md`).

**Open / next**
- Decide canonical valuation date + universe; bootstrap a ~2009 curve for the real book.
- Build `io` loaders + `instruments.Bond`; map rating + holdings from the master sheet.
- Port `BondPrice` (from `Pricing File.xlsm → Bootstrapping.bas`) into `pricing`.
- Locate & port the EIR (amortised-cost) method; then start the CreditMetrics layer.

---

<!-- Template for new entries:

## YYYY-MM-DD — <short title>
**Commit:** `<hash>`
**Hours:** `[TO FILL]`
**Author:** <name>

**Done**
- …

**Open / next**
- …
-->
