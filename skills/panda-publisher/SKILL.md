---
name: panda-publisher
description: 当需要把 src/skills 下已过验收的 skill 发布为 quantskills 组织下的独立仓库，并产出可分发给其它 agent 的 zip 包时，使用此 skill。先用 panda-builder 做发布前验收，再同步到 public 同名工作区、远端仓库存在则 push、不存在则创建后 push，最后用 git archive 生成与克隆结果完全一致的 zip。
tags: [quant, publish, release, git, zip]
---

# Panda Publisher — Skill 发布流程

## 工具定位
- 工具类型：发布流程（Release）
- 解决问题：把 `src/skills/skill-{slug}/` 的交付物，变成三样东西——
  1. `public/skills/skill-{slug}/` 里与远端一致的 clone 工作区；
  2. `github.com/quantskills/skill-{slug}` 上的独立仓库（存在即 push，不存在则创建）；
  3. `public/dist/skill-{slug}-v{version}.zip` 分发包，供其它 agent 直接安装。
- 使用对象：开发者（Claude Code）、发布 Agent（`agents/publish-agent/`）

## 触发时机

任务测试通过后、用户要求"发布 / 上线 / 打包"时。**每一步都是闸门，任一失败立即停止并汇报，不得跳过。**

## 前置依赖（强制）

本 skill 不自建验收标准，**先加载 `skills/panda-builder/SKILL.md`**：

| 引用 | 用途 |
|---|---|
| panda-builder §2 §5 §6 §7 | 目录结构、SKILL.md / skill.json 模板、5 平台适配器 |
| panda-builder §8.1 §8.2 §8.3 | 社区审核硬性 fail 项、适配器 warn 项、内容禁令 |
| panda-builder §9 | 发布前逐项验收清单 |
| panda-builder §10 | 不合格情况：命中任一条即**禁止发布** |

参考仓库：`public/skills/skill-dl-gnn-stock-graph`（已过审）。

---

## 0. 三条铁律

1. **`src/skills/skill-{slug}/` 是唯一真相源。** `public/skills/skill-{slug}/` 只是 clone 工作区。
   同步方向永远 `src → public`，**严禁** `rsync --delete` 反向同步（历史事故：反向同步把旧文档覆盖回 src，冲掉了新写的接口说明）。
   注意这里涉及**三套互不相干的 git**（详见 `CLAUDE.md` §「版本控制归属」）：父仓库忽略 `src/skills/*` 与 `public/skills/*`；
   `$SRC` 里可能另有一个 `git init` 出来的**纯本地快照仓库**（无远端，只用于 worktree 开发留痕）；
   `$PUB` 才是挂着 `quantskills/skill-{slug}` 远端的发布仓库。**发布判断只看 `$PUB` 的 git**，
   绝不因为 `$SRC` 有提交、有分支或有 tag 就认为「已经发过了」。
2. **只发布闸门全绿的包。** `pytest` 必须 0 failed；skip 必须能说出理由。
3. **分发物由 git 的"已跟踪集合"生成，不用 `zip -r` 打工作树。**
   `git archive` 天然等于 `git clone` 的结果：`.gitignore` 排除的运行产物、真实行情载荷、`.DS_Store`、`.git/` 一律进不去。手工打工作树会把机器本地数据发到公网。

---

## 1. 输入

```python
{
    "task_id": "B12",                       # 只用于提交信息与溯源，不进仓库名/包名
    "task_name": "日内仓位动态管理",
    "slug": "intraday-position-manager",
    "skill_name": "skill-intraday-position-manager",
    "src_path": "src/skills/skill-intraday-position-manager/",
    "test_result": {"passed": True, "total_cases": 51, "pass_count": 51, "fail_count": 0},
    "summary": "多品种日内仓位动态管理",
}
```

路径常量（后续所有命令直接引用）：

```bash
PROJECT_ROOT=$(pwd)
SKILL_NAME=skill-{slug}
SRC="$PROJECT_ROOT/src/skills/$SKILL_NAME"
PUB="$PROJECT_ROOT/public/skills/$SKILL_NAME"
DIST="$PROJECT_ROOT/public/dist"
REMOTE="git@github.com:quantskills/$SKILL_NAME.git"
VERSION=$(python3 -c "import json;print(json.load(open('$SRC/skill.json'))['version'])")
echo "publishing $SKILL_NAME v$VERSION"
```

`$SRC` 不存在 → 直接返回错误给主 Agent，**不允许**"那就从 public 发"。

---

