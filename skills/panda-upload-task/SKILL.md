---
name: panda-upload-task
description: 当需要把量枢院任务平台（lsy.quant789.com/app）中"创作中/待创作"任务与本项目已发布 skill 对齐，并将 skill 功能说明、分发 zip、GitHub 地址回填到任务成果表单时，使用此 skill。基于 opencli browser 驱动真实页面填写，默认只保存草稿，正式提交审核必须显式确认。
tags: [quant, upload, task, opencli, lsy]
---

# Panda Upload Task — 量枢院任务成果回填

## 工具定位
- 工具类型：发布收尾（Upload / 回填）
- 解决问题：任务在平台处于「创作中 / 待创作」，而 skill 已在 `public/skills/` + `github.com/quantskills` 发布完毕，需要把三样交付物（功能说明、zip 包、GitHub 地址）逐个填回任务详情页的成果表单。
- 使用对象：开发者（Claude Code）、发布 Agent
- 上游依赖：`panda-publisher`（先有 pushed 的远端仓库与 zip 产物，本 skill 不自建发布链路）

## 前置检查（未通过就停，不得带病执行）

执行前逐项确认，**dry_run（只出计划不动页面）只阻塞第 1 项；真实执行四项全部阻塞**：

1. **Python ≥ 3.9**（本机 3.9.6 实测跑通），标准库即可（零三方依赖；pytest 需 3.11）。
2. **opencli 桥接可用**：`opencli doctor` 的 `extensionConnected=true` 且 `connectivity.ok=true`。读取任务列表走 `eval fetch`，不需要窗口可见。
3. **浏览器窗口可见**：平台的「开始创作 / 填写成果 / 保存草稿」是真实 DOM 点击，opencli 原生输入要求 Chrome 标签页**未被最小化且在最前**。脚本每次写操作前会用 osascript 自动置前（限定 URL 含 `lsy.quant789.com` 的窗口）；置前失败直接报错停止，不盲点。
4. **登录态存在**：`GET /api/v1/auth/me` 返回 200。没有登录态时停下请用户在 Chrome 里登录一次，**严禁**代填账号密码。

## 1. 任务筛选规则

任务列表来自 `GET /api/v1/tasks`（同源 fetch，页面已带 cookie）。只处理状态为：

| API status | 平台展示 | 处理动作 |
|---|---|---|
| `IN_PROGRESS` | 创作中 | 直接填写成果 |
| `PENDING` | 待创作 | 先点「开始创作」使状态转为 IN_PROGRESS，再填写 |
| `PENDING_REVIEW` / `COMPLETED` / `REWORK` 等 | 待审核 / 已完成 / 需修改 | **一律跳过**并在报告中列出 |

> 点「开始创作」会把任务从待创作推进到创作中并启动计时口径，属于平台侧状态变更；报告 `status_before/status_after` 必须如实记录。

## 2. 名称匹配规则（任务名 → skill 名）

按优先级三级匹配，**任一任务只能得到一个匹配；出现歧义一律进 `unmatched`，禁止猜**：

1. **任务编号显式映射** `aliases.task_numbers`：`{"TS202610193FE946": "skill-jev-history-replay", ...}`，最高优先。
2. **英文名括号直译**：任务标题里全角/半角括号内的英文 slug（如 `视频转文字Skill（video-to-text）` → `skill-video-to-text`），目录必须真实存在。
3. **关键词别名表** `aliases.keywords`：标题命中关键词且全表内唯一指向一个已存在目录才算匹配。

内置种子别名（随任务新增在 config 中扩充，不改代码）：

| 关键词 | skill 目录 |
|---|---|
| `JEV` | `skill-jev-history-replay` |
| `约束` / `异常数据` | `skill-constraint-stress-test` |
| `观点` | `skill-opinion-to-ruler` |
| `图神经网络` / `GNN` | `skill-dl-gnn-stock-graph` |
| `仓位` | `skill-intraday-position-manager` |
| `止盈止损` | `skill-auto-stop-loss-take-profit` |

