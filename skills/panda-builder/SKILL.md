---
name: panda-builder
description: 当需要在 panda-trading 项目中创建或验收一个新的 BUILD skill 时，使用此 skill。该 skill 确保目录结构、代码接口、文档格式符合 BUILD 开发规则，并与已过审 skill（skill-dl-gnn-stock-graph）保持同构。
tags: [quant, build, scaffold, development]
---

# Panda Builder — BUILD Skill 脚手架与验收规则

## 工具定位
- 工具类型：开发辅助
- 解决问题：确保每个新 BUILD skill 的目录结构、代码接口、文档模板统一合规
- 使用对象：开发者（Claude Code）

## 触发时机

每次创建新的 BUILD skill 目录或对现有 BUILD 做验收检查时，必须参照本 skill。

---

## 1. 命名规则

| 元素 | 规则 | 示例 |
|---|---|---|
| skill 目录名 | `skill-{slug}` | `skill-intraday-position-manager` |
| `slug` | 中文名称转英文，小写 + 连字符，3–6 词 | `auto-stop-loss-take-profit` |
| `SKILL.md` frontmatter `name` | 与目录名完全一致 | `skill-intraday-position-manager` |
| 任务编号 | 只存在于 `jobs/` 文件名与 TaskSpec 中，**不进入 skill 名** | `jobs/B12 日内仓位动态管理.txt` |

**禁止**：
- 目录名使用 `build-{编号}`、`build-B12-*`、`B12-*` 等带任务编号的形式
- 在 `SKILL.md` 的 `name` 字段里写任务编号

---

## 2. 标准目录结构

每个 BUILD skill 平铺存放，无中间层级（与已过审 skill `public/skills/skill-dl-gnn-stock-graph` 同构）：

```
skill-{slug}/
├── SKILL.md              ← 技能设计书（必填）
├── README.md             ← 中文说明（必填，含免责声明）
├── README.en.md          ← 英文说明（必填）
├── LICENSE               ← GPL-3.0 全文（必填，不可用占位符）
├── INSTALL.md            ← 多平台安装指南（必填）
├── requirements.txt      ← Python 依赖声明（必填）
├── skill.json            ← Skill 元数据（必填）
├── CHANGELOG.md          ← 版本变更记录（必填）
├── scripts/              ← 实现代码
│   └── build.py          ← 主入口，必须提供 run() 与 validate_input()
├── tests/                ← 单元测试
│   ├── test_*.py         ← pytest 用例
│   └── selfcheck.py      ← 可选，无第三方依赖的自测脚本
├── references/           ← 接口与边界文档
│   └── api_guide.md
└── agents/               ← 运行时适配器（社区审核硬性要求）
    ├── cursor-rule.mdc      ← Cursor
    ├── portable-loader.md   ← Hermes / OpenClaw
    └── openai.yaml          ← Codex / OpenClaw
```

运行结果写入 `output/`（必须加入 `.gitignore`），不作为交付目录列出。

可选（按需）：

```
├── config/               ← 集中式参数配置（如 model_config.yaml）
└── .github/workflows/    ← CI（validate.yml：qsh-form 校验 + pytest）
```

**本结构没有 `开发产物/`、`生产产物/` 目录，也没有独立的生产版 `SKILL.md`。**

---

## 3. 标准代码接口

`scripts/build.py` 必须实现以下两个函数：

```python
def run(input_data, config=None):
    """
    Args:
        input_data: 调用方传入的标准结构化数据，或 PandaAI data / 项目指定数据源返回的数据
        config: dict，可选配置
    Returns:
        dict、表格型数据或其他结构化输出
    """

def validate_input(input_data):
    """
    缺字段、空数据、类型错误时必须抛出明确异常。
    """
```

---

## 4. 产出形态

BUILD 只有一种交付形态：**一个自包含的 skill 目录**。区别只在于运行结果落在哪里。

| 形态 | 适用情况 | 运行结果 | 交付 |
|---|---|---|---|
| 调用型 | 轻量、实时、依赖调用方输入 | 直接 `return` 给调用方，不落盘 | 上述完整目录 |
| 结果型 | 重计算、多人复用、定时扫描 | 写入 `output/`（`.gitignore` 排除） | 上述完整目录 + `output/` 说明写入 `SKILL.md` |
| 混合型 | 既能即时调用，也有定时结果 | 两者都有 | 上述完整目录 |

