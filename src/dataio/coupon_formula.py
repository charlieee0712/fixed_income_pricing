"""Bloomberg's coupon FORMULAS, as dated rules -- the "transform these formulas into python".

Mario, 2026-10-14 (the user's paraphrase, flagged as approximate): *"for fixed ... coupon
treated like a constant number, fixed with frequency. And now for floating, variable etc. it
changes from a constant number to a formula, eg: same bond and different dates, 2007-2013:
LIBOR+60BPS, 2013-2019: LIBOR+120BPS. STRUCTURED_NOTE_CPN_FORMULA is the column which has the
formulas ... what we need to do is transform these formulas into python codes."* That
description is exactly right, and the files confirm it: `data/mtge.xlsx` and `data/corp.xlsx`
carry, per security, a sequence of **(effective date, formula, day count, frequency)** periods.

``data/coupon_formula.csv`` is that sequence flattened to one row per security-period --
**1,411 rows over 1,227 securities**, 959 fixed and 451 floating. The xlsx stays the record; the
CSV is what a reader and this loader see, the same split as ``data/factor_history.csv``.

⭐⭐ A PARSER, NOT A MODEL, AND THE LINE IS LOAD-BEARING
-------------------------------------------------------
:func:`load_coupon_formulas` and :func:`rule_in_force` return a RULE -- multiplier, index name,
margin. They never produce a coupon. :func:`coupon_from_rule` is the only function that turns a
rule into a number, and it is the only one that can REFUSE. Keeping them apart matters because
a rule is cheap and sound while a coupon needs state this data does not carry:

* **each pool's own reset anniversary.** Measured 2026-10-14 on the 17 testable ARM pools: the
  formula reproduces the custodian's coupon only at the pool's OWN last reset, whose implied age
  runs 182 to 1,548 days with a median of 251, and no single lookback fits (the residual is
  non-monotonic in it, because the 1-year Treasury was). Five of the 17 imply a reset older than
  400 days -- hybrid ARMs still inside their initial fixed period.
* **the periodic and lifetime caps.** ``2370.000 * US0001M - 15405.000%`` is a real record and
  returns about **-14,220%** at the 2009 LIBOR of 0.50%.

⇒ for Tier 1 the custodian's observed coupon, held constant, is still the better input: it is
the actual reset-and-cap-constrained rate. ``docs/missing_data.md`` G7a/G7d carry the ask.

THE GRAMMARS, all five seen in the two files
--------------------------------------------
```
<rate>% Fixed                                    959 periods
<mult> * <INDEX> <+|-> <margin>%                 the pass-through / CMO form
<mult> * ( <INDEX> + <adj>% ) <+|-> <margin>%    the LIBOR -> Term SOFR transition; the adj is
                                                 folded in, so margin = mult*adj + margin
<INDEX> +<margin>%                               corporate: no multiplier, implicit 1.0
+<margin>%                                       1 period, index absent -- kept as `margin-only`
```

⚠️ Three traps, each of which cost a wrong first answer on 2026-10-14: an index name may START
WITH A DIGIT (``12MTA``); the margin may be NEGATIVE; and a ``-1.000`` multiplier is an inverse
floater, which is ordinary rather than exotic (285 of 451 float periods are |mult| = 1).

⭐ THE REFUSAL BAND IS MEASURED, NOT CHOSEN
------------------------------------------
Every coupon observed anywhere in this book -- the custodian's own net coupons and gross WACs
plus the 959 fixed records -- lies in **[0.0000, 9.3500]** percent (n = 1,983). So
:data:`COUPON_BAND_PCT` is ``(0.0, 20.0)``: more than twice the observed maximum, and zero at
the bottom because a coupon cannot be negative (a floored inverse floater pays nothing).
⚠️ The band is the test, NOT the multiplier: ``-4.000 * US0001M + 28.600%`` returns 26.6% at the
2009 index and is equally unusable, while sitting inside the continuous multiplier band
(|mult| runs continuously to 7.083 and then jumps to 44.8, 1,970.6 and 2,370).
"""
from __future__ import annotations

import csv
import datetime
import os

