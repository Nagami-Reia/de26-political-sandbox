# 黑箱补查：公开材料能把不确定性缩到什么程度

**研究批次：2026-09-18；状态截点仍为 2026-07-31。**  
本文件可以使用截止日之后发布的材料来核实此前已经存在的履历或组织关系，但不得用后来行为、任命或选举结果反推 7 月 31 日的决策状态。

## 证据等级

- **A**：当事人同期直接表述、正式文件、具名投票或公开组织决定。
- **B**：两家相互独立的可靠媒体一致报道，或官方事实加所在地媒体解释。
- **C**：一家可靠媒体的记者观察/匿名党内来源；只形成弱先验。
- **D**：评论、候选人猜测、未获独立确认的“圈内传闻”；不能进入 baseline。

## 1. Merz—Frei 的真实操作关系

### 新材料

- Frei在 7 月 29 日 ZDF 长访谈中明确区分两个岗位：任总理府主任时负责支持总理、协调政府、促成妥协；任党团主席后负责“有力代表党团利益”。他同时说自己在绝大多数政策问题上与 Merz想法相近，但不是议员的单纯传声筒，而有自己强烈的政治意见。**A**
- 2025 年竞选期和组阁报道长期把 Frei描述为 Merz 的“右手”、核心经理和亲近协作者；但 ZDF 对 Merz核心圈的梳理指出，Frei最初由 Brinkhaus选入党团管理层，后来通过组织绩效取得 Merz信任，而非最初私人班底。**B/C**
- 91.9%党团票是独立制度授权，且高于仅靠总理提名即可解释的最低支持。**A；解释为制度资源，不解释为私人忠诚**

### 可安全写入模型

- `policy_similarity(Merz,Frei)`: **高**。
- `operational_trust(Merz,Frei)`: **高，但来源主要是工作表现**。
- `role_obligation_to_faction(Frei)`: **高**。
- `automatic_personal_obedience`: **不得设为真**。

### 仍未知

两人是否就冲突时的最终否决权、汇报节奏、党团异议边界达成私下协议。

## 2. Warken 能否真正驱动总理府

### 新材料

- 她不是纯粹的专业卫生官僚：此前任联盟党团议会经理，长期从事内政、法律和选举法，曾任 Baden-Württemberg CDU总书记、JU联邦副主席、THW州协会主席，并任 CDU妇联全国主席。**A/B**
- 作为卫生部长，她在高度冲突的医保稳定方案上完成了与 SPD 的妥协；Merz在公开场合多次以改革范例称赞。**A/B**
- 2025 联邦选举，她在 Odenwald-Tauber 获约43%第一票，为 Baden-Württemberg CDU候选人中最高；所在地 SWR还把她描述为 Manuel Hagel 的亲近盟友。**B；“亲近”属媒体关系判断**
- 她自述工作风格为急于推进、重沟通、有时固执。此为可用于人格假说的自陈，不是经行为验证的稳定参数。**A但外部效度有限**

### 可安全写入模型

- 将 `coalition_bargaining_experience`、`parliamentary_process_knowledge`、`BW_party_bridge` 从未知提升为 **中高/高**。
- 总理府初始学习成本低于“毫无组织经验的新部长”。
- 与 Hagel/BW网络存在可信桥梁，但不等于受其指挥。

### 仍未知

SPD部长、Frei领导的党团、Söder/CSU以及不满的州总理是否承认她拥有代表 Merz作最终交换的权限。7月31日前没有足够新岗位行动样本。

## 3. Hoppermann 的授权和派系位置

### 新材料

- 1998入JU、1999入CDU，长期在 Hamburg-Wandsbek做基层/区级政治；2017起任 Hamburg妇联主席，进入 CDU联邦执委会、主席团并任财务主管。**A/B**
- 她是 Merz 2025 年推荐的财务主管人选，也是 Merz 2026 年推荐的总书记人选。**A**
- 但她在 2021/22 CDU主席竞选中属于 Norbert Röttgen团队，若 Röttgen胜出原计划出任总书记。**A（竞选团队公开信）**
- 她同时具有 CDA（社会翼）、妇联、Hamburg城市组织和地方基层接口。**A/B**

### 可安全写入模型

- `access_to_Merz`: **高**；`long_term_personal_dependency_on_Merz`: **中低至中，不能设高**。
- 她有跨党内子组织的桥接潜力，不宜归为单一经济自由派或单一保守派。
- `formal_mandate_duration`仍受“临时至下次党代会”约束。

### 仍未知