**结果型不得新建 `生产产物/` 目录，也不得新建 `数据库.parquet` 式的第二套 skill。** 结果文件的路径、字段、更新频率写在同一个 `SKILL.md` 的「输出」章节与 `references/` 中即可。

---

## 5. SKILL.md 模板

````markdown
---
name: skill-{slug}
description: 当需要{BUILD功能}时，使用此 skill。{一句话能力说明}。
tags: [quant, build, {工具类型}]
---

# {BUILD名称}

## 适用场景
- 当用户需要{场景1}时
- 当 Alpha 需要{工具能力}时

## 输入
| 字段 | 类型 | 说明 |
|---|---|---|

## 输出
| 字段 | 类型 | 说明 |
|---|---|---|

## 调用方式
```python
from scripts.build import run

result = run(input_data, config=config)
```

## 数据来源
- PandaAI data / 调用方传入标准结构化数据 / 项目指定数据源

## 依赖
- Python 标准库（或列明三方依赖）

## 验收要求
- 可独立运行
- 测试全通过
- 输出字段稳定

## 已知局限
- ...

## 可被 Alpha 调用
- 是 / 否
- 调用限制：
````

---

## 6. skill.json 模板

```json
{
  "name": "skill-{slug}",
  "version": "0.1.0",
  "entrypoint": "SKILL.md",
  "runtime": "python>=3.10",
  "license": "GPL-3.0-only",
  "data_source": "PandaData",
  "entry_script": "scripts/build.py"
}
```

> 许可证字段统一写 **`GPL-3.0-only`**（SPDX 标识），不要写 `GPL-3.0` 或 `GPLv3`。`SKILL.md` 的 metadata 块同样使用 `license: GPL-3.0-only`。

---

## 7. 运行时适配器入口（5 个平台，社区审核硬性要求）

Skill 仓库必须为 Codex / Claude Code / Cursor / Hermes / OpenClaw 提供入口。Claude Code 用根层 `SKILL.md` + `INSTALL.md`，其余四个平台的适配器放在 `agents/`：

| 平台 | 适配器文件（满足其一即可） | 本仓库约定 |
|---|---|---|
| Claude Code | `SKILL.md`（根层） | 必填 |
| Codex (OpenAI) | `agents/openai.yaml` | 必填 |
| Cursor | `agents/cursor-rule.mdc` 或 `.cursor/` | 必填 `agents/cursor-rule.mdc` |
| Hermes | `agents/portable-loader.md` 或 `HERMES.md` | 必填 `agents/portable-loader.md` |
| OpenClaw | `agents/openai.yaml` / `agents/portable-loader.md` / `OPENCLAW.md` | 由 `agents/openai.yaml` + `agents/portable-loader.md` 覆盖 |

`agents/openai.yaml` 最小结构：

```yaml
openapi: 3.1.0
info:
  title: skill-{slug}
  description: {一句话英文能力说明}
  version: 0.1.0

x-skill-info:
  name: skill-{slug}
  type: build        # 或 alpha
  entry: scripts/build.py
  tags: [quant, build]

x-steps:
  - id: main
    script: scripts/build.py
    description: {英文说明}
    auth_required: false
```

`agents/cursor-rule.mdc` 最小结构：

```markdown
---
description: {英文一句话说明}
globs: []
alwaysApply: false
---

# skill-{slug}

{英文能力说明}

## 快速开始
```bash
python3 scripts/build.py
```

## 依赖
- Python 3.10+
```

`agents/portable-loader.md` 最小结构：英文说明 + 目录结构 + Quick Start + Agent Integration（Python 调用示例）+ Tests + Dependencies。

**缺失上述任一适配器**，社区审核会记 `warn:runtime-adapter`，不得进入 registry / 组织首页索引。

### 7.1 版本单源与结构校验脚本（验收必跑）

```bash
# 工作树模式（src 验收）
python3 skills/panda-builder/scripts/validate_skill.py src/skills/skill-{slug}
# git 形态模式（发布工作区，按 HEAD blob 校验）
python3 skills/panda-builder/scripts/validate_skill.py public/skills/skill-{slug} --ref HEAD
```

