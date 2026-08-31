# CLAUDE.md — persistent context for this project

Operating memory for future sessions. Read `PROJECT_STATUS.md` (full methodology +
architecture) and `WORKLOG.md` (history) alongside this. Keep this file terse and
high-signal; update it when a stated fact changes.

## What this project is
Port a legacy Excel/VBA fixed-income pricing toolkit to a structured, scalable
**Python** module. **Corporate bonds = first reference implementation**; must extend
to MBS/CMBS/ABS/CMO/callables and a CreditMetrics risk layer.
Repo: `github.com/charlieee0712/fixed_income_pricing` (keep **private** — references a client portfolio).

## Fable advisor — consult SPARINGLY (user, 2026-08-25)
`fable` = a **strategic second opinion** (Agent tool, model `fable`), not a workhorse. Consult it
only when a call is **hard to reverse**, **sets the direction of a whole workstream**, or **leaves
this repo as a recommendation** (Mario / Liping / the client) — e.g. locking a convention every
validated number rests on (ACT/364 grid; dirty-vs-clean duration base), redefining the method
(index-rating OAS → per-bond calibration, 2026-06-30), choosing a baseline (3-31 vs 6-10), fixing an
architecture / rollout shape (the `pricer/` template layout), or signing off a headline verdict
before it ships in a deliverable (the `legacy-stale-session` call on the 2010 batch). Bring the
question, the genuine options, and the evidence already in hand; the reply is **advice, not
authority** — verify it against repo code/data, then record the DECISION (+ why) in
`WORKLOG.md`/here, not merely that we asked, and tell the user in one line what was asked and what
came back. One consult per decision; if no answer could change what we do, don't ask.
**NOT for routine work:** implementation, file/sheet inspection, debugging, running or fixing tests,
funnel counts and other bookkeeping, doc / handoff / PDF updates, or "am I done?" completion
checks — those are decided here, from the repo.

## Claude-web handoff — TWO bundles (planning sync; user, 2026-08-25)
- ⚠️ **Refresh protocol: ONLY when the user explicitly asks ("更新handoff")** — never
  auto-refresh at milestones/comms changes (user, 2026-08-17). Both bundles are git-ignored
  when zipped, and BOTH stay OUT of the Drive staging copies (internal comms framing — not
  for Mario).
- **`docs/handoff_for_claude_web_1/`** (was `docs/handoff_for_claude_web/`, renamed
  2026-08-25) = **the DECISION bundle**: **13 files**. ⚠️ **The "keep it short" rule was
  REPEALED by the user 2026-08-30** ("handsoff1也不需要太短 尽可能包含决策端所需的重要信息") —
  the split with h2 is now by **purpose, not length**: h1 carries everything needed to
  **decide** (state · numbers · locked decisions · the numerical laws · open asks · traps ·
  feedback on its own plans), h2 everything needed to **specify** (engine internals, code map,
  module conventions, environment). New content still displaces stale content. Curated (update
  in place, REPLACE the NEW list — never append): `00_START_HERE`,
  `01_current_state_and_open_items`, `02_locked_decisions_and_conventions` (its **§D = the
  numerical laws**, added 08-30), `10_glossary`, **`12_traps_and_plan_feedback` (NEW 08-30 —
  Part A silent failures in cost order, Part B the five habits)**.
  Verbatim (re-copy every refresh): 03←`PROJECT_STATUS.md` · 04←`WORKLOG.md` ·
  05←`COVERAGE.md` · 06←`docs/missing_data.md` · 07←`docs/phase2_methods_2026-07-22.md` ·
  08←**the ACTIVE Mario-facing report** (now `docs/weekly_report_2026-08-30.md`) · 09←Mario's template txt · 11←`docs/monthly_recon_report_2026-08-17.md`.
  Zip → `handoff1_<date>.zip`. Precedence inside: 01 wins over the verbatim copies.
