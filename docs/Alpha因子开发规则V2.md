# Alpha 因子开发规则

## 1. 定位

一个合格 Alpha 必须同时完成三件事：

1. 因子逻辑：能计算、能验证、能回测、能复现。
2. 未来函数检测：证明没有使用未来数据。
3. 结果可读：把算好的因子结果落地为 Parquet，让交易 agent 直接读取，不重复拉数和重算。

Alpha 只有一种交付形态：**一个自包含的 skill 目录**。结果文件写在运行目录的 `output/` 下，不再单独维护第二套「生产版 skill」。

Alpha 因子必须通过 PandaAI data 数据拉取库或项目指定数据源实现。不得使用来源不明、字段不稳定、个人临时整理的数据文件作为正式输入；如不确定应该使用哪个数据源、字段口径或权限配置，必须咨询项目工作人员后再开发。

完整链路：

```text
因子需求 -> job 任务文件 -> 开发 skill -> 因子计算 -> 验证回测 -> 发布为独立 skill 仓库 -> 交易 agent 调用
```

## 2. 适用范围

本规则适用于：

| 类型 | 示例 |
|---|---|
| 股票 Alpha | 龙虎榜资金、首板低吸、连板接力、板块轮动、涨停炸板回封 |
| 期货 Alpha | 会员持仓、席位分歧、主力席位一致性、持仓价格背离 |

## 3. 命名规则

| 元素 | 规则 | 示例 |
|---|---|---|
| skill 目录名 | `skill-{slug}` | `skill-five-day-momentum` |
| `slug` | 中文名称转英文，小写 + 连字符，3–6 词 | `five-day-momentum` |
| `SKILL.md` frontmatter `name` | 与目录名完全一致 | `skill-five-day-momentum` |
| 任务编号 | 只存在于 `jobs/` 文件名与 TaskSpec 中 | `jobs/A00 五日动量.txt` |

**禁止**使用 `alpha-{编号}`、`alpha-A00-*` 作为 skill 目录名或 `name` 字段。

## 4. Alpha 标准交付结构

与已过审 skill `public/skills/skill-dl-gnn-stock-graph` 同构，平铺无中间层级：

```text
skill-{slug}/
├── SKILL.md              ← 技能设计书（因子逻辑 + 验收要求）
├── README.md             ← 中文说明（含免责声明）
├── README.en.md          ← 英文说明
├── LICENSE               ← 完整 GPL-3.0 文本
├── INSTALL.md            ← 多平台安装指南
├── requirements.txt      ← Python 依赖声明
├── skill.json            ← Skill 元数据
├── CHANGELOG.md          ← 版本变更记录
├── scripts/
│   ├── factor.py         ← 因子计算主脚本
│   ├── validate.py       ← 未来函数 / 过拟合 / 样本外检查
│   └── backtest.py       ← IC、IR、分层收益、回撤、换手
├── tests/
│   └── test_factor.py
├── references/
│   └── data_guide.md     ← 数据源、字段、频率、清洗口径
├── agents/               ← 运行时适配器（社区审核硬性要求）
│   ├── cursor-rule.mdc
│   ├── portable-loader.md
│   └── openai.yaml
└── (运行期生成) output/
    ├── factor_YYYYMMDD.parquet
    └── ...
```

说明：

- 上表 8 个根层文件 + `scripts/` + `tests/` + `references/` + `agents/`（三个适配器）为硬性要求。
- **不设 `开发产物/` 与 `生产产物/` 目录，也不设独立的生产版 `SKILL.md`。**
- 因子结果文件写入 `output/`，必须加入 `.gitignore`；路径、字段、更新频率写在同一份 `SKILL.md` 的「输出结果」章节与 `references/data_guide.md` 中。
- `scripts/` 下的脚本命名按因子实际需要命名（如 `factor.py` / `backtest.py` 可合并为 `scan.py`），但必须有一个可独立运行的入口。

## 5. 必须文件与要求

| 文件 | 要求 |
|---|---|
| `SKILL.md` | 描述因子逻辑、适用场景、输入输出、调用方式、数据接口、验收要求、已知局限 |
| `README.md` | 中文交付文档：简介、`## ⚠️ 免责声明`、目录结构、快速开始、核心设计、验收状态、局限 |
| `README.en.md` | 英文版，内容与中文对应 |
| `LICENSE` | 完整 GPL-3.0 文本，不可用占位符 |
| `INSTALL.md` | 覆盖 Claude Code / Codex / Cursor / Hermes / OpenClaw 五个平台 |
| `requirements.txt` | Python 依赖声明 |
| `skill.json` | `name` 与目录名一致，含 `version` / `entrypoint` / `runtime` / `license` / `data_source` |
| `CHANGELOG.md` | 遵循 Keep a Changelog |
| `scripts/factor.py` | 因子计算主脚本，必须能独立运行 |
| `scripts/validate.py` | 必须包含未来函数、过拟合、样本外检查 |
| `scripts/backtest.py` | 输出 IC、ICIR、分层收益、最大回撤、换手等指标 |
| `tests/` | 覆盖正常输入、边界值、异常输入、无未来函数 |
| `references/data_guide.md` | 数据源、字段、频率、接口限制、清洗口径；必须说明 PandaAI data 或指定数据源的实现方式 |

## 6. Alpha SKILL.md 模板

````markdown
---
name: skill-{slug}
description: 当需要开发、计算、验证{因子名称}因子时，使用此 skill。支持数据获取、因子计算、未来函数检测、回测评估和信号输出。
tags: [quant, alpha, {stock/future}]
---

