"""Build the Bloomberg request pack for the 2009-dated mortgage data.

    PYTHONPATH=src python scripts/make_bloomberg_request.py

Writes one folder, ``docs/bloomberg_request_<date>/``, which is what gets sent:

    00_README.txt                  what to run, in what order, and how to tell it worked
    01a_PILOT_cpr.csv              5 rows   -- run first
    01b_PILOT_factor.csv           3 rows   -- run first
    02_cpr_main_505.csv            505 pass-through + TBA, 3 fields x 2 dates
    03_factor_history_364.csv      344 tranches + 20 validation pools (a LIST, not formulas)
    04_cmo_terminal_questions.csv  3 securities x 5 questions, no formulas at all

⭐ TWO SEPARATE ASKS, and the second one is the important one.

**Ask 1 -- prepayment speeds (CPR) for the 505 we already price.** We have these fields;
they came back in July as of the pull date rather than as of 2009. ``BDP`` can only return
a current value, so this is the same request re-dated through ``BDH``.

**Ask 2 -- factor history for the 344 we do NOT price.** These are REMIC/CMO tranches and
IO/PO strips whose cash flows are set by each deal's waterfall, and until now the plan was
to wait for a deal-structure purchase (Intex or Bloomberg's CMO analytics). ⭐ That was
asking for the wrong thing:

    a waterfall's only job is to decide how much principal each tranche receives each
    month -- and the FACTOR FILE RECORDS THAT DECISION.

        principal(t) = orig_face x (factor(t-1) - factor(t))
        interest(t)  = orig_face x factor(t-1) x coupon(t) / 12

⭐ That is the complete cash flow vector, and it needs no knowledge of the structure at
all. It is also **structure-agnostic**: a PO has no coupon term, an IO has no principal
term, and a Z accrual falls out with no special case -- during accrual the interest term
and the (negative) principal term are equal and opposite, so the net cash flow is exactly
zero, which is what a Z does. Verified arithmetically before this file was written.

⭐ And because we are valuing at 2009-03-31, most of that vector is ALREADY OBSERVED. 89 of
the 344 have paid off entirely -- their realised cash flow is complete, with no tail
assumption whatsoever. The 255 survivors have a median 6.7 years left today against the 17
years since the valuation date, so the observed window dominates and the short tail is
handled by the same CPR grid the pools already use.

⚠️ THE HONEST LIMIT, which must travel with every number this produces: a realised path is
**hindsight**. It yields the discount rate the holder actually earned, not the spread the
market demanded in March 2009. For *risk* metrics -- spread duration, DV01, convexity -- a
cash flow vector is a cash flow vector and the numbers are well defined, on exactly the
same footing as the pools' fixed-CPR numbers. For "what was this worth to the market that
morning", it is not the answer, and that still needs the deal structure.

⭐ THE PILOTS EXIST BECAUSE OF WHAT WENT WRONG LAST TIME. The July pull came back complete
and unusable -- every value as of the pull date, and one of eight field names that did not
exist. Both were visible in the first row and neither was noticed until all 882 had been
pulled. Eight rows cost a couple of minutes and would have caught both.

⚠️ NO INVENTED MNEMONICS. ``MTG_HIST_COLLAT_CPR_LIFE`` was our guess in July and returned
Invalid Field on all 882. Where we are unsure, the sheet asks a question instead, and where
a candidate name is used it is labelled as one.
"""
from __future__ import annotations

import csv
import pathlib

import pandas as pd

OUT = pathlib.Path("outputs")
PACK = pathlib.Path("docs/bloomberg_request_2026-09-29")
RISK = OUT / "pool_risk_2009-03-31.csv"
CHECK = OUT / "mbs_data_check_2026-07-30.csv"

#: The two valuation dates the drivers run. Written YYYYMMDD so no spreadsheet locale can
#: read 3/31 as the 3rd of an unrelated month.
DATES = (("20090331", "baseline"), ("20090610", "control"))

CPR_FIELDS = ("MTG_GEN_CPR_3M", "MTG_GEN_CPR_6M", "MTG_GEN_CPR_12M")

#: Hide the date column and hold each answer to one cell, so 505 rows stay a table.
#: ⚠️ Unverified at a terminal -- one of the things the pilot is for.
BDH_OPTS = '"Dts=H","cols=1;rows=1"'

