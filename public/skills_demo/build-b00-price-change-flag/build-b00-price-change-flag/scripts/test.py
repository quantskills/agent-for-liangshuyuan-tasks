from __future__ import annotations

from build import load_real_quotes, run


def test_normal_input() -> None:
    data = [
        {"trade_date": "2026-05-28", "ts_code": "000001.SZ", "close": 10.8, "pre_close": 10.0},
        {"trade_date": "2026-05-28", "ts_code": "000002.SZ", "close": 9.2, "pre_close": 10.0},
        {"trade_date": "2026-05-28", "ts_code": "000003.SZ", "close": 10.2, "pre_close": 10.0},
    ]
    result = run(data, config={"up_threshold": 0.07, "down_threshold": -0.07})
    assert list(result["result_value"]) == ["up_spike", "down_spike", "normal"]
    assert set(result["result_type"]) == {"price_change_flag"}


def test_empty_input() -> None:
    try:
        run([])
    except ValueError as exc:
        assert "不能为空表" in str(exc)
        return
    raise AssertionError("空数据必须抛出 ValueError")


def test_missing_column() -> None:
    try:
        run([{"trade_date": "2026-05-28", "ts_code": "000001.SZ", "close": 10.8}])
    except ValueError as exc:
        assert "缺少必要字段" in str(exc)
        return
    raise AssertionError("缺字段必须抛出 ValueError")


if __name__ == "__main__":
    test_normal_input()
    test_empty_input()
    test_missing_column()
    real_data = load_real_quotes()
    assert not run(real_data).empty
    print("全部测试通过")