# {因子名称} Alpha

## 适用场景
- 当用户需要计算{因子名称}因子时
- 当用户需要验证该因子是否有效时

## 因子逻辑
- 核心假设：
- 计算公式：
- 排序方向：
- 适用市场：

## 数据接口（panda_data）
因子计算必须使用 PandaAI data 数据拉取库或项目指定数据源获取数据；如数据源、字段含义或权限配置不明确，先咨询项目工作人员。

| 接口 | 用途 | 关键字段 |
|---|---|---|

## 输出结果
| 字段 | 说明 |
|---|---|
| factor_value | 因子原始值 |
| score | 标准化评分 |
| signal | 交易信号 |

## 使用方式
```bash
python3 scripts/factor.py
python3 scripts/validate.py
python3 scripts/backtest.py
python3 -m pytest tests/ -v
```

## 验收要求
- 不允许未来函数
- 必须有样本外验证
- 必须有回测指标
- 必须使用 PandaAI data 数据拉取库或项目指定数据源实现
- `tests/` 全部通过

## 已知局限
- ...
````

## 7. Alpha 验收标准

Alpha 必须通过三层沙漏检测：

| 层级 | 检测内容 | 失败处理 |
|---|---|---|
| 第一层 | 未来函数：是否使用未来行情、未来公告、未来财务、不可得数据 | 直接退回重写 |
| 第二层 | 过拟合：训练集好、测试集明显衰减 | 简化因子，减少参数 |
| 第三层 | 样本外：跨年份、跨行情环境、跨品种验证 | 修改逻辑或降低评级 |

必须输出的回测指标：

| 指标 | 必须 |
|---|---:|
| IC / Rank IC | 是 |
| ICIR | 是 |
| 分层收益 | 是 |
| 多空收益 | 推荐 |
| 最大回撤 | 是 |
| 换手率 | 是 |
| 样本外表现 | 是 |
| 信号样例 | 是 |

数据实现要求：

- 因子输入必须来自 PandaAI data 数据拉取库或项目明确指定的数据源接口。
- `factor.py` 不得依赖个人本地临时文件、手工复制表格或来源不明的数据。
- `validate.py` 和 `backtest.py` 必须使用与 `factor.py` 一致的数据口径。
- 数据字段、复权方式、交易日历、合约换月、停牌处理等口径不明确时，必须咨询项目工作人员。

## 8. 结果 Parquet 字段标准

因子结果写入 `output/factor_YYYYMMDD.parquet`（或同类命名）。

| 字段 | 必须 | 说明 |
|---|---:|---|
| `trade_date` | 是 | 交易日期 |
| `asset_type` | 是 | `stock` / `future` |
| `ts_code` | 股票必须 | 股票代码 |
| `symbol` | 期货必须 | 期货合约 |
| `factor_name` | 是 | 因子名称（英文 slug） |
| `factor_value` | 是 | 因子原始值 |
| `score` | 是 | 标准化评分 |
| `rank` | 否 | 横截面排名 |
| `signal` | 是 | 交易信号 |
| `confidence` | 否 | 置信度 |
| `data_version` | 是 | 数据版本 |
| `update_time` | 是 | 结果生成时间 |

注意：字段 `factor_id`（如 `A00`）已废弃，任务编号不进入产物数据。

## 9. Alpha 数据质量要求

生成结果 Parquet 前必须检查：

| 检查项 | 要求 |
|---|---|
| 主键唯一 | 同一交易日、同一标的、同一因子不得重复 |
| 字段完整 | 必须字段不能为空 |
| 日期正确 | 必须是有效交易日 |
| 分数范围 | `score` 必须在约定范围内 |
| 信号合法 | `signal` 必须使用标准枚举 |
| 缺失处理 | 停牌、无数据、接口失败必须有处理口径 |
| 版本记录 | 每次生成必须写入 `data_version` |

## 10. Alpha 读取规则

交易 agent 使用 Alpha 时：

1. 先读取 `SKILL.md`。
2. 根据 `SKILL.md` 找到结果文件（`output/factor_YYYYMMDD.parquet`）。
3. 按 `trade_date`、`ts_code` / `symbol` 查询结果。
4. 默认使用最新有效交易日结果。
5. 若最新结果不存在，可回退最近有效交易日，但必须说明数据日期。
6. 不允许调用脚本临时重算。

## 11. Alpha 不合格情况

出现以下任一情况，Alpha 不得验收：

- 目录名带 `alpha-{编号}` 或任务编号前缀
- 存在 `开发产物/`、`生产产物/` 目录
- 缺少 8 个根层文件中的任一项
- `SKILL.md` 缺失，或 frontmatter `name` 与目录名不一致
- `factor.py` 不能运行
- 未通过未来函数检测
- 未提供回测结果
- 结果字段缺失或 `factor_id` 仍在使用
- agent 必须重新计算才能得到结果
- 因子计算未使用 PandaAI data 数据拉取库或项目指定数据源
- 数据源、字段口径不明确且未咨询项目工作人员
- `LICENSE` 不是完整 GPL-3.0
- `skill.json` 的 `license` 不是 `GPL-3.0-only`
- 缺少任一运行时适配器（`agents/cursor-rule.mdc` / `agents/portable-loader.md` / `agents/openai.yaml`）
- 说明文档包含敏感信息、收益承诺、投资建议或未经确认的官方背书
- `README.md` 缺少免责声明