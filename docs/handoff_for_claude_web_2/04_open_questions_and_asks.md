# Open questions and outstanding asks

Who owes what to whom, and what must **not** be re-asked yet.

---

## 1. With Mario — sent, awaiting reply

| Sent | What | Status |
|---|---|---|
| 2026-07-20 (WhatsApp) | The **11-security Bloomberg list**: 3 exempt US FRNs (all terms) + 8 hybrids (post-call margin only). Table is in `docs/isin_lookup_2026-07-20.md`. | no reply yet |
| 2026-07-22 (WhatsApp) | The **Govt-MBS 8-field × 882-CUSIP pull**, with `outputs/govt_mtge_cusips.csv` attached. | no reply yet |
| 2026-08-25 (pending user action) | The weekly report + the updated Drive folder. Contains two questions (below). | user sends |

## 2. Questions inside the current report (2026-08-30)

1. ⭐ **How should the extra bond types appear on the demonstration spreadsheet?** One sheet
   with a bond-type dropdown that shows and hides the fields each type needs, or one small
   sheet per type. It is purely a layout decision — a couple of hours either way — and it is
   his team's daily view, so it is his call.

   ⚠️ **Restated 08-31; the earlier wording overstated the blockage.** This is no longer "the
   only live blocker", and the bridge no longer "sends plain bonds only". The bridge now
   constructs **five** of the seven types and five are verified by real-Excel round trips.
   What is missing is the *worksheet*, not the plumbing: the engineering test surface drives
   named cells directly, and the visible demo workbook (`DemoBuilder.bas`) is still
   vanilla-only. Two types (`stepped`, `fixed_to_floating`) are deliberately left
   unconstructible so that answering this question does not arrive pre-empted.

**Answered by the 08-27 meeting, no longer open:**

- ~~Which workbook should carry the Excel demonstration?~~ — the small demonstration workbook
  stands; the authoritative holdings file is never touched.
- ~~Is the rollout order still right?~~ — yes, and Mario refined it himself by marking the six
  pivot cells. Those are now done; mortgages are next and are waiting on data, not on us.

Also still open from the August sample, and low-stakes: **`bons_input.py` vs
`bonds_input.py`** — the template's spelling looked like a typo, and the repo kept
`bonds_input.py`.

## 3. With Liping — sent, awaiting reply

Full gap request sent 2026-07-30 (she has campus Bloomberg access, a second channel):
MBS 8×882 with a BDP template, pass-through terms for **13 unique securities**, the
11-security list, and one item that was not on any earlier list — the **AssuredGty
US04622DAA90 call schedule** (`TNTD04923866`, the unpriced fifth callable). She also
code-reviews: her v2 review triggered the 2026-08-04 clean/dirty audit and the lattice fix,
and the response report was sent to her 2026-08-04.

**Dedupe Mario's and Liping's returns before loading** — they were asked for overlapping
data on purpose.

## 4. DEFERRED asks — do not raise before the next touchpoint

These are held deliberately until Mario returns the MBS data, so that a busy counterparty
gets one consolidated request rather than a drip:

- **KTBi indexation terms** + a KRW curve row for 2009-03-31 (a single $1.2M position,
  BT-marked, nothing downstream depends on it);
- **agency call schedules** (the par-call lattice already matches custodian AQ on 4 of 5 —
  this is confirmation, not a blocker);
- the **`TNTD04366584` A/Aa2 rating quirk**;
- the **lost `SteepFlat Table Monthly.txt`** twist table — becomes an ask only when the
  steepening/flattening (T/U) work actually starts. 43% of FIXED rows have a zero twist, so
  a good deal is reconcilable without it;
- ~~a **usable GBP curve**~~ — **WITHDRAWN 2026-08-30. Do not raise this with anyone.**
  It was never a data gap: the GBP file stores par yields in percent while 24 of the 26 store
  decimals, our loader scaled it by 100, and the bootstrap correctly refused the resulting
  73%–415% curve. Both GBP bonds now price. See `05` §1.9. If Liping returns a GBP curve
  anyway (it was on her 07-30 list), treat it as a **cross-check**, not a fix.

A plan that opens one of these without the user asking is a plan that will be edited.

## 5. Genuinely undecided — a plan could usefully take a view

1. **When to migrate the remaining engines** (`curves/`, `credit/`, `dataio/`, ILB, MBS)
   into `pricer/`. Rollout order after floating has never been fixed beyond the sample
   report's proposal.
2. **Whether the endpoint should grow a batch mode**, and when. Today a batch payload is
   refused with a clear message; the single-bond object is canonical. Mario's own phrasing
   was "for each bond", which supports the current choice.