她是否获得独立确定党务路线、人事和竞选信息的权限；党总部团队是否随调任重组；各州党部对她的实际服从程度。

## 4. 党团第一议会经理空缺

补查确认 Bilger离岗，但截止日没有正式继任者。后来9月任命不得回填。故该黑箱不是“缺资料”，而是**真实空缺状态**。

模型处理：短期降低党团日程、纪律和部长—议员协调的确定性；由 Frei、现任议会经理和 CSU侧 Reinhard Brandl临时吸收多少工作仍为 `UNKNOWN`。

## 5. 体育与志愿事务国务部长

7 月 28 日已有媒体报道 Nadine Keßler可能接任，但尚未正式决定。候选传闻列为 **C/D**，baseline 保持空缺；Schenderlein离开造成的 Sachsen/东部代表性损失则是已观察事实。

## 6. “个人忠诚”能否直接观测

只能拆成关系证据：

| 关系 | 可观察证据 | 安全结论 |
|---|---|---|
| Merz—Frei | 多年工作协作、政策相似、共同职位迁移 | 高工作信任；服从边界未知 |
| Merz—Warken | 公开称赞改革表现并升任总理府 | 高绩效信任；私人亲近未知 |
| Warken—Hagel | 州总书记经历、地方媒体称亲近盟友 | 可信州桥梁；不存在指挥关系证据 |
| Merz—Hoppermann | 两次由Merz推荐升任 | 高准入；她有独立于Merz的旧网络 |
| Frei—Spahn | Frei称关系紧密，并认为未来重返领导岗位“很可能” | 未完全组织性切割；网络规模未知 |
| Merz—Söder | 共同提名Frei；Söder同期公开力挺Merz | 当前合作信号高；长期竞争意图未知 |

“接受职务”“同台”或“公开支持”仍不能单独转成忠诚分。

## 7. Fritz Güntzler 为何拒绝交通部

这个黑箱已**大幅缩小**：NDR、Tagesspiegel、Zeit等一致报道，他最初接受、随后以自己缺少交通专业背景为由拒绝；公开比喻是守门员不应踢左边锋。**B，且理由有当事人公开归因**

可写入：继任失败来自候选人—岗位专业匹配判断，而不是已证实的反 Merz政治行动。私人考虑、家属因素或对政府前景判断仍未知。

## 8. 州总理是否形成协调集团

截止日前只看到**分散但方向相近**的信号：RLP围绕 Schnieder形成组织抗议；Kretschmer围绕 Schenderlein和东部代表性公开批评；NRW担忧失去联邦权重；Hessen提出代表性问题。没有同期共同声明、共同会议结果或分工证据。

9 月后来出现的 CDU州总理共同声明属于 cutoff 后结果，不能反推7月已有集团。baseline必须设为 `no_proven_coordinated_bloc`，sensitivity 才允许潜在协调形成。

## 9. Wüst 的联邦意图

### 新材料

- 7 月4日 NRW党代会，Wüst公开感谢并支持 Merz及联邦改革方案，称 Merz可以依靠 NRW州党。**A**
- 5月底/6月初已有全国和NRW媒体反复讨论 Wüst作为替代者；Wüst和Merz共同否认。WDR认为传闻的客观来源是党内对联邦表现不满与Wüst的结构条件，而非Wüst公开发动挑战。**B/C**
- 7月18日后 Spahn退出，WDR把它描述为Wüst通往Berlin少一个潜在阻挡者，但这是记者结构分析。**C**
- 2027年4月 NRW州选是明确的近期约束。**A**

### 可安全写入模型

- `federal_option_value`: 很高；`declared_challenge_intent`: 无。
- `near_term_priority_NRW_2027`: 高。
- baseline不允许由媒体“候选人”标签直接触发挑战；需要额外的党内需求、Merz失败事件和州内安全条件。

## 10. Söder 的联邦意图

### 新材料

- 7 月26日 ZDF夏季访谈中，Söder在换阁争议中公开支持 Merz。**A**
- CSU三名联邦部长未被调整；Söder、Dobrindt、Hoffmann仍是联盟委员会的 CSU三节点。**A/B**
- 同一访谈显示 Söder自身承受 Bavarian地方选举损失、Manfred Weber争议和党内接班议题压力，并公开称 Ilse Aigner是很好的联邦总统候选人。**A；与总理意图无直接等价关系**

### 可安全写入模型

