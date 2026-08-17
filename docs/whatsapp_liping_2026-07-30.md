# WhatsApp request to Liping — 2026-07-30 (verbatim archive)

Attachments sent with it: `outputs/govt_mtge_cusips.csv` + `outputs/govt_mtge_bdp_template.csv`.
Registry tracking these gaps: `docs/missing_data.md`. `*…*` = WhatsApp bold.

---

## 中文版

Liping,你今天在学校有 Bloomberg 的话,帮我拉几块数据 🙏 按优先级排:

*① Govt MBS:882 个 CUSIP × 8 个字段(最优先,引擎已建好就等数据)*
字段(security key = CUSIP + " Mtge"):
MTG_WACPN, MTG_WAM, MTG_STATED_WALA, MTG_AOLS, MTG_GEN_CPR_3M, MTG_GEN_CPR_6M, MTG_GEN_CPR_12M, MTG_HIST_COLLAT_CPR_LIFE
- 附件1 = CUSIP 清单;附件2 已写好 BDP 公式,在有 Bloomberg 插件的 Excel 里直接打开等它算完、另存 xlsx 发回来即可
- 持仓日是 2009-03-31:WAM/WALA/CPR 随时间变,能取历史 as-of 最好(FLDS 里查字段的日期 override,或 BDH 拉月度史);取不到就拉当前值+注明取数日,WAM 我们自己回推。已付清的池子返回 N/A 正常,留空即可

*② 公司 pass-through 13 只(航空 EETC/私募)— 要本金摊还计划*
每只:factor(as of 2009-03-31)+ 摊还时间表(DES → Cash Flow/CSHF 或 factor schedule,导出或截图)+ 息票/频率确认:
1. US247367BH79 — Delta Air 6.821% 2022-08-10
2. US210805CQ83 — Continental 1999-1 Cl A 6.545% 2020-08-02
3. US210805BU05 — Continental 1997-4A 6.90% 2019-07-02
4. US210805DE45 — Continental 2000-2 A-2 7.487% 2012-10-02
5. US210805DD61 — Continental 2000-2 A-1 7.707% 2022-10-02
6. US02378JAC27 — American Airlines 1999-1 A-2 7.024% 2011-04-15
7. US909287AA20 — United Air 2007-1A Cl A 6.636% 2022-07-02
8. US126650AW08 — CVS Caremark 5.298% 2027-01-11 (144A)
9. US126650BF65 — CVS Caremark 6.036% 2028-12-10 (144A)
10. US377672AA80 — Glen Meadow Pass-Thru 6.505% 2067-02-12 (144A)
11. US87203RAA05 — Systems 2001 AT (BAE) Cl G 6.664% 2013-09-15 (144A)
12. US87203RAC60 — BAE Systems 2001 AT Cl B 7.156% 2011-12-15 (144A)
13. US84254QAA76 — Southern Capital 2002-1 Cl G 5.70% 2023-06-30 (144A)

*③ 11 只 FRN/混合债 — 缺条款(144A/私募,公开渠道查不到),每只一页 DES 的事*
3 只要全套浮动条款(index + margin + 付息频率):
- US61532RAA77 — Monumental Global Funding II 2005-C FRN, due 2010-06-16
- US61532XAB29 — Monumental Global Funding III FRN, due 2014-01-15
- US634902LH11 — National City Bank FRN, due 2010-01-21
8 只只要 call/switch 之后的浮动公式(index + margin,固定段已查清):
- US76117JAB44 — Resona 5.85% perp:2016-04-15 之后
- US17133PAA66 — Chuo Mitsui 5.506% perp:2015-04-15 之后
- XS0238543416 — BTMU 3.50% 2015:2010-12-16 之后
- XS0212517550 — Resona EUR 3.75% 2015:2010-04-15 之后
- XS0229704886 — Resona 4.125% perp:2012-09-27 call 之后
- XS0229705008 — Resona 姊妹券:全套条款(哪种 tranche 都查不到)
- XS0244642889 + XS0244642616 — Shinsei LT2(144A/RegS 同一结构):2011-02-23 之后的 margin
(看 DES 的 floater/coupon 页,或 FLDS: RESET_IDX / FLT_SPREAD / MULTI_CPN_SCHEDULE,截图即可)

*④ 1 只缺 call schedule:*
- US04622DAA90 — Assured Guaranty US Hldgs 6.4% 2066:call schedule(日期+价格),顺带看下 call 后是否转浮动(margin 多少)

*⑤ 顺手项(有余量再看,都不急):*
- KR1035027T36 — 韩国通胀债 KTBi 2017:index ratio / base CPI as of 2009-03-31,加一条韩国国债 par 曲线 2009-03-31
- UK Gilt par 曲线 2009-03-31 和 2009-06-10(我们 GBP 曲线 3y 点有问题,卡着几只 GBP 债)
- 5 只 agency callable 的 call schedule 确认(模型现按 par@100 已对上托管人,纯确认):US3133XKKW43 / US3128X4BE02 / US3128X4UZ20 / US31359ML849 / US31359M2B87
- US31359MGT45 — FNMA 6.25% 2011:master 里评级 A/Aa2 很反常,看下是 senior 还是 subordinated + 2009 年当时的评级
- FHLMC REMIC Series 3122 Class ZB(输 FHR 3122 ZB <Mtge>):DES 截图,后面 CMO 阶段用