from pricer.errors import ContractTermsError

#: The plausible range for a coupon, in percent. MEASURED -- see the module docstring.
COUPON_BAND_PCT = (0.0, 20.0)

#: Bloomberg's frequency tokens, as they appear in the records.
PAYMENTS_PER_YEAR = {"MNT": 12, "SMA": 24, "QTL": 4, "S/A": 2, "ANN": 1}

#: The kinds a period's formula can take. An unrecognised one is REFUSED, never mapped.
RULE_KINDS = frozenset({"fixed", "float", "margin-only"})


class CouponRuleNotEvaluable(ContractTermsError):
    """A coupon rule cannot be turned into a usable coupon.

    Rooted at :class:`pricer.errors.ContractTermsError` and therefore NOT at ``ValueError``,
    because the spread solvers catch ``ValueError`` and a swallowed refusal comes back as "no
    spread reprices this security" -- a different and false statement. The same reasoning put
    :class:`~pricer.assets.securitized.observed.UnpublishableRiskMetric` where it is.
    """


def load_coupon_formulas(path: str = "data/coupon_formula.csv") -> dict:
    """Bloomberg's dated coupon rules, per security.

    Inputs
    ------
    1. path : str — the CSV. A missing file yields ``{}``; it is data, not a requirement.

    Returns ``{key: [period, ...]}`` keyed by CUSIP where one exists and otherwise by ISIN
    (the files carry XS and DE issues too — that is how the two EUR Resona tranches were
    resolved). Each period is a dict with ``period`` (1-based int), ``effective_date``
    (``datetime.date`` or None), ``kind``, ``multiplier`` (float or None), ``index`` (str or
    None), ``margin_pct`` (float), ``formula_raw``, ``day_count``, ``freq_token`` and
    ``payments_per_year`` (int or None). Periods come back sorted by ``period``.

    Raises ``ValueError`` on an unrecognised ``kind``, and on a repeated
    ``(security, period)`` — the builder collapses 18 exact duplicates and refuses any that
    disagree, so a duplicate reaching here means the table was edited by hand.
    """
    out: dict = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (row.get("cusip") or "").strip() or (row.get("isin") or "").strip()
            if not key:
                continue
            kind = (row.get("kind") or "").strip()
            if kind not in RULE_KINDS:
                raise ValueError("unrecognised coupon rule kind %r for %s; expected one of %s"
                                 % (kind, key, sorted(RULE_KINDS)))
            eff = (row.get("effective_date") or "").strip()
            mult = (row.get("multiplier") or "").strip()
            freq = (row.get("payments_per_year") or "").strip()
            period = int(float(row["period"]))
            rec = {
                "period": period,
                "effective_date": (datetime.date.fromisoformat(eff) if eff else None),
                "kind": kind,
                "multiplier": float(mult) if mult else None,
                "index": (row.get("index") or "").strip() or None,
                "margin_pct": float(row["margin_pct"]) if (row.get("margin_pct") or "").strip()
                else 0.0,
                "formula_raw": (row.get("formula_raw") or "").strip(),
                "day_count": (row.get("day_count") or "").strip(),
                "freq_token": (row.get("freq_token") or "").strip(),
                "payments_per_year": int(float(freq)) if freq else None,
            }
            bucket = out.setdefault(key, [])
            if any(p["period"] == period for p in bucket):
                raise ValueError("%s has two rows for period %d" % (key, period))
            bucket.append(rec)
    for periods in out.values():
        periods.sort(key=lambda p: p["period"])
    return out


def rule_in_force(periods, when: datetime.date):
    """The period governing the coupon on ``when``.

    Inputs
    ------
    1. periods : list — one security's periods, as :func:`load_coupon_formulas` returns them.
    2. when : datetime.date — the valuation date.

    Returns the period with the latest ``effective_date`` on or before ``when``, or ``None``
    when every period starts later. ⚠️ ``None`` is a real answer and is common in this book:
    at 2009-03-31 **every** fixed-to-float corporate hybrid was still in its first period, and
    a security whose only floating period begins in 2016 has no floating rule yet.
    """
    dated = [p for p in periods if p["effective_date"] is not None
             and p["effective_date"] <= when]
    return max(dated, key=lambda p: p["effective_date"]) if dated else None