- **`docs/handoff_for_claude_web_2/`** (NEW 2026-08-25) = **the DEEP bundle**: cap **40
  files**, no length limit per file, the reference web-Claude PLANS FROM. 32 files today.
  **Last refreshed 2026-08-30** (user: "全面更新handsoff两个包") — h1 3,367 lines /
  `handoff1_2026-08-30.zip` 110 KB · h2 7,548 lines / `handoff2_2026-08-30.zip` 228 KB.
  Structure: `00`-`07` orientation (START_HERE · current state · locked decisions ·
  conventions/laws · open asks · **traps & gotchas** · **feedback on previous plans** ·
  glossary) + `10`-`22` per-domain deep dives (architecture · engines fixed/tree/floating ·
  curves · universe · data & overrides · JSON-Excel · testing · Monthly recon · environment ·
  comms · deliverables) + `30`-`40` verbatim (CLAUDE.md · PROJECT_STATUS · WORKLOG ·
  COVERAGE · missing_data · weekly report · round-2 report · interface v1 · Monthly mapping ·
  phase2 methods · Mario's template). Zip → `handoff2_<date>.zip`.
  **Two files there are the point of the whole bundle:** `05_traps_and_gotchas` (the
  silent-failure list — Excel serials, the 365.25-vs-364 axis, VBA `Null`, Edge writing no
  PDF, staging copies breaking pytest, and **since 08-30 §1.9-1.11: the GBP par-yield units
  bug, the driver's silent `skipped=N`, and the cross-platform convexity noise floor**) and
  `06_feedback_on_previous_plans` (what the two 2026-08-25 plans got wrong + the four habits:
  name a count's SOURCE and POPULATION; never leave a modelling choice to "the caller"; never
  assert code state — schedule a gate check; name the silent-failure modes — **plus habit 5,
  added 08-30: a claimed data gap needs evidence from the SOURCE, not from our own error
  message**; §4's five Round-2b carry-overs are now closed and scored).
- Supersedes the single root `HANDOFF_FOR_CLAUDE_WEB.md` (removed the day it was born,
  2026-08-15). Structure originally copied from the user's csi1000 `handoff_2` pattern.

## ⭐ Deliverables — audience & toolchain (user, 2026-08-25)
- **The Google/cloud team now ATTENDS the briefing in person**, alongside Mario — they no longer
  just receive the code afterwards. Every outward report must therefore serve two audiences at
  once: **plain language throughout** (define each bond term in a clause where it first appears —
  "callable = the borrower may repay early"), plus **one clearly-labelled engineering section**
  (architecture, the single entry point, how to run it, determinism, parallelism) that the finance
  reader can skip. Say in the opening which section is for whom. Never assume fixed-income
  vocabulary; never talk down to Mario either.
- **Package = the git-ignored staging FOLDER `code_structure_sample/` only. ⚠️ NO ZIP
  (user, 2026-08-31: "google drive可以直接传folder") — Drive uploads folders directly, so
  zipping was pure overhead. All packaging zips were deleted; regenerate none.** Contents:
  numbered docs (`00_README` · `01_weekly_report` md+PDF · `02_code_walkthrough` md+PDF ·
  `03_json_excel_interface` · `04_previous_report` · `05_round_detail` ·
  `06_delivery_evidence`) + `src/ tests/ scripts/ integrations/` copied in (robocopy `/E`,
  **never `/MIR`** — the path guard rejects it; and `Remove-Item` must be its own command,
  the guard reads `/E` in a combined line as a path). User drags the folder to Drive.
  **Refresh the folder's doc copies after ANY late edit to the source docs** — the 08-31
  audit corrected five numbers in the weekly report *after* the folder was built.
  Same for the handoff bundles: `docs/handoff_for_claude_web_1/` and `_2/` are folders the
  user uploads; their zips are gone too and are only worth rebuilding if claude.ai ever
  needs an archive rather than files.
- **PDF = `python scripts/md_to_pdf.py --input X.md --output Y.pdf`** (2026-08-25). One local
  command; the old pandoc@47 → HTML → local-Edge dance is RETIRED (local Python has `markdown`,
  Edge is installed). The script carries three Edge flags that each fail **silently** —
  `--headless=new` (the bare `--headless` writes NO pdf in current builds while still exiting 0),
  a throwaway `--user-data-dir`, and `--no-pdf-header-footer`. Don't re-derive them.
- **Self-review the md against the real outputs before rendering** (user's standing instruction):
  every number in a report must be traceable to a run, not to memory.

## Code-structure migration (Mario directive 2026-08-15) — STATUS: sample APPROVED 2026-08-25
- **Directive:** code "difficult to follow, a bit nested"; a **Google team takes over for
  cloud-computing optimisation** ⇒ many SIMPLE functions (not one complicated), **inputs
  highlighted** per function. Template = `docs/code_structure_template - Ver Aug 5 2026.txt`
  (core/ 80% engines + assets/ 20% thin wrappers + endpoints/). Reference + future golden =
  the **Monthly sheet** (`Project Pricing Fixed Income Instruments.xlsm`): rows 47–60 demo =
  per-metric simple functions (`CorpBondOAS`/`CorpBondDuration`/`CorpBondwidening`…), rows 61–98 =
  input dictionaries (Input No/Field/Options/Description + used-flags; Daycount "not used" =
  compatible with our ACT/364), row 99+ = **~2,600-bond legacy golden** (`bondcalc` analysisType
  1–6 → OAS/Dur/Widen/Tighten/Steep/Flat cols P–U, vol/Vega V/W/Y/Z; mostly VAL 2010-03-01 with
  that day's 6-ccy Libor+swap par curves on-sheet; also Bloomberg-OAS col AD + diff AG). Mario:
  our results can be **checked against this sheet** ⇒ reconciliation = proposed next validation
  milestone. [08-15 decode partly superseded 2026-08-17 — Gate 0 found the golden rows do NOT
  price on the on-sheet Libor/swap curves; see the Monthly-recon section below.]
- **Sample DONE (`241e76f`, 2026-08-15) — vanilla chain only (user: sample-first, rest after Mario
  OKs):** `src/pricer/` = template shape (`core/pricing/{cashflows,discounting,analytical}`,
  `core/risk/sensitivities`, `core/market/{spreads,curves}`, `core/utils/dates`,
  `assets/corporate/{bonds_input,vanilla}`); `pricing/{bond_price,calibrate,risk}.py` = thin
  SHIMS (same objects, all old imports/drivers unchanged); float-op order preserved ⇒
  bit-identical; assets layer = legacy-unit per-metric functions (percent/bp) mirroring the
  Monthly demo block + `INPUT_CATALOGUE`. **153 green** (+8 structure locks), 10.3s. Deliverable
  staging `code_structure_sample/` + zip (git-ignored like `corporate_bond/`): plain-language PDF
  report (`docs/code_structure_sample_2026-08-15.md`; pandoc@47 + Edge headless) + code + README —
  user uploads to Drive. Report asks Mario: rollout order (floating→callable→Monthly recon→
  ILB/AGY→MBS), `bons_input` naming, where dataio lives, endpoints=batch-first.
- **Rollout rules when approved:** migrate module-by-module, shims keep old surface until retired,
  full suite green at every step, float-op order preserved (no numeric drift), docstrings carry
  the numbered Inputs blocks, new code imports `pricer.*` (never the shims).
- **FOLLOW-UP ROUND DONE (2026-08-25) — JSON/Excel interface v1.** Mario approved the sample with
  three follow-ups (currency · yield volatility · an Excel↔JSON↔Python process); user's plan =
  `docs/vanilla_json_excel_followup_final_execution_plan_2026-08-25.md` (its §16 = the execution
  revision made here after the alignment gate + one Fable consult). Built, all ADDITIVE (no engine,
  shim or driver touched ⇒ every number unchanged; **166 → 194 green**): `src/pricer/endpoints/`
  (flat — `main.analyze_vanilla_payload(payload)->response` · `contracts` normalise/validate/
  envelope · `pricing` 7-step orchestration, zero formulas · `dependencies` = the only
  environment-aware file) + `core/market/curves.resolve_curve/curve_id/CurveUnavailable` (the
  reusable routing seam; drivers keep their own FREQ_VARIANT maps this round) + `currency` as
  input 5 of `bonds_input` + `scripts/price_json.py` (file in/file out, exit 0/1/2) +
  `integrations/excel_vba/` (bridge .bas · VBA-JSON v2.3.1 MIT vendored · runner_example.cmd ·
  README · REAL fixtures) + `tests/test_vanilla_json_endpoint.py` (28).
  **Contract decisions that must not drift:** ① two operations — `calibrate_and_risk` (clean price
  → implied OAS; still REFUSES a supplied OAS = the methodology lock) and `price_at_oas` (spread →
  price, the legacy per-metric flow); ② **dates must be ISO STRINGS** — a numeric Excel serial is a
  hard error because `pd.Timestamp(39903)` = 1970-01-01 (silent wrong-date pricing); ③ `face_value`
  echoed but NOT applied (everything is quoted per 100); ④ volatility + day_count accepted, echoed,
  reported unused with **null (never 0)** sensitivities; ⑤ no silent USD fallback — CURVE_NOT_FOUND
  (no file / no date row) vs CURVE_BUILD_FAILED (GBP 3-31 = not arb-free) are different codes; ⑥ no
  path, traceback or payload in any error message; ⑦ parity asserted with `==` vs direct calls.
  **Excel side TESTED on real Excel (2026-08-25):** `integrations/excel_vba/tests/Run-BridgeTests.ps1`
  + `TestHarness.bas` drive the VBA in a hidden Excel instance — **23/23**: import + Scripting
  Runtime ref · cells→request JSON with Excel serials 42750/39903 → "2017-01-15"/"2009-03-31" ·
  runner invoked AND waited for · every output cell == the engine's real numbers · error response
  shows its message and clears stale numbers. The script temporarily enables "Trust access to the
  VBA project object model" and restores it in a finally block; needs NO Python (a `.cmd` returning
  the committed fixture stands in). **It found a real bug on first run:** JSON `null` reaches VBA as
  `Null`, not `Nothing`, so `Set x = Field(response, "applicability")` raised "Object required" on
  EVERY error response ⇒ fixed with a `FieldObject` accessor (now a regression check). Untested link
  remaining: Excel calling a LIVE Python runner + the MsgBox/file-picker paths (not drivable headlessly).
  Docs: `docs/vanilla_json_excel_interface_v1.md` (reference) +

  `docs/code_structure_followup_json_excel_2026-08-25.md` (decision record). **Mario's three
  comments are recorded in §1 as the user RECALLED them (paraphrase, not a transcript — treat the
  wording as approximate):** ① "what happens if the volatility of yield changes — for OAS and for
  price?" (he asked for the EFFECT, and the doc answers it: vanilla = exactly none, structurally;
  callable = lower price at fixed spread + higher OAS at fixed price, the two numbers reserved for
  that engine) · ② "add currency to our input" · ③ our code runs in our own Python env — can he and
  the Google team "create ways from Excel to run Python code, to pass these inputs and parameters?"
  with his own proposal Excel/VBA → JSON per bond → Python, "one JSON in, one JSON out" (hence the
  single-bond canonical unit and the refusal of batch).

## Round 2a — one shared tree: callable / puttable / sinking (2026-08-25) — FRN = Round 2b
- **Plan** `docs/round2_monthly_q62_q71_execution_plan_v2_post_json_2026-08-25.md`; its **§21 =
  the execution revision** (authoritative over the body). **Split decided here: FRN + endpoint
  dispatch → Round 2b next week**; this week's headline (Mario's volatility answer) is entirely a
  tree story, the tree cluster shares ONE migration across three wrappers, and sinking (the only
  new modelling) needed the budget. Gate-0 freeze taken full-width (FRN + hybrids included).
- **Q62:Q71 VERIFIED in the workbook:** row 61 = header; rows 62-71 carry the analysisType NUMBER
  in col **P** and the label in col Q; row 67 shows this is input #1 `AnalysisType`. Mapping =
  1 Bullet · 2 Callable · 3 Puttable · 4 SinkingF · 5 OAS · 6 Duration · 7-9 FRN · 10 Mtge.
- **Code:** `core/pricing/tree.py` = the lattice MOVED VERBATIM from `pricing/lattice.py` (now a
  shim; identity-asserted) + `schedule_times()` + `bond_tree()`. `assets/corporate/` gains
  `embedded_option.py` (the ONE shared surface: price/OAS/duration/dv01/convexity/widening/
  tightening + the two volatility experiments) and thin `callable.py` / `puttable.py` /
  `sinking.py`. **194 → 223 green**; all three production CSVs SHA256-identical after every
  code-bearing commit.
- **⚠️ `to_lattice_schedule` still DEFAULTS to 365.25 d/y** while the coupon grid is ACT/364. Both
  drivers pass `days_per_year=364.0` explicitly (production is fine), but a new caller taking the
  default puts exercise dates on the WRONG axis — always route new code through
  `core.pricing.tree.schedule_times`. Fixing the stale default = a follow-up, not this round.
- **Call/put conflict rule ADDED (it did not exist):** the core applies `min(call)` then
  `max(put)`, so a put above a call on one date silently won for the holder. Now refused at the
  wrapper layer (core float path untouched). Same-date call+sink also refused (untested order).
- **SINKING = issuer optional redemption, fractions of OUTSTANDING**, one node rule where the call
  cap fires: `cont <- (1-f)*cont + f*min(cont,P)`. `fraction_basis="original"` is REFUSED (it
  needs a strip decomposition — one callable sub-bond per sink date — because only the outstanding
  basis keeps value-per-unit level-free and the node path-independent on a recombining tree).
  f=1 reduces to the call cap BIT-FOR-BIT; f=0 = straight; value non-increasing in f. **NOT
  amortisation** — no `Sinking=Yes` holding was rerouted; the 13 pass-through securities stay
  data-gated.
- **Monthly reality check (`docs/monthly_q62_q71_non_mortgage_mapping_2026-08-25.md`):** route
  census callable **464** / put **7** / sink **18**, and **ALL 474 are in the stale 2010-03-01
  batch — ZERO in the sound 2012-12 cohort** ⇒ *no numeric golden exists for these families*;
  validation is production parity + `==` direct-call parity + invariants + Bloomberg three-way.
  Also: the plan's "FLOATING 426" is NOT in this extract (`mty_typ` 0, `calc_typ_des` 29) — 426 is
  the URS production count; **2b must re-derive its FRN cohort.**
- **Mario report:** `docs/code_structure_round2_embedded_options_2026-08-25.md` — the volatility
  answer on the one genuinely call-active holding (6.45%/2034, BT 90.04): price 90.4229/90.0426/
  89.5161, OAS 414.52/410.77/404.84bp at vol 10/15/20% (≈10c of price or 1bp of spread per vol
  point); the other two callables are far from the call and move <0.1bp — so a portfolio-level
  vega would mislead.
- **Round 2b carry-over:** FRN → `core/pricing/floating.py` + wrapper; endpoint `instrument_type`
  dispatch for callable/puttable/floating in ONE change. ⚠️ `hybrid.py` imports FRN **privates**
  (`_as_date`, `_df`, `YEAR_DAYS`, `simple_forward`) — the shim must re-export them.

## Round 2b — Mario's pivot column F: floating / hybrid / stepped (2026-08-30) — DONE
- **The ask (meeting ~2026-08-27):** Mario annotated a NEW column **F** on the workbook's
  **`Pivot of Corp Bonds`** sheet (sheet6; the column did not exist in the committed file — it
  arrived with the 08-27 working-tree change). F5 (`F`, 617) = **"finished"**; F21 (zero) =
  "just corp bond(fixed)"; rows 6-11 + 17-19 + 22 left BLANK; and **six rows marked "no"** =
  the ask: **F12** Fixed→Floating 5 · **F13** stepped 7.00/7.50 2 · **F14** GBP LIBOR+Spread 1 ·
  **F15** Reference Rate+Spread 12 · **F16** EURIBOR+Spread 9 · **F20** Step-up schedule 1.
  **= 30 tab rows → 29 held → 23 priced / 6 not** (5 `hybrid-margin-unavailable` + 1 defaulted).
  ⚠️ **"finished" means IN THE NEW `pricer/` STRUCTURE**, not "priced" — every one of these
  already priced in the legacy layer since July. Rows 6-11 (`Fixed → Reset`, 6 tab/6 held/3
  priced) came free: same engine, not part of his ask — report as adjacent.
- **Migrated verbatim (body asserted byte-identical below the docstring), old paths = shims:**
  `pricing/frn.py`→`core/pricing/floating.py` · `pricing/hybrid.py`→`core/pricing/hybrid.py`
  (only its 2 import lines repointed; `pricing.bond_price.price_bond` IS
  `analytical.price_fixed_rate_bond`, a pure alias) · `pricing/coupon_schedule.py`→
  `core/pricing/coupon_schedule.py`. ⚠️ **The frn shim MUST re-export the privates**
  `_as_date/_rate/_df/simple_forward/YEAR_DAYS` — hybrid imports them by name.
  Also closed a real layering violation: `core/pricing/cashflows.py` imported `coupon_at`
  from the legacy `pricing` package (core reaching upward); now a sibling import.
- **Wrappers:** `assets/corporate/{floating,hybrid,stepped}.py` + `bonds_input` inputs 15-17
  (`switch_date`, `float_freq`, `current_coupon`), `spread_over_libor`→**`quoted_margin_bp`**
  (now USED), and `VOLATILITY_NOT_APPLICABLE` = a per-product reason (was one generic line).
- **Endpoint: ONE contract change, seven types** (`bond.instrument_type`: vanilla · stepped ·
  floating · fixed_to_floating · callable · puttable · sinking). `analyze_payload` is the new
  public name; **`analyze_vanilla_payload` kept as an alias and a typeless payload is still
  vanilla**, so the VBA bridge + its 23 Excel checks pass UNCHANGED (re-run and verified).
  `schema_version` 1.0→1.1. Doc = `docs/vanilla_json_excel_interface_v1.md` **§14**.
- ~~**FRN duration has TWO exact regimes and the SIGN flips**~~ **SUPERSEDED 2026-08-31 — the
  two regimes were a BUG, not a property.** They are now ONE: the running coupon is frozen
  under the bumps whether supplied or projected, so duration is **+**time to next reset either
  way. (Was: supplied → +to next reset; omitted → −time SINCE last reset, because the bump
  repriced a coupon already fixed at the last reset.) See the hardening section below.
- **223 → 287 tests** (390 after the 08-31 hardening). New: `test_pricer_floating_structure` (31), `test_json_endpoint_dispatch`
  (29), +4 bootstrap. Production parity re-run after EVERY code-bearing commit: all five driver
  CSVs byte-identical, except the deliberate GBP delta below.
- **⚠️ Excel scope = THREE different numbers, never "the spreadsheet can ask for any of seven"
  (measured 08-31 by driving `BuildRequest`):** **7** supported by the engine + contract · **5**
  constructible by the VBA builder (not `stepped` — no coupon-table cells; not
  `fixed_to_floating` — no margin/switch cells) · **4** tested from real Excel (vanilla,
  callable, puttable, sinking). `floating` is constructible only margin-absent, so the
  current-coupon input is unreachable from the sheet. Closing it = 1 named table + 3 cells,
  layout-neutral — deliberately NOT done, the worksheet design is Mario's to answer.

## Round 2b delivery-quality pass (2026-08-31) — two more silent omissions, closed
- **Plan** `docs/cc_next_instruction_round2b_delivery_quality_and_tree_excel_bridge_2026-08-30.md`;
  its **§26 = the Gate-0 revision** (authoritative over the body). Workstream A (hardening) is
  DONE; **Workstream B (Excel bridge for callable/puttable/sinking) is NOT started** — the plan
  mandates a checkpoint between them and says A ships even if B is dropped.
- **⭐ `TNTD04920858` was priced by NOTHING** (US828807BX41, 5.00% 2012-03-01, callable at par
  from 2011-12-02, gap **90d**; held, par 850k, MV 723,542, BT 85.12, A−/A3). `universe` sent
  gap ≤7d to vanilla and excluded the rest as `callable`; `callable_risk.py` took only gap
  >366d. **Two files owning half a decision each.** In no output, no document, no message. It
  was in the WORKLOG once as a *"minor loose end"* and then fell out of every count.
  **Fix = separate the responsibilities, NOT align two numbers:** routing decides candidacy,
  the driver consumes ALL candidates (`GAP_DAYS` deleted), the tree/wrapper decides
  representability.
- **⭐ Its "option value = 0.000000" was the option NEVER BEING EVALUATED.** The lattice
  exercises on coupon dates and never at root/maturity; a call inside the FINAL COUPON PERIOD
  lands on no node ⇒ `call_array` all-`inf` ⇒ silently prices as a straight bond.
  `ExerciseScheduleNotRepresentable` + `check_representable` now refuse it, **before any spread
  solving**, from `embedded_option._prepare` AND from the driver's hand-built path (one rule,
  two callers), **each right checked separately** (a live put must not license a dead call).
  ⚠️ **The guard tests REPRESENTABILITY, not economic activity** — `fraction = 0` on a sinking
  date is a legitimate contract; a first version broke 2 Round-2a tests by conflating them.
  Endpoint maps it to `VALIDATION_ERROR` + `bond.<right>_schedule`, never `CALIBRATION_FAILED`.
  **All 8 bonds with call schedules verified unaffected — latent, not live.**
- **`src/dataio/dispositions.py` — `reconcile()` over SETS, not counts.** Both drivers run it at
  run time: corporate `population=732 = 565 in-output + 167 named`, callable `5 = 3 + 2`.
  A **terminal** exclusion reason is a disposition; a **routing** reason (`callable`,
  `floating` 32, `special-fixed` 3) is only discharged when the destination honours it.
  Sidecars `outputs/{corporate,callable}_disposition.csv` = intentional structural additions.
- **⚠️ COUNTING CORRECTION — the tab has 676 ROWS but only 616 unique SECURITIES** (60 asset IDs
  listed more than once). `F13`'s "2 rows" are the SAME bond `TNTD04283895` twice. The chain is
  **30 pivot ROWS → 29 SECURITIES → 29 held → 23 priced + 6 named**; the 30→29 step is a
  DUPLICATE LISTING, not an unheld row. The plan, both handoff bundles and the 08-30 report all
  said "2 tab rows, 1 held" — corrected in the report; **the handoff bundles still carry it**
  (no auto-refresh) and must be fixed at the next explicit refresh.
- **Evidence:** `docs/client_directive_pivot_column_f_2026-08-27.md` (provenance — ⚠️ column F is
  IN the tracked workbook, sheet6, committed `a5f7c81`; a screenshot was not the only evidence)
  + `docs/column_f_delivery_matrix_2026-08-31.md` (four populations · six cells · the 6 unpriced
  named · the 29-security table · reconstruction manifest · fresh-run engine evidence) +
  `scripts/column_f_audit.py` (regenerates it).
- **287 → 300 tests**, green locally and on 47; five driver CSVs byte-identical at both dates;
  Excel 23/23. **DEFERRED and named:** an exercise-only lattice node vs a documented
  short-gap⇒vanilla rule. The 0.000000 supports NEITHER — it came from non-exercise.

## Workstream B (2026-08-31) — the Excel bridge sends callable / puttable / sinking
- **DONE.** No second bridge, parser, endpoint, contract or workbook design. `PriceBond` /
  `BuildRequest` / `PopulateOutputs` are the generic path; **`PriceVanillaBond` /
  `BuildVanillaRequest` / `PopulateVanillaOutputs` remain as thin wrappers** and a sheet with
  no `FIP_InstrumentType` builds the **byte-identical v1.0 vanilla request** — which is why
  the original 23 checks pass UNMODIFIED (incl. the "not used by vanilla" wording; that
  sentence now names whichever type the engine echoed, leaving vanilla identical).
- **New optional cells:** `FIP_InstrumentType` · `FIP_Operation` · `FIP_OASBp` (read **ONLY**
  for `price_at_oas` — the calibrating operation refuses a supplied spread) ·
  `FIP_SinkingFractionBasis` (never defaulted). Extra outputs `FIP_Engine` /
  `FIP_InstrumentTypeUsed` / `FIP_VolatilityUsed`.
- **Schedules = named Excel TABLES** (`FIP_CallSchedule`, `FIP_PutSchedule`,
  `FIP_SinkingSchedule`) so they can be any length on any sheet ⇒ **the bridge does not
  depend on the layout Mario has not chosen**. Blank row ignored; **partly-filled row =
  an Excel-side error naming table+row, before Python**; ISO dates only; order preserved;
  nothing sorted/deduped/inferred/defaulted; empty optional table omitted.
- **⭐ A whole class of misleading errors closed, found while generating the fixtures.** The
  call/put conflict came back as `CALIBRATION_FAILED` blaming `market.clean_price_per_100`.
  All exercise-terms refusals are raised as `ValueError` inside the engine, so `_spread`
  caught every one of them. They are now the **`ExerciseTermsError`** family, each carrying
  the JSON path, mapped by the endpoint to `VALIDATION_ERROR` + that field:
  put-above-call→`bond.put_schedule` · sink/call clash→`bond.sinking_schedule` · two prices
  on one date / entirely-post-maturity / grid-can't-place→`bond.call_schedule` ·
  basis→`bond.sinking_fraction_basis`.
- **Excel checks 23 → 48 (no Python) / 50 (live).** The two live-only: a full callable round
  trip reproducing the endpoint exactly, and **the volatility direction driven from the sheet
  — 639.58 / 635.78 / 629.83 bp at 10/15/20%** (three ordinary calls; no scenario operation).
- **7 fixture pairs in `integrations/excel_vba/examples/`, ALL generated by running the live
  endpoint.** ⚠️ **puttable + sinking are SYNTHETIC and labelled everywhere** — no URS holding
  is either. ⚠️ My first harness expectations were transcribed from an earlier single-call
  test instead of the fixtures ⇒ 3 failures. Quote from the run, not from memory.
- **302 pytest.** Interface doc §14.6 = a four-layer table separating "the bridge can send
  this" from "the daily-use worksheet exists" — only the first is true for the tree types.
  **The final layout stays Mario's open question.**

## Round 2b HARDENING + release (2026-08-31) — DONE, 390 tests
Directive `docs/cc_post_round2b_review_hardening_and_release_instruction_2026-08-31.md`;
Gate-0 revision recorded in its §14 BEFORE implementation (6 adjustments).
- **⭐ THE ONE INTENTIONAL NUMERICAL CHANGE — FRN running coupon frozen under risk bumps.**
  It was fixed at the last reset ⇒ a curve bump cannot change it. Supplied → already frozen;
  projected → the bump repriced it ⇒ **the sign flipped**. Now frozen either way, via a
  **base-curve proxy** read off `FrnResult.cashflows[0][2]` (true stub start, margin already in).
  Placed in `frn_risk_metrics`, **NOT** `price_frn` — keeps the par-under-any-shift telescoping
  invariant. At shift 0 the proxy == the old value ⇒ **price and OAS cannot move**. 6 of 7
  floaters moved, all +, each = one period × 100/P to within 3%; 4 stay negative (deep-discount
  spread-annuity = real economics). Doc `docs/frn_current_coupon_freeze_2026-08-31.md`.
- **THIRD "two owners, one decision" found & closed — `defaulted` names a COUPON CLASS *and* an
  EXCLUSION REASON**, with a recovery path keyed on each ⇒ `TNTD03067251` (8.78M par, 3 legs,
  coupon_class `F`, rating D) matched NEITHER = invisible. Now the **rating decides once**,
  unless a permanent Mario coupon-class exclusion outranks it. **Output 565→566 @3-31,
  560→561 @6-10** (11 flagged both dates = 8 hybrid-margin + 3 recovery). `TNTD03044683`
  stays out but its reason is now `excluded-structured` (class `na`), not `defaulted`.
- **Domain exception family `src/pricer/errors.py`** (`PricingDomainError` → `ContractTermsError`
  (+`.field`) → `ExerciseTermsError`; `CalibrationError`) — **rooted at `Exception`, NOT
  `ValueError`**, because the solvers' `except ValueError` was swallowing contract refusals and
  reporting them as "no spread reprices this bond". Only `CalibrationError` may become
  `CALIBRATION_FAILED`. `tests/test_exception_wiring.py` parses every src/scripts file and
  requires each name in an `except` clause to be BOUND — it caught a live `NameError` in
  `phase2_risk.py` (3 handlers named `CalibrationError`, never imported; green only because no
  bond had failed).
- **ONE ACT/364 exercise conversion:** `core/utils/dates.exercise_schedule_times`;
  `tree.schedule_times` + `dataio.to_lattice_schedule` both delegate. **`days_per_year` DELETED**
  (was defaulting to 365.25 while coupons run on 364).
- **Private-helper seam closed:** `hybrid` no longer imports `floating._as_date/_df`.
  `discounting` gains `curve_rate` / `curve_discount_factor`; floating's privates are now
  **aliases** (`is`-asserted) so the `pricing/frn.py` shim's re-export contract still holds.
- **Provenance/confidence labelling.** `data/call_schedules.csv` + `load_call_provenance` →
  `exercise_terms_status|_source|exercise_price_source|_as_of` on all 8 lattice-priced bonds
  (**0 confirmed, 9 of 9 rows provisional** = custodian AB date + par-call convention); a missing
  column defaults to `provisional`, an unrecognised status is REFUSED. `calibrate_risk` adds
  `current_coupon_source` + `risk_status` (6 proxy / 1 supplied). Endpoint: **`PROVISIONAL_TERMS`
  / `PROVISIONAL_RISK` warnings + `bond.exercise_terms_status`** — interface doc **§15**;
  **`schema_version` stays 1.1** (additive). Labels never change a number (`==` asserted).
  `TNTD04115619` carries a named `review_note` (1994bp on a 3.9y BBB @60.65 — recorded, NOT a
  threshold; nothing is filtered on it).
- **Disposition sidecars are now DATED** (`corporate_disposition_<VAL>.csv`,
  `callable_disposition_<VAL>.csv`) — the undated defaults let 6-10 overwrite 3-31, i.e. the
  artifact built to prove nothing is silently lost was itself losing a run. 732 rows each date.
- **`scripts/release_facts.py` → `docs/release_facts_<date>.md`** = rows + sha256 of all 5
  production CSVs + 4 sidecars + the real pytest line, written **UTF-8 explicitly** (redirected
  stdout encodes as GBK here — same trap as `pytest.ini`). Quote docs from THIS, not memory.
- **Docs:** `short_gap_callable_design_note_2026-08-31.md` (why `TNTD04920858` stays refused +
  the 3 things an off-coupon exercise node must settle: irregular-step BDT calibration,
  off-coupon accrued/call price, event ordering) · `shim_exit_policy_2026-08-31.md` (4 exit
  criteria, ALL required; **criterion 1 is UNMET** — all three drivers still import `pricing.*`;
  retire nothing now). Corrected: weekly report **§4.5** (new), walkthrough, interface §14.8/§15,
  `COVERAGE.md`, `missing_data.md` G5 (+3 corporate schedules, confirmation-only).
- **Excel gate re-run on real Excel: 48/48 fixture + 50/50 live.** 6 v1.1 tree fixtures
  regenerated (warnings array only); the 2 vanilla `_v1` fixtures deliberately LEFT at schema
  1.0 — being 1.0 is what they exist to prove.
- **NO new Mario/Liping request opened** (by instruction). The 3 corporate + 5 agency schedules
  went onto the existing **confirmation-only deferred** queue.

## ⭐ GBP par-yield UNITS BUG — "not arbitrage-free" was OURS (2026-08-30)
- **`data/*_Yield_Curve.txt` are NOT uniform: `GBP_Yield_Curve.txt` and `DKK_Yield_Curve.txt`
  store par yields in PERCENT; the other 24 store DECIMALS.** `load_par_curve` multiplied
  every file by 100 ⇒ the 2009-03-31 gilt curve became **73%–415%** ⇒ the bootstrap correctly
  raised *"Non-positive discount factor at t=3.000; par curve is not arbitrage-free"* — and we
  recorded that for two months as a fact about the DATA, and asked Mario/Liping for a
  replacement GBP curve. **Raw row 2009-03-31 = 0.731/1.183/2.341/3.157/4.157 = that day's gilt
  curve, in percent.** Verified across ALL 26 files × 3 dates.
- **Fix = an explicit registry `curves.bootstrap.PAR_YIELD_UNITS` (NOT a sniffer** — no
  threshold separates a 0.5% Danish yield from a 0.5 decimal; DKK would be luck) + `units=`
  per call + **`ParYieldUnitError` raised BEFORE the bootstrap** when a scaled row exceeds 100%.
- **Impact — the ONE intentional output change of Round 2b:** `TNTG700307W` (FT GBP 7.50% 2011)
  `frn-curve-blocked` → priced **205.31bp / 1.86y** @3-31 (146.71 @6-10); **`TNTG301334W`
  (UK EMTN fixed 5.50% 2033) was SILENTLY SKIPPED — not flagged — and is a plain `Fixed` bond,
  i.e. inside the class already reported complete** → priced **197.30bp / 12.55y** @3-31 (149.29
  @6-10). Corporate output **564→565 @3-31 / 559→560 @6-10; priced 553→555; flagged 11→10;
  `frn-curve-blocked` route now EMPTY; driver header `skipped=1→0`.** [08-31: 565→**566** /
  560→**561**, flagged back to **11** — a THIRD invisible bond, see the hardening section.] `callable_risk` +
  both `phase2` CSVs byte-identical (a GBP curve used to RAISE, so nothing could depend on it).
- Cross-check: same bond = 279.93bp on the USD curve vs 197.30 on its own; the ~83bp gap IS the
  gilt-vs-UST difference at 24y — two independent numbers agreeing.
- **GBP ask WITHDRAWN from `docs/missing_data.md` (G5 + the deferred table). Do NOT re-ask.**
  Registry rule added there: **an entry whose only evidence is one of our own error messages is
  not yet a data gap** — reproduce it against the raw file first.
- Two endpoint tests had used GBP as their "unbuildable curve" FIXTURE (borrowing a data defect);
  the build-failure mapping is now monkeypatched, plus a test that a GBP bond prices.

## Monthly-sheet golden reconciliation — Gates 0–3 DONE (2026-08-17)
- **Files:** plan `docs/monthly_reconciliation_plan_2026-08-15.md` (Rev B, gate statuses in
  place) + Gate-0 memo `docs/monthly_gate0_memo_2026-08-17.md` (cell/VBA-line citations) +
  **Gates-1–3 report `docs/monthly_recon_report_2026-08-17.md`** (the results). Gates 1–3 ran
  2026-08-17 on the user's EXPLICIT authorization (recorded in plan §9) — net-new `src/recon/`
  package (zeroyield4 curve replica + legacy-parity month-grid pricer, never imported by
  production) + `scripts/monthly_{extract_golden,recon_run}.py` + `tests/test_monthly_curves`
  (+13 ⇒ **166 green**). Frozen: `outputs/monthly_golden_rows.csv` (2,642) +
  `outputs/monthly_recon_rows.csv` (576).
- **Headline verdicts:** ① engine parity PROVEN — current-code-session caches (2012-12 batch +
  sub-annual 2010 rows) reproduce at the legacy solver's noise floor: govt@2012-12 **32/32
  within tolerance** (ΔOAS ≤0.9bp med 0.51, Δdur ≤0.0003y, ΔPV ≤0.0085); spec dead-AB corp
  @2012-12 33% ≤2bp = empirically recovered at-maturity routes. ② **The 2010-03-01 batch
  (bulk of the table) = `legacy-stale-session`** — older code rev (cached Q = duration÷100
  exactly; dead T/U cells) × mixed-vintage data (run-time Libor deposits survive in the top
  block, sub-annual rows reprice on them EXACTLY; no single curve fits the pillar rows) ⇒ NOT
  a valid numeric golden for any engine. ③ Three-way on stale rows: durations vs Bloomberg
  col I — **ours closer on 94%** (med 0.49y vs cache's 4.30y); OAS vs AD (n=97) not decidable
  (pull-date unknown + basis) as pre-registered. ④ Tolerances re-baselined: OAS ≤1bp
  target/2bp exception, dur ≤0.001y, reprice ≤0.01. Only 2012-12-batch caches are numeric
  goldens for the future tree-gated extensions; 2010-batch rows reconcile three-way instead.
- **H.15 pillar data** = `data/h15_pillars_monthly_recon.csv` (treasury.gov CMT via 47 —
  FRED is GFW-blocked from BOTH local and 47; treasury.gov year-CSV endpoint works from 47).
- **F1 curve truth:** every golden row prices via `zeroyield4(ccy, val-date)` = **GOVERNMENT par
  curves** (USD = H.15/CMT 11 pillars → 41-tenor gap-fill → continuous 374-month ×4-freq
  bootstrap = our own architecture). BondOAS tree consumes the same build (`IYC` par; Libor only
  as 1–5M stubs). Top-block Libor/swap + `c:\blp\curves\` files = separate manual chain, OFF the
  golden path (#NAME?-dead cells; mixed-epoch cached rates). USD pillars = FRED `DGS*` for ALL
  three val dates (2010-03-01/2012-06-01/2012-12-12; tracked txt files have all three too) ⇒
  curves are a rebuild, not recovery; 2012 blocks feasible.
- **F2:** `bondcalc` vanilla chain is convention-consistent (continuous z, `Exp(−(z+OAS)·t)`) —
  NO BondPrice bug here ⇒ `vba_compat` dropped from this workstream (H2 collapsed).
- **F3 real hazards:** ① month-grid convention (Δmonth counts, coupon each 12/freq months, face
  at last step = maturity truncated, NO accrued, 30y cap, freq-matched curve table) ⇒ build a
  thin **legacy-parity mode** beside production; ② routing by live Bloomberg `mty_typ`/
  `calc_typ_des` (cached cols AB/AC with gaps; empty ⇒ FRN-tree fallback; MBS by asset class;
  Govt Bonds → vanilla unconditionally) ⇒ dead-AB rows classified empirically.
- **Scope:** table = multi-asset (MBS 956/corp 856/CMBS 351/govt 198/AGY 104). Vanilla golden ≈
  **420 rows** (248 corp/agy AT-MATURITY-FIXED @2010-03-01 + ~174 govt FIXED, Treasuries = OAS≈0
  anchors) — NOT ~1,900. ZERO(110) legacy P=0 + DEFAULTED(21)=0 ⇒ excluded. FLOATING(426) =
  BondOAS(8) tree, **spread-duration** convention, heavy tails. VARIABLE ≈ fix-to-float priced
  as callable-FIXED (URS-overlapping names; divergence vs `hybrid.py` = reportable finding).
  Calibration input = **col B** (X = base copy); AG = RELATIVE |P−AD|/|AD| (AD n=311); col I =
  Bloomberg eff-dur n=2,278 ⇒ duration three-way (H4). Table ≈ frozen pasted values (56 live
  bondcalc formulas; ~60 stale cells/col). Veloz solver floor ~0.1–1bp; |V−B| = per-row legacy
  solve residual.
- **SteepFlat Table Monthly.txt LOST** (43% of FIXED rows are zero-twist T=U ⇒ reconcilable
  without it); ask Mario ONLY when the T/U gate opens (lock #13). No asks opened at Gate 0.
- **Remaining scope = tree-gated extensions** (callable/NORMAL ~450 · FLOATING 426 · V/W/Y/Z ·
  T/U [SteepFlat file = deferred Mario ask] · mtge at MBS phase); 2012-06 batch has no vanilla
  rows. The sample report to Mario now carries the reconciliation evidence (§5).

## Environment (important)
- **Local Python EXISTS — earlier note was WRONG (corrected 2026-08-25).** `python` on PATH is
  only the Microsoft Store stub (that part was right), but the machine has two full installs,
  found through the registry (`HKLM/HKCU:\SOFTWARE\Python\PythonCore`), not the PATH:
  `C:\Users\cnc\anaconda3\anaconda2025\python.exe` = **3.13.5, numpy 2.3.4 / pandas 2.3.3 /
  scipy 1.16.3 / pytest 8.3.4 / openpyxl 3.1.5 — USE THIS ONE**; `C:\Users\cnc\Documents\Downloads
  \python.exe` = 3.12.4 with the same stack a version older. (`C:\Users\cnc\anaconda3\python.exe`
  = the 3.8.8 base env, numpy import BROKEN via mkl-service — do not use.) ⚠️ **Local ≡ 47 for the TEST SUITE and the
  single-bond endpoint JSON, but NOT byte-for-byte for the 565-bond driver CSVs**: they differ by
  up to **3.6e-8 relative, entirely in `convexity`** (a second difference ÷ bump² amplifies a
  last-ulp by 1e8); prices/OAS/durations agree to ~1e-12 and every text column matches. So a
  cross-platform `sha256` diff of a driver CSV shows a difference that is NOT a regression —
  **do parity local-fresh vs local-fresh** (byte-exact, and stricter). The whole suite runs
  locally: `& "C:\Users\cnc\anaconda3\anaconda2025\python.exe" -m pytest -q` → **194 passed in
  ~19s**, identical to 47, and the endpoint's JSON output is byte-for-byte the same as 47's ⇒
  quick checks no longer need ssh. 47 remains the deployment target and the parity reference.
- **`pytest.ini` (added 2026-08-25) is what makes a bare `pytest` work.** Without
  `testpaths = tests`, a root-level run also walks the git-ignored Drive staging copies
  (`corporate_bond/`, `code_structure_sample/`), which contain duplicates of the test files ⇒
  "import file mismatch … use a unique basename" and ZERO tests run. ⚠️ Keep that file **ASCII**:
  pytest reads it with the system codec (GBK here), so one em dash aborts every run.
- **Interface to 47 = ssh from the Windows box** (chosen). Needs **key-based ssh** (the Bash
  tool is non-interactive — a password prompt hangs). Loop: edit locally → commit → `git push origin main`
  **+ `git push 47 main`** (direct deploy — see GFW bullet below; `git pull` on 47 only works when
  47→GitHub is up). Repo on 47 = **`/home/PengSX/fixed_income_pricing`** (conda env `PengSX`);
  run scripts via **`PYTHONPATH=src python3 scripts/…`**, run tests via **`.venv/bin/python -m pytest`** (pytest
  is in the repo `.venv`, NOT conda's `python3` — bare `python3 -m pytest` fails "No module named pytest"). Quick
  iter: `scp` the file to 47 then run (working-tree edit), or push + `git pull`. Use `ssh -o BatchMode=yes 47`.
- **47 data mirrored locally (2026-07-18):** `data/` + `extracted/` + `outputs/` copied 47→local (68 files;
  sizes verified). `extracted/`/`outputs/` git-ignored both sides; `data/` **tracked in full (59 files)** —
  the 6 root duplicates removed (see canonical-location note above). ⚠️ Windows scp quick-iter leaves **CRLF** working-tree copies
  on 47 that later **block `git pull`** ("would be overwritten … Aborting"); fix = confirm
  `git diff --ignore-cr-at-eol origin/main -- <files>` is empty, then discard & pull (done 2026-07-18:
  47 fast-forwarded `24689a7`→`07fe2a1`, 80 green).
- **47→GitHub is GFW-flaky (diagnosed 2026-07-18):** from 47, TCP to github.com connects (0.25s) but the
  TLS stream is blackholed/reset (baidu 200 in 1.3s ⇒ egress healthy ⇒ targeted interference); symptoms
  seen same-day: crawl-speed fetch, `SSL_read: unexpected eof`, 127s connect failure. Local→GitHub and
  local↔47 stay reliable ⇒ **sync 47 by pushing from local: `git push 47 main`** (local remote `47` =
  `ssh://47/home/PengSX/fixed_income_pricing`; 47 repo has `receive.denyCurrentBranch=updateInstead`, so
  the push updates 47's checked-out working tree). A dirty tree on 47 makes the push REFUSE — that
  guardrail protects scp quick-iter edits (commit/discard on 47, then re-push). 47's stale `origin/main`
  ref is cosmetic. Last-ditch fallback: `git bundle` + scp + `git pull <bundle> main` (used 2026-07-18).
- To read the Excel files without Python, a PowerShell sheet-decoder approach works
  (unzip the xlsx/xlsm and parse `sharedStrings.xml` + `worksheets/sheetN.xml`).
- **No Bloomberg.** Inputs are exported `*_Yield_Curve.txt` + FRED OAS (the VBA's
  `GetBloomberg` is replaced).
- **Client data is now TRACKED in-repo** (policy change 2026-07-08, boss-approved): the client
  portfolio, proprietary workbooks/curves, and derived reports are committed here. The repo **MUST
  stay private** (`github.com/charlieee0712/fixed_income_pricing`). `.gitignore` now excludes only
  build/cache/editor junk (`__pycache__/`, `.venv/`, `outputs/`, `.claude/`, …), not data. [was:
  "Never commit client data — *.xlsx/*.xlsm/*.zip/*.csv/*.txt are git-ignored".]
  **Canonical location = `data/` (2026-07-18):** the root workbook/curve copies were `git rm`'d
  (SHA256-verified identical to the `data/` copies first) — the code's default paths
  (`FIP_DATA_DIR="data"`) ARE the tracked layout. `.gitattributes` marks `data/** -text`
  (byte-frozen, no EOL conversion).

## File roles
- `All_Yield_Curve.zip` — raw **par-yield** history per country/ccy (`Date(Excel serial), 0.25..30`).
  Country-name files alias currency-code files (JAPAN ≡ JPY). Bundles
  `Zero_Yield_Curve_VBA_Code.txt` = auditable bootstrap VBA (replaces old `Veloz`).
- `Bootstrapped-*.zip` — Stage-1 output, **demo @ 2024-01-16** (not the pricing basis).
- `Pricing File.xlsm` — reference VBA: `Bootstrapping.bas` (1706 lines: **`BondPrice`**,
  `ZeroCalc`, `Parcurve`), `Matrix.bas`, `Copulas.bas`. **Port `BondPrice`** — do **not**
  port the ~11k-line `Module1` in the other workbook *for v1* (v2 callables DO port `BondOAS` from it — see below).
  Contains a *separate* Uganda demo.
- `Project Pricing Fixed Income Instruments.xlsm` — legacy risk-system sample (huge `Module1`). **v2 callable
  source** (recon 2026-06-30; VBA → `47:extracted/project_vba.txt`): **`BondOAS`** l.4397-5861 = straight
  callable/putable/sink **binomial short-rate lattice** (`analysisType` 5=implied-OAS, 6=±10bp eff-dur = the
  redefined flow); `CBondPrice` l.3904-4394 = **convertible** (CRR equity tree, NOT the callable target); BS
  equity Greeks l.6928-7225; **no DV01/convexity/Macaulay in legacy**.
- `URS …xlsx` — **the portfolio to price**: a US engineering-company pension, USD ISINs,
  positions split by asset type; `Corporate Bonds` tab is current focus.

## Two clients — do NOT merge
- **URS** = US pension (USD) → the pricing target.
- **Uganda** (UGANGB govt bonds, UGX) = a separate example, only in `Pricing File.xlsm`.

## Conventions (validated)
- Bootstrap recursion (shared): `cpn=100·par/f`; `DF_i=(100−cpn·Σ_{k<i}DF_k)/(100+cpn)`.
  ⚠️ **Two bootstraps exist in legacy** — do NOT conflate (Liping's catch, VERIFIED 2026-06-29):
  (i) the *auditable* routine — **continuous** `z=−ln(DF)/t` — what our `bootstrap.py` ports;
  (ii) `BondPrice`'s **own embedded** bootstrap (`Bootstrapping.bas`) — **semiannual**
  `z=2·((1/DF)^(1/2t)−1)` — what legacy *pricing* actually used. Same `DF`, different expression of `z`.
- **The VBA discounting bug + our fix** (VERIFIED 2026-06-29): `BondPrice` stores a **semiannual**
  zero but discounts it with the **continuous** `exp(−t·z)` (l.449) → convention mismatch,
  systematically **under-prices**. Proof: a curve must reprice its own par bonds to 100 — under
  `exp(−t·z)` they come out **below par (10y → 99.67)**; under the consistent `(1+z/2)^(−2t)` →
  **100.000000**. Our pipeline discounts consistently (`exp(−t·z_cont)`=DF, par→100); **`vba_compat=True`
  reproduces the legacy output EXACTLY** (0.0000% on the sample bond). Effect ≈ **0.2% @8y** (node DF
  −0.43% @10y) — far below v1's 6.4% IG dispersion, so it does **not** change the v1 verdict.
- 41-tenor grid 0.08y…30y; linear interpolation (interior) / linear extrapolation (ends);
  output monthly to ~374 months × {Annual, Semiannual, Quarterly, Monthly}.
- Pricing: discount each cash flow at `z(t)+OAS(rating)`, **linear interpolation** of the
  monthly grid; dirty = Σ coupons·DF + face·DF(T); clean = dirty − accrued.
- **Price-convention law (Liping review 2026-08-04, enforced by `test_price_convention` 16):** model PV =
  dirty, custodian `BT` = clean ⇒ EVERY calibration solves clean(OAS)==BT ⟺ dirty(OAS)==BT+AI (same root —
  AI is date-only); AI = ONE formula `bond_price.accrued_interest` (ACT/364, schedule-aware; FRN accrues the
  current reset, hybrid the fixed leg to the switch, ILB ×ratio_0). **Duration/convexity denominator = DIRTY
  (full price), RETAINED** after a both-ways test vs custodian AQ @3-31 (n=61: dirty closer 41/61, median
  |dur−AQ| 0.236 vs 0.331; the callable-only lean to clean = σ/par-call noise ≫ the 1-2% AI/P effect).
- **OAS — REDEFINED 2026-06-30 (Mario call): a per-bond CALIBRATION factor, NOT a pricing input.** New flow:
  back out each bond's **implied OAS** from the custodian price `BT` (solve OAS s.t. model clean = `BT`,
  `src/pricing/calibrate.py`), then compute **risk metrics** on the calibrated model (`src/pricing/risk.py`).
  Goal = risk metrics; implied OAS is the intermediate. **Supersedes index-rating-OAS as the endpoint**; moots
  v1's 6.4% IG dispersion (no rating average forced on names). ⇒ WRDS *distressed/sector OAS* pulls **CANCELLED**
  (FISD terms-rescue may still be needed — cash flows for risk metrics, not OAS). Calibration @ 2009-06-10/476:
  exact (`|clean−BT|`<2.2e-8), 475/476 OAS>0. Caveats: near-maturity OAS distorted by the 70-day date mismatch
  (3-31 date-match **REOPENS for calibration**), **17/476 EUR/GBP** (→ own-ccy curves), distressed OAS =
  recovery plug. **Caveats handled (2026-06-30):** near-maturity (<1y) flagged + excluded from medians (16);
  EUR/GBP routed to own-ccy curves via `ZeroCurve.from_currency` (15 EUR fixed → OAS −20..55bp, 2 GBP curve-blocked
  @ 6-10); distressed = `recovery-plug` flag. After fixes A/BBB land on the index (291/413 vs 302/453), AA wide
  (386 vs 227 = AA-financials). **3-31 ADOPTED as calibration baseline (2026-07-02)** — Mario's USD 3-31 curve
  (native schema, no adapter) swapped in; near-maturity distortion cleared (1371→464bp, −177→+199bp), universe
  481 (>476: 5 bonds alive @3-31 that 6-10 dropped), IG medians +~100bp (= the ~100bp-lower curve), risk metrics
  stable (eff-dur +0.13y). 6-10 kept as control. See WORKLOG 2026-07-02. [v1 index OAS below, kept for history.]
- **OAS (v1 index, kept for history)** = **ICE BofA US Corporate/HY** Index OAS, **one flat spread per rating** (AAA…CCC).
  **Historical source = `Pricing File.xlsm` / sheet `OAS Credit Curves`** (full daily 1997-01-02 …
  2025-11-07, 7 buckets; archived before ICE/FRED truncated the free series to a rolling 3y window
  in **April 2026**). Read via **`src/credit/oas.py`** (`oas_on(path, date)` → decimal dict, raises on
  missing date). **Do NOT use the FRED online API for OAS history** — it now only serves the last 3y.
  (UST par yields, by contrast, = FRED **`DGS*`** series — government data, **NOT** truncated — usable for
  any historical date; e.g. the 2009-03-31 curve absent from the txt was pulled from DGS and validated
  same-source against the 6-10 txt row.)
- **Bootstrap module** (`src/curves/bootstrap.py`, colleague's validated port): Excel epoch
  **1899-12-30** (`excel_serial_to_date`); output cols `Maturity, {Freq}_Rate`(percent)`, {Freq}_DF`;
  `load_par_curve` **raises** on a missing valuation date (no silent nearest-date — matters for 2009).
- **Data sourcing (corp)**: join master↔tab on **Asset ID** (`S`↔`Asset Code`, 100%; ISIN
  secondary). Terms (coupon rate/type/freq/maturity) ← `Corporate Bonds` tab (master coupon
  cols are EMPTY). Rating ← master `CM` S&P / `CL` Moody (default precedence; NR→fallback→exclude).
  Par held ← master `CV` Shares/Par value. EIR cost ← `Z`. **Golden master** = `BT` price /
  `BU` MV / `DI` YTM — keep in a SEPARATE reconciliation table, never in pricing inputs.

## Critical corrections (don't re-derive — already validated)
- **Valuation date**: holdings = **2009-03-31**; bundled curves = **2024-01-16** (RMSE 0).
  2009-03-31 is **absent** from curve files (gap 2008-11-10 → 2009-06-10). At 2024-01-16
  only **123/668** corporate bonds are still alive (545 matured); at 2009-03-31, **667**.
  → To price the real 2009 book, **bootstrap a ~2009 curve**; the 2024 CSVs are a demo.
  **Curve date: calibration baseline = 2009-03-31** (Mario's USD curve arrived 2026-07-02, fills the gap;
  matches the holdings date → near-maturity distortion cleared, universe 481). 6-10 kept as control (v1 +
  BT-date evidence). [was "6-10 chosen", pre-3-31-file.]
  ⚠️ Even @3-31 the model reproduces the VBA tool's output, not the custodian mark; **BT marking date/source
  RESOLVED (2026-07-03, Mario):** by 3-31 the crisis was near its end & spreads had retreated from peak, so BT's
  tighter credit is the real recovering-market mark (not a date mismatch); implied OAS below the 3-31 peak = that
  recovery. 3-31 baseline unchanged (see WORKLOG 2026-07-03).
- **Universe = deterministic 2-layer pipeline**, **IMPLEMENTED** in `src/dataio/universe.py`.
  Start = master sub-cat == `Corporate Bonds`, dedupe by Asset ID → **732 unique** (from 811
  rows; no separate MTN sub-cat — MTN = a terms-gap label, not a category). Log every drop with
  ONE primary reason + Asset ID. Counts (all reproduce **exactly**): join **597 matched / 135
  master-only / 19 tab-only**; rating **712 covered / 4 defaulted / 16 no-rating**; Layer-A raw
  **54 non-vanilla / 73 callable**. Priority (LOCKED): `terms-unavailable/unmatched → defaulted →
  no-rating → structured/floating → callable → matured`. Layer A = date-independent, Layer B =
  matured-at-val-date. **Result @ 2009-06-10 (post-priority MECE): canonical 522 / terms-unavailable
  135 / structured-floating 51 / callable 5 / no-rating 9 / matured 6 / defaulted 4.** **@2009-03-31 (adopted
  baseline): canonical 527** (5 more alive). **Make-whole callables (call date within `MAKE_WHOLE_MAX_GAP_DAYS`=7d
  of maturity, option value≈0) route to VANILLA — enter canonical, flagged `is_make_whole` (46 bonds) — NOT the
  `callable` exclusion (WORKLOG 2026-07-02); only 5 genuine-gap callables stay excluded → v2 lattice.** [was
  canonical 476/481, callable 51 pre-reclassification.]
  **2026-07-20 make-whole OVERRIDE layer:** `data/make_whole_overrides.csv` (via `dataio/term_overrides.py`,
  passed as `build_universe(..., make_whole_overrides=…)`) routes DOCUMENTED make-whole-only bonds whose
  call/maturity gap fails the 7d heuristic — Sempra 8.9% 2013 (SEC 424B2: T+50bp make-whole, NO par call;
  custodian AB = first coupon date) ⇒ **production canonical 523 @6-10 / 528 @3-31, callable 6→5,
  make-whole 47**. No-override golden counts (522/6/46) unchanged in tests — the override is a data layer.
  135 master-only = `terms-unavailable` (MTN; terms in neither sheet — **data gap, not security type**).
  Notch-map (S&P/Moody → 7 buckets) implemented in **`src/credit/ratings.py`**. Red lines: keep IG/HY split
  (BBB−→BBB, BB+→BB); S&P CC/C & Moody Ca/C → CCC, **not** default (only D/SD).

## Coupon-type routing (Mario 2026-07-08) — read `Coupon_Formula2`, route by structure
- **Directive:** the module defaulted every bond to `F`; now it reads **`Coupon_Formula2`** (Corporate
  Bonds tab, Excel col **M** — Mario said "N", header confirms **M**; N is empty, loader was right) and
  routes by coupon structure. Classifier = **`src/dataio/coupon_types.py`** (`classify_coupon_formula` +
  `ROUTE`), wired into `universe.py` (adds `coupon_class`+`route`; splits the old blanket
  structured/floating funnel bucket). Reconciles **EXACTLY** to Mario's 676-row pivot: **F 617 · floating
  27 · fixed-to-reset 6 · stepped 2 · step-up 1 · zero 1 · defaulted 1 · excluded 21** (in
  `extras["coupon_class_pivot"]`).
- **Route → engine:** F/zero → vanilla · stepped/step-up → vanilla-schedule (Step 3) · floating +
  fixed-to-reset → floating engine (Step 4, TBD) · defaulted → recovery mark (Step 3) ·
  pass-through/amortizing/na → out of the output (16/1/4 = 21). **Meeting 2026-07-20:**
  **pass-through 16 = ⏳ Mario sourcing the data on Bloomberg** (prepayment engine starts when it
  lands); **amortizing 1 + na 4 = ignore PERMANENTLY** (confirmed). Pass-through sheet's
  Collateral-col loader **kept** for the MBS phase. A `data/coupon_schedules.csv` entry now
  OVERRIDES class routing → vanilla-schedule (see term-overrides bullet below).
- **Funnel @6-10:** canonical stays **522** but now 100% `coupon_class F`/`route vanilla` — the 1
  `Amortizing` bond coupon_type mislabelled "Fixed" left canonical (correctness fix), a formula-`Fixed`
  hybrid replaced it; **callable 5→6** (a formula-`Fixed` bond coupon_type had mislabelled non-fixed = real
  fixed callable → v2 lattice). `test_universe` +3, **63 green**.
- **FRN legacy = Step-1 recon (NOT ported):** `BondOAS` **analysisType 7/8/9**
  (`47:extracted/project_vba.txt` **l.5693–5829**) = 7 price / 8 implied-OAS (`Veloz` solve) / 9 eff-dur
  (±10bp) on a **curve-forward FRN recombining tree** — floating coupon `Forward = Discount·sloperow` off
  the discount curve; discount `(OAS+Forward)/Freq` on the **same** curve (single-curve, periodic-simple,
  ≤30 steps). **Bloomberg data = substitutable (the callable-schedule pattern):** `swapcurve` short-end
  (EURIBOR `EU000nM` / GBP-LIBOR `BP000nM` / USD-LIBOR `US000nM` or **H.15 `h15tnM` = FRED-able**),
  `multi_cpn_schedule` (steps), `flt_cpn_hist` (spread+resets) → our ZeroCurve forwards + parsed
  spread/schedule. Step 4 method **CONFIRMED 2026-07-08** — plan below.
- **Step 3 DONE (2026-07-08) — simple special types priced.** New `src/pricing/coupon_schedule.py`
  (`parse_coupon_schedule` free-text → `[(eff_date|None, rate_decimal)]` + `coupon_at`; returns
  **None, never a guess**, when a cell has no numeric coupons); `price_bond`/`implied_oas`/`risk_metrics`
  take an optional `coupon_schedule`. Driver routes the 4 **held** special bonds:
  **stepped** TNTD04283895 (A; switch 2006 < val ⇒ flat 7.50%) → clean **210bp**, eff-dur 1.63, joins the
  A median; **zero** TNTD03037132 (BBB, 2037) priced degenerate-vanilla but BT 93.1 ⇒ **OAS −486bp** =
  BT inconsistent with a pure-discount zero (structured payoff) → route `zero-structured`, **excluded
  from medians**; **step-up** TNTD04150829 → `schedule-unavailable` (steps not in workbook — needs a
  terms source like the call schedule) → BT mark; **defaulted** TNTD03037967 (BT 12) → route `recovery`,
  BT mark, **no OAS**. Only `PRICED_ROUTES` {vanilla, make-whole-as-vanilla, vanilla-schedule} feed the
  by-rating medians. `test_coupon_schedule` (+10) → **73 green**.
- **Step 4 plan LOCKED (2026-07-08, Mario) — floating engine; do pure-FRN 27 FIRST, then reset 6:**
  ① fwd projection = **implied forward off our bootstrapped `ZeroCurve`** (`F(t1,t2)=(DF(t1)/DF(t2)−1)/
  (t2−t1)`, simple — matches legacy periodic discounting; Step-1 recon confirmed the legacy tree does
  exactly this). ② discount = **same curve + implied OAS (single-curve)**, matching legacy; **record in
  code/docs that single-curve = 2009 convention, OIS dual-curve = future enhancement** (transparency,
  not now). ③ data subs: USD short-end → **try pure ZeroCurve forwards first** (may need no external
  fixing), else FRED H.15; EUR/GBP → 47 own-ccy curves; **spread parsed from `coupon_formula`**
  ("EURIBOR + 45bp"→45bp, standalone parser + tests); current-reset coupon ← master `Coupon` (D).
  ④ **Fixed→Reset (6, incl perpetual) DEFERRED** — recon each one's terms first (perpetual = no maturity
  ⇒ CF truncation / perp formula); don't batch. ⑤ **no legacy golden (bbg) → invariant tests** (callable
  pattern): spread=0 & flat curve ⇒ price≈par; implied-OAS round-trip; **FRN eff-dur ≪ same-maturity
  fixed (≈ time-to-next-reset)** = the signature FRN check. ⑥ output: 27 floaters → main table
  (route=floating) with implied OAS + duration/DV01/convexity.
- **Step 4 pure-floating DONE (2026-07-08) — `src/pricing/frn.py`.** Coupons = simple forward off our
  `ZeroCurve` + spread; single-curve discount + implied OAS (calibrated to BT). **Effective duration bumps
  the CURVE (reprojects forwards), NOT the OAS** → ~ time to next reset. Bug fixed en route: the stub
  (current) period's forward must start at the true last-reset (t_prev<0), else the par-floater telescoping
  breaks. `test_frn` (7 invariants: par-under-any-shift, OAS round-trip, near-par dur≈0, **dur ≪
  same-maturity fixed even @78y**). Of 27: **18 priced FRNs** — durations SHORT across maturities to 58y
  (the 2066/2067 floaters: eff-dur **~−10.7** vs a ~+20y fixed; near-par ones ≈0; deep-discount ones carry a
  credit-spread-annuity duration, hence negative). **80 green.**
- **Data needed from Mario/Bloomberg** (flagged, gap-blocked, NOT force-priced; empty
  `data/coupon_schedules.csv` seeded `asset_id,effective_date,coupon_rate`): (a) FRN **spreads**
  ("...+ Spread" has no number → folded into OAS); (b) **Fixed→Floating switch dates** (5); (c) **perpetual**
  terms — 2 FRN + 3 reset have no maturity (CF truncation / perp formula); (d) **step-up** coupon table +
  **zero** structured-payoff terms (Step 3); (e) a usable **GBP curve** (non-arb 3y node blocks the 1 GBP
  floater + any GBP bond).
- **Reset-6 DONE (2026-07-08) — coupon-continuation.** 4 known-coupon hybrids priced as their current
  fixed coupon continued (perp → 90y truncation, face PV≈0; finite → maturity): TNTD03020850 1089bp,
  TNTD04509751 876bp, TNTG532803U 564bp, TNTG533596W 627bp (route `reset-continuation`, LONG dur = correct,
  kept out of by-rating medians). **price-to-call = reference only**: TNTG533596W BT 36 ⇒ to-call 1884bp is
  spurious (market prices extension, not call) ⇒ continuation is the main column. 2 Variable-coupon
  (TNTG532805U, TNTG701894W) → BT-mark `reset-terms-unavailable`.
- **Coupon_Formula2 coverage CLOSED → see `COVERAGE.md`** (class→engine→status over the 676 pivot; output
  now **559 @6-10 = 548 priced + 11 flagged** (564/553/11 @3-31) after the 2026-07-20 overrides [was
  558 = 545 + 13]). FRN neg-duration mechanism + spread=0 convention documented in `frn.py`.
- **ISIN lookup + term-overrides layer (2026-07-20, Mario meeting) — `docs/isin_lookup_2026-07-20.md` = the
  evidence file.** All 35 flagged/data-gap bonds researched by ISIN/CUSIP in public primary sources (SEC
  EDGAR full-text on CUSIP, issuer OCs/20-F/ARs, oblible/gruppotim/unicredit archives): **22 FULL(HIGH) /
  10 PARTIAL / 3 NONE** (exempt US paper). New module **`src/dataio/term_overrides.py`** (3 optional
  tables, missing file = no overrides; wired into `calibrate_risk.py` + `callable_risk.py`):
  ① `coupon_schedules.csv` — 9 documented coupon paths → route ANY class to vanilla-schedule (beats
  free-text parse / degenerate-zero / FRN fallback): Aquila flat 11.875 (steps reversed by 2009) ·
  **Comcast 6.95 (the "zero" was a custodian coupon ERROR — OAS −486→+431bp)** · BT 8.625→9.125 step
  path · Sogerim 7.50 (rating-step level in force) · **TI-2012 7.25 & TI-2033 7.75 (documented PLAIN
  FIXED; workbook "(VAR)"/"Fixed→Reset" tags WRONG)** · Anglian 5.375 · RBS 6.00 (call/float hypothesis
  refuted) · FT-GBP 7.50 floor (seeded; GBP curve still blocks). Sanity: TI-2012 381bp ≈ Sogerim 398bp
  (same guarantor). ② `frn_spreads.csv` — quoted margins priced explicitly (OAS no longer absorbs them):
  Bear L+40, PNC L+14, MS L+45 (all corrected to QUARTERLY via `freq` col; `FRN_FREQ_VARIANT` maps 4→
  Quarterly curve), IndepComm L+182. ③ `make_whole_overrides.csv` — Sempra (see universe bullet).
  Plus **`hybrid_switch_terms.csv`** (18 rows; consumed by `pricing/hybrid.py` since same-day — see the
  hybrid bullet in Validated) = the **fixed-then-float engine's** input:
  at VAL **every** fixed-to-float hybrid was still in its FIXED leg (switches 2009-10…2037) —
  Allstate 6.125→L+193.5 (2017) · Lincoln 7→L+235.75 (2016) · Liberty 7.8→L+357.6 (2037) · Chubb
  6.375→L+225 (2017) · **AmEx 6.80→L+222.75 (2016) & GE 6.375→L+228.9 (2017) — both were misrouted as
  plain FRNs** · SMBC 4.375→6mE+225 (2009-10!) · BofA 4.75→3mE+146 (2014) · BNP 7.195→L+129 (2037) ·
  UniCredit 4.028→3mE+176 (2015) + margin-gap rows. Shinsei "frn-no-maturity" pair RESOLVED = dated
  2016-02-23, 3.75% to call 2011-02-23 (margin → Mario). **Remaining gaps = 11-security Bloomberg list
  for Mario** (3 exempt US FRNs all-terms; 8 hybrids post-call margin only) — table in the lookup doc.
  Drivers re-run @3-31 + @6-10, outputs mirrored locally.
- **Fixed-then-float HYBRID engine (2026-07-20, same-day follow-up; design拍板 by user)** —
  **`src/pricing/hybrid.py`**: fixed leg val→switch on price_bond's EXACT conventions (grid anchored at
  the SWITCH, accrued off it, no face) + floating leg switch→maturity on price_frn's EXACT conventions
  (grid anchored at MATURITY truncated at the switch, first period starts AT the switch, fwd·tau +
  documented margin, face at maturity); one curve + one implied OAS discounts both (`exp(-t(z+shift+oas))`);
  risk = CURVE bump (frn convention). **Degenerate limits DELEGATE** (switch≥mat → price_bond with
  `oas+shift`; switch≤val → price_frn) ⇒ bit-exact; **composition validated by the margin-0 identity**:
  spread=0 & oas=0 ⇒ floating leg telescopes EXACTLY to `face·DF(t_switch)` on ANY curve ⇒ hybrid ==
  fixed-to-switch bullet (= the price-to-call reference bond). Driver: `hyb_terms` intercepts in the
  floating + resets loops — margin known → route **`hybrid`** (main column) + **price-to-call REFERENCE**
  columns (reset-6 dual-column rule; deep-discount to-call OAS is spurious = extension priced, e.g. SMBC
  415bp hybrid vs 1869bp to-call); margin missing → **`hybrid-margin-unavailable`** BT-mark (8 names —
  incl. previously FRN-priced BTMU/Resona-EUR and continuation-priced Chuo/Resona-4.125: never
  half-modelled; a Mario margin fill = one CSV cell → priced, zero code change). Perps (BNP, UniCredit)
  truncate at 90y; `next_switch_t` output per bond (e.g. SMBC 0.58y → dur 0.44; Liberty sw-2037 →
  dur 4.66). **reset-continuation RETIRED.** Hybrid OAS kept OUT of by-rating medians (jr-sub/T1 capital
  spreads). Sanity @3-31: BNP 1209bp (was 1089 continuation — the par-floater tail is worth more than a
  deep-discounted 7.195% annuity tail ⇒ OAS up, direction correct); totals 553 priced / 11 flagged
  unchanged, composition improved. **Tests 90→103 green on 47** (`test_hybrid` 10: bit-exact limits,
  any-curve margin-0 identity, monotonicity, OAS round-trip, dur ≪ fixed & ~switch-bounded, near-limit
  continuity, perp truncation, to-call spuriousness; +3 loader/repo locks).

