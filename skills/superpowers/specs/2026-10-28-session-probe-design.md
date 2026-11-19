# 站点会话探活与派发对齐 · 设计文档

- 日期：2026-10-28
- 分支：`feat/session-probe`（主仓，base `develop`）、`feat/auth-probe`（opencli，base `telescope`）
- 范围：`executor-go/`（现役 Go 执行器）；`opencli/` 范围见 §9 未决项
- 基准：**以 Java 调度器现有代码为唯一契约源**，本设计不改 Java

## 1. 问题

站点会话链路在当前代码上有 4 处断链，且失败方式全是静默：

1. 执行器扫码成功后 `POST /session/login` —— Java 该端点已改名 `/session/exchange`（`SessionController.java:39`）→ **404，cookie 存不进库**。
2. 执行器发 `executionStatus:"LOGIN"` —— 不在 `Task.ExecutionStatus{NULL,RUNNING,SUCCESS,FAILED,EXPIRED,THROTTLE}`（`Task.java:90-97`）→ Jackson 反序列化抛错、`POST /task/result` 返 400、**回调整条丢失**。
3. 人肉登录不上报：唯一上行通道是执行器自己发起的 loginFlow（`site_actor.go:445`），窗口 `300+60=360s`（`:65`）。超过窗口才登进去、或根本不经执行器自己在 VNC 登录 → **profile 有货、调度器无账** → 派发 `session=null` → 任务 PAUSE + 反复弹登录页，让人重扫一次。
4. 风控（`SECURITY_BLOCK`）只在执行器本地指数退避，从不回报 → Java `TaskController.java:69-71` 的 THROTTLE 分支和派发层 2（`ScheduleService.java:199-215`）**永远空转**。

## 2. 目标 / 非目标

**目标**：对齐上述契约；建立"调度器账本 ↔ 执行器 profile"的周期对账；失效/风控可上报。
**非目标**：不改 Java；不接钉钉（`cmd/executor/main.go:122` 保持注释状态）；不做 `auth refresh`；不引入持久化状态。

## 3. 契约基准（Java 现状，逐条取证）

| 项 | 现状 | 位置 |
|---|---|---|
| 派发报文 | `TaskRequest` 含 `type/taskId/siteId/monitorId/website/command/params/**requireLogin**/url/timeoutSeconds/callbackUrl/llmPrompts/dingTalkConfig/**session**`；`session` 是 `WebsiteSession` 实体 → wire 为嵌套对象，主键叫 `id` 不叫 `sessionId` | `model/TaskRequest.java:22-49` |
| 选账号 | 两级：`NORMAL` 且过 `countdown` → `THROTTLE` 且过 `10×MIN`；**已无"硬塞 EXPIRED"的第三级**；都没有 → `session=null` | `ScheduleService.java:178-216` |
| 无账号挂起 | `session==null` 且 `requiresLogin` 且任务已 RUNNING → `PAUSE + EXPIRED` | `ScheduleService.java:238-244` |
| 结果回调 | `POST /task/result`，`EXPIRED` → `task=PAUSE+EXPIRED` 且会话标 EXPIRED；`THROTTLE` → 会话标 THROTTLE；其它 → 会话时间前移 + 置 NORMAL。会话分支嵌在 `if (sessionId != null)` 内 | `TaskController.java:60-81` |
| 登录入库 | `POST /session/exchange`，body `{domain,userId,cookies}`，按 `(websiteId,loginUserId)` upsert 且 `setStatus(NORMAL)`，并批量把本站 `PAUSE+EXPIRED` 的 CRAWL 任务恢复 PENDING | `SessionController.java:39-79` |
| 存活探测 | `GET /session/{domain}/ping`：只判"是否存在 NORMAL 账号"→ 200/204，无副作用 | `SessionController.java:86-103` |
| 账本快照 | `GET /session/status`：`List<WebsiteSessionResponse>`，覆盖全部 `requires_login` 站点，每账号一条 `{websiteDomain,loginUserId,status}`；**无 cookies**（`@JsonInclude(NON_NULL)`）；无账号站点补一条 `status=EXPIRED,loginUserId=""` 占位行；不输出 `websiteId/sessionId/lastUsedTime`；**注释承诺的排序在实现里没有** | `SessionController.java:106-131` |
| 重投 | `GET /task/running/{id}`：置 PENDING，**不回拨 endTime**（仍受 5 分钟门控） | `TaskController.java:98-109` |

