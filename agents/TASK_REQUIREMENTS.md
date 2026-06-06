# Panda Trading — 多 Agent 协作任务规范

## 概述

本文档定义 panda-trading 项目中多 Agent 协作开发的完整规范，包括各 Agent 的职责边界、协作流程、信息传递格式和完备性检查。

---

## Agent 角色一览

| Agent | 目录 | 核心职责 |
|---|---|---|
| 主 Agent | `agents/main-agent/` | 任务调度、子 Agent 编排、流程把控 |
| 需求分析 Agent | `agents/analyst-agent/` | 读取 jobs/*.txt，输出结构化任务描述 |
| Build 开发 Agent | `agents/dev-build-agent/` | 开发 BUILD 类工具，运行 panda-builder skill |
| Alpha 开发 Agent | `agents/dev-alpha-agent/` | 开发 Alpha 信号与因子 |
| 测试 Agent | `agents/test-agent/` | 生成测试用例与测试报告，无代码修改权限 |

---

## 完整开发流程

```
用户下达任务
     │
     ▼
┌─────────────┐
│  主 Agent   │──── 读取 CLAUDE.md + TASK_REQUIREMENTS.md
└──────┬──────┘
       │ 1. 派发分析任务
       ▼
┌──────────────────┐
│  需求分析 Agent  │──── 读取 jobs/*.txt
└──────┬───────────┘
       │ 2. 返回结构化任务描述 (TaskSpec)
       ▼
┌─────────────┐
│  主 Agent   │──── 判断任务类型 (B* → Build, A* → Alpha)
└──────┬──────┘
       │ 3. 派发开发任务 + TaskSpec
       ▼
┌────────────────────────────────────┐
│  开发 Agent (Build 或 Alpha)       │──── 运行对应 Skill + Python 验证
└──────┬─────────────────────────────┘
       │ 4. 返回开发产物路径 + 自检报告
       ▼
┌─────────────┐
│  主 Agent   │──── 派发测试任务
└──────┬──────┘
       │ 5. 派发测试任务 + 开发产物路径
       ▼
┌───────────────┐
│  测试 Agent   │──── 生成测试用例 + 运行 + 输出报告
└──────┬────────┘
       │ 6. 返回测试报告 (TestReport)
       ▼
┌─────────────┐          测试通过?
│  主 Agent   │─────────────────────── 是 ──→ 任务完成 ✓
└──────┬──────┘
       │ 否 (含 Bug 清单)
       │ 7. 携带 TestReport 重新派发开发 Agent
       └──→ 回到步骤 3，最多循环 3 次
              超过 3 次仍失败 → 上报给用户
```

---

## 信息传递格式

### TaskSpec（需求分析 Agent → 主 Agent）

```python
{
    "job_file": "B12 日内仓位动态管理.txt",   # 原始任务文件名
    "task_id": "B12",                         # 任务编号
    "task_type": "build",                     # "build" | "alpha"
    "task_name": "日内仓位动态管理",           # 任务名称
    "target_dir": "src/build/build-B12/开发产物/",  # 输出目录
    "summary": "...",                         # 一句话描述
    "inputs": [                               # 输入字段列表
        {"field": "code", "type": "str", "desc": "股票代码"},
        ...
    ],
    "outputs": [                              # 输出字段列表
        {"field": "action", "type": "str", "desc": "buy/sell/hold"},
        ...
    ],
    "logic": "...",                           # 核心逻辑描述（分点）
    "constraints": ["最小单位100股", "收盘前15分强平"],  # 业务约束
    "production_type": "调用型",              # "调用型" | "结果型" | "混合型"
    "ambiguities": ["输出字段未定义", ...]    # 待澄清项
}
```

### DevReport（开发 Agent → 主 Agent）

```python
{
    "task_id": "B12",
    "status": "success",          # "success" | "partial" | "failed"
    "artifacts": [                # 产出物路径列表
        "src/build/build-B12/开发产物/scripts/build.py",
        "src/build/build-B12/开发产物/scripts/test.py",
        "src/build/build-B12/开发产物/SKILL.md",
    ],
    "run_output": "...",          # python3 build.py 的实际输出
    "checklist": {                # panda-builder 验收清单
        "run_ok": True,
        "run_entry": True,
        "validate_input": True,
        "skill_md": True,
        "test_py": True,
    },
    "notes": "..."                # 备注（如待澄清项的处理方式）
}
```

### TestReport（测试 Agent → 主 Agent）

```python
{
    "task_id": "B12",
    "passed": True,               # 整体是否通过
    "total_cases": 10,
    "pass_count": 9,
    "fail_count": 1,
    "cases": [
        {
            "name": "正常输入-浮盈1.5%加仓",
            "status": "pass",
            "input": {...},
            "expected": {...},
            "actual": {...},
            "diff": ""
        },
        {
            "name": "边界值-浮亏恰好0.5%",
            "status": "fail",
            "input": {...},
            "expected": {"action": "sell", "qty_change": -500},
            "actual": {"action": "hold"},
            "diff": "qty_change 应为 -500，实际为 0"
        }
    ],
    "bugs": [                     # Bug 清单，供开发 Agent 修复
        {
            "id": "BUG-1",
            "severity": "high",   # "high" | "medium" | "low"
            "file": "scripts/build.py",
            "line_hint": 42,
            "description": "浮亏 0.5% 边界条件使用了 > 而非 >=",
            "reproduce": "input pnl_pct=-0.005 期望触发砍半仓但实际 hold"
        }
    ],
    "coverage_notes": "未覆盖：收盘前强平逻辑、资金不足时的降级处理"
}
```

---

## 权限与约束矩阵

| 能力 | 主 Agent | 需求分析 Agent | Build 开发 Agent | Alpha 开发 Agent | 测试 Agent |
|---|:---:|:---:|:---:|:---:|:---:|
| 读取 jobs/*.txt | ✓ | ✓ | ✗ | ✗ | ✗ |
| 写入 src/build/ | ✓ | ✗ | ✓ | ✗ | ✗ |
| 写入 src/alpha/ | ✓ | ✗ | ✗ | ✓ | ✗ |
| 运行 Python 脚本 | ✓ | ✗ | ✓ | ✓ | ✓（只读运行）|
| 修改已有代码 | ✓ | ✗ | ✓ | ✓ | ✗ |
| 生成测试报告 | ✗ | ✗ | ✗ | ✗ | ✓ |
| 调用 panda-builder skill | ✗ | ✗ | ✓ | ✗ | ✗ |
| 派发子 Agent | ✓ | ✗ | ✗ | ✗ | ✗ |

---

## 流程完备性说明

### 已覆盖场景

- [x] BUILD 任务（B 前缀）完整开发流程
- [x] Alpha 任务（A 前缀）完整开发流程
- [x] 需求不清晰时的歧义上报机制（`ambiguities` 字段）
- [x] 测试失败后的迭代修复（最多 3 轮）
- [x] 验收检查清单（panda-builder 6 项）
- [x] 权限隔离（测试 Agent 无法修改代码）

### 边界规则

- 需求分析 Agent **不得**猜测未说明的字段，歧义项必须列入 `ambiguities` 上报
- 测试 Agent **不得**直接修改任何 `.py` 文件，只能运行和读取
- 开发 Agent 每次提交前必须确认 `python3 scripts/build.py` 能独立跑通
- 主 Agent 在循环超过 3 次仍有 `high` severity bug 时，停止并向用户汇报

---

## 目录结构

```
agents/
├── TASK_REQUIREMENTS.md      ← 本文件，多 Agent 协作总规范
├── main-agent/
│   └── SKILL.md              ← 主 Agent 职责与调度规则
├── analyst-agent/
│   └── SKILL.md              ← 需求分析 Agent 规则
├── dev-build-agent/
│   └── SKILL.md              ← Build 开发 Agent 规则
├── dev-alpha-agent/
│   └── SKILL.md              ← Alpha 开发 Agent 规则
└── test-agent/
    └── SKILL.md              ← 测试 Agent 规则
```
