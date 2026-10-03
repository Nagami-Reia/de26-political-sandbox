# 2024 K-Frage：民调事件窗校准

## 结论先行

2024-09-16/17 的 K-Frage 收束，对 Union 全国政党票没有可辨认的稳定正向跳升。同机构前后变化落在 `-2.0…+1.0` 个百分点；较干净的三个短窗（INSA online、INSA TOM、Forsa）分别为 `-1、-1、+1`，中位数 `-1`、均值 `-0.33`。考虑样本误差和同步新闻，稳健规则不是 `-1`，而是：

> orderly closure 对全国政党票的中央估计为 `0.0 pp`，合理敏感区间 `-1.0…+1.0 pp`。

候选人特定指标反应更大。Forsa 在最干净的周度切分中，Merz 的直接总理偏好由 26% 升到 28%，即 `+2 pp`；同一周 Union 政党票只增 `+1 pp`。但 FGW 的一般形象评分和 Infratest 的满意度没有同步改善，说明“被视为可行候选人”与“喜欢/满意”必须分开。

## 识别设计

1. 只做同机构前后比较，避免把不同机构的 house effect 当作事件效果。
2. 优先使用 2024-09-16/17 前后各一期；把跨越 Brandenburg 州选或一个月的窗口标为混杂。
3. 16 日 Wüst/NRW 决定与 17 日 Merz–Söder closure 无法用公开民调拆开，因为没有一天频率的独立测量；模型只能校准整个事件包。
4. 观测变化不是纯因果估计。同期还有 Brandenburg 州选、移民政策争论和政府新闻。
5. 所有变化都与典型抽样误差同量级。Forsa 对 2,500 人样本明确给出约 `±2.5 pp`，因此单次 `±1 pp` 不应解释为真实结构性移动。

## 同机构事件窗

| 机构 | 前值 | 后值 | 变化 | 窗口质量 |
|---|---:|---:|---:|---|
| INSA online | 33.0 | 32.0 | -1.0 pp | 短窗；前期截至事件日 |
| INSA TOM | 33.0 | 32.0 | -1.0 pp | 短窗；后期覆盖事件 |
| Forsa | 31.0 | 32.0 | +1.0 pp | 最干净的周度切分 |
| FGW | 33.0 | 31.0 | -2.0 pp | 长窗；受 Brandenburg 混杂 |
| Infratest dimap | 33.0 | 31.0 | -2.0 pp | 长窗；多重混杂 |
| YouGov | 32.0 | 32.0 | 0.0 pp | 长窗；多重混杂 |
| Allensbach | 35.5 | 36.0 | +0.5 pp | 长窗；多重混杂 |

## 对 H001 情景的应用

这里把用户指定的“Evers/CDU 赢 Berlin；SPD 在 MV 险胜 AfD”作为已知情景，不预测选举结果本身，只预测下一轮民调可能怎样消化结果。

| 指标 | 事件前基线 | 中央增减 | 下一轮中央值 | 敏感区间（增减） |
|---|---:|---:|---:|---:|
| Berlin CDU 投票意向 | 20.5 | +1.5 pp | 22.0 | +0.5…+3.0 |
| Evers 适任市长 | 22.0 | +4.5 pp | 26.5 | +3.0…+7.0 |
| Evers 工作满意度 | 18.0 | +3.5 pp | 21.5 | +2.0…+6.0 |
| Union 全国投票意向（四机构均值） | 19.8 | +0.4 pp | 20.2 | -0.5…+1.2 |
| SPD 全国投票意向（四机构均值） | 12.6 | +0.6 pp | 13.2 | 0.0…+1.5 |
| AfD 全国投票意向（四机构均值） | 28.0 | -0.4 pp | 27.6 | -1.2…+0.3 |
| Merz 满意度 | 13.0 | +0.3 pp | 13.3 | -0.5…+1.0 |

`20.5` 是两份 Berlin 州民调 20/21 的简化中点。全国基线是情景日前最近的 INSA、Forsa、Infratest dimap、YouGov 的简化等权平均，不是 poll-of-polls。所有“下一轮中央值”都是模型投影，真实发布时必须覆盖为 `OBSERVED`，不能继续沿用模型线。

## 规则分解

- **组织收束效应**：对全国政党票中央值约 0；它主要改变党内行动能力，而非立即创造选民。
- **可行性/胜者更新**：候选人直接适任指标通常比政党票更敏感。2024 的弱处理（获得提名）为 +2 pp；H001 的强处理（实际赢得州选）因此用 +3…+7 pp，而不是直接套用 +2。
- **州到联邦折损**：地方胜负传到全国只保留约四分之一，中央值是模型假设，2024 K-Frage 本身不能识别该倍数。
- **归因分配**：Berlin 胜利主要给 Evers 和 Berlin CDU；MV 险胜主要给 SPD 州级执政能力。Merz 只得到很小的间接外溢。
- **反事实警报**：若下一轮民调超出区间，不应把参数硬调回命中；应先检查联盟谈判、投票率、候选人采访、联邦同期新闻和机构 house effect。

