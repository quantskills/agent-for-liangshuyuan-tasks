# 🐼 Panda Trading · Quantitative Toolkit

> A modular quantitative trading tool library powered by Claude Code Multi-Agent Collaboration — Pure Python · Zero Framework Dependencies · Skill Architecture

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

---

## 📖 Overview

**Panda Trading (量枢学院)** is a modular quantitative trading development platform that uses an **Atomic Skill** + **Multi-Agent Collaboration** architecture to decompose core trading capabilities into independent, reusable BUILD tools and Alpha factors.

The project is built with the **Python standard library only** — no pandas, numpy, or other third-party dependencies (unless explicitly required by a task), ensuring every Skill is lightweight, self-contained, and freely callable by agents or Alpha signals.

### Core Principles

| Principle | Description |
|---|---|
| **Skills are Tools** | Each subdirectory is an independent trading BUILD skill — runnable, testable, and deployable in isolation |
| **BUILD Serves Alpha** | BUILD is the tool layer; Alpha is the signal layer. Alpha calls BUILD, never duplicates its logic |
| **Agent Collaboration** | Multi-agent pipeline: analysis → development → testing → acceptance, fully automated |
| **Zero Dependencies** | Pure Python standard library by default — runs anywhere without setup |

---

## 🏗️ Architecture

### Skill System

```
skills/
└── panda-builder/          ← Scaffold Skill: unified spec for creating/verifying BUILD skills
```

### Task Classification

| Prefix | Type | Directory | Description |
|---|---|---|---|
| **B** | BUILD Tool | `src/build/` | Data processing, position management, monitoring, review analysis |
| **A** | Alpha Factor | `src/alpha/` | Stock & futures Alpha signals and factors |

### Multi-Agent Collaboration

```
User issues a task
     │
     ▼
┌─────────────────┐      ┌────────────────────┐
│   Main Agent    │─────→│  Analyst Agent     │  Reads jobs/*.txt, outputs TaskSpec
└────────┬────────┘      └────────────────────┘
         │ ←── TaskSpec (with ambiguity flags)
         │
         ├── B-type task → Build Dev Agent + panda-builder skill
         ├── A-type task → Alpha Dev Agent
         │
         │ ←── DevReport (artifacts + self-check report)
         ▼
┌─────────────────┐
│   Test Agent    │  Generates test cases → runs → outputs TestReport
└────────┬────────┘
         │ ←── Pass ✓ / Fail (bugs flow back, max 3 iterations)
         ▼
     Task Complete
```

| Agent | Responsibility | Write Access |
|---|---|---|
| **Main Agent** (`agents/main-agent/`) | Orchestration, connects all sub-agents | Yes |
| **Analyst Agent** (`agents/analyst-agent/`) | Reads `jobs/*.txt`, outputs TaskSpec | Read-only |
| **Build Dev Agent** (`agents/dev-build-agent/`) | Develops B-type tasks with panda-builder | `src/build/` |
| **Alpha Dev Agent** (`agents/dev-alpha-agent/`) | Develops A-type tasks | `src/alpha/` |
| **Test Agent** (`agents/test-agent/`) | Generates test cases & reports | Read-only execution |

---

## 📦 Implemented Modules

### B12 — Multi-Instrument Intraday Position Manager v2

**Supported instruments**: A-Shares / A-Share ETFs / Index Futures / Commodity Futures / HK Stocks & ETFs

**Decision rules** (priority high → low):

| Priority | Condition | Action |
|---|---|---|
| 1 | time ≥ instrument force-close time | Force liquidate (by sellable_qty) |
| 2 | PnL ≤ -1% | Full stop-loss |
| 3 | PnL ≤ -0.5% | Cut half position |
| 4 | PnL > +1% | Add 50% (with cash/margin check) |
| 5 | Otherwise | Hold |

**Features**:

