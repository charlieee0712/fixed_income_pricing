# The running coupon of a floating-rate note is now held fixed when we measure its rate risk

**2026-08-31 · the one intentional change to a published number in this round**

## What a floating-rate note is, and what "the running coupon" means

A floating-rate note pays a coupon that is reset periodically — every six months, say — to
whatever a reference interest rate happens to be on the reset date, plus a fixed margin. On any
day between two resets, the coupon *now being earned* was already decided at the last reset. It
is a known amount. The next one is not: it will be set at the next reset date, from a rate
nobody knows yet.

Measuring the note's interest-rate risk means asking: if the whole interest-rate curve moved up
by one basis point today, how much would this note be worth? We answer it by repricing the note
on a shifted curve and comparing.

## The defect

A curve shift changes every coupon that has not yet been set. It cannot change the one that
already was. Our engine got this right whenever the custodian file recorded a numeric coupon —
we passed that number in and it stayed put through the shift. When the field was blank, the
engine projected the running coupon off the curve like all the others, **and then the shift
moved it too.**

The consequence was not a small error. It reversed the sign:

| running coupon | measured duration | reads as |
|---|---|---|
| recorded in the custodian file | **+** time to the next reset | risk ends at the next reset — correct |
| not recorded | **−** time since the last reset | risk accrues backwards from the last reset |

Two notes with the same issuer, the same maturity and the same economics received
opposite-signed risk numbers, and the thing that decided which was whether a custodian field
happened to be numeric. Nothing anywhere reported this. The negative numbers were carried in the
output and explained in the documentation as a real second regime.

## The fix

`frn_risk_metrics` now freezes the running coupon across the bumps in both cases. When it was
not recorded we freeze a **base-curve proxy**: the rate the *unshifted* curve implies for the
current period, read back off the engine's own cash-flow grid so that it uses the true period
start (which is before the valuation date) and already includes the quoted margin.

Because the proxy is taken from the unshifted curve, at zero shift it reproduces the old number
exactly. **Price and calibrated OAS therefore cannot move.** Only the three sensitivity columns
do, and afterwards the two regimes are one code path rather than two.

The freeze lives in the risk function, not in the pricing function. `price_frn` stays a plain
scenario repricer, which keeps intact the invariant that anchors the whole floating engine: a
pure floater must hold par under *any* curve shift.

## What moved

Six bonds at each valuation date — every `route=floating` row that had a negative duration, and
no others. The seventh floating row had its coupon recorded, was already frozen, and did not
move. `callable_risk` and both `phase2` files are byte-identical; within the corporate files
only `eff_dur`, `dv01` and `convexity` differ.

| asset | BT | duration before | duration after | Δ | τ·(100/P) | ratio |
|---|---|---|---|---|---|---|
| TNTD04955876 | 69.62 | −1.1322 | −0.4313 | +0.7009 | 0.7182 | 0.98 |
| TNTD04259874 | 72.64 | −1.3663 | −0.6878 | +0.6785 | 0.6883 | 0.99 |
| TNTD03035014 | 92.92 | −0.3322 | **+0.1990** | +0.5311 | 0.5381 | 0.99 |
| TNTD04882955 | 67.04 | −1.8521 | −1.4814 | +0.3707 | 0.3729 | 0.99 |
| TNTD04131505 | 81.34 | −0.4719 | −0.1669 | +0.3050 | 0.3073 | 0.99 |
| TNTD03027773 | 98.54 | −0.2042 | **+0.0491** | +0.2533 | 0.2537 | 1.00 |

*(2009-03-31 baseline. The 2009-06-10 control moves the same six by the same amounts to within
0.03y; τ = one coupon period, P = the custodian price.)*

Every move is **positive**, and every move matches the first-order prediction — one coupon
period, scaled by how far below par the bond trades — to within 3%. That scaling is why the
correction is largest for the notes trading nearest par and why it is not a uniform shift.

## What is deliberately unchanged

Four of the six are still negative afterwards, and that is correct rather than a residue of the
bug. A floater trading far below par does so because its credit spread is wide, and that wide
spread behaves like a fixed annuity sitting on top of the floating leg. The annuity has ordinary
fixed-income sensitivity, and at a price in the 60s it is large enough to dominate the stub. The
bug removed here was the engine repricing a coupon that was already set; the spread annuity is
real economics and stays.

The two notes closest to par (92.92 and 98.54) cross into small positive durations, which is the
textbook floater result and is the clearest sign the correction is doing what it should.

## Locks

`tests/test_pricer_floating_structure.py` pins the change in one assertion — the stub cash-flow
amount is *identical* under −1bp, 0 and +1bp — plus the regime merge (projected and supplied
now return the same duration, DV01 and convexity) and the unchanged base price. The Round-2b
test that asserted the negative regime has been rewritten in the same commit; its docstring
records that it documented real pre-change behaviour, and that the behaviour was the defect.
