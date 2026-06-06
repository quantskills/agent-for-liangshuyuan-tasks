---
name: build-B12
description: 当需要对日内持仓做动态仓位管理时，使用此 skill。根据实时浮盈亏和时间，输出标准调仓指令（加仓/砍半仓/全平/强平/hold）。
tags: [quant, build, development, 仓位管理]
---

# B12 日内仓位动态管理

## 工具定位
- 工具类型：交易执行辅助型
- 解决问题：根据浮盈亏阈值和时间窗口，自动生成标准化调仓指令，避免人工判断延迟
- 使用对象：交易 agent / 人工辅助决策

## 适用场景
- 日内持仓监控，需对每只股票实时判断是否加仓、减仓或持有
- 收盘前统一触发强平

## 决策规则（优先级从高到低）

| 优先级 | 条件 | 动作 |
|---|---|---|
| 1 | 时间 >= 14:45:00 | 强平（全部卖出） |
| 2 | 浮亏 >= 1% | 全平止损 |
| 3 | 浮亏 >= 0.5% | 砍半仓 |
| 4 | 浮盈 > 1% | 加仓 50% |
| 5 | 其他 | hold |

## 输入

| 字段 | 类型 | 说明 |
|---|---|---|
| code | str | 股票代码 |
| pnl_pct | float | 浮盈亏，小数形式（0.01=+1%，-0.005=-0.5%） |
| current_qty | int | 当前持仓股数 |
| time | str | 当前时间，格式 HH:MM:SS |

## 输出

| 字段 | 类型 | 说明 |
|---|---|---|
| code | str | 股票代码 |
| pnl_pct | float | 浮盈亏（原样返回） |
| current_qty | int | 当前持仓 |
| time | str | 时间 |
| action | str | "buy" / "sell" / "hold" |
| qty_change | int | 正=买入股数，负=卖出股数，0=不动 |
| target_qty | int | 目标持仓股数 |
| reason | str | 触发原因说明 |

## 调用方式

```python
from scripts.build import run

# 单条
result = run({"code": "600036", "pnl_pct": 0.015, "current_qty": 1000, "time": "10:30:00"})

# 批量
results = run([
    {"code": "600036", "pnl_pct":  0.015, "current_qty": 1000, "time": "10:30:00"},
    {"code": "000001", "pnl_pct": -0.007, "current_qty": 2000, "time": "10:30:00"},
])
```

## 可被 Alpha 调用
- 是
- 调用限制：Alpha 负责提供 pnl_pct / current_qty，本 BUILD 只做决策不拉数据
- 依赖数据：调用方传入标准结构化数据

## 是否需要生产结果
- 是否生成 `数据库.parquet`：否（调用型，实时返回）

## 依赖
- 调用方传入标准结构化数据
- Python 标准库（math, datetime）

## 已知限制（TODO）
- `available_cash` 字段当前版本不做资金约束，加仓量仅按持仓比例计算
