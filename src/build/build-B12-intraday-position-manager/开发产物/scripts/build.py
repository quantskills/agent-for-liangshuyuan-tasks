"""
B12 v2 — 日内仓位动态管理（多品种）

按品种分发到独立模块决策：
    A_STOCK / A_ETF       → markets/a_stock.py
    INDEX_FUTURE          → markets/index_future.py
    COMMODITY_FUTURE      → markets/commodity_future.py
    HK_STOCK              → markets/hk_stock.py
    UNKNOWN               → 直接 hold

规则（优先级从高到低，对所有品种语义一致）：
    1. 到达品种强平时间 → 强平
    2. 浮亏 >= 1%        → 全平
    3. 浮亏 >= 0.5%      → 砍半仓
    4. 浮盈 > 1%         → 加仓 50%
    5. 其他              → hold

差异点封装在每个 markets 模块的：
    sellable_qty 计算（T+1 vs T+0）
    lot_size      （A股=100, 期货=1, 港股按表）
    资金/保证金    （现金 vs margin）

v2 仅支持多头持仓。
"""
import os
import re
import sys

# 允许 `python build.py` 直接运行：把 scripts/ 加入 sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from classify import classify
from common import make_hold, reason_prefix
from markets import a_stock, index_future, commodity_future, hk_stock


# ── 入参字段 ─────────────────────────────────────────────────────────
_REQUIRED_FIELDS = (
    "code", "pnl_pct",
    "sellable_qty", "locked_qty",
    "price", "available_cash",
    "time",
)

_RE_TIME = re.compile(r"^\d{2}:\d{2}$")


# ── 输入校验 ─────────────────────────────────────────────────────────
def validate_input(input_data) -> None:
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
        raise TypeError(f"input_data 必须是 dict 或 list，收到 {type(input_data).__name__}")

    if len(items) == 0:
        raise ValueError("input_data 不能为空列表")

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise TypeError(f"第 {i} 条记录必须是 dict，收到 {type(item).__name__}")
        missing = set(_REQUIRED_FIELDS) - set(item.keys())
        if missing:
            raise KeyError(f"第 {i} 条记录缺少字段: {sorted(missing)}")
        if not isinstance(item["code"], str) or not item["code"]:
            raise TypeError(f"第 {i} 条 code 必须是非空字符串")
        if not isinstance(item["pnl_pct"], (int, float)):
            raise TypeError(f"第 {i} 条 pnl_pct 必须是数值")
        for fld in ("sellable_qty", "locked_qty"):
            if not isinstance(item[fld], int) or item[fld] < 0:
                raise ValueError(f"第 {i} 条 {fld} 必须是非负整数")
        if not isinstance(item["price"], (int, float)) or item["price"] <= 0:
            raise ValueError(f"第 {i} 条 price 必须是正数")
        if not isinstance(item["available_cash"], (int, float)) or item["available_cash"] < 0:
            raise ValueError(f"第 {i} 条 available_cash 必须是非负数")
        if not isinstance(item["time"], str) or not _RE_TIME.match(item["time"]):
            raise ValueError(f"第 {i} 条 time 必须是 'HH:MM' 字符串，收到 '{item['time']}'")


# ── 决策分发 ─────────────────────────────────────────────────────────
def _dispatch(item: dict) -> dict:
    """按品种分发到对应市场模块。"""
    market = classify(item["code"])
    total = int(item["sellable_qty"]) + int(item["locked_qty"])

    if market == "A_STOCK":
        return a_stock.manage(item, "A_STOCK")
    if market == "A_ETF":
        return a_stock.manage(item, "A_ETF")
    if market == "INDEX_FUTURE":
        return index_future.manage(item)
    if market == "COMMODITY_FUTURE":
        return commodity_future.manage(item)
    if market == "HK_STOCK":
        return hk_stock.manage(item)

    # UNKNOWN：直接 hold，避免误操作
    return make_hold(
        item["code"], float(item["pnl_pct"]), total, item["time"],
        f"{reason_prefix('UNKNOWN', 0)} 未识别品种 hold",
    )


