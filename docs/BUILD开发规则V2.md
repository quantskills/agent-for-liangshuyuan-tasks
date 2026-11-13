# BUILD 开发规则

## 1. 定位

BUILD 是工具，不是因子。

Alpha 直接面向交易信号，BUILD 面向可复用能力。BUILD 可以为 Alpha 服务，也可以为交易 agent 服务，例如数据清洗、复盘、新闻过滤、龙虎榜监控、IC 评估、仓位管理、调度器等。

BUILD 只有一种交付形态：**一个自包含的 skill 目录**。调用型与结果型的区别只在于运行结果落不落盘，不改变交付结构。

BUILD 必须通过 PandaAI data 数据拉取库、调用方传入的标准结构化数据，或项目指定数据源实现。不得使用来源不明、字段不稳定、个人临时整理的数据作为正式输入；如不确定应该使用哪个数据源、字段口径、接口权限或生产路径，必须咨询项目工作人员后再开发。

## 2. BUILD 完整链路

```text
工具需求 -> job 任务文件 -> 开发 skill -> 运行验证 -> 测试验收 -> 发布为独立 skill 仓库 -> agent / Alpha 调用
```

BUILD 不是所有项目都必须输出交易信号，但必须明确：

- 它解决什么工具问题。
- 谁会调用它。
- 输入是什么。
- 输出是什么。
- 输入是否来自 PandaAI data、调用方传入的标准结构化数据或项目指定数据源。
- 运行结果是否需要落盘；若需要，落在哪里、字段是什么、更新频率如何。
- 是否能被 Alpha 复用。

## 3. BUILD 类型

| 类型 | 说明 | 示例 |
|---|---|---|
| 数据处理型 | 清洗、合并、标准化、补全数据 | 数据清洗 BUILD、概念板块爬虫 |
| 分析报告型 | 输出结构化报告或解释 | 复盘 SKILL、新闻助手 |
| 监控预警型 | 定时扫描并输出异常或机会 | 早盘竞价扫描、龙虎榜监控 |
| 评估体系型 | 为 Alpha 做验证和评分 | IC 测试与因子评估体系 |
| 交易执行辅助型 | 输出仓位、止盈止损、冲突处理建议 | 仓位管理、多策略调度器 |

## 4. 命名规则

| 元素 | 规则 | 示例 |
|---|---|---|
| skill 目录名 | `skill-{slug}` | `skill-intraday-position-manager` |
| `slug` | 中文名称转英文，小写 + 连字符，3–6 词 | `auto-stop-loss-take-profit` |
| `SKILL.md` frontmatter `name` | 与目录名完全一致 | `skill-intraday-position-manager` |
| 任务编号 | 只存在于 `jobs/` 文件名与 TaskSpec 中 | `jobs/B12 日内仓位动态管理.txt` |

**禁止**使用 `build-{编号}`、`build-B12-*`、`B12-*` 作为 skill 目录名或 `name` 字段。

## 5. BUILD 标准交付结构

每个 BUILD skill 平铺存放，无中间层级，与已过审 skill `public/skills/skill-dl-gnn-stock-graph` 同构：

```text
skill-{slug}/
├── SKILL.md              ← 技能设计书
├── README.md             ← 中文说明（含免责声明）
├── README.en.md          ← 英文说明
├── LICENSE               ← 完整 GPL-3.0 文本
├── INSTALL.md            ← 多平台安装指南
├── requirements.txt      ← Python 依赖声明
├── skill.json            ← Skill 元数据
├── CHANGELOG.md          ← 版本变更记录
├── scripts/
│   ├── build.py          ← 主脚本，必须提供 run() 与 validate_input()
│   └── ...
├── tests/
│   ├── test_*.py         ← pytest 用例
│   └── selfcheck.py      ← 可选，无第三方依赖的自测脚本
├── references/
│   └── api_guide.md
└── agents/               ← 运行时适配器（社区审核硬性要求）
    ├── cursor-rule.mdc      ← Cursor
    ├── portable-loader.md   ← Hermes / OpenClaw
    └── openai.yaml          ← Codex / OpenClaw
```

可选：`config/`（集中式参数）、`.github/workflows/validate.yml`（CI）。

说明：

- 上表 8 个根层文件 + `scripts/` + `tests/` + `references/` + `agents/`（三个适配器）为硬性要求，缺一不可。
- **不设 `开发产物/` 与 `生产产物/` 目录，也不设独立的生产版 `SKILL.md`。**
- 结果型 BUILD 的结果文件写入运行目录下的 `output/`，并在同一份 `SKILL.md` 的「输出」章节与 `references/` 中说明路径、字段、更新频率。`output/` 必须加入 `.gitignore`。

## 6. 产出形态（不改变交付结构）

| 形态 | 适用情况 | 运行结果 | 交付 |
|---|---|---|---|
| 调用型 | 轻量、实时、依赖调用方输入 | 直接 `return` 给调用方，不落盘 | 标准交付结构 |
| 结果型 | 重计算、多人复用、定时扫描 | 写入 `output/` | 标准交付结构 + `output/` 说明 |
| 混合型 | 既能即时调用，也有定时结果 | 两者都有 | 标准交付结构 |

示例：

| BUILD | 推荐形态 | 原因 |
|---|---|---|
| 数据清洗工具 | 调用型 | 依赖调用方传入数据 |
| 新闻助手 | 结果型 | 多人查询同一批新闻结果 |
| 龙虎榜监控 | 结果型 | 收盘后统一计算，agent 直接读 |
| IC 测试体系 | 混合型 | 可即时评估，也可沉淀每日评估结果 |
| 仓位管理 | 调用型 | 与账户实时状态有关 |

