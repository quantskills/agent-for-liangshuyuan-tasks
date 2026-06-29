# 🐼 量枢学院 · Panda Trading

> 基于 Claude Code 多 Agent 协作框架的量化交易工具库 —— 纯 Python · 零框架依赖 · Skill 架构

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

---

## 📖 简介

**量枢学院（Panda Trading）** 是一个模块化的量化交易工具开发平台，采用 **Skill 原子能力** + **多 Agent 协作** 架构，将交易系统的核心能力拆分为独立的、可复用的 BUILD 工具和 Alpha 因子。

项目采用 **纯 Python 标准库** 实现，不依赖 pandas / numpy 等第三方框架（除非任务需求明确指定），确保每个 Skill 轻量、可独立运行、可被 Agent 或 Alpha 自由调用。

本仓库为 **Agent 型仓库**（`agent-for-liangshuyuan-tasks`），遵循 QuantSkills 社区规则。声明文件见 `AGENTS.md`。

### 核心理念

| 理念 | 说明 |
|---|---|
| **Skill 即工具** | 每个子目录是一个独立的交易 BUILD skill，可独立运行、独立测试、独立部署 |
| **BUILD 为 Alpha 服务** | BUILD 是工具层，Alpha 是信号层；Alpha 调用 BUILD，不复制 BUILD 逻辑 |
| **Agent 协作** | 多 Agent 分工：需求分析 → 开发 → 测试 → 发布，全流程自动化 |
| **零框架依赖** | 默认纯 Python 标准库实现，确保任意环境可直接运行 |

### 维护者

