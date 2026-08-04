# Code-review response — clean/dirty 校准口径:审计结论与修复(致 Liping)

*2026-08-04 · 修复 commit `f7e9e7d` · 全文技术记录见 WORKLOG 2026-08-04 · draft,发送渠道由
charlieee 定(如需英文版可转)*

---

## TL;DR

你在 code review 里提的问题是对的,值得提,而且**真的抓出了一个 bug——只是和猜想的不是同一个**。
审计结论:七个引擎里六个(vanilla / vanilla-schedule / zero / FRN / hybrid / ILB)本来就是
clean-对-clean 校准,自洽;唯一的异类是 callable lattice——但它**不是**"dirty PV 对 clean BT",
而是**根本没建应计**的整周期近似网格,真正的缺陷在网格计时上。我们把它修成了精确口径(真实票息
时点 ⇒ 真 dirty ⇒ 减共享应计 ⇒ 对 BT),并把你那句"implied OAS 不随价格表示方式变化"固化成了
16 条永久回归测试。影响面:只有 8 只 lattice 券的数字变了,±35bp 以内、方向不一;其余全部逐位不变。

---

## 1. 你的框架,数学上的表述

模型折出的 PV 天生是 dirty(含下一张完整票息的现值);托管行 BT 是 clean(文件里有独立的
Accrued income 列;近到期高评级债 our_clean 对 BT 差 0.02%)。应计 AI 只依赖日期——与曲线、
OAS、任何内嵌期权都无关——所以两种校准写法:

    解 OAS 使 dirty(OAS) = BT + AI      (dirty 形式)
    解 OAS 使 clean(OAS) = BT           (clean 形式,clean ≡ dirty − AI)

是**同一个方程两边加减同一个常数,根相同**。这就是你说的"implied OAS 不会随 price 变化"——
它对价格的*表示方式*(净价/全价)不变,而不是对价格水平不变。这个恒等式现在是一条被测试
锁死的 invariant(§4)。

## 2. 审计结果(逐引擎打开代码查,不靠推理)

| 引擎 | 校准目标(实况) | 判定 |
|---|---|---|
| vanilla / vanilla-schedule | `implied_oas` 解 clean == BT,clean = dirty − AI | ✅ 自洽 |
| zero / STRIPS | coupon=0 ⇒ AI≡0,clean≡dirty | ✅ 平凡自洽 |
| FRN | clean == BT;AI = 上次 reset 锁定票息 × elapsed/364 | ✅ |
| fixed-then-float | clean == BT;AI = 固定腿在 switch 锚定网格上的应计 | ✅ |
| ILB | clean == BT;AI = 实际票息应计 × ratio₀(与 BT 的通胀调整口径一致) | ✅ |
| to-call 参照列 | 走 `price_bond`(clean 形式),不经 lattice | ✅ |
| **lattice** | **树 PV 直接对 BT** —— 但树里没有任何应计现金流 | ⚠️ 见 §3 |

风险指标分母:`risk.py`/FRN/hybrid/ILB 全部本来就用 **dirty**(risk.py 文档明确写了理由)。

## 3. lattice 真正的问题——以及为什么"减个 AI"反而会制造 bug

旧 lattice 是整周期网格:`N = round(T·freq)`,估值日被当作票息日,第一张票息放在整整半年后,
**无 stub、无应计**。这样的 PV 是"integer-period fiction"意义上的**近似 clean**(这正是净价
作为报价惯例存在的原因),所以它对 BT 的校准*意图*上是 clean 对 clean——你假设的那种系统性
+AI 高估不存在。

但这个近似只在贴近平价/贴近票息日时成立,真实缺陷有三个,全在计时上:

1. 首张票息放在整周期外,而真实 stub 只有零点几年;
2. 到期日被 `round` 吸到半周期栅格上;
3. `T` 和 call 时点用 **365.25 天**换算,而整个 vanilla 栈是 **ACT/364** ——两套天数打架。

具体到 TNTD04441873(6.45% 2034,估值 2009-03-31):真实剩余票息 **51** 张(182 天回溯网格),
旧树上只有 **50** 张——365.25/364 的错位恰好把 `round` 翻了过去,**整整丢了一张票息**。

**为什么不能照字面执行"latticePV − AI 对 BT"**:旧 PV 已经通过整周期虚构"近似排除"了应计,
再减一次 AI 等于双重扣减——模型价被压低 ~AI,解出的 OAS 会被**压低**约 10-30bp,恰好*制造出*
假设中要修的那个量级的误差,只是方向相反。这是"先打开代码验证、再动手修"的又一个实例
(z_semi 那次的教训,这次同样适用)。

