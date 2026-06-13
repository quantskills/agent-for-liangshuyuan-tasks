---
name: build-B12
description: 当需要对日内多品种持仓做动态仓位管理时，使用此 skill。支持 A股/A股ETF/股指期货/商品期货/港股+ETF；区分 T+1/T+0、昨仓/今仓、保证金/现金，输出标准 8 字段调仓指令。
tags: [quant, build, development, 仓位管理, 多品种]
---

# B12 v2 多品种日内仓位动态管理

## 工具定位
- 工具类型：交易执行辅助型
- 解决问题：根据浮盈亏阈值和时间窗口，按品种规则（T+1/T+0、保证金、合约乘数、可卖部分）自动生成标准化调仓指令
- 使用对象：交易 agent / 人工辅助决策 / Alpha 信号

## 适用场景
- 日内多品种持仓监控，需对每只品种实时判断是否加仓、减仓或持有
- 收盘前按品种各自规则触发强平
- 资金不足时阻断加仓，避免越界报单

## 支持品种

| 类别 | 识别规则 | 结算 | 强平时间 | 单位 |
|---|---|---|---|---|
| A_STOCK | 6 位数字（沪/深主板/科创板/创业板）或 sh/sz 前缀 | T+1 | 14:45 | 100 股 |
| A_ETF | 510xxx / 159xxx / 588xxx 等 | T+1 | 14:45 | 100 股 |
| INDEX_FUTURE | IF/IC/IH/IM + 4 位 | T+0 | 14:45 | 1 手 |
| COMMODITY_FUTURE | rb / cu / m / au / ag / i 等小写前缀 + 数字 | T+0 | 14:45 | 1 手 |
| HK_STOCK | 5 位数字 / HK 前缀 | T+0 | 15:45 | 按表（默认 100） |
| UNKNOWN | 其他 | — | — | 一律 hold |

## 决策规则（优先级从高到低，对所有品种语义一致）

| 优先级 | 条件 | 动作 |
|---|---|---|
| 1 | 时间 >= 品种强平时间 | 强平（按 sellable_qty） |
| 2 | 浮亏 >= 1% | 全平止损（按 sellable_qty） |
| 3 | 浮亏 >= 0.5% | 砍半仓（按 sellable_qty × 0.5） |
| 4 | 浮盈 > 1% | 加仓 50%（按 sellable_qty × 0.5，校验现金/保证金） |
| 5 | 其他 | hold |

`sellable_qty` 计算：
- T+1 品种（A股/A股ETF）：`sellable = sellable_qty`，`locked_qty` 视为今日新建被 T+1 锁定，当日不可卖
- T+0 品种（股指/商品期货/港股）：`sellable = sellable_qty + locked_qty`，BUILD 容错处理（调用方一般传 `locked_qty=0`）

字段语义说明：
- `sellable_qty` — 可卖数量，可能是任何此前交易日建的仓位（不仅限于昨日）
- `locked_qty`   — 锁仓数量，A股/ETF 表示今日 T+1 锁定的部分；T+0 品种应填 0

资金校验：加仓时计算 `_required_cash`（A股/港股用现金+手续费，期货用保证金+手续费），不足时直接 `hold`，**不降级**到部分加仓。

## 输入

| 字段 | 类型 | 说明 |
|---|---|---|
| code | str | 品种代码 |
| pnl_pct | float | 浮盈亏，小数形式（0.01=+1%，-0.005=-0.5%） |
| sellable_qty | int | 可卖数量（>=0），任何此前交易日建的仓位 |
| locked_qty | int | 锁仓数量（>=0），A股/ETF 表示今日 T+1 锁定；T+0 品种填 0 |
| price | float | 现价（>0） |
| available_cash | float | 可用现金/保证金（>=0） |
| time | str | 当前时间，格式 HH:MM |

## 输出

严格遵循 `CLAUDE.md §调仓指令数据结构`，8 字段不增不减：

| 字段 | 类型 | 说明 |
|---|---|---|
| code | str | 品种代码 |
| pnl_pct | float | 浮盈亏（原样返回） |
| current_qty | int | 总持仓 = sellable_qty + locked_qty |
| time | str | 时间 |
| action | str | "buy" / "sell" / "hold" |
| qty_change | int | 正=加仓，负=减仓，0=不动 |
| target_qty | int | 目标持仓 |
| reason | str | 触发原因，含结构化前缀 `[MARKET][sellable=N][cash_req=X]` |

