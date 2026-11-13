# 🐼 Panda Trading · Quantitative Toolkit

> A modular quantitative trading tool library powered by Claude Code Multi-Agent Collaboration — Pure Python · Zero Framework Dependencies · Skill Architecture

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

---

## 📖 Overview

**Panda Trading (量枢学院)** is a modular quantitative trading development platform that uses an **Atomic Skill** + **Multi-Agent Collaboration** architecture to decompose core trading capabilities into independent, reusable BUILD tools and Alpha factors.

The project uses the **Python standard library by default** — no pandas, numpy, or other third-party dependencies unless a task explicitly requires them — ensuring every skill is lightweight, self-contained, and freely callable by agents or Alpha signals.

This is an **Agent-type repository** (`agent-for-liangshuyuan-tasks`), compliant with QuantSkills community rules. See `AGENTS.md` for the agent declaration.

### Core Principles

| Principle | Description |
|---|---|
| **Skills are Tools** | Each subdirectory is an independent trading skill — runnable, testable, and releasable in isolation |
| **BUILD Serves Alpha** | BUILD is the tool layer; Alpha is the signal layer. Alpha calls BUILD, never duplicates its logic |
| **Agent Collaboration** | Multi-agent pipeline: analysis → development → testing → publishing, fully automated |
| **Zero Dependencies** | Pure Python standard library by default — runs anywhere without setup |

### Maintainer