## 2. 阶段一：发布前验收（panda-builder 闸门）

```bash
cd "$SRC"
for f in SKILL.md README.md README.en.md LICENSE INSTALL.md requirements.txt skill.json CHANGELOG.md; do
  [ -f "$f" ] || echo "FAIL: 缺 $f"
done
for a in agents/cursor-rule.mdc agents/portable-loader.md agents/openai.yaml; do
  [ -f "$a" ] || echo "FAIL: 缺运行时适配器 $a"
done
[ -d 开发产物 ] || [ -d 生产产物 ] && echo "FAIL: 存在禁用交付目录（panda-builder §10）"
head -1 LICENSE | grep -q "GNU GENERAL PUBLIC LICENSE" || echo "FAIL: LICENSE 不是 GPL-3.0 全文"
grep -q "\"name\": \"$SKILL_NAME\"" skill.json || echo "FAIL: skill.json name 与目录名不一致"
grep -q '"license": "GPL-3.0-only"' skill.json || echo "FAIL: license 必须 GPL-3.0-only"
grep -q "^name: $SKILL_NAME\$" SKILL.md || echo "FAIL: SKILL.md frontmatter name 不一致"
grep -q "## ⚠️ 免责声明" README.md || echo "FAIL: README.md 缺免责声明"
grep -qiE "^#+ .*(Disclaimer|免责声明)" README.en.md || echo "FAIL: README.en.md 缺英文免责声明"
for p in "Claude Code" Codex Cursor Hermes OpenClaw; do
  grep -q "$p" INSTALL.md || echo "FAIL: INSTALL.md 未覆盖 $p"
done
# 内容禁令：只匹配肯定式承诺，否定式免责声明不算违规
grep -rnE "(稳赚|必涨|保证(收益|盈利|回报)|无风险|荐股|官方认证)" README.md README.en.md SKILL.md \
  | grep -vE "(不保证|无法保证|不构成|不提供|无需|未经)" && echo "FAIL: 命中内容禁令"
# 凭证与私货：任何 token / 内网地址 / 私人邮箱都不许随包发布（git@github.com 是 clone 地址，不算邮箱）
grep -rnEi "(api[_-]?key|secret|passwd|password|access[_-]?token|token)[[:space:]]*[:=][[:space:]]*['\"][^'\"]{8,}" \
  --include='*.py' --include='*.md' --include='*.json' --include='*.yaml' . | grep -v 'your-\|<TOKEN>\|example' \
  && echo "FAIL: 疑似凭证"
grep -rnE "10\.[0-9]+\.[0-9]+\.[0-9]+|192\.168\.|localhost:[0-9]+" --include='*.md' --include='*.py' . \
  && echo "WARN: 疑似内网地址"
```

**功能闸门**（结构与文档合规不等于能跑）：

```bash
cd "$SRC"
python3 scripts/build.py || echo "FAIL: 入口脚本跑不通"
python3 -m pytest tests -q 2>&1 | tail -5
```

- 出现 `No module named pytest` → 换用带 pytest 的解释器（本机：`/opt/homebrew/bin/python3.11 -m pytest`）。
- 若 skill 声明"零三方依赖 / 纯标准库"，**再用系统 `python3`（本机 3.9.6，无三方库）跑一遍** `scripts/build.py`，数字必须一致。这条声明是读者最常照抄的。

---

## 3. 阶段二：版本与打包一致性

版本号有 **4 个**落点，漂移是常态（实测过 `openai.yaml` 停在 0.1.0 而 `skill.json` 已 0.13.1）：

```bash
cd "$SRC"
echo "skill.json : $(python3 -c "import json;print(json.load(open('skill.json'))['version'])")"
echo "CHANGELOG  : $(grep -m1 -oE '## \[[0-9]+\.[0-9]+\.[0-9]+\]' CHANGELOG.md)"
echo "SKILL.md   : $(grep -m1 -E '^(version|metadata:)|version:' SKILL.md | head -1)"
echo "openai.yaml: $(grep -m1 -E '^[[:space:]]*version:' agents/openai.yaml)"
```

四处必须是同一个 `$VERSION`。不一致 → 先改文档再发布，**禁止**"发完再补"。

**随包发布的东西必须在包里**（结果型 skill 最容易翻车的一处：把验收锚点放在 `output/` 里，而 `output/` 被 gitignore，从 git 安装的人根本拿不到）：

