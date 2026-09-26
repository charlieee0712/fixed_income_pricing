"""Securitised and pooled products — the thin wrapper layer.

Companion to ``assets/corporate/`` and ``assets/government/``. Four classes of Mario's book
belong here; one has an engine so far:

  pool         Government Mortgage-Backed     888 master rows -> 882 securities   engine built
  (planned)    Non-Government C.M.O.s         265 master rows -> 264 securities
  (planned)    Asset-Backed Securities         79 master rows ->  79 securities
  (planned)    Commercial Mortgage-Backed      73 master rows ->  69 securities

Named **securitized**, not **mortgage**, because asset-backed securities are in this book and
car and card receivables are not mortgages. All four share the same shape — many loans pooled,
borrowers who may repay early — and so share ``core.pricing.prepayment``.

⚠️ **There is no driver and no output file for any of these yet**, which is exactly why the
engine was migrated now: every earlier migration in this project had to hold production CSVs
byte-identical, and this one had nothing to hold. The moment the first pool driver exists that
is no longer true.

⚠️ **Nothing in this package routes a security to an engine.** Routing has a single owner per
class — for the three migrated families that is ``dataio.phase2``, and a pool router will be
one named function there too, not a set of branches spread across wrappers. Duplicating routing
rules into an asset module is the "two files owning half a decision" defect this project has
closed five separate times.

⚠️ **The static model does not respond to rates.** A constant CPR means the cash flows are
fixed, so every risk number here is a SPREAD duration of fixed flows, not an option-adjusted
one. Real pools prepay faster as rates fall, which is what makes mortgage paper negatively
convex; that behaviour is the v2 prepayment model and is absent by construction. A convexity
figure from this layer is not the market's convexity, and reporting it as if it were would be
the quiet kind of wrong.
"""
