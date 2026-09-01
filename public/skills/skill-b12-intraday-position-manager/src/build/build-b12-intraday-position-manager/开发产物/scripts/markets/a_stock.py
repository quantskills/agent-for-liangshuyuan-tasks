"""
B12 v2 — A股 / A股ETF 决策模块

T+1 规则：今日新建仓位被锁定（locked_qty），当日不可卖。
    sellable = sellable_qty
    total    = sellable_qty + locked_qty
LOT_SIZE = 100，加仓校验现金 + 手续费。
"""
from common import (
    PNL_ADD_THRESHOLD, PNL_HALF_CUT_THRESHOLD, PNL_CLOSE_ALL_THRESHOLD,
    ADD_RATIO, HALF_CUT_RATIO,
    round_lot, make_instr, make_hold, reason_prefix,
)
from specs import CATEGORIES


def _required_cash(qty: int, price: float, cat: dict) -> float:
    """买入所需现金 = qty × price + 手续费（费率与最低费两者取大）。"""
    if qty <= 0 or price <= 0:
        return 0.0
    notional = qty * price
    fee = max(notional * cat["fee_rate"], cat["min_fee"])
    return notional + fee


def manage(item: dict, market: str) -> dict:
    """A股 / A股ETF 共用决策逻辑。market 取值 A_STOCK 或 A_ETF。"""
    code     = item["code"]
    pnl_pct  = float(item["pnl_pct"])
    sellable = int(item["sellable_qty"])
    locked   = int(item["locked_qty"])
    price    = float(item["price"])
    cash     = float(item["available_cash"])
    time_str = item["time"]

    cat     = CATEGORIES[market]
    lot     = cat["lot_size"]
    force_t = cat["force_close_time"]
    total   = sellable + locked

    # ── 1) 强平：到点收盘前 15 分钟 ──
    if time_str >= force_t:
        if sellable <= 0:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(market, sellable)} {force_t} 强平 但锁仓 {locked} 股 T+1 不可卖 hold",
            )
        sell = round_lot(sellable, lot)
        block = f"（T+1 阻断 {locked} 股）" if locked > 0 else ""
        return make_instr(
            code, pnl_pct, total, time_str, "sell", -sell, total - sell,
            f"{reason_prefix(market, sellable)} {force_t} 强平 平 {sell} 股{block}",
        )

    # ── 2) 全平：浮亏 >= 1% ──
    if pnl_pct <= PNL_CLOSE_ALL_THRESHOLD:
        if sellable <= 0:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(market, sellable)} 浮亏 {pnl_pct*100:.2f}% 全平 但锁仓 T+1 不可卖 hold",
            )
        sell = round_lot(sellable, lot)
        block = f"（T+1 阻断 {locked} 股）" if locked > 0 else ""
        return make_instr(
            code, pnl_pct, total, time_str, "sell", -sell, total - sell,
            f"{reason_prefix(market, sellable)} 浮亏 {pnl_pct*100:.2f}% 全平 {sell} 股{block}",
        )

    # ── 3) 砍半仓：浮亏 >= 0.5% ──
    if pnl_pct <= PNL_HALF_CUT_THRESHOLD:
        raw = int(sellable * HALF_CUT_RATIO)
        cut = round_lot(raw, lot)
        if cut <= 0:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(market, sellable)} 浮亏 {pnl_pct*100:.2f}% "
                f"砍半计算 {raw} 股不足一手 hold",
            )
        return make_instr(
            code, pnl_pct, total, time_str, "sell", -cut, total - cut,
            f"{reason_prefix(market, sellable)} 浮亏 {pnl_pct*100:.2f}% 砍半仓 {cut} 股",
        )

    # ── 4) 加仓：浮盈 > 1%（基数为 sellable） ──
    if pnl_pct > PNL_ADD_THRESHOLD:
        raw = int(sellable * ADD_RATIO)
        add = round_lot(raw, lot)
        if add <= 0:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(market, sellable)} 浮盈 {pnl_pct*100:.2f}% "
                f"加仓计算 {raw} 股不足一手 hold",
            )
        need = _required_cash(add, price, cat)
        if need > cash:
            return make_hold(
                code, pnl_pct, total, time_str,
                f"{reason_prefix(market, sellable, need)}[v2:cash_insufficient] "
                f"浮盈 {pnl_pct*100:.2f}% 加仓 {add} 股需 {need:.2f} 现金 {cash:.2f} 不足 hold",
            )
        return make_instr(
            code, pnl_pct, total, time_str, "buy", add, total + add,
            f"{reason_prefix(market, sellable, need)} 浮盈 {pnl_pct*100:.2f}% 加仓 {add} 股",
        )

    # ── 5) 默认 hold ──
    return make_hold(
        code, pnl_pct, total, time_str,
        f"{reason_prefix(market, sellable)} 浮盈/亏 {pnl_pct*100:+.2f}% 未触发任何条件 hold",
    )
