from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {"trade_date", "ts_code", "close", "pre_close"}
BUILD_ID = "B00"
BUILD_NAME = "涨跌幅异常标记"


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
        fields=["close", "pre_close"],
    )
    if raw.empty:
        raise ValueError("Panda data 未返回行情数据")

    quotes = raw.rename(columns={"symbol": "ts_code", "date": "trade_date"})[
        ["trade_date", "ts_code", "close", "pre_close"]
    ]
    quotes["trade_date"] = pd.to_datetime(quotes["trade_date"].astype(str), format="%Y%m%d").dt.strftime("%Y-%m-%d")
    return quotes


def validate_input(input_data: Any) -> pd.DataFrame:
    """Validate and normalize quote data."""
    if input_data is None:
        raise ValueError("input_data 不能为空")

    df = pd.DataFrame(input_data)
    if df.empty:
        raise ValueError("input_data 不能为空表")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"input_data 缺少必要字段: {sorted(missing)}")

    for col in ["close", "pre_close"]:
        df[col] = pd.to_numeric(df[col], errors="raise")

    if (df["pre_close"] <= 0).any():
        raise ValueError("pre_close 必须大于 0")

    return df.copy()


def run(input_data: Any, config: dict | None = None) -> pd.DataFrame:
    config = config or {}
    up_threshold = float(config.get("up_threshold", 0.02))
    down_threshold = float(config.get("down_threshold", -0.02))
    data_version = str(config.get("data_version", "real-v1"))
    update_time = str(config.get("update_time", datetime.now().isoformat(timespec="seconds")))

    df = validate_input(input_data)
    df["change_pct"] = df["close"] / df["pre_close"] - 1

    def flag(change_pct: float) -> str:
        if change_pct >= up_threshold:
            return "up_spike"
        if change_pct <= down_threshold:
            return "down_spike"
        return "normal"

    output = pd.DataFrame(
        {
            "trade_date": df["trade_date"].astype(str),
            "build_id": BUILD_ID,
            "build_name": BUILD_NAME,
            "target_id": df["ts_code"].astype(str),
            "result_type": "price_change_flag",
            "result_value": df["change_pct"].map(flag),
            "result_json": [
                json.dumps(
                    {
                        "change_pct": round(float(change_pct), 6),
                        "up_threshold": up_threshold,
                        "down_threshold": down_threshold,
                    },
                    ensure_ascii=False,
                )
                for change_pct in df["change_pct"]
            ],
            "data_version": data_version,
            "update_time": update_time,
        }
    )
    return output


if __name__ == "__main__":
    print(run(load_real_quotes()).to_string(index=False))