**实际的修法**(`f7e9e7d`):把格子铺到真实 ACT/364 票息时点上(变步长 BDT,首步 = 真 stub)
⇒ 根节点 PV = **真 dirty**;再减共享的 vanilla 应计公式(`bond_price.accrued_interest`,全库
唯一一份,`price_bond` 自己也改为消费它)⇒ clean 对 BT。call 时点统一 364 d/y。副产品是一条
很强的新 invariant:**无期权债上树 ≡ `price_bond` dirty 到机器精度**,即 lattice 和 vanilla
校准器对同一目标解出同一个 OAS(已测试)。

## 4. 你的话变成了机制:`tests/test_price_convention.py`(16 条,全套 145 绿)

每个引擎:clean 形式的根(引擎自己的 API)vs dirty 形式的根(独立 brentq 解
`engine.dirty == BT + 共享AI`,故意不用引擎自带的 accrued)之差 **< 1e-10**;外加 FRN/hybrid/
ILB 的共享 AI 恒等锁、lattice≡price_bond、估值日恰逢票息日的角点、零息 AI=0。今后任何引擎
再犯口径混用、或私造第二份 AI 公式,测试会机械式挂掉——你的 review 意见从此不依赖任何人记得它。

## 5. 影响面(只有 lattice 路由的 8 只;其余输出逐位比对不变)

| 券 | implied OAS (bp) 前→后 | eff-dur 前→后 |
|---|---|---|
| 公司 TNTD04115619 (BBB '13) | 1959.0 → 1993.6 (+34.6) | 3.42 → 3.31 |
| 公司 TNTD04441873 (A '34) | 412.3 → 410.8 (−1.5) | 10.54 → 10.37(straight 11.43,AQ 11.73)|
| 公司 TNTG701850W (EUR A '14) | 293.2 → 305.6 (+12.4) | 5.31 → 5.00 |
| 机构 FHLB 5.53 '14 | 160.5 → 190.0 (+29.5) | 0.99 → 1.07(AQ 0.87)|
| 机构 FHLMC 5.30 '20 | 223.0 → 212.0 (−11.0) | 4.30 → 3.72(AQ 5.92)|
| 机构 FHLMC 5.625 '35 | 181.2 → 178.9 (−2.3) | 9.66 → 9.43(AQ 9.74)|
| 机构 FNMA 6.00 '36 | 194.1 → 191.4 (−2.6) | 9.12 → 8.88(AQ 9.62)|
| 机构 FNMA 5.625 '21 | 197.0 → 189.7 (−7.3) | 5.33 → 4.74(AQ 5.38)|

注意变化是**混合方向、≤35bp**,而不是 dirty-对-clean 假设预言的"统一高估 ~AI/dur ⇒ 修后统一
下调 10-30bp"——这本身就是"实际机制是计时漂移而非应计错配"的实证。诚实备注:机构 callable
修后离托管行 AQ 略远了一点(4/5 由 0.5y 内变 0.75y 内)——旧引擎两个近似(snap 网格 + 类 clean
基准)恰好相互抵消偏向 AQ;我们选精确口径 + 机器精度的 vanilla 对齐,不迁就对一个模型未知的
托管数字的偶然拟合。

## 6. 两个附带问题的落定

- **久期分母(dirty vs clean)**:两种都算了,对全部 61 只带托管行 AQ 的债逐只对照——dirty
  更近 41/61,median |dur−AQ| 0.236 vs 0.331;在模型与 AQ 吻合最好的信息子集(TLGP 块,误差
  0.006-0.028)dirty 一致胜出 ⇒ 托管行 AQ 本身就是全价基准。**保留 dirty(全价)分母**,与
  Bloomberg 惯例一致;仅 callable 子集偏 clean(4/5),但那里 σ/par-call 假设噪声比分母效应
  大一个量级,是小样本噪声。两种分母现在都常设输出在 driver CSV 里,随时可复核。
- **ILB 应计的 ratio 口径**:确认一致——应计 = 实际票息应计 × 估值日 ratio₀,与 BT(通胀调整
  净价,BT==BU/par·100)同口径,已有单测锁死。

## 7. 如何自己复核(如果你想)

47 上:`.venv/bin/python -m pytest tests/test_price_convention.py -q`(16 passed);
`outputs/callable_risk.csv` 与 `outputs/phase2_risk_2009-03-31.csv` 新增 `accrued` /
`eff_dur_*cleanden` 列;修前数字的完整对照在 WORKLOG 2026-08-04 与
`docs/headline_numbers_2026-08-04.md`。

---

谢谢这次 review——z_semi 那次你抓的是两套 bootstrap 的混用,这次抓的是一个没有明确口径的引擎:
两次都是 convention 层面的真问题,也都变成了永久测试。另:你 7-30 清单第④项的 AssuredGty 2066
(US04622DAA90)call schedule 一到,那只最后的 callable 就会在修好的引擎上直接定价。
