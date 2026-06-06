# BUILD 开发与生产规则

## 1. 定位

BUILD 是工具，不是因子。

Alpha 直接面向交易信号，BUILD 面向可复用能力。BUILD 可以为 Alpha 服务，也可以为交易 agent 服务，例如数据清洗、复盘、新闻过滤、龙虎榜监控、IC 评估、仓位管理、调度器等。

BUILD 的交付要比 Alpha 更细，因为它可能有两种生产形态：

1. 调用型工具：agent 或 Alpha 调用 BUILD 的能力，得到即时处理结果。
2. 结果型工具：生产任务提前运行 BUILD，把结果落地为 `数据库.parquet`，agent 直接读取。

BUILD 必须通过 PandaAI data 数据拉取库、调用方传入的标准结构化数据，或项目指定数据源实现。不得使用来源不明、字段不稳定、个人临时整理的数据作为正式输入；如不确定应该使用哪个数据源、字段口径、接口权限或生产路径，必须咨询项目工作人员后再开发。

## 2. BUILD 完整链路

```text
工具需求 -> 开发 skill -> BUILD 实现 -> 测试验收 -> 生产部署 -> 调用或读取 -> agent / Alpha 使用
```

BUILD 不是所有项目都必须输出交易信号，但必须明确：

- 它解决什么工具问题。
- 谁会调用它。
- 输入是什么。
- 输出是什么。
- 输入是否来自 PandaAI data、调用方传入的标准结构化数据或项目指定数据源。
- 是否需要落地 `数据库.parquet`。
- 是否能被 Alpha 复用。

## 3. BUILD 类型

| 类型 | 说明 | 示例 |
|---|---|---|
| 数据处理型 | 清洗、合并、标准化、补全数据 | 数据清洗 BUILD、概念板块爬虫 |
| 分析报告型 | 输出结构化报告或解释 | 复盘 SKILL、新闻助手 |
| 监控预警型 | 定时扫描并输出异常或机会 | 早盘竞价扫描、龙虎榜监控 |
| 评估体系型 | 为 Alpha 做验证和评分 | IC 测试与因子评估体系 |
| 交易执行辅助型 | 输出仓位、止盈止损、冲突处理建议 | 仓位管理、多策略调度器 |

## 4. BUILD 最终交付物

每个 BUILD 必须有开发产物。是否需要生产产物，取决于它是否需要提前生成可复用结果。

```text
build-{编号}/
├── 开发产物/
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── build.py
│   │   └── test.py
│   ├── references/
│   │   └── api_guide.md
│   └── demo.mp4
└── 生产产物/
    ├── SKILL.md
    └── 数据库.parquet
```

说明：

- 调用型 BUILD 可以只部署 `SKILL.md + scripts/`，由 agent 或 Alpha 调用。
- 结果型 BUILD 必须额外交付 `SKILL.md + 数据库.parquet`。
- 如果 BUILD 输出会被很多 agent 重复查询，优先做成结果型 BUILD。

## 5. BUILD 开发产物要求

开发目录建议使用 Claude Code 标准 skill 结构：

```text
.claude/skills/build-{编号}/
├── SKILL.md
├── skill.json
├── scripts/
│   ├── build.py
│   └── test.py
├── references/
│   └── api_guide.md
└── demo.mp4
```

必须文件：

| 文件 | 要求 |
|---|---|
| `SKILL.md` | 描述 BUILD 功能、适用场景、输入输出、调用方式、是否可被 Alpha 调用 |
| `build.py` | BUILD 主脚本，必须提供标准入口 |
| `test.py` | 测试脚本，覆盖正常输入、异常输入、空数据 |
| `api_guide.md` | 数据接口、字段、外部依赖、调用示例；必须说明使用 PandaAI data、调用方传入的标准结构化数据或指定数据源的实现方式 |
| `demo.mp4` | 3-5 分钟跑通视频 |

## 6. BUILD 标准代码接口