①③ 之前发过 Mario 还没回音,你能拉到就不用等他了。谢谢!!

---

## English version

Liping, if you have Bloomberg access at school today, could you help me pull a few things? In priority order:

*① Govt MBS: 882 CUSIPs × 8 fields (top priority — the pricing engine is built and waiting on this)*
Fields (security key = CUSIP + " Mtge"):
MTG_WACPN, MTG_WAM, MTG_STATED_WALA, MTG_AOLS, MTG_GEN_CPR_3M, MTG_GEN_CPR_6M, MTG_GEN_CPR_12M, MTG_HIST_COLLAT_CPR_LIFE
- Attachment 1 = the CUSIP list; attachment 2 already has the BDP formulas — just open it in Excel with the Bloomberg add-in, let it finish, save as xlsx and send it back
- The holdings date is 2009-03-31: WAM/WALA/CPR drift over time, so as-of historical values are best (check the field's date override in FLDS, or pull monthly history via BDH); if not possible, pull current values and note the pull date — we can roll WAM back ourselves. Paid-off pools returning N/A is expected, just leave them blank

*② Corporate pass-throughs, 13 securities (airline EETCs / private placements) — need the principal amortization schedules*
For each: factor (as of 2009-03-31) + amortization schedule (DES → Cash Flow/CSHF or the factor schedule — export or screenshot) + coupon/frequency confirmation:
1. US247367BH79 — Delta Air 6.821% 2022-08-10
2. US210805CQ83 — Continental 1999-1 Cl A 6.545% 2020-08-02
3. US210805BU05 — Continental 1997-4A 6.90% 2019-07-02
4. US210805DE45 — Continental 2000-2 A-2 7.487% 2012-10-02
5. US210805DD61 — Continental 2000-2 A-1 7.707% 2022-10-02
6. US02378JAC27 — American Airlines 1999-1 A-2 7.024% 2011-04-15
7. US909287AA20 — United Air 2007-1A Cl A 6.636% 2022-07-02
8. US126650AW08 — CVS Caremark 5.298% 2027-01-11 (144A)
9. US126650BF65 — CVS Caremark 6.036% 2028-12-10 (144A)
10. US377672AA80 — Glen Meadow Pass-Thru 6.505% 2067-02-12 (144A)
11. US87203RAA05 — Systems 2001 AT (BAE) Cl G 6.664% 2013-09-15 (144A)
12. US87203RAC60 — BAE Systems 2001 AT Cl B 7.156% 2011-12-15 (144A)
13. US84254QAA76 — Southern Capital 2002-1 Cl G 5.70% 2023-06-30 (144A)

*③ 11 FRNs/hybrids — missing terms (144A/private placements, nothing public); one DES page each*
3 need the full floating terms (index + margin + payment frequency):
- US61532RAA77 — Monumental Global Funding II 2005-C FRN, due 2010-06-16
- US61532XAB29 — Monumental Global Funding III FRN, due 2014-01-15
- US634902LH11 — National City Bank FRN, due 2010-01-21
8 only need the post-call/post-switch floating formula (index + margin; the fixed leg is already sourced):
- US76117JAB44 — Resona 5.85% perp: after 2016-04-15
- US17133PAA66 — Chuo Mitsui 5.506% perp: after 2015-04-15
- XS0238543416 — BTMU 3.50% 2015: after 2010-12-16
- XS0212517550 — Resona EUR 3.75% 2015: after 2010-04-15
- XS0229704886 — Resona 4.125% perp: after the 2012-09-27 call
- XS0229705008 — Resona sister tranche: ALL terms (couldn't even identify the tranche type)
- XS0244642889 + XS0244642616 — Shinsei LT2 (144A/RegS, same structure): margin after 2011-02-23
(DES coupon/floater page, or FLDS: RESET_IDX / FLT_SPREAD / MULTI_CPN_SCHEDULE — screenshots are fine)

*④ 1 bond missing its call schedule:*
- US04622DAA90 — Assured Guaranty US Hldgs 6.4% 2066: call schedule (dates + prices), and check whether it flips to floating after the call (what margin)

*⑤ Nice-to-haves (only if you have time left, none urgent):*
- KR1035027T36 — Korean inflation-linked KTBi 2017: index ratio / base CPI as of 2009-03-31, plus a KRW govt par curve for 2009-03-31
- UK Gilt par curve for 2009-03-31 and 2009-06-10 (our GBP curve has a bad 3y node blocking a few GBP bonds)
- Call-schedule confirmation for 5 agency callables (model assumes par@100 and already matches the custodian — confirmation only): US3133XKKW43 / US3128X4BE02 / US3128X4UZ20 / US31359ML849 / US31359M2B87
- US31359MGT45 — FNMA 6.25% 2011: the master file rates it A/Aa2, which looks odd — check senior vs subordinated + the ratings as of 2009
- FHLMC REMIC Series 3122 Class ZB (type FHR 3122 ZB <Mtge>): DES screenshot, for the CMO phase later

① and ③ went to Mario earlier with no reply yet — if you can pull them we won't wait on him. Thanks a lot!!
