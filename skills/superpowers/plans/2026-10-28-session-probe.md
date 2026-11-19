# 站点会话探活与派发对齐 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Go 执行器与 Java 调度器现有的会话契约对齐（`/session/exchange`、`EXPIRED`/`THROTTLE` 回报、`requireLogin`），并新增以 `opencli auth status` + `GET /session/status` 为基础的周期对账，覆盖人肉登录与换账号不上报的缺口。

**Architecture:** 三层 —— ①`scheduler.Client` 收口 HTTP 契约（exchange / status / task-result）；②`fetcher` 新增一条**不带 site 前缀**的全局子命令调用面，承载 `opencli auth status`；③新组件 `probe.Scheduler` 做周期对账（拉账本快照 + 本地探活 → 四态分派：上报 / 等待 / 弹页 / 不动），经 `Coordinator` 的登录窗口 FIFO 与抓取互斥。反应式通道（撞墙回报）永久保留，覆盖无 `auth.js` 的站点。

**Tech Stack:** Go 1.27.2，纯标准库（无 go.sum，`CGO_ENABLED=0` 静态链接）；测试用 `httptest` + 假 opencli shell 桩（`internal/pipelines/sitestest`）。

**Spec:** `skills/superpowers/specs/2026-10-28-session-probe-design.md`（executors read both）

## Global Constraints

- 宿主 `develop` worktree：`/Users/duanyong/workspace/industry_report/.claude/worktrees/session-probe`，分支 `feat/session-probe`（base `develop` @ `55f84c8`）。
- **不改 Java**（`scheduler/` 一律只读；契约以 spec §3 记录的行号为准）。
- **不接钉钉**：`cmd/executor/main.go:122` 的 `ding := dingtalk.New(nil)` 保持注释状态。
- **不用 `opencli auth refresh`**（会 goto 站点、改 profile cookie、内建 24h 节流）。
- **不引入持久化**：探活状态只在进程内，重启即忘。
- 枚举词表两个方向不得混用：入向 `session.status ∈ {NORMAL,THROTTLE,EXPIRED}`；出向 `executionStatus ∈ {SUCCESS,FAILED,EXPIRED,THROTTLE}`（Java `Task.java:90-97` 全集含 `NULL,RUNNING`，执行器禁发）。`NORMAL` 不是合法出向值。
- 敏感数据：`cookies` 不得进日志；不得整体序列化 `Task`。
- 每个 Task 收尾必须：`go build ./... && go vet ./... && go test ./<受影响包>/... -race -count=1` 全绿 + 一次 commit。
- commit 消息一律写文件再 `git commit -F`（本仓已三次踩 `-m` 双引号被当 pathspec 的坑）；结尾 `Co-Authored-By: Claude Code <noreply@anthropic.com>`。
- 站点数据判据只认 opencli 产出 + 库行，禁止 Python 解析页面。

---

### Task 1: LoginSession 端点改名 `/session/exchange`

**Files:**
- Modify: `executor-go/internal/clients/scheduler/client.go:254-276`
- Modify: `executor-go/internal/clients/scheduler/types.go:70-77`
- Modify: `executor-go/internal/actor/site_actor.go:542`
- Test: `executor-go/internal/clients/scheduler/session_client_test.go`

**Interfaces:**
- Consumes: 无
- Produces: `LoginSession(ctx context.Context, req LoginSessionRequest) error`（签名不变），POST 路径 `/session/exchange`

- [ ] **Step 1: 写失败测试**

在 `session_client_test.go` 追加（沿用该文件既有的 `gotPath` 断言风格）：

