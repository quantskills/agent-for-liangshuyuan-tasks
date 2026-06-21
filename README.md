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

### 多 Agent 协作 —— 从任务到发布全自动

把任务需求写成 `.txt` 放入 `jobs/` 目录，Agent 系统会自动完成**分析 → 路由 → 开发 → 测试 → 发布**全流程。文件名前缀决定路由规则：

| 前缀示例 | 类型 | 路由至 | 产出目录 |
|---|---|---|---|
| `B12 日内仓位...txt` | BUILD 工具 | Build 开发 Agent + panda-builder | `src/build/build-B12-.../` |
| `A3 连板龙头...txt` | Alpha 因子 | Alpha 开发 Agent | `src/alpha/alpha-A3-.../` |

```
jobs/B12 日内仓位动态管理.txt          ← 你只需要写这个
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
│  发布 Agent  │  生成社区笔记 → 创建 GitHub 仓库 → Git Submodule 归档 → 推送
└──────┬──────┘
       │
       ▼
   ✅ 任务完成 + 已发布
```

| Agent | 一句话职责 |
|---|---|
| **需求分析** | 读 `jobs/*.txt`，输出结构化 TaskSpec，标记歧义 |
| **Build/Alpha 开发** | 按 TaskSpec 编码，输出可运行的 Python Skill |
| **测试** | 生成测试用例，验证输入输出，报告 Bug |
| **发布** | 生成技术笔记，归档至 `public/skills/`，发布到 GitHub |

### 发布 Agent 做了什么

当任务测试通过后，发布 Agent 自动将开发产物发布为 GitHub 上 `quantskills` 组织下的独立技能仓库：

| 步骤 | 产物 | 位置 |
|---|---|---|
| 生成技术笔记 | 约 500 字中文文档 | `public/community/{task_id}-{short_name}.md` |
| 创建 GitHub 仓库 | 独立 skill repo | `github.com/quantskills/{type}-{id}-{slug}` |
| Git Submodule 归档 | 主仓库追踪技能版本 | `public/skills/{type}-{id}-{slug}/` |
| 推送主仓库 | 笔记 + submodule 引用 | gitee + github |

**发布的技能目录结构**（`skills_demo` 规范）：

```
{type}-{id}-{slug}/                    ← GitHub 仓库根
├── README.md                          ← 完整交付文档（目录树/快速开始/设计要点/验收/局限）
├── INSTALL_CLAUDE_CODE.md             ← 安装到 Claude Code 的说明
├── requirements.txt                   ← Python 依赖声明
├── {type}-{id}-{slug}/                ← 开发产物（必选）
│   ├── SKILL.md
│   ├── scripts/   (build.py + test.py + ...)
│   └── references/ (api_guide.md + ...)
└── {type}-{id}-{slug}-production/     ← 生产产物（结果型/混合型才有）
    ├── SKILL.md
    └── database.parquet
```

安装到 Claude Code 后可直接调用：`/{type}-{id}-{slug}`

**环境要求**：`.mpc.json` 配置 GitHub MCP + `GITHUB_TOKEN` 环境变量

---

## 📦 已实现模块

| 编号 | 名称 | 简介 | 详情 |
|---|---|---|---|
| B12 | 日内仓位动态管理 v2 | 多品种持仓动态调仓（A股/ETF/期货/港股），T+1/T+0，资金校验 | `src/build/build-B12-intraday-position-manager/开发产物/SKILL.md` |
| — | 发布至 GitHub | 独立仓库 + 社区笔记 | `quantskills/build-b12-intraday-position-manager` |

### 待开发

| 编号 | 任务 | 需求 |
|---|---|---|
| B5 | 早盘竞价扫描 | `jobs/B5 早盘竞价扫描.txt` |
| B12 v3 | 日内仓位动态管理（空头/双向/套利） | — |

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
    │   └── build-B12-intraday-position-manager/              ←     B12 日内仓位动态管理
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
python3 src/build/build-B12-intraday-position-manager/开发产物/scripts/build.py

# 运行测试
python3 src/build/build-B12-intraday-position-manager/开发产物/scripts/test.py
```

### 作为模块调用

```python
import sys
sys.path.insert(0, "src/build/build-B12-intraday-position-manager/开发产物/scripts")
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
├── README.md                      ← 交付说明（必填）
├── INSTALL_CLAUDE_CODE.md         ← 安装指南（必填）
├── requirements.txt               ← Python 依赖声明（必填）
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
touch src/build/build-{编号}-{名称}/{README.md,INSTALL_CLAUDE_CODE.md,requirements.txt}

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

## 🤖 外部 AI 使用指南

> 如果你是外部 AI（如 Claude Code、Copilot、Cursor 等），以下是你进入本项目后应该执行的标准流程。

### 第一步：Skill 发现

遍历 `src/build/` 和 `src/alpha/` 目录，每个匹配 `build-{编号}-{名称}/` 或 `alpha-{编号}-{名称}/` 的子目录就是一个 Skill：