校验项：八件套 + 三适配器、name 三处一致、**版本单源**（skill.json 为准，
CHANGELOG 当前条目 / agents/openai.yaml 不得漂移）、LICENSE GPL-3.0 全文、
license=GPL-3.0-only、免责声明。**任何 FAIL 即 panda-builder §10 不合格情况，禁止发布。**

**CHANGELOG 条目约定（版本单源的前提）**：第一个**带方括号**条目必须是当前版本号；
未发布改动使用无方括号的 `## Unreleased`。历史遗留的 `## [Unreleased]` 带括号写法会劫持
当前条目判定，须在下次发布时一并规范化（如 jev / constraint-stress-test 的 HEAD 现状）。

---

## 8. 社区审核规则（收录 / 公开前置条件）

以下规则来自 QuantSkills 社区审核器实际输出，**任一 `fail` 项存在时不得申请公开、收录、恢复 public 或进入 registry / quantskills / 组织首页索引**。

### 8.1 硬性 fail 项

| 规则 | 要求 | 建议动作 |
|---|---|---|
| `english-readme` | 仓库必须有 `README.en.md`，同时 `README.md` 保持中文优先 | 补英文 README，不要用中文 README 顶替 |
| `license` | 仓库必须有 `LICENSE` 文件，为 **GPLv3 全文**，且元数据声明 `GPL-3.0-only` | 补 `LICENSE`，`skill.json` / `SKILL.md` metadata 改为 `GPL-3.0-only` |
| `repository-name` | 仓库名小写，`skill-` 或 `agent-` 前缀 | `skill-{slug}`，全小写连字符 |

### 8.2 运行时适配器 warn 项

| 规则 | 缺失时补 |
|---|---|
| `warn:runtime-adapter` (Cursor) | `agents/cursor-rule.mdc` 或 `.cursor/` |
| `warn:runtime-adapter` (Hermes) | `agents/portable-loader.md` 或 `HERMES.md` |
| `warn:runtime-adapter` (OpenClaw) | `agents/openai.yaml` / `agents/portable-loader.md` / `OPENCLAW.md` |

### 8.3 内容禁令（说明文档中一律不得出现）

| 禁令 | 说明 |
|---|---|
| 敏感信息 | 账号、密码、Token、内网地址、真实资金规模、个人联系方式以外的隐私信息 |
| 收益承诺 | 「稳赚」「必涨」「年化 X% 保证」「无风险」等表述 |
| 投资建议 | 任何形式的买卖建议、荐股、仓位推荐 |
| 未经确认的官方背书 | 不得声称获得监管机构、交易所、券商或 QuantSkills 官方认证；只能写「社区项目，未经专业审计」 |

**必须出现的免责声明段落**（`README.md` / `README.en.md` 各一份）：

- 仅供研究与教育用途，不构成投资建议
- 不保证收益
- 风险边界说明
- QuantSkills 社区项目，非官方背书

### 8.4 审核自查命令

发布前逐项确认：

```bash
cd public/skills/skill-{slug}
test -f README.md && test -f README.en.md || echo "FAIL english-readme"
head -1 LICENSE | grep -q "GNU GENERAL PUBLIC LICENSE" || echo "FAIL license"
grep -q '"license": "GPL-3.0-only"' skill.json || echo "FAIL license-metadata"
test -f agents/cursor-rule.mdc || echo "WARN cursor-adapter"
test -f agents/portable-loader.md || echo "WARN hermes/openclaw-adapter"
test -f agents/openai.yaml || echo "WARN openclaw/codex-adapter"
# 注意：只匹配肯定式承诺。「不保证收益」「未经官方认证」等免责声明不算违规，
# 因此先按行匹配，再剔除含否定词的整行。
grep -rnE "(稳赚|必涨|保证(收益|盈利|回报)|无风险|荐股|官方认证)" README.md README.en.md SKILL.md \
  | grep -vE "(不保证|无法保证|不构成|不提供|无需|未经)" \
  && echo "FAIL forbidden-claims" || true
```

### 8.5 评测类 skill 附加约束

