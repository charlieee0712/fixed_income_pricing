"""Build the presenter's Word document for slides 6-9 of the investor deck.

Two things in one file, deliberately in two languages:

  * the WALKTHROUGH, in Chinese -- what each slide means, what every number on it is, and
    the finance concept underneath it, written for someone who has to understand it rather
    than recognise it. This exists because the presenter said twice that he could no longer
    follow his own bullets.
  * the SCRIPT, in English -- the actual words, because that is what gets said in the room.

Every figure here was read from a live run on 2026-09-22, not from memory, and the sources
are listed on the last page. Regenerate with:

    python scripts/make_presenter_notes.py --output "docs/Presenter Notes v6.docx"

Needs ``python-docx``. Like ``make_investor_deck.py`` and ``md_to_pdf.py`` this is document
tooling, so it is deliberately NOT in requirements.txt.
"""
from __future__ import annotations

import argparse
import pathlib

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

INK = RGBColor(0x1F, 0x4E, 0x79)      # headings
SAY = RGBColor(0x0B, 0x3D, 0x62)      # the words actually spoken
WARN = RGBColor(0xA6, 0x3A, 0x00)     # things that would cost you if said wrong
QUIET = RGBColor(0x5A, 0x5A, 0x5A)
CJK = "Microsoft YaHei"
LATIN = "Calibri"


def _font(run, size, colour=None, bold=False, italic=False, latin=LATIN):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = latin
    if colour is not None:
        run.font.color.rgb = colour
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), CJK)


def _p(doc, text="", size=10.5, colour=None, bold=False, italic=False,
       indent=0.0, before=2, after=4, latin=LATIN):
    """One paragraph. ``**bold**`` inside the text becomes bold runs."""
    para = doc.add_paragraph()
    para.paragraph_format.left_indent = Inches(indent)
    para.paragraph_format.space_before = Pt(before)
    para.paragraph_format.space_after = Pt(after)
    for i, chunk in enumerate(str(text).split("**")):
        if chunk:
            _font(para.add_run(chunk), size, colour, bold or (i % 2 == 1), italic, latin)
    return para


def h1(doc, text):
    doc.add_page_break()
    _p(doc, text, 18, INK, bold=True, before=0, after=10)


def h2(doc, text):
    _p(doc, text, 13.5, INK, bold=True, before=14, after=5)


def h3(doc, text):
    _p(doc, text, 11.5, INK, bold=True, before=10, after=3)


def body(doc, text, indent=0.0):
    _p(doc, text, 10.5, None, indent=indent)


def bullet(doc, text, indent=0.25):
    _p(doc, "•  " + text, 10.5, None, indent=indent, before=1, after=3)


def say(doc, text):
    """A line to be spoken aloud, set apart so it is findable while standing up."""
    _p(doc, text, 11.5, SAY, indent=0.28, before=5, after=5)


def warn(doc, text):
    _p(doc, "⚠  " + text, 10, WARN, indent=0.1, before=5, after=5)


def star(doc, text):
    _p(doc, "⭐  " + text, 10.5, None, bold=False, indent=0.1, before=5, after=5)


def table(doc, rows, widths=None, header=True):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    for r_i, row in enumerate(rows):
        cells = t.add_row().cells
        for c_i, val in enumerate(row):
            cells[c_i].text = ""
            para = cells[c_i].paragraphs[0]
            para.paragraph_format.space_before = Pt(2)
            para.paragraph_format.space_after = Pt(2)
            for i, chunk in enumerate(str(val).split("**")):
                if chunk:
                    _font(para.add_run(chunk), 9.5,
                          INK if (header and r_i == 0) else None,
                          (header and r_i == 0) or (i % 2 == 1))
    if widths:
        for row in t.rows:
            for c_i, w in enumerate(widths):
                row.cells[c_i].width = Inches(w)
    _p(doc, "", 4, after=0)
    return t


# ----------------------------------------------------------------------------------------

