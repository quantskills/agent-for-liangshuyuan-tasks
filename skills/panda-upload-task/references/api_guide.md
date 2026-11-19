# 量枢院成员运营平台 — 任务成果回填接口与页面指南

实测时间：2026-11-18，站点 `https://lsy.quant789.com`（Chrome 已登录会话，cookie 同源携带）。
站点改版时以 `opencli browser --session S state` 现场为准，本文件随之更新。

## 1. 路由

| 页面 | URL |
|---|---|
| 我的任务列表 | `/app/tasks`（SPA，直接 `open` 可用） |
| 任务详情 | `/app/tasks/{task.id}` |

## 2. 数据 API（同源 GET，只读 fetch）

### `GET /api/v1/tasks?page=1&sortBy=updatedAt&order=desc`

```jsonc
{ "ok": true,
  "data": { "items": [
    { "id": "cmveo9wmr0017ski583cybsk4",
      "taskNumber": "TS202610193FE946",
      "title": "JEV盯盘条件与历史回放的语义能否一致",
      "status": "PENDING",
      "sourceType": "OFFICIAL",          // OFFICIAL / TOPIC / LEGACY
      "startsAt": "...", "endsAt": "...", "updatedAt": "..." } ] } }
```

### `GET /api/v1/tasks/{id}`

返回单任务对象（同上字段 + `description` 全文、`cohort`、`officialTask` 等）。
成果表单相关写入接口未在本指南验证；本 skill 一律走 UI 点击，不直接 POST。

## 3. 状态枚举（已线上核实）

| API status | UI 文案 | 是否回填 |
|---|---|---|
| `PENDING` | 待创作 | ✅（需先点「开始创作」） |
| `IN_PROGRESS` | 创作中 | ✅ |
| `PENDING_REVIEW` | 待审核 | ❌ 跳过 |
| `COMPLETED` | 已完成 | ❌ 跳过 |
| `REWORK` | 需修改 | ❌（本版本未启用，出现时先人工判断） |

列表页顶部的筛选按钮组：`全部 / 待开始 / 待创作 / 创作中 / 待审核 / 需修改`。

## 4. 任务详情页控件（state 实测）

按 `open /app/tasks/{id}` → `wait time 2` 后：

- 状态为待创作：底部按钮 `[返回任务列表]` `[开始创作]`
- 点「开始创作」后：状态文案变「创作中」，底部按钮变 `[返回任务列表]` `[填写成果]`
- 折叠区：任务说明 / **成果与版本**（未填时显示「尚未提交成果；可先保存草稿，正式提交后当前版本锁定」）/ 审核记录 / 周期与额度 / 操作时间线

## 5. 成果弹窗（点击「填写成果」后）

容器：`section[role=dialog]`。字段（ref 必须每次从 `find`/`state` 现取，禁止跨页复用）：

| 表单 | CSS | 控件 | 填什么 |
|---|---|---|---|
| 成果说明 | `section[role=dialog] textarea` | textarea | skill 功能描述（README 提取，≤ 默认 1200 字） |
| 成果链接 | `section[role=dialog] input[type=url]` | url input，placeholder `https://github.com/...` | `https://github.com/quantskills/skill-{slug}` |
| 本地附件 | `section[role=dialog] input[type=file]` | compound `{control:file, multiple:false}`；平台约束：**单记录≤20个文件、单文件≤50MB**，支持文档/图片/Markdown/CSV/ZIP | `public/dist/skill-{slug}-v{version}.zip` |

按钮：`保存草稿`、`提交审核`（正式提交后当前版本**锁定**）。关闭弹窗：右上角 `aria-label=关闭` 或 `keys Escape`。

### 草稿附件区（编辑态，实测 2026-11-18）

弹窗内「草稿已有附件」列表：

```
.attachment-list > .attachment-item.editable
  ├─ a.attachment-link[download="<文件名>"][href=/api/v1/attachments/<id>]
  └─ button.attachment-delete-button[aria-label="删除附件 <文件名>"]
```

版本替换规则：新 zip ≠ 草稿旧 zip 时，先点旧 zip 的删除按钮（语义定位 `--role button --name "删除附件 <文件名>"`），再向 `input[type=file]` upload 新包；非 zip 附件不删；同名不重传。