```go
// TestLoginSessionPath 锁定 Java 现役端点：/session/exchange（/session/login 已改名，
// 旧路径会拿 404 —— SessionController.java:39）。
func TestLoginSessionPath(t *testing.T) {
	var gotPath, gotMethod string
	var gotBody map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath, gotMethod = r.URL.Path, r.Method
		_ = json.NewDecoder(r.Body).Decode(&gotBody)
		w.WriteHeader(http.StatusOK)
	}))
	defer srv.Close()

	c := NewClient(srv.URL, srv.Client())
	if err := c.LoginSession(context.Background(), LoginSessionRequest{
		Domain: "weibo", UserID: "u9", Cookies: `[{"name":"SUB","value":"v"}]`,
	}); err != nil {
		t.Fatalf("LoginSession: %v", err)
	}
	if gotMethod != http.MethodPost || gotPath != "/session/exchange" {
		t.Errorf("method/path = %s %s, want POST /session/exchange", gotMethod, gotPath)
	}
	// body 三键逐字：Java WebsiteSessionRequest 只有 domain/userId/cookies
	for _, k := range []string{"domain", "userId", "cookies"} {
		if _, ok := gotBody[k]; !ok {
			t.Errorf("body 缺键 %q, got %v", k, gotBody)
		}
	}
	if len(gotBody) != 3 {
		t.Errorf("body 键数 = %d, want 3（不得带 websiteId/result/sessionId）", len(gotBody))
	}
}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `go test ./internal/clients/scheduler/ -run TestLoginSessionPath -v -count=1`
Expected: FAIL — `path = /session/login, want POST /session/exchange`

- [ ] **Step 3: 改实现与注释**

`client.go:263`：`path := "/session/login"` → `path := "/session/exchange"`。
同函数注释 `:254-261` 与 `types.go:70-77` 里所有「POST /session/login」措辞改为 `/session/exchange`；`:261` 那句「404 说明端点不存在」的举例改为「旧 `/executor/session/report`、`/session/login` 均已退役」；`site_actor.go:542` 注释同步。
`client.go:259` 引用的 Java 行号 `SessionController:139-142` 已过时 → 改为 `SessionController.java:43-46`（`findByDomain` 落空即 204）。

- [ ] **Step 4: 跑测试确认通过**

Run: `go test ./internal/clients/scheduler/ -race -count=1`
Expected: ok（含既有 `TestLoginSession204…` 等用例不回归）

- [ ] **Step 5: Commit**

```bash
git add executor-go/internal/clients/scheduler/client.go executor-go/internal/clients/scheduler/types.go executor-go/internal/clients/scheduler/session_client_test.go executor-go/internal/actor/site_actor.go
git commit -F /tmp/cm_t1.txt
```
消息首行：`fix(scheduler-client): 登录上报端点改 POST /session/exchange`

---

### Task 2: `Task.RequireLogin` 接入派发报文

**Files:**
- Modify: `executor-go/internal/state/task.go:10-26`
- Test: `executor-go/internal/state/task_test.go`

**Interfaces:**
- Consumes: 无
- Produces: `Task.RequireLogin bool`（`json:"requireLogin"`），供 Task 5/6 判定「需登录站点」

- [ ] **Step 1: 写失败测试**

```go
// TestParseTaskRequireLogin 契约源：Java TaskRequest.java:36 private boolean requireLogin
// ← ScheduleService.java:289 .requireLogin(website.getRequiresLogin())。
// 键名按 Lombok boolean（isRequireLogin）+ Jackson 规则推为 requireLogin，
// 本测试同时容住 false 缺失的形态。
func TestParseTaskRequireLogin(t *testing.T) {
	cases := []struct {
		name, body string
		want       bool
	}{
		{"true", `{"taskId":"1","website":"weibo","command":"search","requireLogin":true}`, true},
		{"false", `{"taskId":"1","website":"weibo","command":"search","requireLogin":false}`, false},
		{"缺失（旧报文形态容忍）", `{"taskId":"1","website":"weibo","command":"search"}`, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			task, err := ParseTask([]byte(tc.body))
			if err != nil {
				t.Fatalf("ParseTask: %v", err)
			}
			if task.RequireLogin != tc.want {
				t.Errorf("RequireLogin = %v, want %v", task.RequireLogin, tc.want)
			}
		})
	}
}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `go test ./internal/state/ -run TestParseTaskRequireLogin -v -count=1`
Expected: 编译失败 `task.RequireLogin undefined`（缺字段即红，不必先写断言变体）

- [ ] **Step 3: 加字段**

`state/task.go` 的 `Task` 结构体里，`URL` 之后插入：

```go
	// RequireLogin 派发标记该站点是否需要登录态（Java TaskRequest.requireLogin
	// ← website.getRequiresLogin()，ScheduleService.java:289）。
	// 用途限定在任务内判定：true 且 session 为空 → 本次派发无 cookie，走扫码；
	// 探活周期任务（probe）不受此字段驱动 —— 它的宇宙来自 GET /session/status。
	RequireLogin bool `json:"requireLogin"`
```

注意：`Task.UnmarshalJSON` 走「先解 `map[string]json.RawMessage`、摘掉多态的 `taskId/monitorId` 再解 alias」，未识别键被 `encoding/json` 忽略 → 加字段即可，`UnmarshalJSON` 无需改动。

- [ ] **Step 4: 跑测试确认通过**

Run: `go test ./internal/state/ -race -count=1`
Expected: ok

- [ ] **Step 5: Commit**

消息首行：`feat(state): Task 接入派发字段 requireLogin`

---

### Task 3: 风控回报接通 `THROTTLE`（当前 Java 分支空转）

**Files:**
- Modify: `executor-go/internal/actor/site_actor.go:300-312`（`case d.LimitedRetry:` 分支）
- Modify: `executor-go/internal/state/events.go:26-33`
- Test: `executor-go/internal/actor/session_report_test.go`

**Interfaces:**
- Consumes: `TaskResult{Status, SessionID}`（已有）
- Produces: `Status:"THROTTLE"` + `SessionID` 的回报；`state.StatusThrottle` 常量

- [ ] **Step 1: 写失败测试**

