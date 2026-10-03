# “箱”政治模拟器便携包：快速开始

本包只需要 Python 3.11 或更高版本，不需要安装第三方库。

请在解压后的目录中运行命令。所有命令都以：

```bash
python3 -m kfrage_model
```

开头。

## 1. 先检查包是否完整

```bash
python3 -m kfrage_model validate --pretty
python3 -m unittest discover -s kfrage_model -p 'test_*.py'
```

## 2. 查看可用人物与人物卡

```bash
python3 -m kfrage_model actors
python3 -m kfrage_model card Merz --pretty
python3 -m kfrage_model card Frei --pretty
```

## 3. 让一个人物处理自定义决策

包内提供了示例请求：

```bash
python3 -m kfrage_model decide Merz \
  --request examples/decision_request.json --pretty
```

查看完整JSON协议和可用字段：

```bash
python3 -m kfrage_model protocol
```

另一个AI只需要修改请求中的：

- `history`：此前发生的事件和行动后果；
- `resources`：人物当前可使用的资源；
- `goals`：该节点的即时目标；
- `scene_tags`：情境标签；
- `actions`：本轮允许考虑的行动。

人物卡会评价所有行动，并返回选择、逐项评分、PSS状态和关系状态。

## 4. 启动持续会话

`play`模式使用逐行JSON协议，适合另一个AI或程序连续推动世界：

```bash
python3 -m kfrage_model play Merz < examples/session.jsonl
```

支持的命令包括：

```text
event
decide
outcome
advance_time
state
quit
```

在持续会话中，人物的PSS、记忆和关系会保留到下一条命令。

## 5. 运行内置情景

列出情景：

```bash
python3 -m kfrage_model scenarios
```

运行当前德俄风险箱庭：

```bash
python3 -m kfrage_model run-scenario germany-russia-risk-2026 \
  --seed 20261001 --runs 10000
```

不提供种子时，程序会生成种子并写入输出，以便以后重现。

## 6. 交给另一个GPT或AI时怎么说

可以把整个ZIP交给它，并使用下面这段提示：

```text
请先阅读 PORTABLE_QUICKSTART_CN.md 和 kfrage_model/MODEL_OVERVIEW_CN.md。
不要直接编造人物反应。使用 `python3 -m kfrage_model actors` 查看人物，
使用 `python3 -m kfrage_model protocol` 读取接口，然后通过 decide 或 play
运行决策。世界事实、人物信念、法律检查和行动结果必须保持分离。
随机项只表示外部偶发性或不可观测信息，不允许随机改写人格。
所有运行请保存种子，并明确区分模型路径比例与现实概率。
```

## 7. 主要说明文件

- `kfrage_model/MODEL_OVERVIEW_CN.md`：模型整体介绍；
- `kfrage_model/ARCHITECTURE.md`：架构与模块边界；
- `kfrage_model/personality_cards_2026/PERSONA_V2.md`：人物卡；
- `kfrage_model/personality_cards_2026/POLITICAL_STATE_SYSTEM.md`：PSS；
- `kfrage_model/DECISION_SPACE.md`：行动空间生成；
- `kfrage_model/NARRATIVE_MEDIA.md`：媒体与叙事竞争；
- `kfrage_model/HISTORICAL_DYNAMICS.md`：历史因果与事件生成。

## 8. 输出解释

模拟产生的路径比例是给定环境、参数和随机扰动下的模型分布，不是现实世界预测概率。若要比较人物与制度影响，应分别运行：

- 相同环境、不同人物卡；
- 相同人物卡、不同制度或资源条件；
- 相同设置、不同随机种子；
- 固定种子的确定性复现。

