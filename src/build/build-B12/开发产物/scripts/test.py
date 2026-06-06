"""
B12 日内仓位动态管理 — 测试脚本
覆盖：正常输入（每个分支）、边界值、异常输入、A股约束
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build import run, validate_input, manage_position


def _assert(condition, msg):
    if not condition:
        raise AssertionError(f"FAIL: {msg}")
    print(f"  PASS: {msg}")


# ── 正常输入：每个逻辑分支各一条 ─────────────────────────────────────
def test_normal():
    print("\n[test_normal]")

    # 加仓：浮盈 1.5%，持仓 1000 股 → 加仓 500 股
    r = run({"code": "A", "pnl_pct": 0.015, "current_qty": 1000, "time": "10:00:00"})[0]
    _assert(r["action"] == "buy", "浮盈1.5%应触发加仓")
    _assert(r["qty_change"] == 500, f"加仓量应为500，实际{r['qty_change']}")
    _assert(r["target_qty"] == 1500, f"目标持仓应为1500，实际{r['target_qty']}")

    # 砍半仓：浮亏 0.7%，持仓 2000 股 → 卖出 1000 股
    r = run({"code": "B", "pnl_pct": -0.007, "current_qty": 2000, "time": "10:00:00"})[0]
    _assert(r["action"] == "sell", "浮亏0.7%应触发砍半仓")
    _assert(r["qty_change"] == -1000, f"砍半仓量应为-1000，实际{r['qty_change']}")

    # 全平止损：浮亏 1.2%，持仓 500 股 → 全平
    r = run({"code": "C", "pnl_pct": -0.012, "current_qty": 500, "time": "10:00:00"})[0]
    _assert(r["action"] == "sell", "浮亏1.2%应触发全平")
    _assert(r["qty_change"] == -500, f"全平应卖出500，实际{r['qty_change']}")
    _assert(r["target_qty"] == 0, "全平后目标持仓应为0")

    # hold：浮盈 0.5%，未触发任何条件
    r = run({"code": "D", "pnl_pct": 0.005, "current_qty": 1000, "time": "10:00:00"})[0]
    _assert(r["action"] == "hold", "浮盈0.5%应hold")
    _assert(r["qty_change"] == 0, "hold时qty_change应为0")

    # 强平：时间 14:50:00 >= 14:45:00
    r = run({"code": "E", "pnl_pct": 0.015, "current_qty": 1000, "time": "14:50:00"})[0]
    _assert(r["action"] == "sell", "14:50应触发强平")
    _assert(r["qty_change"] == -1000, "强平应全部卖出")
    _assert("强平" in r["reason"], "强平原因应包含'强平'")


# ── 边界值 ────────────────────────────────────────────────────────────
def test_boundary():
    print("\n[test_boundary]")

    # 恰好浮亏 0.5%（含边界 >=）→ 应触发砍半仓
    r = run({"code": "A", "pnl_pct": -0.005, "current_qty": 1000, "time": "10:00:00"})[0]
    _assert(r["action"] == "sell", "浮亏恰好0.5%（含边界）应触发砍半仓")

    # 恰好浮亏 1.0%（含边界 >=）→ 应触发全平
    r = run({"code": "B", "pnl_pct": -0.01, "current_qty": 1000, "time": "10:00:00"})[0]
    _assert(r["action"] == "sell", "浮亏恰好1.0%（含边界）应触发全平")
    _assert(r["qty_change"] == -1000, "全平应卖出全部")

    # 恰好浮盈 1.0%（严格大于 > 不触发）→ 应 hold
    r = run({"code": "C", "pnl_pct": 0.01, "current_qty": 1000, "time": "10:00:00"})[0]
    _assert(r["action"] == "hold", "浮盈恰好1.0%（不含边界）应hold")

    # 恰好时间 14:45:00 → 应触发强平
    r = run({"code": "D", "pnl_pct": 0.0, "current_qty": 1000, "time": "14:45:00"})[0]
    _assert(r["action"] == "sell", "14:45:00（含边界）应触发强平")

    # 时间 14:44:59 → 不触发强平
    r = run({"code": "E", "pnl_pct": -0.007, "current_qty": 1000, "time": "14:44:59"})[0]
    _assert(r["action"] == "sell", "14:44:59不应强平，但因浮亏0.7%触发砍半仓")
    _assert("强平" not in r["reason"], "14:44:59不应因强平卖出")

    # 100股整数倍：持仓 150 股，砍半仓 → 75 股向下取整 = 0，兜底至 100 股
    r = run({"code": "F", "pnl_pct": -0.007, "current_qty": 150, "time": "10:00:00"})[0]
    _assert(r["qty_change"] == -100, f"150股砍半应卖出100股(兜底)，实际{r['qty_change']}")

    # 持仓 50 股（不足1手），砍半仓 → hold
    r = run({"code": "G", "pnl_pct": -0.007, "current_qty": 50, "time": "10:00:00"})[0]
    _assert(r["action"] == "hold", "持仓50股不足1手，砍半仓应hold")

    # 加仓取整：持仓 150 股，加仓50% → 75 → 向下取整 = 0 → hold
    r = run({"code": "H", "pnl_pct": 0.015, "current_qty": 150, "time": "10:00:00"})[0]
    _assert(r["qty_change"] == 0, "加仓量不足1手时qty_change应为0")


# ── 异常输入 ──────────────────────────────────────────────────────────
def test_invalid_input():
    print("\n[test_invalid_input]")

    # 非 dict/list 类型
    try:
        validate_input("not a dict")
        _assert(False, "字符串输入应抛出 TypeError")
    except TypeError:
        print("  PASS: 字符串输入正确抛出 TypeError")

    # 空列表
    try:
        validate_input([])
        _assert(False, "空列表应抛出 ValueError")
    except ValueError:
        print("  PASS: 空列表正确抛出 ValueError")

    # 缺少字段
    try:
        validate_input({"code": "A", "pnl_pct": 0.01, "current_qty": 1000})  # 缺 time
        _assert(False, "缺少time字段应抛出 KeyError")
    except KeyError:
        print("  PASS: 缺少time字段正确抛出 KeyError")

    # pnl_pct 类型错误
    try:
        validate_input({"code": "A", "pnl_pct": "1%", "current_qty": 1000, "time": "10:00:00"})
        _assert(False, "pnl_pct字符串应抛出 TypeError")
    except TypeError:
        print("  PASS: pnl_pct字符串正确抛出 TypeError")

    # current_qty 负数
    try:
        validate_input({"code": "A", "pnl_pct": 0.01, "current_qty": -100, "time": "10:00:00"})
        _assert(False, "current_qty负数应抛出 ValueError")
    except ValueError:
        print("  PASS: current_qty负数正确抛出 ValueError")

    # time 格式错误
    try:
        validate_input({"code": "A", "pnl_pct": 0.01, "current_qty": 1000, "time": "10:00"})
        _assert(False, "time格式错误应抛出 ValueError")
    except ValueError:
        print("  PASS: time格式错误正确抛出 ValueError")

    # 空 code
    try:
        validate_input({"code": "", "pnl_pct": 0.01, "current_qty": 1000, "time": "10:00:00"})
        _assert(False, "空code应抛出 TypeError")
    except TypeError:
        print("  PASS: 空code正确抛出 TypeError")


# ── 批量入口测试 ──────────────────────────────────────────────────────
def test_batch():
    print("\n[test_batch]")
    positions = [
        {"code": "A", "pnl_pct":  0.015, "current_qty": 1000, "time": "10:00:00"},
        {"code": "B", "pnl_pct": -0.007, "current_qty": 2000, "time": "10:00:00"},
        {"code": "C", "pnl_pct": -0.012, "current_qty":  500, "time": "10:00:00"},
    ]
    results = run(positions)
    _assert(len(results) == 3, "批量返回数量应为3")
    _assert(results[0]["action"] == "buy",  "第1条应加仓")
    _assert(results[1]["action"] == "sell", "第2条应砍半仓")
    _assert(results[2]["action"] == "sell", "第3条应全平")


if __name__ == "__main__":
    test_normal()
    test_boundary()
    test_invalid_input()
    test_batch()
    print("\n所有测试通过 ✓")