- ✅ T+1 / T+0 differentiation (A-shares/ETFs block selling locked positions)
- ✅ Yesterday/today position separation (sellable_qty / locked_qty)
- ✅ Independent margin/cash validation — blocks orders when insufficient
- ✅ Contract multiplier central table (contract_specs.json)
- ✅ HK stock lot_size override table
- ✅ Standard 8-field order instruction + structured reason prefix

```python
# Usage example
from scripts.build import run

results = run([
    {"code": "600036", "pnl_pct":  0.015, "sellable_qty":  800, "locked_qty":   0,
     "price": 10.0,    "available_cash": 100000, "time": "10:00"},
    {"code": "IF2406", "pnl_pct":  0.015, "sellable_qty":    2, "locked_qty":   0,
     "price": 4000.0,  "available_cash": 200000, "time": "10:00"},
    {"code":  "00700", "pnl_pct": -0.007, "sellable_qty":  200, "locked_qty":   0,
     "price": 400.0,   "available_cash":      0, "time": "10:00"},
])
```

### Planned Tasks

| ID | Task | Status |
|---|---|---|
| B5 | Morning Auction Scanner | 📋 Requirements recorded |
| B12 | Position Manager v3 (short/bidirectional/spread) | 🔜 Planned |

---

## 📂 Project Structure

```
panda-trading/
├── README.md                       ← Chinese readme
├── README.en.md                    ← English readme (this file)
├── LICENSE                         ← MIT License
├── CLAUDE.md                       ← Claude Code project spec (Agent collaboration, Skill architecture, data interfaces)
│
├── agents/                         ← Multi-agent collaboration specs
│   ├── TASK_REQUIREMENTS.md        ←   Agent roles, workflow, message formats
│   ├── main-agent/SKILL.md         ←   Main Agent orchestration rules
│   ├── analyst-agent/SKILL.md      ←   Analyst Agent rules
│   ├── dev-build-agent/SKILL.md    ←   Build Dev Agent rules
│   ├── dev-alpha-agent/SKILL.md    ←   Alpha Dev Agent rules
│   └── test-agent/SKILL.md         ←   Test Agent rules
│
├── skills/                         ← Local project skills
│   └── panda-builder/              ←   BUILD scaffold & verification spec
│       ├── SKILL.md
│       └── skill.json
│
├── docs/                           ← Production rule docs
│   ├── BUILD开发与生产规则V2.md     ←   BUILD tool development full-lifecycle spec
│   └── Alpha因子开发与生产规则V2.md ←   Alpha factor development & production spec
│
├── jobs/                           ← Raw task requirements
│   ├── B12 日内仓位动态管理.txt    ←   Completed
│   └── B5 早盘竞价扫描.txt         ←   Pending
│
└── src/                            ← Development artifacts (all outputs go here)
    ├── build/                      ←   BUILD tools
    │   └── build-B12/              ←     B12 Intraday Position Manager
    │       └── 开发产物/            ←       (development artifacts)
    │           ├── SKILL.md
    │           ├── scripts/
    │           │   ├── build.py        ← Main entry: run() + validate_input()
    │           │   ├── test.py         ← Self-test script
    │           │   ├── common.py       ← Shared constants & utilities
    │           │   ├── classify.py     ← Instrument classification
    │           │   ├── specs.py        ← Contract spec loader
    │           │   └── markets/        ← Market modules
    │           │       ├── a_stock.py          ← A-Shares + ETFs (T+1)
    │           │       ├── index_future.py     ← Index Futures (IF/IC/IH/IM)
    │           │       ├── commodity_future.py ← Commodity Futures
    │           │       └── hk_stock.py         ← HK Stocks + ETFs (T+0)
    │           └── references/
    │               ├── api_guide.md     ← API documentation
    │               └── contract_specs.json ← Contract specs central table
    └── alpha/                      ←   Alpha factors (reserved)
```

---

## 🚀 Quick Start

### Requirements

- Python 3.8+
- No third-party dependencies (stdlib only)