适用于对模型、Agent 或交易系统做评测 / 回放 / 压测的 skill（如 `skill-constraint-stress-test`）。普通工具型 skill 不适用。

| 约束 | 要求 |
|---|---|
| **范围边界** | 评测必须基于合成数据、历史数据或本地 fixture 回放，全程不得连接实盘账户、真实交易网关或生产委托通道。**禁止为了触发某个测试场景而真实下单**。fixture 只读，`trader_fn` 只返回决策 dict，返回结果不得被执行。 |
| **预算固定** | 跨模型比较必须固定 fixture 集、注入类型、案例数、判定阈值、温度与 token/时间预算。这些字段必须计入 `config_hash`，报告须输出该哈希，使「同条件可比」可被外部验证。 |
| **模型不混算** | 不同模型（例如 JEV 专用模型与 Flash）的评测结果**不得合并为同一指标**，也不得混作同一评审模型。依赖表须按模型单列，报告须按模型分组输出。 |

**依赖表写法**（`skill.json` 中的 `evaluation` 段）：

```json
{
  "evaluation": {
    "mode": "replay-only",
    "live_trading_access": false,
    "models_under_test": [
      { "id": "jev-dedicated", "role": "subject", "budget": { "tokens": 0, "timeout_s": 0 } },
      { "id": "flash", "role": "subject", "budget": { "tokens": 0, "timeout_s": 0 } }
    ],
    "group_by": "model_id"
  }
}
```

> `models_under_test` 中每个模型单独一行，`role` 区分 `subject`（被评测）与 `judge`（评审）。不同模型的指标分别统计，不做加权合并。

#### 价值验收产出（评测类必填）

评测类 skill 的报告必须能回答「改变了什么、作用多大、在什么边界下成立」，否则不构成有效交付。

| 产出 | 要求 |
|---|---|
| **改变了什么决策** | 聚合被改写/被拦下的决策数量、动作迁移（如 `buy→hold`）、按故障类型拆分、被避免的后果 |
| **作用多大** | 效应量（ARR / RRR / NNT）+ 置信区间 + 显著性检验 |
| **结论判定** | `verdict` 三值：`positive`（显著改善）/ `negative`（基线有问题但无改善）/ `inconclusive`（基线无问题或样本不足） |
| **适用边界** | 覆盖哪些约束、在什么范围内、哪些不在范围内、何种条件下结论失效 |
| **冻结基线** | 支持把一次运行结果持久化，供后续 run 做跨运行比对；`config_hash` 不一致时必须标记不可比 |

**负结果同样构成有效交付**：`verdict=negative` 只要满足①`config_hash` 可比 ②样本量足够，即可作为结论引用，不因「没改善」而判为不合格。

**判定规则必须可复现**，不得依赖主观判断。例如：

```python
if arr > 0 and mcnemar_p < 0.05:
    verdict = "positive"
elif baseline_has_violations and arr <= 0:
    verdict = "negative"
else:
    verdict = "inconclusive"
```

**桩件不得判 positive**：若被测系统是占位桩件（固定返回同一决策），基线必然无违规，必须判 `inconclusive` 并说明「仅证明链路可运行」。

---

## 9. 验收检查清单

完成开发后逐项确认：

