"""
B12 日内仓位动态管理

规则（优先级从高到低）：
  1. 当前时间 >= 14:45:00  → 强平（全平）
  2. 浮亏 >= 1%            → 全平止损
  3. 浮亏 >= 0.5%          → 砍半仓
  4. 浮盈 > 1%             → 加仓 50%
  5. 其他                  → hold

pnl_pct 单位：小数（0.01 表示 1%，-0.005 表示 -0.5%）
数量约束：所有 qty_change 向下取整到 100 的整数倍（A股最小交易单位）
"""

import math
from datetime import datetime, time as dtime


# ── 配置常量 ─────────────────────────────────────────────────────────
TAKE_PROFIT_THRESHOLD = 0.01       # 浮盈加仓阈值（严格大于）
STOP_LOSS_HALF_THRESHOLD = 0.005   # 砍半仓阈值（含边界 >=）
STOP_LOSS_FULL_THRESHOLD = 0.01    # 全平阈值（含边界 >=）
FORCE_CLOSE_TIME = dtime(14, 45, 0)  # 强平时间（收盘前15分钟）
LOT_SIZE = 100                     # A股最小交易单位


# ── 判断层（纯函数）──────────────────────────────────────────────────
def _round_down_lot(qty: int) -> int:
    return math.floor(qty / LOT_SIZE) * LOT_SIZE


def _should_force_close(now_time: dtime) -> bool:
    return now_time >= FORCE_CLOSE_TIME


def _should_stop_loss_full(pnl_pct: float) -> bool:
    return pnl_pct <= -STOP_LOSS_FULL_THRESHOLD


def _should_stop_loss_half(pnl_pct: float) -> bool:
    return pnl_pct <= -STOP_LOSS_HALF_THRESHOLD


def _should_take_profit(pnl_pct: float) -> bool:
    return pnl_pct > TAKE_PROFIT_THRESHOLD


# ── 决策层 ───────────────────────────────────────────────────────────
def manage_position(code: str, pnl_pct: float, current_qty: int, now: str) -> dict:
    """
    单只股票仓位决策。

    Args:
        code:        股票代码，如 "600036"
        pnl_pct:     浮盈亏，小数形式（0.01=+1%，-0.005=-0.5%）
        current_qty: 当前持仓股数（整数）
        now:         当前时间字符串 "HH:MM:SS"

    Returns:
        调仓指令 dict，字段遵循 CLAUDE.md §调仓指令数据结构
    """
    now_time = datetime.strptime(now, "%H:%M:%S").time()

    order = {
        "code": code,
        "pnl_pct": pnl_pct,
        "current_qty": current_qty,
        "time": now,
        "action": "hold",
        "qty_change": 0,
        "target_qty": current_qty,
        "reason": "",
    }

    # 优先级 1：强平
    if _should_force_close(now_time):
        order["action"] = "sell"
        order["qty_change"] = -current_qty
        order["target_qty"] = 0
        order["reason"] = "收盘前15分钟强平"
        return order

    # 优先级 2：全平止损
    if _should_stop_loss_full(pnl_pct):
        order["action"] = "sell"
        order["qty_change"] = -current_qty
        order["target_qty"] = 0
        order["reason"] = f"浮亏 {pnl_pct:.2%} >= -1%，全平止损"
        return order

    # 优先级 3：砍半仓
    if _should_stop_loss_half(pnl_pct):
        raw_sell = current_qty // 2
        sell_qty = _round_down_lot(raw_sell)
        if sell_qty == 0 and current_qty >= LOT_SIZE:
            sell_qty = LOT_SIZE
        if sell_qty > 0:
            order["action"] = "sell"
            order["qty_change"] = -sell_qty
            order["target_qty"] = current_qty - sell_qty
            order["reason"] = f"浮亏 {pnl_pct:.2%} >= -0.5%，砍半仓 {sell_qty} 股"
        else:
            order["reason"] = f"浮亏 {pnl_pct:.2%}，持仓不足1手无法砍仓"
        return order

    # 优先级 4：加仓
    if _should_take_profit(pnl_pct):
        raw_add = int(current_qty * 0.5)
        add_qty = _round_down_lot(raw_add)
        if add_qty > 0:
            order["action"] = "buy"
            order["qty_change"] = add_qty
            order["target_qty"] = current_qty + add_qty
            order["reason"] = f"浮盈 {pnl_pct:.2%} > 1%，加仓50% {add_qty} 股"
        else:
            order["reason"] = f"浮盈 {pnl_pct:.2%}，加仓量不足1手"
        return order

    # 优先级 5：hold
    order["reason"] = f"浮盈亏 {pnl_pct:+.2%}，未触发任何条件"
    return order