```bash
cd "$SRC"
[ -f .gitignore ] && grep -qE '^output/?$|^output/\*$' .gitignore || echo "FAIL: .gitignore 未排除 output/"
# 冻结基线 / 验收锚点若属于交付物，必须用否定规则逃出 gitignore，并在此确认
grep -qE '^!baselines/' .gitignore && echo "OK: 锚点随包发布"
ls baselines/*.json 2>/dev/null && echo "注意: baselines/ 有锚点文件，确认它会被 git 跟踪（见阶段四 ls-files 核对）"
```

> **`.gitignore` 的两条硬规则（本轮真实翻车处，务必照做）**
> 1. **目录被整体忽略后，里面的 negation 永远不生效。** 写了 `output/` 再在文件末尾追加
>    `!output/report.json` 是**无效**的——必须先删掉 `output/` 那一行，改成 `output/*` 加点名放行。
>    v0.3.2 就是这么"发布了"一份根本不在包里的证据，直到解包核对才暴露。
> 2. **反向 grep 会打印假绿。** `git ls-files | grep output/ | grep -v <放行清单>` 在
>    **零个** output 文件被跟踪时输出为空、退出码非零，`|| echo "OK"` 于是报"检查通过"。
>    证据类文件一律用**正向断言**：逐个 `git ls-files --error-unmatch <path>`，
>    以及 `unzip -l "$ZIP" | grep <path>`，两者都绿才算入包。

---

## 4. 阶段三：远端仓库——存在则 push，不存在则创建

```bash
GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=10' \
  git ls-remote --exit-code --heads "$REMOTE" >/dev/null 2>&1; echo "exit=$?"
```

> macOS 没有 GNU `timeout` 命令（`command not found: timeout`），别用 `timeout git ls-remote` 包一层——
> 用上面的 `ConnectTimeout` + `BatchMode=yes`，既不会挂在口令提示上，也不会挂在网络上。

| exit | 含义 | 动作 |
|---|---|---|
| `0` | 仓库存在且有分支 | **走增量发布**（阶段四起），禁止重复建库 |
| `2` | 仓库存在但为空（无任何 ref） | 走首发：clone 后直接提交 `main` |
| `128` | 仓库不存在 / 无权限 / SSH 未配置 | 先建库；建库前先确认 SSH 可用：`ssh -T git@github.com` |

> `ls-remote` 返回 128 不能直接断定"仓库不存在"——SSH key 没加载时同一个库也是 128。看到 128 先跑 `ssh -T git@github.com` 再决定。

**建仓三选一，按顺序探测**（发布只建 **private** 库，公开由社区审核后决定）：

```bash
# 方式 A：gh CLI
command -v gh >/dev/null && gh auth status >/dev/null 2>&1 \
  && gh repo create "quantskills/$SKILL_NAME" --private \
       --description "{task_name} — QuantSkills 量化交易 skill（研究/教育用途）"
```

```text
# 方式 B：GitHub MCP（mcp__github__create_repository）
name: skill-{slug}   org: quantskills   private: true
description: "{task_name} — panda-trading 量化交易工具（研究/教育用途）"
```

```text
# 方式 C：都没有 → 停下来请用户手动建空仓库（不要勾选 Initialize with README）
https://github.com/organizations/quantskills/repositories/new
Name: skill-{slug}   Visibility: Private
```

方式 C 触发时，把已完成的本地发布与 zip 先行交付，并在汇报里写明"远端待人工建仓后 push"，不要假装已发布。

---

## 5. 阶段四：同步到 public 同名工作区

```bash
mkdir -p "$DIST"
if [ ! -d "$PUB/.git" ]; then
  mkdir -p "$PROJECT_ROOT/public/skills"
  git clone "$REMOTE" "$PUB" || echo "clone 失败：确认仓库已建、URL 正确、SSH 可用"
fi
```

**clone 后先看工作区干净不干净——这一步不能省：**

```bash
cd "$PUB"
git status --porcelain -b | head -40
git log --oneline -3
git fetch origin -q && echo "local HEAD : $(git rev-parse --short HEAD)" && echo "origin/main: $(git rev-parse --short origin/main)"
```

| 状态 | 处理 |
|---|---|
| 干净且 `HEAD == origin/main` | 正常，往下同步 |
| **有未提交改动 / 有未推送提交** | **停止并汇报**。这通常意味着真正的开发成果住在工作区里而没进 git（真实事故：远端停在 v0.3.0，`public` 工作区里躺着 3,370 行未提交的 v0.4.0–v0.7.0）。先判明 `src` 与工作区谁更新，人工确认后才能覆盖 |
| 落后远端 | `git pull --ff-only`；不能快进则停下问用户 |

