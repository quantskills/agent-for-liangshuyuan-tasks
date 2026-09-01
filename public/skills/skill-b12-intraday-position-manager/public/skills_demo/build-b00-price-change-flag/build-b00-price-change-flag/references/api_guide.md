# 数据接口与字段说明

## 数据来源

本示例使用 Panda data SDK 拉取真实日频股票行情数据，并转换为调用方传入的标准结构化行情数据。

正式生产时，行情数据应来自 PandaAI data 数据拉取库或项目指定数据源。不得使用来源不明、字段不稳定、手工整理的临时表作为正式输入。

## 环境变量

运行前设置：

```bash
set PANDA_DATA_USERNAME=你的账号
set PANDA_DATA_PASSWORD=你的密码
```

可选参数：

```bash
set PANDA_DATA_START_DATE=2026-05-01
set PANDA_DATA_END_DATE=2026-05-28
```

## 字段口径

| 字段 | 口径 |
|---|---|
| trade_date | 由 Panda data `date` 字段转换，格式为 `YYYY-MM-DD` |
| ts_code | 由 Panda data `symbol` 字段转换，使用标准交易所后缀 |
| close | Panda data 日频收盘价 |
| pre_close | Panda data 前收盘价，必须大于 0 |

## 计算口径

```text
change_pct = close / pre_close - 1
```

默认阈值：

- `change_pct >= 0.02` 标记为 `up_spike`
- `change_pct <= -0.02` 标记为 `down_spike`
- 其他情况标记为 `normal`

## 异常处理

- 输入为空：抛出明确异常。
- 缺少必要字段：抛出明确异常并列出缺失字段。
- `pre_close <= 0`：抛出明确异常。
- 数值字段无法转为数字：由 pandas 抛出类型错误。
