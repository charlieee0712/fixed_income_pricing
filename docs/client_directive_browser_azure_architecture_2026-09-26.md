# Client direction — a browser front end calling Azure pricing APIs

**Recorded 2026-09-26.** Mario showed JavaScript, written inside an HTML file, at a meeting a
few days earlier (exact date not noted). **Not started, and not scheduled: the work waits
until instrument coverage is complete.** This file exists so the direction is on record while
it is fresh, and so that what we already have can be lined up against it.

---

## 1. What was shown — Lichen's recollection, not a transcript

⚠️ **Treat every word in this section as approximate.** It is one person's recollection of a
demo in a language he does not work in, written down two days later, and he said so at the
time. Nothing here should be quoted back to Mario as his own words, and anything load-bearing
should be confirmed before it is built against. The same convention was used for his three
JSON-interface comments in `docs/code_structure_followup_json_excel_2026-08-25.md` §1.

The chain as described:

1. A user makes a request.
2. JavaScript in an HTML file reads the Excel data the user points it at.
3. It routes the request to **different Azure APIs** depending on the fixed-income type.
4. Those APIs run the pricing engines, **in parallel, in the cloud**.
5. Results come back to the page.

And one further remark, the one he was least sure he had heard correctly:

> *some similar types with some different parameters or inputs might share the same API
> endpoints*

---

## 2. What this maps onto, in code that exists today

This section is checkable — every claim points at a file.

| Mario's step | What we have | Where |
|---|---|---|
| 2. read Excel, build a request | The VBA bridge already does exactly this, from inside Excel | `integrations/excel_vba/` |
| 3. route by instrument type | `bond.instrument_type` dispatch over seven types | `endpoints/contracts.py`, `endpoints/pricing.py` |
| 4. run the engine | `analyze_payload(payload) -> dict` — one dict in, one dict out | `endpoints/main.py:28` |
| 4. in parallel | Every request is one bond and carries no state | by design, see §3 |
| 5. return a result | The response object, always JSON-serialisable | `endpoints/contracts.py` |

⭐ **The JavaScript replaces the host of step 2, not the contract.** The Excel bridge and a
browser page are two callers of the same JSON interface; that separation is precisely what the
contract was built for, and it means a second front end costs no engine work.

⭐ **The HTTP layer already has its reserved place, and a reason for being empty.**
`endpoints/__init__.py` lines 20-22:

> *The template also shows `endpoints/routes/` for HTTP routes; with a single non-HTTP entry
> point that folder would be empty nesting, so it arrives with the service.*

⭐ **And this answers a question we asked him.** `docs/azure_trial_report_2026-09-16.md` §4.2
set out option A (each person runs their own copy — done, measured) against option B (one
service everyone calls), and closed with: *"Do you want B as well, and on what timeline?"*
The demo is the answer to the first half. The timeline half is still open.

---

## 3. The remark that sounded odd is the design we already have

⚠️ **This section is our reading, not Mario's statement.** It is offered because Lichen
flagged the remark as one he might have misheard, and it is worth recording that the remark
makes sense as stated rather than leaving it as a suspected mishearing.

There are two ways to expose several instrument types over HTTP:

* **by path** — `/price/vanilla`, `/price/callable`, `/price/floating` … one endpoint each;
* **by payload** — one `/price`, with an `instrument_type` field selecting the engine.

We chose the second, in Round 2b: **one contract, seven types**, dispatched on
`bond.instrument_type`. Callable, puttable and sinking share one binomial tree; vanilla and
stepped share the analytical path. "Similar types with different parameters sharing an
endpoint" is a description of that.

The natural reading of *different* Azure APIs alongside *shared* endpoints is that the split
follows **the shape of the inputs, not the product name**:

| likely grouping | why they group | inputs |
|---|---|---|
| corporate / government / agency / municipal | same request shape | coupon, frequency, maturity, price |
| mortgage pools | nothing in common with a bond request | WAC, remaining term, prepayment rate |
| CMO / structured | different again | deal structure, tranche |

That would be a sound design, and it is close to how the code is already organised —
`assets/corporate/`, `assets/government/`, `assets/securitized/` split on the same lines.

⚠️ Sound is not the same as confirmed. **Ask before building.**

---

## 4. What would actually have to be built

Short, and most of it is not ours.

1. **An HTTP wrapper — ours, and thin.** `analyze_payload` already takes a dict and returns a
   dict, so the wrapper is request-body-in, response-body-out with no logic of its own. It
   belongs in the `endpoints/routes/` the module docstring reserves.
2. **An Azure hosting decision — Function App or Web App.** Not settled. Liping raised the
   same question; it affects cold-start behaviour and how parallelism is billed, not the
   engine.
3. ⚠️ **Cross-origin access and authentication.** A browser page calling an API on another
   host hits CORS, and an endpoint on the open internet needs an auth story. Neither applies
   to the VBA bridge, which calls a local process — so this is genuinely new ground rather
   than a port of something working.
4. **Reading Excel in the browser** — Mario's side.
5. **Which tenant it lives in.** Open since the September trial: a personal free subscription
   on a university email is not where a group's shared environment belongs
   (`azure_trial_report_2026-09-16.md` §5).

⭐ **Parallelism needs nothing.** When the JSON interface was designed we refused a batch
operation and made **one bond the canonical unit** — at the time for a different reason, that
a single bond is the unit you can verify against a direct call. It happens to be exactly the
shape parallel execution wants: N independent, stateless requests. The decision was made for
correctness and paid off for throughput.

---

## 5. To confirm with Mario, when this becomes live work

1. Is the split across Azure APIs by **input shape** (§3) or by something else?
2. Does the browser page replace the Excel/VBA bridge, or sit alongside it? Both call the same
   contract, so either is fine — but it decides whether the bridge keeps being maintained.
3. Function App or Web App, and in **whose tenant**?
4. Who owns authentication — is the page internal-only, or reachable from outside?
5. Does "parallel" mean many bonds at once (which the current contract already supports, one
   request each), or many *scenarios* on one bond? The second would be a new operation, and it
   is the one that matters for the thousand-scenario what-if on slide 3 of the investor deck.

---

## 6. Status

**Not started. Waits for coverage.** Six non-securitised classes are complete and the mortgage
book is in progress; the structured classes need deal-level data we do not have. Nothing in
this file changes that order, and nothing here should be presented as in flight.