```go
// TestRateLimitedReportsThrottle 风控必须回报 THROTTLE：
// Java TaskController.java:69-71 据此把会话置 THROTTLE，派发层 2（ScheduleService:199-215）
// 才有账号可降级；此前风控只本地退避不回报，那两个分支一直空转。
// 同时锁定「风控 ≠ 失效」：不得发 EXPIRED（那会把账号永久踢出第一级）。
func TestRateLimitedReportsThrottle(t *testing.T) {
	// 装配沿用本文件既起的 fake scheduler（记录 TaskResultPayload）+ 真 SiteActor。
	fs := newFakeSched()
	a, cleanup := startActorForTest(t, "sitestest", fs)
	defer cleanup()

	a.Enqueue(taskWithCookies("t1", 42))          // 带派发 cookies 的任务
	a.PipelineDone(state.PipelineDone{            // 模拟 SECURITY_BLOCK 收尾
		Task:   taskWithCookies("t1", 42),
		Err:    state.ErrRateLimited,
		LimitedRetry: true,
	})

	got := waitForResults(t, fs, 1)               // 本文件既有 helper
	if got[0].ExecutionStatus != "THROTTLE" {
		t.Fatalf("executionStatus = %q, want THROTTLE", got[0].ExecutionStatus)
	}
	if got[0].SessionID != 42 {
		t.Errorf("sessionId = %d, want 42（不带则 Java 找不到那一行）", got[0].SessionID)
	}
}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `go test ./internal/actor/ -run TestRateLimitedReportsThrottle -v -count=1`
Expected: FAIL — 收到 0 条回调（现分支不回报，注释写着「Python 语义：风控不发 /task/result」）

- [ ] **Step 3: 改 actor 与词表**

`site_actor.go` 的 `case d.LimitedRetry:` 内，保留「backoff 已 +1、任务回队头优先重试」的原语义，**追加**一条回报（异步、失败仅记日志，复用既有 `a.reportAsync`）：

```go
	case d.LimitedRetry: // 风控：backoff 已在 fetcher +1，任务回队头优先重试
		// 回报 THROTTLE（不发 EXPIRED —— 风控期 cookie 仍有效，标失效会误踢出层 1）。
		// 仍保留本地退避与队头重试：THROTTLE 只是给调度器的账号标记，不是终态。
		if d.Task.SessionID != 0 {
			a.reportAsync(state.TaskResult{
				TaskID:    d.Task.TaskID,
				Status:    state.StatusThrottle,
				Summary:   a.site + " 命中风控(SECURITY_BLOCK)，账号标 THROTTLE",
				SessionID: d.Task.SessionID,
			})
		}
		// …以下原有回队头/状态转换逻辑逐字不动…
```

`state/events.go` 顶部加词表常量（把散落的字面量收口，spec §3 的出向词表为唯一基准）：

```go
// 出向执行结果词表。唯一基准是 Java Task.ExecutionStatus（entity/Task.java:90-97）。
// ⚠ 不得跨表回填：入向 session.status 的 NORMAL 不是合法出向值（发出去即 400）。
// 判据来源仅限枚举声明处 —— schema.sql 的 result_status 注释、@Schema 描述、
// 本仓旧注释都出现过 LOGIN/TIMEOUT/VALID/INVALID 这类已退役的词，均不可信。
const (
	StatusSuccess = "SUCCESS" // 抓取完成，携 SessionID（若派发带了账号）
	StatusFailed  = "FAILED"  // 与账号无关的失败；不带 SessionID
	StatusExpired = "EXPIRED" // 派发 cookie 确认失效；必须带 SessionID（否则 Java 不进 PAUSE 分支）
	StatusThrottle = "THROTTLE" // 派发账号被站点风控；必须带 SessionID
)
// Java 侧 NULL / RUNNING 是初值与中间态，执行器永不下发。
```

`events.go:26-33` 里「THROTTLE 预留，风控回报通路另开一轮」的说明改为「THROTTLE 已在 actor 的 LimitedRetry 分支接通」。同函数 `Status` 字段类型仍是 `string`（不改类型，避免波及 8 处 fake；靠常量约束）。

- [ ] **Step 4: 跑测试确认通过**

Run: `go test ./internal/actor/ ./internal/state/ -race -count=1`
Expected: ok；且既有 `TestCookiesImportedAndCrawlSucceeds` 等不回归

- [ ] **Step 5: Commit**

消息首行：`feat(actor): 风控命中回报 THROTTLE 并收口执行结果词表常量`

---

### Task 4: `GET /session/status` 客户端与账本归组

**Files:**
- Create: `executor-go/internal/clients/scheduler/session_status.go`
- Test: `executor-go/internal/clients/scheduler/session_status_test.go`
- Modify: `executor-go/internal/clients/scheduler/client.go`（接口声明区）

**Interfaces:**
- Consumes: `httpClient.do(method, path, query, body, dest)`（既有私有）
- Produces:
  - `Client.SessionAccounts(ctx context.Context) (SessionStatusReport, error)`
  - `type SessionAccount struct { Domain, LoginUserID, Status string }`
  - `type SessionStatusReport struct { BySite map[string][]SessionAccount; DroppedRows int }`
  - `func HasNormal(accounts []SessionAccount) bool`（Task 6 用同一口径）

> **已核实的现场事实（不要臆造）**：`type httpClient struct { base string; hc *http.Client }` —— **client 侧没有任何日志字段/方法**，
> 因此丢弃行数只能作为返回值交给调用方记日志，不能在 client 里打日志。

- [ ] **Step 1: 写失败测试（夹具用 Java 现役响应形态）**

```go
// TestSessionAccounts 契约源 SessionController.java:106-131：
// 返回 List<WebsiteSessionResponse>，元素只保证 websiteDomain/loginUserId/status 三键
// （@JsonInclude(NON_NULL) → websiteId/sessionId/lastUsedTime/cookies 都不出现）；
// 无账号站点是一条 status=EXPIRED、loginUserId="" 的占位行。
func TestSessionAccounts(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/session/status" || r.Method != http.MethodGet {
			t.Errorf("请求走偏: %s %s", r.Method, r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`[
		  {"websiteDomain":"weibo","loginUserId":"u1","status":"NORMAL"},
		  {"websiteDomain":"weibo","loginUserId":"u2","status":"EXPIRED"},
		  {"websiteDomain":"douyin","loginUserId":"","status":"EXPIRED"},
		  {"websiteId":9,"status":"THROTTLE"}
		]`))
	}))
	defer srv.Close()

	report, err := NewClient(srv.URL, srv.Client()).SessionAccounts(context.Background())
	if err != nil {
		t.Fatalf("SessionAccounts: %v", err)
	}
	bySite := report.BySite
	if len(bySite) != 2 {
		t.Fatalf("站点数 = %d, want 2（weibo/douyin；无 domain 的行只能丢弃）\n%v", len(bySite), bySite)
	}
	if report.DroppedRows != 1 {
		t.Errorf("DroppedRows = %d, want 1（第 4 行只有 websiteId，无 websiteDomain）", report.DroppedRows)
	}
	if len(bySite["weibo"]) != 2 {
		t.Errorf("weibo 账号数 = %d, want 2", len(bySite["weibo"]))
	}
	if !HasNormal(bySite["weibo"]) {
		t.Error("weibo 应判为有 NORMAL 可用账号")
	}
	if HasNormal(bySite["douyin"]) {
		t.Error("douyin 只有占位行，不得判为有 NORMAL")
	}
	if bySite["douyin"][0].LoginUserID != "" {
		t.Error("占位行的空 loginUserId 必须原样保留（Task 6 靠它做上报抑制）")
	}
}

