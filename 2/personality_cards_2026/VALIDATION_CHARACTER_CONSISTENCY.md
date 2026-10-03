# 人物卡可运行性与角色一致性检查

检查日期：2026-09-19。对象为基础牌组与2026-09扩展叠加后的全部16张人物卡。

## 检查内容

1. **结构完整性**：价值层级、控制偏好、五种冲突策略、情境风险、六类资源、PSS及来源ID均可解析。
2. **共享菜单辨识度**：16人面对同一组17个合法行动及一个“无资金、纯表演、高不确定性”行动；每人应选择与其证据化核心逻辑一致的行动。
3. **压力保持性**：向每人施加与其最高敏感项匹配的0.900严重压力事件后重新决策。压力可以改变有效参数，但不应把人物身份逻辑完全擦除。
4. **自由选择边界**：检查不规定人物在真实场景必须选择该行动；它只排查数值映射错误、标签错接和明显OOC漂移。

## 结果

| Actor | 基线选择 | 相对次优项分差 | 高压后选择 | 结果 |
|---|---|---:|---|---|
| Merz | strategic_reform_direction | 52.014 | strategic_reform_direction | PASS |
| Frei | counted_majority_operation | 51.546 | counted_majority_operation | PASS |
| Wuest | acceptance_verified_coalition | 57.018 | acceptance_verified_coalition | PASS |
| Soeder | bavarian_apparatus_signal | 45.769 | bavarian_apparatus_signal | PASS |
| Linnemann | measurable_implementation_mechanism | 45.737 | measurable_implementation_mechanism | PASS |
| Guenther | broad_majority_consensus | 49.756 | broad_majority_consensus | PASS |
| Rhein | mandate_backed_state_delivery | 50.281 | mandate_backed_state_delivery | PASS |
| Dobrindt | staged_enforcement_package | 50.266 | staged_enforcement_package | PASS |
| Wadephul | alliance_legal_intersection | 53.930 | alliance_legal_intersection | PASS |
| Evers | budgeted_administrative_rescue | 50.377 | budgeted_administrative_rescue | PASS |
| Schulze | regional_delivery_program | 45.278 | regional_delivery_program | PASS |
| Kretschmer | territorial_variable_majority | 50.748 | territorial_variable_majority | PASS |
| Warken | stakeholder_passage_package | 51.703 | stakeholder_passage_package | PASS |
| Baer | hightech_flagship_coalition | 51.133 | hightech_flagship_coalition | PASS |
| Hoppermann | party_trust_and_process_audit | 50.208 | party_trust_and_process_audit | PASS |
| Reiche | executive_industrial_reset | 54.853 | executive_industrial_reset | PASS |

测试实现位于`kfrage_model/test_persona_expansion.py`，并进入全项目测试发现流程。当前全套55项测试通过。

## 能确认与不能确认

可以确认：所有16张卡能实际加载、评分、选择和响应PSS事件；在共享菜单中具有清晰区分；明显违反自身核心价值且无执行路径的动作不会被选中；高压不会导致标签接错或人格完全反转。

不能据此确认：所有未来真实选择都必然“符合我们对人物的理解”。边缘情境中的OOC只能通过新的真实行为、对抗性反事实菜单和回测继续发现。尤其Hoppermann联邦党务任期短、Schulze败选后的状态尚不稳定，这两张卡仍需较高频率更新。
