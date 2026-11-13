# 🐼 量枢学院 · Panda Trading

> 基于 Claude Code 多 Agent 协作框架的量化交易工具库 —— 纯 Python · 零框架依赖 · Skill 架构

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

---

## 📖 简介

**量枢学院（Panda Trading）** 是一个模块化的量化交易工具开发平台，采用 **Skill 原子能力** + **多 Agent 协作** 架构，将交易系统的核心能力拆分为独立的、可复用的 BUILD 工具和 Alpha 因子。

项目默认采用 **纯 Python 标准库** 实现，不依赖 pandas / numpy 等第三方框架（除非任务需求明确指定），确保每个 Skill 轻量、可独立运行、可被 Agent 或 Alpha 自由调用。

本仓库为 **Agent 型仓库**（`agent-for-liangshuyuan-tasks`），遵循 QuantSkills 社区规则。声明文件见 `AGENTS.md`。

### 核心理念

| 理念 | 说明 |
|---|---|
| **Skill 即工具** | 每个子目录是一个独立的交易 skill，可独立运行、独立测试、独立发布 |
| **BUILD 为 Alpha 服务** | BUILD 是工具层，Alpha 是信号层；Alpha 调用 BUILD，不复制 BUILD 逻辑 |
| **Agent 协作** | 多 Agent 分工：需求分析 → 开发 → 测试 → 发布，全流程自动化 |
| **零框架依赖** | 默认纯 Python 标准库实现，确保任意环境可直接运行 |

### 维护者