```bash
# 列出所有已实现的 BUILD skill
ls -d src/build/build-*/开发产物/

# 列出所有已实现的 Alpha skill
ls -d src/alpha/alpha-*/
```

### 第二步：读取 SKILL.md —— 理解 Skill 能力

每个 Skill 的 `开发产物/SKILL.md` 是其「原子行为说明书」，必须首先阅读。SKILL.md 的 frontmatter 和正文会明确告诉你：

| 你需要知道的信息 | SKILL.md 中的对应字段 |
|---|---|
| 这个 Skill 解决什么问题 | `description`（frontmatter）+ `## 工具定位` |
| 什么时候用它 | `## 适用场景` |
| 输入需要哪些字段 | `## 输入` 表格 |
| 输出会有什么字段 | `## 输出` 表格 |
| 怎么调用它 | `## 调用方式`（含 Python import 示例） |
| 能否被 Alpha 调用 | `## 可被 Alpha 调用` |
| 是否需要读 Parquet | `## 是否需要生产结果` |

### 第三步：校验 Skill 是否可用

对每个 Skill 执行以下校验：

```bash
BUILD_DIR="src/build/build-B12-intraday-position-manager/开发产物"   # 替换为你要检查的 Skill

# 1. 结构完整性检查
echo "=== 必选文件检查 ==="
for f in SKILL.md scripts/build.py scripts/test.py references/api_guide.md; do
  [ -f "$BUILD_DIR/$f" ] && echo "✅ $f" || echo "❌ 缺失 $f"
done

# 2. 代码入口检查 —— build.py 必须实现 run() + validate_input()
echo ""
echo "=== 入口函数检查 ==="
grep -q "def run(" "$BUILD_DIR/scripts/build.py" && echo "✅ run()" || echo "❌ 缺失 run()"
grep -q "def validate_input(" "$BUILD_DIR/scripts/build.py" && echo "✅ validate_input()" || echo "❌ 缺失 validate_input()"

# 3. 运行自测
echo ""
echo "=== 自测结果 ==="
python3 "$BUILD_DIR/scripts/build.py" && echo "✅ build.py 可独立运行" || echo "❌ build.py 运行失败"
python3 "$BUILD_DIR/scripts/test.py" && echo "✅ test.py 通过" || echo "❌ test.py 未通过"
```

### 第四步：调用 Skill

所有 BUILD skill 遵循统一调用协议。对于**调用型** BUILD（如 B12），直接 import：

```python
import sys
sys.path.insert(0, "src/build/build-B12-intraday-position-manager/开发产物/scripts")
from build import run

# 单条输入（dict）→ 单条输出（dict）
order = run({
    "code": "600036", "pnl_pct": 0.015,
    "sellable_qty": 800, "locked_qty": 0,
    "price": 10.0, "available_cash": 100000, "time": "10:00",
})

# 批量输入（list）→ 批量输出（list）
orders = run([pos1, pos2, pos3])
```

对于**结果型** BUILD，直接读取 `生产产物/数据库.parquet`，不要重复拉数重算。

### 第五步：理解 Skill 的生产形态

| 形态 | 识别方式 | 正确做法 |
|---|---|---|
| **调用型** | SKILL.md 写"是否需要生产结果：否" | `import build; build.run(data)` |
| **结果型** | 存在 `生产产物/数据库.parquet` | 直接读 Parquet，不重算 |
| **混合型** | 两者皆有 | 优先读 Parquet，按需调用 build.py |

### 第六步：发布 Skill 到 GitHub

开发完成并测试通过后，可将 Skill 发布为 `quantskills` 组织下的独立仓库，同时以 Git Submodule 形式归档到本仓库的 `public/skills/`：

```bash
# 发布（需要 GitHub MCP + GITHUB_TOKEN）
# 直接告诉 Claude："发布 B12"
```

发布的 Skill 可安装到任意 Claude Code 环境：

```bash
cp -r public/skills/build-b12-intraday-position-manager ~/.claude/skills/
# 然后在 Claude Code 中调用：/build-b12-intraday-position-manager
```

### 常见错误（AI 应避免）

- ❌ 自己凭空判断仓位，而不是调用 B12 仓位管理 Skill
- ❌ 对结果型 BUILD 重新拉取原始行情 + 重算因子
- ❌ 忽略 SKILL.md 中标注的调用限制（如 B12 仅多头）
- ❌ 不看 `references/api_guide.md` 就猜输入输出格式
- ❌ 跳过 `validate_input()` 直接传入脏数据

---

## 📚 参考资料

- [BUILD 开发与生产规则 V2](./docs/BUILD开发与生产规则V2.md)
- [Alpha 因子开发与生产规则 V2](./docs/Alpha因子开发与生产规则V2.md)
- [多 Agent 协作任务规范](./agents/TASK_REQUIREMENTS.md)
- [发布 Agent 规范](./agents/publish-agent/SKILL.md)
- [panda-builder Skill 规范](./skills/panda-builder/SKILL.md)