def coupon_from_rule(rule, index_level_pct=None) -> float:
    """Turn ONE rule into a coupon, in percent — the only function here that produces a number.

    Inputs
    ------
    1. rule : dict — a period from :func:`load_coupon_formulas`.
    2. index_level_pct : float | None — the reference index, in percent, as of the reset the
       caller has decided on. Required for a ``float`` rule, ignored for a ``fixed`` one.

    Returns the coupon in percent.

    Raises :class:`CouponRuleNotEvaluable` when the rule cannot give a usable coupon: a
    ``float`` rule with no index level or no named index, a ``margin-only`` rule (its reference
    never came through), or **a result outside** :data:`COUPON_BAND_PCT`.

    ⚠️ The band is what stops a leveraged inverse floater publishing nonsense:
    ``2370.000 * US0001M - 15405.000%`` returns about -14,220% at a 0.50% index and must raise
    rather than return. ⚠️ And a refusal here does NOT mean the rule is wrong — it means the
    rule needs a cap, a floor or a reset date that this data does not carry.
    """
    kind = rule.get("kind")
    if kind == "fixed":
        value = float(rule["margin_pct"])
    elif kind == "margin-only":
        raise CouponRuleNotEvaluable(
            "the rule %r names no index, so its margin alone cannot give a coupon"
            % rule.get("formula_raw"))
    elif kind == "float":
        if not rule.get("index"):
            raise CouponRuleNotEvaluable("float rule %r names no index"
                                         % rule.get("formula_raw"))
        if index_level_pct is None:
            raise CouponRuleNotEvaluable(
                "rule %r needs a level for %s and none was supplied"
                % (rule.get("formula_raw"), rule["index"]))
        mult = rule["multiplier"]
        if mult is None:
            raise CouponRuleNotEvaluable("float rule %r has no multiplier"
                                         % rule.get("formula_raw"))
        value = mult * float(index_level_pct) + float(rule["margin_pct"])
    else:
        raise CouponRuleNotEvaluable("unrecognised rule kind %r" % kind)

    lo, hi = COUPON_BAND_PCT
    if not lo <= value <= hi:
        raise CouponRuleNotEvaluable(
            "%r gives %.4f%%, outside the measured band [%g, %g]%% — this rule needs a cap, a "
            "floor or a reset date that the source field does not carry"
            % (rule.get("formula_raw"), value, lo, hi))
    return value


def coupon_multiplier(formulas, keys, when: datetime.date):
    """How far the coupon moves per unit move in its index, or ``None``.

    Inputs
    ------
    1. formulas : dict — from :func:`load_coupon_formulas`.
    2. keys     : iterable of str — identifiers to try in order. The table is keyed by CUSIP
       where one exists and by ISIN otherwise, and a caller usually holds only one of them,
       so the candidates are tried rather than guessed.
    3. when     : datetime.date — the valuation date.

    Returns the ``multiplier`` of the rule in force: ``+1.0`` for an ordinary floater,
    ``-1.0`` or less for an inverse one, and a large number for a leveraged tranche.
    ``None`` means **unknown**, not one — no record, no period in force, a rule that names no
    index (so the coupon does not track a curve at all), or a rule with no multiplier.

    ⭐ The distinction matters more than it looks. Of the 64 Government-MBS floaters whose
    multiplier is known, **46 are inverse**: assuming ``+1`` for all of them moves the median
    rate duration from **+4.72 years to −0.005**, which is a different answer, not a rounding
    error. ⚠️ And ``None`` must not be defaulted to 1.0 by a caller — 97 of the 180 securitised
    floaters have no multiplier at all, and a rate sensitivity assumed for them would be
    indistinguishable in the output from one that was measured.
    """
    for key in keys:
        key = (key or "").strip()
        if not key or key not in formulas:
            continue
        rule = rule_in_force(formulas[key], when)
        if rule is None or not (rule.get("index") or ""):
            continue
        mult = rule.get("multiplier")
        return None if mult is None else float(mult)
    return None
