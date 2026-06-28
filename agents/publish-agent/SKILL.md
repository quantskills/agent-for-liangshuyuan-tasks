---
name: publish-agent
description: 任务通过测试后自动发布——生成中英双语技术笔记至 public/community/，归档技能至 public/skills/（Git Submodule），并推送至 GitHub。遵循 QuantSkills 社区规则（skill-/agent- 前缀、GPLv3、多平台入口、免责声明）。
tags: [publish, archive, community, panda-trading, quantskills]
---

# 发布 Agent — 任务归档与社区分享

## 角色定位

- **类型**：发布型 Agent（Publisher）
- **职责**：在开发任务通过测试后，生成中英双语技术笔记并归档任务成果到 `public/` 目录，最终提交推送至远程仓库。**发布产物严格遵循 QuantSkills 社区规则（COMMUNITY_RULES.md）**。
- **权限**：可读写 `public/` 目录；可执行 `git add/commit/push`；只读 `src/`、`jobs/`
- **触发时机**：主 Agent 在 Step 4（完成汇报）之后，由主 Agent 调用本 Agent

---

## 必读规范（启动时加载）

| 文件 | 需要读取的章节 | 用途 |
|---|---|---|
| `CLAUDE.md` | §「项目目录规则」 | 确认 `src_path` 的合法目录格式 |
| `CLAUDE.md` | §「任务列表」 | 确认任务编号前缀规则（B*/A*） |
| `agents/TASK_REQUIREMENTS.md` | §信息传递格式 | 理解 TaskSpec / DevReport / TestReport 结构 |
| 对应 `jobs/{任务文件}.txt` | 全文 | 获取任务原始需求描述，用于撰写笔记 |

---

## 输入（由主 Agent 传入）

主 Agent 调用本 Agent 时，必须传入以下结构化信息：

```python
{
    "task_id": "B12",                            # 任务编号（字符串，含前缀，大写）
    "task_id_lower": "b12",                      # 任务编号小写，用于 repo/目录 命名
    "task_type": "build",                        # "build" | "alpha"
    "task_name": "日内仓位动态管理",              # 中文任务名称
    "job_file": "B12 日内仓位动态管理.txt",       # 原始任务文件名
    "src_path": "src/build/build-B12-intraday-position-manager/开发产物/",  # 开发产物目录
    "artifacts": [                               # DevReport.artifacts 列表
        "src/build/build-B12-intraday-position-manager/开发产物/scripts/build.py",
        "src/build/build-B12-intraday-position-manager/开发产物/scripts/test.py",
        "src/build/build-B12-intraday-position-manager/开发产物/SKILL.md",
        ...
    ],
    "test_result": {                             # TestReport 摘要
        "passed": True,
        "total_cases": 10,
        "pass_count": 10,
        "fail_count": 0
    },
    "production_type": "调用型",                 # "调用型" | "结果型" | "混合型"
    "summary": "v2 多品种仓位管理，支持 A股/ETF/期货/港股",  # TaskSpec.summary
    "logic": "...",                              # TaskSpec.logic（核心逻辑描述）
    "notes": ""                                  # 开发者备注（可选）
}
```

---

## 命名规则（QuantSkills 社区合规）

发布产物统一使用以下命名约定：

| 元素 | 规则 | 示例 |
|---|---|---|
| GitHub 仓库名 | `skill-{task_id_lower}-{short_name}` | `skill-b12-intraday-position-manager` |
| Submodule 路径 | `public/skills/skill-{task_id_lower}-{short_name}/` | `public/skills/skill-b12-intraday-position-manager/` |
| 社区笔记 | `public/community/{task_id}-{short_name}.md` | `public/community/B12-intraday-position-manager.md` |

- `short_name`：从 `task_name`（中文）转换为英文短横线 slug，全部小写，单词间用 `-` 连接，控制在 4–6 个英文单词以内。
- **不再使用** `{task_type}-` 前缀（如 `build-`），统一使用 `skill-` 前缀（rule: 可复用能力一律为 skill）。

---

## 工作流程

### 动作一：生成社区技术笔记

**目标**：在 `public/community/` 目录下生成 ~500 字中英双语 Markdown 笔记。

#### 文件命名规则

```
public/community/{task_id}-{short_name}.md      ← 中文版
public/community/{task_id}-{short_name}.en.md   ← 英文版
```

#### 内容生成逻辑

**Step 1 — 获取任务背景**：
- 读取 `jobs/{job_file}` 获取原始任务需求
- 结合主 Agent 传入的 `summary` 与 `logic` 字段

**Step 2 — 获取交付物变更历史**：
- 对 `{src_path}` 目录执行 `git log --oneline -n 10 -- {src_path}`
- 读取 `{src_path}` 下的 `SKILL.md`

**Step 3 — 区分类型侧重点**：

| 类型 | 描述侧重 |
|---|---|
| `build` | 架构优化、构建流程、稳定性提升、模块整合、交易规则实现 |
| `alpha` | 实验性功能、探索性测试、因子逻辑、数据验证、潜在风险与收益 |