- 段绪勇 [https://github.com/duanyong](https://github.com/duanyong)
- Community: QuantSkills (https://github.com/quantskills)

---

## 🏗️ Architecture

### Task Classification

| Prefix | Type | Directory | Description |
|---|---|---|---|
| **B** | BUILD Tool | `src/skills/` | Data processing, position management, monitoring, review analysis |
| **A** | Alpha Factor | `src/skills/` | Stock & futures Alpha signals and factors |

Task IDs (e.g. `B12`, `A00`) are used only for routing and traceability — they never appear in skill names. Every skill is named `skill-{slug}`.

### Multi-Agent Collaboration

Put task requirements into `jobs/*.txt`, and the Agent system handles the full pipeline:

```
jobs/B{id} {name}.txt
     │
     ▼
┌──────────────────┐
│  Analyst Agent   │  Reads job file → identifies B/A type → outputs TaskSpec
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│  Main Agent  │── B-type → Build Dev Agent + panda-builder
└──────┬──────┘── A-type → Alpha Dev Agent
       │
       │ ←── DevReport (skill path + self-check)
       ▼
┌─────────────┐
│  Test Agent  │  Generates cases → runs → TestReport
└──────┬──────┘
       │ ←── Pass ✓ / Fail (bugs rebound, max 3 iterations)
       ▼
┌─────────────┐
│ Publish Agent│  Create GitHub repo skill-{slug} → copy skill artifacts
│              │  → add compliance files → push to quantskills org
└──────┬──────┘
       │
       ▼
   ✅ Complete + Published (QuantSkills Community Rules compliant)
```

| Agent | Responsibility | Spec |
|---|---|---|
| **Analyst** | Reads `jobs/*.txt`, outputs TaskSpec | `agents/analyst-agent/SKILL.md` |
| **Build/Alpha Dev** | Codes to TaskSpec, outputs a `skill-{slug}` directory | `agents/dev-{build,alpha}-agent/SKILL.md` |
| **Test** | Generates test cases, validates I/O, reports bugs | `agents/test-agent/SKILL.md` |
| **Publish** | Publishes as a standalone quantskills repo | `agents/publish-agent/SKILL.md` |

---

## 📂 Project Structure

```
panda-trading/
├── README.md                       ← Chinese README
├── README.en.md                    ← English README (this file)
├── LICENSE                         ← GPL-3.0
├── AGENTS.md                       ← Agent declaration (QuantSkills community rules)
├── CLAUDE.md                       ← Claude Code project spec
│
├── agents/                         ← Multi-agent collaboration specs
│   ├── TASK_REQUIREMENTS.md
│   ├── main-agent/SKILL.md
│   ├── analyst-agent/SKILL.md
│   ├── dev-build-agent/SKILL.md
│   ├── dev-alpha-agent/SKILL.md
│   ├── test-agent/SKILL.md
│   └── publish-agent/SKILL.md
│
├── skills/                         ← Local project skills
│   └── panda-builder/              ← Skill scaffold & acceptance rules
│
├── docs/                           ← Development rule documents
│   ├── BUILD开发规则V2.md
│   └── Alpha因子开发规则V2.md
│
├── jobs/                           ← Raw task requirements
│
├── public/                         ← Publish workspace (gitignored, not committed)
│   └── skills/
│       └── skill-dl-gnn-stock-graph/   ← Reference: approved skill
│
└── src/
    └── skills/                     ← Development artifacts (all outputs live here)
        └── skill-{slug}/           ←   One self-contained skill per task
```

### Standard skill layout

```
skill-{slug}/
├── SKILL.md              ← Skill specification (required)
├── README.md             ← Chinese docs with ## ⚠️ 免责声明 (required)
├── README.en.md          ← English docs (required)
├── LICENSE               ← Full GPL-3.0 text (required)
├── INSTALL.md            ← Multi-platform install guide (required)
├── requirements.txt      ← Python dependencies (required)
├── skill.json            ← Skill metadata (required)
├── CHANGELOG.md          ← Version history (required)
├── scripts/              ← Implementation (required)
├── tests/                ← Unit tests (required)
├── references/           ← API & boundary docs (required)
└── agents/               ← Runtime adapters (required)
    ├── cursor-rule.mdc      ← Cursor
    ├── portable-loader.md   ← Hermes / OpenClaw
    └── openai.yaml          ← Codex / OpenClaw
```

> **There is no `开发产物/` or `生产产物/` directory, and no separate production SKILL.md.** Result-producing skills write to `output/` (gitignored); paths and fields are documented in the same `SKILL.md` and `references/`.

---

## 🚀 Quick Start

### Requirements

- Python 3.8+
- No third-party dependencies by default (standard library is enough; some skills declare extras in `requirements.txt`)

### Run a skill

```bash
cd src/skills/skill-{slug}
python3 scripts/build.py
python3 -m pytest tests/ -v
```

### Install into Claude Code

```bash
cp -R src/skills/skill-{slug} ~/.claude/skills/
# Then invoke: /skill-{slug}
```

### Use as a module

```python
import sys
sys.path.insert(0, "src/skills/skill-{slug}")
from scripts.build import run

order = run({
    "code": "600036", "pnl_pct": 0.015,
    "sellable_qty": 800, "locked_qty": 0,
    "price": 10.0, "available_cash": 100000, "time": "10:00",
})

orders = run([...])   # Batch: pass a list
```

---

## 📐 Development Rules

### Naming

| Element | Rule | Example |
|---|---|---|
| Directory | `skill-{slug}` | `skill-intraday-position-manager` |
| slug | Chinese name → English, lowercase + hyphens, 3–6 words | `auto-stop-loss-take-profit` |
| `SKILL.md` `name` | Must match the directory name exactly | `skill-intraday-position-manager` |

**Forbidden**: `build-{id}`, `build-B12-*`, `alpha-A00-*`, or any task ID in the directory name.

### Code interface

`scripts/build.py` must provide:

```python
def run(input_data, config=None): ...
def validate_input(input_data): ...   # must raise on missing/empty/invalid input
```

### Publishing rules (QuantSkills community)

Hard requirements enforced by the community audit:

| Rule | Requirement |
|---|---|
| `english-readme` | `README.en.md` must exist; `README.md` stays Chinese-first |
| `license` | `LICENSE` must contain the full GPLv3 text and metadata must declare `GPL-3.0-only` |
| `repository-name` | Lowercase repo name with a `skill-` or `agent-` prefix |
| `runtime-adapter` | `agents/cursor-rule.mdc`, `agents/portable-loader.md`, `agents/openai.yaml` must all exist |

Docs must not contain sensitive information, return guarantees, investment advice, or unconfirmed official endorsements. See `skills/panda-builder/SKILL.md` §8.


A published repo is identical in shape to `public/skills/skill-dl-gnn-stock-graph`:

```
skill-{slug}/                    ← standalone GitHub repo
├── SKILL.md                     ← Root declaration (frontmatter name matches repo name)
├── README.md                    ← Chinese delivery docs (with disclaimer)
├── README.en.md                 ← English delivery docs
├── LICENSE                      ← Full GPL-3.0
├── INSTALL.md                   ← Multi-platform guide (Claude Code/Codex/Cursor/Hermes/OpenClaw)
├── requirements.txt
├── skill.json
├── CHANGELOG.md
├── .gitignore                   ← excludes output/ and other runtime artifacts
├── .github/workflows/validate.yml  ← CI: pytest
├── scripts/
├── tests/
├── references/
├── agents/                      ← runtime adapters (required): cursor-rule.mdc / portable-loader.md / openai.yaml
└── config/                      ← (optional) centralized parameters
```

### Standard order format

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

### A-share trading constraints

- Minimum lot size 100 shares; add/reduce quantities round down to multiples of 100
- Market close 15:00; default force-close window is the last 15 minutes (14:45)
- T+1: positions opened today are locked and cannot be sold the same day

---

## 📄 License

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](./LICENSE)

This project is open-sourced under the GPL-3.0 License. Copyright (C) 2026 QuantSkills.

> All published standalone skill repos also use GPL-3.0, per QuantSkills community rules.