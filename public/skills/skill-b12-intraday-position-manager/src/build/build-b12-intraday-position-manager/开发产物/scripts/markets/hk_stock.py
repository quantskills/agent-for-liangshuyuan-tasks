"""
B12 v2 — 港股 / 港股ETF 决策模块

T+0：当日买入可卖。
    sellable = sellable_qty + locked_qty
LOT_SIZE 按 hk_lot_overrides 覆盖表查，未命中默认 100。
强平时间 15:45（港股下午半场 16:00 收盘）。
"""
from common import (
    PNL_ADD_THRESHOLD, PNL_HALF_CUT_THRESHOLD, PNL_CLOSE_ALL_THRESHOLD,
    ADD_RATIO, HALF_CUT_RATIO,
    round_lot, make_instr, make_hold, reason_prefix,
)
from specs import CATEGORIES, HK_LOT_OVERRIDES

MARKET = "HK_STOCK"


def _normalize_code(code: str) -> str:
    """归一化为 5 位数字代码用于查 hk_lot_overrides。"""
    c = code.upper().replace("HK", "")
    digits = "".join(ch for ch in c if ch.isdigit())
    return digits.zfill(5)[-5:]


def _lot_size(code: str) -> int:
    return HK_LOT_OVERRIDES.get(_normalize_code(code), CATEGORIES[MARKET]["lot_size"])


def _required_cash(qty: int, price: float, cat: dict) -> float:
    if qty <= 0 or price <= 0:
        return 0.0
    notional = qty * price
    fee = max(notional * cat["fee_rate"], cat["min_fee"])
    return notional + fee


def manage(item: dict) -> dict:
    code     = item["code"]
    pnl_pct  = float(item["pnl_pct"])
    sellable = max(0, int(item["sellable_qty"]) + int(item["locked_qty"]))
    price    = float(item["price"])
    cash     = float(item["available_cash"])
    time_str = item["time"]

    cat     = CATEGORIES[MARKET]
    lot     = _lot_size(code)
    force_t = cat["force_close_time"]
    total   = sellable

    # 1) 强平
    if time_str >= force_t:
        if sellable <= 0:
            return make_hold(code, pnl_pct, total, time_str,
                             f"{reason_prefix(MARKET, sellable)} {force_t} 强平 无持仓 hold")
        sell = round_lot(sellable, lot)
        return make_instr(
            code, pnl_pct, total, time_str, "sell", -sell, total - sell,
            f"{reason_prefix(MARKET, sellable)} {force_t} 强平 平 {sell} 股",
        )

    # 2) 全平
    if pnl_pct <= PNL_CLOSE_ALL_THRESHOLD:
        if sellable <= 0:
            return make_hold(code, pnl_pct, total, time_str,
                             f"{reason_prefix(MARKET, sellable)} 浮亏 {pnl_pct*100:.2f}% 全平 无持仓 hold")
        sell = round_lot(sellable, lot)
        return make_instr(
            code, pnl_pct, total, time_str, "sell", -sell, total - sell,
            f"{reason_prefix(MARKET, sellable)} 浮亏 {pnl_pct*100:.2f}% 全平 {sell} 股",
        )

    # 3) 砍半仓
    if pnl_pct <= PNL_HALF_CUT_THRESHOLD:
        raw = int(sellable * HALF_CUT_RATIO)
        cut = round_lot(raw, lot)
        if cut <= 0:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(MARKET, sellable)} 浮亏 {pnl_pct*100:.2f}% "
                f"砍半计算 {raw} 股不足一手 hold",
            )
        return make_instr(
            code, pnl_pct, total, time_str, "sell", -cut, total - cut,
            f"{reason_prefix(MARKET, sellable)} 浮亏 {pnl_pct*100:.2f}% 砍半仓 {cut} 股",
        )

    # 4) 加仓
    if pnl_pct > PNL_ADD_THRESHOLD:
        raw = int(sellable * ADD_RATIO)
        add = round_lot(raw, lot)
        if add <= 0:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(MARKET, sellable)} 浮盈 {pnl_pct*100:.2f}% "
                f"加仓计算 {raw} 股不足一手 hold",
            )
        need = _required_cash(add, price, cat)
        if need > cash:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(MARKET, sellable, need)}[v2:cash_insufficient] "
                f"浮盈 {pnl_pct*100:.2f}% 加仓 {add} 股需 {need:.2f} 现金 {cash:.2f} 不足 hold",
            )
        return make_instr(
            code, pnl_pct, total, time_str, "buy", add, total + add,
            f"{reason_prefix(MARKET, sellable, need)} 浮盈 {pnl_pct*100:.2f}% 加仓 {add} 股",
        )

    # 5) 默认 hold
    return make_hold(
        code, pnl_pct, total, time_str,
        f"{reason_prefix(MARKET, sellable)} 浮盈/亏 {pnl_pct*100:+.2f}% 未触发任何条件 hold",
    )