#: ⚠️ A CANDIDATE, not a known-good name. The pilot's question column asks for FLDS to
#: confirm it. Unlike a cash-flow projection, a factor is a published monthly fact with a
#: date, which is the category BDH is built for -- that part we are confident about; the
#: spelling is what we are not.
FACTOR_FIELD = "MTG_FACTOR"
COUPON_FIELD = "CPN"

TRANCHES = ("remic-tranche", "cmo-tranche", "io-strip", "po-strip")


def _bdh(cell: str, field: str, start: str, end: str, opts: str = BDH_OPTS) -> str:
    return f'=BDH({cell},"{field}","{start}","{end}",{opts})'


def _column_letter(index0: int) -> str:
    """0 -> A. Only ever asked about the first 26 here, but written honestly."""
    letters, n = "", index0
    while True:
        letters = chr(ord("A") + n % 26) + letters
        n = n // 26 - 1
        if n < 0:
            return letters


def verify(path: pathlib.Path) -> int:
    """Reopen what was written and check the formulas point where they claim to.

    ⭐ This exists because the first draft got it wrong in a way nothing would have caught.
    The pilot's headers were named ``D_today_BDP`` … ``G_no_layout_opts`` while ``security``
    sat in column D, so every one of those names was off by one and the covering note
    described the wrong cells. A colleague would have found it at the terminal, which is the
    most expensive place to find anything.

    The cell reference is the part that actually breaks: ``$D2`` has to be the ticker for
    that row and no other. Point it one column left and it reads a structure label; point it
    one row up and every security silently gets its neighbour's number -- a spreadsheet full
    of plausible values for the wrong bonds.
    """
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], rows[1:]
    tick_col = header.index("security")
    tick_letter = _column_letter(tick_col)

    for r, row in enumerate(body, start=2):          # start=2: row 1 is the header
        assert row[tick_col].endswith(" Mtge"), f"{path.name} row {r}: not a Mtge ticker"
        for c, cell in enumerate(row):
            if not cell.startswith("="):
                continue
            want = f"(${tick_letter}{r},"
            assert want in cell, (
                f"{path.name} row {r} col {_column_letter(c)}: formula references "
                f"{cell[cell.index('(') : cell.index(',')]} but this row's ticker "
                f"is in {want[1:-1]}")

    # A header whose letter prefix disagrees with where the column actually sits is the
    # exact defect above, so it is checked rather than trusted.
    for c, name in enumerate(header):
        if len(name) > 1 and name[1] == "_" and name[0].isupper():
            assert name[0] == _column_letter(c), (
                f"{path.name}: header {name!r} sits in column {_column_letter(c)}")
    return len(body)


def _write(name: str, header, rows, check=True) -> pathlib.Path:
    path = PACK / name
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    if check:
        assert verify(path) == len(rows)
    return path


# --------------------------------------------------------------------------- data

def load() -> pd.DataFrame:
    """The priced book, the unpriced tranches, and what July returned for each."""
    import os
    import sys
    sys.path[:0] = ["src", "scripts"]
    os.environ.setdefault("FIP_DATA_DIR", "data")
    import pool_risk as D
    from dataio.phase2 import build_pool_universe, load_master_phase2

    master = load_master_phase2(D.WB)
    u, _, _ = build_pool_universe(master, D.load_pool_terms(), valuation_date=D.VAL_DATE)
    gold = (master.groupby("asset_id")
            .agg(mv=("gold_mkt_value", "sum"), par=("par_value", "sum"),
                 factor=("paydown_factor", "max"), coupon=("income_rate", "max"))
            .reset_index())
    chk = pd.read_csv(CHECK)
    u = (u.merge(gold, on="asset_id", how="left")
          .merge(chk[["asset_id", "cusip", "pool_alive_at_pull", "cpr_12m_at_pull_pct"]],
                 on="asset_id", how="left"))
    missing = u["cusip"].isna().sum()
    if missing:
        raise SystemExit(f"{missing} securities have no cusip in {CHECK}")
    u["security"] = u["cusip"].astype(str) + " Mtge"
    return u.sort_values("cusip")


# --------------------------------------------------------------------------- ask 1: CPR

