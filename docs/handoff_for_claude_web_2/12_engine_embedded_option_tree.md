# The embedded-option tree — callable, puttable, sinking fund

This week's work, and the most intricate file in the repo. `core/pricing/tree.py`.

---

## 1. The model

A recombining binomial short-rate lattice. Deliberately a **clean standard implementation,
not a replica** of the legacy VBA `BondOAS`: the legacy fed itself short-end fixings, exercise
schedules and bespoke "SteepFlat" ASCII tables from Bloomberg at run time (none of which we
have, and one of which is lost), and it fitted the curve with a hand-rolled per-step
"sloperow" adjustment rather than a standard calibration. A faithful replica is not merely
undesirable here, it is impossible.

```text
short rate at node (i,j)    r = a_i · exp(σ · √dt · (2j − i)),   j = 0..i
level a_i                   calibrated by FORWARD INDUCTION with Arrow-Debreu state prices,
                            so the tree reprices the input curve's P(0,t_i) EXACTLY
probability                 p = 0.5 (the BDT convention)
one-period discount         exp(−(r + oas) · dt)   — continuous, so the OAS adds flat to
                            the short rate, exactly as a parallel curve shift
volatility                  lognormal, constant σ; v1 default 0.15 (Mario, 2026-07-03)
```

A consequence worth knowing: because the calibration is exact, a **straight** bond on the
tree is independent of σ and equals the directly discounted price to machine precision.
That is a strong internal check and it is a test.

## 2. Two time grids

| Grid | Used by | Property |
|---|---|---|
| `coupon_times` = the REAL remaining coupon dates as ACT/364 fractions | **production** | every grid time is a true coupon date, so the root value is the TRUE DIRTY price |
| regular `T` grid, `dt = 1/freq` | synthetic tests | the valuation date sits on a coupon date, so dirty == clean and `accrued = 0` applies |

The production grid came out of Liping's 2026-08-04 review. Before it, the grid was snapped
and regular, the PV was compared to BT with no accrued anywhere, and a 25-year bond could
lose a whole coupon to a `round()`. Impact of the fix: OAS moved ±35 bp with mixed sign,
durations up to 0.6 y. It was **not** the dirty-vs-clean bug that had been hypothesised, but
it was a real one.

## 3. The rollback, and where exercise fires

```python
cont = 0.5 * (V_up + V_down) * discount        # continuation value
if i >= 1:                                     # EX-COUPON exercise, then pay the coupon
    if call:  cont = min(cont, call_price[i])         # issuer caps
    if sink:  cont = (1-f)*cont + f*min(cont, P[i])   # issuer retires a fraction
    if put:   cont = max(cont, put_price[i])          # holder floors
    V = cont + coupon
```

Three things a plan should know about this block:

1. **exercise is tested ex-coupon** — the holder receives the coupon in addition to the
   exercise price. That is the legacy order and it is documented;
2. **the root (i=0) and the terminal node are never exercisable** — you do not exercise at
   issue or at redemption;
3. **call is applied before put**, so a contradictory pair would silently favour the holder.
   The wrapper refuses that combination; the core itself still resolves it that way.

## 4. Call and put schedules

`[(time_years, price)]`, built into a per-step array by `_schedule_array`. The semantics are
a **step function**: a right is exercisable at that price from its date **onward**, until a
later entry supersedes it. So `[(t, 100)]` means "callable at par from t to maturity", which
is the common case, and a multi-row schedule expresses a declining call price.

There is **no hard-coded par call anywhere**. The schedule comes from
`data/call_schedules.csv` via `dataio.call_schedules` — Mario's explicit requirement
(2026-07-03) so that a real Bloomberg schedule is a data-only change.

## 5. The sinking fund — the new capability

**The product**: on scheduled dates the issuer may retire a fraction of the amount still
outstanding, at a contractual price. It is an issuer option, so it belongs beside the call
rather than in a separate engine.

**The node rule**, applied exactly where the call cap fires:

```text
cont ← (1 − f) · cont + f · min(cont, P)
```

**Why fractions of OUTSTANDING and not of original face.** This is the round's one real
modelling decision and it is structural, not a preference:

