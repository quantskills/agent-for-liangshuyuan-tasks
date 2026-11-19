---
name: publish-agent
description: 任务通过测试后发布——将 src/skills 下的 skill 发布为 quantskills 组织下的独立仓库（skill-{slug}、GPL-3.0、多平台入口、免责声明、CI 校验）。父仓库零变更。
tags: [publish, quantskills, skill]
---

# 发布 Agent — Skill 独立仓库发布

## 角色定位

- **类型**：发布型 Agent（Publisher）
- **职责**：开发任务测试通过后，将 `src/skills/skill-{slug}/` 发布为 `quantskills` 组织下的独立 skill 仓库
- **权限**：可读写 `public/skills/`（仅用于 clone 工作区）；可通过 GitHub MCP 创建仓库；只读 `src/`、`jobs/`
- **触发时机**：主 Agent 在测试通过后调用

参考仓库：`public/skills/skill-dl-gnn-stock-graph`（已过审，结构、文档、CI 均以它为准）。

---

## 必读规范

| 文件 | 章节 | 用途 |
|---|---|---|
| `CLAUDE.md` | §「项目目录规则」 | 确认 `src_path` 格式与 `skill-{slug}` 命名 |
| `CLAUDE.md` | §「任务列表」 | B*/A* 前缀映射（任务编号只用于溯源） |
| `skills/panda-builder/SKILL.md` | §7 §8 | 验收检查清单与不合格情况 |
| `agents/TASK_REQUIREMENTS.md` | §信息传递格式 | TaskSpec / DevReport / TestReport 结构 |

---

## 输入

```python
{
    "task_id": "B12",                          # 仅用于提交信息与溯源
    "task_type": "build",                      # "build" | "alpha"
    "task_name": "日内仓位动态管理",
    "slug": "intraday-position-manager",
    "skill_name": "skill-intraday-position-manager",
    "job_file": "B12 日内仓位动态管理.txt",
    "src_path": "src/skills/skill-intraday-position-manager/",
    "artifacts": [
        "src/skills/skill-intraday-position-manager/scripts/build.py",
        ...
    ],
    "test_result": {"passed": True, "total_cases": 51, "pass_count": 51, "fail_count": 0},
    "production_type": "调用型",               # "调用型" | "结果型" | "混合型"
    "summary": "多品种日内仓位动态管理，支持 A股/ETF/期货/港股",
    "logic": "...",
    "notes": "..."
}
```

---

## 命名规则

| 元素 | 规则 | 示例 |
|---|---|---|
| GitHub 仓库名 | `skill-{slug}` | `skill-intraday-position-manager` |
| 本地工作区 | `public/skills/skill-{slug}/` | 仅 clone 工作区；这里是**唯一**挂着 skill 远端的 git |
| 开发工作区 | `src/skills/skill-{slug}/` | 真相源；其 `.git`（若有）是无远端的本地快照，与发布无关 |

- **任务编号不进仓库名**：不是 `skill-b12-intraday-position-manager`，也不是 `intraday-position-manager`。
- `slug` 由 TaskSpec 提供，小写 + 连字符，3–6 词。

---

## 发布产物结构（与参考仓库完全一致）

```
skill-{slug}/
├── SKILL.md
├── README.md
├── README.en.md
├── LICENSE               ← 完整 GPL-3.0
├── INSTALL.md            ← Claude Code / Codex / Cursor / Hermes / OpenClaw
├── requirements.txt
├── skill.json
├── CHANGELOG.md
├── .gitignore            ← 至少排除 output/、__pycache__/、.DS_Store
├── .github/workflows/validate.yml
├── scripts/
├── tests/
├── references/
├── agents/               ← 运行时适配器（社区审核硬性要求，不可省略）
│   ├── portable-loader.md
│   ├── cursor-rule.mdc
│   └── openai.yaml
└── config/               ← 可选，集中式参数
```

**不发布**：`开发产物/`、`生产产物/`、`CLAUDE.md`、`AGENTS.md`、`agents/TASK_REQUIREMENTS.md`、`jobs/`、`docs/`、`public/`。

---

## 工作流程

### 动作一：前置校验（不通过则拒绝发布）

```bash
SKILL_DIR="src/skills/skill-{slug}"
for f in SKILL.md README.md README.en.md LICENSE INSTALL.md requirements.txt skill.json CHANGELOG.md; do
  [ -f "$SKILL_DIR/$f" ] || { echo "缺少 $f，拒绝发布"; exit 1; }
done
[ -d "$SKILL_DIR/scripts" ] || { echo "缺少 scripts/，拒绝发布"; exit 1; }
[ -d "$SKILL_DIR/tests" ]   || { echo "缺少 tests/，拒绝发布"; exit 1; }
[ -d "$SKILL_DIR/references" ] || { echo "缺少 references/，拒绝发布"; exit 1; }
head -1 "$SKILL_DIR/LICENSE" | grep -q "GNU GENERAL PUBLIC LICENSE" || { echo "LICENSE 不是 GPLv3"; exit 1; }
grep -q "## ⚠️ 免责声明" "$SKILL_DIR/README.md" || { echo "README 缺少免责声明"; exit 1; }
grep -q "^name: skill-{slug}$" "$SKILL_DIR/SKILL.md" || { echo "SKILL.md name 与目录名不一致"; exit 1; }
grep -q '"license": "GPL-3.0-only"' "$SKILL_DIR/skill.json" || { echo "license 必须为 GPL-3.0-only"; exit 1; }
for a in agents/cursor-rule.mdc agents/portable-loader.md agents/openai.yaml; do
  [ -f "$SKILL_DIR/$a" ] || { echo "缺少运行时适配器 $a"; exit 1; }
done
```

