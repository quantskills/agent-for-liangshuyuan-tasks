#!/usr/bin/env python3
# B11 自动止盈止损+仓位管理
# 适用品种：A股 / 股指期货 / 商品期货
# 纯 Python 标准库，零框架依赖

import json
import os
import sys
from datetime import datetime, timedelta

# ============================================================
# 配置常量（交易规则阈值）
# ============================================================

STOP_PROFIT_PCT   =  0.05   # 次日高开 ≥ 5% → 止盈
STOP_LOSS_PCT     = -0.03   # 次日低开 ≤ -3% → 止损
FORCE_CLOSE_DAYS  =  2       # 持仓 ≥ 2 日（含入场日）→ 强平
MAX_SINGLE_RATIO  =  0.10    # 单票仓位上限 10%

# 日期格式
DATE_FMT = "%Y-%m-%d"

# A股最小交易单位
A_STOCK_LOT = 100
# 期货最小交易单位
FUTURE_LOT = 1

# A股代码特征：6位数字 或 sh/sz 前缀
def _is_a_stock(code):
    c = code.replace("sh", "").replace("sz", "").replace("SH", "").replace("SZ", "")
    return c.isdigit() and len(c) == 6

# 期货代码特征：字母前缀 + 数字（如 IF2406, rb2401）
def _is_future(code):
    # 股指期货：IF/IC/IH/IM
    for pf in ("IF", "IC", "IH", "IM"):
        if code.upper().startswith(pf):
            return True
    # 商品期货：小写字母前缀 + 数字
    import re
    return bool(re.match(r'^[a-z]{1,3}\d+$', code)) or bool(re.match(r'^[A-Z]{1,3}\d+$', code))

def _get_lot_size(code):
    """返回最小交易单位"""
    if _is_future(code):
        return FUTURE_LOT
    return A_STOCK_LOT  # A股默认100


# ============================================================
# 校验层
# ============================================================

def validate_input(pos):
    """校验单条输入，返回 (ok, error_msg)"""
    required = {
        "code": str, "entry_price": (int, float),
        "entry_date": str, "current_qty": int,
        "open_price": (int, float), "available_cash": (int, float),
        "today": str,
    }
    for field, typ in required.items():
        if field not in pos:
            return False, f"缺少字段: {field}"
        if not isinstance(pos[field], typ):
            return False, f"字段 {field} 类型错误，期望 {typ}，实际 {type(pos[field])}"
    if pos["entry_price"] <= 0:
        return False, "entry_price 必须 > 0"
    if pos["open_price"] <= 0:
        return False, "open_price 必须 > 0"
    if pos["current_qty"] < 0:
        return False, "current_qty 必须 >= 0"
    if pos["available_cash"] < 0:
        return False, "available_cash 必须 >= 0"
    # 校验日期格式
    try:
        datetime.strptime(pos["entry_date"], DATE_FMT)
        datetime.strptime(pos["today"], DATE_FMT)
    except ValueError:
        return False, "日期格式错误，需为 YYYY-MM-DD"
    return True, ""


# ============================================================
# 判断层
# ============================================================

def _days_held(entry_date_str, today_str):
    """计算持仓天数（含入场日，entry_date = 第 1 日）"""
    entry = datetime.strptime(entry_date_str, DATE_FMT)
    today = datetime.strptime(today_str, DATE_FMT)
    return (today - entry).days + 1  # +1 含入场日


def _is_next_day(entry_date_str, today_str):
    """判断今日是否为入场次日"""
    entry = datetime.strptime(entry_date_str, DATE_FMT)
    today = datetime.strptime(today_str, DATE_FMT)
    return (today - entry).days == 1


def _calc_pnl_pct(entry_price, open_price):
    """计算浮盈亏百分比（小数形式）"""
    return (open_price - entry_price) / entry_price


# ============================================================
# 决策层
# ============================================================