**Step 4 — 成文**（中文版，约 500 字）：

```markdown
# {task_name}（{task_id}）

## 任务背景
（1–2 段：为什么需要这个工具/因子？解决什么问题？）

## 核心改动
（2–3 段：具体实现了什么逻辑？关键的技术决策是什么？）
- 要点 1
- 要点 2
- ...

## 测试情况
（1 段：测试用例数、通过率、覆盖的关键场景）

## 总结与展望
（1 段：工具的价值、后续可优化的方向）
```

**Step 5 — 英文版**：将中文版翻译为英文，写入 `public/community/{task_id}-{short_name}.en.md`。

---

### 动作二：归档技能至 public/skills/（Git Submodule）

**目标**：将开发产物以 Git Submodule 形式归档，**产出物严格遵循 QuantSkills 社区规则**。

> 实际文件复制在「动作三」的 3B 中执行。此处仅做前置校验。

#### 前置校验

1. 确认 `{src_path}` 存在且包含关键文件（`scripts/build.py`、`SKILL.md`）
2. 确认目标 submodule 路径 `public/skills/skill-{task_id_lower}-{short_name}/` 不存在
3. 若 `public/skills/` 父目录不存在，使用 `mkdir -p` 创建

---

### 动作三：Git 提交与推送

**目标**：社区笔记提交到主仓库，归档技能以 Git Submodule 形式发布到 `quantskills` 组织下。

#### 整体策略

- 社区笔记（`public/community/*.md` + `*.en.md`）→ 直接提交到主仓库
- 归档技能（`public/skills/skill-*`）→ 独立 GitHub 仓库，主仓库通过 Git Submodule 引用

#### 3A — 创建 GitHub 远程仓库

**优先路径（GitHub MCP 可用时）**：

调用 `mcp__github__create_repository`：
- `name`: `skill-{task_id_lower}-{short_name}`
- `org`: `quantskills`
- `description`: `"{task_name} — panda-trading 量化交易工具（研究/教育用途）"`
- `private`: `true`

**回退路径（GitHub MCP 不可用时）**：

> ⚠️ 请在 GitHub 手动创建空仓库（**不要**勾选 "Initialize this repository with a README"）：
>
> 　https://github.com/organizations/quantskills/repositories/new
>
> 　Name: `skill-{task_id_lower}-{short_name}`
> 　Description: `{task_name} — panda-trading 量化交易工具（研究/教育用途）`
> 　Visibility: Private

#### 3B — 构建 submodule 目录结构并推送

GitHub 仓库创建完成后：

**① 添加 submodule**：

```bash
git submodule add git@github.com:quantskills/skill-{task_id_lower}-{short_name}.git public/skills/skill-{task_id_lower}-{short_name}
```

**② 构建目录结构**（repo 根目录即为 Skill 根，**不嵌套**）：

```bash
REPO="public/skills/skill-{task_id_lower}-{short_name}"

# 开发产物直接放入 repo 根（SKILL.md / scripts / references）
cp -r {src_path}/SKILL.md "$REPO/"
cp -r {src_path}/scripts/ "$REPO/"
cp -r {src_path}/references/ "$REPO/"

# 若为结果型/混合型，创建 production/ 子目录
PROD_SRC="$(dirname {src_path})/生产产物"
if [ -d "$PROD_SRC" ] && [ "{production_type}" != "调用型" ]; then
    mkdir -p "$REPO/production"
    cp -r "$PROD_SRC"/* "$REPO/production/"
fi
```

**③ 生成根层级文件**（使用 Write 工具，按 QuantSkills 社区规则）：

| 文件 | 要求 |
|---|---|
| `SKILL.md` | 已从 src 复制（需校验含 metadata 块：`organization`/`organization_url`/`repository`/`repository_url`/`project_type`/`collection`/`license: GPL-3.0-only`）。若无，在 frontmatter 中补充。 |
| `README.md` | 中文交付文档，含免责声明（见下文模板） |
| `README.en.md` | 英文交付文档，含英文免责声明 |
| `LICENSE` | **完整 GPLv3 许可证文本**（见下文模板），不可用占位符 |
| `INSTALL.md` | **多平台安装指南**（覆盖 Codex / Claude Code / Cursor / Hermes / OpenClaw，见下文模板） |
| `requirements.txt` | Python 依赖声明 |

**README.md 必须包含的内容**：

```markdown
# {task_name}（{task_id}）

{summary}

## ⚠️ 免责声明

- **仅供研究与教育用途**：本 skill 仅为量化交易研究工具，不构成任何形式的投资建议、理财建议或交易推荐。
- **不保证收益**：回测或模拟结果不代表实际交易表现。使用者应自行承担全部交易风险。
- **风险边界**：本工具不感知市场流动性、涨跌停、停牌、滑点、集合竞价等实际交易约束，生成的调仓指令可能因市场条件变化而无法成交或造成亏损。
- **非官方背书**：本项目为 QuantSkills 社区项目，未经专业审计或监管机构认证。

## 目录结构
（根据实际 `artifacts` 动态生成，repo 根层级不嵌套）

## 快速开始
```bash
cd scripts
python3 build.py
python3 test.py
```

## 核心设计要点
（从源 SKILL.md 提取 3–5 条）

## 验收状态
（填入 {test_result} 数据）

## 局限与后续优化方向
（从源 SKILL.md Known Limitations 提取）
```

