BLOOMBERG DATA REQUEST
URS fixed income pricing project
Prepared 2026-10-02

--------------------------------------------------------------------------
WHAT THIS IS
--------------------------------------------------------------------------

Four Excel files. Each one already contains the Bloomberg formulas; nothing
needs to be typed. Open the file on a machine with the Bloomberg Excel
add-in, let it calculate, save, and send it back.

We are valuing a bond portfolio as it stood on 31 March 2009. For mortgage
and asset-backed securities we need to know how much of each one was repaid
in each month since then, and what interest rate it paid. Both are published
monthly facts with a date, which is what these formulas ask for.

--------------------------------------------------------------------------
PLEASE RUN THEM IN THIS ORDER
--------------------------------------------------------------------------

   01_CHECK_FIRST.xlsx       3 securities      under a minute
   02_factor_history.xlsx    375 securities    the important one
   03_coupon_monthly.xlsx    156 securities
   04_coupon_classify.xlsx   595 securities    quick

Sheet 01 is three cells' worth of work and it answers whether this terminal
can return this kind of data at all. If it comes back empty, please tell us
what the cells say and stop — the other three would fail the same way, and
there is no point spending the time.

If time runs short after that, 02 is the one that matters most.

--------------------------------------------------------------------------
EVERY FILE WORKS THE SAME WAY
--------------------------------------------------------------------------

   * The first tab, "READ ME", says what that sheet is and what a good
     result looks like. The second tab, "data", is the sheet itself.

   * If the cells do not fill in on their own, press Ctrl+Alt+F9.

   * Please save as .xlsx and send the files back as they are. Sorting,
     deleting or inserting rows and columns would separate the numbers
     from the securities they belong to.

   * Blank cells at the bottom or the right of a column are normal. They
     mean that security had already been repaid by that date.

--------------------------------------------------------------------------
ONE THING WE CANNOT ASK FOR
--------------------------------------------------------------------------

There are 412 securities in these three categories. 375 of them are in
sheet 02. The remaining 37 have no ISIN recorded in the custodian file we
were given, so there is no identifier to look them up by. That is a gap on
our side, not something this request can close, and it is noted here so the
difference between 412 and 375 is not a mystery.

--------------------------------------------------------------------------
IF ANYTHING LOOKS WRONG
--------------------------------------------------------------------------

Please send the file back as it is, with the error text showing. An error
message tells us exactly which field or which security the terminal did not
accept, and that is genuinely more useful to us than a blank sheet or a
partial one. Nothing here is wasted effort.

Thank you very much for doing this.
