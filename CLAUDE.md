# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 每次对话开始时：运行前置守护检查 (Pre-run Guard)

每次用户启动全新会话或首次下达指令前，你必须作为“系统管理员”无条件自检：
1. 检查当前项目目录下 `.claude/skills/` 目录中是否完整存在本项目 `skills/` 目录下的所有本地 skill。
2. 对于每个缺失的 skill，你必须**主动调用 `execute_command` 运行以下经过 macOS 兼容优化的安全 Bash 命令**，将缺失技能从 `skills/{skill_name}/` 完整同步（含隐藏文件）至项目专属的 `.claude/skills/{skill_name}/`。

```bash
PROJECT_ROOT=$(pwd)
TARGET_DIR="$PROJECT_ROOT/.claude/skills"
mkdir -p "$TARGET_DIR"
for skill_path in "$PROJECT_ROOT/skills"/*; do
  if [ -d "$skill_path" ]; then
    skill_name=$(basename "$skill_path")
    project_skill_dir="$TARGET_DIR/$skill_name"
    if [ ! -d "$project_skill_dir" ]; then
      echo "🚀 正在安装项目专属 skill: $skill_name"
      mkdir -p "$project_skill_dir"
      cp -R "$skill_path/." "$project_skill_dir/"
    fi
  fi
done
```

本项目下所有的任务开发以 `skills/` 目录下当前包含的 skill：

| Skill | 用途 |
|---|---|
| `panda-builder` | 创建或验收新 BUILD skill 时使用，确保目录结构、代码接口、文档合规 |

---

## 任务列表
所有的原始任务需求都存储在 `jobs/*.txt` 文件中，任务遵循以下严格前缀映射规则：
- 任务文件名以 `A{编号}-{名称}.txt` 命名的为 Alpha 类任务，必须由主 Agent 路由指派至 **Alpha 开发 Agent** 配合 `panda-alpha` 进行迭代。
- 任务文件名以 `B{编号}-{名称}.txt` 命名的为 Build 类任务，必须由主 Agent 路由指派至 **Build 开发 Agent** 配合 `panda-builder` 进行开发。

## 项目目录规则

所有任务的产出物**必须**且只能存放在 `src/` 下对应的二级分类目录中，**严禁**直接存放在项目根目录：


| 目录 | 存放内容 | 任务新建与落地绝对路径 |
|---|---|---|
| `src/build/` | BUILD 类工具（数据处理、仓位管理、监控预警等） | `src/build/build-{编号}-{名称}/开发产物/` |
| `src/alpha/` | Alpha 信号与因子 | `src/alpha/alpha-{编号}-{名称}/` |

---

## 量枢学院量化交易 BUILD Skill 规范

本库中每个子目录是一个独立的交易 BUILD skill，使用**纯 Python 实现**，必须保持零框架依赖（无 pandas/numpy 等三方库依赖，除非 `TASK_REQUIREMENTS.md` 明确指定）。

### 创建新 BUILD skill 的硬性物理结构
**必须先加载项目内 `skills/panda-builder/SKILL.md`，严格按照以下拓扑结构创建，缺少任何一项均视为不合规：**
- `src/build/build-{编号}/开发产物/scripts/build.py`（必须包含 `run()` 入口函数与 `validate_input()` 校验函数）
- `src/build/build-{编号}/开发产物/scripts/test.py`（本地自测脚本）
- `src/build/build-{编号}/开发产物/SKILL.md`（该 Skill 的原子行为说明书）
- `src/build/build-{编号}/开发产物/references/api_guide.md`（接口对外调用文档）
- **结果型 BUILD 专属**：`src/build/build-{编号}/生产产物/数据库.parquet`

### 运行与验证方式
```bash
python3 src/build/build-{编号}/开发产物/scripts/build.py
```



量枢学院量化交易 skill 库，每个子目录是一个独立的交易 BUILD skill，使用纯 Python 实现，无框架依赖。

## 创建新 BUILD skill

**必须先加载项目内 `skills/panda-builder/SKILL.md`，按其规则创建目录结构、代码接口和文档。核心要求：

- 目录命名：`build-{编号}-{名称}/开发产物/`
- 必须提供 `scripts/build.py`（含 `run()` + `validate_input()`）、`scripts/test.py`、`SKILL.md`、`references/api_guide.md`
- 数据源只能使用 PandaAI data、调用方传入标准结构化数据或项目指定数据源
- 结果型 BUILD 额外需要 `生产产物/数据库.parquet`