## 4. opencli 探活能力的事实基线

- `opencli auth status`（全局子命令，非 `opencli <site> <cmd>`）：范围 = registry 中 `name=whoami && browser && access=read` 的站点；`--site` 过滤；默认 **quick** 模式。
- quick：把 whoami 的 func 换成适配器 `authStatus.quickCheck`，`navigateBefore:false` + `siteSession:ephemeral` + `keepTab:false`，并发 8、每站超时 8s。
  → **不导航、不改 cookie**；`siteSession` 只管 tab 身份，cookie 在 profile 里，ephemeral 读到的仍是真实登录态。
- `--full`：跑真 whoami（weibo 的 verify 会 `goto` + `fetch`）→ **会改 profile cookie、有风控面**。
- 返回行 `{site,status,logged_in,identity,checked,error}`；`status ∈ logged_in|not_logged_in|unknown|error`；`AuthRequiredError` 归一为 `not_logged_in`。
- `opencli auth refresh`：`page.goto(站点首页)` + persistent → **会改 cookie**，且内建 24h 节流。本设计不使用。
- 现役 requires_login 五站 `weibo/xiaohongshu/douyin/bilibili/zhihu` 均有 `clis/<site>/auth.js`（quickCheck + verify）；`tieba/weixin/ths/cls` **没有**。

## 5. 核心设计：周期对账

```
每轮（≈50min + 随机抖动，进程内计时，不落盘）
A. GET /session/status                       → 按 domain 归组：{hasNormal, userIds[]}
B. opencli auth status --site <A 的 domains> -f json → 每站 {status, identity}
C. 对账处置：
   本地 logged_in 且（!A.hasNormal 或 identity ∉ A.userIds）
        → whoami 取 userId → cookie-export → POST /session/exchange
          （Java 插入/更新该行并唤醒本站 PAUSE 任务）→ 人肉登录、迟到扫码、换账号三种场景统一由此闭合
   本地 not_logged_in 且 A.hasNormal → 不弹页，等下一次派发带 cookie 覆盖 profile
   本地 not_logged_in 且 !A.hasNormal → 申请登录窗口 → loginFlow 弹页
   本地 unknown / error               → 只记日志，不改状态、不弹页、不上报
   A 里没有该站（免登录/未登记）        → 不参与探活
D. 反应式通道永久保留（不依赖适配器）：
   抓取撞 ErrAuthRequired  → 回报 EXPIRED + sessionId（必须带，否则 Java 不进 PAUSE 分支）
   抓取撞 SECURITY_BLOCK   → 回报 THROTTLE + sessionId
   正常完成                → 回报 SUCCESS + sessionId
   与账号无关的失败        → 回报 FAILED，不带 sessionId
```

`exchange` 上报的抑制条件（**只有本地 logged_in 才允许上报**）是关键防抖：`/status` 给无账号站点补的是 `loginUserId=""` 占位行，与本地 identity 比对必然不等；若不设这道闸，每轮会对每个空站白跑一次 `whoami`（会导航、改 cookie、有风控面）。

## 6. 已知局限（写死在 spec，不当缺陷处理）

1. **判不出"NORMAL 但全在冷却中"**：`/status` 与 `ping` 都不含 `lastUsedTime/available`，而 `countdown = max(8h / countByWebsiteId, 3min)` 依赖 monitor 数，执行器算不出。
   → 处置口径：`hasNormal` 一律按"有货、等"处理，代价是**可能白等一个派发周期**。
2. **探活侧无法精确标某一行失效**：`/status` 不输出 `sessionId`，而 `TaskController.java:61` 按 `sessionId` 定位。
   → 探活判出的失效只能靠"下一次派发把它撞出来后，由任务态回报标掉"。
3. **占位行不可区分**："从没建过账号"与"有一个真 EXPIRED 账号"在响应里同形（`status=EXPIRED, loginUserId=""`）。对 `hasNormal` 判定无害，对计数展示会虚高 1。
4. **无排序契约**：`/status` 声明按 ordinal 升序但实现未排序 → Go 一律自行按 status 归组，不依赖顺序。
5. **探活覆盖不全**：无 `auth.js` 的站点在 `auth status` 里**根本没有行**（不是 unknown）→ 只能靠 §5-D 反应式通道。