## 3. 成果资源来源（全部取自"已发布"形态，禁止就地取材）

| 表单字段 | 来源 | 闸门 |
|---|---|---|
| 成果说明（textarea） | `git show <ref>:README.md` 的功能段提取（真实标题 + 简介段 + 「它解决什么问题」等首个正文章节，容忍 `# README` 伪标题），截断默认 1200 字 | 提取为空 → blocked |
| 成果链接（input[url]） | `git remote get-url origin` 规范化为 `https://github.com/<org>/<repo>` | 无 remote → blocked |
| 本地附件（input[file]） | `public/dist/skill-{slug}-v{version}.zip`；缺失时对 `<ref>` 执行 `git archive` 生成并自检八件套+适配器 | 见下 |

- **版本选择（用户规则）：`public/dist/` 里同 skill 多版本 zip 时，取「最后一个已发布的」**：
  候选 = HEAD 版本 ∪ {dist 中存在且 origin 有 `v{version}` tag 的版本}，按 semver **数值**比较取最大（`0.17.0 > 0.2.0`，禁止字符串比较）；
  dist 里没有 tag 的新版本文件一律无视（宁可用已发布旧版，不上传幽灵包）。选中的 `<ref>` = HEAD 或对应 tag，成果说明与 zip 都按 `<ref>` 取。
- `HEAD == origin/main` 才允许（先 `git fetch`）。不一致 → blocked，提示先跑 `panda-publisher`。
- 工作区有未提交改动 → **warn** 并在报告注明"工作树 vX vs 已发布 vY，本次按已发布版本提交"，不自动提交、不 stash。
- zip 必须 ≤ 50MB；校验：`zipfile` 完整性（BadZipFile → blocked 稍后重试，防并行写入半截包）、8 根文件 + `agents/openai.yaml` 齐全、不得含 `.git/ output/ __pycache__/`；报告记录 `sha256`。

## 4. 表单与页面知识（实测于 2026-11-18，字段以现场 state 为准）

- 路由：列表 `/app/tasks`，详情 `/app/tasks/{id}`；详情按钮依次为「开始创作」→「填写成果」。
- 成果弹窗 `section[role=dialog]`：`textarea`（成果说明）、`input[type=url]`（成果链接，placeholder `https://github.com/...`）、`input[type=file]`（本地附件，多记录≤20 个、单文件≤50MB）。
- 弹窗按钮：「保存草稿」「提交审核」；正式提交后**版本锁定**，草稿可反复修改。
- 草稿附件区：`.attachment-item.editable` 内 `a.attachment-link[download=<文件名>]` + 删除按钮 `button[aria-label="删除附件 <文件名>"]`。
- 已有草稿时主按钮文案为「继续编辑」，且页面存在两个同名按钮，语义点击会歧义拒绝——须回退点第一个可见 ref。
- 待审核状态提供「撤回并补充成果」：确认弹窗「撤回成果审核？」→「确认撤回并保留草稿」；撤回后任务回到 IN_PROGRESS、内容与附件保留到新草稿，修改后重新提交生成「成果第 N+1 版」，旧版本保留。**撤回/重交同样受截止闸门约束，且重新提交前需用户明确同意。**

## 5. 安全闸门

