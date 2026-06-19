# 🐼 量枢学院 · Panda Trading

> 基于 Claude Code 多 Agent 协作框架的量化交易工具库 —— 纯 Python · 零框架依赖 · Skill 架构

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

---

## 📖 简介

**量枢学院（Panda Trading）** 是一个模块化的量化交易工具开发平台，采用 **Skill 原子能力** + **多 Agent 协作** 架构，将交易系统的核心能力拆分为独立的、可复用的 BUILD 工具和 Alpha 因子。

项目采用 **纯 Python 标准库** 实现，不依赖 pandas / numpy 等第三方框架（除非任务需求明确指定），确保每个 Skill 轻量、可独立运行、可被 Agent 或 Alpha 自由调用。

### 核心理念

| 理念 | 说明 |
|---|---|
| **Skill 即工具** | 每个子目录是一个独立的交易 BUILD skill，可独立运行、独立测试、独立部署 |
| **BUILD 为 Alpha 服务** | BUILD 是工具层，Alpha 是信号层；Alpha 调用 BUILD，不复制 BUILD 逻辑 |
| **Agent 协作** | 多 Agent 分工：需求分析 → 开发 → 测试 → 验收，全流程自动化 |
| **零框架依赖** | 默认纯 Python 标准库实现，确保任意环境可直接运行 |

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

### 多 Agent 协作

```
用户下达任务
     │
     ▼
┌─────────────┐      ┌──────────────────┐
│  主 Agent   │─────→│  需求分析 Agent   │  读取 jobs/*.txt，输出结构化 TaskSpec
└──────┬──────┘      └──────────────────┘
       │ ←── TaskSpec（含歧义标记）
       │
       ├── B 类任务 → Build 开发 Agent + panda-builder skill
       ├── A 类任务 → Alpha 开发 Agent
       │
       │ ←── DevReport（产出物路径 + 自检报告）
       ▼
┌─────────────┐
│  测试 Agent  │  生成测试用例 → 运行 → 输出 TestReport
└──────┬──────┘
       │ ←── 通过 ✓ / 失败（Bug 回流，最多迭代 3 轮）
       ▼
   任务完成
```

| Agent | 职责 | 代码权限 |
|---|---|---|
| **主 Agent** (`agents/main-agent/`) | 调度编排，串联所有子 Agent | 写入权限 |
| **需求分析 Agent** (`agents/analyst-agent/`) | 读取 `jobs/*.txt`，输出 TaskSpec | 只读 |
| **Build 开发 Agent** (`agents/dev-build-agent/`) | 开发 B 类任务，使用 panda-builder | 写入 `src/build/` |
| **Alpha 开发 Agent** (`agents/dev-alpha-agent/`) | 开发 A 类任务，实现 Alpha 因子 | 写入 `src/alpha/` |
| **测试 Agent** (`agents/test-agent/`) | 生成测试用例与测试报告 | 只读运行 |

---

## 📦 已实现模块

### B12 — 多品种日内仓位动态管理 v2

**适用品种**：A股 / A股ETF / 股指期货 / 商品期货 / 港股+ETF

**决策规则**（优先级从高到低）：

| 优先级 | 条件 | 动作 |
|---|---|---|
| 1 | 时间 ≥ 品种强平时间 | 强平（按可卖数量） |
| 2 | 浮亏 ≥ 1% | 全平止损 |
| 3 | 浮亏 ≥ 0.5% | 砍半仓 |
| 4 | 浮盈 > 1% | 加仓 50%（校验资金） |
| 5 | 其他 | hold |

**特性**：

- ✅ T+1 / T+0 品种区分（A股/ETF 锁仓阻断卖出）
- ✅ 昨仓/今仓分离（sellable_qty / locked_qty）
- ✅ 保证金/现金独立校验，资金不足自动阻断
- ✅ 合约乘数中央表驱动（contract_specs.json）
- ✅ 港股独立 lot_size 覆盖表
- ✅ 标准化 8 字段调仓指令 + reason 结构化前缀

```python
# 调用示例
from scripts.build import run

results = run([
    {"code": "600036", "pnl_pct":  0.015, "sellable_qty":  800, "locked_qty":   0,
     "price": 10.0,    "available_cash": 100000, "time": "10:00"},
    {"code": "IF2406", "pnl_pct":  0.015, "sellable_qty":    2, "locked_qty":   0,
     "price": 4000.0,  "available_cash": 200000, "time": "10:00"},
    {"code":  "00700", "pnl_pct": -0.007, "sellable_qty":  200, "locked_qty":   0,
     "price": 400.0,   "available_cash":      0, "time": "10:00"},
])
```

### 待开发任务

| 编号 | 任务 | 状态 |
|---|---|---|
| B5 | 早盘竞价扫描 | 📋 需求已录入 |
| B12 | 日内仓位动态管理 v3（空头/双向/套利） | 🔜 规划中 |

---

## 📂 项目结构

