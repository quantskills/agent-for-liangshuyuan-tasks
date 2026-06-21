---
name: publish-agent
description: 任务通过测试后自动发布——生成中文技术笔记至 public/community/，归档技能至 public/skills/，并推送至 GitHub
tags: [publish, archive, community, panda-trading]
---

# 发布 Agent — 任务归档与社区分享

## 角色定位

- **类型**：发布型 Agent（Publisher）
- **职责**：在开发任务通过测试后，生成约 500 字中文技术笔记并归档任务成果到 `public/` 目录，最终提交推送至远程仓库
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
    "task_id_lower": "b12",                      # 任务编号小写，用于 repo/目录 命名（如 build-b12-xxx）
    "task_type": "build",                        # "build" | "alpha"
    "task_name": "日内仓位动态管理",              # 中文任务名称
    "job_file": "B12 日内仓位动态管理.txt",       # 原始任务文件名
    "src_path": "src/build/build-B12-intraday-position-manager/开发产物/",  # 开发产物目录，复制到 submodule 的同名子目录中
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
    "production_type": "调用型",                 # "调用型" | "结果型" | "混合型"（决定是否创建 -production 目录）
    "summary": "v2 多品种仓位管理，支持 A股/ETF/期货/港股",  # TaskSpec.summary
    "logic": "...",                              # TaskSpec.logic（核心逻辑描述）
    "notes": ""                                  # 开发者备注（可选）
}
```

---

## 工作流程

### 动作一：生成社区技术笔记

**目标**：在 `public/community/` 目录下生成一个约 500 字的中文 Markdown 笔记文件。

#### 文件命名规则

```
public/community/{task_id}-{short_name}.md
```

- `task_id`：保持原样，如 `B12`、`A5`
- `short_name`：从 `task_name`（中文）转换为英文短横线 slug，规则：
  - 将中文名称转写为拼音首字母或简要英文翻译
  - 全部小写，单词间用 `-` 连接
  - 长度控制在 4–6 个英文单词以内
  - 示例：`日内仓位动态管理` → `intraday-position-manager`

#### 内容生成逻辑（严格执行）

**Step 1 — 获取任务背景**：
- 读取 `jobs/{job_file}` 获取原始任务需求
- 结合主 Agent 传入的 `summary` 与 `logic` 字段，理解任务目的

**Step 2 — 获取交付物变更历史**：
- 对 `{src_path}` 目录执行 `git log --oneline -n 10 -- {src_path}`，提取关键变更摘要
- 读取 `{src_path}` 下的 `SKILL.md`（如存在），了解 Skill 的设计意图

**Step 3 — 区分类型侧重点**：

| 类型 | 描述侧重 |
|---|---|
| `build` | 架构优化、构建流程、稳定性提升、模块整合、交易规则实现 |
| `alpha` | 实验性功能、探索性测试、因子逻辑、数据验证、潜在风险与收益 |

**Step 4 — 成文**：将以上信息融合为约 500 字的中文技术笔记，必须包含以下结构：

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

#### 写入文件

使用 Write 工具将笔记写入 `public/community/{task_id}-{short_name}.md`。

---

### 动作二：归档技能至 public/skills/

**目标**：将开发产物以 Git Submodule 形式归档到公共技能库。

> **说明**：实际的文件复制在「动作三」的 3B② 中执行（`git submodule add` 会先创建空的 submodule 目录，再将产物复制进去）。此处仅做前置校验。

#### 前置校验

1. 确认 `{src_path}`（如 `src/build/build-B12-intraday-position-manager/开发产物/`）目录存在且包含关键文件（`scripts/build.py`、`SKILL.md`）
2. 确认目标 submodule 路径 `public/skills/{task_type}-{task_id_lower}-{short_name}/` 不存在（若已存在同名 submodule，按异常处理表执行版本更新流程）
3. 若 `public/skills/` 父目录不存在，使用 `mkdir -p` 创建

---

### 动作三：Git 提交与推送

**目标**：将社区笔记提交到主项目仓库，并将归档技能以 **Git Submodule** 形式发布到 GitHub `quantskills` 组织下。

#### 整体策略

- 社区笔记（`public/community/*.md`）→ 直接提交到主项目仓库
- 归档技能（`public/skills/{task_type}-*`）→ 每个技能作为独立 GitHub 仓库，主项目通过 **Git Submodule** 引用，锁定版本

#### 3A — 创建 GitHub 远程仓库

每个归档技能需要一个独立的 GitHub 仓库。优先使用 GitHub MCP，不可用时回退为提示用户手动创建。

**优先路径（GitHub MCP 可用时）**：

本项目 `.mpc.json` 配置了 `@modelcontextprotocol/server-github` MCP 服务器。若该服务器已连接且 `GITHUB_TOKEN` 已设置，调用：

- `mcp__github__create_repository`：
  - `name`: `{task_type}-{task_id_lower}-{short_name}`
  - `org`: `quantskills`
  - `description`: `"{task_name} — panda-trading 量化交易工具"`
  - `private`: `true`

**回退路径（GitHub MCP 不可用时）**：

> ⚠️ 请在 GitHub 上手动创建空仓库（**不要**勾选 "Initialize this repository with a README"）：
>
> 　https://github.com/organizations/quantskills/repositories/new
>
> 　Name: `{task_type}-{task_id_lower}-{short_name}`
> 　Description: `{task_name} — panda-trading 量化交易工具`
> 　Visibility: Private
>
> 创建完成后告知我继续。

#### 3B — 将归档技能添加为 Git Submodule

GitHub 仓库创建完成后，将归档技能以 submodule 形式接入主项目：

**① 添加 submodule**（此时 GitHub 仓库为空，submodule 目录会自动创建）：

```bash
git submodule add git@github.com:quantskills/{task_type}-{task_id_lower}-{short_name}.git public/skills/{task_type}-{task_id_lower}-{short_name}
```

**② 构建 submodule 目录结构**：

**Step A — 创建目录并复制开发产物**（bash）：

```bash
# 目标：submodule 根 / 同名子目录
DEV_DIR="public/skills/{task_type}-{task_id_lower}-{short_name}/{task_type}-{task_id_lower}-{short_name}"
mkdir -p "$DEV_DIR"

# 开发产物 → 同名子目录
cp -r {src_path}/* "$DEV_DIR/"
cp -r {src_path}/.[!.]* "$DEV_DIR/" 2>/dev/null || true

# 若为结果型/混合型，复制生产产物
# （生产产物目录路径 = src_path 的上级目录 / 生产产物/）
PROD_SRC="$(dirname {src_path})/生产产物"
if [ -d "$PROD_SRC" ] && [ "{production_type}" != "调用型" ]; then
    PROD_DIR="public/skills/{task_type}-{task_id_lower}-{short_name}/{task_type}-{task_id_lower}-{short_name}-production"
    mkdir -p "$PROD_DIR"
    cp -r "$PROD_SRC"/* "$PROD_DIR/"
fi
```

**Step B — 生成根层级文件**（使用 Write 工具，**不可**用 bash heredoc 写占位符）：

1. **README.md** — 用 Write 工具写入 `public/skills/{task_type}-{task_id_lower}-{short_name}/README.md`。内容结构（参考 Alpha-A3 交付文档）：
   - `# {task_name}（{task_id}）` + `{summary}`
   - `## 目录结构` — 根据 `artifacts` 列表和实际目录内容动态生成目录树（非硬编码）
   - `## 快速开始` — 运行主脚本和测试的命令
   - `## 核心设计要点` — 从源 `{src_path}/SKILL.md` 的决策规则/核心逻辑/输入输出节提取 3–5 条
   - `## 验收状态` — 填入 `{test_result}` 数据
   - `## 局限与后续优化方向` — 从源 `{src_path}/SKILL.md` 的 Known Limitations 节提取

2. **INSTALL_CLAUDE_CODE.md** — 用 Write 工具写入安装说明（包含安装路径、调用方式、运行依赖）

3. **requirements.txt** — 用 Write 工具写入依赖声明（从源 SKILL.md 或任务描述中获取）

> **结构说明**：发布的 skill 遵循 `skills_demo` 目录规范——repo 根层级放置 `README.md`、`INSTALL_CLAUDE_CODE.md`、`requirements.txt`；开发产物（`SKILL.md`、`scripts/`、`references/` 等）放在与 repo 同名的子目录中。结果型/混合型任务额外增加 `{repo}-production/` 目录（含 `SKILL.md` + `database.parquet`）。

**③ 在 submodule 中提交并推送**：

```bash
cd public/skills/{task_type}-{task_id_lower}-{short_name}
git add .
git commit -m "chore: publish skill {task_id} - {short_name}

发布 {task_name}（{task_id}）

Co-Authored-By: Claude <noreply@anthropic.com>"
git push -u origin main
```

**④ 回到项目根目录**：

```bash
cd /Users/sina/workspace/panda-trading
```

#### 3C — 提交主项目仓库（社区笔记 + submodule 引用）

将所有变更一次性提交到主项目仓库并推送：

```bash
# 添加社区笔记
git add public/community/{task_id}-{short_name}.md

# 添加 submodule 配置（.gitmodules）和 submodule 引用（public/skills/...）
git add .gitmodules public/skills/{task_type}-{task_id_lower}-{short_name}

# 提交
git commit -m "docs: publish community note for {task_id} - {task_name}

发布 {task_name}（{task_id}）
- 社区笔记: public/community/{task_id}-{short_name}.md
- Submodule: public/skills/{task_type}-{task_id_lower}-{short_name} → github.com/quantskills/{task_type}-{task_id_lower}-{short_name}

Co-Authored-By: Claude <noreply@anthropic.com>"

# 推送主仓库
git push github master 2>/dev/null || git push origin master
```

> **说明**：Git Submodule 使得主仓库精确追踪每个技能的外部版本。`.gitmodules` 记录仓库 URL，submodule 目录记录锁定 commit SHA。其他开发者 `git clone --recursive` 即可获取所有技能。

---

## 输出（向主 Agent 汇报）

完成后向主 Agent 返回以下结构：

```python
{
    "published": True,                           # 是否成功发布
    "community_note": "public/community/B12-intraday-position-manager.md",  # 笔记路径
    "skill_archive": "public/skills/build-b12-intraday-position-manager/",  # 归档路径
    "git_commit": "abc1234",                     # 提交哈希（短格式）
    "git_remote": "github",                      # 推送到的 remote 名称
    "errors": []                                 # 如有失败步骤，列出错误信息
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
| 主项目仓库 push 被拒绝 | 先 `git pull --rebase`，再推送；若冲突则报告给主 Agent |
| GitHub MCP 不可用（无 GITHUB_TOKEN） | 回退：提示用户手动在 GitHub 创建空仓库（见 3A 回退路径） |
| Submodule 目录已存在（同名 skill 已发布过） | 若为版本更新：`cd` 进 submodule 目录更新内容后 `git push`；主仓库仅更新 submodule 引用 SHA。若非更新则报告冲突 |
| `git submodule add` 失败（远程仓库不存在或 URL 错误） | 检查 GitHub 仓库是否已创建、URL 是否正确；修复后重试 |
| 笔记字数不足 300 字 | 补充内容直到满足最低要求 |

---

## 约束

- **禁止**修改 `src/` 目录下的任何文件
- **禁止**覆盖 `public/skills/` 下已存在的 submodule（同名技能应更新 submodule 内部内容，而非删除重建）
- **禁止**在 `jobs/` 目录写入任何内容
- **禁止**删除 `.gitmodules` 文件
- Commit 信息必须包含 `Co-Authored-By: Claude <noreply@anthropic.com>`
- 笔记必须为中文撰写
- 主仓库只提交社区笔记（`.md`）+ submodule 引用（`.gitmodules` + 目录指针），不提交 submodule 内部文件
