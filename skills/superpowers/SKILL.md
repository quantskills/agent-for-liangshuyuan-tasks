---
name: superpowers
description: 路由表 — superpowers 技能库（14 个技能）的入口。当任务涉及：写新功能/做设计需先梳理需求（brainstorming）、遇到 bug 或测试失败要先找根因（systematic-debugging）、写实现计划（writing-plans）、按计划执行（executing-plans / subagent-driven-development）、写代码前先写测试（test-driven-development）、任务收尾前验证（verification-before-completion）、请求或接收 code review、并行派发子代理、用 git worktree 隔离、或要新建/修改 skill 本身时，先用本 skill 定位，再 Read 对应子目录的 SKILL.md 全文并遵循。
---

# Superpowers 技能库（路由表）

本目录 (`skills/superpowers/`) 是 superpowers 技能库。**注意：这些技能不是 harness 注册的 skill**，
所以它们不出现在系统的 skill 列表里，也不能用 `superpowers:xxx` 语法调用。

**使用方法：先在本表定位，再 `Read skills/superpowers/<目录名>/SKILL.md` 全文，然后严格按该 skill 执行**
（有 checklist 就逐条建 todo）。读全文前不要开始动手 —— 这些 skill 的正文才是规范所在。

## 技能索引

| 目录 | 何时用 |
|------|--------|
| `using-superpowers/` | **对话开始时**的总纲：要求任何响应（含追问）之前先查 skill。含平台适配（Codex/Pi/Hermes 见 `references/`） |
| `brainstorming/` | **任何创造性工作之前**：做新功能、加组件、改行为。先厘清用户意图 / 需求 / 设计，再进入实现或 plan mode。产出写入 `specs/` |
| `writing-plans/` | 已有 spec 或明确需求的多步任务，**动代码之前**。产出的计划写入 `plans/` |
| `executing-plans/` | 有一份写好的实现计划，要在**独立会话**中带 review checkpoint 执行 |
| `subagent-driven-development/` | 在当前会话执行实现计划，适合任务之间相互独立、可派子代理。含 implementer / reviewer 提示词模板与 `scripts/` 辅助脚本 |
| `dispatching-parallel-agents/` | 有 **2 个以上**互不依赖（无共享状态、无先后顺序）的任务时并行派发 |
| `test-driven-development/` | **写实现代码之前**：任何 feature 或 bugfix。含 `writing-good-tests.md` |
| `systematic-debugging/` | **任何 bug / 测试失败 / 异常行为，在提出修复之前**。先找根因，禁止打症状补丁。含 `root-cause-tracing.md`、`defense-in-depth.md`、`condition-based-waiting.md` |
| `verification-before-completion/` | 将要声称"完成 / 修好 / 通过"之前，或提交 / 建 PR 之前：必须实跑验证命令并确认输出，用证据说话 |
| `requesting-code-review/` | 完成任务、实现大功能、或合并之前，请人 review 以核对是否满足需求。含 `code-reviewer.md` 提示词 |
| `receiving-code-review/` | 收到 review 意见、开始改之前（尤其意见含糊或技术上存疑时）：要技术性地核实，不要表演式认同或盲从 |
| `using-git-worktrees/` | 需要与当前工作区隔离地开发时，或要执行实现计划之前：用原生工具或 git worktree 建隔离工作区 |
| `finishing-a-development-branch/` | 实现完成、测试全过、要决定如何合入时 |
| `writing-skills/` | 新建 skill、改已有 skill、或部署前验证 skill 是否有效时。含 `anthropic-best-practices.md`、`graphviz-conventions.dot`、`testing-skills-with-subagents.md` |

## 优先级

多个技能都沾边时，**流程类技能优先** —— 先由它定方法，再由实现类技能落地：

- "我们来做 X" → 先 `brainstorming`，再实现类技能
- "修这个 bug" → 先 `systematic-debugging`，再领域技能
- 有 spec 要落地 → `writing-plans` →（`subagent-driven-development` 或 `executing-plans`）→ `verification-before-completion`

## 本仓目录约定

- `specs/` — `brainstorming` 产出的设计文档，命名 `YYYY-MM-DD-<topic>-design.md`
- `plans/` — `writing-plans` 产出的实现计划，命名 `YYYY-MM-DD-<feature>.md`
- 两者各自的 `README.md` 有详细约定。它们是数据目录，不是 skill。

## 与项目规则的关系

本仓 `../../AGENTS.md` 及其引用的项目 skill（`telescope-*`、`opencli-*` 等）优先于本技能库；
本技能库优先于默认行为。