def write_cpr(u: pd.DataFrame) -> int:
    # ⚠️ The population is the driver's OUTPUT, not the universe's routing. Routing gives
    # 519 candidates and the driver prices 505 -- the 14 are all named in the disposition
    # sidecar (12 ARM pools whose pulled WAC has reset since 2009, 2 TBAs whose description
    # never states a settle month), and a prepayment speed unblocks none of them. Asking
    # for CPR on a security that is stuck on something else would just be noise in a
    # colleague's spreadsheet.
    priced = set(pd.read_csv(RISK)["asset_id"])
    d = u[u["route"].isin(("pool", "tba-forward")) & u["asset_id"].isin(priced)]
    assert len(d) == len(priced), f"{len(d)} matched against {len(priced)} priced"

    header = ["cusip", "asset_id", "structure", "security"]
    for stamp, _ in DATES:
        header += [f"{f}_{stamp}" for f in CPR_FIELDS]
    rows = []
    for i, (_, r) in enumerate(d.iterrows(), start=2):
        cell = f"$D{i}"
        row = [r["cusip"], r["asset_id"], r["structure"], r["security"]]
        for stamp, _ in DATES:
            row += [_bdh(cell, f, stamp, stamp) for f in CPR_FIELDS]
        rows.append(row)
    p = _write("02_cpr_main_505.csv", header, rows)
    print(f"   {p.name:32s} {len(rows)} securities x {len(CPR_FIELDS)} fields x "
          f"{len(DATES)} dates = {len(rows)*len(CPR_FIELDS)*len(DATES):,} points")
    return len(rows)


def write_cpr_pilot(u: pd.DataFrame) -> int:
    """⭐ Stratified, not sampled -- each row answers a different question.

    The strata come from what the July pull actually returned for these same securities:
    486 of the 505 came back with a value, so the identifiers resolve and the field name is
    real. Neither is what this tests. The open question is whether BDH applies the DATE.

    ⚠️ 215 of the 221 pools that have already PAID OFF still return a CPR today --
    Bloomberg freezes the last value rather than blanking it, exactly as it freezes WALA.
    A frozen number is indistinguishable from a live one, which is why row 2 is here.
    """
    d = u[u["route"].isin(("pool", "tba-forward"))]
    has = d["cpr_12m_at_pull_pct"].notna()
    live = d["pool_alive_at_pull"].eq("yes")
    pool = d["route"].eq("pool")
    tba = d["route"].eq("tba-forward")

    strata = [
        (pool & live & has,
         "LIVE pool with a value today. E is a genuine 2026 speed; 2009 was a refi wave, "
         "so E and F must differ by a lot. If they match, the date did not apply."),
        (pool & ~live & has,
         "PAID-OFF pool -- E is FROZEN at whenever it died and looks like a live number. "
         "If F differs from E, the date reached back past the payoff: the strongest single "
         "confirmation on this sheet."),
        (pool & live & ~has,
         "LIVE pool with NO value today (5 of these, all ARM-like). Does the history hold "
         "what the current field does not?"),
        (tba & has,
         "TBA generic that answered in July -- confirms a generic carries a cohort speed."),
        (tba & ~has,
         "TBA generic that did NOT answer in July. If it stays empty we price the 27 TBAs "
         "off the cohort grid, which is already built -- so an empty answer costs us "
         "nothing and is still worth knowing."),
    ]
    rows = []
    for i, (mask, why) in enumerate(strata, start=2):
        sel = d[mask]
        if sel.empty:
            raise SystemExit(f"cpr pilot stratum {i-1} is empty")
        r = sel.iloc[0]
        cell = f"$D{i}"
        rows.append([
            r["cusip"], r["asset_id"], r["route"], r["security"],
            f'=BDP({cell},"MTG_GEN_CPR_3M")',
            _bdh(cell, "MTG_GEN_CPR_3M", "20090331", "20090331"),
            _bdh(cell, "MTG_GEN_CPR_3M", "20090301", "20090331"),
            f'=BDH({cell},"MTG_GEN_CPR_3M","20090331","20090331")',
            why,
        ])
    p = _write("01a_PILOT_cpr.csv",
               ["cusip", "asset_id", "route", "security",
                "E_value_today_BDP", "F_single_day_BDH", "G_whole_month_BDH",
                "H_no_layout_options", "why_this_row_is_here"], rows)
    print(f"   {p.name:32s} {len(rows)} rows, 4 ways of asking")
    return len(rows)


# --------------------------------------------------------------------- ask 2: factors