# ── 批量层 ───────────────────────────────────────────────────────────
def batch_manage(positions: list) -> list:
    """
    批量生成调仓指令。

    Args:
        positions: list of dict，每项包含 code / pnl_pct / current_qty / time

    Returns:
        list of 调仓指令 dict
    """
    return [
        manage_position(p["code"], p["pnl_pct"], p["current_qty"], p["time"])
        for p in positions
    ]


# ── 输入验证 ─────────────────────────────────────────────────────────
def validate_input(input_data):
    """
    校验输入数据合法性。

    Args:
        input_data: dict 或 list of dict

    Raises:
        TypeError / ValueError / KeyError：字段缺失、类型错误、非法值
    """
    if isinstance(input_data, dict):
        items = [input_data]
    elif isinstance(input_data, list):
        items = input_data
    else:
        raise TypeError(f"input_data 必须是 dict 或 list，收到 {type(input_data)}")

    if len(items) == 0:
        raise ValueError("input_data 不能为空列表")

    required = {"code", "pnl_pct", "current_qty", "time"}
    for i, item in enumerate(items):
        missing = required - set(item.keys())
        if missing:
            raise KeyError(f"第 {i} 条记录缺少字段: {missing}")
        if not isinstance(item["code"], str) or not item["code"]:
            raise TypeError(f"第 {i} 条 code 必须是非空字符串")
        if not isinstance(item["pnl_pct"], (int, float)):
            raise TypeError(f"第 {i} 条 pnl_pct 必须是数值")
        if not isinstance(item["current_qty"], int) or item["current_qty"] < 0:
            raise ValueError(f"第 {i} 条 current_qty 必须是非负整数")
        try:
            datetime.strptime(item["time"], "%H:%M:%S")
        except ValueError:
            raise ValueError(f"第 {i} 条 time 格式必须为 HH:MM:SS，收到 '{item['time']}'")


# ── 标准入口 ─────────────────────────────────────────────────────────
def run(input_data, config=None) -> list:
    """
    标准调用入口。

    Args:
        input_data: dict（单条）或 list of dict（批量）
        config:     保留参数，暂未使用

    Returns:
        list of 调仓指令 dict
    """
    validate_input(input_data)
    if isinstance(input_data, dict):
        return [manage_position(
            input_data["code"],
            input_data["pnl_pct"],
            input_data["current_qty"],
            input_data["time"],
        )]
    return batch_manage(input_data)


# ── 输出层 ───────────────────────────────────────────────────────────
def print_order(order: dict):
    label = {"buy": "【加仓 BUY】", "sell": "【减仓/平仓 SELL】", "hold": "【持仓不动 HOLD】"}
    print("=" * 52)
    print(f"  股票代码  : {order['code']}")
    print(f"  当前时间  : {order['time']}")
    print(f"  浮盈亏    : {order['pnl_pct']:+.2%}")
    print(f"  当前持仓  : {order['current_qty']} 股")
    print(f"  操作指令  : {label.get(order['action'], order['action'])}")
    if order["qty_change"] != 0:
        print(f"  变动数量  : {order['qty_change']:+d} 股")
        print(f"  目标持仓  : {order['target_qty']} 股")
    print(f"  触发原因  : {order['reason']}")
    print("=" * 52)


# ── 示例入口 ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = [
        {"code": "600036", "pnl_pct":  0.015, "current_qty": 1000, "time": "10:30:00"},  # 加仓
        {"code": "000001", "pnl_pct": -0.007, "current_qty": 2000, "time": "13:00:00"},  # 砍半仓
        {"code": "300750", "pnl_pct": -0.012, "current_qty":  500, "time": "13:00:00"},  # 全平
        {"code": "002594", "pnl_pct":  0.003, "current_qty":  800, "time": "13:00:00"},  # hold
        {"code": "601318", "pnl_pct":  0.008, "current_qty": 1200, "time": "14:50:00"},  # 强平
    ]

    print("\nB12 日内仓位动态管理 — 调仓指令演示\n")
    for order in run(sample):
        print_order(order)