# ── 批量层 ───────────────────────────────────────────────────────────
def batch_manage(positions: list) -> list:
    return [_dispatch(p) for p in positions]


# ── 标准入口 ─────────────────────────────────────────────────────────
def run(input_data, config=None) -> list:
    """
    标准调用入口。
    Args:
        input_data: dict（单条）或 list of dict（批量）
        config:     保留参数，暂未使用
    Returns:
        list of 调仓指令 dict（即使单条也返回长度为 1 的列表）
    """
    validate_input(input_data)
    items = [input_data] if isinstance(input_data, dict) else input_data
    return batch_manage(items)


# ── 输出层 ───────────────────────────────────────────────────────────
def print_order(order: dict) -> None:
    label = {"buy": "【加仓 BUY】", "sell": "【减仓/平仓 SELL】", "hold": "【持仓不动 HOLD】"}
    print("=" * 64)
    print(f"  代码      : {order['code']}")
    print(f"  当前时间  : {order['time']}")
    print(f"  浮盈亏    : {order['pnl_pct']:+.2%}")
    print(f"  当前持仓  : {order['current_qty']}")
    print(f"  操作指令  : {label.get(order['action'], order['action'])}")
    if order["qty_change"] != 0:
        print(f"  变动数量  : {order['qty_change']:+d}")
        print(f"  目标持仓  : {order['target_qty']}")
    print(f"  触发原因  : {order['reason']}")
    print("=" * 64)


# ── 示例入口 ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample = [
        # A股 — 加仓（可卖 800，锁仓 0，加仓 50% × 800 = 400 股）
        {"code": "600036", "pnl_pct":  0.015, "sellable_qty":  800, "locked_qty":   0,
         "price": 10.0, "available_cash": 100000, "time": "10:30"},
        # A股 — 砍半仓但今仓 800 锁仓不可卖（可卖 200 → 砍 100 股）
        {"code": "000001", "pnl_pct": -0.007, "sellable_qty":  200, "locked_qty": 800,
         "price": 10.0, "available_cash":      0, "time": "13:00"},
        # A股 — 全平但 T+1 阻断 400 股（可卖 600，平 600）
        {"code": "300750", "pnl_pct": -0.012, "sellable_qty":  600, "locked_qty": 400,
         "price": 100.0, "available_cash":     0, "time": "13:00"},
        # A股 — 14:50 强平，全是锁仓 → hold
        {"code": "601318", "pnl_pct":  0.008, "sellable_qty":    0, "locked_qty": 500,
         "price": 60.0, "available_cash":      0, "time": "14:50"},
        # 股指期货 IF — 加仓 1 手（可卖 2，T+0 锁仓应为 0，加仓 50% × 2 = 1 手）
        {"code": "IF2406", "pnl_pct":  0.015, "sellable_qty":    2, "locked_qty":   0,
         "price": 4000.0, "available_cash": 200000, "time": "10:30"},
        # 商品期货 rb — 砍半仓 T+0（可卖 4，T+0 锁仓应为 0）
        {"code": "rb2410", "pnl_pct": -0.007, "sellable_qty":    4, "locked_qty":   0,
         "price": 3500.0, "available_cash":      0, "time": "10:30"},
        # 港股 00700 — 加仓 T+0（可卖 200，T+0 锁仓应为 0）
        {"code":  "00700", "pnl_pct":  0.015, "sellable_qty":  200, "locked_qty":   0,
         "price": 400.0,   "available_cash": 200000, "time": "10:30"},
        # 资金不足 — A股加仓改 hold
        {"code": "600519", "pnl_pct":  0.015, "sellable_qty": 1000, "locked_qty":   0,
         "price": 1700.0, "available_cash":   1000, "time": "10:30"},
        # UNKNOWN — 未识别代码
        {"code":   "ABCD", "pnl_pct": -0.012, "sellable_qty":  100, "locked_qty":   0,
         "price": 10.0,    "available_cash":      0, "time": "10:30"},
    ]

    print("\nB12 v2 多品种日内仓位动态管理 — 调仓指令演示\n")
    for order in run(sample):
        print_order(order)