> With per-date fractions of *outstanding*, every remaining cash flow — coupons, later
> redemptions, the final principal — scales linearly with the amount outstanding. The value
> *per unit outstanding* therefore does not depend on how much was retired earlier, the node
> value is path-independent, and the tree stays recombining. With fractions of *original*
> face, a fixed retirement amount works against a shrinking base, per-unit value stops being
> level-free, and a recombining tree can no longer represent it — that structure needs a
> **strip decomposition** (one callable sub-bond per sink date), which is deferred.

`fraction_basis="original"` is **refused** with a message naming the strip decomposition.
Accepting the label while running the other model would silently change the number.

**Properties, each a test:**

| Property | Why it matters |
|---|---|
| `f = 1` reduces to `min(cont, P)` — literally the call path, bit for bit | the anchor: the new rule is the old rule at the limit |
| `f = 0` prices the straight bond | an explicit "nothing retired on this date" is a no-op |
| value is non-increasing in `f` | an issuer right can only cost the holder |
| cumulative retirement `1 − ∏(1 − fᵢ) ≤ 1` **by construction** | no separate range check is needed |
| inactive steps carry `f = 0` | the formula never multiplies a fraction into a price alone, so `0 × inf` (NaN) is impossible |

**One semantic difference from a call, easy to miss**: a sinking entry fires **only on its
own date**; a call array stays exercisable from its date to maturity. Comparing the two
naively compares a European right with a Bermudan one — the anchor test therefore compares
at the *node*, not through the wrappers.

## 6. Refusals in the wrapper layer

- `put > call` on a shared date — contradictory terms;
- a sinking date coinciding with a call or put date — two rights on one node need a defined
  order and none is tested (the core keeps all three arrays possible, so the legacy
  `CALL/SINK` route stays reachable once an order is decided);
- two redemptions inside one coupon period — the tree resolves exercise on coupon dates and
  would otherwise coarsen the schedule silently;
- a fraction outside [0, 1]; a basis other than `outstanding`; a schedule entirely after
  maturity.

## 7. Calibration and risk

`implied_oas` solves `tree PV − accrued == BT` — clean versus clean, using the **shared**
accrued formula. `risk_metrics` bumps the OAS ±1 bp (identical to a parallel short-rate
shift) and divides by the **dirty** base. For a callable this correctly captures the
option's rate response: duration is shorter than the straight bond's, and convexity can be
negative.

## 8. The volatility experiments

Two questions that must never be conflated:

```text
price_at_volatility        hold the spread, move σ   -> what happens to the PRICE
implied_oas_at_volatility  hold the mark,   move σ   -> what happens to the SPREAD
volatility_sensitivity     both local slopes, per 1 volatility point, units named
```

Directions, on deliberately option-active fixtures: an **issuer** right (call or sinking)
makes the price fall and the recalibrated spread tighten as σ rises; a **holder** right (put)
does the opposite. These are statements about those fixtures, not universal claims — for a
bond priced far from its exercise price, σ moves essentially nothing.

## 9. Production reality

Three corporate callables (one EUR) and five agency callables price on this engine. Only
**one** corporate has a call that is currently worth anything; the other two are priced far
from par (one at 60) and are insensitive to volatility. The agencies use a Bermudan par call
from the master `AB` date at σ = 0.15 — the industry-standard agency assumption — and their
lattice durations match the custodian's own option-adjusted duration on 4 of 5, which is a
free external validation that the corporate side does not get (custodian AQ for corporates
is a straight duration and misses the call).

---

## Update 2026-08-30

Two additions, both small:

- **`price_detail(...)`** returns clean, dirty and accrued from **one** tree build. It exists
  because a caller reporting a full result set — the JSON endpoint, a driver — should not
  build the tree three times to get three numbers. `clean` is bit-for-bit what
  `calculated_price` returns (same call, same order), and `clean = dirty − accrued` exactly,
  because accrued is the one shared date-only formula.