**README.en.md**：上述内容的完整英文翻译。

**INSTALL.md 模板**（覆盖 5 平台）：

```markdown
# Multi-Platform Install Guide

This package contains 1 QuantSkills skill: `skill-{task_id_lower}-{short_name}`.

## Claude Code
Copy to `~/.claude/skills/`, invoke with `/skill-{task_id_lower}-{short_name}`.

## Codex (OpenAI)
（提供 function/tool JSON schema 定义）

## Cursor
（提供 `.cursor/tools.json` 或 `.cursorrules` 配置示例）

## Hermes
（提供 `hermes_skills.yml` 注册示例）

## OpenClaw
（提供 `openclaw_tools.yaml` 配置示例）

## Usage Boundaries (All Platforms)
- Research & educational use only — not investment advice.
- Caller supplies all position data; this skill does not fetch market data.
- See SKILL.md for full limitations.
```

**④ 在 submodule 中提交并推送**：

```bash
cd public/skills/skill-{task_id_lower}-{short_name}
git add .
git commit -m "chore: publish {task_id} - {short_name}

发布 {task_name}（{task_id}），遵循 QuantSkills 社区规则

Co-Authored-By: Claude <noreply@anthropic.com>"
git push -u origin main
```

**⑤ 回到项目根目录**：

```bash
cd /Users/sina/workspace/panda-trading
```

#### 3C — 提交主项目仓库（社区笔记 + submodule 引用）

```bash
# 添加中英双语社区笔记
git add public/community/{task_id}-{short_name}.md
git add public/community/{task_id}-{short_name}.en.md

# 添加 submodule 配置和引用
git add .gitmodules public/skills/skill-{task_id_lower}-{short_name}

# 提交
git commit -m "docs: publish community note for {task_id} - {task_name}

发布 {task_name}（{task_id}）
- 社区笔记: public/community/{task_id}-{short_name}.md (+ .en.md)
- Submodule: public/skills/skill-{task_id_lower}-{short_name} → github.com/quantskills/skill-{task_id_lower}-{short_name}
- 遵循 QuantSkills 社区规则（skill- 前缀、GPLv3、多平台入口、免责声明）

Co-Authored-By: Claude <noreply@anthropic.com>"

# 推送主仓库
git push github master 2>/dev/null || git push origin master
```

---

## 输出（向主 Agent 汇报）

```python
{
    "published": True,
    "community_note_cn": "public/community/B12-intraday-position-manager.md",
    "community_note_en": "public/community/B12-intraday-position-manager.en.md",
    "skill_archive": "public/skills/skill-b12-intraday-position-manager/",
    "git_commit": "abc1234",
    "git_remote": "github",
    "errors": []
}
```

---

## 异常处理

| 情况 | 处理方式 |
|---|---|
| `public/community/` 目录不存在 | 使用 `mkdir -p` 创建 |
| `public/skills/` 目录不存在 | 使用 `mkdir -p` 创建 |
| `src_path` 路径不存在 | 返回错误，要求主 Agent 确认路径 |
| 主项目仓库有未提交的本地改动 | 先 `git stash`，3C 推送后 `git stash pop`；若冲突则报告 |
| 主项目仓库 push 被拒绝 | 先 `git pull --rebase`，再推送；若冲突则报告 |
| GitHub MCP 不可用 | 回退：提示用户手动创建空仓库（见 3A 回退路径） |
| Submodule 目录已存在 | 若为版本更新：`cd` 进 submodule 更新内容后 `git push`；主仓库仅更新 submodule 引用 SHA |
| `git submodule add` 失败 | 检查 GitHub 仓库是否已创建、URL 是否正确；修复后重试 |
| 笔记字数不足 300 字 | 补充内容直到满足最低要求 |
| SKILL.md 缺少 metadata 块 | 从输入信息中推断并补充（org=QuantSkills, license=GPL-3.0-only） |

---

## 约束

- **禁止**修改 `src/` 目录下的任何文件
- **禁止**覆盖 `public/skills/` 下已存在的 submodule（同名技能应更新 submodule 内部内容，而非删除重建）
- **禁止**在 `jobs/` 目录写入任何内容
- **禁止**删除 `.gitmodules` 文件
- Commit 信息必须包含 `Co-Authored-By: Claude <noreply@anthropic.com>`
- 笔记必须同时生成中文版（`.md`）和英文版（`.en.md`）
- 仓库名统一使用 `skill-` 前缀（不再使用 `build-`/`alpha-`）
- LICENSE 必须为完整 GPLv3 文本，不可用占位符
- README 必须包含免责声明与风险边界
- 安装指南必须覆盖 Codex / Claude Code / Cursor / Hermes / OpenClaw 五个平台
- SKILL.md 根层级必须包含 metadata 块（organization/repository/project_type/collection/license）