## 运行方式

```bash
python3 <skill目录>/scripts/build.py
```

## 架构约定

每个 BUILD skill 目录结构遵循四层架构。具体输出数据结构由任务实际需求定义，以下为**仓位管理类 BUILD** 的参考示例：

- **配置常量** — 交易规则阈值（如止盈止损百分比、时间窗口）定义在文件顶部
- **判断层** — 纯函数，输入状态返回布尔值
- **决策层** — `manage_position(code, pnl_pct, current_qty, now)` 核心函数，返回调仓指令 dict
- **批量层** — `batch_manage(positions)` 循环调用决策层
- **输出层** — `print_order()` 格式化打印，`__main__` 提供示例数据

### 仓位管理类 BUILD 输出结构（参考）

```python
{
    "code": str,         # 股票代码
    "pnl_pct": float,    # 浮盈亏 %（正=盈，负=亏）
    "current_qty": int,  # 当前持仓股数
    "time": str,         # HH:MM:SS
    "action": str,       # "buy" / "sell" / "hold"
    "qty_change": int,   # 正数=买入股数，负数=卖出股数
    "target_qty": int,   # 目标持仓股数
    "reason": str,       # 触发原因说明
}
```

> **注意**：非仓位管理类 BUILD（如数据处理、监控预警等）的输出结构由任务实际需求决定，不做统一约束。

### A股交易约束（仓位管理类适用）

- 最小交易单位为 100 股，加仓/减仓数量需向下取整到 100 的整数倍
- 收盘时间 15:00，强平窗口默认收盘前 15 分钟（14:45）

---

## 多 Agent 协作开发

本项目支持多 Agent 协作完成任务开发，完整规范见 `agents/TASK_REQUIREMENTS.md`。

### Agent 分工

| Agent | 目录 | 职责概要 |
|---|---|---|
| 主 Agent | `agents/main-agent/SKILL.md` | 调度编排，接收用户指令，串联所有子 Agent |
| 需求分析 Agent | `agents/analyst-agent/SKILL.md` | 读取 `jobs/*.txt`，输出结构化 TaskSpec |
| Build 开发 Agent | `agents/dev-build-agent/SKILL.md` | 开发 B 类任务，使用 panda-builder skill |
| Alpha 开发 Agent | `agents/dev-alpha-agent/SKILL.md` | 开发 A 类任务，实现 Alpha 因子 |
| 测试 Agent | `agents/test-agent/SKILL.md` | 生成测试用例与测试报告，无代码修改权限 |

### 各 Agent 引用本文件的规范章节

各子 Agent 启动时会引用 CLAUDE.md 中的以下特定章节，不需要重复在各 Agent SKILL.md 中定义：

| 章节 | 被哪些 Agent 引用 | 用途 |
|---|---|---|
| §「任务列表」 | 主 Agent、需求分析 Agent | B*/A* 前缀判断、任务类型映射 |
| §「项目目录规则」 | 需求分析 Agent、主 Agent、Alpha 开发 Agent | 确定 target_dir 路径 |
| §「架构约定」 | Build 开发 Agent | build.py 四层结构实现规范 |
| §「仓位管理类 BUILD 输出结构」 | 需求分析 Agent、Build 开发 Agent、测试 Agent | 仓位管理类任务的输出 dict 参考字段 |
| §「A股交易约束」 | 需求分析 Agent、Build 开发 Agent、测试 Agent | 仓位管理类任务适用：100股整数倍、14:45强平时间 |

> **输出规范原则**：各任务的实际输出数据结构由 `jobs/*.txt` 中的需求文档决定，以上仅为仓位管理类的参考示例。非仓位管理类 BUILD 和 Alpha 任务不受此结构约束。

### 启动多 Agent 协作

当用户说"完成任务 B12"或"开发 jobs 下的任务"时，按以下步骤启动：

1. 主 Agent 加载 `agents/TASK_REQUIREMENTS.md`
2. 主 Agent 派发需求分析 Agent 读取对应 `jobs/*.txt`
3. 需求分析 Agent 返回 TaskSpec（含歧义项）
4. 若有歧义，主 Agent 向用户澄清后继续
5. 主 Agent 根据任务类型派发对应开发 Agent
6. 开发 Agent 完成后，主 Agent 派发测试 Agent
7. 测试不通过时，Bug 清单回流给开发 Agent，最多迭代 3 轮
8. 最终向用户汇报产出物路径和测试结果