**同步（唯一的正确方向）：**

```bash
rsync -a --delete \
  --exclude='/.git' --exclude='.claude/' --exclude='.idea/' --exclude='.vscode/' \
  --exclude='output/' --exclude='__pycache__/' --exclude='*.pyc' --exclude='.pytest_cache/' \
  --exclude='.DS_Store' --exclude='.venv/' --exclude='venv/' \
  "$SRC/" "$PUB/"
```

- `--delete` 让 src 里已删除的文件在发布分支上同步消失；`--exclude` 同时保护这些路径不被删。
- **排除 git 必须写 `/.git`，不能写 `.git/`**：`--exclude='.git/'` 只匹配目录，而 linked worktree
  的 `.git` 是一个 **gitdir 指针文件**，于是 `--delete` 会把它删掉、worktree 当场掉线
  （`fatal: not a git repository`）。补救：向 `.git` 写回
  `gitdir: <主仓库>/.git/worktrees/<name>`。
- `--exclude='.git/'` 是**双向**起作用的一层：既保住 `$PUB` 自己的发布历史，也挡住 `$SRC` 那个纯本地快照仓库的 `.git/`
  被复制进工作区。因此**不能**用「`$SRC` 的 git 历史」当发布依据，也不能把它拷进包里。
- 机器本地数据（真实行情载荷、`output/`）不靠 rsync 排除，**靠 `.gitignore` 挡住**——所以下面的 `git add -A` + `ls-files` 核对才是真正的防线。

**暂存并核对"将发布的文件集合"：**

```bash
cd "$PUB"
git add -A
git status --short
git diff --cached --name-only | grep -E '(^|/)(\.env|\.mpc\.json)|token|secret|credential' && echo "FAIL: 敏感文件将被提交"
git ls-files | grep -E '^tests/fixtures/(raw|landed)/' | grep -v 'README\.md' && echo "FAIL: 机器本地数据载荷混入交付集"
git ls-files | grep -E '^output/' && echo "FAIL: 运行产物混入交付集"
```

**在发布工作区里复跑一遍测试**（`.gitignore`、CI、锚点路径只有在这里才是发布时的真实形态；`src` 全绿而 `public` 红，多半就是这里的 ignore/CI 文件过期）：

```bash
cd "$PUB" && /opt/homebrew/bin/python3.11 -m pytest tests -q 2>&1 | tail -8
```

红 → 回 `src` 修，重新走阶段四。**禁止**只在 `public` 里改好就算完（下一次同步会冲掉）。

---

## 6. 阶段五：提交、打 tag、推送

```bash
cd "$PUB"
git commit -m "feat: {中文一句话变更} v$VERSION" \
  -m "发布 {task_name}（{task_id}），遵循 QuantSkills 社区规则

Co-Authored-By: Claude <noreply@anthropic.com>"
git tag -a "v$VERSION" -m "v$VERSION — {一句话摘要}"
git push -u origin main --follow-tags
git rev-parse --short HEAD   # 记下这个 sha，汇报用
```

- 无新增改动（`git commit` 报 nothing to commit）且远端已含该版本 → 如实说"远端已是最新，本次无变更"，不要空推、不要造空提交。
- push 被拒（non-fast-forward）→ `git pull --rebase` 后重推；**禁止** `--force`。

---

## 7. 阶段六：生成 zip 并自证

```bash
cd "$PUB"
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" || echo "FAIL: HEAD 未推送，zip 会远端不一致"
ZIP="$DIST/$SKILL_NAME-v$VERSION.zip"
rm -f "$ZIP"
git archive --format=zip --prefix="$SKILL_NAME/" -o "$ZIP" HEAD
shasum -a 256 "$ZIP"
```

`--prefix` 保证解压即得 `skill-{slug}/` 一层目录，安装方 `cp -R` 到 skills 目录就能用。

**内容自证**（缺件与夹带都要查）：

```bash
for f in SKILL.md README.md README.en.md LICENSE INSTALL.md requirements.txt skill.json CHANGELOG.md; do
  unzip -l "$ZIP" | grep -q "/$f\$" || echo "FAIL: zip 缺 $f"
done
unzip -l "$ZIP" | grep -E "/(\.git/|output/|__pycache__/|\.DS_Store)" && echo "FAIL: zip 混入非交付物"
unzip -l "$ZIP" | grep -q "/agents/openai.yaml$" || echo "FAIL: zip 缺运行时适配器"
```