3. **What happens to the `pricing/*` shims** in the long run — retire them, or keep them
   permanently as the public surface?
4. **The original-face sinking-fund basis** (strip decomposition) — worth building only if
   real terms arrive that need it.
5. **EIR / amortised cost (IFRS-9)**: it is a *requirement*, not legacy code — a search of
   14k VBA lines and every sheet found zero hits. There is no golden to reconcile to. The
   spec preset (Z as amortised carrying value, EIR = IRR of Z against remaining cash flows)
   is waiting on CEO confirmation, and implementation was deliberately parked until after
   the v1 report.
6. **CreditMetrics risk layer** — the eventual destination, untouched so far.

---

## Refresh 2026-09-16 — four rounds since 2026-08-31

### ⭐ Two new questions FOR Mario, both better asked with something working in hand

1. **Where do the three inflation-linked inputs sit on the worksheet?** — a real coupon,
   an index ratio, an inflation assumption. The engine and its wrapper are finished and
   deliberately unreachable from Excel until he answers. This is section 7 of the
   2026-09-10 report and the only thing blocking an eighth instrument type.
2. **Which Azure tenant, and which shape?** He asked for the code to run on Azure so
   "everyone in our group can run and test these codes". ⚠️ A personal free subscription
   on a university email is not where a group's shared environment belongs — not a
   sensitivity point, simply that his people need a tenant they can be added to. And his
   words point at *a shell each* while his Excel proposal points at *a called service*.

### Answered since the last refresh

* **Is the client data sensitive enough to keep off a cloud tenant?** — Mario, 09-15:
  **no**. The repo was cloned whole onto Azure. ⚠️ The *tenant* question above is separate
  and still open.
* **Is the Excel/JSON interface in sync with the code?** — measured 09-13: functionally
  yes (nine of eleven committed fixtures reproduce byte-for-byte). The documentation was
  not, in three places, all now fixed.

### Unchanged, and still the largest unlock

**The Govt-MBS 8-field × 882-CUSIP Bloomberg pull**, requested 2026-07-22. 882 securities,
plus the CMO/ABS/CMBS block behind it. `pricing/mbs.py` is built and waiting on the exact
8-mnemonic interface — the data lands, zero code changes.

⚠️ **Do NOT re-raise before Mario returns that data:** KTBi indexation terms + the KRW
3-31 curve row; agency call schedules (confirmation-only); the `TNTD04366584` rating
quirk; the `SteepFlat` file; `FHR-3122-ZB`.

---

## Refresh 2026-09-26 — the mortgage round

### ⭐ Two asks sent to Mario on 09-26 (WhatsApp), both unanswered

**1. Re-pull three CPR fields with a 2009-03-31 as-of override.** The delivered pull is
as-of the pull date, so its prepayment speeds describe 2026. Only
`MTG_GEN_CPR_3M / 6M / 12M` are affected; WAC and loan size are fine either way.
⚠️ **Also told him `MTG_HIST_COLLAT_CPR_LIFE` is not a Bloomberg field** — 877 ×
`#N/A Invalid Field`, an error in the list *we* sent. Owned, not glossed.

⭐ **This sharpens rather than unlocks, and the message says so**, because otherwise he
would chase it as a blocker. Measured: ±5 pp of CPR uncertainty is ±12 bp of spread on a
250 bp number.

**2. Deal-level structure data for ~756 tranche securities.** A third of the book.
⚠️ **Framed explicitly as a different KIND of request** from the field pulls so far —
probably a cost decision rather than a scheduling one. If this is not clear to him he will
hear "you need a few more weeks of coding", which is the wrong picture entirely.

### Answered since the last refresh

- **"Do you want a hosted service as well?"** (`azure_trial_report_2026-09-16` §4.2) —
  **yes.** He demoed a browser front end calling Azure APIs. The *timeline* half of that
  question, and the tenant, are still open. See `25` and
  `docs/client_directive_browser_azure_architecture_2026-09-26.md`.
- **"Can we source inflation data ourselves?"** — done 09-19, and the measurement redirected
  the work: a constant per-country assumption is a no-op, so the data landed on the index
  ratio instead. All 13 US ratios validate to 5.9e-06.

### Still unchanged

The July asks (G2 pass-through schedules 13, G3 FRN/hybrid terms 11, G4 one call schedule)
and the deferred confirmation queue. Mentioned in the 09-26 message as "a short list, none
of it urgent" rather than itemised — the two asks above are what need a decision.