// TestSessionAccountsNon200 非 200 / 坏 JSON 一律 err，不得静默给空 map——
// 空 map 在 Task 6 里等价于「所有站都没账号」，会批量误弹登录页。
func TestSessionAccountsNon200(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer srv.Close()
	if _, err := NewClient(srv.URL, srv.Client()).SessionAccounts(context.Background()); err == nil {
		t.Fatal("500 应返回 err")
	}
}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `go test ./internal/clients/scheduler/ -run TestSessionAccounts -v -count=1`
Expected: 编译失败 `SessionAccounts undefined`

- [ ] **Step 3: 写实现**

`session_status.go`：

```go
package scheduler

import (
	"context"
	"fmt"
	"net/http"
)

// SessionAccount 账本快照里的一行账号（GET /session/status 的 WebsiteSessionResponse 投影）。
// 只取对账需要的三键：Domain 是分组键，Status 是 NORMAL/THROTTLE/EXPIRED，
// LoginUserID 是 upsert 靶子；无账号站点由 Java 补一条 LoginUserID=""、Status="EXPIRED"
// 的占位行（spec §6.3），空串原样保留、不当缺失处理。
type SessionAccount struct {
	Domain      string
	LoginUserID string
	Status      string
}

// sessionStatusWire 线上形态。websiteId 等键当前不输出，故不声明——
// Java 侧若补上这些字段，encoding/json 会自动忽略，解析不受影响。
type sessionStatusWire struct {
	WebsiteDomain string `json:"websiteDomain"`
	LoginUserID   string `json:"loginUserId"`
	Status        string `json:"status"`
}

// HasNormal 判定该站是否至少有 1 个 NORMAL 账号（等价于 Java ping 的
// existsByWebsiteIdAndStatus(id, NORMAL)，SessionController.java:98-102）。
// 注意：不含冷却信息 —— spec §6.1，NORMAL 全在冷却中时派发仍会给回 session=nil。
func HasNormal(accounts []SessionAccount) bool {
	for _, a := range accounts {
		if a.Status == StatusNormal {
			return true
		}
	}
	return false
}

// SessionStatusReport 快照归组结果 + 被丢弃的行数（client 侧无日志器，只能回传给调用方记）。
type SessionStatusReport struct {
	BySite      map[string][]SessionAccount
	DroppedRows int
}

// SessionAccounts 拉全量账本快照并按 domain 归组。一次调用覆盖全部 requires_login 站点。
// 非 200 / 解析失败一律 err（空结果 ≠ 无账号，误判会批量弹登录页）；
// 缺 websiteDomain 的行丢弃并计数，由调用方在日志里暴露——它是 Java 侧的孤儿数据。
func (c *httpClient) SessionAccounts(ctx context.Context) (SessionStatusReport, error) {
	path := "/session/status"
	var rows []sessionStatusWire
	status, digest, err := c.do(ctx, http.MethodGet, path, nil, nil, &rows)
	if err != nil {
		return SessionStatusReport{}, err
	}
	if status != http.StatusOK {
		return SessionStatusReport{}, fmt.Errorf("scheduler %s %s: status %d, 响应: %s", http.MethodGet, path, status, digest)
	}

	rep := SessionStatusReport{BySite: make(map[string][]SessionAccount, len(rows))}
	for _, r := range rows {
		if r.WebsiteDomain == "" {
			rep.DroppedRows++
			continue
		}
		rep.BySite[r.WebsiteDomain] = append(rep.BySite[r.WebsiteDomain], SessionAccount{
			Domain: r.WebsiteDomain, LoginUserID: r.LoginUserID, Status: r.Status,
		})
	}
	return rep, nil
}
```

接口声明区（`client.go` 的 `Client` interface，紧接 `LoginSession` 之后）加：

```go
	// SessionAccounts 拉站点会话快照（GET /session/status，List<WebsiteSessionResponse>），
	// 按 domain 归组；一次覆盖全部 requires_login 站点。非 200/坏 JSON→err。
	SessionAccounts(ctx context.Context) (SessionStatusReport, error)
```

并在 `state` 侧不动的前提下，于 `types.go` 补入向词表常量（与 Task 3 的出向常量分表，防混用）：

```go
// 入向账号状态词表。唯一基准 Java WebsiteSession.SessionStatus（entity/WebsiteSession.java:52-56）。
// 与出向 Task.ExecutionStatus 只有 THROTTLE/EXPIRED 两个词重合，NORMAL 不可回填到回调。
const (
	StatusNormal   = "NORMAL"
	StatusThrottle = "THROTTLE"
	StatusExpired  = "EXPIRED"
)
```

