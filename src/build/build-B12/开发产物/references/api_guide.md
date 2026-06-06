# B12 数据接口说明

## 数据来源

本 BUILD 为**调用型**，不依赖外部数据拉取，由调用方传入标准结构化数据。

## 输入格式

```python
# 单条（dict）
{
    "code":        str,    # 股票代码，如 "600036"
    "pnl_pct":     float,  # 浮盈亏，小数形式（0.01=+1%，-0.005=-0.5%）
    "current_qty": int,    # 当前持仓股数，非负整数
    "time":        str,    # 当前时间 "HH:MM:SS"
}

# 批量（list of dict）
[
    {"code": "600036", "pnl_pct": 0.015, "current_qty": 1000, "time": "10:30:00"},
    ...
]
```

## 输出格式

遵循 `CLAUDE.md §调仓指令数据结构`：

```python
{
    "code":        str,   # 股票代码
    "pnl_pct":     float, # 浮盈亏（原样返回）
    "current_qty": int,   # 当前持仓（原样返回）
    "time":        str,   # 时间（原样返回）
    "action":      str,   # "buy" / "sell" / "hold"
    "qty_change":  int,   # 正数=买入股数，负数=卖出股数，0=不动
    "target_qty":  int,   # 目标持仓股数
    "reason":      str,   # 触发原因说明
}
```

## 调用示例

```python
from scripts.build import run

# 单条
result = run({"code": "600036", "pnl_pct": 0.015, "current_qty": 1000, "time": "10:30:00"})

# 批量
positions = [
    {"code": "600036", "pnl_pct":  0.015, "current_qty": 1000, "time": "10:30:00"},
    {"code": "000001", "pnl_pct": -0.007, "current_qty": 2000, "time": "10:30:00"},
]
results = run(positions)
```

## 约束说明

- `pnl_pct` 使用小数形式，不是百分比整数（1% 传 `0.01`，不是 `1.0`）
- `current_qty` 必须是 100 的整数倍（持仓本身应满足 A 股约束）
- `qty_change` 输出保证是 100 的整数倍
- `available_cash` 字段当前版本**不做**资金约束校验（TODO：加仓时按资金上限压缩）
