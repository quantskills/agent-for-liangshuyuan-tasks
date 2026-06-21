#!/usr/bin/env python3
"""B11 自测脚本"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from build import run, validate_input, manage_position

PASS, FAIL = 0, 0

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"✅ {name}")
    except AssertionError as e:
        FAIL += 1
        print(f"❌ {name}: {e}")
    except Exception as e:
        FAIL += 1
        print(f"💥 {name}: {e}")

# ---- 校验层 ----
def test_validate_ok():
    ok, err = validate_input({
        "code": "600036", "entry_price": 10.0, "entry_date": "2026-06-19",
        "current_qty": 800, "open_price": 10.5, "available_cash": 100000,
        "today": "2026-06-20",
    })
    assert ok, err

def test_validate_missing_field():
    ok, err = validate_input({"code": "600036"})
    assert not ok

def test_validate_bad_price():
    ok, err = validate_input({
        "code": "600036", "entry_price": -1.0, "entry_date": "2026-06-19",
        "current_qty": 800, "open_price": 10.5, "available_cash": 100000,
        "today": "2026-06-20",
    })
    assert not ok

def test_validate_bad_date():
    ok, err = validate_input({
        "code": "600036", "entry_price": 10.0, "entry_date": "bad",
        "current_qty": 800, "open_price": 10.5, "available_cash": 100000,
        "today": "2026-06-20",
    })
    assert not ok

# ---- 次日止盈 ----
def test_next_day_take_profit():
    r = run({
        "code": "600036", "entry_price": 10.0, "entry_date": "2026-06-19",
        "current_qty": 800, "open_price": 10.55, "available_cash": 100000,
        "today": "2026-06-20",
    })
    assert r["action"] == "sell", f"expected sell, got {r['action']}"
    assert r["target_qty"] == 0, f"expected 0, got {r['target_qty']}"
    assert "止盈" in r["reason"]

# ---- 次日止损 ----
def test_next_day_stop_loss():
    r = run({
        "code": "600036", "entry_price": 10.0, "entry_date": "2026-06-19",
        "current_qty": 800, "open_price": 9.65, "available_cash": 100000,
        "today": "2026-06-20",
    })
    assert r["action"] == "sell"
    assert r["target_qty"] == 0
    assert "止损" in r["reason"]

# ---- 持仓2日强平（含入场日） ----
def test_force_close_2_days():
    r = run({
        "code": "600036", "entry_price": 10.0, "entry_date": "2026-06-19",
        "current_qty": 800, "open_price": 10.1, "available_cash": 100000,
        "today": "2026-06-20",  # 19=day1, 20=day2 → 强平
    })
    assert r["action"] == "sell"
    assert "强平" in r["reason"] or "强制平仓" in r["reason"]

# ---- 止盈优先级高于强平 ----
def test_stop_profit_before_force_close():
    """次日同时满足止盈和强平时，止盈优先"""
    r = run({
        "code": "600036", "entry_price": 10.0, "entry_date": "2026-06-19",
        "current_qty": 800, "open_price": 10.55, "available_cash": 100000,
        "today": "2026-06-20",  # 次日 + 浮盈 = 止盈，非强平
    })
    assert r["action"] == "sell"
    assert "止盈" in r["reason"]

# ---- hlod ----
def test_hold():
    r = run({
        "code": "600036", "entry_price": 10.0, "entry_date": "2026-06-20",
        "current_qty": 800, "open_price": 10.1, "available_cash": 100000,
        "today": "2026-06-20",  # 入场当天，无触发
    })
    assert r["action"] == "hold"

# ---- 单票 > 10% ----
def test_single_over_10pct():
    r = run({
        "code": "600036", "entry_price": 10.0, "entry_date": "2026-06-20",
        "current_qty": 2000, "open_price": 10.0, "available_cash": 100000,
        "today": "2026-06-20",  # pos=20000 > 10000(10%)
    })
    assert r["action"] == "sell"
    assert r["target_qty"] == 1000  # 10000/10=1000, floor to 100

# ---- 期货次日止盈 ----
def test_future_take_profit():
    r = run({
        "code": "IF2406", "entry_price": 4000.0, "entry_date": "2026-06-19",
        "current_qty": 2, "open_price": 4220.0, "available_cash": 200000,
        "today": "2026-06-20",
    })
    assert r["action"] == "sell"
    assert r["target_qty"] == 0
    assert "止盈" in r["reason"]

# ---- 期货单票 > 10% ----
def test_future_over_10pct():
    r = run({
        "code": "rb2401", "entry_price": 3500.0, "entry_date": "2026-06-20",
        "current_qty": 10, "open_price": 3500.0, "available_cash": 100000,
        "today": "2026-06-20",  # pos=35000 > 10000(10%)
    })
    assert r["action"] == "sell"
    assert 0 < r["target_qty"] < 10

# ---- 批量调用 ----
def test_batch():
    results = run([
        {"code": "600036", "entry_price": 10.0, "entry_date": "2026-06-19",
         "current_qty": 800, "open_price": 10.55, "available_cash": 100000, "today": "2026-06-20"},
        {"code": "000001", "entry_price": 15.0, "entry_date": "2026-06-20",
         "current_qty": 200, "open_price": 15.0, "available_cash": 50000, "today": "2026-06-20"},
    ])
    assert len(results) == 2
    assert results[0]["action"] == "sell"  # 止盈
    assert results[1]["action"] == "hold"  # 入场当天，仓位 6% 未触发

# ---- 边界：恰好 +5% ----
def test_boundary_5pct():
    r = run({
        "code": "600036", "entry_price": 10.0, "entry_date": "2026-06-19",
        "current_qty": 800, "open_price": 10.50, "available_cash": 100000,
        "today": "2026-06-20",
    })
    assert r["action"] == "sell"  # >= 5%

# ---- 边界：恰好 -3% ----
def test_boundary_3pct():
    r = run({
        "code": "600036", "entry_price": 10.0, "entry_date": "2026-06-19",
        "current_qty": 800, "open_price": 9.70, "available_cash": 100000,
        "today": "2026-06-20",
    })
    assert r["action"] == "sell"  # <= -3%

# ---- 空列表 ----
def test_empty_list():
    r = run([])
    assert r == []


if __name__ == "__main__":
    test("校验通过", test_validate_ok)
    test("校验缺字段", test_validate_missing_field)
    test("校验价格异常", test_validate_bad_price)
    test("校验日期异常", test_validate_bad_date)
    test("次日止盈", test_next_day_take_profit)
    test("次日止损", test_next_day_stop_loss)
    test("持仓2日强平", test_force_close_2_days)
    test("止盈优先于强平", test_stop_profit_before_force_close)
    test("hold", test_hold)
    test("单票>10%减仓", test_single_over_10pct)
    test("期货止盈", test_future_take_profit)
    test("期货>10%减仓", test_future_over_10pct)
    test("批量调用", test_batch)
    test("边界+5%", test_boundary_5pct)
    test("边界-3%", test_boundary_3pct)
    test("空列表", test_empty_list)

    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(0 if FAIL == 0 else 1)
