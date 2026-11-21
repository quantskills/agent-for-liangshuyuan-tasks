# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 每次对话开始时：运行前置守护检查 (Pre-run Guard)

每次用户启动全新会话或首次下达指令前，你必须作为“系统管理员”无条件自检：
1. 检查当前项目目录下 `.claude/skills/` 目录中是否完整存在本项目 `skills/` 目录下的所有本地 skill。
2. 对于每个缺失**或内容与 `skills/` 不一致**的 skill，你必须**主动运行以下经过 macOS 兼容优化的安全 Bash 命令**，将其从 `skills/{skill_name}/` 完整同步（含隐藏文件）至项目专属的 `.claude/skills/{skill_name}/`。

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
    elif ! diff -rq "$skill_path" "$project_skill_dir" >/dev/null 2>&1; then
      echo "🔄 正在更新项目专属 skill: $skill_name"
      cp -R "$skill_path/." "$project_skill_dir/"
    fi
  fi
done
```

> 注意：只判断“目录是否存在”会永久残留旧副本。必须同时比较内容，`skills/` 更新后 `.claude/skills/` 才会同步。

> 另注：本项目的 `.claude/skills` 已是指向 `../skills` 的**符号链接**，上述循环对它会全部报 `OK`（内容天然一致），并不代表发生了复制；此时若要确保规则最新，直接读 `skills/` 原件即可。在其他项目里若 `.claude/skills/` 是实体目录，才需要上面的复制逻辑。

本项目下所有的任务开发以 `skills/` 目录下当前包含的 skill：

| Skill | 用途 |
|---|---|
| `panda-builder` | 创建或验收新 BUILD skill 时使用，确保目录结构、代码接口、文档合规 |
| `panda-publisher` | 发布已过验收的 skill 时使用：先经 `panda-builder` 验收，再同步 `public/` 同名工作区、远端存在则 push 不存在则创建，并生成 `public/dist/` 下的分发 zip |
| `panda-upload-task` | 把量枢院任务平台（lsy.quant789.com/app）中「创作中/待创作」任务与已发布 skill 对齐，用 opencli 驱动成果表单回填（功能说明 / zip / GitHub 地址），默认保存草稿，提交审核需用户明确确认 |
| `opencli-usage` / `opencli-browser` / `opencli-adapter-author` / `opencli-autofix` / `opencli-browser-sitemap` / `opencli-sitemap-author` | OpenCLI 浏览器驱动与站点适配器开发工具链；`panda-upload-task` 依赖其中的 browser 能力 |
| `superpowers` | 通用工程技能路由表（brainstorming / TDD / systematic-debugging / code review 等 14 项），新建或修改 skill 本身前先查表 |

---

## 任务列表

所有的原始任务需求都存储在 `jobs/*.txt` 文件中，文件名格式为 `{类型}{编号} {名称}.txt`（类型与编号之间无分隔符，编号与名称之间为空格）。任务遵循以下严格前缀映射规则：

- 任务文件名以 `A{编号} {名称}.txt` 命名的为 Alpha 类任务，必须由主 Agent 路由指派至 **Alpha 开发 Agent** 进行开发。
- 任务文件名以 `B{编号} {名称}.txt` 命名的为 Build 类任务，必须由主 Agent 路由指派至 **Build 开发 Agent** 配合 `panda-builder` 进行开发。

任务编号（如 `B12`、`A00`）**只用于任务路由和溯源**，不进入任何 skill 名称、目录名或产物数据字段。

> **`jobs/` 仅本地保留**：任务文件含平台评分口径与内部评测反馈，已被 `.gitignore` 排除。任何 Agent 都不得 `git add jobs/`、不得把任务文件内容写进可发布的 skill 文档，也不得在发布产物中出现任务原文。

## 项目目录规则

所有任务的产出物**必须**且只能存放在 `src/` 下对应的二级分类目录中，**严禁**直接存放在项目根目录：

| 目录 | 存放内容 | 任务新建与落地绝对路径 |
|---|---|---|
| `src/skills/` | BUILD 类工具（数据处理、仓位管理、监控预警等） | `src/skills/skill-{slug}/` |
| `src/skills/` | Alpha 信号与因子 | `src/skills/skill-{slug}/` |
| `public/skills/` | 已发布 skill 的 clone 工作区：每个目录各自对应 `quantskills/skill-{slug}` 远端仓库（**不是 submodule**，父仓库不跟踪） | `public/skills/skill-{slug}/` |

- `{slug}`：中文任务名转英文，小写 + 连字符，3–6 词（如 `intraday-position-manager`）。
- 目录名格式为 `skill-{slug}`，**不带** `build-`、`alpha-` 或任务编号前缀。
- BUILD 与 Alpha 同处 `src/skills/`，用 `skill.json` 的 `type` 字段区分（`"build"` / `"alpha"`）；任务编号只记录在 `skill.json` 的 `source_task` 字段用于溯源。

### 版本控制归属（三套 git，互不相干）

| 仓库 | 位置 | 远端 | 用途与边界 |
|---|---|---|---|
| 父仓库 | 项目根 | `quantskills/agent-for-liangshuyuan-tasks` | 只管工程文件（`docs/`、`agents/`、`skills/`、`CLAUDE.md`）。`.gitignore` 已排除 `src/skills/*`、`public/skills/*` 与 `jobs/`，**skill 产物与原始任务需求都不进父仓库/不推线上** |
| 开发快照仓库 | `src/skills/skill-{slug}/.git`（按需 `git init`，可以没有） | **无** | 只做本地留痕与 `git worktree` 分支开发；历史与发布无关，**禁止**用它的分支/提交判断发布状态 |
| 发布仓库 | `public/skills/skill-{slug}/.git` | `quantskills/skill-{slug}` | 唯一与公网有关的 git；HEAD、tag、dirty、`origin/main` 只在这里核对 |

- 三者**不共享历史**：`src → public` 只靠 `panda-publisher` 的 `rsync` + 在 `$PUB` 里重新提交传递，**不靠** git remote / push / pull / submodule 关系。
- 在 `src/skills/skill-{slug}/` 里直接跑 git，命中的是该 skill 的本地快照仓库（若存在），**不是**父仓库；要查父仓库状态必须显式 `git -C <项目根>`。
- `$SRC` 里若存在 `.git`，`rsync` 的 `--exclude='.git/'` 会把它挡在发布包外，快照历史不会随包发布。
- 严禁在这几套仓库之间做反向 git 搬运（`public → src` 的 fetch / pull / cherry-pick / checkout），代码流向只有一个方向。

---

## 量枢学院量化交易 Skill 规范

本库中每个子目录是一个独立的交易 skill，使用**纯 Python 实现**，默认保持零框架依赖（无 pandas/numpy 等三方库依赖，除非 `jobs/*.txt` 任务需求明确指定）。

### 必须加载的规范

**创建或验收任何 skill 前，必须先加载 `skills/panda-builder/SKILL.md`，并参考已过审 skill `public/skills/skill-dl-gnn-stock-graph` 的实际形态。** 详细规则见 `docs/BUILD开发规则V2.md` 与 `docs/Alpha因子开发规则V2.md`。

### 标准物理结构（BUILD 与 Alpha 共用）

平铺结构，无中间层级，无 `开发产物/`、`生产产物/` 目录：

```
skill-{slug}/
├── SKILL.md              ← 技能设计书（必填）
├── README.md             ← 中文说明，含 ## ⚠️ 免责声明（必填）
├── README.en.md          ← 英文说明（必填）
├── LICENSE               ← 完整 GPL-3.0 文本（必填）
├── INSTALL.md            ← 多平台安装指南：Claude Code / Codex / Cursor / Hermes / OpenClaw（必填）
├── requirements.txt      ← Python 依赖声明（必填）
├── skill.json            ← Skill 元数据，name 与目录名一致（必填）
├── CHANGELOG.md          ← 版本变更记录（必填）
├── scripts/
│   └── build.py          ← 必须包含 run() 入口与 validate_input() 校验
├── tests/                ← 必须覆盖正常输入、边界值、异常输入
├── references/
│   └── api_guide.md      ← 数据接口、字段、调用示例
└── agents/               ← 运行时适配器（社区审核硬性要求）
    ├── cursor-rule.mdc      ← Cursor
    ├── portable-loader.md   ← Hermes / OpenClaw
    └── openai.yaml          ← Codex / OpenClaw
```

可选：`config/`（集中式参数）、`.github/workflows/validate.yml`（CI）。

`skill.json` 的 `license` 必须为 `GPL-3.0-only`。说明文档不得包含敏感信息、收益承诺、投资建议或未经确认的官方背书。

### 运行与验证方式

```bash
python3 src/skills/skill-{slug}/scripts/build.py
python3 -m pytest src/skills/skill-{slug}/tests/ -v
```

### 结果型 skill 的结果落盘

结果型 skill **不新建第二套 skill、不新建 `生产产物/` 目录**。运行结果写入运行目录下的 `output/`（必须加入 `.gitignore`），并在同一份 `SKILL.md` 的「输出」章节与 `references/` 中说明路径、字段与更新频率。

---

## 架构约定

每个 BUILD skill 的 `scripts/build.py` 遵循四层架构。具体输出数据结构由任务实际需求定义，以下为**仓位管理类 BUILD** 的参考示例：

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
    "time": str,         # HH:MM
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
- T+1：当日新建仓位锁定，不可当日卖出

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
| 发布 Agent | `agents/publish-agent/SKILL.md` | 发布为 quantskills 组织下的独立 skill 仓库 |

### 各 Agent 引用本文件的规范章节

各子 Agent 启动时会引用 CLAUDE.md 中的以下特定章节，不需要重复在各 Agent SKILL.md 中定义：

| 章节 | 被哪些 Agent 引用 | 用途 |
|---|---|---|
| §「任务列表」 | 主 Agent、需求分析 Agent | B*/A* 前缀判断、任务类型映射 |
| §「项目目录规则」 | 需求分析 Agent、主 Agent、Build/Alpha 开发 Agent | 确定 target_dir 路径与 `skill-{slug}` 命名 |
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
8. 通过后派发发布 Agent，发布为 `quantskills` 组织下的独立 skill 仓库
9. 最终向用户汇报 skill 路径、测试结果与发布状态