1. **截止闸门（用户规则）**：任务截止日 **23:50:59（北京时间，`submit_cutoff_time`）** 之后不再对平台做任何写入（包括撤回重交），该任务进 `skipped[reason=past_deadline]`；`endsAt` 缺失的任务不拦截。
2. **默认 `dry_run=True`**：只产出执行计划（每条任务的动作序列），不碰页面。
3. **默认 `mode="draft"`（保存草稿）**。`mode="submit"`（提交审核）会锁定版本进入审核流，**只有在用户明确说"提交审核"之后才允许**。
4. **附件替换规则**：线上草稿挂的 zip 与最新已发布版本不同时，**先删除旧版本 zip 附件，再上传最新 zip**；只删形如 `skill-*-vX.Y.Z.zip` 的旧包，其他类型附件（补充说明等）不动；同名 zip 已存在则不重复上传。
5. 每个字段写完必须回读验证（`get value`；React 受控组件重渲染导致 `stale_ref` 时重新定位后再读一次），不一致 → 停止该任务并报错，不带病点提交。
6. 进入详情页先关闭遗留的成果弹窗（它会遮挡底层按钮导致语义定位 0 命中），再判断按钮文案。
7. 一次会话一个任务：填写、验证、关弹窗之后才进下一条；任何一步失败不重试超过 1 次，失败即报告。
8. 严禁操作与目标标签页无关的页面；严禁 `eval` 改页面（读 fetch 除外）。
9. 不得把平台 token、手机号、成员编号写入成果说明或提交信息。

## 6. 输入

```python
input_data = {
    "tasks": None,   # 传入 [{id, task_number, title, status}] 则跳过在线抓取
    "skills": None,  # 传入 {slug: {feature, github_url, zip_path, version}} 则跳过本地资源扫描（测试/离线场景）
}
```

```python
config = {
    "session": "panda-upload",        # opencli browser 会话名
    "base_app_url": "https://lsy.quant789.com/app",
    "statuses": ["IN_PROGRESS", "PENDING"],
    "mode": "draft",                  # draft | submit
    "dry_run": True,
    "submit_cutoff_time": "23:50:59", # 截止日该时刻（北京时间）后不再写入
    "aliases": {"task_numbers": {...}, "keywords": {...}},
    "max_feature_chars": 1200,
}
```

## 7. 调用方式

```python
from scripts.build import run, validate_input

validate_input(input_data)
report = run(input_data, config=config)   # dry_run 出计划；确认后 dry_run=False 真执行
```

```bash
# 计划（离线可跑，演示用内置样例）
python3 skills/panda-upload-task/scripts/build.py
# 真实执行（保存草稿）
python3 skills/panda-upload-task/scripts/build.py --execute
# 真实执行并提交审核（必须用户已明确同意）
python3 skills/panda-upload-task/scripts/build.py --execute --mode submit
```

## 8. 输出（报告固定字段）

```python
{
  "mode": "draft", "dry_run": true,
  "targets": [{"task_number","title","id","status_before","skill","version",
               "github_url","zip","zip_sha256","action","status_after","verified","notes"}],
  "skipped": [{"task_number","title","status"}],       # 不在筛选状态
  "unmatched": [{"task_number","title","reason"}],     # 匹配不到 skill
  "blocked": [{"task_number","skill","reason"}],       # 资源闸门不过（如需先 panda-publisher）
  "errors": [...],
}
```

## 9. 验收要求
- `python3 scripts/build.py` 离线可独立跑通（dry_run 演示）。
- `tests/` 覆盖：筛选、三级匹配（含歧义→unmatched）、URL 规范化、README 提取、计划构建、validate_input 异常、dry_run 全链路（fake runner）。
- 真实执行前必须先出一份 dry_run 计划给用户过目。

## 10. 已知局限
- 平台若改版（路由/按钮文案/表单结构变化），以 `browser state` 现场为准重新核对 references/api_guide.md；本 skill 不做 selector 兜底猜测。
- Chrome 处于其他 Space/分屏时 osascript 置前可能不生效，需要人工把窗口拖回主屏。
- 附件字段实测为单文件（multiple:false），多附件需逐次打开弹窗追加。

## 11. 禁止事项
- 禁止未经 panda-publisher 发布（远端无仓库/未 push）就编造 github 地址或 zip 路径上传。
- 禁止把未过 panda-builder 验收的目录当成果提交。
- 禁止默认动作之外的一切平台写操作（撤单、改状态、删除版本等）。
- 禁止用 `提交审核` 代替用户决策；平台版本锁定后只能走补充窗口。

## 可被 Alpha 调用
- 否（平台运维类工具，与信号/因子无关）。