### Run B12 Position Manager

```bash
# Direct run (includes built-in examples)
python3 src/build/build-B12/开发产物/scripts/build.py

# Run tests
python3 src/build/build-B12/开发产物/scripts/test.py
```

### Use as a Module

```python
import sys
sys.path.insert(0, "src/build/build-B12/开发产物/scripts")
from build import run

# Single position
order = run({
    "code": "600036",
    "pnl_pct": 0.015,
    "sellable_qty": 800,
    "locked_qty": 0,
    "price": 10.0,
    "available_cash": 100000,
    "time": "10:00",
})

# Batch
orders = run([...])   # Pass a list for batch processing
```

---

## 📐 Development Standards

### BUILD Skill Directory Structure (panda-builder spec)

```
build-{id}-{name}/
├── 开发产物/                     ← Development artifacts
│   ├── SKILL.md                   ← Skill specification (required)
│   ├── scripts/
│   │   ├── build.py               ← Main script: must include run() + validate_input()
│   │   └── test.py                ← Test script (required)
│   ├── references/
│   │   └── api_guide.md           ← Data interface docs (required)
│   └── demo.mp4                   ← Demo video (required)
└── 生产产物/                      ← Production artifacts (result-type BUILD only)
    ├── SKILL.md
    └── 数据库.parquet
```

### Standard Order Instruction Format

```python
{
    "code": str,         # Instrument code
    "pnl_pct": float,    # P&L percentage (decimal: 0.01 = +1%)
    "current_qty": int,  # Current total position
    "time": str,         # HH:MM
    "action": str,       # "buy" / "sell" / "hold"
    "qty_change": int,   # Positive = add, negative = reduce
    "target_qty": int,   # Target position
    "reason": str,       # Trigger reason
}
```

### A-Share Trading Constraints

- Minimum trading unit: 100 shares (all quantity changes round down to multiples of 100)
- Market close: 15:00, force-close window: 14:45
- T+1 Rule: Positions opened today are locked and cannot be sold same-day

### BUILD Production Types

| Type | When to use | Deliverables |
|---|---|---|
| **Callable** | Lightweight, real-time, depends on caller input | `SKILL.md + scripts/` |
| **Result-type** | Heavy computation, multi-consumer, scheduled, needs caching | `SKILL.md + 数据库.parquet` |
| **Hybrid** | Supports both instant calls and scheduled production | All of the above |

---

## 🤝 Contributing

1. **Fork** this repository
2. Create a `Feat_xxx` branch
3. Place your work under `src/build/` or `src/alpha/`, following panda-builder conventions
4. Ensure `python3 scripts/build.py` runs independently
5. Commit and create a **Pull Request**

### Minimal Steps to Develop a BUILD Skill

```bash
# 1. Create directory structure
mkdir -p src/build/build-{id}-{name}/开发产物/{scripts,references}

# 2. Write build.py (must implement run() and validate_input())
# 3. Write test.py (cover normal/edge/error cases)
# 4. Write SKILL.md (specification)
# 5. Write references/api_guide.md (API docs)

# 6. Self-test
python3 src/build/build-{id}-{name}/开发产物/scripts/build.py
python3 src/build/build-{id}-{name}/开发产物/scripts/test.py

# 7. Commit
```

---

---

## 🤖 External AI Guide

> If you are an external AI (e.g., Claude Code, Copilot, Cursor, etc.), follow this standard protocol upon entering this repository.

### Step 1: Skill Discovery

Traverse `src/build/` and `src/alpha/` directories — each subdirectory matching `build-{id}-{name}/` or `alpha-{id}-{name}/` is a Skill:

```bash
# List all implemented BUILD skills
ls -d src/build/build-*/开发产物/

# List all implemented Alpha skills
ls -d src/alpha/alpha-*/
```

### Step 2: Read SKILL.md — Understand the Skill

