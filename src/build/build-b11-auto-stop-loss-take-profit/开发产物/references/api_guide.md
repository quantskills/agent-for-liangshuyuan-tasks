# B11 API 接口文档

## 调用入口

```python
from scripts.build import run, validate_input
```

### `run(data)`

- **入参**：`dict`（单条）或 `list[dict]`（批量）
- **返回**：`dict`（单条）或 `list[dict]`（批量）
- **异常**：`ValueError`（校验失败）、`TypeError`（类型错误）

### `validate_input(pos)`

- **入参**：`dict`
- **返回**：`(bool, str)` — (是否通过, 错误信息)

## 输入字段规范

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| code | str | 是 | A股代码 / 期货代码 |
| entry_price | float | 是 | > 0 |
| entry_date | str | 是 | YYYY-MM-DD |
| current_qty | int | 是 | >= 0 |
| open_price | float | 是 | > 0 |
| available_cash | float | 是 | >= 0 |
| today | str | 是 | YYYY-MM-DD |

## 输出字段规范

| 字段 | 类型 | 说明 |
|---|---|---|
| code | str | 品种代码（原样返回） |
| pnl_pct | float | 浮盈亏（小数，0.05 = +5%） |
| current_qty | int | 当前总持仓 |
| time | str | 当前日期 |
| action | str | `"sell"` / `"hold"` |
| qty_change | int | 调仓变化量（负 = 卖出，0 = 不动） |
| target_qty | int | 目标持仓数量 |
| reason | str | 触发原因，格式 `[B11]<规则名> <详情>` |

## reason 前缀说明

| 前缀 | 含义 |
|---|---|
| `[B11]次日止盈` | 次日高开 ≥ +5% |
| `[B11]次日止损` | 次日低开 ≤ -3% |
| `[B11]持仓N日≥2日强制平仓` | 持仓超期 |
| `[B11]单票仓位X%>10%` | 仓位超限 |
| `[B11]hold` | 无触发 |

## 品种识别规则

| 类型 | 匹配规则 | 最小单位 | 示例 |
|---|---|---|---|
| A股 | 6 位纯数字，或 sh/sz 前缀 | 100 | `600036`, `sh600036` |
| 股指期货 | IF/IC/IH/IM + 4 位数字 | 1 | `IF2406` |
| 商品期货 | 字母前缀 + 数字 | 1 | `rb2401`, `cu2401` |