def write_factor_pilot(u: pd.DataFrame) -> int:
    """Three rows: a dead tranche, a live tranche, and a pool we already price.

    ⭐ The pool row is the validation seed. Our engine already has an answer for it, so the
    factor method can be checked against a number we trust BEFORE it is ever applied to a
    tranche -- the Gate-0 pattern, moved to the front where it belongs.

    A four-month window, not seventeen years: enough to show the layout and prove the field
    is history-enabled, small enough to run in seconds.
    """
    tr = u[u["structure"].isin(TRANCHES)]
    picks = [
        (tr[tr["pool_alive_at_pull"].eq("no")].sort_values("mv", ascending=False),
         "PAID-OFF tranche. Its realised cash flow is COMPLETE -- if the factor series "
         "runs to zero we can price this bond with no assumption of any kind."),
        (tr[tr["pool_alive_at_pull"].eq("yes")].sort_values("mv", ascending=False),
         "LIVE tranche. Realised 2009-today plus a short tail we handle with the same CPR "
         "grid the pools use."),
        (u[u["structure"].eq("pass-through")].sort_values("mv", ascending=False),
         "VALIDATION: a plain pool our engine ALREADY prices. If the factor method "
         "reproduces our own number here, the method is proven before we point it at a "
         "tranche. This row is the reason to trust the other two."),
    ]
    rows = []
    for i, (sel, why) in enumerate(picks, start=2):
        if sel.empty:
            raise SystemExit("factor pilot stratum empty")
        r = sel.iloc[0]
        cell = f"$D{i}"
        rows.append([
            r["cusip"], r["asset_id"], r["structure"], r["security"],
            f'=BDP({cell},"{FACTOR_FIELD}")',
            _bdh(cell, FACTOR_FIELD, "20090301", "20090630", '"Dts=H"'),
            _bdh(cell, COUPON_FIELD, "20090301", "20090630", '"Dts=H"'),
            why,
        ])
    p = _write("01b_PILOT_factor.csv",
               ["cusip", "asset_id", "structure", "security",
                "E_factor_today_BDP", "F_factor_4month_series", "G_coupon_4month_series",
                "why_this_row_is_here"], rows)
    print(f"   {p.name:32s} {len(rows)} rows, factor + coupon history")
    return len(rows)


def write_factor_list(u: pd.DataFrame) -> int:
    """A security LIST, not a formula sheet -- the precedent is govt_mtge_cusips.csv.

    ⚠️ Deliberate. A factor request returns a TIME SERIES per security, and 364 of those
    cannot be laid out on one row each. How to arrange them is a decision to make at the
    terminal once the pilot has shown what one series looks like, so pretending to know
    here would just be a layout somebody has to undo.
    """
    tr = u[u["structure"].isin(TRANCHES)].copy()
    # ⚠️ `group` already exists in the universe (an asset-class field). A second column of
    # that name would be silently ambiguous, so this one says what it is.
    tr["request_group"] = "tranche-unpriced"
    tr["why"] = "cash flows need the deal waterfall; the factor path replaces it"

    pools = u[u["structure"].eq("pass-through")].sort_values("mv", ascending=False).head(20).copy()
    pools["request_group"] = "validation-pool"
    pools["why"] = ("our engine already prices this one -- used to check the factor method "
                    "against a number we trust")

    d = pd.concat([tr, pools])
    rows = [[r["cusip"], r["asset_id"], r["security"], r["request_group"], r["structure"],
             f"{(r['mv'] or 0)/1e6:.2f}",
             "yes" if r["pool_alive_at_pull"] == "no" else "no",
             r["why"]]
            for _, r in d.iterrows()]
    p = _write("03_factor_history_364.csv",
               ["cusip", "asset_id", "security", "request_group", "structure", "mv_musd",
                "already_paid_off", "why_we_need_it"], rows, check=False)
    dead = sum(1 for r in rows if r[6] == "yes")
    print(f"   {p.name:32s} {len(rows)} securities "
          f"({len(tr)} tranches + {len(pools)} validation pools; {dead} already paid off)")
    return len(rows)


# --------------------------------------------------------------- ask 2b: the fallback

