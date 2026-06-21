# B12 v2 数据接口说明

## 数据来源

本 BUILD 为**调用型**，不依赖外部数据拉取，由调用方传入标准结构化数据。

## 输入格式

```python
# 单条（dict）
{
    "code":           str,    # 品种代码（A股/ETF/期货/港股）
    "pnl_pct":        float,  # 浮盈亏，小数形式（0.01=+1%）
    "sellable_qty":   int,    # 可卖数量（>=0），任何此前交易日建的仓位
    "locked_qty":     int,    # 锁仓数量（>=0），A股/ETF 表示今日 T+1 锁定；T+0 品种填 0
    "price":          float,  # 现价，正数
    "available_cash": float,  # 可用现金/保证金，非负数
    "time":           str,    # 当前时间 "HH:MM"
}

# 批量（list of dict）
[
    {"code": "IF2406", "pnl_pct":  0.015, "sellable_qty": 2, "locked_qty": 0,
     "price": 4000.0,  "available_cash": 200000, "time": "10:00"},
    ...
]
```

## 输出格式

严格遵循 `CLAUDE.md §调仓指令数据结构`，8 字段：

```python
{
    "code":        str,    # 品种代码
    "pnl_pct":     float,  # 浮盈亏（原样返回）
    "current_qty": int,    # 总持仓 = sellable_qty + locked_qty
    "time":        str,    # 时间（原样返回）
    "action":      str,    # "buy" / "sell" / "hold"
    "qty_change":  int,    # 正=加仓，负=减仓，0=不动
    "target_qty":  int,    # 目标持仓
    "reason":      str,    # 触发原因（含结构化前缀，见下）
}
```

## reason 结构化协议

为不破坏 8 字段契约，多品种附加信息（市场、可卖、所需资金）放进 `reason` 字符串的前缀：

```
[<MARKET>][sellable=<N>][cash_req=<X>] <动作描述>[（注释）][标签]
```

调用方用正则提取：

```python
import re
m = re.match(
    r"^\[([A-Z_]+)\]\[sellable=(\d+)\]\[cash_req=([\d.]+)\]",
    order["reason"],
)
market   = m.group(1)
sellable = int(m.group(2))
cash_req = float(m.group(3))
```

特殊标签：
- `[v2:cash_insufficient]` — 加仓所需资金/保证金不足，已降级为 hold
- `（T+1 阻断 N 股）` — A股强平/全平时锁仓不可卖

### 实例

| 输入特征 | reason 形态 |
|---|---|
| A股加仓 400 股，需 4002.0 现金 | `[A_STOCK][sellable=800][cash_req=4002.00] 浮盈 1.50% 加仓 400 股` |
| A股 14:45 强平，含锁仓 200 | `[A_STOCK][sellable=300][cash_req=0.00] 14:45 强平 平 300 股（T+1 阻断 200 股）` |
| A股资金不足 | `[A_STOCK][sellable=500][cash_req=51250.00][v2:cash_insufficient] 浮盈 1.50% 加仓 500 股需 51250.00 现金 1000.00 不足 hold` |
| IF 加仓 1 手 | `[INDEX_FUTURE][sellable=2][cash_req=144096.00] 浮盈 1.50% 加仓 1 手` |
| 港股 15:45 强平 | `[HK_STOCK][sellable=100][cash_req=0.00] 15:45 强平 平 100 股` |
| UNKNOWN | `[UNKNOWN][sellable=0][cash_req=0.00] 未识别品种 hold` |

## 品种识别规则

| 输入示例 | 识别为 | 备注 |
|---|---|---|
| 600036 / 000001 / 300750 / 688981 | A_STOCK | 6 位数字按号段判 |
| 510300 / 159919 / 588000 | A_ETF | 6 位数字按 ETF 号段判 |
| sh600036 / sz000001 | A_STOCK | 剥离前缀后按 6 位判 |
| IF2406 / IC2406 / IH2406 / IM2406 | INDEX_FUTURE | 必须 4 位 |
| rb2410 / cu2406 / au2412 | COMMODITY_FUTURE | 小写字母 + 数字，需命中规格表白名单 |
| 00700 / 02800 / 09988 | HK_STOCK | 5 位数字 |
| HK00700 | HK_STOCK | 带 HK 前缀 |
| ABCD / 123 / FOO | UNKNOWN | 一律 hold |

## 调用示例

```python
from scripts.build import run

# 多品种批量
positions = [
    {"code": "600036", "pnl_pct":  0.015, "sellable_qty":  800, "locked_qty":   0,
     "price": 10.0,    "available_cash": 100000, "time": "10:00"},  # A股加仓
    {"code": "300750", "pnl_pct": -0.012, "sellable_qty":  600, "locked_qty": 400,
     "price": 100.0,   "available_cash":      0, "time": "13:00"},  # A股全平 T+1 阻断
    {"code": "IF2406", "pnl_pct":  0.015, "sellable_qty":    2, "locked_qty":   0,
     "price": 4000.0,  "available_cash": 200000, "time": "10:00"},  # IF 加仓
    {"code":  "00700", "pnl_pct": -0.007, "sellable_qty":  200, "locked_qty":   0,
     "price": 400.0,   "available_cash":      0, "time": "10:00"},  # 港股砍半 T+0
]
for order in run(positions):
    print(order)
```

## 约束说明

- `pnl_pct` 使用小数形式，不是百分比整数（1% 传 `0.01`）
- `time` 必须是 `HH:MM` 格式（v2 不再接受 `HH:MM:SS`）
- 持仓数据由调用方提供 `sellable_qty + locked_qty`（可卖 + 锁仓），BUILD 不维护持仓状态
- 资金占用近似计算（A股/港股=现金+手续费，期货=保证金+手续费）；不计印花税、过户费等细项
- v2 仅支持多头持仓；空头/双向 v3 处理

## 异常

| 异常 | 触发条件 |
|---|---|
| `TypeError` | input_data 非 dict 或 list；item 非 dict；code 非字符串；pnl_pct 非数值 |
| `KeyError`  | item 缺 7 个必填字段中的任一 |
| `ValueError` | 空列表；qty 为负；price <= 0；available_cash < 0；time 格式错；code 为空 |