Each Skill's `开发产物/SKILL.md` is its atomic specification document. Always read it first. The frontmatter and body tell you:

| What you need to know | Where to find it in SKILL.md |
|---|---|
| What problem this Skill solves | `description` (frontmatter) + `## 工具定位` |
| When to use it | `## 适用场景` |
| Required input fields | `## 输入` table |
| Output fields | `## 输出` table |
| How to invoke it | `## 调用方式` (includes Python import example) |
| Whether Alpha can call it | `## 可被 Alpha 调用` |
| Whether it produces Parquet results | `## 是否需要生产结果` |

### Step 3: Validate the Skill

Run these checks on each Skill:

```bash
BUILD_DIR="src/build/build-B12/开发产物"   # Replace with the Skill you're checking

# 1. Structural integrity
echo "=== Required files ==="
for f in SKILL.md scripts/build.py scripts/test.py references/api_guide.md; do
  [ -f "$BUILD_DIR/$f" ] && echo "✅ $f" || echo "❌ Missing $f"
done

# 2. Code entry points — build.py must implement run() + validate_input()
echo ""
echo "=== Entry functions ==="
grep -q "def run(" "$BUILD_DIR/scripts/build.py" && echo "✅ run()" || echo "❌ Missing run()"
grep -q "def validate_input(" "$BUILD_DIR/scripts/build.py" && echo "✅ validate_input()" || echo "❌ Missing validate_input()"

# 3. Self-test
echo ""
echo "=== Self-test ==="
python3 "$BUILD_DIR/scripts/build.py" && echo "✅ build.py runs independently" || echo "❌ build.py failed"
python3 "$BUILD_DIR/scripts/test.py" && echo "✅ test.py passed" || echo "❌ test.py failed"
```

### Step 4: Invoke the Skill

All BUILD skills follow a unified calling convention. For **callable** BUILD skills (e.g., B12), import directly:

```python
import sys
sys.path.insert(0, "src/build/build-B12/开发产物/scripts")
from build import run

# Single input (dict) → single output (dict)
order = run({
    "code": "600036", "pnl_pct": 0.015,
    "sellable_qty": 800, "locked_qty": 0,
    "price": 10.0, "available_cash": 100000, "time": "10:00",
})

# Batch input (list) → batch output (list)
orders = run([pos1, pos2, pos3])
```

For **result-type** BUILD skills, read `生产产物/数据库.parquet` directly — do NOT re-pull raw data and re-compute.

### Step 5: Determine Production Type

| Type | How to identify | Correct action |
|---|---|---|
| **Callable** | SKILL.md states "是否需要生产结果：否" | `import build; build.run(data)` |
| **Result-type** | `生产产物/数据库.parquet` exists | Read Parquet directly, do not recompute |
| **Hybrid** | Both exist | Prefer reading Parquet; call build.py when needed |

### Common Mistakes (AI should avoid)

- ❌ Making position decisions ad-hoc instead of calling the B12 position manager Skill
- ❌ Re-pulling raw market data and re-computing factors for result-type BUILD skills
- ❌ Ignoring documented limitations in SKILL.md (e.g., B12 is long-only)
- ❌ Guessing input/output formats without reading `references/api_guide.md`
- ❌ Skipping `validate_input()` and passing dirty data directly

---

## 📄 License

This project is open-sourced under the [MIT License](./LICENSE). Copyright (c) 2026 Maduan.

---

## 📚 References

- [BUILD Development & Production Rules V2](./docs/BUILD开发与生产规则V2.md) (Chinese)
- [Alpha Factor Development & Production Rules V2](./docs/Alpha因子开发与生产规则V2.md) (Chinese)
- [Multi-Agent Collaboration Spec](./agents/TASK_REQUIREMENTS.md) (Chinese)
- [panda-builder Skill Spec](./skills/panda-builder/SKILL.md) (Chinese)
- [B12 API Documentation](./src/build/build-B12/开发产物/references/api_guide.md) (Chinese)