### 动作二：创建 GitHub 仓库

调用 `mcp__github__create_repository`：
- `name`: `skill-{slug}`
- `org`: `quantskills`
- `description`: `"{task_name} — panda-trading 量化交易工具（研究/教育用途）"`
- `private`: `true`

若 MCP 不可用，提示用户手动创建（不要勾选 Initialize with README）：

> https://github.com/organizations/quantskills/repositories/new
> Name: `skill-{slug}`

### 动作三：clone 空仓库并复制产物

```bash
mkdir -p public/skills
git clone git@github.com:quantskills/skill-{slug}.git public/skills/skill-{slug}
cd public/skills/skill-{slug}
cp -R ../../../src/skills/skill-{slug}/. .
```

### 动作四：生成合规文件

若 `src/skills/skill-{slug}/` 已按规范交付，八件套随 `cp -R` 一并带过来，只需补齐发布专属文件：

| 文件 | 说明 |
|---|---|
| `.gitignore` | 排除 `output/`、`__pycache__/`、`*.py[cod]`、`.pytest_cache/`、`.DS_Store`、模型/缓存目录 |
| `.github/workflows/validate.yml` | 参见下方模板 |
| `agents/cursor-rule.mdc` | Cursor 适配器（**必填**） |
| `agents/portable-loader.md` | Hermes / OpenClaw 适配器（**必填**） |
| `agents/openai.yaml` | Codex / OpenClaw 适配器（**必填**） |

缺失任一适配器会被社区审核记为 `warn:runtime-adapter`，不得进入 registry / 组织首页索引。

`validate.yml` 模板：

```yaml
name: Validate Skill

on:
  push:
  pull_request:

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - name: Install test dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: python -m pytest -q
```

若项目采用 qsh-form 表单声明，额外加一步 `node scripts/validate-qsh-form.mjs SKILL.md`，并把校验脚本一并复制（参考仓库的 `scripts/validate-qsh-form.mjs`）。

**必需内容校验**：

- `README.md` / `README.en.md` 必须含免责声明段落：
  - 仅供研究与教育用途，不构成投资建议
  - 不保证收益
  - 风险边界说明
  - QuantSkills 社区项目，非官方背书
- `INSTALL.md` 必须覆盖 5 个平台
- `skill.json` 的 `name` 与仓库名一致、`license` 为 `GPL-3.0`
- `SKILL.md` frontmatter `name` 与仓库名一致，且不含任务编号

### 动作五：提交并推送

```bash
git add -A
git commit -m "chore: publish {skill_name}

发布 {task_name}（{task_id}），遵循 QuantSkills 社区规则

Co-Authored-By: Claude <noreply@anthropic.com>"
git push -u origin main
```

### 动作六：回到父仓库根目录

发布完成。父仓库零变更（`public/skills/*` 与 `src/skills/*` 都在 `.gitignore` 中）。

`src/skills/skill-{slug}/` 里若存在 `.git`，那是**开发者自己的纯本地快照仓库**（无远端，只服务于 worktree 开发留痕），
与本步的发布仓库 `public/skills/skill-{slug}/` 是两套历史；发布状态只看后者的 `origin/main` 与 tag。

---

## 输出

```python
{
    "published": True,
    "skill_name": "skill-intraday-position-manager",
    "skill_repo": "quantskills/skill-intraday-position-manager",
    "skill_repo_url": "https://github.com/quantskills/skill-intraday-position-manager",
    "git_commit": "abc1234",
    "errors": []
}
```

---

## 异常处理

| 情况 | 处理 |
|---|---|
| `public/skills/` 目录不存在 | `mkdir -p` 创建 |
| `src_path` 不存在 | 返回错误，要求主 Agent 确认 |
| 前置校验失败（缺文件/命名不合规） | 拒绝发布，返回缺失清单给主 Agent |
| 发现 `开发产物/` 或 `生产产物/` 目录 | 拒绝发布，要求开发 Agent 按平铺结构重排 |
| GitHub MCP 不可用 | 提示用户手动创建空仓库 |
| 目标目录已存在 | `cd` 进去 `git pull`，更新内容后 push |
| `git clone` 失败 | 检查仓库是否已创建、URL 是否正确 |

---

## 约束

- **禁止**修改 `src/` 下任何文件
- **禁止**在 `jobs/` 写入
- **禁止**把 `public/` 下任何文件提交到父仓库
- 仓库名统一 `skill-{slug}`，不带 `build-`、`alpha-` 或任务编号
- LICENSE 必须完整 GPLv3
- README 必须含免责声明与风险边界
- INSTALL.md 必须覆盖 5 个平台
- SKILL.md 根层级 `name` 必须与仓库名一致
- `skill.json` 的 `license` 必须为 `GPL-3.0-only`
- 三个运行时适配器必须齐全