BUILD 必须提供稳定入口：

```python
def run(input_data, config=None):
    """
    Args:
        input_data: 调用方传入的标准结构化数据，或 PandaAI data / 项目指定数据源返回的数据
        config: dict，可选配置

    Returns:
        dict、表格型数据或其他结构化输出
    """
```

必须同时提供输入校验：

```python
def validate_input(input_data):
    """
    缺字段、空数据、类型错误时必须抛出明确异常。
    """
```

## 7. BUILD 开发版 SKILL.md 模板

````markdown
---
name: build-{编号}
description: 当需要{BUILD功能}时，使用此 skill。该 BUILD 提供{工具能力}，可被 agent 或 Alpha 调用。
tags: [quant, build, development, {工具类型}]
---

# {BUILD名称}

## 工具定位
- 工具类型：
- 解决问题：
- 使用对象：agent / Alpha / 人工分析

## 适用场景
- 当用户需要{场景1}时
- 当 Alpha 需要{工具能力}时

## 输入
BUILD 输入必须来自 PandaAI data 数据拉取库、调用方传入的标准 Python 结构化数据，或项目指定数据源；如数据源、字段含义、接口权限或生产路径不明确，先咨询项目工作人员。

| 字段 | 类型 | 说明 |
|---|---|---|

## 输出
| 字段 | 类型 | 说明 |
|---|---|---|

## 调用方式
```python
from scripts.build import run

result = run(input_data, config=config)
```

## 可被 Alpha 调用
- 是 / 否
- 调用限制：
- 依赖数据：

## 是否需要生产结果
- 是否生成 `数据库.parquet`：是 / 否
- 如果是，说明更新频率和字段结构。

## 依赖
- PandaAI data
- numpy
- akshare / tushare / 其他
- 项目指定数据源：如不明确，咨询项目工作人员
````

## 8. BUILD 开发验收标准

| 检查项 | 标准 |
|---|---|
| 独立运行 | `python scripts/build.py` 可跑通 |
| 标准入口 | 必须提供 `run(input_data, config=None)` |
| 数据来源 | 必须使用 PandaAI data、调用方传入的标准结构化数据或项目指定数据源 |
| 输入校验 | 缺字段、空数据、非法类型必须报错 |
| 输出稳定 | 输出字段、类型、含义必须固定 |
| 可复用 | 能被 agent 或 Alpha 调用 |
| 文档完整 | `SKILL.md` 说明清楚适用场景和调用方式 |
| 视频证明 | 必须提供 `demo.mp4` |

## 9. BUILD 生产形态选择

BUILD 生产部署前，必须先判断属于哪种形态。

| 形态 | 适用情况 | 生产交付 |
|---|---|---|
| 调用型 BUILD | 轻量、实时、依赖调用方输入、结果不需要缓存 | `SKILL.md + scripts/` |
| 结果型 BUILD | 重计算、多人复用、定时扫描、结果需要缓存 | `SKILL.md + 数据库.parquet` |
| 混合型 BUILD | 既能即时调用，也有定时结果 | `SKILL.md + scripts/ + 数据库.parquet` |

示例：

| BUILD | 推荐形态 | 原因 |
|---|---|---|
| 数据清洗工具 | 调用型 | 依赖调用方传入数据 |
| 新闻助手 | 结果型 | 多人查询同一批新闻结果 |
| 龙虎榜监控 | 结果型 | 收盘后统一计算，agent 直接读 |
| IC 测试体系 | 混合型 | 可即时评估，也可沉淀每日评估结果 |
| 仓位管理 | 调用型或混合型 | 与账户实时状态有关 |

## 10. BUILD 生产版 SKILL.md 模板

结果型 BUILD 必须提供生产版 `SKILL.md`。

````markdown
---
name: build-{编号}-production
description: 当需要读取{BUILD名称}的生产结果时，使用此 skill。该 skill 读取已生成的 Parquet 结果，不重复执行重计算流程。
tags: [quant, build, production, {工具类型}]
---

