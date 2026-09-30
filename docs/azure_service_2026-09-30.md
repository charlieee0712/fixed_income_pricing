# The pricing tool now runs in the cloud

**2026-09-30 · one page**

In September you asked whether the code could live somewhere **everyone in the group can
run and test it**, rather than only on our own machines. In the trial two weeks ago we
answered half of that: the engine runs unchanged on Azure. **This is the other half — it
is now a service anyone authorised can call, and we have proved it gives the right
answers.**

---

## What it is

A single web address. You send it one bond; it sends back that bond's price, spread and
risk figures. Nothing is installed, and there is nothing to keep up to date.

⭐ **It is the same request our Excel bridge already sends.** A spreadsheet and a web page
are simply two things knocking on the same door — which means **the browser front end you
demonstrated needs no new pricing work from us**. The page changes where the request is
*assembled*; what it means, and what comes back, is already built and tested.

The same is true of running many bonds at once: we made a single bond the unit of work back
in August, so pricing a hundred of them in parallel needs nothing new.

**It is switched off at the moment**, on purpose — nobody is calling it yet, and a service
that is off cannot be reached by anyone. Turning it back on takes about a minute.

---

## Why we believe it, rather than just hoping

"The website loads" is a much weaker claim than "it produces the right numbers", so this is
the part worth a paragraph.

We keep **11 reference bonds** with their correct answers recorded in the project — a plain
bond, a callable, a puttable, a sinking-fund bond, two floating-rate notes, and five cases
that are *supposed* to be rejected. One command sends all 11 to the cloud service and
compares every figure that comes back against the recorded answer:

> **All 11 matched. 156 individual numbers, none of them different.**

⭐ Two details that make that worth something. The check **reports how many numbers it
compared** and refuses to declare success if it compared too few — a clean result that
quietly examined nothing is worse than a failure. And it **runs on any ordinary computer**,
with nothing from our pricing environment installed, so you or the cloud team can run it
against the service yourselves at any time.

---

## What it costs, and a choice for you

**About USD 13 a month**, on the card registered to the account. That is the smallest
option that keeps the service warm; the free option puts it to sleep after twenty minutes,
which makes the first request of the day take a minute and look broken.

⚠️ **Switching the service off does not stop that charge** — the hosting is billed whether
it runs or not.

Because the whole setup is now a single script rather than a sequence of manual steps, we
can **rebuild it from nothing in about five minutes**. So deleting it between
demonstrations is a perfectly reasonable thing to do.

**Two options, your call:**

| | cost | to have it back |
|---|---|---|
| leave it in place, switched off | ~$13/month | about a minute |
| delete it between demonstrations | **nothing** | about five minutes |

---

## Two things deliberately left undone

**Sign-in.** Access is currently limited to one network address — ours. Proper sign-in,
where you add a colleague and they can simply use it, is written and ready to switch on.
⭐ We have held it back on purpose: **a person signing in through a web page and a program
signing in automatically need different arrangements**, and choosing before your browser
front end is designed means choosing twice. **The trigger is the first person who needs
access who is not us** — tell us who, and it is a short job.

**Letting a web page call it.** By default a browser blocks a page on one address from
calling a service on another. ⚠️ It does this *in the browser*, before the request ever
reaches us, so it leaves no trace anywhere on our side and simply looks like the service is
down. It is a one-line setting — but the line has to name the page it is permitting, which
is a decision that belongs with the front-end design.

⭐ **Both of these wait on the same thing:** where the browser page is going to live. Once
that is decided, they are an afternoon.