若 `types.go` 与 `events.go` 的常量命名撞车（`StatusThrottle` 在两包各一份），
以包名限定即可（`scheduler.StatusThrottle` 入向 / `state.StatusThrottle` 出向），
**不要把两个词表合成一个常量** —— 它们只有两个词重合，合成一个就会诱导出跨表回填（见 Global Constraints）。

- [ ] **Step 4: 跑测试确认通过**

Run: `go test ./internal/clients/scheduler/ -race -count=1`
Expected: ok；所有实现 `scheduler.Client` 的 fake（`sitestest.go:134`、`base_test.go:947`、`coordinator_test.go:143`、`weibo_test.go:655`、`runtime_test.go:498`、`alk_callback_test.go:231`）需补 `SessionAccounts` 空实现才能编译

- [ ] **Step 5: Commit**

消息首行：`feat(scheduler-client): 新增 GET /session/status 账本快照客户端`

---

### Task 5: `opencli auth status` 全局子命令调用面与四态解析

**Files:**
- Modify: `executor-go/internal/fetcher/fetcher.go`（新增 `ExecuteGlobal`）
- Create: `executor-go/internal/probe/authstatus.go`
- Test: `executor-go/internal/probe/authstatus_test.go`

**Interfaces:**
- Consumes: 假 opencli 桩机制（`sitestest.FakeOpencliPath(t)` + `FAKE_OPENCLI_FIXTURE_*` 环境变量约定）
- Produces:
  - `probe.SiteAuthState{Site string; Status string; LoggedIn *bool; Identity string; Checked string; Error string}`
  - `probe.ParseAuthStatus(raw []byte) (map[string]SiteAuthState, error)`
  - `probe.StatusLive/StatusDead/StatusUnknown/StatusError` 常量

- [ ] **Step 1: 写失败测试（两个解析陷阱都必须覆盖）**

```go
// TestParseAuthStatus 契约源 opencli/src/commands/auth.ts:26-33（AuthStatusRow）：
//   {"site","status","logged_in","identity","checked","error"}
// 两个必须容住的形态：
//   ① logged_in 是 `boolean | ''`（出错/unknown 时给空串而非 null）——
//      直接 Unmarshal 进 bool 会报错；
//   ② status 用下划线（logged_in/not_logged_in），CLI 的 --only 才用连字符；
//   ③ 没有 auth.js 的站点在响应里根本没有行 —— 不得据此判死（spec §6.5）。
func TestParseAuthStatus(t *testing.T) {
	raw := []byte(`[
	 {"site":"weibo","status":"logged_in","logged_in":true,"identity":"","checked":"quick","error":""},
	 {"site":"douyin","status":"not_logged_in","logged_in":false,"identity":"","checked":"quick","error":""},
	 {"site":"zhihu","status":"unknown","logged_in":"","identity":"","checked":"skipped","error":"quickCheck not implemented"},
	 {"site":"bilibili","status":"error","logged_in":"","identity":"","checked":"quick","error":"ETIMEDOUT: browser hung"}
	]`)

	got, err := ParseAuthStatus(raw)
	if err != nil {
		t.Fatalf("ParseAuthStatus: %v", err)
	}
	if len(got) != 4 {
		t.Fatalf("站点数 = %d, want 4", len(got))
	}
	if got["weibo"].Status != StatusLive || got["weibo"].LoggedIn == nil || !*got["weibo"].LoggedIn {
		t.Errorf("weibo 解析走偏: %+v", got["weibo"])
	}
	if got["douyin"].Status != StatusDead {
		t.Errorf("douyin = %q, want not_logged_in", got["douyin"].Status)
	}
	if got["zhihu"].Status != StatusUnknown || got["bilibili"].Status != StatusError {
		t.Errorf("unknown/error 必须与「死亡」区分开: %q %q", got["zhihu"].Status, got["bilibili"].Status)
	}
	if got["zhihu"].LoggedIn != nil {
		t.Error("logged_in 为空串时必须解出 nil，不得当成 false")
	}
}

// TestParseAuthStatusNotArray Java 侧返回裸对象或坏 JSON 一律 err ——
// 空 map 在调用方等价于「全部站点无数据」，会误判成集体死亡。
func TestParseAuthStatusNotArray(t *testing.T) {
	for _, body := range []string{`{}`, `not json`, ``} {
		if _, err := ParseAuthStatus([]byte(body)); err == nil {
			t.Errorf("坏载荷未报错: %q", body)
		}
	}
}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `go test ./internal/probe/ -run TestParseAuthStatus -v -count=1`
Expected: 编译失败（包不存在）

- [ ] **Step 3: 写实现**

`internal/probe/authstatus.go`：

```go
// Package probe 周期对账「执行器 profile 实况」与「调度器账号账本」。
// 设计依据：specs/2026-10-28-session-probe-design.md §5–§6。
package probe

// 出向探活状态词表（opencli auth status 的 status 列，auth.ts:19）。
const (
	StatusLive    = "logged_in"
	StatusDead    = "not_logged_in"
	StatusUnknown = "unknown"
	StatusError   = "error"
)

// SiteAuthState 一站点一行的解析结果。LoggedIn 用 *bool：Java/opencli 在无结论时
// 给空串而非 null（AuthStatusRow.logged_in: boolean | ''），必须能表达"未知"。
type SiteAuthState struct {
	Site     string
	Status   string
	LoggedIn *bool
	Identity string
	Checked  string
	Error    string
}