# {BUILD名称}生产结果

## 工具定位
- 工具类型：
- 服务对象：agent / Alpha / 人工复盘
- 是否可被 Alpha 调用：

## 结果文件
- 文件路径：`数据库.parquet`
- 数据格式：Parquet
- 更新频率：
- 生成任务：

## 主键
- `trade_date`
- `build_id`
- `target_id`

## 字段说明
| 字段 | 类型 | 说明 |
|---|---|---|
| trade_date | date/string | 结果所属日期 |
| build_id | string | BUILD 编号 |
| build_name | string | BUILD 名称 |
| target_id | string | 作用对象，如股票、合约、策略、账户 |
| result_type | string | 结果类型 |
| result_value | string/float/int | 核心结果 |
| result_json | string | 复杂结构结果，JSON 字符串 |
| data_version | string | 数据版本 |
| update_time | datetime/string | 结果生成时间 |

## 读取规则
交易 agent 读取 `数据库.parquet`，按日期、对象和结果类型查询。

## 禁止行为
- 不允许多人查询时重复触发重计算。
- 不允许手工修改 Parquet 结果。
- 生产结果异常时必须提示数据日期和异常原因。
````

## 11. BUILD 结果 Parquet 字段标准

结果型 BUILD 的 `数据库.parquet` 推荐字段：

| 字段 | 必须 | 说明 |
|---|---:|---|
| `trade_date` | 视情况 | 结果所属日期 |
| `build_id` | 是 | BUILD 编号，例如 `B10` |
| `build_name` | 是 | BUILD 名称 |
| `target_id` | 否 | 股票、合约、策略、账户等对象 |
| `result_type` | 是 | `score` / `report` / `risk_flag` / `signal_list` 等 |
| `result_value` | 是 | 核心结果值 |
| `result_json` | 否 | 复杂结果使用 JSON 字符串 |
| `source_data_date` | 否 | 原始数据日期 |
| `data_version` | 是 | 数据版本 |
| `update_time` | 是 | 结果生成时间 |

## 12. BUILD 生产数据质量要求

| 检查项 | 要求 |
|---|---|
| 主键稳定 | 同一日期、同一 BUILD、同一对象、同一结果类型不得重复 |
| 字段完整 | 必须字段不能为空 |
| 类型稳定 | 同一字段不能今天是数字、明天是文本 |
| JSON 可解析 | `result_json` 必须是合法 JSON 字符串 |
| 版本记录 | 每次生成必须写入 `data_version` |
| 异常说明 | 生产失败必须有日志或错误标记 |

## 13. BUILD 与 Alpha 的关系

BUILD 是工具，Alpha 是信号或因子。

| 关系 | 要求 |
|---|---|
| Alpha 调用 BUILD | BUILD 必须提供稳定 `run()` 入口 |
| BUILD 生成结果供 Alpha 使用 | BUILD 结果字段必须写入 `SKILL.md` |
| 多个 Alpha 复用 BUILD | BUILD 输入输出必须保持向后兼容 |
| BUILD 逻辑变更 | 必须更新版本号和 `data_version` |

Alpha 不应复制 BUILD 逻辑。如果某个能力会被多个 Alpha 使用，应沉淀为 BUILD。

## 14. BUILD 不合格情况

出现以下任一情况，BUILD 不得验收或上线：

- 缺少 `SKILL.md`
- 没有标准 `run(input_data, config=None)` 入口
- 未使用 PandaAI data、调用方传入的标准结构化数据或项目指定数据源
- 数据源、字段口径、接口权限不明确且未咨询项目工作人员
- 输入输出字段不稳定
- 无测试脚本
- 无跑通视频
- 声称可被 Alpha 调用但无法 import
- 结果型 BUILD 缺少 `数据库.parquet`
- 生产版 `SKILL.md` 未说明 Parquet 路径
- agent 查询时必须重复触发重计算
- `result_json` 无法解析
