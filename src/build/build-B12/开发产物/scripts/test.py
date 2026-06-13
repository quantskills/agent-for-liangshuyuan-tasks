"""
B12 v2 测试脚本

覆盖维度：
  1. 4 品种 × 5 优先级（强平/全平/砍半/加仓/hold）
  2. T+1 边界（A股 14:45 强平时今仓阻断）
  3. 资金不足 → hold
  4. UNKNOWN 兜底
  5. 异常输入：缺字段、负数、空列表、非 dict、time 格式错、price <= 0、available_cash < 0
  6. 优先级冲突（14:45 + 浮亏 -1.2% → 强平优先于全平）
  7. 不足一手 → hold

运行：python3 src/build/build-B12/开发产物/scripts/test.py
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from build import run, validate_input  # noqa: E402


# ── 测试框架 ─────────────────────────────────────────────────────────
_PASSED = 0
_FAILED = 0
_FAILS = []


def assert_eq(actual, expected, label):
    global _PASSED, _FAILED
    if actual == expected:
        _PASSED += 1
        print(f"  ✓ {label}")
    else:
        _FAILED += 1
        msg = f"  ✗ {label}: expected {expected!r}, got {actual!r}"
        _FAILS.append(msg)
        print(msg)


def assert_in(needle, haystack, label):
    global _PASSED, _FAILED
    if needle in haystack:
        _PASSED += 1
        print(f"  ✓ {label}")
    else:
        _FAILED += 1
        msg = f"  ✗ {label}: '{needle}' not in '{haystack}'"
        _FAILS.append(msg)
        print(msg)


def assert_raises(exc_types, fn, label):
    global _PASSED, _FAILED
    try:
        fn()
    except exc_types:
        _PASSED += 1
        print(f"  ✓ {label}")
        return
    except Exception as e:
        _FAILED += 1
        msg = f"  ✗ {label}: expected {exc_types}, got {type(e).__name__}: {e}"
        _FAILS.append(msg)
        print(msg)
        return
    _FAILED += 1
    msg = f"  ✗ {label}: no exception raised"
    _FAILS.append(msg)
    print(msg)


def section(title):
    print(f"\n── {title} ──")


def _r(item):
    """run 单条便捷封装。"""
    return run(item)[0]


# ════════════════════════════════════════════════════════════════════
# 1) A 股 — 5 优先级 + T+1 边界 + 资金不足
# ════════════════════════════════════════════════════════════════════
section("A_STOCK 全规则")

o = _r({"code": "600036", "pnl_pct": 0.015, "sellable_qty": 800, "locked_qty": 0,
        "price": 10.0, "available_cash": 100000, "time": "10:00"})
assert_eq(o["action"], "buy", "A股加仓 action=buy")
assert_eq(o["qty_change"], 400, "A股加仓 +400 股")
assert_eq(o["target_qty"], 1200, "A股加仓 target=1200")
assert_in("[A_STOCK]", o["reason"], "reason 含 A_STOCK 前缀")

o = _r({"code": "600036", "pnl_pct": 0.015, "sellable_qty": 800, "locked_qty": 200,
        "price": 10.0, "available_cash": 100000, "time": "10:00"})
assert_eq(o["qty_change"], 400, "A股加仓基数=sellable 而非总持仓")

o = _r({"code": "000001", "pnl_pct": -0.007, "sellable_qty": 1000, "locked_qty": 0,
        "price": 10.0, "available_cash": 0, "time": "10:00"})
assert_eq(o["action"], "sell", "A股砍半 action=sell")
assert_eq(o["qty_change"], -500, "A股砍半 -500 股")

o = _r({"code": "000001", "pnl_pct": -0.007, "sellable_qty": 200, "locked_qty": 800,
        "price": 10.0, "available_cash": 0, "time": "10:00"})
assert_eq(o["qty_change"], -100, "A股砍半基数=可卖 200 而非总 1000")

o = _r({"code": "300750", "pnl_pct": -0.012, "sellable_qty": 600, "locked_qty": 400,
        "price": 100.0, "available_cash": 0, "time": "10:00"})
assert_eq(o["qty_change"], -600, "A股全平仅平可卖部分")
assert_in("T+1 阻断", o["reason"], "reason 标注 T+1 阻断")

o = _r({"code": "601318", "pnl_pct": -0.003, "sellable_qty": 0, "locked_qty": 500,
        "price": 60.0, "available_cash": 0, "time": "14:45"})
assert_eq(o["action"], "hold", "A股强平时全锁仓不可卖 → hold")
assert_eq(o["qty_change"], 0, "qty_change=0")

o = _r({"code": "601318", "pnl_pct": -0.003, "sellable_qty": 300, "locked_qty": 200,
        "price": 60.0, "available_cash": 0, "time": "14:45"})
assert_eq(o["qty_change"], -300, "A股强平仅平可卖 300")

o = _r({"code": "600519", "pnl_pct": 0.015, "sellable_qty": 800, "locked_qty": 0,
        "price": 100.0, "available_cash": 1000, "time": "10:00"})
assert_eq(o["action"], "hold", "A股资金不足 → hold")
assert_in("cash_insufficient", o["reason"], "reason 含 cash_insufficient")

o = _r({"code": "600036", "pnl_pct": 0.015, "sellable_qty": 850, "locked_qty": 0,
        "price": 10.0, "available_cash": 100000, "time": "10:00"})
assert_eq(o["qty_change"], 400, "A股加仓向下取整 425→400")

o = _r({"code": "600036", "pnl_pct": 0.005, "sellable_qty": 800, "locked_qty": 0,
        "price": 10.0, "available_cash": 100000, "time": "10:00"})
assert_eq(o["action"], "hold", "A股浮盈不足 1% → hold")


# ════════════════════════════════════════════════════════════════════
# 2) A 股 ETF
# ════════════════════════════════════════════════════════════════════
section("A_ETF")

o = _r({"code": "510300", "pnl_pct": 0.02, "sellable_qty": 1000, "locked_qty": 0,
        "price": 1.5, "available_cash": 10000, "time": "10:00"})
assert_eq(o["action"], "buy", "ETF 加仓 action=buy")
assert_eq(o["qty_change"], 500, "ETF 加仓 500 股")
assert_in("[A_ETF]", o["reason"], "reason 含 A_ETF")

o = _r({"code": "510300", "pnl_pct": -0.008, "sellable_qty": 600, "locked_qty": 0,
        "price": 1.5, "available_cash": 0, "time": "10:00"})
assert_eq(o["qty_change"], -300, "ETF 砍半 -300 股")


# ════════════════════════════════════════════════════════════════════
# 3) 股指期货
# ════════════════════════════════════════════════════════════════════
section("INDEX_FUTURE (IF/IC)")

o = _r({"code": "IF2406", "pnl_pct": 0.015, "sellable_qty": 2, "locked_qty": 0,
        "price": 4000.0, "available_cash": 200000, "time": "10:00"})
assert_eq(o["action"], "buy", "IF 加仓 action=buy")
assert_eq(o["qty_change"], 1, "IF 加 1 手")
assert_in("[INDEX_FUTURE]", o["reason"], "reason 含 INDEX_FUTURE")

o = _r({"code": "IF2406", "pnl_pct": 0.015, "sellable_qty": 2, "locked_qty": 0,
        "price": 4000.0, "available_cash": 50000, "time": "10:00"})
assert_eq(o["action"], "hold", "IF 保证金不足 → hold")
assert_in("cash_insufficient", o["reason"], "IF reason 含 cash_insufficient")

o = _r({"code": "IC2406", "pnl_pct": -0.007, "sellable_qty": 2, "locked_qty": 2,
        "price": 6000.0, "available_cash": 0, "time": "10:00"})
assert_eq(o["qty_change"], -2, "IC 砍半基数=4(T+0 含锁仓)")

o = _r({"code": "IF2406", "pnl_pct": -0.001, "sellable_qty": 0, "locked_qty": 3,
        "price": 4000.0, "available_cash": 0, "time": "14:45"})
assert_eq(o["qty_change"], -3, "IF 强平 T+0 含锁仓全平")


# ════════════════════════════════════════════════════════════════════
# 4) 商品期货
# ════════════════════════════════════════════════════════════════════
section("COMMODITY_FUTURE (rb/cu)")

o = _r({"code": "rb2410", "pnl_pct": 0.015, "sellable_qty": 4, "locked_qty": 0,
        "price": 3500.0, "available_cash": 50000, "time": "10:00"})
assert_eq(o["action"], "buy", "rb 加仓")
assert_eq(o["qty_change"], 2, "rb 加 2 手")
assert_in("[COMMODITY_FUTURE]", o["reason"], "reason 含 COMMODITY_FUTURE")

o = _r({"code": "cu2406", "pnl_pct": -0.012, "sellable_qty": 1, "locked_qty": 1,
        "price": 70000.0, "available_cash": 0, "time": "10:00"})
assert_eq(o["qty_change"], -2, "cu 全平 T+0 平 2 手")


# ════════════════════════════════════════════════════════════════════
# 5) 港股
# ════════════════════════════════════════════════════════════════════
section("HK_STOCK")

o = _r({"code": "00700", "pnl_pct": 0.015, "sellable_qty": 100, "locked_qty": 100,
        "price": 400.0, "available_cash": 200000, "time": "10:00"})
assert_eq(o["action"], "buy", "港股加仓")
assert_eq(o["qty_change"], 100, "港股加 100 股 T+0")
assert_in("[HK_STOCK]", o["reason"], "reason 含 HK_STOCK")

o = _r({"code": "00700", "pnl_pct": -0.007, "sellable_qty": 100, "locked_qty": 100,
        "price": 400.0, "available_cash": 0, "time": "10:00"})
assert_eq(o["qty_change"], -100, "港股砍半 -100 股 T+0")

o = _r({"code": "00700", "pnl_pct": -0.003, "sellable_qty": 100, "locked_qty": 0,
        "price": 400.0, "available_cash": 0, "time": "14:50"})
assert_eq(o["action"], "hold", "港股 14:50 未到强平时间")

o = _r({"code": "00700", "pnl_pct": -0.003, "sellable_qty": 100, "locked_qty": 0,
        "price": 400.0, "available_cash": 0, "time": "15:45"})
assert_eq(o["qty_change"], -100, "港股 15:45 强平")


# ════════════════════════════════════════════════════════════════════
# 6) UNKNOWN 兜底 + 优先级冲突 + 不足一手
# ════════════════════════════════════════════════════════════════════
section("UNKNOWN & 优先级冲突 & 不足一手")

o = _r({"code": "ABCD", "pnl_pct": -0.012, "sellable_qty": 100, "locked_qty": 0,
        "price": 10.0, "available_cash": 0, "time": "10:00"})
assert_eq(o["action"], "hold", "UNKNOWN → hold")
assert_in("[UNKNOWN]", o["reason"], "reason 含 UNKNOWN")

o = _r({"code": "600036", "pnl_pct": -0.012, "sellable_qty": 500, "locked_qty": 0,
        "price": 10.0, "available_cash": 0, "time": "14:45"})
assert_eq(o["qty_change"], -500, "优先级冲突 强平/全平结果一致")
assert_in("强平", o["reason"], "优先级 1 强平触发(reason 含强平)")

o = _r({"code": "600036", "pnl_pct": -0.007, "sellable_qty": 50, "locked_qty": 0,
        "price": 10.0, "available_cash": 0, "time": "10:00"})
assert_eq(o["action"], "hold", "砍半不足一手 → hold")


# ════════════════════════════════════════════════════════════════════
# 7) 异常输入
# ════════════════════════════════════════════════════════════════════
section("validate_input 异常")

assert_raises(KeyError, lambda: run({
    "code": "600036", "pnl_pct": 0.015, "sellable_qty": 800, "locked_qty": 0,
    "available_cash": 100000, "time": "10:00",
}), "缺字段 price → KeyError")

assert_raises(ValueError, lambda: run({
    "code": "600036", "pnl_pct": 0.015, "sellable_qty": -100, "locked_qty": 0,
    "price": 10.0, "available_cash": 100000, "time": "10:00",
}), "负 sellable_qty → ValueError")

assert_raises(ValueError, lambda: run([]), "空列表 → ValueError")

assert_raises(TypeError, lambda: run("not a dict"), "字符串输入 → TypeError")

assert_raises(ValueError, lambda: run({
    "code": "600036", "pnl_pct": 0.015, "sellable_qty": 800, "locked_qty": 0,
    "price": 10.0, "available_cash": 100000, "time": "10:00:00",
}), "time HH:MM:SS 格式 → ValueError(v2 仅 HH:MM)")

assert_raises(ValueError, lambda: run({
    "code": "600036", "pnl_pct": 0.015, "sellable_qty": 800, "locked_qty": 0,
    "price": 0, "available_cash": 100000, "time": "10:00",
}), "price=0 → ValueError")

assert_raises(ValueError, lambda: run({
    "code": "600036", "pnl_pct": 0.015, "sellable_qty": 800, "locked_qty": 0,
    "price": 10.0, "available_cash": -1, "time": "10:00",
}), "available_cash<0 → ValueError")

o = _r({"code": "600036", "pnl_pct": 0.015, "sellable_qty": 800, "locked_qty": 0,
        "price": 10.0, "available_cash": 100000, "time": "10:00"})
expected_keys = {"code", "pnl_pct", "current_qty", "time",
                 "action", "qty_change", "target_qty", "reason"}
assert_eq(set(o.keys()), expected_keys, "8 字段契约严格匹配")


# ════════════════════════════════════════════════════════════════════
# 总结
# ════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 64}")
print(f"测试总数：{_PASSED + _FAILED}  通过：{_PASSED}  失败：{_FAILED}")
print('=' * 64)
if _FAILED:
    print("\n失败用例：")
    for m in _FAILS:
        print(m)
    sys.exit(1)
print("\n✓ 所有用例通过")