- `current_coalition_support_signal`: 高。
- `CSU_personnel_control`与`coalition_committee_access`: 很高。
- `future_chancellor_intent`: 仍未知。不能把2021经历或高曝光度直接转换成当前参选规则。

## 11. 选举条件变量

仍是外生未来节点。7月底可观察的是选举日期、民调、候选人、地方组织压力；不能观察结果。每个选举应有独立 shock，而不是统一的“东部选举”随机数。

## 12. Spahn 剩余网络

### 新材料

- 正式党团主席和由职位带来的主席团资源归零，这是确定的。
- 7 月29日 Frei公开称两人关系紧密，并认为 Spahn未来再任领导角色“很可能”；Söder也作出相近表述。**A（表态存在）；不证明会实现**
- NRW仍是最大 CDU州籍议员群，Spahn保留联邦议席和长期卫生、经济及青年网络履历。**A；实际可调动性未知**

### 可安全写入模型

- 不应把 Spahn删出网络，也不能保留原来的党团控制。
- 可设 `formal_power=low`、`latent_personal_network=unknown_medium_range`、`near_term_public_cost=very_high`。
- 任何“很快复出”路径必须经过声誉修复和新组织入口，不得自动发生。

## 更新后的黑箱状态

| 黑箱 | 状态 |
|---|---|
| Merz—Frei关系 | **部分解决**：高政策/工作相似 + 高角色自主，私下边界未知 |
| Warken执行能力 | **部分解决**：经验和桥梁显著强于原先估计，新岗位授权认可未知 |
| Hoppermann派系位置 | **部分解决**：Merz准入高、跨翼网络明确、长期授权未知 |
| 党团第一经理 | **真实空缺，不应填补** |
| 体育国务部长 | **真实空缺；候选传闻不足** |
| 个人忠诚 | **只能关系化，不能统一量化** |
| Güntzler拒绝原因 | **大幅解决**：专业匹配是公开理由 |
| 州总理协调 | **未发现同期集团证据** |
| Wüst意图 | **结构资源明确，主观意图未解** |
| Söder意图 | **当前合作信号明确，未来意图未解** |
| 选举结果 | **原则上不可在截点观察** |
| Spahn网络 | **部分解决**：未被完全切割，实际动员力未知 |

## 本批新增关键来源

- [ZDF：Frei 7月29日长访谈](https://www.zdfheute.de/politik/deutschland/frei-fraktionsvorsitzender-union-cdu-fraktion-was-nun-100.html)
- [Tagesschau：Frei人物稿](https://www.tagesschau.de/inland/innenpolitik/thorsten-frei-portraet-100.html)
- [ZDF：Merz的信任圈](https://www.zdfheute.de/politik/deutschland/friedrich-merz-wem-vertraut-der-kanzler-100.html)
- [Tagesschau：Warken人物稿](https://www.tagesschau.de/inland/innenpolitik/warken-portraet-gesundheitsministerin-100.html)
- [SWR：Warken地方网络与直接选举资源](https://www.swr.de/swraktuell/baden-wuerttemberg/nina-warken-kanzleramtschefin-100.html)
- [NDR：Hoppermann履历、组织接口和临时授权](https://www.ndr.de/nachrichten/hamburg/hamburger-abgeordnete-hoppermann-zur-neuen-cdu-generalsekretaerin-gewaehlt%2Choppermann-102.html)
- [CDU/Röttgen团队公开信](https://www.cdu-deutschlands.de/sites/default/files/media/dokumente/211129-kandidatur-cdu-vorsitz-mitgliederbrief-team-norbert-roettgen.pdf)
- [NDR：Güntzler先接受后以专业理由拒绝](https://www.ndr.de/nachrichten/niedersachsen/goettinger-cdu-politiker-sagt-kanzler-merz-als-minister-zu-dann-ab%2Cguentzler-112.html)
- [WDR：7月4日 NRW党代会与Wüst对Merz支持](https://www1.wdr.de/politik/politik-in-nrw/merz-landesparteitag-cdu-100.amp)
- [WDR：Wüst联邦传闻的结构背景](https://www1.wdr.de/politik/politik-in-nrw/kommentar-wuest-merz-cdu-meschede-100.html)
- [ZDF：Söder 7月26日夏季访谈](https://www.zdfheute.de/video/berlin-direkt/berlin-direkt---sommerinterview-vom-26-juli-2026-102.html)
- [SWR：RLP党团的组织性抗议信号](https://www.swr.de/swraktuell/rheinland-pfalz/entlassung-verkehrsminister-schnieder-rlp-cdu-auf-konfrontationskurs-100.html)

