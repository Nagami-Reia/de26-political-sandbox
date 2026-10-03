# Political State System（PSS）

PSS 是人物的政治状态/压力—恢复系统。代码和报告不使用 “SAN” 一词，因为它会错误暗示精神健康判断。

核心边界：

> 人格是固定参数，状态是动态变量。事件不改写人格；它先改变状态，状态再调制人格在本轮决策中的有效权重。

## 数值规范

- 所有卡片参数、资源、关系、记忆强度和五项状态统一使用 `0.000–1.000`；
- 输入和对外 trace 最多保留三位小数；
- 正负效价、行动效果和关系变化属于方向性 delta，不是 0–1 参数，可以带符号；
- `sensitivity_map` 保存归一化敏感度：`0.000` 为最低、`1.000` 为最高；
- 计算时映射为 `0.500–1.500` 的冲击倍率。

## 五项动态状态

```text
energy
pressure
confidence
control
identity_integrity
```

- Energy：主动推动事务的剩余能力；
- Pressure：角色实际承受的环境压力；
- Confidence：对自己方法有效性的判断，不是支持率；
- Control：对本人偏好控制对象的掌控感；
- Identity Integrity：当前行为与自我政治身份的一致程度。

## 事件管线

```text
PoliticalEvent
  → calculate_impact(actor)
  → StateImpact
  → apply_impact(actor)
  → MemoryNode
```

基础冲击公式：

```text
sensitivity_multiplier = 0.500 + sensitivity
resistance_factor = 1.000 - stress_resistance
memory_multiplier = 1.000 + bounded_resonance

effective_damage = clamp01(
    event_severity
    × resistance_factor
    × sensitivity_multiplier
    × memory_multiplier
)
```

同一世界事件会为每个人生成不同的 `StateImpact`。事件本身不能直接修改角色状态。

## 记忆共振

记忆节点记录：事件标签、严重度、正负效价、每日衰减、未解决程度和已学习反应。新事件与旧记忆标签重叠时才产生共振。共振提高的是本次 actor-specific impact，不改写固定人格。

例如 Wüst 的 `2010_resignation` 记忆与新的 `loss_of_control`/`media_failure` 事件重叠时会放大冲击；普通的不相关政策新闻不会调用这段记忆。

## 恢复约束

自然时间推进只会：

- 恢复 Energy；
- 降低 Pressure；
- 衰减记忆强度和未解决程度。

它不会自动恢复：

- Confidence：需要成功或有效反馈；
- Control：需要重新取得资源、票数、程序或组织控制；
- Identity Integrity：需要身份一致行动及结果，且单次变化被严格限制。

## 状态调制人格

卡片不保存带符号的 “压力加减值”。它保存目标和调制强度，两者都在 0–1：

```text
pressure_risk_target
pressure_risk_strength
pressure_ambition_target
pressure_ambition_strength
low_control_control_strength
```

例如压力升高时：

- Merz 的有效 Ambition/Risk 向更高目标移动；
- Wüst 的有效 Risk 向较低目标移动，过程控制偏好的有效强度上升；
- 固定人格参数本身始终不被覆盖。

## 与自由行动决策连接

PSS 只提供本轮有效人格参数和状态修正。最终行动仍由六项评分决定：

```text
goal_alignment
+ resource_feasibility
+ identity_consistency
+ current_state_modifier
+ memory_modifier
+ risk_calculation
```

行动执行后由世界、投票、谈判或舆论模块结算结果，再通过 PSS 写回状态和记忆。

主要实现：

- `political_state_system.py`
- `persona_v2.py`
- `free_agent_game.py`
- `personality_cards_2026/cards_pss.json`