- 段绪勇 [https://github.com/duanyong](https://github.com/duanyong) <hiduan@qq.com>
- 社区维护：QuantSkills (https://github.com/quantskills)

---

## 🏗️ 系统架构

### Skill 体系

```
skills/
└── panda-builder/          ← 脚手架 Skill：创建/验收 BUILD skill 的统一规范
```

### 任务分类

| 前缀 | 类型 | 目录 | 说明 |
|---|---|---|---|
| **B** | BUILD 工具 | `src/build/` | 数据处理、仓位管理、监控预警、复盘分析等 |
| **A** | Alpha 因子 | `src/alpha/` | 股票/期货 Alpha 信号与因子 |

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
       │ ←── DevReport（产物路径 + 自检报告）
       ▼
┌─────────────┐
│  测试 Agent  │  生成用例 → 运行 → TestReport
└──────┬──────┘
       │ ←── 通过 ✓ / 失败（Bug 回流，最多 3 轮）
       ▼
┌─────────────┐
│  发布 Agent  │  生成中英双语社区笔记 → 创建 GitHub 仓库（skill- 前缀）
│              │  → Git Submodule 归档 → 推送至 quantskills 组织
└──────┬──────┘
       │
       ▼
   ✅ 任务完成 + 已发布（遵循 QuantSkills 社区规则）
```

| Agent | 一句话职责 | 文件 |
|---|---|---|
| **需求分析** | 读 `jobs/*.txt`，输出结构化 TaskSpec，标记歧义 | `agents/analyst-agent/SKILL.md` |
| **Build/Alpha 开发** | 按 TaskSpec 编码，输出可运行的 Python Skill | `agents/dev-{build,alpha}-agent/SKILL.md` |
| **测试** | 生成测试用例，验证输入输出，报告 Bug | `agents/test-agent/SKILL.md` |
| **发布** | 生成中英双语技术笔记，发布至 GitHub + Submodule 归档 | `agents/publish-agent/SKILL.md` |

---

## 📦 已实现模块

| 编号 | 名称 | 简介 | GitHub 仓库 |
|---|---|---|---|
| **B11** | 自动止盈止损+仓位管理 | 按入场日期和开盘价自动判断止盈、止损、强平，单票仓位上限控制 | `quantskills/skill-b11-auto-stop-loss-take-profit` |
| **B12** | 日内仓位动态管理 v2 | 多品种持仓动态调仓（A股/ETF/期货/港股），T+1/T+0，资金校验 | `quantskills/skill-b12-intraday-position-manager` |

### 待开发

| 编号 | 任务 | 需求 |
|---|---|---|
| B5 | 早盘竞价扫描 | `jobs/B5 早盘竞价扫描.txt` |
| B12 v3 | 日内仓位动态管理（空头/双向/套利） | — |

---

## 📂 项目结构

```
panda-trading/
├── README.md                       ← 本文件（中文）
├── README.en.md                    ← 英文版
├── LICENSE                         ← MIT License
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
│   └── panda-builder/              ←   BUILD 脚手架与验收规范
│       ├── SKILL.md
│       └── skill.json
│
├── docs/                           ← 生产规则文档
│   ├── BUILD开发与生产规则V2.md     ←   BUILD 工具开发全流程规范
│   └── Alpha因子开发与生产规则V2.md ←   Alpha 因子开发与生产规范
│
├── jobs/                           ← 原始任务需求
│   ├── B11 自动止盈止损和仓位管理.txt  ← 已开发完成
│   ├── B12 日内仓位动态管理.txt        ← 已开发完成
│   └── B5 早盘竞价扫描.txt             ← 待开发
│
├── public/                         ← 发布归档
│   ├── community/                  ←   社区技术笔记（中英双语）
│   │   ├── B11-auto-stop-loss-take-profit.md
│   │   └── B12-intraday-position-manager.md
│   └── skills/                     ←   已发布技能的 Git Submodule
│       ├── skill-b11-auto-stop-loss-take-profit/   ← B11 独立仓库
│       └── skill-b12-intraday-position-manager/    ← B12 独立仓库
│
└── src/                            ← 开发产物（所有产出必须放此处）
    ├── build/                      ←   BUILD 工具
    │   └── build-B12-intraday-position-manager/
    │       └── 开发产物/
    │           ├── SKILL.md
    │           ├── scripts/
    │           │   ├── build.py        ← 主入口 run() + validate_input()
    │           │   ├── test.py         ← 自测脚本
    │           │   ├── common.py       ← 共享常量与工具
    │           │   ├── classify.py     ← 品种识别
    │           │   ├── specs.py        ← 合约规格加载
    │           │   └── markets/        ← 市场模块
    │           │       ├── a_stock.py
    │           │       ├── index_future.py
    │           │       ├── commodity_future.py
    │           │       └── hk_stock.py
    │           └── references/
    │               ├── api_guide.md
    │               └── contract_specs.json
    └── alpha/                      ←   Alpha 因子（预留）
```

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 无第三方依赖（标准库即可运行）

### 运行已发布的 Skill

```bash
# B11 — 自动止盈止损+仓位管理
cd public/skills/skill-b11-auto-stop-loss-take-profit/scripts
python3 build.py && python3 test.py

# B12 — 日内仓位动态管理
cd public/skills/skill-b12-intraday-position-manager/scripts
python3 build.py && python3 test.py
```

### 安装到 Claude Code

```bash
cp -r public/skills/skill-b12-intraday-position-manager ~/.claude/skills/
# 然后在 Claude Code 中调用：/skill-b12-intraday-position-manager
```

### 作为模块调用

```python
import sys
sys.path.insert(0, "public/skills/skill-b12-intraday-position-manager/scripts")
from build import run

# 单条
order = run({
    "code": "600036", "pnl_pct": 0.015,
    "sellable_qty": 800, "locked_qty": 0,
    "price": 10.0, "available_cash": 100000, "time": "10:00",
})

# 批量
orders = run([...])   # 传入 list 即可
```

---

## 📐 开发规范

### BUILD Skill 目录结构（panda-builder 规范）

```
build-{编号}-{名称}/
├── 开发产物/
│   ├── SKILL.md                   ← 功能说明书（必填）
│   ├── scripts/
│   │   ├── build.py               ← 主脚本，必须含 run() + validate_input()
│   │   └── test.py                ← 测试脚本（必填）
│   ├── references/
│   │   └── api_guide.md           ← 数据接口说明（必填）
│   └── demo.mp4                   ← 跑通视频（必填）
└── 生产产物/                      ← 结果型 BUILD 需要
    ├── SKILL.md
    └── 数据库.parquet
```

### 发布规范（QuantSkills 社区规则）

开发产物通过发布 Agent 发布时，自动转换为社区合规的独立仓库：

```
skill-{编号}-{名称}/               ← GitHub 独立仓库（skill- 前缀）
├── SKILL.md                       ← 根层级声明文件（含 metadata 块）
├── README.md                      ← 中文交付文档（含免责声明）
├── README.en.md                   ← 英文交付文档
├── LICENSE                        ← GPL-3.0
├── INSTALL.md                     ← 多平台安装指南（Codex/Cursor/Hermes/OpenClaw/Claude Code）
├── requirements.txt               ← Python 依赖声明
├── scripts/                       ← 开发产物
├── references/                    ← 参考文档
└── production/                    ← 生产产物（结果型/混合型）
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

> 已发布的 Skill 子仓库（`skill-b11-*`、`skill-b12-*`）使用 GPL-3.0，遵循 QuantSkills 社区规则。