- 段绪勇 [https://github.com/duanyong](https://github.com/duanyong)
- 社区维护：QuantSkills (https://github.com/quantskills)

---

## 🏗️ 系统架构

### Skill 体系

```
skills/
└── panda-builder/          ← 脚手架 Skill：创建/验收 skill 的统一规范
```

### 任务分类

| 前缀 | 类型 | 目录 | 说明 |
|---|---|---|---|
| **B** | BUILD 工具 | `src/skills/` | 数据处理、仓位管理、监控预警、复盘分析等 |
| **A** | Alpha 因子 | `src/skills/` | 股票/期货 Alpha 信号与因子 |

任务编号（如 `B12`、`A00`）只用于任务路由和溯源，**不进入 skill 名称**。所有 skill 统一命名为 `skill-{slug}`。

### 多 Agent 协作 —— 从任务到发布全自动

把任务需求写成 `.txt` 放入 `jobs/` 目录，Agent 系统会自动完成**分析 → 路由 → 开发 → 测试 → 发布**全流程。文件名前缀决定路由规则：

```
jobs/B{编号} {名称}.txt          ← 用户只需写这个
     │
     ▼
┌──────────────────┐
│  需求分析 Agent   │  读取任务文件 → 识别 B/A 类型 → 输出结构化 TaskSpec
└──────┬───────────┘
       │ TaskSpec（含歧义项则先向人类澄清）
       ▼
┌─────────────┐
│  主 Agent   │──── B 类 → Build 开发 Agent + panda-builder
└──────┬──────┘──── A 类 → Alpha 开发 Agent
       │
       │ ←── DevReport（skill 路径 + 自检报告）
       ▼
┌─────────────┐
│  测试 Agent  │  生成用例 → 运行 → TestReport
└──────┬──────┘
       │ ←── 通过 ✓ / 失败（Bug 回流，最多 3 轮）
       ▼
┌─────────────┐
│  发布 Agent  │  创建 GitHub 仓库 skill-{slug} → 复制 skill 产物
│              │  → 补充合规文件 → 推送至 quantskills 组织
└──────┬──────┘
       │
       ▼
   ✅ 任务完成 + 已发布（遵循 QuantSkills 社区规则）
```

| Agent | 一句话职责 | 文件 |
|---|---|---|
| **需求分析** | 读 `jobs/*.txt`，输出结构化 TaskSpec，标记歧义 | `agents/analyst-agent/SKILL.md` |
| **Build/Alpha 开发** | 按 TaskSpec 编码，输出可运行的 `skill-{slug}` 目录 | `agents/dev-{build,alpha}-agent/SKILL.md` |
| **测试** | 生成测试用例，验证输入输出，报告 Bug | `agents/test-agent/SKILL.md` |
| **发布** | 发布为 quantskills 独立仓库并推送 | `agents/publish-agent/SKILL.md` |

---

## 📂 项目结构

```
panda-trading/
├── README.md                       ← 本文件（中文）
├── README.en.md                    ← 英文版
├── LICENSE                         ← GPL-3.0
├── AGENTS.md                       ← Agent 声明文件（QuantSkills 社区规则）
├── CLAUDE.md                       ← Claude Code 项目规范（Agent 协作、Skill 架构、数据接口定义）
│
├── agents/                         ← 多 Agent 协作规范
│   ├── TASK_REQUIREMENTS.md        ←   Agent 分工、流程、信息传递格式
│   ├── main-agent/SKILL.md         ←   主 Agent 调度规则
│   ├── analyst-agent/SKILL.md      ←   需求分析 Agent 规则
│   ├── dev-build-agent/SKILL.md    ←   Build 开发 Agent 规则
│   ├── dev-alpha-agent/SKILL.md    ←   Alpha 开发 Agent 规则
│   ├── test-agent/SKILL.md         ←   测试 Agent 规则
│   └── publish-agent/SKILL.md      ←   发布 Agent 规则（遵循 QuantSkills 社区规则）
│
├── skills/                         ← 项目本地 Skill
│   └── panda-builder/              ←   skill 脚手架与验收规范
│       ├── SKILL.md
│       └── skill.json
│
├── docs/                           ← 开发规则文档
│   ├── BUILD开发规则V2.md           ←   BUILD 工具开发全流程规范
│   └── Alpha因子开发规则V2.md       ←   Alpha 因子开发规范
│
├── jobs/                           ← 原始任务需求
│
├── public/                         ← 发布工作区（.gitignore 排除，不入库）
│   └── skills/
│       └── skill-dl-gnn-stock-graph/   ← 已过审 skill 参考实现
│
└── src/
    └── skills/                     ← 开发产物（所有产出必须放此处）
        └── skill-{slug}/           ←   每个任务一个自包含 skill 目录
```

### 单个 skill 的标准结构

```
skill-{slug}/
├── SKILL.md              ← 技能设计书（必填）
├── README.md             ← 中文说明，含 ## ⚠️ 免责声明（必填）
├── README.en.md          ← 英文说明（必填）
├── LICENSE               ← 完整 GPL-3.0 文本（必填）
├── INSTALL.md            ← 多平台安装指南（必填）
├── requirements.txt      ← Python 依赖声明（必填）
├── skill.json            ← Skill 元数据（必填）
├── CHANGELOG.md          ← 版本变更记录（必填）
├── scripts/              ← 实现代码（必填）
├── tests/                ← 单元测试（必填）
├── references/           ← 接口与边界文档（必填）
└── agents/               ← 运行时适配器（必填）
    ├── cursor-rule.mdc      ← Cursor
    ├── portable-loader.md   ← Hermes / OpenClaw
    └── openai.yaml          ← Codex / OpenClaw
```

> **本结构没有 `开发产物/`、`生产产物/` 目录，也没有独立的生产版 `SKILL.md`。** 结果型 skill 的运行结果写入 `output/`（`.gitignore` 排除），路径与字段写在同一份 `SKILL.md` 与 `references/` 中。

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 默认无第三方依赖（标准库即可运行；个别 skill 按 `requirements.txt` 安装）

### 运行 skill

```bash
# 在 skill 目录内
cd src/skills/skill-{slug}
python3 scripts/build.py
python3 -m pytest tests/ -v
```

### 安装到 Claude Code

```bash
cp -R src/skills/skill-{slug} ~/.claude/skills/
# 然后在 Claude Code 中调用：/skill-{slug}
```

### 作为模块调用

```python
import sys
sys.path.insert(0, "src/skills/skill-{slug}")
from scripts.build import run

order = run({
    "code": "600036", "pnl_pct": 0.015,
    "sellable_qty": 800, "locked_qty": 0,
    "price": 10.0, "available_cash": 100000, "time": "10:00",
})

orders = run([...])   # 批量：传入 list
```

---

## 📐 开发规范

### skill 命名

| 元素 | 规则 | 示例 |
|---|---|---|
| 目录名 | `skill-{slug}` | `skill-intraday-position-manager` |
| slug | 中文名转英文，小写 + 连字符，3–6 词 | `auto-stop-loss-take-profit` |
| `SKILL.md` 的 `name` | 与目录名完全一致 | `skill-intraday-position-manager` |

**禁止**使用 `build-{编号}`、`build-B12-*`、`alpha-A00-*` 等带任务编号的命名。

### 代码接口

`scripts/build.py` 必须提供：

```python
def run(input_data, config=None): ...
def validate_input(input_data): ...   # 缺字段/空数据/类型错误必须抛异常
```

### 发布规范（QuantSkills 社区规则）

社区审核硬性要求：

| 规则 | 要求 |
|---|---|
| `english-readme` | 必须有 `README.en.md`，`README.md` 保持中文优先 |
| `license` | 必须有 `LICENSE`（GPLv3 全文），元数据声明 `GPL-3.0-only` |
| `repository-name` | 仓库名全小写，`skill-` 或 `agent-` 前缀 |
| `runtime-adapter` | 必须有 `agents/cursor-rule.mdc`、`agents/portable-loader.md`、`agents/openai.yaml` |

说明文档不得包含敏感信息、收益承诺、投资建议或未经确认的官方背书。详见 `skills/panda-builder/SKILL.md` §8。


发布后的仓库与 `public/skills/skill-dl-gnn-stock-graph` 完全同构：

```
skill-{slug}/                    ← GitHub 独立仓库
├── SKILL.md                     ← 根层级声明（frontmatter name 与仓库名一致）
├── README.md                    ← 中文交付文档（含免责声明）
├── README.en.md                 ← 英文交付文档
├── LICENSE                      ← 完整 GPL-3.0
├── INSTALL.md                   ← 多平台安装指南（Claude Code/Codex/Cursor/Hermes/OpenClaw）
├── requirements.txt
├── skill.json
├── CHANGELOG.md
├── .gitignore                   ← 排除 output/ 等运行产物
├── .github/workflows/validate.yml  ← CI：pytest
├── scripts/
├── tests/
├── references/
├── agents/                      ← 运行时适配器（必填）：cursor-rule.mdc / portable-loader.md / openai.yaml
└── config/                      ← （可选）集中式参数
```

### 调仓指令标准数据结构

```python
{
    "code": str,         # 品种代码
    "pnl_pct": float,    # 浮盈亏 %（小数形式：0.01 = +1%）
    "current_qty": int,  # 当前总持仓
    "time": str,         # HH:MM
    "action": str,       # "buy" / "sell" / "hold"
    "qty_change": int,   # 正=加仓，负=减仓
    "target_qty": int,   # 目标持仓
    "reason": str,       # 触发原因
}
```

### A股交易约束

- 最小交易单位 100 股，加仓/减仓数量向下取整到 100 的整数倍
- 收盘时间 15:00，强平窗口默认收盘前 15 分钟（14:45）
- T+1：当日新建仓位锁定，不可当日卖出

---

## 📄 License

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](./LICENSE)

本项目以 GPL-3.0 License 开源。Copyright (C) 2026 QuantSkills.

> 所有已发布 skill 独立仓库同样使用 GPL-3.0，遵循 QuantSkills 社区规则。