# Comms and counterparties

Who is involved, what has been sent, and the discipline around asking for more.

---

## 1. The people

**Mario** — the decision-maker on method and scope. Reviews quickly, forwards to non-quant
readers, and gives direction in short WhatsApp messages rather than documents. His calls so
far: OAS as a calibration output (2026-06-30), the 3-31 curve (2026-07-02), σ = 0.15 and
data-driven call schedules (2026-07-03), coupon-type routing (2026-07-08), the pass-through
/ amortising decisions (2026-07-20), the missing-data-table framing (2026-07-30), the
code-structure directive (2026-08-15) and its approval with three follow-ups (2026-08-25).

**The Google / cloud team** — taking over the code for cloud optimisation, and **as of
2026-08-25 they attend the briefing in person**. That changes how deliverables are written
(see `22`).

**Liping** — a colleague with campus Bloomberg access: a **second data channel** and a code
reviewer. Her v2 review triggered the 2026-08-04 clean/dirty audit and the lattice
calibration fix — a genuinely valuable catch. The response report went to her the same day.

**The user** — runs the CLI session, relays to Mario and Liping, and decides what gets sent
and when.

## 2. Timeline of what has been sent

| Date | To | What | Status |
|---|---|---|---|
| 2026-07-20 | Mario | the **11-security Bloomberg list** (3 exempt US FRNs, all terms; 8 hybrids, post-call margin) | no reply |
| 2026-07-20 | Mario | the `corporate_bond` project folder, via Google Drive | delivered |
| 2026-07-22 | Mario | the **Govt-MBS 8-field × 882-CUSIP pull** + `outputs/govt_mtge_cusips.csv` | no reply |
| 2026-07-30 | Liping | the **full gap request**: MBS 8×882 with a BDP template, pass-through terms for 13 uniques, the 11-security list, and the AssuredGty call schedule | no reply |
| 2026-08-04 | Liping | the code-review response report (EN PDF) | delivered |
| 2026-08-25 | Mario | the code-structure sample (Drive) + WhatsApp note | **approved**, with three follow-ups |
| 2026-08-25 | Mario | the weekly report + refreshed Drive folder | user to send |

A planned 2026-07-21 phase-2 request was **never sent**; a trimmed version went on 07-22
instead. Worth knowing so the record is not misread as two requests.

## 3. The deferral discipline

Several asks are deliberately **held** until Mario returns the MBS data, so that a busy
counterparty gets one consolidated request instead of a drip: KTBi indexation terms + a KRW
curve row, agency call schedules (confirmation only — the par-call lattice already matches
custodian AQ on 4 of 5), the `TNTD04366584` rating quirk, the lost SteepFlat twist table, and
a usable GBP curve.

This is a real constraint on plans. A plan that opens one of these unprompted will be edited
before execution.

Related: **dedupe Mario's and Liping's returns before loading** — they were asked for
overlapping data deliberately, as two channels onto the same terminal.

## 4. What Mario actually asked, in his own framing

Worth keeping close, because the wording shapes the right answer:

- *"what happens if volatility of yield changes, for OAS and price"* — he asked for the
  **effect**, not whether the field is an input. That is why the answer is two experiments
  and a signed, per-bond table.
- *"add currency to our input"*.
- *our code runs in our own Python environment; when he and the Google team take it over,*
  **"can they create ways from Excel to run Python code, to pass these inputs and
  parameters?"** — with his own proposal: Excel/VBA reads cells → JSON **per bond** → Python,
  **"one JSON in, one JSON out"**. The single-bond canonical unit follows directly from his
  phrasing.
- earlier, on structure: the code was *"difficult to follow, a bit nested"*; he wants **many
  simple functions** with **inputs highlighted**.
- on interim data (2026-07-30): web-sourced terms are fine as interim but *"not as precise as
  bloomberg"*; what matters is that the process is automated and working end to end, and that
  every unavailable field is **specified on a table**, so that when complete data arrives
  *"we'll run all what you've built"*.

These are recorded as a **recollection**, not a transcript — they were relayed from memory,
and the record says so. If a plan turns on the exact wording of one of them, ask.

## 5. Confidentiality

The repository contains a real client portfolio and must stay **private**. The handoff
bundles carry internal comms framing and must **not** go into the Drive staging copies that
Mario receives. Drive access to the shared folder is Mario-only.

---

## Update 2026-08-30

### The meeting of ~2026-08-27, and how this client communicates

Mario discussed the 08-25 report, **agreed the next-week plan**, and then gave the actual ask
**by annotating the workbook**: a new column F on the `Pivot of Corp Bonds` sheet, `finished`
against the plain-fixed row, `no` against six others.

That is worth internalising: **this client's directives can arrive as spreadsheet
annotations**, not as messages. The column is now committed with the workbook, because it is
the only record of what was asked and when. Check the workbook's diff after a meeting.

### One thing we owe him, stated plainly in the report

Section 3 of the 08-30 report says, in his language, that the sterling-curve blockage we had
reported to him was **our bug** — a units mistake in our loader, not bad market data — and
that the replacement-curve request is withdrawn. It also says that the same bug had been
silently dropping a bond from the class he had already been shown as complete.

**Reporting this rather than quietly fixing it is the decision.** He has been making planning
decisions partly on the strength of a coverage number that was wrong, and the correction is
more useful to him than the two extra bonds.

### Outbound status

- **Nothing new was asked of Mario or Liping this round**, and the deferral discipline stands.
- The **GBP curve is off Liping's 07-30 list**. If she returns one anyway, it is a
  cross-check, not a fix.
- **One question is outstanding to Mario**, inside the 08-30 report: how he wants the extra
  bond types laid out on the demonstration sheet. It is the only thing blocking us on the
  Excel side, and it is deliberately posed as his call rather than presented as done.

### The standing shape of a report to this audience

Unchanged and working: plain language throughout with each bond term defined in a clause where
it first appears, **one clearly-labelled engineering section** the finance reader can skip, and
a statement in the opening of which section is for whom. The Google team attends in person.