def manage_position(code, entry_price, entry_date, current_qty, open_price, available_cash, today):
    """
    核心决策函数。
    返回标准 8 字段调仓指令 dict。
    """
    lot = _get_lot_size(code)
    days = _days_held(entry_date, today)
    pnl_pct = _calc_pnl_pct(entry_price, open_price)
    is_next = _is_next_day(entry_date, today)
    position_value = current_qty * open_price

    def _qty_round(q):
        """向下取整到最小交易单位"""
        return max(0, int(q // lot) * lot)

    def _mk_order(action, target_qty, reason):
        return {
            "code": code,
            "pnl_pct": round(pnl_pct, 6),
            "current_qty": current_qty,
            "time": today,
            "action": action,
            "qty_change": target_qty - current_qty,
            "target_qty": target_qty,
            "reason": reason,
        }

    # ---- 优先级 1：次日止盈 ----
    if is_next and pnl_pct >= STOP_PROFIT_PCT:
        return _mk_order("sell", 0, f"[B11]次日止盈 open={open_price:.2f} entry={entry_price:.2f} pnl={pnl_pct:.4f}")

    # ---- 优先级 2：次日止损 ----
    if is_next and pnl_pct <= STOP_LOSS_PCT:
        return _mk_order("sell", 0, f"[B11]次日止损 open={open_price:.2f} entry={entry_price:.2f} pnl={pnl_pct:.4f}")

    # ---- 优先级 3：持仓 ≥ 2日强平 ----
    if days >= FORCE_CLOSE_DAYS:
        return _mk_order("sell", 0, f"[B11]持仓{days}日≥{FORCE_CLOSE_DAYS}日强制平仓 entry_date={entry_date}")

    # ---- 优先级 4：单票仓位 > 10% ----
    max_value = available_cash * MAX_SINGLE_RATIO
    if position_value > max_value:
        target_qty = _qty_round(max_value / open_price)
        if target_qty < current_qty:
            return _mk_order("sell", target_qty,
                f"[B11]单票仓位{position_value/available_cash:.2%}>{MAX_SINGLE_RATIO:.0%} 减仓至{target_qty}股")

    # ---- 优先级 5：hold ----
    return _mk_order("hold", current_qty, f"[B11]hold days={days} pnl={pnl_pct:.4f}")


# ============================================================
# 批量层
# ============================================================

def batch_manage(positions):
    """批量处理持仓列表"""
    return [manage_position(**pos) for pos in positions]


# ============================================================
# 入口
# ============================================================

def run(data):
    """
    标准入口函数。
    入参：dict（单条）或 list[dict]（批量）
    返回：dict（单条）或 list[dict]（批量）
    """
    if isinstance(data, list):
        if len(data) == 0:
            return []
        # 校验
        for i, pos in enumerate(data):
            ok, err = validate_input(pos)
            if not ok:
                raise ValueError(f"输入[{i}]校验失败: {err}")
        return batch_manage(data)
    elif isinstance(data, dict):
        ok, err = validate_input(data)
        if not ok:
            raise ValueError(f"输入校验失败: {err}")
        return manage_position(**data)
    else:
        raise TypeError("run() 入参必须为 dict 或 list[dict]")


# ============================================================
# 示例
# ============================================================

if __name__ == "__main__":
    test_positions = [
        {
            "code": "600036",
            "entry_price": 10.0,
            "entry_date": "2026-06-19",
            "current_qty": 800,
            "open_price": 10.55,
            "available_cash": 100000,
            "today": "2026-06-20",
        },
        {
            "code": "IF2406",
            "entry_price": 4000.0,
            "entry_date": "2026-06-18",
            "current_qty": 2,
            "open_price": 4050.0,
            "available_cash": 200000,
            "today": "2026-06-20",
        },
        {
            "code": "000001",
            "entry_price": 15.0,
            "entry_date": "2026-06-20",
            "current_qty": 500,
            "open_price": 14.5,
            "available_cash": 50000,
            "today": "2026-06-20",
        },
    ]

    print("=== B11 自动止盈止损+仓位管理 ===\n")
    for pos in test_positions:
        result = run(pos)
        print(f"code={result['code']:8s} entry={pos['entry_price']:>7.2f} "
              f"open={pos['open_price']:>7.2f} pnl={result['pnl_pct']:>+.4f} "
              f"qty={result['current_qty']:>5d} -> action={result['action']:4s} "
              f"target={result['target_qty']:>5d} reason={result['reason']}")

    print("\n=== 批量调用 ===")
    results = run(test_positions)
    for r in results:
        print(f"{r['code']}: {r['action']} qty_change={r['qty_change']:+d}")