**冷克隆冒烟**——这是读者最常照抄的路径，也是唯一能证明"包里东西自洽"的检查：

```bash
TMP=$(mktemp -d)
unzip -q "$ZIP" -d "$TMP"
( cd "$TMP/$SKILL_NAME" && python3 scripts/build.py && /opt/homebrew/bin/python3.11 -m pytest tests -q ) | tail -5
rm -rf "$TMP"
```

冒烟不过 → 说明包里缺文件（典型：锚点、fixture 被 ignore 规则挡住），回阶段三补 `.gitignore` 否定规则，重发新版本，**不要**手往 zip 里塞文件。

**确认 zip 不进父仓库：**

```bash
cd "$PROJECT_ROOT"
grep -q '^public/dist/$' .gitignore || printf '\n# 发布分发包：本机/内部分发用，不入库\npublic/dist/\n' >> .gitignore
git status --porcelain public/ | grep . && echo "WARN: public/ 下有文件被父仓库跟踪，应全部 ignore"
```

---

## 8. 发布汇报（固定字段）

```python
{
    "published": True,
    "skill_name": "skill-{slug}",
    "version": "0.7.0",
    "skill_repo": "quantskills/skill-{slug}",
    "skill_repo_url": "https://github.com/quantskills/skill-{slug}",
    "repo_action": "pushed" | "created+pushed" | "pending_manual_create",
    "git_commit": "abc1234",
    "git_tag": "v0.7.0",
    "workspace": "public/skills/skill-{slug}/",
    "tests": {"passed": 224, "failed": 0, "skipped": 1, "skip_reason": "..."},
    "zip": {"path": "public/dist/skill-{slug}-v0.7.0.zip", "sha256": "...", "files": 41, "size_kb": 180},
    "cold_clone_smoke": "build.py ok / pytest 224 passed",
    "excluded_from_package": ["output/", "tests/fixtures/raw/*", "tests/fixtures/landed/*", ".git/"],
    "errors": [],
}
```

`published` 只有在**远端 sha 已确认 == 本地 HEAD** 时才为 `true`；仅本地提交/仅生成 zip 时写 `false` 并在 `errors` 里说明缺哪一步。

---

## 9. 异常处理

| 情况 | 处理 |
|---|---|
| `$SRC` 缺八件套之一 / 缺适配器 | 拒绝发布，回开发 Agent（panda-builder §10） |
| `src` 与 `public` 内容互相矛盾，无法判断谁更新 | 停止，列差异给用户，等指令。绝不默认覆盖任一侧 |
| `public` 工作区有未提交改动 | 先 `git stash` 前先汇报；确认改动无用才可丢弃，默认保留并停止 |
| `pytest` 有 failed | 拒绝发布。"只有 2 条红、是打包测试不算功能问题"也拒绝——打包测试正是发布闸门 |
| 远端不存在且无建仓权限 | 本地提交 + zip 照常交付，`repo_action: pending_manual_create`，给出建仓链接 |
| push 报 `Permission denied (publickey)` | SSH key 未加载：`ssh-add -l`；提示用户，不要改用 HTTPS 明文凭证 |
| 版本号在远端已有同名 tag | 说明本次改动没升版本。回 `src` 升 `$VERSION` 重发，禁止强推覆盖 tag |
| 文档引用的脚本在包里不存在 | 曾真实发生（文档写 `fixture_generator.py`，仓库里没有）。阶段二把 `scripts/` 清单与 `SKILL.md`/`references/` 引用的路径逐条对一遍 |

---

## 10. 禁止事项

- 禁止绕过 panda-builder 验收直接发布，或自己在本 skill 里另立一套验收标准
- 禁止 `src ← public` 反向同步，或对 `$SRC` 用 `rsync --delete`
- 禁止 `zip -r` 打工作树（会带进 `.git/`、`output/`、机器本地真实数据）
- 禁止把 `public/` 下任何文件提交到父仓库（`public/skills/*`、`public/dist/` 必须 ignore）
- 禁止把任务编号写进仓库名、tag、zip 文件名（编号只进 `skill.json.source_task` 与提交信息）
- 禁止把凭证、内网地址、私人邮箱留在包内；`~/.pandadata/*.env`、`.mpc.json` 一类只在本地
- 禁止 `--force` 推送、覆盖已存在的 tag、或在测试未全绿时申请公开 / 收录 / 进 registry
- 禁止只发 zip 不发 git，或只 push 不生成 zip——两者是同一版本的两份交付物，缺一即未完成