### 按钮文案随状态变化

- `PENDING`：`开始创作` → 点击后 `IN_PROGRESS`
- `IN_PROGRESS` 无草稿：`填写成果`
- 已有草稿：`继续编辑`（页面出现**两个**同名按钮：草稿卡片一个、底部一个；`click --role button --name` 会因歧义拒绝，需 `find` 后点第一个可见 ref）
- `PENDING_REVIEW`：`撤回并补充成果` → 确认弹窗「撤回成果审核？」按钮 `确认撤回并保留草稿`；撤回后任务回到 `IN_PROGRESS`，内容与附件并入新草稿；修改后重新提交生成「成果第 N+1 版」，旧版本保留可查

### 提交截止（用户规则）

平台到期日为 23:59:59（北京时间），但**实际写入截止按 23:50:59**（`submit_cutoff_time`）执行：超过后不再保存草稿 / 撤回重交 / 任何平台写入；历史任务（`截止 —`，`endsAt` 缺失）不拦截。

## 6. opencli 调用范式

```bash
S=panda-upload
# 读任务（只读 fetch，窗口不可见也能用；eval 结果若是字符串，stdout 就是原始 JSON 文本）
opencli browser --session $S open "https://lsy.quant789.com/app/tasks"
opencli browser --session $S eval "(() => fetch('/api/v1/tasks?page=1&sortBy=updatedAt&order=desc', {credentials:'include'}).then(r => r.text()))()"

# 写操作（必须窗口可见）
osascript -e 'tell application "Google Chrome"
activate
repeat with w in windows
  try
    if (URL of active tab of w) contains "lsy.quant789.com" then
      set index of w to 1
      set minimized of w to false
    end if
  end try
end repeat
end tell'
opencli browser --session $S click --role button --name 填写成果
opencli browser --session $S wait selector "section[role=dialog]" --timeout 8000
opencli browser --session $S find --css "section[role=dialog] textarea"   # 取 ref
opencli browser --session $S fill <ref> "<功能说明>"
opencli browser --session $S get value <ref>                              # 回读验证
opencli browser --session $S upload <file_ref> /abs/path/to/xxx.zip
opencli browser --session $S click --role button --name 保存草稿
```

## 7. 陷阱清单（已踩实）

1. **原生输入要求窗口可见**：窗口最小化/被遮挡时 `click` 报
   `COMMAND_EXEC: Native input requires a visible browser page`。`osascript` 置前后**同一个 shell 里立即点击**，跨命令之间焦点可能再次丢失；`ensure_visible` 应在每个写操作前执行。
2. `opencli browser chrome call windows.update` 对含活跃 OpenCLI 会话的窗口会报 `managed_resource_conflict`，不要用这条路。
3. 详情页按钮文案随状态变化（开始创作 → 填写成果），点击前用 `state` 或语义定位确认，不猜 ref。
4. refs 跨页面/弹窗切换即失效：每次 `wait` 到新状态后重新 `find`。
5. `fill` 后必须 `get value` 回读；textarea 内容可能含换行，回读比较用前缀即可（代码用前 40 字）。
6. opencli v2.0.2 会话语法为 `--session <name>`（不是本仓库 opencli-browser 文档里的位置参数写法）。
7. stdout 与 stderr 分离：更新提示走 stderr，解析时只读 stdout，从第一个 `{` 起取 JSON。
8. `find --css` 在 0 命中时**抛 `selector_not_found` 错误**而不是返回 `matches_n: 0`——存在性检查必须 try/except 包住。
9. 上一次会话遗留的成果弹窗会遮挡详情页按钮（语义定位 0 命中）；进入页面先探测并 `keys Escape` 关掉。
10. `fill` textarea 后 React 受控组件会重渲染节点，旧 ref 的 `get value` 报 `stale_ref`——重新 `find` 再回读，值其实已写入成功。
11. eval 的字符串结果会被 opencli `{ok,data}` envelope 再包一层（data=原始 body 文本）；解包后还要检查平台自身的 `ok` 字段。