PROBE = (
    ("31396XJY1", "TNTD03416170", "largest tranche position, $15.7M",
     "FEDERAL NATIONAL MORTGAGE ASSOC 6% CMO"),
    ("31396XDP6", "TNTD03415261", "largest PO strip, $5.0M",
     "FNMA REMIC SER 2007-80 CL WO 25 AUG 2037"),
    ("31392PPG4", "TNTD03131620", "a Z accrual tranche, $3.9M -- the hardest case",
     "FHLMC SER 2460 CL VZ 6.0% 15 NOV 2029"),
)

PROBE_QUESTIONS = (
    ("Q1_is_the_factor_field_history_enabled",
     "THE ONE THAT MATTERS MOST. FLDS on this security -- is there a factor field, and does "
     "it carry history back to 2009? Please paste the exact field name. A factor is a "
     "published monthly fact, so this should be the easy one."),
    ("Q2_can_a_projection_be_dated_to_2009",
     "Can a cash flow projection be run AS OF 2009-03-31, or only forward from today? We "
     "expect 'only forward' -- a projection is computed off today's collateral. A clear no "
     "is a useful answer and closes the question."),
    ("Q3_is_there_a_cash_flow_table",
     "Does the terminal show a projected cash flow table for THIS tranche (date, interest, "
     "principal), and can it be exported to Excel?"),
    ("Q4_what_cmo_fields_exist",
     "Any other CMO-specific fields worth knowing about (tranche type, deal name, PAC "
     "bands, original tranche amount)? Exact names please -- we are deliberately not "
     "guessing them."),
    ("Q5_what_does_DES_call_it",
     "What does DES call the tranche type? Our guess from the description text is "
     "unreliable: of the 54 tranches whose class letter starts with P, 29 are PRINCIPAL "
     "ONLY strips rather than PACs."),
)


def write_probe() -> int:
    rows = [[c, a, f"{c} Mtge", why, desc, qn, qt, ""]
            for c, a, why, desc in PROBE for qn, qt in PROBE_QUESTIONS]
    p = _write("04_cmo_terminal_questions.csv",
               ["cusip", "asset_id", "security", "why_this_one", "description",
                "question", "what_it_settles", "answer_here"], rows, check=False)
    print(f"   {p.name:32s} {len(PROBE)} securities x {len(PROBE_QUESTIONS)} questions")
    return len(rows)


# --------------------------------------------------------------------------- readme