多品种额外信息（market、sellable_qty、cash_req）通过 **reason 字符串前缀**承载，调用方按 api_guide.md 的正则解析协议提取。

## 调用方式

```python
from scripts.build import run

# 单条
result = run({
    "code": "600036", "pnl_pct": 0.015,
    "sellable_qty": 800, "locked_qty": 0,
    "price": 10.0, "available_cash": 100000,
    "time": "10:00",
})

# 批量
results = run([
    {"code": "IF2406", "pnl_pct":  0.015, "sellable_qty":   2, "locked_qty":   0,
     "price": 4000.0, "available_cash": 200000, "time": "10:00"},
    {"code": "00700",  "pnl_pct": -0.007, "sellable_qty": 200, "locked_qty":   0,
     "price":  400.0, "available_cash":      0, "time": "10:00"},
])
```

## 模块结构

```
开发产物/
├── SKILL.md
├── scripts/
│   ├── build.py                # 标准入口 run() / validate_input() / 派发
│   ├── specs.py                # 加载 contract_specs.json
│   ├── classify.py             # 品种识别
│   ├── common.py               # 共享常量、工具、调仓指令构造器
│   ├── markets/
│   │   ├── __init__.py
│   │   ├── a_stock.py          # A股 + A股ETF（T+1）
│   │   ├── index_future.py     # 股指期货（IF/IC/IH/IM）
│   │   ├── commodity_future.py # 商品期货（rb/cu/m/au/ag/i）
│   │   └── hk_stock.py         # 港股+ETF（T+0，覆盖手数）
│   └── test.py
└── references/
    ├── contract_specs.json     # 合约规格中央表
    └── api_guide.md            # 调用协议、reason 解析协议
```

## 可被 Alpha 调用
- 是
- 调用限制：Alpha 负责提供 pnl_pct / yesterday_qty / today_qty / price / available_cash，本 BUILD 只做决策不拉数据
- 依赖数据：调用方传入标准结构化数据

## 是否需要生产结果
- 是否生成 `数据库.parquet`：否（调用型，实时返回）

## 依赖
- 调用方传入标准结构化数据
- Python 标准库（json, os, re, sys）
- 无三方依赖（无 pandas / numpy）

## Changelog

### v2（BREAKING）
- **input schema 变更**：`current_qty` 拆分为 `sellable_qty + locked_qty`（语义=可卖+锁仓，非"昨仓+今仓"），新增 `price` 与 `available_cash`，`time` 由 HH:MM:SS 改为 HH:MM
- **多品种支持**：A股 / A股ETF / 股指期货 / 商品期货 / 港股+ETF
- **T+1/T+0 区分**：A股 14:45 强平时锁仓阻断，仅卖可卖部分
- **资金校验**：加仓时计算所需现金/保证金，不足 → hold（reason 标 `[v2:cash_insufficient]`）
- **调仓基数 = sellable_qty**（T+0 品种为 sellable_qty + locked_qty）
- **强平时间按品种表**：港股 15:45，其他 14:45
- **模块拆分**：build.py 单文件 → 按市场分拆为 markets/*.py

### v1
- 单一 A股、单一 14:45 强平、不区分可卖/锁仓、不校验资金

## Known Limitations（v3 待解决）

1. **仅多头**：不处理空头 / 双向 / 套利 / 跨期组合
2. **不感知涨跌停 / 停牌 / 流动性**：执行失败由调用方回报
3. **不区分集合竞价 / 盘前盘后**：`time >= force_close_time` 一刀切
4. **手续费固定 fee_rate**：不计 A股印花税、过户费、规费档位
5. **港股 lot_size 覆盖表仅 6 支**：未命中按 100 兜底，可能与真实手数不符
6. **不处理多币种**：港股价格按港币、A股按人民币，调用方自行换算
7. **商品期货品种表有限**：仅 rb/cu/m/au/ag/i，扩展需要在 contract_specs.json 中补充
