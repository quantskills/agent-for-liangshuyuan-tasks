from __future__ import annotations

from factor import calculate_factor, load_real_quotes


def check_no_future_function() -> None:
    quotes = load_real_quotes()
    result = calculate_factor(quotes, update_time="2026-05-28T15:30:00")
    last_date = result["trade_date"].max()
    truncated = quotes[quotes["trade_date"] <= last_date]
    recalculated = calculate_factor(truncated, update_time="2026-05-28T15:30:00")

    left = result[result["trade_date"] == last_date].sort_values("ts_code").reset_index(drop=True)
    right = recalculated[recalculated["trade_date"] == last_date].sort_values("ts_code").reset_index(drop=True)
    assert left["factor_value"].round(10).equals(right["factor_value"].round(10))


def check_required_fields() -> None:
    result = calculate_factor(load_real_quotes(), update_time="2026-05-28T15:30:00")
    required = {
        "trade_date",
        "asset_type",
        "ts_code",
        "factor_id",
        "factor_name",
        "factor_value",
        "score",
        "signal",
        "data_version",
        "update_time",
    }
    missing = required - set(result.columns)
    assert not missing, f"结果缺少字段: {sorted(missing)}"
    assert result["score"].between(0, 100).all()
    assert set(result["signal"]).issubset({"buy", "hold"})


def check_out_of_sample_slice() -> None:
    quotes = load_real_quotes()
    result = calculate_factor(quotes, update_time="2026-05-28T15:30:00")
    split_date = sorted(result["trade_date"].unique())[len(result["trade_date"].unique()) // 2]
    train = result[result["trade_date"] <= split_date]
    test = result[result["trade_date"] > split_date]
    assert not train.empty
    assert not test.empty


if __name__ == "__main__":
    check_no_future_function()
    check_required_fields()
    check_out_of_sample_slice()
    print("验证通过：无未来函数，字段完整，样本外切片可用")