## Validated so far
- **Bootstrap ported** (`src/curves/bootstrap.py`, colleague's validated module): A/S exact,
  Q exact ≤30y, Monthly <0.1 pp (short-end fill); golden-master `tests/test_bootstrap.py` uses
  **segmented** thresholds — A/S strict <1e-9 red line; Quarterly terminal-extrapolation node
  (>30y) and Monthly-DF short-end residual carved out (see WORKLOG 2026-06-27). Rating notch-map
  `src/credit/ratings.py` (`tests/test_ratings.py`). Bloomberg cut.
- **Universe pipeline** (`src/dataio/loaders.py` + `universe.py`, run on 47): reproduces the
  documented funnel **exactly** (join 597/135/19, rating 712/4/16, Layer-A raw 54/73, MECE=732)
  → **canonical = 522 @ 2009-06-10** (incl. 46 make-whole-as-vanilla; callable=5); per-bond exclusion log; golden
  `tests/test_universe.py` (53 tests).
- **Pricing + reconciliation** (`zero_curve.py` + `bond_price.py` + `oas.py`, on 47): 2009-06-10 USD curve
  sane vs actual June-2009 UST; priced canonical 476. **v1 method VALIDATED.** *Is the method correct?* →
  **yes, UNBIASED**: IG (AAA-BBB) signed median **−0.4% (≈0)**, curve+OAS centred on BT; plus OAS=0 near-
  maturity high-grade ties BT **<0.2%**. *Precision?* → **~6.4% median |diff%|, which is DISPERSION not bias**
  — name-level scatter around the index rating OAS (±300 bp normal in 2009); a **known v1 design boundary,
  not a bug** (distress removal leaves it 6.1% → broad, not outliers). NOT a "near-miss vs 5%": success,
  precision to improve in v1.5. Narrowing path to <5% = **finer OAS (sector/quality/name), v2** — the
  3-31 date-match is a **tested dead end** (makes IG *worse*, 6.4%→11.1%: the 3-31 crisis-peak OAS overstates
  these holdings' spreads — see WORKLOG). HY / distressed / callable = v2.
- **Calibration + risk layer** (`src/pricing/calibrate.py` + `risk.py`, on 47) — **the redefined direction**:
  per-bond **implied OAS** from `BT` (canonical 476: exact, 475/476>0) → **effective duration / DV01 / convexity**
  (numerical ±1bp = parallel-shift bump; == continuous Macaulay to 1e-7). `outputs/implied_oas.csv`. Driver `scripts/calibrate_risk.py`. **Caveats handled:** `from_currency` routes per-ccy curves (15 EUR
  fixed, 2 GBP curve-blocked), `near_maturity` flags+excludes <1y → A/BBB land on the index (291/413 vs
  302/453), AA wide (386) = AA-financials, HY = distress. See WORKLOG 2026-06-30.
  **3-31 adopted as baseline (2026-07-02):** re-calibrated @2009-03-31 (canonical 481, exact), near-maturity
  cleared, by-rating index now **date-matched** via `oas_on(VAL)`; driver env-parameterised
  (`FIP_VAL_DATE`/`FIP_OUT`/`FIP_OAS_WB`). See WORKLOG 2026-07-02.
- **v2 callable lattice** (`src/pricing/lattice.py` + `scripts/callable_risk.py`, on 47) — **clean standard BDT**
  short-rate tree (fwd-induction Arrow-Debreu calib to `ZeroCurve`, arb-free), **NOT a `BondOAS` replica** (legacy
  unrunnable w/o Bloomberg). Invariant-validated (`test_lattice` 29 + `test_call_schedules` 4). Only **4 genuine
  fixed callables** (46 make-whole → vanilla); lattice moves ~1 (TNTD04441873 eff-dur 11.43→**10.37 @σ=0.15**);
  custodian AQ ≈ straight dur (misses the call). **Calibration convention EXACT since 2026-08-04 (Liping
  code review):** grid = the REAL ACT/364 remaining coupon dates (per-step-dt BDT via
  `bond_price.lattice_inputs`) ⇒ root PV = TRUE dirty; OAS solves PV − shared `accrued_interest` == BT
  (clean-vs-clean, the vanilla equation; call times @364d/y). Straight-on-lattice ≡ `price_bond` dirty to
  machine precision (tested). Was: snapped regular grid, no accrued, T@365.25d (≈clean only near par; a 25y
  bond lost a whole coupon to `round`) — NOT the dirty-vs-BT bug Liping hypothesized, but fixed exactly.
  Impact ±35bp mixed-sign (corp: +34.6/−1.5/+12.4; AGY: +29.5…−11.0), dur ≤0.6y. **Mario v1 (2026-07-03): σ=0.15** (was 0.18); **call schedule
  DATA-DRIVEN** — `data/call_schedules.csv` (`asset_id|call_date|call_price`, tracked in `data/` since 2026-07-18) via
  `dataio.call_schedules`, seeded by `scripts/init_call_schedules.py`; the lattice reads a `[(time,price)]` step
  schedule (**no hard-coded par-call** — a real schedule = CSV-only change). v1 values = par-call@100, call_date ←
  AB. ~~TNTD03203204 "par-call conflicts w/ BT 108.69"~~ **RESOLVED 2026-07-20: Sempra is make-whole-only (SEC
  424B2, T+50bp, no par call) → re-routed off the lattice to make-whole-as-vanilla (implied 509bp ≈ the old
  straight-OAS 507 — conflict was the par-call assumption, not the bond); its wrong CSV row deleted.** Lattice
  set now 3 priced of the 5-callable bucket (TNTD04923866 awaits a schedule row). **All 3 Mario Qs
  (schedule/vol/BT) RESOLVED — WORKLOG 2026-07-03.**

## Open questions
- **PHASE 2 BUILT (2026-07-22): AGY/GTD/ILB priced end-to-end; MBS = engine skeleton awaiting data.**
  `docs/phase2_inventory_2026-07-20.md` (findings) + **`docs/phase2_methods_2026-07-22.md`** (methods/
  results/decisions). Modules: `dataio/phase2.py` (master-superset loader Q/T/Y/BG/BH/BX/CA/CB/AQ +
  per-class universe; dup legs SUM par/MV/cost ⇒ ILB `BT=BU/par·100` exact) · `pricing/ilb.py` ·
  `pricing/mbs.py` · driver `scripts/phase2_risk.py` (env FIP_VAL_DATE/FIP_OUT/FIP_VOL/FIP_INFL);
  outputs `outputs/phase2_risk_2009-03-31.csv` (baseline, calib ≤6.6e-9) + `…06-10.csv` (control:
  ~110bp tighter across the board = Mar→Jun yield backup absorbed — mirrors corporate; 3-31 baseline).
  **AGY 42→39** (routes vanilla 27 / callable-lattice 5 / call-passed-vanilla 4 [desc "…/2006"
  one-time calls PASSED, AB blank → bullets+flag] / zero 2 [RefCorp STRIPS 107-113bp] / cmo-tranche 1
  [TNTD04733316 "SER 3122 CL ZB" REMIC Z misfiled → BT mark]); median 121bp, wides = quasi-sov credit
  (KDB 607/KEXIM 594/PEMEX 620/FHLB-Chi SUB 392); **callables = Bermudan par@100 from AB σ=0.15
  (industry-correct agency default), lie detector clean, lattice dur ≈ custodian AQ 4/5 (AQ IS
  option-adjusted here — reverse of corporate, free lattice validation; post-2026-08-04
  clean-calibration: OAS −11…+30bp, dur 4/5 within 0.75y of AQ)**. **GTD 11→9** all FDIC-TLGP
  → own `TLGP-guaranteed` bucket (NEVER bank buckets), median 86bp. **ILB 16→15**: nominal own-ccy
  curve + `ratio(t)=ratio_0·(1+FIP_INFL)^t` (ratio_0=BG÷desc-coupon, `parse_desc_coupon`); spread in
  OWN column `implied_spread_vs_nominal_bp` ≈ **−breakeven @ FIP_INFL=0 (EXPECTED NEGATIVE — π-at-s ≡
  0-at-(s−ln(1+π)), unit-tested; never mix with credit OAS)**; @3-31 extracted breakevens = the
  deflation-panic curve (2010 −34bp → 2032 +139bp), JGBi +229bp spread = breakeven −2.3% (Japan,
  sign flips right), per-bond z+s ≈ custodian DI real YTM; TIPS deflation floor ignored = v1 boundary
  (needs inflation vol, v2); **KTBi BT-marked `ilb-indexation-unverified`** (BG==coupon, no desc
  coupon ⇒ ratio underivable; KRW curve lacks 3-31) → Mario. **MBS `pricing/mbs.py`** = static-CPR
  skeleton on the EXACT 8-mnemonic interface (`PoolTerms.from_bloomberg` — data lands, zero code
  change): level-pay + CPR→SMM, price/implied-spread/implied-CPR/risk+WAL; invariants green (annuity
  degeneration, principal conservation, par-at-WAC, dur↓ in CPR). **BZ>1 RESOLVED = REMIC accrual
  (Z/VZ/ZC) tranches, factor>1 CORRECT; BZ ≡ master CA 849/849; BX empty for MBS ⇒ BZ descriptive,
  engine doesn't need it.** Negative-par 10 = MBS TBA-style shorts; master Y uniformly 'A' (non-
  discriminating) — loader flags on sign (`is_short`); none in the three built classes. Next: when
  the 8-field pull lands → pool routing方案 (incl. REMIC Z/paid-down rows inside Govt MBS) + driver
  vs BS golden.
- **Mario meeting HELD 2026-07-20** (was: awaiting v3 feedback). Decisions: ① **pass-through 16 — Mario
  pulls the data from Bloomberg** and sends it (prepayment engine work starts then); ② **amortizing 1 +
  na 4 — ignore permanently**; ③ flagged bonds → resolve by ISIN online, unresolvable → back to Mario.
  ③ EXECUTED same day: 35 bonds looked up, term-overrides layer landed (see the 2026-07-20 bullet above +
  `docs/isin_lookup_2026-07-20.md`). **Now ⏳ AWAITING Mario: (a) the 11-security Bloomberg request list**
  (in the lookup doc — 3 exempt US FRNs all-terms, 8 hybrids post-call margin), **(b) pass-through
  Bloomberg data, (c) the Govt-MBS 8-field × 882-CUSIP pull (requested 2026-07-22; `pricing/mbs.py`
  skeleton built and waiting).** KTBi terms / agency call schedules / rating quirk = intentionally
  DEFERRED asks (see Comms state below), not yet with Mario. ~~Next engine step: fixed-then-float pricer~~ **DONE same-day** (`pricing/hybrid.py`,
  design拍板 by user — see the hybrid bullet in Validated): the 10 fully-termed hybrids are priced
  (route `hybrid`), the 8 margin-gap names BT-marked `hybrid-margin-unavailable`; **a Mario margin
  fill = one `hybrid_switch_terms.csv` cell → the bond prices with zero code change.**
  **Comms state:** 11-security list WhatsApp'd to Mario **2026-07-20** (awaiting reply); the planned
  7-21 phase-2 request was **never sent** — the trimmed version (MBS 8-field × 882-CUSIP pull ONLY +
  progress + inflation one-liner; NO pass-through mention) **sent 2026-07-22** with
  `outputs/govt_mtge_cusips.csv` (882 rows, local + 47). **DEFERRED to the next touchpoint (when Mario returns the MBS data), by
  design — do NOT re-ask before then:** ① KTBi indexation terms + KRW 3-31 curve row (single $1.2M
  position, BT-marked, no downstream dependency); ② agency call schedules (par-call lattice already
  matches custodian AQ ⇒ confirmation-only); ③ the TNTD04366584 A/Aa2 rating quirk. Project folder delivered to Mario via Google Drive as `corporate_bond`
  (staging dir at repo root, git-ignored — regenerate via robocopy + re-drag on updates, see WORKLOG
  2026-07-20 afternoon; Drive access = Mario only).
- **Mario design directive (2026-07-30, WhatsApp) → `docs/missing_data.md` registry + Liping channel.**
  Mario on the ISIN-lookup approach: web/ChatGPT-sourced terms are fine as INTERIM but "not as precise
  as bloomberg"; we're building an ALL-PURPOSE tool ⇒ what matters is ① the process itself automated &
  working end-to-end, ② every unavailable field SPECIFIED ON A TABLE, so when complete data arrives
  "we'll run all what you've built". ⇒ **`docs/missing_data.md`** = the living missing-data registry
  (every gap → landing CSV/loader → interim treatment → request status; **web-sourced override values =
  PROVISIONAL — on any Bloomberg return, diff, Bloomberg wins, log deltas**). Architecture already
  complies (term-overrides data layer, generic engines, zero-code-change landings). **Liping = second
  Bloomberg channel** (campus access): full gap request WhatsApp'd **2026-07-30** — MBS 8×882 (+ BDP
  template `outputs/govt_mtge_bdp_template.csv`, regenerable), pass-through **13 uniques** ("16" = tab
  rows; all EETC/private scheduled-amortization ⇒ likely amortizing-vanilla, no prepayment model), the
  11-security list, **NEW ask: AssuredGty US04622DAA90 call schedule** (TNTD04923866, the unpriced 5th
  callable — absent from all earlier lists), + deferred trio/GBP/FHR-3122-ZB as opportunistic extras
  (Mario-side deferral discipline unchanged). **Dedupe Mario/Liping returns before loading.**
  **Liping also code-reviews:** her v2 review triggered the 2026-08-04 clean/dirty audit + lattice fix;
  review-response report (EN PDF, `docs/review_response_liping_2026-08-04.pdf`) **sent to her 2026-08-04**.
  Her 07-30 data request still pending.
