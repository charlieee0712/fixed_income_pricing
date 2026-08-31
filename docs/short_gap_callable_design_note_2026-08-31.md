# The one callable bond we refuse to price, and what it would take to price it

**TNTD04920858 · design memo · 2026-08-31**

*Plain language throughout; the engineering detail is in §4 and §5, which a finance reader can
skip.*

## 1. What the bond is and why it is stuck

A **callable** bond is one the borrower may repay early, at a stated price, on stated dates. That
right has value to the borrower and costs the lender, so pricing one means working out what the
right is worth — which requires a model that can ask, at each date the right exists, "would the
borrower repay here?"

Our model asks that question on the bond's **coupon dates**. That is not an arbitrary choice: the
coupon dates are where the model's own arithmetic already lives (§4). For almost every callable
bond this is fine, because call dates in practice sit on coupon dates.

TNTD04920858 does not:

| | date | years from valuation |
|---|---|---|
| valuation | 2009-03-31 | 0 |
| … coupon dates … | 2009-09-03, 2010-03-04, 2010-09-02, 2011-03-03 | |
| **last date the model can exercise** | **2011-09-01** | 2.4286 |
| **the actual call date** | **2011-12-02** | 2.6813 |
| maturity | 2012-03-01 | 2.9286 |

The call falls **92 days after the last exercisable coupon date and 90 days before maturity** — in
other words, almost exactly in the middle of the final coupon period, on a 182-day cycle. The
model has no node there. It never has had.

## 2. Why this is refused rather than quietly handled

Before 2026-08-31 the schedule was simply converted to a time, found no node, and the bond priced
as if the call did not exist. The output reported an option worth **0.000000**.

That number was not a valuation. It was the absence of a question. A reader — Mario, the Google
team, anyone reviewing the book — cannot distinguish "we evaluated the borrower's right and it is
worthless" from "we never evaluated it". The first is information; the second is a gap wearing the
costume of information.

So the bond is now **refused by name**, and the refusal states the arithmetic: the earliest
exercise date, the last exercisable coupon date, and maturity. It appears in
`outputs/callable_disposition_<date>.csv` with reason
`call-schedule-not-representable-on-current-grid`.

**This is a reduction in reported coverage and an increase in reported honesty.** One bond that
used to carry a number now carries a named reason instead.

## 3. What we deliberately did NOT do

Two shortcuts were available and both were rejected in this round:

- **Route it to the plain (non-callable) engine.** That produces the same number the bug produced,
  with the same missing caveat, and hides the modelling gap behind a routing decision.
- **Snap the call date to the nearest coupon date.** Moving it back to 2011-09-01 gives the
  borrower a right three months before they have it; moving it forward to maturity removes the
  right entirely. Both are silent changes to a contract term, and neither is visible in the output.

Inserting a raw extra node at the call date is *also* rejected as a quick patch, for the reasons
in §4: it is not one line, and done carelessly it breaks things that currently hold exactly.

## 4. What a real exercise-date grid has to settle (engineering)

The lattice today is built on the true ACT/364 coupon dates, with a **per-step `dt`**. That gives
three properties we rely on and test: the root present value is the true dirty price; a straight
bond on the lattice equals the analytic engine to machine precision; and the calibration solves
clean-against-clean, the same equation the vanilla engine solves. Adding an off-coupon node has to
preserve all three. Three specific questions:

**4.1 Irregular-step calibration.** The Black-Derman-Toy calibration walks forward, fitting each
step so the tree reprices the curve. Inserting a node splits one 182-day step into 92 + 90 days.
The forward induction handles unequal steps in principle, but the volatility parameter is
per-step, and the two fragments must jointly reproduce what the single step did, or every bond on
the lattice moves — not just this one. That is a regression risk across the whole callable set,
which is why it needs its own golden freeze.

**4.2 Off-coupon accrued and call price.** A bond called between coupon dates is repaid at the call
price **plus accrued interest**. Our exercise comparison is currently clean-against-clean, which is
correct precisely *because* every exercise node is a coupon date, where accrued is zero. At an
off-coupon node it is not, and the comparison has to be made explicitly on one basis. Getting this
wrong is worth roughly half a coupon — here, about 2.5 points — and would not look wrong.

**4.3 Event ordering at a node.** At a coupon date the order is unambiguous: the coupon is paid,
then the borrower decides. At an inserted node there is no coupon, so the rule must say the
continuation value is compared without one. If the same code path handles both, the ordering must
be explicit rather than incidental.

## 5. A cheap prototype, if one is wanted

None of §4 is hard; it is simply not a one-line change, and it touches the calibration that every
other callable bond depends on. A non-production prototype — a separate lattice builder taking an
explicit node list, tested against the current one for the bonds whose calls *are* on coupon dates
— would settle 4.1 empirically before any production code moves. Estimated at well under a day.

**It is not scheduled in this round**, and the reason is proportion rather than difficulty: this is
one bond, its call is 90 days before maturity, and the option is very probably worth little. But
"very probably worth little" is a judgement, and the whole point of §2 is that the output should
not present a judgement as a computation.

## 6. Recommendation

Keep the refusal. Build the prototype when the next tree work is scheduled — most naturally
alongside the MBS lattice work, which needs an explicit time grid anyway. Do not open a Bloomberg
request for this bond: the terms are not in doubt, our grid is.