```
panda-trading/
├── README.md                       ← 本文件
├── README.en.md                    ← 英文版
├── LICENSE                         ← MIT License
├── CLAUDE.md                       ← Claude Code 项目规范（Agent 协作、Skill 架构、数据接口定义）
│
├── agents/                         ← 多 Agent 协作规范
│   ├── TASK_REQUIREMENTS.md        ←   Agent 分工、流程、信息传递格式
│   ├── main-agent/SKILL.md         ←   主 Agent 调度规则
│   ├── analyst-agent/SKILL.md      ←   需求分析 Agent 规则
│   ├── dev-build-agent/SKILL.md    ←   Build 开发 Agent 规则
│   ├── dev-alpha-agent/SKILL.md    ←   Alpha 开发 Agent 规则
│   └── test-agent/SKILL.md         ←   测试 Agent 规则
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
│   ├── B12 日内仓位动态管理.txt    ←   已开发完成
│   └── B5 早盘竞价扫描.txt         ←   待开发
│
└── src/                            ← 开发产物（所有产出必须放此处）
    ├── build/                      ←   BUILD 工具
    │   └── build-B12/              ←     B12 日内仓位动态管理
    │       └── 开发产物/
    │           ├── SKILL.md
    │           ├── scripts/
    │           │   ├── build.py        ← 主入口 run() + validate_input()
    │           │   ├── test.py         ← 自测脚本
    │           │   ├── common.py       ← 共享常量与工具
    │           │   ├── classify.py     ← 品种识别
    │           │   ├── specs.py        ← 合约规格加载
    │           │   └── markets/        ← 市场模块
    │           │       ├── a_stock.py          ← A股 + ETF（T+1）
    │           │       ├── index_future.py     ← 股指期货（IF/IC/IH/IM）
    │           │       ├── commodity_future.py ← 商品期货
    │           │       └── hk_stock.py         ← 港股 + ETF（T+0）
    │           └── references/
    │               ├── api_guide.md     ← 接口调用文档
    │               └── contract_specs.json ← 合约规格中央表
    └── alpha/                      ←   Alpha 因子（预留目录）
```

---

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 无第三方依赖（标准库即可运行）

### 运行 B12 仓位管理

```bash
# 直接运行（含内置示例）
python3 src/build/build-B12/开发产物/scripts/build.py

# 运行测试
python3 src/build/build-B12/开发产物/scripts/test.py
```

### 作为模块调用

```python
import sys
sys.path.insert(0, "src/build/build-B12/开发产物/scripts")
from build import run

# 单条
order = run({
    "code": "600036",
    "pnl_pct": 0.015,
    "sellable_qty": 800,
    "locked_qty": 0,
    "price": 10.0,
    "available_cash": 100000,
    "time": "10:00",
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

- 最小交易单位：100 股（加仓/减仓取整到 100 的整数倍）
- 收盘时间：15:00，强平窗口：14:45
- T+1 制度：当日新买仓位锁仓，不可当日卖出

### BUILD 生产形态

| 形态 | 说明 | 交付物 |
|---|---|---|
| 调用型 | 轻量级，依赖调用方输入，实时返回结果 | `SKILL.md + scripts/` |
| 结果型 | 重计算/定时任务，结果缓存复用 | `SKILL.md + 数据库.parquet` |
| 混合型 | 既支持即时调用，也有定时生产结果 | 全部 |

---

## 🤝 参与贡献

1. **Fork** 本仓库
2. 新建 `Feat_xxx` 分支
3. 开发任务放到 `src/build/` 或 `src/alpha/` 下，遵循 panda-builder 规范
4. 确保 `python3 scripts/build.py` 可独立跑通
5. 提交代码并新建 **Pull Request**

### 开发一个 BUILD Skill 的最小步骤

```bash
# 1. 创建目录结构
mkdir -p src/build/build-{编号}-{名称}/开发产物/{scripts,references}

# 2. 编写 build.py（必须实现 run() 和 validate_input()）
# 3. 编写 test.py（覆盖正常/异常/边界）
# 4. 编写 SKILL.md（功能说明书）
# 5. 编写 references/api_guide.md（接口文档）

# 6. 自测
python3 src/build/build-{编号}-{名称}/开发产物/scripts/build.py
python3 src/build/build-{编号}-{名称}/开发产物/scripts/test.py

# 7. 提交
```

---

## 📄 许可证

本项目基于 [MIT License](./LICENSE) 开源，Copyright (c) 2026 码段。

---

## 📚 参考资料

- [BUILD 开发与生产规则 V2](./docs/BUILD开发与生产规则V2.md)
- [Alpha 因子开发与生产规则 V2](./docs/Alpha因子开发与生产规则V2.md)
- [多 Agent 协作任务规范](./agents/TASK_REQUIREMENTS.md)
- [panda-builder Skill 规范](./skills/panda-builder/SKILL.md)
- [B12 API 接口文档](./src/build/build-B12/开发产物/references/api_guide.md)