- **OAS redefined → calibration (2026-06-30; see WORKLOG).** Implied OAS per bond from `BT`, then risk metrics;
  index/sector/distressed OAS no longer external inputs (**WRDS distressed/sector OAS pulls cancelled**). New opens
  for Mario: (a) calibration date — **3-31 ARRIVED & ADOPTED (2026-07-02)**: Mario's USD 3-31 curve (native schema)
  swapped in, `VAL`=2009-03-31, near-maturity distortion cleared (the v1 3-31 *rating-OAS* refutation below does
  **NOT** apply to calibration); (b) **EUR/GBP own-ccy curves DONE** (15 EUR fixed, **2 GBP still curve-blocked** —
  non-arb 3y node, needs a GBP replacement curve or `bootstrap` variant-isolation, NOT a date issue); (c) **FX
  RESOLVED** — custodian base-USD columns (`BU`='Market value - base', `Z`='Book cost - base') read directly, no
  self-convert (`to_usd` removed; `currency` kept for routing); (d) **BT marking date/source — RESOLVED
  (2026-07-03, Mario):** by 3-31 the crisis was near its end & spreads had retreated from peak, so BT's tighter
  credit = the real recovering-market mark, NOT a date mismatch (implied@3-31 143–206bp *below* the 3-31 peak index
  IS that recovery). 3-31 baseline unchanged.