type wireRow struct {
	Site     string          `json:"site"`
	Status   string          `json:"status"`
	LoggedIn json.RawMessage `json:"logged_in"` // bool 或 ""，见上
	Identity string          `json:"identity"`
	Checked  string          `json:"checked"`
	Error    string          `json:"error"`
}

func ParseAuthStatus(raw []byte) (map[string]SiteAuthState, error) {
	var rows []wireRow
	if err := json.Unmarshal(raw, &rows); err != nil {
		return nil, fmt.Errorf("auth status 载荷非数组: %w", err)
	}
	if rows == nil {
		return nil, fmt.Errorf("auth status 载荷为空/null")
	}
	out := make(map[string]SiteAuthState, len(rows))
	for _, r := range rows {
		if r.Site == "" {
			return nil, fmt.Errorf("auth status 行缺 site: %s", string(raw[:min(len(raw), 120)]))
		}
		var s SiteAuthState
		// logged_in 宽容解：先试 bool，失败即视为"无结论"（空串/其它形态）
		var b bool
		if err := json.Unmarshal(r.LoggedIn, &b); err == nil {
			s.LoggedIn = &b
		}
		s.Site, s.Status, s.Identity, s.Checked, s.Error = r.Site, r.Status, r.Identity, r.Checked, r.Error
		out[r.Site] = s
	}
	return out, nil
}
```

`fetcher.go` 新增全局子命令通道（现有 `Execute*` 的 argv 一律是 `[site, cmd, …]`，`auth` 是顶层命令组，**不能复用**）：

```go
// ExecuteGlobal 发不带站点前缀的全局子命令（opencli auth status --site a,b -f json）。
// 与 Execute 的区别：argv 首位不是 site；不经 ThrottleGate（站点级限速针对抓取，
// 探活是全站一次的控制面调用，套 gate 会让 8 个并发退化成串行等待）。
// 旗标必须与抓取一致地**不传 --profile**：profile 由 env/默认路由决定，
// 一旦探活与抓取落到不同 profile，读到的登录态就不是真的那份。
func (f *Fetcher) ExecuteGlobal(ctx context.Context, timeout time.Duration, args ...string) (json.RawMessage, error)
```

实现要求：复用既有 `newCommand`/超时/SIGKILL 子进程组语义；stdout 原样返回；非零退出返回含 exit code 与 stderr 摘要的 error（与 `Execute` 同口径，便于上层区分 error 与"探活结论 unknown"）。

- [ ] **Step 4: 跑测试确认通过**

Run: `go test ./internal/probe/ ./internal/fetcher/ -race -count=1`
Expected: ok

- [ ] **Step 5: 补一条 argv 断言测试并 commit**

在 `fetcher/cookies_test.go` 同风格新增 `TestExecuteGlobalArgv`，断言 argv 恰为
`["auth","status","--site","weibo,douyin","-f","json","--timeout","8"]` 且**不含站点前缀、不含 `--profile`**。

消息首行：`feat(probe): opencli auth status 全局调用面与四态宽容解析`

---

### Task 6: `probe.Scheduler` 周期对账与三态处置

**Files:**
- Create: `executor-go/internal/probe/scheduler.go`
- Create: `executor-go/internal/probe/scheduler_test.go`
- Modify: `executor-go/internal/app/runtime.go`（装配 + goroutine，对齐 `HeartbeatLoop` 的启动方式 `:287`）
- Modify: `executor-go/internal/config/config.go`（`PROBE_INTERVAL_SECONDS`，默认 3000 = 50min）

**Interfaces:**
- Consumes: `scheduler.Client.SessionAccounts`（Task 4）、`probe.ParseAuthStatus` + `Fetcher.ExecuteGlobal`（Task 5）、`scheduler.Client.LoginSession`（Task 1）、`Coordinator` 窗口 FIFO（`coordinator.go:146-205`）
- Produces:
  - `probe.New(deps Deps, cfg Config) *Scheduler`
  - `type Deps struct { Accounts func(ctx context.Context) (scheduler.SessionStatusReport, error); Auth func(ctx context.Context) ([]byte, error); Export func(ctx context.Context, site string) ([]byte, error); WhoAmI func(ctx context.Context, site string) (string, bool, error); Login func(ctx context.Context, req scheduler.LoginSessionRequest) error; RequestLogin func(site, taskID string); SiteBusy func(site string) bool }`
  - `func (s *Scheduler) Run(ctx context.Context)`（带 jitter 的 ticker）
  - `func (s *Scheduler) reconcileOnce(ctx context.Context) Report`

- [ ] **Step 1: 写失败测试（决策矩阵全组合）**

```go
// TestReconcileMatrix 断言 spec §5-C 的每一种处置。夹具：Java /session/status 现役形态 +
// opencli auth status 四态行。逐条锁定：
//   ① 只有 logged_in 才允许上报（占位行 loginUserId="" 与 identity 必然不等，
//      不设这道闸会对每个空站每轮白跑一次 whoami —— 而 whoami 会导航、改 cookie）；
//   ② not_logged_in + hasNormal → 不弹页（NORMAL 可能全在冷却，代价是多等一轮，spec §6.1）；
//   ③ not_logged_in + !hasNormal → 申请登录窗口；
//   ④ unknown/error → 什么都不做（故障不是死亡）；
//   ⑤ 快照里没有该站 → 不参与（免登录/未登记）。
func TestReconcileMatrix(t *testing.T) {
	cases := []struct {
		name        string
		accounts    map[string][]scheduler.SessionAccount
		authRows    string
		wantLogin   bool // 是否申请登录窗口
		wantReport  bool // 是否 POST /session/exchange
	}{
		{"有货但本地死亡-等待派发",
			map[string][]scheduler.SessionAccount{"weibo": {{Domain: "weibo", LoginUserID: "u1", Status: "NORMAL"}}},
			`[{"site":"weibo","status":"not_logged_in","logged_in":false,"identity":"","checked":"quick","error":""}]`,
			false, false},
		{"无货且本地死亡-弹页",
			map[string][]scheduler.SessionAccount{"weibo": {{Domain: "weibo", LoginUserID: "", Status: "EXPIRED"}}},
			`[{"site":"weibo","status":"not_logged_in","logged_in":false,"identity":"","checked":"quick","error":""}]`,
			true, false},
		{"人肉登录-上报唤醒",
			map[string][]scheduler.SessionAccount{"weibo": {{Domain: "weibo", LoginUserID: "", Status: "EXPIRED"}}},
			`[{"site":"weibo","status":"logged_in","logged_in":true,"identity":"","checked":"quick","error":""}]`,
			false, true},
		{"换账号登录-上报新账号",
			map[string][]scheduler.SessionAccount{"weibo": {{Domain: "weibo", LoginUserID: "u1", Status: "NORMAL"}}},
			`[{"site":"weibo","status":"logged_in","logged_in":true,"identity":"","checked":"quick","error":""}]`,
			false, true},
		{"本地故障-不动",
			map[string][]scheduler.SessionAccount{"weibo": {}},
			`[{"site":"weibo","status":"error","logged_in":"","identity":"","checked":"quick","error":"ETIMEDOUT"}]`,
			false, false},
		{"快照无此站-不参与",
			map[string][]scheduler.SessionAccount{},
			`[{"site":"tieba","status":"not_logged_in","logged_in":false,"identity":"","checked":"quick","error":""}]`,
			false, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			rec := newRecorder(tc.accounts, tc.authRows) // whoami 固定返回 ("u9", true)
			s := New(rec.Deps(), Config{Jitter: 0})
			s.reconcileOnce(context.Background())
			if got := rec.loginCalled; got != tc.wantLogin {
				t.Errorf("申请登录窗口 = %v, want %v", got, tc.wantLogin)
			}
			if got := rec.exchangeCalled; got != tc.wantReport {
				t.Errorf("POST /session/exchange = %v, want %v", got, tc.wantReport)
			}
			if tc.wantReport && rec.lastDomain != "weibo" {
				t.Errorf("exchange 的 domain = %q, want weibo（a.site 同源）", rec.lastDomain)
			}
		})
	}
}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `go test ./internal/probe/ -run TestReconcileMatrix -v -count=1`
Expected: 编译失败 `undefined: New`