## 加入机构正在使用的观测/投影模型

这里必须区分两层：我们的事件模型先产生一个“潜在支持变化”；民调机构再通过自己的抽样、加权、投影和取整把它变成公布值。机构层采用：

`公布值(i,t) = 按机构刻度取整[该机构上期值 + 保留率(i) × 潜在事件冲击 + 抽样/田野误差]`

从各机构自己的上期值出发，会自动保留 house effect，但不会假装知道其内部权重。确定性 baseline 只用中央值；Monte Carlo 才抽取误差。

| 机构 | 官方可见模型 | 本模型如何模拟 | 仍是黑箱 |
|---|---|---|---|
| INSA | 约 2,000 人 online，永久电话调查支撑；只计合资格选民自报意向；另有 safe/max/negative potential | 周频、冲击保留率 1.0、0.5 pp 刻度 | 配额、电话融合、权重上限、未决者分配 |
| Forsa | 随机电话选择、户内 last-birthday；可做 fixed/mobile dual frame；自愿报名不能进入 omninet | 周度滚动、保留率 1.0、1 pp 刻度 | 当前 Sonntagsfrage 的 mode mix、政治权重与 recall 系数 |
| FGW | fixed/mobile RDD + SMS 一次性 online；design weight、dual frame、按性别/年龄/教育校正 | “政治情绪”保留 1.0；正式 projection 保留 0.6、1 pp 刻度 | 长期认同、党派绑定、策略投票的系数 |
| Infratest dimap | 随机电话 + online；明确说是当前倾向而非预测 | 月频，保留率 0.75、1 pp 刻度 | 2026 的详细权重；2021 曾公开社会人口 + 回忆票、Sonntagsfrage 单独加权 |
| YouGov | 自有 online panel；按年龄、性别、教育、地区、政治兴趣、回忆票、城乡配额/加权 | 多日 online，保留率 0.9、0.5 pp 刻度 | propensity、weight caps、未决者处理 |
| Allensbach | 面访 quota；约 1,000，公布 95% 区间 | 较长田野窗，保留率 0.5、0.5 pp 刻度 | Sonntagsfrage 专属 quota、政治换算与未决者处理 |

“保留率”不是机构自报参数，而是我们为了模拟发布时间和窗口稀释而设的假设。因此不能写成“INSA 算法认为 +0.4”；正确说法是“我们的潜在冲击经 INSA 周频观测层后，中央公布值会怎样取整”。完整机器可读版本见 `pollster_observation_models_2026.json`。

以 Union 全国潜在 `+0.4 pp` 为例：

- INSA：`19.5 + 1.0×0.4 = 19.9 → 20.0`；
- Forsa：`20.0 + 1.0×0.4 = 20.4 → 20`，因此中央情景显示“不动”；
- Infratest：`21.0 + 0.75×0.4 = 21.3 → 21`；
- YouGov：`18.5 + 0.9×0.4 = 18.86 → 19.0`。

这解释了为什么同一个弱事件可能表现为某机构 `+0.5`、某机构 `0`：并不需要假设选民在不同机构里真的改变了方向。

## Source notes

- INSA weekly series: https://www.wahlrecht.de/umfragen/insa/2025.htm
- Forsa weekly series: https://www.wahlrecht.de/umfragen/forsa.htm
- Forsa post-closure candidate and party metrics: https://www.presseportal.de/pm/154530/5871957
- ZDF Politbarometer September II: https://presseportal.zdf.de/pressemitteilung/zdf-politbarometer-september-ii-2024
- ARD DeutschlandTrend October: https://presse.wdr.de/plounge/tv/das_erste/2024/10/20241010_deutschlandtrend_politische_stimmung.html
- YouGov series: https://www.wahlrecht.de/umfragen/yougov.htm
- Allensbach series: https://www.wahlrecht.de/umfragen/allensbach.htm
- INSA current method/products: https://www.insa-consulere.de/leistungen/
- Forsa sampling dialogue: https://www.forsa.de/dialog-mit-forsa/
- FGW sampling, weighting and projection: https://www.forschungsgruppe.de/Rund_um_die_Meinungsforschung/Methodik_Politbarometer/ and https://www.forschungsgruppe.de/FAQ/
- Infratest Sonntagsfrage/FAQ: https://www.infratest-dimap.de/umfragen-analysen/bundesweit/sonntagsfrage and https://www.infratest-dimap.de/service/faqs/
- YouGov quota/weighting disclosure: https://ygo-assets-websites-editorial-emea.yougov.net/documents/YouGov_Sonntagsfrage_August2024.pdf
- Allensbach current series and quota interviewing: https://www.ifd-allensbach.de/studien-und-berichte/sonntagsfrage/gesamt.html and https://www.ifd-allensbach.de/das-institut/interviewen-fuer-allensbach.html

Structured values and quality flags are in `2024_kfrage_poll_event_study.json`.