## 7. 组件划分

| 单元 | 职责 | 落点 |
|---|---|---|
| `scheduler.Client.SessionStatus` | 一次拉全账本，返回按 domain 归组的结构；解析宽容（缺字段不炸） | `internal/clients/scheduler/{client,types}.go` |
| `scheduler.Client.LoginSession` | 上报登录态到 `/session/exchange`（body `domain/userId/cookies`） | 同上（路径改名） |
| `fetcher.ExecuteGlobal` | 承载**不带 site 前缀**的全局子命令 argv（`opencli auth status …`），不复用 `[site, cmd, …]` 组装 | `internal/fetcher/fetcher.go` |
| `state.Task.RequireLogin` | 派发字段，任务内判"该不该走 cookie/该不该弹页" | `internal/state/task.go` |
| `probe.Scheduler` | 周期对账：拉快照 → 探活 → 按 §5-C 分派动作；进程内 map，重启即忘 | 新文件 `internal/probe/probe.go` |
| `state.TaskResult` 状态词表 | 出向四值常量 + 边界闸白名单对齐 | `internal/state/events.go` |

探活器与抓取共用的约束：它起的浏览器页面与抓取、扫码同进程同 profile，**必须经 `Coordinator` 的登录窗口 FIFO 协调**，且不得在 `LOGIN_IN_PROGRESS` 期间发起（避免打断人工扫码）。

## 8. 测试与验收

- 单测/集成：`state` 报文解析（嵌套 `session`、`requireLogin` 两形态）、`clients/scheduler` 契约（`/session/exchange`、`/session/status`、200/204 语义）、`probe` 决策矩阵（四态 × hasNormal 全组合，含占位行与 unknown/error 不误判）、`actor` 回报状态（EXPIRED/THROTTLE/SUCCESS 带 sessionId、FAILED 不带）。
- 夹具必须换成**当前 Java 真实报文**：`/status` 的 `List<WebsiteSessionResponse>`（含占位行、无 websiteId）、派发体的 `session:{id,websiteId,loginUserId,cookies,status,…}`。
- 验收线：`go build ./... && go vet ./... && go test ./... -race -count=1` 全绿。
- 容器实开取证（合并回 develop 后，主工作区 + `docker cp` 热更，走 `telescope-executor-ops`）：
  1. `GET /session/status` 在 dev 调度器上的真实响应逐键核对（验证我们对 §3 的读解）；
  2. 造一次"库里有 NORMAL 账号"的站，人为清掉本地 profile 登录态 → 看对账判 `not_logged_in + hasNormal` → **不弹页**；
  3. 人为清空该站账号行 → 看是否走弹页 + `exchange` 上报 → 库中出现 NORMAL 行、PAUSE 任务被唤醒；
  4. 抓一次真实 `SECURITY_BLOCK` → 看 Java 端 `ts_website_session.status` 是否变 THROTTLE。
- 声称完成前执行 `verification-before-completion`。

## 9. 未决项

1. **opencli 侧改什么**（本设计的 §4 显示 quick 探活对现役五站已可用）：
   (a) 给缺 `auth.js` 的 `requires_login=1` 站点补适配器；(b) 增强现有 quickCheck 判据（cookie 存在性 → 服务端有效性）；(c) 不改。→ 需人工定范围。
2. **`ping` 撤不撤**：`/status` 已覆盖其判定（`count(status==NORMAL)>0`），撤掉可少一个端点、少 N 次调用。
3. **A7**：`ts_website.task_interval_seconds` 存量是否有 0（DDL 默认仍是 0，初始化 INSERT 不含该列）→ 有 0 时成功冷却被压成 0 秒，属最高优先级现网问题，与本设计无关但会污染验证结果。

## 10. 决策记录（本轮人工确认）

A1 任务失败必须回调并携带 session 状态；A2 Java 只置 PENDING 不回拨 endTime；A3 `ping`/`exchange` 未知 domain 维持 204 静默；A4 探活采用 `auth status`（quick）；A5 不用 `auth refresh`；A6 `last_used_time` 的线上 ALTER 已执行；A7 认为 `task_interval_seconds` 不会是 0（与 DDL 默认值证据冲突，见 §9.3）。