- **The three tree products now reach the JSON interface** via `bond.instrument_type`, with
  their schedules carried as arrays of objects. Two refusals were added at the contract layer
  rather than left to surface from inside the solver:
  - a **sinking schedule with no `sinking_fraction_basis`** — the engine already refused it,
    but from inside the spread solver, so the message read *"no spread reprices this bond —
    check the price, the coupon and the maturity"*, which sends the reader hunting in the
    wrong place. It now names the field;
  - **`"original"` as a fraction basis** — refused with the reason (a fixed share of the
    original face works against a shrinking base; a recombining tree cannot represent it, and
    it needs one callable sub-bond per sink date).

**The volatility answer is now in the response**, both directions, for all three tree
products: `price_effect_per_1pct_vol` (price at a fixed spread) and
`oas_effect_bp_per_1pct_vol` (spread at a fixed price). They answer **different questions and
must never be combined**. Both need a market price, so under `price_at_oas` the second is
`null` with that reason. A full scenario table is opt-in via `analysis.volatility_scenarios`,
because each scenario costs two more solved lattices.

⚠️ **Test fixtures for volatility direction must be option-ACTIVE.** A call struck at 100 on a
bond worth 96 is worthless, and the callable prices identically to the straight bond — which
is correct, and asserts nothing. The dispatch tests use a 9.5% coupon marked at 104 against a
par call, where the price falls 104.0772 → 104.0000 → 103.8615 and the spread tightens
639.58 → 635.78 → 629.83 bp across 10/15/20% volatility.

---

## Update 2026-08-31 — refusals are a named family, and one bond is refused by design

### The refusals stopped being `ValueError`

Every refusal in section 6 used to be a `ValueError`, and the spread solver's own
`except ValueError` swallowed them. A contradictory pair of exercise dates came back as
*"no spread reprices this bond — check the price, the coupon and the maturity"*: three fields,
all correct, and the reader sent to the wrong file. See `05` §1.15 for the full account.

They are now `ExerciseTermsError`, under `ContractTermsError` → `PricingDomainError` →
`Exception`, each carrying the JSON path of the field at fault. **Only `CalibrationError` may
become `CALIBRATION_FAILED`.** The endpoint maps a `ContractTermsError` to `VALIDATION_ERROR`
plus `err.field`, so `bond.put_schedule`, `bond.sinking_schedule`, `bond.call_schedule` and
`bond.sinking_fraction_basis` each name themselves.

### A schedule the grid cannot place is refused BEFORE any spread solving

The lattice exercises on **coupon dates only**, never at the root or at maturity. A call inside
the FINAL coupon period therefore lands on no node: `call_array` comes out all-`inf` and the
bond prices as a straight bond, reporting an option worth exactly `0.000000`.

That number is not a valuation — it is the absence of a question, and no reader can tell it
apart from a genuine zero. `ExerciseScheduleNotRepresentable` + `check_representable` now refuse
it, from both `embedded_option._prepare` and the driver's hand-built path — one rule, two
callers — and **each right is checked separately**, because a live put must not license a dead
call.

⚠️ **The guard tests REPRESENTABILITY, not economic activity.** A sinking `fraction = 0` on a
date is a legitimate contract. A first version conflated the two and correctly broke two
Round-2a tests. The rule: refuse *"the model cannot express this"*, never *"this right happens
to be worth nothing"*.

`TNTD04920858` is the bond this concerns — 850,000 nominal, marked 85.12, callable at par 90
days before maturity. It stays **refused and named** in
`outputs/callable_disposition_<date>.csv`, and
`docs/short_gap_callable_design_note_2026-08-31.md` sets out the three things an off-coupon
exercise node must settle before it can be production code: irregular-step BDT calibration
(inserting a node splits one 182-day step into 92 + 90, and the two fragments must jointly
reproduce what the single step did, or **every** callable moves), off-coupon accrued and call
price (the exercise comparison is clean-against-clean, which is correct only because every node
is currently a coupon date — worth about half a coupon here), and explicit event ordering where
no coupon is paid.

**All eight bonds with call schedules were verified unaffected: latent, not live.**

### The exercise-date conversion is now single-sourced

`schedule_times` delegates to `core/utils/dates.exercise_schedule_times`, as does
`dataio.to_lattice_schedule`. `days_per_year` is deleted — see `05` §1.2, which is now a closed
trap rather than an open one.
