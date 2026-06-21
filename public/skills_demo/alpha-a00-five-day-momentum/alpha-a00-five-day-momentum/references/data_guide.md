# 数据源与字段说明

## 数据来源

本示例使用 Panda data SDK 拉取真实日频股票行情数据。

正式 Alpha 开发必须使用 PandaAI data 数据拉取库或项目明确指定的数据源。不得使用来源不明、字段不稳定、个人临时整理的数据文件作为正式输入。

## 环境变量

运行前设置：

```bash
set PANDA_DATA_USERNAME=你的账号
set PANDA_DATA_PASSWORD=你的密码
```

`panda-data` 要求 Python 3.10 以上。当前录屏环境可使用 Codex 自带 Python 3.12。

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

## 因子计算

```text
factor_value = close(t) / close(t-5) - 1
```

本因子只使用当前交易日及之前的收盘价，不使用未来行情、未来公告或未来财务数据。

## 清洗规则

- `close` 必须大于 0。
- 历史长度不足 5 个交易日的股票不输出因子。
- 当日横截面内进行排名和标准化打分。

## 正式接入提醒

正式任务中如果出现复权方式、停牌处理、交易日历、股票池范围不明确的情况，必须先咨询项目工作人员，再进入开发。