- ~~3-31 curve = the v1 IG lever~~ **REFUTED (tested 2026-06-27, for the v1 rating-OAS method; REOPENS for calibration — see above):** date-matching to 3-31 (3-31 DGS curve +
  3-31 OAS) makes IG **worse** (6.43%→11.14%, signed −0.41%→−6.70%) — the 3-31 crisis-peak OAS (BBB 7.31% vs
  6-10's 4.53%) overstates these high-grade holdings' spreads; **BT aligns with ~6-10 (tighter) spreads, the
  70-day gap is NOT a precision lever** (real lever = finer OAS, v2).
- ~~Confirm BT's marking date/source~~ **RESOLVED (2026-07-03, Mario):** by 2009-03-31 the crisis was near its end
  and spreads had already retreated from the peak ⇒ BT's tighter credit is the genuine recovering-market mark, not
  a date mismatch; the implied OAS sitting 143–206bp below the 3-31 crisis-peak index is that recovery, not an
  error. 3-31 stays the calibration baseline. See WORKLOG 2026-07-03.
- ~~Historical OAS source~~ **RESOLVED** — `Pricing File.xlsm` / `OAS Credit Curves` via `src/credit/oas.py`
  (FRED online truncated to 3y in April 2026; the workbook holds the full 1997-2025 archive).
- ~~Canonical universe definition + exclusion list~~ **RESOLVED** — `dataio/universe.py` →
  canonical **476 @ 2009-06-10** + per-bond exclusion log (final valuation date pending colleague).
- **EIR (IFRS-9 amortised cost)** — **a requirement, not legacy code**: searched both workbooks (14k VBA
  lines + all sheets), **zero hits** → implement from the standard, **no legacy golden** to reconcile. Spec
  preset (confirm w/ CEO): `Book cost` (Z) = amortised carrying value (data-inferred) ⇒ amortised cost ≈ Z,
  EIR = IRR(Z, remaining CFs); deliver per-bond {eff. yield, amortised cost} + amortised-cost-vs-market table.
  **Implement only after the v1 Mario report + spec confirmation.**
- ~~Where per-bond rating/holdings are sourced~~ **RESOLVED** — see Data sourcing above
  (rating `CM`/`CL`, par `CV`; join on Asset ID). ~~build the MECE pipeline~~ **done**.

## Target architecture (`src/<layer>/`; root `conftest.py` puts `src/` on path)
- `src/curves/` — ✅ `bootstrap.py` (par→zero, reproduces golden) · ✅ `zero_curve.py` (`ZeroCurve`, linear-interp z/DF + OAS spread; `from_currency` per-ccy curves — `CURVE_FILE` maps USD/EUR/GBP/**JPY/AUD/KRW** since 2026-07-22; the country txt files carry BOTH 2009-03-31 & 06-10 rows — the "3-31 absent" gap was USD-only; KRW = 06-10 only).
- `src/credit/` — ✅ `ratings.py` (notch-map) · ✅ `oas.py` (per-rating OAS from `OAS Credit Curves`).
- `src/dataio/` — ✅ `loaders.py` (master + Corporate Bonds tab) + `universe.py` (`build_universe`,
  MECE funnel → **canonical 522 @ 2009-06-10** (46 make-whole→vanilla; **523/47 with the production
  make-whole override**)) + ✅ `call_schedules.py` (call/put
  exercise table `data/call_schedules.csv` → per-asset `[(date,price)]`; the lattice's only call-terms source)
  + ✅ `coupon_types.py` (`Coupon_Formula2` → coupon-class + engine route, Mario 2026-07-08)
  + ✅ `term_overrides.py` (2026-07-20: the three optional override tables — coupon paths / FRN margins /
  make-whole list — primary-source fills from the ISIN lookup; consumed by both drivers)
  + ✅ `phase2.py` (2026-07-22: AGY/GTD/ILB master-superset loader + per-class mini-universe + `parse_desc_coupon`;
  routes per `docs/phase2_methods_2026-07-22.md`; driver `scripts/phase2_risk.py`);
  FRED OAS loader next. (Named `dataio`, **not** `io`: `conftest` puts `src/` at `sys.path[0]`, so an `io` package
  would shadow stdlib `io`.)
- `src/pricer/endpoints/` — **✅ NEW (2026-08-25):** the external interface (one request in, one
  complete result out) — `main.py` (public entry, failures are values not exceptions) ·
  `contracts.py` (the v1 request/response contract, standard library only) · `pricing.py` (vanilla
  orchestration over the approved wrappers) · `dependencies.py` (FIP_DATA_DIR — swap this file for
  a cloud deployment). Flat by decision: the template's `endpoints/routes/` arrives with the HTTP
  service. Driven by `scripts/price_json.py`; consumed by `integrations/excel_vba/`.
- `src/pricer/` — **✅ NEW (2026-08-15, the template-layout target; see Code-structure migration
  section):** `core/pricing/{analytical,cashflows,discounting}` + `core/risk/sensitivities` +
  `core/market/{spreads,curves}` + `core/utils/dates` + `assets/corporate/{bonds_input,vanilla}`;
  `pricing/{bond_price,calibrate,risk}` are now SHIMS over it — edit the `pricer` modules, not the shims.
- `src/pricing/` — ✅ `bond_price.py` (`BondPrice` port: ACT/364, 182-day schedule, accrued, clean/dirty;
  **default = corrected DF**, `vba_compat` reproduces the legacy `exp(-t·z_semi)` bug; `oas`/`freq` params;
  since 2026-08-04 exports `coupon_dates` + `accrued_interest` [THE single AI formula] + `lattice_inputs`) ·
  ✅ `calibrate.py` (`implied_oas`: solve OAS s.t. clean=`BT`) · ✅ `risk.py` (`risk_metrics`: effective
  duration / DV01 / convexity by ±1bp = parallel-shift bump) · ✅ `coupon_schedule.py` (**Step-3** coupon
  time-table for stepped/step-up/zero; threaded through `price_bond`/`implied_oas`/`risk_metrics`) ·
  ✅ `frn.py` (**Step-4** FRN: forward-projection off `ZeroCurve` + spread, single-curve discount, implied
  OAS; **curve-bump eff-dur ~ next reset**) ·
  ✅ `hybrid.py` (**fixed-then-float** = price_bond fixed leg to the switch + price_frn floating leg after,
  glued on one curve+OAS; degenerate limits delegate bit-exact; margin-0 telescoping identity = the
  composition test; consumes `data/hybrid_switch_terms.csv`; `next_switch_t` + price-to-call reference) ·
  ✅ `lattice.py` (**v2** callable/putable BDT
  short-rate tree: fwd-induction Arrow-Debreu calib to `ZeroCurve`, arb-free; implied OAS + eff-dur; NOT a
  `BondOAS` replica — invariant-validated; `call_array`/`put_array` read a `[(time,price)]` schedule from
  `dataio.call_schedules` — no hard-coded par-call; driver `scripts/callable_risk.py`, σ=0.15; since
  2026-07-22 also prices the 5 AGY callables — their par-call rows appended to `data/call_schedules.csv`;
  since 2026-08-04 `coupon_times=` real-ACT/364-grid mode + `accrued=` on `implied_oas`/`risk_metrics` —
  clean-vs-clean calibration, dirty-base duration, regular-`T` grid kept for synthetic tests) ·
  ✅ `ilb.py` (**phase-2** inflation-linked: nominal curve + `ratio_0·(1+FIP_INFL)^t` path; spread-vs-nominal
  calibration ≈ −breakeven @0 — own column, never credit OAS) ·
  ✅ `mbs.py` (**phase-2** static-CPR pool skeleton on the exact 8-mnemonic Bloomberg interface;
  level-pay+SMM, price/implied-spread/implied-CPR/risk+WAL — awaiting Mario's pull).
- `src/instruments/` (Bond model + cash flows) · `src/risk/` (CreditMetrics, later) · `src/config/`.
- `tests/` — golden-master (`test_bootstrap`, `test_ratings`, `test_universe`, `test_oas`) + `test_lattice`
  (v2 callable-lattice **invariants**: par-reprice/arb-free, callable≤straight≤putable, σ=0 degeneracy, multi-date
  schedule ordering) + `test_call_schedules` (loader: multi-row grouping, date→time clamp) + `test_universe`
  coupon-class locks (pivot reconciliation, canonical-all-F/vanilla, funnel-bucket split) + `test_coupon_schedule`
  (formula parser + schedule-aware pricing: past-step→flat, future-step, zero) + `test_frn` (FRN
  invariants: par-under-any-shift, OAS round-trip, near-par dur≈0, dur ≪ same-maturity fixed) + `test_hybrid`
  (bit-exact limits, margin-0 identity) + `test_ilb` (exact degeneration to `price_bond`, ratio scaling,
  the −breakeven identity) + `test_mbs` (annuity degeneration, principal conservation, par-at-WAC,
  dur↓ in CPR, Bloomberg interface) + `test_phase2_universe` (goldens 39/9/15 + routes + ratios) +
  `test_price_convention` (16: per-engine clean-form vs dirty-form OAS root invariance <1e-10, shared-AI
  identity locks, lattice≡price_bond, val-on-coupon-date corner) + `test_pricer_structure` (8:
  template-layout locks — shim identity, bit-exact wrapper reprice, bp round-trip, flat-curve
  zero-coupon closed form, sensitivity arithmetic, input validation) + `test_monthly_curves` (13:
  the Monthly-recon curve replica) + `test_vanilla_json_endpoint` (28: endpoint↔direct-call parity
  with `==`, the three live curve failure modes with a no-file-path assertion, the Excel-serial
  date refusal, the calibrate-mode OAS lock, lenient normalisation/warnings, 2 CLI subprocess
  runs). **194 total** (~20s of engine tests; the workbook-loading tests dominate wall clock).
