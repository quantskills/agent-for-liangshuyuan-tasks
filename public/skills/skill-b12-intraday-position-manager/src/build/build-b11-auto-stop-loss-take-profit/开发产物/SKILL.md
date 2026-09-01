---
name: build-B11-auto-stop-loss-take-profit
description: 当需要对 A 股和期货持仓做自动止盈止损与仓位管理时，使用此 skill。支持次日高开止盈、次日低开止损、持仓超期强平、单票仓位上限控制。
tags: [quant, build, 止盈止损, 仓位管理, A股, 期货]
---

# B11 自动止盈止损+仓位管理

## 工具定位
- 工具类型：交易执行辅助型（调用型 BUILD）
- 解决问题：按入场日期和开盘价自动判断止盈、止损、强平，以及单票仓位上限控制
- 使用对象：交易 agent / 人工辅助决策 / Alpha 信号

## 适用场景
- 每日开盘后检查持仓是否需要止盈/止损
- 持仓超期自动平仓（含入场日 2 日）
- 单票仓位超限自动减仓

## 支持品种

| 类别 | 识别规则 | 最小交易单位 |
|---|---|---|
| A_STOCK | 6 位数字，或 sh/sz 前缀 | 100 股 |
| INDEX_FUTURE | IF/IC/IH/IM + 4 位数字 | 1 手 |
| COMMODITY_FUTURE | 小写字母前缀 + 数字（如 rb2401） | 1 手 |

## 决策规则（优先级从高到低）

| 优先级 | 条件 | 动作 |
|---|---|---|
| 1 | 次日（today = entry_date + 1）高开 ≥ 5% | 止盈全平 |
| 2 | 次日低开 ≤ -3% | 止损全平 |
| 3 | 持仓 ≥ 2 日（含入场日） | 强制平仓 |
| 4 | 单票仓位 > 总资金 10% | 减仓至 10% |
| 5 | 其他 | hold |

- 持仓天数 = today - entry_date + 1（含入场日，入场当日 = 第 1 日）
- 盈亏比例 = (open_price - entry_price) / entry_price
- 所有数量向下取整到品种最小交易单位

## 输入

| 字段 | 类型 | 说明 |
|---|---|---|
| code | str | 品种代码 |
| entry_price | float | 入场价（>0） |
| entry_date | str | 入场日期 YYYY-MM-DD |
| current_qty | int | 当前持仓数量（>=0） |
| open_price | float | 当日开盘价（>0） |
| available_cash | float | 可用资金（>=0） |
| today | str | 当前日期 YYYY-MM-DD |

## 输出

标准 8 字段调仓指令：

| 字段 | 类型 | 说明 |
|---|---|---|
| code | str | 品种代码 |
| pnl_pct | float | 浮盈亏（小数形式） |
| current_qty | int | 当前总持仓 |
| time | str | 当前日期 |
| action | str | "sell" / "hold" |
| qty_change | int | 负 = 减仓，0 = 不动 |
| target_qty | int | 目标持仓 |
| reason | str | 触发原因，含 `[B11]` 前缀 |

## 调用方式

```python
from scripts.build import run

# 单条
result = run({
    "code": "600036", "entry_price": 10.0,
    "entry_date": "2026-06-19", "current_qty": 800,
    "open_price": 10.55, "available_cash": 100000,
    "today": "2026-06-20",
})

# 批量
results = run([pos1, pos2, pos3])
```

## 依赖
- Python 标准库（json, os, re, sys, datetime）
- 无三方依赖

## Known Limitations
1. 不区分涨停/跌停/停牌状态
2. 日期按自然日计算（非交易日可能在非交易环境触发误判）
3. 仅支持多头持仓
4. 不处理多币种