结果型结果文件（`output/`）的推荐字段：

| 字段 | 必须 | 说明 |
|---|---:|---|
| `trade_date` | 视情况 | 结果所属日期 |
| `build_name` | 是 | skill 名称，如 `skill-intraday-position-manager` |
| `target_id` | 否 | 股票、合约、策略、账户等对象 |
| `result_type` | 是 | `score` / `report` / `risk_flag` / `signal_list` 等 |
| `result_value` | 是 | 核心结果值 |
| `result_json` | 否 | 复杂结果使用 JSON 字符串 |
| `source_data_date` | 否 | 原始数据日期 |
| `data_version` | 是 | 数据版本 |
| `update_time` | 是 | 结果生成时间 |

注意：字段 `build_id`（如 `B12`）已废弃，任务编号不进入产物数据。

## 7. BUILD 必须文件与要求

| 文件 | 要求 |
|---|---|
| `SKILL.md` | 描述适用场景、输入输出、调用方式、数据来源、验收要求、已知局限、是否可被 Alpha 调用 |
| `README.md` | 中文交付文档：简介、`## ⚠️ 免责声明`、目录结构、快速开始、核心设计、验收状态、局限 |
| `README.en.md` | 英文版，内容与中文对应 |
| `LICENSE` | 完整 GPL-3.0 文本，不可用占位符 |
| `INSTALL.md` | 覆盖 Claude Code / Codex / Cursor / Hermes / OpenClaw 五个平台 |
| `requirements.txt` | Python 依赖声明；零三方依赖时写明标准库 |
| `skill.json` | `name` 与目录名一致，含 `version` / `entrypoint` / `runtime` / `license` / `data_source` |
| `CHANGELOG.md` | 遵循 Keep a Changelog |
| `scripts/build.py` | 主脚本，必须提供标准入口 |
| `tests/` | 覆盖正常输入、边界值、异常输入 |
| `references/api_guide.md` | 数据接口、字段、外部依赖、调用示例；必须说明数据源实现方式 |

## 8. BUILD 标准代码接口

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

## 9. BUILD SKILL.md 模板

````markdown
---
name: skill-{slug}
description: 当需要{BUILD功能}时，使用此 skill。该 BUILD 提供{工具能力}，可被 agent 或 Alpha 调用。
tags: [quant, build, {工具类型}]
---

# {BUILD名称}

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

## 数据来源
- PandaAI data / 调用方传入标准结构化数据 / 项目指定数据源

## 依赖
- Python 标准库（或列明三方依赖）

## 验收要求
- 可独立运行
- `tests/` 全通过
- 输出字段稳定

## 已知局限
- ...

## 可被 Alpha 调用
- 是 / 否
- 调用限制：
````

## 10. BUILD 验收标准

| 检查项 | 标准 |
|---|---|
| 命名 | 目录名 `skill-{slug}`，不含任务编号 |
| 结构 | 8 个根层文件 + `scripts/` + `tests/` + `references/` + `agents/`（cursor-rule.mdc / portable-loader.md / openai.yaml）齐全 |
| 独立运行 | `python3 scripts/build.py` 可跑通 |
| 标准入口 | 必须提供 `run(input_data, config=None)` |
| 数据来源 | 必须使用 PandaAI data、调用方传入的标准结构化数据或项目指定数据源 |
| 输入校验 | 缺字段、空数据、非法类型必须报错 |
| 输出稳定 | 输出字段、类型、含义必须固定 |
| 可复用 | 能被 agent 或 Alpha 调用 |
| 文档完整 | `SKILL.md` 说明清楚适用场景和调用方式；README 含免责声明 |
| 测试 | `tests/` 全部通过 |

## 11. BUILD 与 Alpha 的关系

BUILD 是工具，Alpha 是信号或因子。

| 关系 | 要求 |
|---|---|
| Alpha 调用 BUILD | BUILD 必须提供稳定 `run()` 入口 |
| 多个 Alpha 复用 BUILD | BUILD 输入输出必须保持向后兼容 |
| BUILD 逻辑变更 | 必须更新 `CHANGELOG.md` 与 `skill.json` 的 `version` |

Alpha 不应复制 BUILD 逻辑。如果某个能力会被多个 Alpha 使用，应沉淀为 BUILD。

## 12. BUILD 不合格情况

出现以下任一情况，BUILD 不得验收或上线：

- 目录名带 `build-{编号}` 或任务编号前缀
- 存在 `开发产物/`、`生产产物/` 目录
- 缺少 8 个根层文件中的任一项
- 缺少 `SKILL.md`，或 frontmatter `name` 与目录名不一致
- 没有标准 `run(input_data, config=None)` 入口
- 未使用 PandaAI data、调用方传入的标准结构化数据或项目指定数据源
- 数据源、字段口径、接口权限不明确且未咨询项目工作人员
- 输入输出字段不稳定
- 无 `tests/` 或无通过记录
- 声称可被 Alpha 调用但无法 import
- `LICENSE` 不是完整 GPL-3.0
- `skill.json` 的 `license` 不是 `GPL-3.0-only`
- 缺少任一运行时适配器（`agents/cursor-rule.mdc` / `agents/portable-loader.md` / `agents/openai.yaml`）
- 说明文档包含敏感信息、收益承诺、投资建议或未经确认的官方背书
- `README.md` 缺少免责声明