README = """\
Bloomberg 数据请求 - 2026-09-29
================================================================

一共两件事,第二件是这次真正重要的。

先跑 01a 和 01b 这两个小表(加起来 8 行,几分钟),把结果发回来。
确认没问题之后再跑 02 和 03。04 是附带的几个问题,看到了顺手回答就好。


为什么要先跑小表
----------------------------------------------------------------
七月那次拉回来的数据是"完整但不能用"的:所有值都是拉取当天的,不是
我们估值的 2009 年;另外八个字段里有一个名字是我们写错的。这两个问题
在第一行就能看出来,但当时 882 只全拉完才发现。

所以这次先花两分钟。


================================================================
第一件事:提前还款速度 CPR (01a -> 02)
================================================================

这部分我们已经有了,只是日期不对。BDP 只能返回"今天的值",要拿到
2009 年的值必须用 BDH。所以是同一批证券、同一个字段,换个日期。

02_cpr_main_505.csv   505 只 x 3 个字段 x 2 个日期 = 3030 个数据点
                      (七月那次是 7056,这次少了 57%)

字段:MTG_GEN_CPR_3M / 6M / 12M
日期:2009-03-31(主日期)和 2009-06-10(对照日期)

** 一眼判断对错的办法 **
这批 pool 现在的 CPR 大约 8%(很集中,7-12)。但 2009 年它们平均
in the money 1.53 个百分点,正赶上再融资潮,速度应该是现在的好几倍,
大概 20-40%。

>>> 如果 2009 那一列也读出 8% 左右,就说明日期没生效。

01a 的五行每行测的东西都不一样,表里 why_this_row_is_here 那列写了。
其中第二行是一只**已经还清**的 pool - Bloomberg 对还清的 pool 不是
留空,而是把最后一个值冻住,看上去和活的一模一样。这行如果能返回
2009 的值,最能说明日期真的生效了。


================================================================
第二件事:历史 factor (01b -> 03)  <- 这次的重点
================================================================

我们有 344 只 REMIC / CMO / IO / PO 的 tranche 一直定不了价,因为它们
的现金流由每个 deal 自己的 waterfall 决定。之前我们以为只能等着买
deal structure 数据(Intex,或者 Bloomberg 的 CMO 分析模块)。

后来想明白了,我们要的东西不对。

  waterfall 唯一的工作,就是决定每个月每一层 tranche 分到多少本金。
  而 factor 文件把这个决定记录下来了。

    本金(t) = 原始面额 x (factor(t-1) - factor(t))
    利息(t) = 原始面额 x factor(t-1) x 票息(t) / 12

这就是完整的现金流,完全不需要知道 deal 的结构。而且它对任何结构都
成立:PO 没有利息项,IO 没有本金项,Z accrual 更妙 - 计息期内利息项
和(负的)本金项正好相等相反,净现金流精确为零,正是 Z 的行为,不需要
任何特殊处理。

关键是:我们估的是 2009-03-31,十七年前。这些现金流大部分**已经发生
过了**。344 只里有 89 只已经完全还清,它们的现金流是完整的,不需要
任何假设。剩下 255 只今天还有中位数 6.7 年,相对已经观察到的 17 年
来说尾巴很短,而且可以用我们给 pool 用的那套 CPR 假设处理。

** 为什么这个请求比上一个容易 **
factor 是每月公布的**事实**,带日期的,本来就是 BDH 该干的事。
和"把一个现金流预测倒回 2009"完全不是一个难度 - 后者是用今天的
抵押品状态算出来的,倒不回去。

03_factor_history_364.csv 是一份**清单**,不是公式表。因为 factor 是
时间序列,一只证券一行放不下,怎么排版等 01b 跑出来看过再定 - 我们
先猜一个反而要你返工。

清单里 344 只 tranche + 20 只 pool。那 20 只 pool 是**验证用的**:
我们自己的引擎已经能算它们,如果 factor 方法能重现我们自己的数字,
这个方法就在用到 tranche 之前先被证明了。

01b 里我们填的字段名 MTG_FACTOR 是**猜的**,不确定。麻烦用 FLDS 看
一下真实的名字,不对的话我们改一个字就行 - 七月那个 Invalid Field
就是我们乱猜字段名造成的,不想再来一次。


================================================================
不用麻烦你的两件事(说明一下,免得你以为我们漏了)
================================================================

** WAC 不用重拉 **
七月的 WAC 是 2026 年的值。对固定利率的 pool 来说无所谓 - 我们量过,
WAC 差 0.5 个百分点,算出来的 spread 才动 0.24bp(最差 0.87bp)。

但有 12 只 ARM(浮动利率)pool 不一样:它们的 WAC 不是"漂移",是
**重置**过了,最多差了 3.9 个百分点(2026 年拉到 2.875%,2009 年
实际是 6.756%)。这 12 只现在因为这个定不了价。

不过这个我们自己能解决 - 2009 年的净票息本来就在托管方的文件里,
加上我们已经在用的 0.5% servicing 就是当年的 WAC,误差大概 0.12bp。
所以不用麻烦你。

** MTG_HIST_COLLAT_CPR_LIFE 也不要了 **
七月那个返回 Invalid Field 的字段,是我们自己写错了名字,不是数据
缺口,这次不重复了。


================================================================
04_cmo_terminal_questions.csv  (附带,看到顺手回答)
================================================================

3 只证券 x 5 个问题,不是公式,是想请你在终端上看一眼告诉我们。
Q1 最重要(factor 字段到底叫什么、有没有历史)。
其余几个是备选路线,答不上来完全没关系。


================================================================
最后
================================================================

哪一格实在没有数据,留空就好,不要补 - 看得见的缺口比看不见的错数
便宜得多,每一个我们都有备用方案。

格式不好跑(想一次一个日期、想拆小一点、想换排版),说一声,这些
文件我们一条命令就能重新生成。

非常感谢 🙏
"""


def main():
    PACK.mkdir(parents=True, exist_ok=True)
    u = load()
    print(f"building {PACK}/")
    write_cpr_pilot(u)
    write_factor_pilot(u)
    write_cpr(u)
    write_factor_list(u)
    write_probe()
    (PACK / "00_README.txt").write_text(README, encoding="utf-8-sig")
    print(f"   {'00_README.txt':32s} written")
    print("\n   !! Send the two PILOT sheets first -- 8 rows, a couple of minutes.")
    print("   The July pull came back complete and unusable, and both reasons were")
    print("   visible in its first row.")


if __name__ == "__main__":
    main()
