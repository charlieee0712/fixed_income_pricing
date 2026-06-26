# Work Log

Reverse-chronological. Each entry is **anchored to the commit** that delivered the
work. Hours are recorded per entry; `[TO FILL]` = not yet logged.

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