- [ ] **Step 3: 写实现**

`scheduler.go` 的处置逻辑要点（完整函数在实现时落码，逐条对应 Step 1 的 ①–⑤）：

```go
// Report 一轮对账的计数，供日志与 /debug/statez 暴露（不新增指标系统）。
type Report struct {
	Sites      int // 快照里的站点数
	Probed     int // auth status 返回了行的站点数
	Reported   int // 触发 POST /session/exchange 的次数
	LoginPaged int // 申请登录窗口的次数
	Skipped    int // busy / 无探活行 / unknown / error
}

func (s *Scheduler) reconcileOnce(ctx context.Context) Report {
	var rep Report

	snap, err := s.deps.Accounts(ctx)
	if err != nil {
		s.log.Warn("[Probe] 账本快照拉取失败，本轮不行动", "err", err) // 空 map 会被判成"全站无货"→批量弹页
		return rep
	}
	if snap.DroppedRows > 0 {
		s.log.Warn("[Probe] 快照有缺 websiteDomain 的孤儿账号行", "dropped", snap.DroppedRows)
	}
	raw, err := s.deps.Auth(ctx)
	if err != nil {
		s.log.Warn("[Probe] auth status 调用失败，本轮不行动", "err", err)
		return rep
	}
	states, err := ParseAuthStatus(raw)
	if err != nil {
		s.log.Warn("[Probe] auth status 载荷不可解析，本轮不行动", "err", err)
		return rep
	}

	rep.Sites = len(snap.BySite)
	for domain, accounts := range snap.BySite { // 宇宙 = 账本快照（spec §5-A），不靠本地登记表
		st, ok := states[domain]
		if !ok {
			rep.Skipped++
			continue // 无 auth.js 的站点在响应里没有行：不判死（spec §6.5），交反应式通道
		}
		rep.Probed++
		if s.deps.SiteBusy(domain) {
			rep.Skipped++
			continue // 抓取在跑或 LOGIN_IN_PROGRESS：不打扰人工扫码窗口（spec §7 互斥约束）
		}
		hasNormal := scheduler.HasNormal(accounts)

		switch st.Status {
		case StatusLive:
			if s.needReport(ctx, domain, accounts) {
				if s.reportSession(ctx, domain) { // whoami→export→POST /session/exchange
					rep.Reported++
				}
			}
		case StatusDead:
			if !hasNormal {
				s.deps.RequestLogin(domain, "") // 只有调度器确实无货才弹页
				rep.LoginPaged++
			}
			// hasNormal：不弹页、不报（NORMAL 可能全在冷却，等下一轮派发覆盖 profile）
		case StatusUnknown, StatusError:
			rep.Skipped++
			s.log.Info("[Probe] 探活无结论，保持原状", "site", domain, "status", st.Status, "err", st.Error)
		}
	}
	return rep
}

// needReport：logged_in 且（无 NORMAL 行 或 本地账号不在快照账号集里）才需要上行。
// quick 模式不返回 identity（runQuick 里 identity 恒空，只有 --full 才填），
// 所以 identity 一律靠 WhoAmI 现取一次 —— 这同时是上报需要的 userId，一次导航两件事用。
// ⚠ 只有本地 logged_in 才走到这里（spec §5 的抑制闸）：无账号站点的快照是
//   loginUserId="" 的占位行，与任何真实 userId 都不等，不设闸就会每轮为每个空站白跑 whoami。
func (s *Scheduler) needReport(ctx context.Context, domain string, accounts []scheduler.SessionAccount) bool {
	userID, loggedIn, err := s.deps.WhoAmI(ctx, domain)
	if err != nil || !loggedIn || userID == "" {
		return false // 取不到身份就不报（宁可漏报一轮，不可用空 userId 造 login_user_id='' 脏行）
	}
	if !scheduler.HasNormal(accounts) {
		return true // 调度器无货：人肉登录/迟到扫码，必须入账
	}
	for _, a := range accounts {
		if a.LoginUserID == userID {
			return false // 已在账本里，状态也还活着
		}
	}
	return true // 换账号登录：新 userId，落一条新账号行
}
```

