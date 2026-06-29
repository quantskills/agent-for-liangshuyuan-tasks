# 🐼 Panda Trading · Quantitative Toolkit

> A modular quantitative trading tool library powered by Claude Code Multi-Agent Collaboration — Pure Python · Zero Framework Dependencies · Skill Architecture

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

---

## 📖 Overview

**Panda Trading (量枢学院)** is a modular quantitative trading development platform that uses an **Atomic Skill** + **Multi-Agent Collaboration** architecture to decompose core trading capabilities into independent, reusable BUILD tools and Alpha factors.

The project is built with the **Python standard library only** — no pandas, numpy, or other third-party dependencies (unless explicitly required by a task), ensuring every Skill is lightweight, self-contained, and freely callable by agents or Alpha signals.

This is an **Agent-type repository** (`agent-for-liangshuyuan-tasks`), compliant with QuantSkills community rules. See `AGENTS.md` for the agent declaration.

### Core Principles

| Principle | Description |
|---|---|
| **Skills are Tools** | Each subdirectory is an independent trading BUILD skill — runnable, testable, and deployable in isolation |
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
| **B** | BUILD Tool | `src/build/` | Data processing, position management, monitoring, review analysis |
| **A** | Alpha Factor | `src/alpha/` | Stock & futures Alpha signals and factors |

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
       │ ←── DevReport (artifacts + self-check)
       ▼
┌─────────────┐
│  Test Agent  │  Generates cases → runs → TestReport
└──────┬──────┘
       │ ←── Pass ✓ / Fail (bugs rebound, max 3 iterations)
       ▼
┌─────────────┐
│ Publish Agent│  Bilingual community notes → GitHub repo (skill- prefix)
│              │  → Git Submodule → push to quantskills org
└──────┬──────┘
       │
       ▼
   ✅ Complete + Published (QuantSkills Community Rules compliant)
```

| Agent | Responsibility | Spec |
|---|---|---|
| **Analyst** | Reads `jobs/*.txt`, outputs TaskSpec | `agents/analyst-agent/SKILL.md` |
| **Build/Alpha Dev** | Codes to TaskSpec, outputs Python Skill | `agents/dev-{build,alpha}-agent/SKILL.md` |
| **Test** | Generates test cases, validates I/O, reports bugs | `agents/test-agent/SKILL.md` |
| **Publish** | Bilingual notes, GitHub repo (skill- prefix), Submodule archive | `agents/publish-agent/SKILL.md` |

---

---

## 📂 Project Structure

```
panda-trading/
├── README.md                       ← Chinese README
├── README.en.md                    ← English README (this file)
├── LICENSE                         ← MIT License
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
│   └── publish-agent/SKILL.md      ←   Publish Agent (QuantSkills-compliant)
│
├── skills/                         ← Local project skills
│   └── panda-builder/
│
├── docs/                           ← Production rule docs
│
├── jobs/                           ← Raw task requirements
│
├── public/                         ← Published archive
│   ├── community/                  ←   Community notes (bilingual)
│   └── skills/                     ←   Published skills (Git Submodule)
│       ├── skill-b11-auto-stop-loss-take-profit/
│       └── skill-b12-intraday-position-manager/
│
└── src/                            ← Development artifacts
    ├── build/
    │   └── build-B12-intraday-position-manager/
    │       └── 开发产物/
    └── alpha/                      ← (reserved)
```

---

## 🚀 Quick Start

### Requirements

- Python 3.8+
- No third-party dependencies (stdlib only)

### Run Published Skills

```bash
# B11 — Auto Stop-Loss / Take-Profit + Position Sizing
cd public/skills/skill-b11-auto-stop-loss-take-profit/scripts
python3 build.py && python3 test.py

# B12 — Intraday Position Manager
cd public/skills/skill-b12-intraday-position-manager/scripts
python3 build.py && python3 test.py
```

### Install to Claude Code

```bash
cp -r public/skills/skill-b12-intraday-position-manager ~/.claude/skills/
# Invoke: /skill-b12-intraday-position-manager
```

---

## 📐 Development Standards

### BUILD Skill Directory Structure (panda-builder)

```
build-{id}-{name}/
├── 开发产物/                     ← Development artifacts
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── build.py               ← run() + validate_input()
│   │   └── test.py
│   ├── references/
│   │   └── api_guide.md
│   └── demo.mp4
└── 生产产物/                      ← Production (result-type only)
    ├── SKILL.md
    └── 数据库.parquet
```

### Publish Standard (QuantSkills Community Rules)

Published skills are transformed into standalone repos:

```
skill-{id}-{name}/                ← GitHub repo (skill- prefix)
├── SKILL.md                       ← Root-level declaration (with metadata block)
├── README.md                      ← Chinese README (with disclaimer)
├── README.en.md                   ← English README
├── LICENSE                        ← GPL-3.0
├── INSTALL.md                     ← Multi-platform guide (Codex/Cursor/Hermes/OpenClaw/Claude Code)
├── requirements.txt
├── scripts/
├── references/
└── production/                    ← (result-type/hybrid only)
```

### Standard Order Format

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

---

## 📄 License

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](./LICENSE)

This project is open-sourced under the GPL-3.0 License. Copyright (C) 2026 QuantSkills.

> Published Skill sub-repos (`skill-b11-*`, `skill-b12-*`) use GPL-3.0, per QuantSkills community rules.