- [ ] 目录名符合 `skill-{slug}`，全小写，不含任务编号
- [ ] `SKILL.md` frontmatter `name` 与目录名一致
- [ ] `SKILL.md / README.md / README.en.md / LICENSE / INSTALL.md / requirements.txt / skill.json / CHANGELOG.md` 八件套齐全
- [ ] 无 `开发产物/`、`生产产物/` 目录
- [ ] `LICENSE` 为完整 GPL-3.0 文本
- [ ] `skill.json` 与 `SKILL.md` metadata 的 license 为 `GPL-3.0-only`
- [ ] `README.md` 含 `## ⚠️ 免责声明`，`README.en.md` 含对应 Disclaimer
- [ ] `INSTALL.md` 覆盖 Claude Code / Codex / Cursor / Hermes / OpenClaw
- [ ] `agents/cursor-rule.mdc`、`agents/portable-loader.md`、`agents/openai.yaml` 三个适配器齐全
- [ ] 说明文档无敏感信息、收益承诺、投资建议、未经确认的官方背书
- [ ] `python3 scripts/build.py` 可独立跑通
- [ ] 提供标准 `run(input_data, config=None)` 入口
- [ ] `validate_input()` 对缺字段、空数据、非法类型抛出明确异常
- [ ] `tests/` 覆盖正常输入、边界值、异常输入
- [ ] `references/api_guide.md` 说明数据接口、字段、调用示例
- [ ] 输出字段、类型、含义固定
- [ ] 数据来源为 **agent 经 PandaData MCP 取回并落盘**的结果，或调用方传入的标准结构化数据（运行环境与数据通道一律属于 QuantStudio 宿主；文档、注释、依赖声明与 `skill.json` 的 `data_source` 都不得再描述任何取数客户端）
- [ ] `SKILL.md` 首节为 `## 前置检查`，排在所有 `python3 scripts/` 与代码块**之前**，并有 `tests/test_preflight.py` 反向守卫；阻塞语义**分两条线路**：需要新取数时 MCP 会话 / 权限探针 / 截断处理是阻塞项，既有夹具的离线评测不因 MCP 缺失而阻塞，但必须标注数据来源与落盘日期
- [ ] 文档里的用例总数、自检项数、关键指标与版本号有「以实测为唯一真相」的对账守卫（`pytest --collect-only` 与实跑输出），不靠人工回忆维护
- [ ] 解释器下限在 `skill.json` / `env_check.py` / `SKILL.md` / CI 矩阵**四处一致**，且支持范围只等于被验证过的范围（能 import ≠ 受支持）
- [ ] （评测类）仅基于本地 fixture / 历史数据回放，不连接实盘账户或真实委托通道
- [ ] （评测类）跨模型比较的预算与配置字段已计入 `config_hash`
- [ ] （评测类）不同模型的结果未合并统计，`skill.json` 的 `evaluation.models_under_test` 已按模型单列
- [ ] （评测类）报告含 `value_assessment`：决策改变、效应量、`verdict`
- [ ] （评测类）报告含 `applicability`：覆盖范围、不在范围、结论失效情形
- [ ] （评测类）`verdict` 判定规则可复现；桩件基线不得判 `positive`
- [ ] （评测类）支持冻结基线，`config_hash` 不一致时明确标记不可比

---

## 10. 不合格情况（禁止验收上线 / 禁止申请公开）

- 目录名带 `build-{编号}` 或任务编号前缀，或仓库名不是全小写 `skill-` / `agent-` 前缀
- 存在 `开发产物/` 或 `生产产物/` 目录
- 缺少八件套中任一文件
- 缺少 `README.en.md`（`fail:english-readme`）
- 缺少 `LICENSE`，或不是完整 GPLv3 文本（`fail:license`）
- 元数据 license 不是 `GPL-3.0-only`（`fail:license`）
- 缺少任一运行时适配器：`agents/cursor-rule.mdc` / `agents/portable-loader.md` / `agents/openai.yaml`
- 说明文档包含敏感信息、收益承诺、投资建议或未经确认的官方背书
- 缺少 `SKILL.md` 或 frontmatter `name` 与目录名不一致
- 没有标准 `run()` 入口
- 未使用规定数据源，且未咨询项目工作人员
- 缺 `## 前置检查` 小节、该小节排在可执行流程之后，或没有对应的反向守卫测试
- 文档数字与实测不符（用例数、覆盖率、p 值、版本），或用过松的容差把声称值失真判成「已核验」
- 四处解释器下限不一致，或把未跑过验收套件的解释器写成受支持环境
- 输入输出字段不稳定
- 无 `tests/` 或无通过记录
- 声称可被 Alpha 调用但无法 import
- `README.md` 缺少免责声明
- （评测类）连接实盘账户或真实委托通道，或为触发测试场景真实下单
- （评测类）跨模型比较未固定预算与配置，或不同模型结果合并为同一指标
- （评测类）报告缺少 `value_assessment` / `applicability`，或 `verdict` 判定不可复现
- （评测类）用桩件基线判 `positive`，或跨 run 比对未校验 `config_hash` 一致性

存在上述任一情况，**不得申请公开、收录、恢复 public 或进入 registry / quantskills / 组织首页索引**。