def build(out: pathlib.Path) -> pathlib.Path:
    doc = Document()
    s = doc.sections[0]
    s.left_margin = s.right_margin = Inches(0.85)
    s.top_margin = s.bottom_margin = Inches(0.75)
    normal = doc.styles["Normal"]
    normal.font.name = LATIN
    normal.font.size = Pt(10.5)

    # ---------------------------------------------------------------- cover
    _p(doc, "投资人汇报 · 你要讲的四页",
       22, INK, bold=True, before=0, after=2)
    _p(doc, "Slides 6–9 — 逐页讲解与逐字讲稿",
       14, QUIET, after=12)
    table(doc, [
        ["场合", "Ryse 项目进度汇报 · 高盛投资人"],
        ["分工", "Liping 讲 slides 2–5，你讲 **6–9**"],
        ["你的时长", "约 **9 分钟** + Q&A"],
        ["对应文件", "docs/Ryse Presentation v6.pptx"],
        ["数字来源", "2026-09-22 实跑输出；最后一页列了每个数的出处"],
    ], widths=[1.2, 5.6], header=False)

    h2(doc, "这份文档怎么用")
    bullet(doc, "**第一部分（讲解）** — 今晚看。中文，"
                "把每页的每个数字和背后的概念拆开，"
                "目标是你合上稿子也能讲。")
    bullet(doc, "**第二部分（讲稿）** — 明天照着讲。"
                "英文原话，**蓝色缩进的就是要说出口的那句**，"
                "黑字是给你自己的提示。")
    bullet(doc, "**第三部分（Q&A）** — 高盛的人真会问的问题，"
                "包括最锋利的那个。")
    bullet(doc, "**第四部分** — 如果有人问“最难的是什么”，"
                "三个可以讲的真实故事。")
    bullet(doc, "**最后一页** — 数字速查，可以打印出来拿在手上。")

    warn(doc, "全文只有一件事你必须先确认："
              "**Liping 说给你的 MBS 数据到了没有。** "
              "讲稿里只说“七月已经请求了”（这是事实），"
              "**不要说“至今未到”**——万一已经到了，"
              "这句话会把整场的可信度都拖下水。")

    # ---------------------------------------------------------------- concepts
    h1(doc, "零 · 先把八个词弄懂")
    body(doc, "这八个词支撑你要讲的四页。弄懂了，"
              "后面所有内容都是顺的。")

    table(doc, [
        ["词", "大白话"],
        ["**债券** bond",
         "一张借条。发行人借钱，定期付利息（coupon），"
         "到期还本金。按 **100** 报价：价格 90 = 打九折。"],
        ["**收益率曲线** yield curve",
         "政府在不同期限上借钱的成本（1年 0.5%、10年 3%…）。"
         "它是所有定价的基准线。"],
        ["**利差** spread",
         "⭐ 核心。市场要求这个借款人比本国政府多给多少补偿。"
         "单位 bp（1bp = 0.01%）。**这是我们系统的主要输出。**"],
        ["**久期** duration",
         "利率变动 1%，价格变动百分之几。久期 5 = 利率涨 1%，"
         "价格跌约 5%。单位是“年”。"],
        ["**托管行** custodian",
         "替养老金保管证券、记官方账的银行。"
         "它也会自己算一套数 —— slide 8 第二个检查就靠它。"],
        ["**可赎回债** callable",
         "发行人可以提前还钱。难在要算那个“提前还款权”值多少，"
         "需要一棵利率树。"],
        ["**通胀挂钩债** TIPS",
         "本金随通胀调整。那个调整系数叫 **index ratio** —— "
         "slide 8 第三个检查重算的就是它。"],
        ["**池化产品** MBS / CMO / ABS / CMBS",
         "一堆贷款打包成证券。房贷包 = MBS，再切成不同风险档 = CMO，"
         "车贷/卡贷 = ABS，商业地产贷 = CMBS。"
         "难在借款人可以提前还款，得建预测模型。"],
    ], widths=[1.55, 5.25])

    h3(doc, "⭐ 最重要的一件事：我们的流程是怎么跑的")
    body(doc, "输入三样东西：（a）债券条款、（b）那天的"
              "政府利率曲线、（c）**托管行记录的价格**。"
              "然后解出一个 spread，让模型算出的价格等于"
              "托管行那个价。最后在校准好的模型上算风险指标。")
    star(doc, "所以记住：**价格是输入，不是输出。** "
              "这一句是 slide 8 存在的理由，也是 Q&A 里"
              "最锋利那个问题的答案基础。你必须能"
              "随时说出这句话。")

    # ================================================================ PART 1
    h1(doc, "一 · 逐页讲解")

    # ---- slide 6
    h2(doc, "Slide 6 — Coverage（覆盖范围）")
    body(doc, "**一句话：** 这本账有 2,260 只证券；"
              "949 只所在的六大类做完了，882 只的引擎建好了在等数据，"
              "429 只还没开始。")

    h3(doc, "屏幕上那条横条")
    table(doc, [
        ["颜色", "标签", "数", "意思"],
        ["深蓝", "Complete", "**949**", "六个债券大类，引擎建好并在跑"],
        ["橙", "Engine built — next", "**882**",
         "政府房贷类。引擎已建并测过，缺的是数据"],
        ["灰", "Not yet built", "**429**",
         "三类池化产品 412 + 期货期权 16 + 基金份额 1"],
    ], widths=[0.7, 1.9, 0.7, 3.5])

    h3(doc, "两个 bullet 分别在说什么")
    bullet(doc, "**“13 类里 6 类完成 — 42%”** —— 949 ÷ 2,260 = 42.0%。")
    bullet(doc, "**“949 里 766 有我们自己算的价，剩下 183 "
                "逐只列名”** —— 这句是这页最容易被误读的地方。")

    star(doc, "**“Complete” 不等于每只债都有数字。** "
              "它的意思是这一类的引擎建好了、跑通了。"
              "949 里有 183 只没有我们的价 —— "
              "**不是算不出来，是它们的条款在给我们的"
              "原始文件里就不存在**。")
    body(doc, "这件事要讲成优点，不是道歉。一个"
              "准备用在任意组合上的工具，**必须能说出"
              "它算不了什么，而不是猜一个数糊弄过去**。"
              "183 只里的每一只都在一张登记表里有名有姓有原因。"
              "真实的账就是会有不完整的记录。")

    h3(doc, "投资人会怎么听这页")
    body(doc, "他们关心的是“进度到哪了、还要多久”。"
              "42% 听起来一般，但**真正的信息是剩下那 1,311 "
              "只里有 882 只（即 67%）不卡在我们这边**。"
              "这才是这页要传达的东西。")

    # ---- slide 7
    h2(doc, "Slide 7 — 十三类（那张表）")
    body(doc, "**一句话：** 把整本账摊开，一类不漏，"
              "行数和证券数都对得上。")

    h3(doc, "为什么两列数不一样")
    body(doc, "2,366 **行** vs 2,260 **只证券**。同一只债被两个"
              "基金经理分别持有，就会出现两行。"
              "我们按证券去重来算。**行数和客户自己"
              "那张表完全对得上，2,366。**")
    warn(doc, "这一点值得主动说一句。一个做过账的"
              "人一眼就会注意到两个总数不一样，"
              "你先解释比被问好。")

    h3(doc, "十三类分别是什么")
    table(doc, [
        ["#", "类别", "证券", "大白话"],
        ["1", "Corporate Bonds", "732", "公司借钱"],
        ["2", "Government Bonds", "147", "主权国借钱"],
        ["3", "Government Agencies", "39", "房利美这类准政府机构"],
        ["4", "Index-Linked Government", "15", "本金随通胀调整的国债"],
        ["5", "Guaranteed Fixed Income", "9",
         "有政府担保的（这批全是 FDIC 危机期担保的银行债）"],
        ["6", "Municipal / Provincial", "7", "州、市、省借钱"],
        ["7", "Government Mortgage-Backed", "**882**",
         "一堆有政府担保的房贷打包 —— **剩下最大的一块**"],
        ["8", "Non-Government C.M.O.s", "264", "房贷包再切档，没政府担保"],
        ["9", "Asset-Backed Securities", "79", "车贷、卡贷这类打包"],
        ["10", "Commercial Mortgage-Backed", "69", "商业地产抵押贷打包"],
        ["11–12", "FI Derivatives — Futures / Options", "7 / 9",
         "**不是债券**，需要我们还没设计过的机器"],
        ["13", "Other Fixed Income", "1",
         "一个基金份额：无 ISIN、无到期日、无评级"],
    ], widths=[0.5, 2.3, 0.7, 3.3])

    h3(doc, "最后三行怎么讲")
    star(doc, "期货期权算“还没做”，不是“不做”。"
              "它们才 16 只（732 对比 2,260），而且是剩下"
              "唯一需要全新机器的一类。最后一行是"
              "基金份额，债券模型对它无从下手。")
    warn(doc, "**这是全场唯一一处 deck 和项目记录不一致的"
              "地方。** 项目文档里期货期权仍标为"
              "“out of scope”，deck 里改成了“Scoped”（Liping "
              "的意思）。如果 Mario 当场问起，就照实说："
              "标的是“not yet built”，这句话不承诺任何东西。")

    # ---- slide 8
    h2(doc, "Slide 8 — 怎么知道数字是对的  ⭐ 最重要的一页")
    body(doc, "**一句话：** 我们的价格必然对得上（因为"
              "价格是输入），所以找了三个 **完全在"
              "系统外面** 的东西来验。")

    h3(doc, "先把问题说清楚（这是这页的前提）")
    body(doc, "我们解出一个 spread 让模型价格 == 托管行"
              "价格。那价格当然对得上 —— "
              "**所以价格本身不能用来证明模型对**。"
              "必须找外部证据。")

    h3(doc, "检查一 — 温度计要在冰水里读零度")
    bullet(doc, "我们算的是“这只债比它本国政府借钱贵多少”。")
    bullet(doc, "那么拿一只**政府自己的债**去比"
                "**政府自己的曲线**，答案必须是零 —— "
                "你在拿一个东西跟它自己比。")
    bullet(doc, "日本：11 只，中位数 **+0.02 bp = 0.00%**。"
                "英国：12 只，**+4.42 bp = 0.04%**。")
    star(doc, "关键在于：**我们没有为了这个结果"
              "调过任何参数**。如果机器错了，"
              "它不会自己落在零上。")

    h3(doc, "检查二 — 外面有个系统算同样的数，我们对得上")
    bullet(doc, "托管行自己会算一个“利率动 1% 这只债"
                "价格动多少”的数。")
    bullet(doc, "我们从零自己算 —— **算的时候完全"
                "没看它的数**。")
    bullet(doc, "五只可提前赎回的机构债上两边都有数："
                "**四只差在 0.75 年以内**（0.200 / 0.316 / 0.633 / 0.741），"
                "而这些久期本身跨度是 1.1 到 9.4 年。")
    warn(doc, "**第五只差 2.2 年。** 被问到就直说："
              "这五只都是发行人可提前还款的，"
              "两边对“提前还款权”的处理不完全一样。"
              "四只对得上已经是很强的证据，"
              "因为我们从未参照过它的数。"
              "**不要把它藏起来** —— 主动说出来反而加分。")

    h3(doc, "检查三 — 用公开数据重建了客户自己的数字")
    bullet(doc, "通胀挂钩债的本金要按发行以来的通胀"
                "调整，那个系数叫 index ratio。")
    bullet(doc, "我们用**美国政府公布的 CPI**、按**美国财政部"
                "公布的规则**，从零重算了全部 13 只美国通胀债。")
    bullet(doc, "对上到**百万分之六**。")
    star(doc, "而且顺带发现了一件客户自己不知道的事："
              "**那套记录是按估值日的后一天定的。** "
              "我们是在估值日算出来差 10 倍才发现的。"
              "这个细节很有分量 —— 我们不只是“对上了”，"
              "而是从对不上的地方里挖出了事实。")

    # ---- slide 9
    h2(doc, "Slide 9 — 下一步")
    body(doc, "**一句话：** 四件事，按依赖顺序排。")
    table(doc, [
        ["", "什么", "要讲准的点"],
        ["1", "房贷类（882）",
         "引擎建好测过。**缺数据，不缺开发。**"],
        ["2", "三类池化产品（412）",
         "**真正的剩余工程，不要粉饰。** 但难的部分"
         "（现金流机器、期权模型、行情数据管道）"
         "已经在 766 只上建好并验证过了。"],
        ["3", "托管成服务 + 并行跑",
         "⭐ **这条最容易讲大。** 今天是：我们各自在"
         "自己的 Azure 终端里跑（9月16日测过，整本账 40 秒）。"
         "把它托管成别的系统能调的服务是**下一步**。"],
        ["4", "组合层风险", "最后做，等覆盖完成。"],
    ], widths=[0.35, 1.75, 4.7])
    warn(doc, "绝对不要让人把“**runs on Azure**”听成"
              "“**deployed as a service**”。前者是真的，后者还没做。"
              "这是全场最容易被事后抓住的一句话。")

    # ================================================================ PART 2
    h1(doc, "二 · 逐字讲稿")
    body(doc, "**蓝色缩进 = 要说出口的英文原话。** "
              "黑字是给你自己看的提示，不要念。"
              "每页的时长是数出来的，不是拍的：900 词，纯读稿 6.7 分钟，按汇报节奏（含停顿、看屏幕）约 **8.8 分钟**。")

    h2(doc, "从 Liping 手里接过来（slide 5 → 6）")
    body(doc, "提示：先给听众一张地图 —— 告诉他们"
              "你这半场要讲哪三件事。听众知道路线"
              "就会跟得住。")
    say(doc, "Thanks, Liping. Liping has told you what the system does. I'll cover three "
             "things: how much of the portfolio it covers, how we know the numbers are "
             "right, and what's left.")

    h2(doc, "Slide 6 — Coverage · 约 2 分钟")
    say(doc, "This is the whole portfolio — two thousand two hundred and sixty securities.")
    say(doc, "The blue block is finished: nine hundred and forty-nine securities, six of the "
             "thirteen categories. That's forty-two percent.")
    say(doc, "The orange block is the mortgage book — eight hundred and eighty-two "
             "securities. I want to be precise about this one, because it's the single "
             "largest block left and it is not blocked on us. The engine for it is built and "
             "tested. What it needs is the terms data, and that was requested in July.")
    warn(doc, "就说到“requested in July”为止。"
              "**不要加“still outstanding”**，除非你今晚"
              "确认了 Liping 那份 MBS 数据还没到。")
    say(doc, "The grey block is genuine remaining engineering.")
    say(doc, "One honest note on the blue. ‘Complete’ means the category is built and "
             "running — it does not mean every bond in it has our number. Of those nine "
             "hundred and forty-nine, seven hundred and sixty-six carry a price we computed. "
             "The other hundred and eighty-three don't, because their terms aren't in the "
             "records we were given.")
    say(doc, "That's deliberate, and it's worth a sentence. A tool that's going to be pointed "
             "at any portfolio has to be able to say what it cannot price, rather than guess "
             "at it. Every one of those hundred and eighty-three is named in a register, with "
             "its reason.")

    h2(doc, "Slide 7 — The thirteen categories · 约 1.5 分钟")
    body(doc, "提示：这页不要逐行念。说清两列的"
              "区别，再指出三块就行。")
    say(doc, "Here's the same thing with nothing rolled up.")
    say(doc, "Two columns, because they measure different things. The holdings file counts "
             "lines — two thousand three hundred and sixty-six. We count securities — "
             "two thousand two hundred and sixty. The difference is that a bond held by two "
             "managers appears twice. The line count reconciles against the client's own "
             "sheet exactly.")
    say(doc, "The top six are the bond categories, and they're done. Row seven is the "
             "mortgage book. Rows eight to ten are the pooled products — mortgage "
             "obligations, asset-backed, and commercial mortgage-backed.")
    say(doc, "The last three rows are small, and different in kind. The futures and options "
             "aren't bonds — they'd need machinery we haven't designed. They're sixteen "
             "securities out of two thousand two hundred and sixty, and they're counted as "
             "work still to do, not work written off.")

    h2(doc, "Slide 8 — How we know the numbers are right · 约 3 分钟  ⭐")
    body(doc, "提示：**这是你这半场的重心，慢一点讲。** "
              "先把“为什么需要这一页”说清楚 —— "
              "这一段不在屏幕上，但它是全页的钥匙，"
              "而且会把一个尖锐提问提前化掉。")
    say(doc, "This is the slide I'd most like you to take away.")
    say(doc, "Here's the problem it solves. The way this system works is: we take the bond's "
             "terms, the market rates for that day, and the price the custodian recorded — "
             "and we solve for the spread that reproduces that price. Which means the price "
             "always matches. Of course it does. The price is an input.")
    say(doc, "So the price can't tell us the model is right. We need checks that don't use "
             "anything we control. There are three.")
    say(doc, "First — a thermometer has to read zero in ice water. What we compute is what "
             "a bond pays above its own government's cost of borrowing. So take a "
             "government's own bond, and price it against that same government's curve, and "
             "the answer has to be zero — you're comparing the thing to itself. Japan comes "
             "out at zero point zero zero percent. The UK at zero point zero four. We didn't "
             "tune anything to land there; if the machinery were wrong, it wouldn't.")
    say(doc, "Second — somebody else computes some of the same numbers, and ours match. "
             "The custodian, the bank that holds these securities and keeps the official "
             "records, publishes its own measure of how much each bond moves when rates "
             "move. We compute ours from scratch, without looking at theirs. On four of the "
             "five bonds where both figures exist, they agree.")
    say(doc, "Third — we rebuilt the client's own figures from public data. An "
             "inflation-linked bond carries a factor for the inflation since it was issued. "
             "We recomputed all thirteen of the US ones from published government inflation "
             "statistics, using the Treasury's own rule. They match to six parts in a "
             "million.")
    say(doc, "And that third check found something. The client's factors are struck one day "
             "after the valuation date, not on it. Nobody knew that — we found it because "
             "at the valuation date the numbers were ten times worse.")
    say(doc, "So none of the three is us grading our own homework. One is a mathematical "
             "identity, one is somebody else's calculation, and one is public government "
             "data.")

    h2(doc, "Slide 9 — What's next · 约 2 分钟")
    say(doc, "Four things, in order.")
    say(doc, "The mortgage book. Engine built and tested — it needs terms data, not "
             "development.")
    say(doc, "The three pooled classes — mortgage obligations, asset-backed, commercial "
             "mortgage-backed. That's genuine remaining engineering and I won't dress it up "
             "as anything else. What makes it tractable is that the hard parts — the "
             "cash-flow machinery, the option model, the market-data plumbing — are already "
             "built and proven on the seven hundred and sixty-six we price today.")
    say(doc, "Third, hosting it as a service and then running it in parallel, with Ryse's "
             "engineer. I want to be precise here. Today each of us runs the code in our own "
             "Azure terminal — that's what the September trial proved, and it reprices the "
             "whole book in forty seconds. Hosting it so that Excel, or another system, can "
             "call it over the network is the next step. It's a defined piece of work rather "
             "than a rewrite, because the system already answers one request at a time, "
             "which is exactly the shape a service wants.")
    say(doc, "And last, the portfolio risk layer — once coverage is complete.")
    say(doc, "That's where we are. Happy to take questions.")

    # ================================================================ PART 3
    h1(doc, "三 · Q&A 预案")
    body(doc, "按“被问到的概率 × 答不好的代价”排序。")

    h2(doc, "Q1  ⭐ “You calibrate to the custodian's price — so of course your price "
            "matches. How is that validation?”")
    body(doc, "**这是整场最锐的问题，而且很可能真的"
              "被问。** 一个做固收的人一眼就看得出来。"
              "答好了是加分项。")
    say(doc, "You're right that it isn't — and that's exactly why that slide exists. The "
             "price is an input, not an output. What we produce is the spread and the risk "
             "numbers. The three checks are chosen precisely because none of them touches "
             "the calibration: a government bond on its own curve has to give zero by "
             "identity, the rate sensitivity is computed by somebody else, and the inflation "
             "factors come from public CPI data.")

    h2(doc, "Q2  “Why 2009 data?”")
    say(doc, "It's the client's own reference case — they chose it because the answers are "
             "already known, so we can be checked against them. It also happens to be the "
             "hardest test available: March 2009 is the crisis trough, when spreads were at "
             "their widest and the market was least well behaved.")

    h2(doc, "Q3  “Once the mortgage data lands, how long?”")
    say(doc, "The engine is built against an exact eight-field interface, so when the data "
             "lands it runs — no code change, by design. I'd rather not put a date on the "
             "validation, because that depends on what the data actually looks like.")
    warn(doc, "**不要承诺日期。** 投资人会记住日期。")

    h2(doc, "Q4  “Is it production-ready? Could the client run it tomorrow?”")
    say(doc, "They can run it today — it runs on Azure from a clean checkout and reproduces "
             "the published results exactly. What's not done is hosting it as a shared "
             "service that other systems call over the network. That's the third item on the "
             "last slide.")

    h2(doc, "Q5  “Why is the US number forty basis points and not zero, if the zero test "
            "works?”")
    body(doc, "⭐ **如果有人问这个，说明房间里有真懂"
              "固收的人。** 这个答案会让他记住你。")
    say(doc, "That's the off-the-run liquidity premium — a real market effect, not model "
             "error. We checked it directly: at the same maturity, the on-the-run ten-year "
             "comes out at about four basis points, while the older off-the-run bond at that "
             "same maturity is at forty-three. Recently issued Treasuries have a median "
             "under three.")

    h2(doc, "Q6  “How big is the team? How long?”")
    say(doc, "Two of us, twelve weeks, directed by Mario.")

    h2(doc, "Q7  “What's the commercial case?”")
    body(doc, "这是 Liping 那半场的内容，但你要能接住。")
    say(doc, "The capability that doesn't exist today isn't speed — it's scenario analysis "
             "at all. A thousand-round what-if in the spreadsheet either takes days or "
             "crashes it, so nobody asks for it. At forty seconds a full revaluation, a "
             "thousand scenarios becomes a capacity question, and capacity you can buy.")

    h2(doc, "Q8  “你具体做了什么？” / “What did you build?”")
    warn(doc, "这个问题对你的目的最重要。**具体，"
              "不要谦虚到模糊，也不要括大。** "
              "用下一页三个故事里的任意一个回答 —— "
              "讲一个具体的技术判断，比列一串职责有力得多。")

    # ================================================================ PART 4
    h1(doc, "四 · 如果有机会展示你自己：三个真实故事")
    body(doc, "三个都是真事，都能在 60 秒内讲完。"
              "按听众选：**A 给 quant，B 给工程，C 给任何人**。")

    h2(doc, "A · 一次测量阻止了我们做错的东西  ⭐ 首选")
    body(doc, "（适合高盛：定量洞察 + 先测量再动手）")
    say(doc, "Mario asked us to make inflation a parameter — per-country assumptions, "
             "sourced ourselves. Before building it, we measured what a constant inflation "
             "assumption actually does. At two percent, every single calibrated spread moved "
             "by exactly the same amount — a hundred and ninety-eight basis points — and "
             "nothing else moved at all. Not the price, not the duration.")
    say(doc, "The reason is that one-plus-pi to the t is exp of t times log one-plus-pi, so a "
             "constant inflation assumption folds straight into the discount exponent. It "
             "and a flat spread are mathematically the same single knob. Twenty-six "
             "countries of constants would have been twenty-six no-ops.")
    say(doc, "So we put the data where it does bite — the index ratio, which scales every "
             "cash flow, and which had never actually been validated. A one percent error "
             "there moves a published breakeven by six basis points.")

    h2(doc, "B · 一只没被任何东西定价的债")
    body(doc, "（适合工程背景的人：静默失败、职责归属）")
    say(doc, "We found a bond that nothing in the system priced. One module sent bonds with a "
             "short call gap to the simple pricer; another took only long gaps. This one had "
             "a ninety-day gap and fell in the hole between them. It wasn't in any output, "
             "any error log, or any report — two files each owned half of one decision, and "
             "neither knew it.")
    say(doc, "And the option value it reported as zero wasn't a small option — the option "
             "had never been evaluated at all. The fix wasn't to make the two numbers agree; "
             "it was to separate the responsibilities, so one place decides whether a bond is "
             "a candidate and another decides whether we can actually represent it.")

    h2(doc, "C · “数据不是无套利的”—— 其实是我们自己的 bug")
    body(doc, "（适合任何人：智识上的诚实）")
    say(doc, "For two months we believed the UK gilt curve data was broken. Our bootstrap "
             "kept refusing it as not arbitrage-free, and we'd asked the client for a "
             "replacement file. It turned out our own loader multiplied every curve file by a "
             "hundred — and two of the twenty-six files were already in percent. So the "
             "gilt curve was arriving at four hundred percent.")
    say(doc, "The error message was real. The conclusion was wrong. We fixed it with an "
             "explicit registry rather than a sniffer, because no threshold separates a "
             "zero-point-five percent yield from a zero-point-five decimal. And we added a "
             "rule to the project: a claimed data gap whose only evidence is your own error "
             "message isn't a data gap yet — reproduce it against the raw file first.")

    h2(doc, "几条实用建议")
    bullet(doc, "**你真正的优势是把技术系统讲清楚给"
                "非技术的人听。** 今天这场就是在演示"
                "这个能力 —— **讲得清楚本身就是内容**。")
    bullet(doc, "**不知道就说不知道：**“I don't know — I can find "
                "out and follow up.” 金融圈的人在测这个。"
                "**当场编一个数字的代价，比说不知道大得多。**")
    bullet(doc, "默认说“we”，但**被直接问到你做了什么"
                "时，要能具体说出来**。含糊地谦虚"
                "和括大一样不加分。")
    bullet(doc, "**会后找一个人、一个具体话题。** "
                "最好的后续理由是：“You asked about X — I looked "
                "into it, here's the answer.” 比任何寒暄开场白都管用。")
    warn(doc, "汇报里不要主动提找工作。今天的"
              "任务只有一个：让他们记住"
              "**这个人讲得清楚、数字靠得住**。"
              "剩下的交给会后。")

    # ================================================================ PART 5
    h1(doc, "五 · 数字速查（可以打印拿在手上）")
    table(doc, [
        ["数", "是什么", "出处"],
        ["**2,260 / 2,366**", "证券数 / 行数", "持仓表 Summary sheet"],
        ["**949**", "已完成的六大类", "同上"],
        ["**42%**", "949 ÷ 2,260", ""],
        ["**766**", "带我们自己价格的",
         "555 公司 + 3 可赎回 + 147 国债/市政 + 61 机构/担保/通胀"],
        ["**183**", "在完成类里但逐只列名的", "949 − 766"],
        ["**882**", "房贷类，引擎已建", "7 月请求数据"],
        ["**429**", "还未开始", "412 池化 + 16 期货期权 + 1 基金"],
        ["**0.00% / 0.04%**", "日本 / 英国 零测试中位数",
         "n=11 / n=12，+0.02bp / +4.42bp"],
        ["**4 / 5**", "机构债久期与托管行一致",
         "0.75 年内；第五只差 2.2 年"],
        ["**6 / 1,000,000**", "13 只美国通胀债 index ratio 重建误差",
         "CPI-U NSA + 财政部规则"],
        ["**40 秒**", "Azure 上重算整本账", "2026-09-16 实测"],
        ["**12 周**", "项目时长", "6月26日 – 9月22日"],
        ["**+40.6bp**", "美国国债中位数 = 老券流动性溢价",
         "同期限新券 +3.9bp，老券 +42.8bp"],
    ], widths=[1.3, 2.7, 2.8])

    warn(doc, "每个数都来自 2026-09-22 的实跑输出。"
              "如果明天之前又跑了一次驱动脚本，"
              "拿 `docs/release_facts_<date>.md` 核一下再用。")

    doc.save(str(out))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="docs/Presenter Notes v6.docx")
    args = ap.parse_args()
    out = build(pathlib.Path(args.output))
    print("wrote %s (%s bytes)" % (out, format(out.stat().st_size, ",")))


if __name__ == "__main__":
    main()