`Config{IntervalSeconds, Jitter}` 来自 `config.go` 新增的 `PROBE_INTERVAL_SECONDS`（默认 3000，与 `THROTTLE_*` 同一套 `envInt` 读法，`config.go:89-90` 为范式）。`Run` 用 `time.NewTicker(interval)` + 每轮 `rand` 抖动 ≤10%，启动方式对齐 `runtime.go:287` 的 `go coord.HeartbeatLoop(runCtx, id)`，并在 `runCtx` 取消时退出。

- [ ] **Step 4: 跑测试确认通过**

Run: `go test ./internal/probe/ ./internal/app/ -race -count=1`
Expected: ok

- [ ] **Step 5: Commit**

消息首行：`feat(probe): 周期对账账本与 profile 的会话探活调度器`

---

### Task 7: 死码清理（与 Java 现役契约不符的残留）

**Files:**
- Modify: `executor-go/internal/state/task.go:18`
- Modify: `executor-go/internal/clients/scheduler/client.go:64-65,278-295`（删 `WebsiteDetail`）
- Modify: 各 fake（`sitestest.go:134`、`base_test.go:947`、`coordinator_test.go:143`、`weibo_test.go:655`、`runtime_test.go:498`、`alk_callback_test.go:231`）
- Test: `executor-go/internal/clients/scheduler/session_client_test.go:97-130`（删 `TestWebsiteDetail`）

**Interfaces:**
- Consumes: Task 1/4（`SessionAccounts` 已取代 `WebsiteDetail` 的用途；`LoginSessionRequest.Domain` 已不再需要数字 id）
- Produces: 无对外接口变化（纯删除）

- [ ] **Step 1: 确认零调用方再动手**

```bash
cd executor-go
grep -rn "SessionPath" --include="*.go" . | grep -v "_test.go"          # 期望：只有 task.go 的定义行
grep -rn "WebsiteDetail" --include="*.go" . | grep -v "_test.go"          # 期望：只有 client.go 的声明与实现
grep -rn "task/resume\|/session/login" --include="*.go" .                  # 期望：0（Task 1 已改名）
```

- [ ] **Step 2: 删 `Task.SessionPath`**

Java `TaskRequest` 无此键（`model/TaskRequest.java:22-49` 全量核对），全仓零读写点；e2e fixture 里的 `"sessionPath":""` 字面量一并清掉（`encoding/json` 忽略未知键，删字段不影响旧夹具解析）。

- [ ] **Step 3: 删 `WebsiteDetail`**

接口声明 + `httpClient.WebsiteDetail` 实现 + `TestWebsiteDetail` + 6 个 fake 的空实现。理由：`84664ea` 起 Java 的 login DTO 改收 `domain`，`/website/{domain}/detail` 前置往返已退役（`runtime.go:236` 注释在案），生产调用方为零。

- [ ] **Step 4: 全量验收线**

Run: `go build ./... && go vet ./... && go test ./... -race -count=1`
Expected: 全绿；若 `test/e2e` 有 FAIL，先按 `docs` 记录的既有失败基线（`TestAlkCallbackEndToEnd` flaky、`TestSiteXueqiuSearchPostsEndToEnd`）核对是不是本任务引入

- [ ] **Step 5: Commit**

消息首行：`chore(executor-go): 清理与会话现役契约不符的死码`

---

## 合并与实开取证（Task 7 之后，一次性）

1. 合并 `feat/session-probe` → 本地 `develop`（合并前 `git fetch origin develop` 确认无他人新提交）。
2. 容器生效按手册 §2.2：`go build -trimpath -ldflags="-s -w" -o /tmp/…/executor ./cmd/executor` → **先过 `/debug/statez` 硬闸门确认无站点在跑** → `docker cp` → 重启走 `telescope-executor-ops`（mac 需 `GOOS=linux GOARCH=amd64`，容器实测 x86_64）。
3. 取证四步（spec §8 列的 1–4），逐条留 before/after。
4. 单站点检查期间开 `DEBUG_SITES`，收尾必须删除并重建容器。
5. `git push` 需单独批准。
