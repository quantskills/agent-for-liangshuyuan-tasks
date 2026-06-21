from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import pandas as pd


FACTOR_ID = "A00"
FACTOR_NAME = "五日动量"
REQUIRED_COLUMNS = {"trade_date", "ts_code", "close"}


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"请先设置环境变量 {name}")
    return value


def load_real_quotes(
    symbols: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> pd.DataFrame:
    import panda_data

    username = _get_env("PANDA_DATA_USERNAME")
    password = _get_env("PANDA_DATA_PASSWORD")
    symbols = symbols or ["000001.SZ", "000002.SZ", "000333.SZ", "600519.SH"]
    start_date = start_date or os.getenv("PANDA_DATA_START_DATE", "2026-05-01")
    end_date = end_date or os.getenv("PANDA_DATA_END_DATE", "2026-05-28")

    panda_data.init_token(username=username, password=password)
    raw = panda_data.get_market_data(
        symbol=symbols,
        start_date=start_date,
        end_date=end_date,
        type="stock",
        fields=["close"],
    )
    if raw.empty:
        raise ValueError("Panda data 未返回行情数据")

    quotes = raw.rename(columns={"symbol": "ts_code", "date": "trade_date"})[
        ["trade_date", "ts_code", "close"]
    ]
    quotes["trade_date"] = pd.to_datetime(quotes["trade_date"].astype(str), format="%Y%m%d").dt.strftime("%Y-%m-%d")
    return quotes


def validate_input(input_data: Any) -> pd.DataFrame:
    df = pd.DataFrame(input_data)
    if df.empty:
        raise ValueError("行情数据不能为空")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"行情数据缺少必要字段: {sorted(missing)}")

    df = df.copy()
    df["trade_date"] = df["trade_date"].astype(str)
    df["ts_code"] = df["ts_code"].astype(str)
    df["close"] = pd.to_numeric(df["close"], errors="raise")
    if (df["close"] <= 0).any():
        raise ValueError("close 必须大于 0")
    return df.sort_values(["ts_code", "trade_date"])


def calculate_factor(input_data: Any, window: int = 5, update_time: str | None = None) -> pd.DataFrame:
    df = validate_input(input_data)
    update_time = update_time or datetime.now().isoformat(timespec="seconds")

    df["factor_value"] = df.groupby("ts_code")["close"].pct_change(periods=window)
    factor = df.dropna(subset=["factor_value"]).copy()
    if factor.empty:
        raise ValueError("历史数据长度不足，无法计算五日动量")

    factor["rank"] = factor.groupby("trade_date")["factor_value"].rank(ascending=False, method="first").astype(int)
    factor["score"] = factor.groupby("trade_date")["factor_value"].rank(pct=True).mul(100).round(2)
    factor["signal"] = factor.groupby("trade_date")["score"].transform(lambda s: s >= s.quantile(0.7))
    factor["signal"] = factor["signal"].map({True: "buy", False: "hold"})
    factor["confidence"] = (factor["score"] / 100).round(4)
    factor["asset_type"] = "stock"
    factor["factor_id"] = FACTOR_ID
    factor["factor_name"] = FACTOR_NAME
    factor["data_version"] = "real-v1"
    factor["update_time"] = update_time

    columns = [
        "trade_date",
        "asset_type",
        "ts_code",
        "factor_id",
        "factor_name",
        "factor_value",
        "score",
        "rank",
        "signal",
        "confidence",
        "data_version",
        "update_time",
    ]
    return factor[columns].sort_values(["trade_date", "rank"]).reset_index(drop=True)


if __name__ == "__main__":
    result = calculate_factor(load_real_quotes(), update_time=datetime.now().isoformat(timespec="seconds"))
    print(result.to_string(index=False))
